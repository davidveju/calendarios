#!/usr/bin/env python3
"""Festivos de Madrid -> festivos/madrid.ics."""

from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, date
from pathlib import Path
from zoneinfo import ZoneInfo

from scripts.comun.archivos import escribir_json, escritura_atomica
from scripts.comun.contexto import contexto_desde_ejecucion
from scripts.comun.http import fetch
from scripts.comun.ics import MADRID, Evento, generar_ics
from scripts.comun.log import log, warn

from scripts.calendarios.festivos.madrid.config import CONFIG
from scripts.proveedores.openholidays import fuentes


def resumen(p: dict) -> str:
    return f"🎉 {p.get('rival', 'Festivo')}"


def descripcion(p: dict) -> str:
    return f"Festivo oficial de Madrid\nFuente: {p.get('acta', '')}"


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
            fin = inicio
            fin_raw = p.get("fin_madrid") or ""
            try:
                fin_dt = datetime.fromisoformat(fin_raw) if fin_raw else None
                if fin_dt is not None:
                    if fin_dt.tzinfo is None:
                        fin_dt = fin_dt.replace(tzinfo=MADRID)
                    fin = fin_dt.astimezone(MADRID)
            except (TypeError, ValueError):
                pass
            if fin <= inicio:
                fin = inicio + timedelta(hours=1)
            eventos.append(
                Evento(
                    uid=uid,
                    inicio=inicio,
                    fin=fin,
                    resumen=resumen(p),
                    descripcion=descripcion(p),
                    url=acta,
                    lugar="",
                    estado="CONFIRMED",
                    transparencia="OPAQUE",
                    todo_el_dia=True,
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


def _festivos_ciudad(config, desde: int, hasta: int) -> list[dict]:
    extra = []
    for year in range(desde, hasta + 1):
        for mes, dia, nombre in (config.extra_city or ()):
            iso = date(year, mes, dia).isoformat()
            kickoff = f"{iso}T00:00"
            fin = f"{iso}T23:59"
            uid = f"{config.uid_prefix}-ciudad-{iso}@{config.uid_dominio}"
            extra.append(
                {
                    "uid": uid,
                    "competicion": "festivo",
                    "competicion_nombre": config.nombre_calendario,
                    "estado": "pendiente",
                    "casa": True,
                    "rival": nombre,
                    "inicio_madrid": kickoff,
                    "fin_madrid": fin,
                    "fecha_provisional": False,
                    "acta": "https://www.madrid.es/",
                    "ronda": nombre,
                }
            )
    return extra


def main() -> None:
    ctx = contexto_desde_ejecucion(__name__, __file__)
    json_path = ctx.ruta_estado("partidos.json")
    ics_path = ctx.ruta_ics
    zona = ZoneInfo(ctx.zona)

    prev = _cargar_previo(json_path)
    hoy = datetime.now(zona).date()

    desde = hoy.year
    hasta = hoy.year + 2
    partidos = fuentes.generar_festivos(CONFIG, desde, hasta)

    # Corrección oficial del año en curso (OpenHolidays) si está disponible.
    try:
        url = (
            "https://openholidaysapi.org/PublicHolidays"
            f"?countryIsoCode=ES&languageIsoCode=ES"
            f"&validFrom={hoy.year}-01-01&validTo={hoy.year}-12-31"
            f"&subdivisionCode={CONFIG.subdivision_code}"
        )
        respuesta = fetch(url, timeout=30)
        oficiales = fuentes.obtener_festivos(respuesta, CONFIG)
        if oficiales:
            fechas_oficiales = {p["inicio_madrid"][:10] for p in oficiales}
            partidos = [
                p for p in partidos
                if not (p["inicio_madrid"].startswith(f"{hoy.year}-") and p["inicio_madrid"][:10] in fechas_oficiales)
            ] + oficiales
    except Exception as e:  # noqa: BLE001
        warn(f"festivos: OpenHolidays ({e}); se mantienen los generados")

    # deduplicar por (día, nombre)
    unicos = []
    vistos = set()
    for p in partidos:
        clave = p["inicio_madrid"][:10] + "|" + p["rival"].lower()
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(p)
    partidos = unicos

    if not partidos and prev:
        warn("FESTIVOS_FALLBACK")
        partidos = prev
    if not partidos:
        raise ValueError("festivos: no se obtuvo ningún resultado")

    # Validar UIDs
    conteo = {u: sum(1 for p in partidos if p.get("uid") == u) for u in {p["uid"] for p in partidos}}
    dups = sorted(u for u, n in conteo.items() if n > 1)
    if dups:
        raise ValueError(f"UIDs duplicados {dups}")

    eventos = a_eventos(partidos)
    ics = generar_ics(ctx.nombre, eventos, zona=zona)

    escribir_json(json_path, partidos)
    escritura_atomica(ics_path, ics.encode("utf-8"))

    log(f"festivos={len(partidos)} eventos_ics={len(eventos)}")
    log(f"json={json_path.relative_to(ctx.raiz)} ics={ics_path.relative_to(ctx.raiz)}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        raise
