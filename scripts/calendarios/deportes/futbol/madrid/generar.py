#!/usr/bin/env python3
"""Real Madrid (26/27) -> madrid.ics.

Agrega todas las competiciones en una misma tabla (Transfermarkt: LaLiga, Copa
del Rey, Champions League...). Los datos se guardan en ``estado/<id>/`` y el ICS
se publica en ``deportes/futbol/madrid.ics``. Solo stdlib.
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
from scripts.comun.fusion import fusionar, recolectar
from scripts.comun.http import fetch
from scripts.comun.ics import MADRID, Evento, generar_ics
from scripts.comun.log import log, warn

from scripts.calendarios.deportes.futbol.madrid.config import CONFIG, CONFIG_UEFA
from scripts.proveedores.transfermarkt import fuentes
from scripts.proveedores.uefa import fuentes as uefa


BASE_URL = (
    "https://www.transfermarkt.com/{slug}/spielplan/verein/"
    "{team_id}/saison_id/{season_id}/plus/1"
)


def _ronda_txt(p: dict) -> str:
    ronda = fuentes.traducir_ronda(p.get("ronda", ""))
    if p.get("competicion") == "liga" and ronda.isdigit():
        return f"J{ronda}"
    return ronda


def etiqueta(p: dict) -> str:
    comp = p.get("competicion")
    ronda = _ronda_txt(p)
    if comp == "liga":
        return ronda or "Liga"
    if comp == "copa":
        return f"Copa · {ronda}" if ronda else "Copa"
    if comp == "champions":
        return f"Champions · {ronda}" if ronda else "Champions"
    if comp == "europa":
        return f"Europa · {ronda}" if ronda else "Europa"
    if comp == "conference":
        return f"Conf · {ronda}" if ronda else "Conf"
    return ronda or comp or "Partido"


def _marca(p: dict) -> str:
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
    local = CONFIG.team_name if p.get("casa") else p.get("rival", "Rival")
    visitante = p.get("rival", "Rival") if p.get("casa") else CONFIG.team_name
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
    ronda = _ronda_txt(p)
    if ronda:
        ambito = f"{ambito} · {ronda}" if ambito else ronda
    lineas = [
        ambito,
        (
            f"{CONFIG.team_name} en casa vs {p.get('rival', 'Rival')}"
            if p.get("casa")
            else f"{CONFIG.team_name} fuera vs {p.get('rival', 'Rival')}"
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
            f"Resultado: {CONFIG.team_name} {p['resultado_equipo']}-{p['resultado_rival']} "
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
    s = p.get("sede") or {}
    partes = [s.get("pabellon"), s.get("ciudad") or s.get("direccion")]
    texto = ", ".join(x for x in partes if x)
    if texto:
        return texto
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


def _fuentes_oficiales():
    """Fuentes oficiales que sustituyen a Transfermarkt por competición."""
    return [
        (
            f"UEFA {comp.nombre.format(temporada=CONFIG_UEFA.temporada)}",
            {comp.codigo},
            lambda comp=comp: uefa.fetch_competicion(CONFIG_UEFA, comp),
        )
        for comp in CONFIG_UEFA.competiciones
    ]


def main() -> None:
    ctx = contexto_desde_ejecucion(__name__, __file__)
    json_path = ctx.ruta_estado("partidos.json")
    ics_path = ctx.ruta_ics
    zona = ZoneInfo(ctx.zona)

    prev = _cargar_previo(json_path)
    prev_by_uid = {p["uid"]: p for p in prev if isinstance(p, dict) and p.get("uid")}

    try:
        tm_partidos = _fetch_liga()
    except Exception as e:  # noqa: BLE001
        warn(f"transfermarkt: fallo ({e}); se usan solo las fuentes oficiales")
        tm_partidos = None

    try:
        partidos = fusionar(prev, recolectar(tm_partidos, _fuentes_oficiales()))
    except Exception as e:  # noqa: BLE001
        if not prev:
            raise
        warn(f"fuentes: fallo ({e}); se reutilizan {len(prev)} partidos previos")
        partidos = []

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
