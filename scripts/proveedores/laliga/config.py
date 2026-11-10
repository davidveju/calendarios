"""Configuración de un equipo en la API pública de LALIGA (sin clave propia)."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class LigaOficial:
    """Una competición de LALIGA (liga o copa).

    ``codigo`` debe coincidir con el de las demás fuentes del calendario
    (``"liga"``, ``"copa"``...) para que la fusión conserve los UIDs.
    ``base`` es el prefijo del ``subscriptionSlug`` (``"laliga-easports"``,
    ``"copa-del-rey"``); el año se deriva de la temporada. ``nombre`` admite
    ``{temporada}`` y ``acta`` es la página oficial de resultados.
    """

    codigo: str
    base: str
    nombre: str
    acta: str


@dataclass(frozen=True)
class ConfigLaLiga:
    """Parámetros que cambian de un equipo a otro."""

    team_slug: str
    team_name: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    ligas: tuple[LigaOficial, ...] = ()
    casa_estadio: str = ""
