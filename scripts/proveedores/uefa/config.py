"""Configuración de las competiciones UEFA de un equipo o selección."""

from __future__ import annotations

from dataclasses import dataclass

BASE = "https://match.uefa.com/v5/matches"


@dataclass(frozen=True)
class CompeticionUEFA:
    """Una competición y temporada de la API de UEFA.

    ``slug`` es el segmento de la URL pública que usa UEFA para el partido
    (``uefachampionsleague``, ``uefaconferenceleague``...).
    """

    codigo: str
    nombre: str
    competition_id: str
    season_year: str
    slug: str


@dataclass(frozen=True)
class ConfigUEFA:
    team_id: str
    team_name: str
    uid_prefix: str
    uid_dominio: str
    temporada: str = ""
    competiciones: tuple[CompeticionUEFA, ...] = ()
