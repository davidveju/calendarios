"""Parsea los partidos de un equipo desde la API oficial de UEFA.

La API ``match.uefa.com`` no necesita clave. Con ``competitionId``,
``seasonYear`` y ``teamId`` devuelve solo los partidos de ese equipo en esa
competición, ya con traducciones al español.
"""

from __future__ import annotations

import json
from datetime import datetime
from zoneinfo import ZoneInfo

from scripts.proveedores.uefa.config import BASE, CompeticionUEFA, ConfigUEFA

MADRID = ZoneInfo("Europe/Madrid")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# UEFA usa estos estados; los desconocidos se tratan como pendientes.
_ESTADOS = {
    "FINISHED": "jugado",
    "UPCOMING": "pendiente",
    "CANCELED": "aplazado",
    "CANCELLED": "aplazado",
    "POSTPONED": "aplazado",
}


def _texto_es(valor: dict | None, clave: str = "name") -> str:
    traducciones = (valor or {}).get("translations") or {}
    return (traducciones.get(clave) or {}).get("ES") or ""


def _nombre_equipo(equipo: dict) -> str:
    return (
        _texto_es(equipo, "displayName")
        or _texto_es(equipo, "countryName")
        or equipo.get("internationalName")
        or ""
    )


def _ronda(partido: dict) -> str:
    ronda = partido.get("round") or {}
    base = _texto_es(ronda) or ((ronda.get("metaData") or {}).get("name") or "")
    meta = (ronda.get("metaData") or {}).get("name") or ""
    if meta != "League Phase":
        return base

    # En la fase liga el nombre de la ronda es genérico; aporta más contexto
    # el grupo (Nations League) y la jornada.
    grupo = _texto_es(partido.get("group"))
    partes: list[str] = []
    if grupo and grupo.lower() != "league":
        partes.append(grupo)
    secuencia = (partido.get("matchday") or {}).get("sequenceNumber")
    if secuencia:
        partes.append(f"Jornada {secuencia}")
    return " · ".join(partes) or base


def _sede(partido: dict) -> dict[str, str] | None:
    estadio = partido.get("stadium") or {}
    traducciones = estadio.get("translations") or {}
    pabellon = (
        (traducciones.get("officialName") or {}).get("ES")
        or (traducciones.get("mediaName") or {}).get("ES")
        or (traducciones.get("name") or {}).get("ES")
        or estadio.get("name")
        or ""
    )
    ciudad = ((estadio.get("city") or {}).get("translations") or {}).get("name") or {}
    ciudad = ciudad.get("ES") or ""
    sede = {}
    if pabellon:
        sede["pabellon"] = pabellon
    if ciudad:
        sede["ciudad"] = ciudad
    return sede or None


def _inicio_madrid(partido: dict) -> str:
    crudo = (partido.get("kickOffTime") or {}).get("dateTime") or ""
    if not crudo:
        return ""
    try:
        dt = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return ""
    if dt.tzinfo is None:
        return ""
    return dt.astimezone(MADRID).replace(tzinfo=None).isoformat(timespec="minutes")


def parse_partidos(
    payload_text: str,
    config: ConfigUEFA,
    competicion: CompeticionUEFA,
) -> list[dict]:
    """Normaliza la respuesta de UEFA para una competición."""
    try:
        datos = json.loads(payload_text)
    except (TypeError, ValueError):
        return []
    if not isinstance(datos, list):
        return []

    partidos: list[dict] = []
    vistos: set[str] = set()
    for match in datos:
        if not isinstance(match, dict):
            continue
        match_id = str(match.get("id") or "")
        if not match_id or match_id in vistos:
            continue

        casa_team = match.get("homeTeam") or {}
        fuera_team = match.get("awayTeam") or {}
        if str(casa_team.get("id")) == str(config.team_id):
            casa = True
            rival = _nombre_equipo(fuera_team)
        elif str(fuera_team.get("id")) == str(config.team_id):
            casa = False
            rival = _nombre_equipo(casa_team)
        else:
            continue

        inicio = _inicio_madrid(match)
        if not inicio:
            continue

        estado = _ESTADOS.get(str(match.get("status") or "").upper(), "pendiente")
        marcador = ((match.get("score") or {}).get("total")) or {}
        goles_local = marcador.get("home")
        goles_visitante = marcador.get("away")
        if estado == "jugado" and (goles_local is None or goles_visitante is None):
            estado = "pendiente"

        vistos.add(match_id)
        uid = f"{config.uid_prefix}-uefa-{match_id}@{config.uid_dominio}"
        partido = {
            "uid": uid,
            "competicion": competicion.codigo,
            "competicion_nombre": competicion.nombre.format(temporada=config.temporada),
            "estado": estado,
            "casa": casa,
            "rival": rival,
            "inicio_madrid": inicio,
            "fecha_provisional": False,
            "uid_evento": match_id,
            "fuente": "uefa",
            "acta": f"https://www.uefa.com/{competicion.slug}/match/{match_id}/",
            "ronda": _ronda(match),
        }
        sede = _sede(match)
        if sede:
            partido["sede"] = sede
        if estado == "jugado":
            gl, gv = int(goles_local), int(goles_visitante)
            partido["resultado_local"] = gl
            partido["resultado_visitante"] = gv
            partido["resultado_equipo"] = gl if casa else gv
            partido["resultado_rival"] = gv if casa else gl
            partido["victoria"] = partido["resultado_equipo"] > partido["resultado_rival"]
        partidos.append(partido)
    return partidos


def fetch_competicion(
    config: ConfigUEFA,
    competicion: CompeticionUEFA,
) -> list[dict]:
    """Descarga y normaliza una competición concreta."""
    from scripts.comun.http import fetch

    url = (
        f"{BASE}?competitionId={competicion.competition_id}"
        f"&seasonYear={competicion.season_year}"
        f"&teamId={config.team_id}&offset=0&limit=100"
    )
    return parse_partidos(
        fetch(url, user_agent=USER_AGENT, timeout=45), config, competicion
    )


def fetch_partidos(config: ConfigUEFA) -> list[dict]:
    """Descarga todas las competiciones configuradas."""
    partidos: list[dict] = []
    for competicion in config.competiciones:
        partidos.extend(fetch_competicion(config, competicion))
    return partidos
