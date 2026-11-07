"""Parsea la EuroLeague desde la API oficial api-live.euroleague.net."""

from __future__ import annotations

import json
from datetime import datetime, timezone, timedelta
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
BASE = "https://api-live.euroleague.net/v2/competitions/E/seasons/{season}/games"

BASE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def parse_games(payload_text: str, config) -> list[dict]:
    try:
        data = json.loads(payload_text)
    except (TypeError, ValueError):
        return []

    games = data.get("data", [])
    partidos: list[dict] = []
    vistos: set[str] = set()
    for g in games:
        local = g.get("local", {}).get("club", {}) or {}
        road = g.get("road", {}).get("club", {}) or {}
        code_home = local.get("code")
        code_away = road.get("code")
        if config.team_code not in (code_home, code_away):
            continue

        game_code = g.get("gameCode")
        uid = f"{config.uid_prefix}-el{game_code}@{config.uid_dominio}"
        if uid in vistos:
            continue
        vistos.add(uid)

        casa = config.team_code == code_home
        rival = (code_away if casa else code_home)
        # buscar nombre legible
        rival_name = (
            (road if casa else local).get("name")
            or (road if casa else local).get("abbreviatedName")
            or rival
        )

        utc_date = g.get("utcDate") or g.get("date")
        try:
            dt = datetime.fromisoformat(str(utc_date).replace("Z", "+00:00"))
        except (TypeError, ValueError):
            dt = None
        if dt is None or dt.tzinfo is None:
            continue
        inicio_local = dt.astimezone(MADRID).replace(tzinfo=None)
        kickoff = inicio_local.isoformat(timespec="minutes")

        played = bool(g.get("played"))
        home_score = g.get("local", {}).get("score")
        road_score = g.get("road", {}).get("score")
        estado = "jugado" if played else "pendiente"

        data_partido = {
            "uid": uid,
            "competicion": "euroliga",
            "competicion_nombre": f"EuroLeague {config.temporada}",
            "estado": estado,
            "casa": casa,
            "rival": rival_name,
            "inicio_madrid": kickoff,
            "fecha_provisional": False,
            "uid_evento": str(game_code),
            "acta": f"https://www.euroleaguebasketball.net/en/euroleague/teams/real-madrid/mad/",
            "ronda": g.get("roundName") or f"Round {g.get('round')}",
        }
        if played and home_score is not None and road_score is not None:
            victory = (home_score > road_score) if casa else (road_score > home_score)
            data_partido["victoria"] = bool(victory)
            data_partido["resultado_local"] = int(home_score)
            data_partido["resultado_visitante"] = int(road_score)
            data_partido["resultado_equipo"] = int(home_score) if casa else int(road_score)
            data_partido["resultado_rival"] = int(road_score) if casa else int(home_score)
        venue = g.get("venue") or {}
        name = venue.get("name", "")
        addr = venue.get("address", "")
        if name or addr:
            data_partido["sede"] = {"pabellon": name, "direccion": addr}
        partidos.append(data_partido)
    return partidos


def fetch_partidos(config) -> list[dict]:
    from scripts.comun.http import fetch

    page_size = 300
    offset = 0
    texto_acumulado: list[str] = []
    # La API pagina; concatenamos en un structure for parsing.
    clubs = set()
    all_games: list[dict] = []
    while True:
        url = (
            f"https://api-live.euroleague.net/v2/competitions/E/seasons/"
            f"{config.season_code}/games?limit={page_size}&offset={offset}"
        )
        txt = fetch(url, timeout=30)
        data = json.loads(txt)
        games = data.get("data", [])
        if not games:
            break
        all_games.extend(games)
        total = data.get("total", len(all_games))
        offset += page_size
        if offset >= total:
            break
    filtered = []
    for g in all_games:
        local = (g.get("local") or {}).get("club", {}).get("code")
        road = (g.get("road") or {}).get("club", {}).get("code")
        if config.team_code in (local, road):
            filtered.append(g)
    # Reuse parser on a synthetic payload.
    payload = {"data": filtered}
    return parse_games(json.dumps(payload), config)
