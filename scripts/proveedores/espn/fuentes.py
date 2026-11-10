"""Resultados y calendario de un equipo desde la API pública de ESPN.

``site.api.espn.com`` no requiere clave y es accesible desde GitHub Actions,
donde Transfermarkt sirve una página vacía (bloqueo anti-bots por IP). Por
eso este proveedor actúa como *fallback* de LaLiga/Copa cuando TM falla: los
generadores lo intentan solo en ese caso y la fusión conserva los UIDs.

Limitaciones respecto a TM: ESPN no publica el número de jornada (``ronda``
queda vacío) y los nombres de rival pueden variar ligeramente (``"Atlético
Madrid"`` frente a ``"Atlético"``). La identidad del partido la dan fecha y
localía, así que ni los UIDs ni la fusión se ven afectados.

El proveedor no conoce equipos concretos; solo un :class:`ConfigESPN`.
"""

from __future__ import annotations

import json as _json
from datetime import datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")

SCOREBOARD = (
    "https://site.api.espn.com/apis/site/v2/sports/soccer/{slug}/scoreboard"
)
FUENTE = "espn"


def _temporada_anios(temporada: str) -> tuple[int, int]:
    """``"26/27"`` -> ``(2026, 2027)``."""
    a, b = temporada.split("/")
    return 2000 + int(a), 2000 + int(b)


def _ventana(temporada: str) -> tuple[str, str]:
    """Rango de fechas de la temporada (1 jul -> 1 jul) en ISO."""
    ini, fin = _temporada_anios(temporada)
    return f"{ini}-07-01", f"{fin}-07-01"


def _inicio_madrid(utc_raw: str) -> str | None:
    try:
        dt = datetime.fromisoformat(str(utc_raw).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return dt.astimezone(MADRID).replace(tzinfo=None).isoformat(timespec="minutes")


def _acta(evento: dict, eid: str) -> str:
    for enlace in evento.get("links") or []:
        rel = enlace.get("rel") or []
        if "summary" in rel and enlace.get("href"):
            return str(enlace["href"])
    return f"https://www.espn.com/soccer/match/_/gameId/{eid}"


def _sede(competicion: dict, *, casa: bool, casa_estadio: str) -> dict:
    sede: dict = {}
    venue = competicion.get("venue") or {}
    pabellon = str(venue.get("fullName") or "").strip()
    ciudad = str((venue.get("address") or {}).get("city") or "").strip()
    if pabellon:
        sede["pabellon"] = pabellon
    if ciudad:
        sede["ciudad"] = ciudad
    if casa and not sede and casa_estadio:
        sede["pabellon"] = casa_estadio
    return sede


def parse_evento(evento: dict, config, liga) -> dict | None:
    """Normaliza un evento del scoreboard. None si no es del equipo."""
    eid = str(evento.get("id") or "")
    comps = evento.get("competitions") or []
    if not eid or not comps:
        return None
    comp = comps[0]
    rivales = comp.get("competitors") or []
    propio = next(
        (c for c in rivales if str((c.get("team") or {}).get("id")) == str(config.team_id)),
        None,
    )
    if propio is None:
        return None
    otro = next((c for c in rivales if c is not propio), None)
    if otro is None:
        return None
    casa = propio.get("homeAway") == "home"
    rival = str((otro.get("team") or {}).get("displayName") or "").strip()
    if not rival:
        return None

    estado_raw = ((comp.get("status") or {}).get("type") or {}).get("state", "")
    completado = bool(((comp.get("status") or {}).get("type") or {}).get("completed"))
    jugado = estado_raw == "post" and completado

    provisional = not comp.get("timeValid", True)
    inicio = _inicio_madrid(comp.get("date") or evento.get("date") or "")
    if inicio is None:
        return None
    if provisional:
        inicio = inicio[:10] + "T12:00"

    partido = {
        "uid": f"{config.uid_prefix}-espn{eid}@{config.uid_dominio}",
        "competicion": liga.codigo,
        "competicion_nombre": liga.nombre.format(temporada=config.temporada),
        "estado": "jugado" if jugado else "pendiente",
        "casa": casa,
        "rival": rival,
        "inicio_madrid": inicio,
        "fecha_provisional": provisional,
        "uid_evento": eid,
        "fuente": FUENTE,
        "acta": _acta(evento, eid),
        "ronda": "",
        "sede": _sede(comp, casa=casa, casa_estadio=config.casa_estadio),
    }
    if not partido["sede"]:
        del partido["sede"]
    if jugado:
        try:
            goles = {
                str(c.get("homeAway")): int(str(c.get("score")))
                for c in rivales
            }
            res_local, res_visit = goles["home"], goles["away"]
        except (KeyError, TypeError, ValueError):
            return None
        if casa:
            victoria = res_local > res_visit
            equipo, rival_goles = res_local, res_visit
        else:
            victoria = res_visit > res_local
            equipo, rival_goles = res_visit, res_local
        partido.update(
            {
                "resultado_local": res_local,
                "resultado_visitante": res_visit,
                "resultado_equipo": equipo,
                "resultado_rival": rival_goles,
                "victoria": bool(victoria),
            }
        )
    return partido


def fetch_liga(config, liga, *, retries: int = 2, timeout: int = 30) -> list[dict]:
    """Descarga una competición completa (los dos años de la temporada)."""
    from scripts.comun.http import fetch

    inicio, fin = _ventana(config.temporada)
    ini_anio, fin_anio = _temporada_anios(config.temporada)
    partidos: list[dict] = []
    vistos: set[str] = set()
    eventos_totales = 0
    for anio in (ini_anio, fin_anio):
        url = f"{SCOREBOARD.format(slug=liga.slug)}?dates={anio}&limit=500"
        try:
            datos = _json.loads(fetch(url, retries=retries, timeout=timeout))
        except Exception as e:  # noqa: BLE001
            raise ValueError(f"espn {liga.slug} {anio} falló ({e})") from e
        eventos = datos.get("events") or []
        eventos_totales += len(eventos)
        for evento in eventos:
            eid = str(evento.get("id") or "")
            if not eid or eid in vistos:
                continue
            p = parse_evento(evento, config, liga)
            if p is None:
                continue
            if not (inicio <= p["inicio_madrid"][:10] < fin):
                continue
            vistos.add(eid)
            partidos.append(p)
    if eventos_totales == 0:
        # La liga no devolvió nada: respuesta rota, no "equipo sin partidos".
        raise ValueError(f"espn {liga.slug}: no se obtuvo ningún partido")
    return partidos


def fetch_competiciones(config) -> list[dict]:
    """Descarga todas las ligas de la config (falla si alguna falla)."""
    partidos: list[dict] = []
    for liga in config.ligas:
        partidos.extend(fetch_liga(config, liga))
    return partidos
