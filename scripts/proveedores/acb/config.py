"""Configuración de un equipo de la ACB/Liga Endesa."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigACB:
    team_name: str
    temporada: str
    uid_prefix: str
    uid_dominio: str
    casa_pabellon: str = ""
    url: str = (
        "https://acb.com/es/liga/noticias/"
        "calendario-liga-endesa-2026-27-todas-las-fechas-y-horarios-145767"
    )
