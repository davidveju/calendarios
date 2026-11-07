#!/usr/bin/env python3
"""Getafe CF (26/27): LaLiga -> getafe.ics.

Orquesta la API pública de ESPN, mantiene el histórico y genera el ICS con el
motor común. Los datos se guardan en ``estado/<id>/`` y el ICS se publica en
``deportes/futbol/getafe.ics``. Solo stdlib.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.comun.archivos import escribir_json, escritura_atomica
from scripts.comun.contexto import contexto_desde_ejecucion
from scripts.comun.http import fetch
from scripts.comun.ics import MADRID, Evento, generar_ics
from scripts.comun.log import log, warn
from scripts.proveedores.espn import fuentes

from scripts.calendarios.deportes.futbol.getafe.config import CONFIG


ESPN_BASE = fuentes.ESPN_BASE


def etiqueta(_p: dict) -> str:
    return "Liga"


def resumen(p: dict) -> str:
    emoji = "⚽"
    tag = etiqueta(p)
    local = (
        CONFIG.equipo_corto if p.get("casa") else p.get("rival", "Rival")
    )
    visitante = (
        p.get("rival", "Rival") if p.get("casa") else CONFIG.equipo_corto
    )
    if (
        p.get("estado") == "jugado"
        and "resultado_local" in p
        and "resultado_visitante" in p
    ):
        marca = "✅" if p.get("victoria") else "❌"
        gl, gv = p["resultado_local"], p["resultado_visitante"]
        return f"{emoji} {local} - {visitante} ({tag}: {gl}-{gv} {marca})"
    return f"{emoji} {local} - {visitante} ({tag})"


def descripcion(p: dict) -> str:
    ambito = f"{p.get('competicion_nombre', CONFIG.liga_nombre)} · {etiqueta(p)}"
    lineas = [
        ambito,
        (
            (f"{CONFIG.equipo_corto} en casa" if p.get("casa") else f"{CONFIG.equipo_corto} fuera")
            + f" vs {p.get('rival', 'Rival')}"
        ),
    ]
    if (
        p.get("estado") == "jugado"
        and "resultado_equipo" in p
        and "resultado_rival" in p
    ):
        lineas.append(
            f"Resultado: {CONFIG.equipo_corto} {p['resultado_equipo']}-{p['resultado_rival']} "
            + ("victoria ✅" if p.get("victoria") else "derrota ❌")
        )
    else:
        dt_raw = p.get("inicio_madrid") or ""
        try:
            dt = datetime.fromisoformat(dt_raw) if dt_raw else None
        except (TypeError, ValueError):
            dt = None
        if dt is not None:
            lineas.append(f"Inicio: {dt.strftime('%d/%m/%Y %H:%M')} (Madrid)")
        else:
            lineas.append("Fecha por determinar (por confirmar)")
    acta = p.get("acta", "")
    if acta:
        lineas.append(f"Acta: {acta}")
    return "\n".join(lineas)


def sede_txt(p: dict) -> str:
    s = p.get("sede") or {}
    return ", ".join(x for x in (s.get("pabellon"), s.get("direccion")) if x)


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
            lugar = sede_txt(p) or (CONFIG.casa_pabellon if p.get("casa") else "")
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


def _fetch_liga() -> list[dict]:
    # 1) Vista por defecto: calendario anual de la liga.
    base_url = f"{ESPN_BASE}/{CONFIG.liga_slug}/scoreboard"
    base_payload = fetch(base_url)
    fechas = fuentes.fechas_calendario(base_payload)
    if not fechas:
        warn("liga: no se pudo leer el calendario de fechas; se abandona la carga")
        return []

    seen: set[str] = set()
    partidos: list[dict] = []
    for compacto in fechas:
        url = f"{base_url}?dates={compacto}&limit=1000"
        try:
            payload = fetch(url, retries=2)
        except Exception as e:  # noqa: BLE001
            warn(f"liga: fecha {compacto} falló ({e}); se salta")
            continue
        for p in fuentes.extraer_eventos(payload, CONFIG):
            if p["uid"] not in seen:
                seen.add(p["uid"])
                partidos.append(p)

    return partidos


def main() -> None:
    ctx = contexto_desde_ejecucion(__name__, __file__)
    json_path = ctx.ruta_estado("partidos.json")
    ics_path = ctx.ruta_ics
    zona = ZoneInfo(ctx.zona)

    prev = _cargar_previo(json_path)
    prev_by_uid = {p["uid"]: p for p in prev if isinstance(p, dict) and p.get("uid")}

    feb_fallback = False
    try:
        liga = _fetch_liga()
        if not liga:
            raise ValueError("liga: no se obtuvo ningún partido")
    except Exception as e:  # noqa: BLE001
        if prev:
            warn(f"liga: fallo ({e}); se reutilizan {len(prev)} partidos previos")
            liga = prev
            feb_fallback = True
        else:
            raise

    # Revisar la kickoff publicada previamente si el nuevo scrape perdió la hora.
    hoy = datetime.now(zona).date()
    for p in liga:
        old = prev_by_uid.get(p["uid"])
        if (
            old
            and p.get("estado") == "jugado"
            and old.get("inicio_madrid")
            and not p.get("inicio_madrid")
        ):
            p["inicio_madrid"] = old["inicio_madrid"]

    # Validar UIDs
    from collections import Counter

    conteo = Counter(p.get("uid", "?") for p in liga)
    dups = sorted(u for u, n in conteo.items() if n > 1)
    if dups:
        raise ValueError(f"UIDs duplicados {dups}")

    eventos = a_eventos(liga)
    ics = generar_ics(ctx.nombre, eventos, zona=zona)

    escribir_json(json_path, liga)
    escritura_atomica(ics_path, ics.encode("utf-8"))

    jug = sum(1 for p in liga if p.get("estado") == "jugado")
    log(
        f"liga={len(liga)} jugados={jug} pendientes={len(liga) - jug} "
        f"eventos_ics={len(eventos)}"
    )
    log(
        f"json={json_path.relative_to(ctx.raiz)} ics={ics_path.relative_to(ctx.raiz)}"
    )
    if feb_fallback:
        warn("ESPN_FALLBACK=true: una fuente falló y se usó histórico; revisar logs")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        raise
