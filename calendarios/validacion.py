"""Validación byte a byte de un iCalendar (RFC 5545)."""

from __future__ import annotations

import re
from pathlib import Path


def validar_bytes(data: bytes) -> list[str]:
    """Devuelve una lista de errores; vacía si el ICS es válido."""
    errores: list[str] = []
    if not data:
        return ["el fichero está vacío"]
    if not data.endswith(b"\r\n"):
        errores.append("el fichero no termina en CRLF")
    if b"\r\r\n" in data:
        errores.append("hay secuencias CR CR LF")
    resto = data.replace(b"\r\n", b"")
    if b"\r" in resto:
        errores.append("hay CR sin LF")
    if b"\n" in resto:
        errores.append("hay LF sin CR")

    lineas = data.split(b"\r\n")
    if lineas and lineas[-1] == b"":
        lineas.pop()
    for i, linea in enumerate(lineas, 1):
        if len(linea) > 75:
            errores.append(f"línea {i}: {len(linea)} octetos (>75)")
        if b"\r" in linea or b"\n" in linea:
            errores.append(f"línea {i}: salto de línea embebido")
        try:
            linea.decode("utf-8")
        except UnicodeDecodeError:
            errores.append(f"línea {i}: UTF-8 inválido")

    if not lineas or lineas[0] != b"BEGIN:VCALENDAR":
        errores.append("no empieza por BEGIN:VCALENDAR")
    if not lineas or lineas[-1] != b"END:VCALENDAR":
        errores.append("no termina por END:VCALENDAR")

    for obligatoria in (b"VERSION:2.0", b"PRODID:"):
        if not any(linea == obligatoria or linea.startswith(obligatoria) for linea in lineas):
            errores.append(f"falta {obligatoria.decode()}")

    inicios = sum(1 for x in lineas if x == b"BEGIN:VEVENT")
    finales = sum(1 for x in lineas if x == b"END:VEVENT")
    if inicios != finales:
        errores.append(f"VEVENT desbalanceados: {inicios} BEGIN / {finales} END")
    uids = [x[4:].decode("utf-8", "replace") for x in lineas if x.startswith(b"UID:")]
    if len(uids) != inicios:
        errores.append(f"UIDs ({len(uids)}) != VEVENT ({inicios})")
    if len(set(uids)) != len(uids):
        errores.append("hay UIDs duplicados")
    for prefijo in (b"DTSTART:", b"DTEND:"):
        n = sum(1 for x in lineas if x.startswith(prefijo))
        if n != inicios:
            errores.append(f"{prefijo.decode()} ({n}) != VEVENT ({inicios})")
    for i, linea in enumerate(lineas, 1):
        if linea.startswith((b"DTSTART:", b"DTEND:")) and not re.fullmatch(
            rb"DT(?:START|END):\d{8}T\d{6}Z", linea
        ):
            errores.append(f"línea {i}: fecha no UTC/ISO básica ({linea[:40]!r})")
    return errores


def validar_ics(path: Path) -> list[str]:
    """Valida el fichero ``path`` y devuelve sus errores."""
    return validar_bytes(path.read_bytes())
