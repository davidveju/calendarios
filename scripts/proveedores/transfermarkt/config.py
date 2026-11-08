"""Configuración de un equipo en Transfermarkt (schedule agregado)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CompeticionTM:
    """Regla para reconocer una competición en la cabecera de Transfermarkt.

    ``claves`` son fragmentos de texto que aparecen en la cabecera de la tabla
    (por ejemplo ``"world cup"``). ``nombre`` admite ``{temporada}``.
    """

    codigo: str
    nombre: str
    claves: tuple[str, ...] = ()


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
    competiciones: tuple[CompeticionTM, ...] = ()
