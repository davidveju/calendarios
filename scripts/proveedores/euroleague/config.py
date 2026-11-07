"""Configuración de un equipo en la EuroLeague (API oficial)."""

from __future__ import annotations

from datetime import datetime

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigEuroLeague:
    team_code: str
    team_name: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    season_code: str = ""
    casa_pabellon: str = ""


def config_actual(team_code: str, team_name: str, uid_dominio: str, casa_pabellon: str = ""):
    now = datetime.now()
    season_start = now.year if now.month >= 9 else now.year - 1
    return ConfigEuroLeague(
        team_code=team_code,
        team_name=team_name,
        temporada=f"{season_start % 100:02d}/{(season_start + 1) % 100:02d}",
        uid_prefix=f"{uid_dominio}-{season_start}",
        uid_dominio=uid_dominio,
        season_code=f"E{season_start}",
        casa_pabellon=casa_pabellon,
    )
