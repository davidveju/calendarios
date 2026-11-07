"""Configuración del calendario del Movistar Estudiantes."""

from __future__ import annotations

from scripts.proveedores.feb.config import ConfigFEB

CONFIG = ConfigFEB(
    equipo_id="1010493",
    equipo_corto="Estu",
    temporada="26/27",
    uid_prefix="estu-2627",
    uid_dominio="estudiantes-calendario",
    liga_url="https://competiciones.feb.es/estadisticas/Calendario.aspx",
    copa_url="https://www.feb.es/competiciones/resultados/copaespaa/73/2026",
    liga_nombre="Primera FEB 26/27",
    copa_nombre="Copa España 26/27",
    casa_pabellon="Movistar Arena, Madrid",
    jornadas_liga=34,
)
