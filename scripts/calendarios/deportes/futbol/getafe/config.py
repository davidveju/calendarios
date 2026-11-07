"""Configuración del calendario del Getafe CF."""

from __future__ import annotations

from scripts.proveedores.espn.config import ConfigESPN

CONFIG = ConfigESPN(
    team_id="2922",
    team_name="Getafe",
    equipo_corto="Getafe",
    temporada="26/27",
    uid_prefix="getafe-2627",
    uid_dominio="getafe-calendario",
    liga_slug="esp.1",
    liga_nombre="LaLiga",
    casa_pabellon="Coliseum, Getafe",
)
