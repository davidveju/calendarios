"""Configuración del calendario del Getafe CF."""

from __future__ import annotations

from scripts.proveedores.transfermarkt.config import ConfigTM

CONFIG = ConfigTM(
    team_name="Getafe",
    slug="getafe-cf",
    team_id="3709",
    temporada="26/27",
    uid_prefix="getafe-2627",
    uid_dominio="getafe-calendario",
    season_id="2026",
    casa_pabellon="Coliseum, Getafe",
)
