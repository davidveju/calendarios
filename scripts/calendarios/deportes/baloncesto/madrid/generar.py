#!/usr/bin/env python3
"""Real Madrid Baloncesto (Liga Endesa 26/27) -> madrid.ics."""

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

from scripts.calendarios.deportes.baloncesto.madrid.config import CONFIG
from scripts.proveedores.acb import fuentes


def resumen(p: dict) -> str:
    emoji = "🏀"
    tag = "EuroLeague" if p.get("competicion") == "euroliga" else "Liga Endesa"
    local = "Real Madrid" if p.get("casa") else p.get("rival", "Rival")
    visitante = p.get("rival", "Rival") if p.get("casa") else "Real Madrid"
    return f"{emoji} {local} - {visitante} ({tag})"


def descripcion(p: dict) -> str:
    nombre_comp = "EuroLeague 26/27" if p.get("competicion") == "euroliga" else "Liga Endesa 26/27"
    lineas = [nombre_comp, f"Real Madrid {'en casa' if p.get('casa') else 'fuera'} vs {p.get('rival', 'Rival')}"]
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
    for p in partidos:
        try:
            uid = str(p.get("uid") or "").strip()
            acta = str(p.get("acta") or "").strip()
            if not uid or not acta:
                raise KeyError(f"uid/acta ausentes ({uid!r})")
            inicio = _inicio_evento(p)
            if inicio is None:
                raise ValueError("sin fecha")
            eventos.append(
                Evento(
                    uid=uid,
                    inicio=inicio,
                    fin=inicio + timedelta(hours=2),
                    resumen=resumen(p),
                    descripcion=descripcion(p),
                    url=acta,
                    lugar=sede_txt(p),
                    estado="TENTATIVE" if p.get("fecha_provisional") else "CONFIRMED",
                    transparencia="TRANSPARENT",
                )
            )
        except Exception as e:  # noqa: BLE001
            warn(f"ics: se omite {p.get('uid', '?')}: {e}")
            omitidos += 1
    if omitidos:
        warn(f"ics: {omitidos} evento(s) omitido(s)")
    return eventos


def _cargar_previo(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:  # noqa: BLE001
        warn(f"previo {path} ilegible ({e}); se sigue sin histórico")
        return []


def main() -> None:
    ctx = contexto_desde_ejecucion(__name__, __file__)
    json_path = ctx.ruta_estado("partidos.json")
    ics_path = ctx.ruta_ics
    zona = ZoneInfo(ctx.zona)

    prev = _cargar_previo(json_path)
    html = fetch(CONFIG.url, timeout=30)
    partidos = fuentes.extraer_partidos(html, CONFIG)
    # Euroliga oficial desde el anuncio del calendario del Real Madrid.
    try:
        html_el = fetch(
            "https://www.realmadrid.com/en-US/news/basket/first-team/latest-news/"
            "el-calendario-del-real-madrid-para-la-euroliga-2026-27-29-07-2026",
            timeout=30,
        )
        euro = fuentes.extraer_euroliga(html_el, CONFIG)
        if euro:
            partidos.extend(euro)
    except Exception as e:  # noqa: BLE001
        warn(f"euroleague: fallo ({e}); solo ACB disponible")

    # Eliminar duplicados por (día, rival) tras combinar.
    vistos = set()
    unicos = []
    for p in partidos:
        clue = p["inicio_madrid"][:10] + "|" + p["rival"].lower()
        if clue in vistos:
            continue
        vistos.add(clue)
        unicos.append(p)
    partidos = unicos

    # Acumulación: mantener temporadas anteriores.
    actuales = {p["uid"] for p in partidos}
    partidos = [p for p in prev if p.get("uid") not in actuales] + partidos

    if not partidos and prev:
        warn("ACB: sin resultados, uso histórico")
        partidos = prev
    if not partidos:
        raise ValueError("ACB: no se obtuvo ningún partido")

    conteo = Counter(p.get("uid", "?") for p in partidos)
    dups = sorted(u for u, n in conteo.items() if n > 1)
    if dups:
        raise ValueError(f"UIDs duplicados {dups}")

    eventos = a_eventos(partidos)
    ics = generar_ics(ctx.nombre, eventos, zona=zona)

    escribir_json(json_path, partidos)
    escritura_atomica(ics_path, ics.encode("utf-8"))

    log(f"partidos={len(partidos)} eventos_ics={len(eventos)}")
    log(f"json={json_path.relative_to(ctx.raiz)} ics={ics_path.relative_to(ctx.raiz)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        raise
