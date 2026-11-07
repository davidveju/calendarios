"""Configuración de un equipo en Transfermarkt (schedule agregado)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigTM:
    """Parámetros que cambian de un equipo a otro."""

    team_name: str
    slug: str
    team_id: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    season_id: str = "2026"
    casa_pabellon: str = ""
