"""Configuración de un equipo en una competición de fútbol de ESPN."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigESPN:
    """Parámetros que cambian de un equipo a otro."""

    team_id: str
    team_name: str
    equipo_corto: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    liga_slug: str = "esp.1"
    liga_nombre: str = "LaLiga"
    casa_pabellon: str = ""
