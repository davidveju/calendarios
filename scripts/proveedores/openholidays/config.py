"""Configuración de un calendario de festivos por subdivisión OpenHolidays."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConfigFestivos:
    nombre_calendario: str
    subdivision_code: str
    uid_prefix: str
    uid_dominio: str
    extra_city: tuple[tuple[int, int, str], ...] = ()
