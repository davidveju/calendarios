"""Configuración de un equipo concreto dentro de una competición FEB."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigFEB:
    """Parámetros que cambian de un equipo a otro.

    El parser es el mismo; el equipo, la temporada, las URLs y el prefijo de
    UIDs viven aquí. Añadir otro equipo de la FEB es crear otra instancia de
    esta configuración, no copiar el parser.
    """

    equipo_id: str
    equipo_corto: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    liga_url: str
    copa_url: str
    liga_nombre: str
    copa_nombre: str
    casa_pabellon: str
    jornadas_liga: int = 34
