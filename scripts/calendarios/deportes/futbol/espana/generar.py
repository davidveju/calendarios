#!/usr/bin/env python3
"""Selección Española de Fútbol -> espana.ics.

Agrega amistosos, Mundial, Nations League y Finalissima en un mismo calendario
(Transfermarkt). Los datos se guardan en ``estado/<id>/`` y el ICS se publica
en ``deportes/futbol/espana.ics``. Solo stdlib.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.comun.archivos import escribir_json, escritura_atomica
from scripts.comun.contexto import contexto_desde_ejecucion
from scripts.comun.http import fetch
from scripts.comun.ics import MADRID, Evento, generar_ics
from scripts.comun.log import log, warn

from scripts.calendarios.deportes.futbol.espana.config import CONFIG
from scripts.proveedores.transfermarkt import fuentes


BASE_URL = (
    "https://www.transfermarkt.com/{slug}/spielplan/verein/"
    "{team_id}/saison_id/{season_id}/plus/1"
)

NOMBRE = "España"

# Transfermarkt publica los nombres en inglés; el ICS se muestra en español.
RIVALES = {
    "Argentina": "Argentina",
    "Austria": "Austria",
    "Belgium": "Bélgica",
    "Brazil": "Brasil",
    "Cape Verde": "Cabo Verde",
    "Croatia": "Croacia",
    "Czechia": "Chequia",
    "Denmark": "Dinamarca",
    "Egypt": "Egipto",
    "England": "Inglaterra",
    "France": "Francia",
    "Germany": "Alemania",
    "Greece": "Grecia",
    "Iraq": "Irak",
    "Italy": "Italia",
    "Mexico": "México",
    "Morocco": "Marruecos",
    "Netherlands": "Países Bajos",
    "Norway": "Noruega",
    "Peru": "Perú",
    "Poland": "Polonia",
    "Portugal": "Portugal",
    "Saudi Arabia": "Arabia Saudí",
    "Scotland": "Escocia",
    "Serbia": "Serbia",
    "Sweden": "Suecia",
    "Switzerland": "Suiza",
    "Turkey": "Turquía",
    "Uruguay": "Uruguay",
    "USA": "Estados Unidos",
    "United States": "Estados Unidos",
    "Wales": "Gales",
}

def etiqueta(p: dict) -> str:
    comp = p.get("competicion")
    ronda = fuentes.traducir_ronda(p.get("ronda", ""))
    if comp == "amistoso":
        return "Amistoso"
    if comp == "finalissima":
        return "Finalissima"
    base = {
        "mundial": "Mundial",
        "nations": "Nations",
        "euro": "Euro",
        "clasificacion": "Clasificación",
    }.get(comp)
    if base:
        return f"{base} · {ronda}" if ronda else base
    return ronda or comp or "Partido"


def _rival(p: dict) -> str:
    rival = p.get("rival", "Rival")
    return RIVALES.get(rival, rival)


def _marca(p: dict) -> str:
    """Marca del resultado desde el punto de vista de España."""
    gl = p.get("resultado_equipo")
    gv = p.get("resultado_rival")
    if gl is None or gv is None:
        return ""
    if gl > gv:
        return "✅"
    if gl < gv:
        return "❌"
    return "🤝"


def resumen(p: dict) -> str:
    emoji = "⚽"
    tag = etiqueta(p)
    rival = _rival(p)
    local = NOMBRE if p.get("casa") else rival
    visitante = rival if p.get("casa") else NOMBRE
    if (
        p.get("estado") == "jugado"
        and "resultado_local" in p
        and "resultado_visitante" in p
    ):
        gl, gv = p["resultado_local"], p["resultado_visitante"]
        return f"{emoji} {local} - {visitante} ({tag}: {gl}-{gv} {_marca(p)})"
    return f"{emoji} {local} - {visitante} ({tag})"


def descripcion(p: dict) -> str:
    ambito = p.get("competicion_nombre", "")
    ronda = fuentes.traducir_ronda(p.get("ronda", ""))
    if ronda:
        ambito = f"{ambito} · {ronda}" if ambito else ronda
    lineas = [
        ambito,
        (
            f"{NOMBRE} en casa vs {_rival(p)}"
            if p.get("casa")
            else f"{NOMBRE} fuera vs {_rival(p)}"
        ),
    ]
    if (
        p.get("estado") == "jugado"
        and "resultado_equipo" in p
        and "resultado_rival" in p
    ):
        marca = _marca(p)
        texto = {"✅": "victoria", "❌": "derrota", "🤝": "empate"}.get(marca, "")
        lineas.append(
            f"Resultado: {NOMBRE} {p['resultado_equipo']}-{p['resultado_rival']} "
            f"{texto} {marca}".rstrip()
        )
    else:
        dt_raw = p.get("inicio_madrid") or ""
        try:
            dt = datetime.fromisoformat(dt_raw) if dt_raw else None
        except (TypeError, ValueError):
            dt = None
        if dt is not None:
            if p.get("fecha_provisional"):
                lineas.append(
                    f"Inicio provisional: {dt.strftime('%d/%m/%Y %H:%M')} (Madrid, por confirmar)"
                )
            else:
                lineas.append(f"Inicio: {dt.strftime('%d/%m/%Y %H:%M')} (Madrid)")
        else:
            lineas.append("Fecha por determinar (por confirmar)")
    acta = p.get("acta", "")
    if acta:
        lineas.append(f"Acta: {acta}")
    return "\n".join(lineas)


def sede_txt(p: dict) -> str:
    return CONFIG.casa_pabellon if p.get("casa") else ""


def _inicio_evento(p: dict):
    dt_raw = p.get("inicio_madrid") or ""
    if not dt_raw:
        return None
    try:
        dt = datetime.fromisoformat(dt_raw)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=MADRID)
    return dt.astimezone(MADRID)


def a_eventos(partidos: list[dict]) -> list[Evento]:
    eventos: list[Evento] = []
    omitidos = 0
    aplazados = 0
    for p in partidos:
        if p.get("estado") == "aplazado":
            aplazados += 1
            continue
        try:
            uid = str(p.get("uid") or "").strip()
            acta = str(p.get("acta") or "").strip()
            if not uid or not acta:
                raise KeyError(f"uid/acta ausentes ({uid!r})")
            inicio = _inicio_evento(p)
            if inicio is None:
                raise ValueError("sin fecha")
            lugar = sede_txt(p)
            eventos.append(
                Evento(
                    uid=uid,
                    inicio=inicio,
                    fin=inicio + timedelta(hours=2),
                    resumen=resumen(p),
                    descripcion=descripcion(p),
                    url=acta,
                    lugar=lugar,
                    estado="TENTATIVE" if p.get("fecha_provisional") else "CONFIRMED",
                    transparencia="TRANSPARENT",
                )
            )
        except Exception as e:  # noqa: BLE001
            warn(f"ics: se omite {p.get('uid', '?')}: {e}")
            omitidos += 1
    if aplazados:
        log(f"ics: {aplazados} partido(s) aplazado(s) sin evento")
    if omitidos:
        warn(f"ics: {omitidos} evento(s) omitido(s)")
    return eventos


def _cargar_previo(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            return []
        return data
    except Exception as e:  # noqa: BLE001
        warn(f"previo {path} ilegible ({e}); se sigue sin histórico")
        return []


def _fetch_partidos() -> list[dict]:
    url = BASE_URL.format(
        slug=CONFIG.slug,
        team_id=CONFIG.team_id,
        season_id=CONFIG.season_id,
    )
    html = fetch(url, user_agent=fuentes.USER_AGENT)
    partidos = fuentes.extraer_partidos(html, CONFIG)
    if not partidos:
        raise ValueError("transfermarkt: no se obtuvo ningún partido")
    return partidos


def main() -> None:
    ctx = contexto_desde_ejecucion(__name__, __file__)
    json_path = ctx.ruta_estado("partidos.json")
    ics_path = ctx.ruta_ics
    zona = ZoneInfo(ctx.zona)

    prev = _cargar_previo(json_path)
    prev_by_uid = {p["uid"]: p for p in prev if isinstance(p, dict) and p.get("uid")}

    try:
        partidos = _fetch_partidos()
    except Exception as e:  # noqa: BLE001
        if prev:
            warn(f"transfermarkt: fallo ({e}); se reutilizan {len(prev)} partidos previos")
            partidos = prev
        else:
            raise

    # Acumulación: los partidos de temporadas anteriores se conservan.
    claves_actuales = {p["uid"] for p in partidos}
    partidos = [p for p in prev if p.get("uid") not in claves_actuales] + partidos

    for p in partidos:
        old = prev_by_uid.get(p["uid"])
        if (
            old
            and p.get("estado") == "jugado"
            and old.get("inicio_madrid")
            and not p.get("inicio_madrid")
        ):
            p["inicio_madrid"] = old["inicio_madrid"]

    conteo = Counter(p.get("uid", "?") for p in partidos)
    dups = sorted(u for u, n in conteo.items() if n > 1)
    if dups:
        raise ValueError(f"UIDs duplicados {dups}")

    eventos = a_eventos(partidos)
    ics = generar_ics(ctx.nombre, eventos, zona=zona)

    escribir_json(json_path, partidos)
    escritura_atomica(ics_path, ics.encode("utf-8"))

    jug = sum(1 for p in partidos if p.get("estado") == "jugado")
    bycomp = Counter(p.get("competicion", "?") for p in partidos)
    log(
        f"partidos={len(partidos)} por_competicion={dict(bycomp)} "
        f"jugados={jug} pendientes={len(partidos) - jug} eventos_ics={len(eventos)}"
    )
    log(
        f"json={json_path.relative_to(ctx.raiz)} ics={ics_path.relative_to(ctx.raiz)}"
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        raise
