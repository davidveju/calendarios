"""Configuración del calendario de festivos de Madrid."""

from __future__ import annotations

from scripts.proveedores.openholidays.config import ConfigFestivos

CONFIG = ConfigFestivos(
    nombre_calendario="Festivos de Madrid",
    subdivision_code="ES-MD-MD",
    uid_prefix="madrid-festivos",
    uid_dominio="madridfestivos-calendario",
    extra_city=(),
)
