"""Parsea el calendario oficial de la Liga Endesa desde la noticia de acb.com."""

from __future__ import annotations

import html as _html
import re

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _limpia(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\\u0026", "&").strip()


def _normalizar(texto: str) -> str:
    return texto.encode("latin-1", "backslashreplace").decode("unicode_escape") if False else texto


def extraer_partidos(html: str, config) -> list[dict]:
    texto = _limpia(html)
    # Entradas: **FECHA**. EQUIPO - EQUIPO, (con posibles comas dentro)
    dia_names = "lunes|martes|miércoles|jueves|viernes|sábado|domingo"
    patron = re.compile(
        rf"\*\*(?P<fecha>(?:{dia_names})[^*]+?\([^)]*\))\*\*\s*\.?\s*(?P<match>.+?)(?=\s*-\s*\*\*|\Z)",
        re.I | re.S,
    )
    partidos: list[dict] = []
    for m in patron.finditer(texto):
        fecha_raw = m.group("fecha").strip()
        match_txt = m.group("match").replace("\\r", " ").replace("\\n", " ")
        match_txt = _limpia(match_txt)
        match_txt = re.sub(r"###.*", "", match_txt).strip(" -·")
        match_txt = re.sub(r"\s+", " ", match_txt)
        if config.team_name not in match_txt:
            continue

        # día(s) / mes
        mfecha = re.search(
            r"(\d{1,2})(?:/\d+)*\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?",
            fecha_raw,
            re.I,
        )
        if not mfecha:
            continue
        dias = [int(x) for x in re.findall(r"\d{1,2}", mfecha.group(1))]
        dia = dias[0] if dias else 1
        mes_txt = mfecha.group(2).lower()
        mes = MESES.get(mes_txt)
        if mes is None:
            continue
        anio = mfecha.group(3)
        if anio is None:
            anio_int = 2026 if mes >= 9 else 2027
        else:
            anio_int = int(anio)

        # hora
        mhora = re.search(r"\(([^)]*)\)", fecha_raw)
        hora_txt = (mhora.group(1) if mhora else "").strip()
        provisional = "sin confirmar" in hora_txt.lower() or hora_txt == "Horario sin confirmar"
        mtime = re.search(r"(\d{1,2}):(\d{2})", hora_txt)
        if mtime and not provisional:
            hh, mm = mtime.group(1), mtime.group(2)
            kickoff = f"{anio_int:04d}-{mes:02d}-{dia:02d}T{int(hh):02d}:{int(mm):02d}"
        else:
            kickoff = f"{anio_int:04d}-{mes:02d}-{dia:02d}T12:00"
            provisional = True

        # rivales
        match_txt = _html.unescape(match_txt).strip(" .-")
        _limpiar = lambda x: re.sub(r"\s+", " ", x.replace("\\r", " ").replace("\\n", " ").strip())
        partes = [_limpiar(x.strip()) for x in match_txt.split(" - ")]
        if len(partes) != 2:
            partes = [_limpiar(x.strip()) for x in re.split(r"\s+-\s+", match_txt)]
        if len(partes) != 2:
            continue
        local_txt, visit_txt = partes
        casa = config.team_name in local_txt
        rival = visit_txt if casa else local_txt

        uid = f"{config.uid_prefix}-{anio_int}{mes:02d}{dia:02d}-{rival.lower().replace(' ', '-')}"
        partidos.append(
            {
                "uid": f"{uid}@{config.uid_dominio}",
                "competicion": "acb",
                "competicion_nombre": f"Liga Endesa {config.temporada}",
                "estado": "pendiente",
                "casa": casa,
                "rival": rival,
                "inicio_madrid": kickoff,
                "fecha_provisional": provisional,
                "acta": config.url,
                "ronda": "Regular",
            }
        )
    # La página repite la tabla en HTML y en JSON embebido; nos quedamos con
    # una entrada por (día, rival).
    unicos = []
    vistos = set()
    for p in partidos:
        clave = (
            p["inicio_madrid"][:10]
            + "|"
            + re.sub(r"[^a-z0-9]", "", p["rival"].lower())
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(p)
    return unicos
