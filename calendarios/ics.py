"""Generación de iCalendar (RFC 5545) sin dependencias externas.

Los calendarios concretos solo tienen que construir una lista de :class:`Evento`;
este módulo se encarga del escapado, plegado de líneas, fechas UTC y cabeceras.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Iterable
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
ESTADOS_VALIDOS = {"CONFIRMED", "TENTATIVE", "CANCELLED"}
TRANSPARENCIAS_VALIDAS = {"OPAQUE", "TRANSPARENT"}


@dataclass(frozen=True)
class Evento:
    """Un evento listo para publicar en un calendario ICS."""

    uid: str
    inicio: datetime
    fin: datetime | None = None
    resumen: str = ""
    descripcion: str = ""
    url: str = ""
    lugar: str = ""
    estado: str = "CONFIRMED"
    transparencia: str = "TRANSPARENT"
    secuencia: int = 0


def esc(texto: str) -> str:
    """Escapa un valor TEXT de iCalendar."""
    return (
        texto.replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\r\n", "\\n")
        .replace("\n", "\\n")
        .replace("\r", "\\n")
    )


def _prefijo_utf8(raw: bytes, limite: int) -> int:
    """Mayor corte <= limite que termina en un carácter UTF-8 completo."""
    corte = min(limite, len(raw))
    for k in range(corte, max(corte - 4, -1), -1):
        try:
            raw[:k].decode("utf-8")
            return k
        except UnicodeDecodeError:
            continue
    raise ValueError("fold_line: bytes UTF-8 inválidos")


def fold_line(line: str, limit: int = 75) -> str:
    """Pliega una línea ICS por octetos UTF-8 (RFC 5545 §3.1) sin partir multibyte."""
    if limit < 2:
        raise ValueError("fold_line: límite demasiado pequeño")
    raw = line.encode("utf-8")
    if len(raw) <= limit:
        return line
    partes: list[str] = []
    corte = _prefijo_utf8(raw, limit)
    partes.append(raw[:corte].decode("utf-8"))
    resto = raw[corte:]
    while resto:
        corte = _prefijo_utf8(resto, limit - 1)
        partes.append(" " + resto[:corte].decode("utf-8"))
        resto = resto[corte:]
    return "\r\n".join(partes)


def _a_utc(dt: datetime, zona: ZoneInfo) -> datetime:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=zona)
    return dt.astimezone(timezone.utc)


def _validar_texto_un_linea(valor: str, campo: str) -> str:
    valor = str(valor or "").strip()
    if "\r" in valor or "\n" in valor:
        raise ValueError(f"{campo}: no puede contener saltos de línea")
    return valor


def _validar_evento(evento: Evento, zona: ZoneInfo) -> tuple[datetime, datetime, str]:
    uid = _validar_texto_un_linea(evento.uid, "UID")
    if not uid:
        raise ValueError("UID vacío")
    resumen = _validar_texto_un_linea(evento.resumen, f"SUMMARY {uid}")
    if not resumen:
        raise ValueError(f"SUMMARY vacío en {uid}")
    estado = str(evento.estado or "").upper()
    if estado not in ESTADOS_VALIDOS:
        raise ValueError(f"STATUS no válido en {uid}: {evento.estado!r}")
    transparencia = str(evento.transparencia or "").upper()
    if transparencia not in TRANSPARENCIAS_VALIDAS:
        raise ValueError(f"TRANSP no válido en {uid}: {evento.transparencia!r}")
    if not isinstance(evento.secuencia, int) or evento.secuencia < 0:
        raise ValueError(f"SEQUENCE no válido en {uid}: {evento.secuencia!r}")

    inicio = _a_utc(evento.inicio, zona)
    fin = _a_utc(evento.fin, zona) if evento.fin is not None else inicio + timedelta(hours=2)
    if fin <= inicio:
        raise ValueError(f"DTEND anterior o igual a DTSTART en {uid}")
    return inicio, fin, resumen


def generar_ics(
    nombre: str,
    eventos: Iterable[Evento],
    *,
    ahora: datetime | None = None,
    zona: ZoneInfo = MADRID,
    prodid: str = "-//davidveju//calendarios//ES",
) -> str:
    """Genera un ICS completo a partir de eventos.

    - Valida UIDs únicos y no vacíos (un duplicado crearía eventos duplicados).
    - Ordena los eventos por fecha de inicio.
    - Convierte las fechas a UTC y usa CRLF + plegado RFC 5545.
    - ``DTSTAMP`` es el mismo para todos los eventos de la ejecución.
    """
    nombre = _validar_texto_un_linea(nombre, "X-WR-CALNAME")
    if not nombre:
        raise ValueError("El calendario necesita un nombre")

    lista = list(eventos)
    conteo = Counter(_validar_texto_un_linea(e.uid, "UID") for e in lista)
    duplicados = sorted(uid for uid, n in conteo.items() if n > 1)
    if duplicados:
        raise ValueError(f"UIDs duplicados: {duplicados}")

    if ahora is None:
        ahora = datetime.now(timezone.utc)
    elif ahora.tzinfo is None:
        ahora = ahora.replace(tzinfo=timezone.utc)
    dtstamp = ahora.astimezone(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    lineas = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        f"PRODID:{prodid}",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
        f"X-WR-CALNAME:{esc(nombre)}",
        "X-WR-TIMEZONE:Europe/Madrid",
    ]

    for evento in sorted(lista, key=lambda e: _a_utc(e.inicio, zona)):
        inicio, fin, resumen = _validar_evento(evento, zona)
        uid = _validar_texto_un_linea(evento.uid, "UID")
        url = _validar_texto_un_linea(evento.url, f"URL {uid}")
        descripcion = str(evento.descripcion or "")
        lugar = str(evento.lugar or "")
        estado = str(evento.estado).upper()
        transparencia = str(evento.transparencia).upper()

        contenido = [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTAMP:{dtstamp}",
            f"DTSTART:{inicio.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{fin.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:{esc(resumen)}",
        ]
        if descripcion:
            contenido.append(f"DESCRIPTION:{esc(descripcion)}")
        if url:
            contenido.append(f"URL:{url}")
        if lugar:
            contenido.append(f"LOCATION:{esc(lugar)}")
        contenido += [
            f"TRANSP:{transparencia}",
            f"STATUS:{estado}",
            f"SEQUENCE:{evento.secuencia}",
            "END:VEVENT",
        ]
        lineas.extend(fold_line(linea) for linea in contenido)

    lineas.append("END:VCALENDAR")
    return "\r\n".join(lineas) + "\r\n"
