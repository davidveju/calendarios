"""Configuración del calendario de la Selección Española de Fútbol."""

from __future__ import annotations

from datetime import datetime

from scripts.proveedores.transfermarkt.config import CompeticionTM, ConfigTM

_now = datetime.now()
# Transfermarkt usa temporadas por año natural en las selecciones.
_anio = _now.year

CONFIG = ConfigTM(
    team_name="Spain",
    slug="spanien",
    team_id="3375",
    temporada=str(_anio),
    uid_prefix=f"espana-{_anio}",
    uid_dominio="espana-calendario",
    season_id=str(_anio),
    casa_pabellon="",
    competiciones=(
        CompeticionTM(
            codigo="amistoso",
            nombre="Amistoso internacional",
            claves=("international friendlies", "friendlies"),
        ),
        CompeticionTM(
            codigo="mundial",
            nombre="Copa Mundial {temporada}",
            claves=("world cup",),
        ),
        CompeticionTM(
            codigo="nations",
            nombre="UEFA Nations League {temporada}",
            claves=("nations league",),
        ),
        CompeticionTM(
            codigo="finalissima",
            nombre="Finalissima",
            claves=("conmebol-uefa cup of champions", "finalissima"),
        ),
        CompeticionTM(
            codigo="euro",
            nombre="Eurocopa {temporada}",
            claves=("european championship", "euro "),
        ),
        CompeticionTM(
            codigo="clasificacion",
            nombre="Clasificación {temporada}",
            claves=("qualification", "qualifying", "qualifier"),
        ),
    ),
)
