"""Parsea los partidos de una selección desde la API oficial de FIFA.

La API ``api.fifa.com`` no necesita clave. Con ``idCompetition``,
``idSeason`` e ``idTeam`` devuelve solo los partidos de ese equipo. El
parámetro ``language=es`` localiza los nombres de equipo, fase y grupo.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from scripts.proveedores.fifa.config import BASE, CompeticionFIFA, ConfigFIFA

MADRID = ZoneInfo("Europe/Madrid")

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Estados de FIFA: 0 finalizado, 1 pendiente, 3 en directo, 4 abandonado,
# 7 aplazado, 8 cancelado, 12 alineaciones.
_ESTADOS = {
    0: "jugado",
    1: "pendiente",
    3: "pendiente",
    4: "aplazado",
    7: "aplazado",
    8: "aplazado",
    12: "pendiente",
}


def _texto(lista: list[dict] | None) -> str:
    """Primera descripción en español (o la primera disponible)."""
    if not lista:
        return ""
    for item in lista:
        if str(item.get("Locale") or "").lower().startswith("es"):
            return item.get("Description") or ""
    return lista[0].get("Description") or ""


def _dt_utc(partido: dict) -> datetime | None:
    crudo = partido.get("Date") or ""
    if not crudo:
        return None
    try:
        dt = datetime.fromisoformat(crudo.replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        return None
    return dt


def _inicio_madrid(partido: dict) -> str:
    dt = _dt_utc(partido)
    if dt is None:
        return ""
    return dt.astimezone(MADRID).replace(tzinfo=None).isoformat(timespec="minutes")


def _ronda(partido: dict, competicion: CompeticionFIFA) -> str:
    if not competicion.usar_fase:
        return ""
    fase = _texto(partido.get("StageName"))
    grupo = _texto(partido.get("GroupName"))
    if fase and grupo:
        return f"{fase} · {grupo}"
    return fase


def _url_partido(partido: dict) -> str:
    return (
        "https://www.fifa.com/en/match-centre/match/"
        f"{partido.get('IdCompetition')}/{partido.get('IdSeason')}/"
        f"{partido.get('IdStage')}/{partido.get('IdMatch')}"
    )


def parse_partidos(
    payload_text: str,
    config: ConfigFIFA,
    competicion: CompeticionFIFA,
) -> list[dict]:
    """Normaliza la respuesta de FIFA para una competición."""
    try:
        datos = json.loads(payload_text)
    except (TypeError, ValueError):
        return []
    if isinstance(datos, dict):
        resultados = datos.get("Results") or []
    elif isinstance(datos, list):
        resultados = datos
    else:
        return []

    partidos: list[dict] = []
    vistos: set[str] = set()
    for match in resultados:
        if not isinstance(match, dict):
            continue
        match_id = str(match.get("IdMatch") or "")
        if not match_id or match_id in vistos:
            continue

        casa_team = match.get("Home") or {}
        fuera_team = match.get("Away") or {}
        if str(casa_team.get("IdTeam")) == str(config.team_id):
            casa = True
            rival = _texto(fuera_team.get("TeamName"))
        elif str(fuera_team.get("IdTeam")) == str(config.team_id):
            casa = False
            rival = _texto(casa_team.get("TeamName"))
        else:
            continue

        dt = _dt_utc(match)
        inicio = _inicio_madrid(match)
        if not inicio or dt is None:
            continue

        estado = _ESTADOS.get(match.get("MatchStatus"), "pendiente")
        goles_local = casa_team.get("Score")
        goles_visitante = fuera_team.get("Score")
        # FIFA publica marcadores simulados en competiciones futuras (p. ej. el
        # cuadro del Mundial 2026). No se consideran resultados reales.
        if estado == "jugado" and dt > datetime.now(timezone.utc):
            estado = "pendiente"
            goles_local = goles_visitante = None
        if estado == "jugado" and (goles_local is None or goles_visitante is None):
            estado = "pendiente"

        vistos.add(match_id)
        uid = f"{config.uid_prefix}-fifa-{match_id}@{config.uid_dominio}"
        partido = {
            "uid": uid,
            "competicion": competicion.codigo,
            "competicion_nombre": competicion.nombre.format(temporada=config.temporada),
            "estado": estado,
            "casa": casa,
            "rival": rival,
            "inicio_madrid": inicio,
            "fecha_provisional": not bool(match.get("TimeDefined", True)),
            "uid_evento": match_id,
            "fuente": "fifa",
            "acta": _url_partido(match),
            "ronda": _ronda(match, competicion),
        }
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
    config: ConfigFIFA,
    competicion: CompeticionFIFA,
) -> list[dict]:
    """Descarga y normaliza una competición concreta."""
    from scripts.comun.http import fetch

    url = (
        f"{BASE}?idCompetition={competicion.competition_id}"
        f"&idSeason={competicion.season_id}"
        f"&idTeam={config.team_id}&count=100&language=es"
    )
    return parse_partidos(
        fetch(url, user_agent=USER_AGENT, timeout=45), config, competicion
    )


def fetch_partidos(config: ConfigFIFA) -> list[dict]:
    """Descarga todas las competiciones configuradas."""
    partidos: list[dict] = []
    for competicion in config.competiciones:
        partidos.extend(fetch_competicion(config, competicion))
    return partidos
