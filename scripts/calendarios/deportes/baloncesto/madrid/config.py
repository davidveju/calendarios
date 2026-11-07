"""Configuración del calendario del Real Madrid de baloncesto."""

from __future__ import annotations

from scripts.proveedores.acb.config import ConfigACB

CONFIG = ConfigACB(
    team_name="Real Madrid",
    temporada="26/27",
    uid_prefix="madrid-b-2627",
    uid_dominio="madridbaloncesto-calendario",
    casa_pabellon="Movistar Arena, Madrid",
)
