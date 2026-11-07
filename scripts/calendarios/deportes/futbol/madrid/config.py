"""Configuración del calendario del Real Madrid."""

from __future__ import annotations

from scripts.proveedores.transfermarkt.config import ConfigTM

CONFIG = ConfigTM(
    team_name="Real Madrid",
    slug="real-madrid",
    team_id="418",
    temporada="26/27",
    uid_prefix="madrid-2627",
    uid_dominio="madrid-calendario",
    season_id="2026",
    casa_pabellon="Santiago Bernabéu, Madrid",
)
