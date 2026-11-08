"""Configuración de competiciones de la FIFA para una selección."""

from __future__ import annotations

from dataclasses import dataclass

BASE = "https://api.fifa.com/api/v3/calendar/matches"


@dataclass(frozen=True)
class CompeticionFIFA:
    """Una competición y temporada de la API de FIFA.

    ``usar_fase`` permite omitir el nombre de la fase en competiciones donde
    no aporta nada (por ejemplo, los amistosos).
    """

    codigo: str
    nombre: str
    competition_id: str
    season_id: str
    usar_fase: bool = True


@dataclass(frozen=True)
class ConfigFIFA:
    team_id: str
    team_name: str
    uid_prefix: str
    uid_dominio: str
    temporada: str = ""
    competiciones: tuple[CompeticionFIFA, ...] = ()
