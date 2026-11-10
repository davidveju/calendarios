"""Configuración de un equipo en la API pública de ESPN (sin clave)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LigaESPN:
    """Una competición de ESPN (p. ej. liga o copa de un país).

    ``codigo`` debe coincidir con el de las demás fuentes del calendario
    (``"liga"``, ``"copa"``...) para que la fusión conserve los UIDs.
    ``nombre`` admite ``{temporada}``.
    """

    codigo: str
    slug: str
    nombre: str


@dataclass(frozen=True)
class ConfigESPN:
    """Parámetros que cambian de un equipo a otro."""

    team_id: str
    team_name: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    ligas: tuple[LigaESPN, ...] = ()
    casa_estadio: str = ""
