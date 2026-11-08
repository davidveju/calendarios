"""Configuración del calendario de la Selección Española de Fútbol."""

from __future__ import annotations

from datetime import datetime

from scripts.proveedores.fifa.config import CompeticionFIFA, ConfigFIFA
from scripts.proveedores.transfermarkt.config import CompeticionTM, ConfigTM
from scripts.proveedores.uefa.config import CompeticionUEFA, ConfigUEFA

_now = datetime.now()
# Transfermarkt usa temporadas por año natural en las selecciones.
_anio = _now.year
# Las competiciones de clubes y la Nations League empiezan en agosto.
_season_start = _now.year if _now.month >= 8 else _now.year - 1
_temporada = f"{_season_start % 100:02d}/{(_season_start + 1) % 100:02d}"

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

CONFIG_FIFA = ConfigFIFA(
    team_id="43969",
    team_name="Spain",
    uid_prefix=f"espana-{_anio}",
    uid_dominio="espana-calendario",
    temporada=str(_anio),
    competiciones=(
        CompeticionFIFA(
            codigo="amistoso",
            nombre="Amistoso internacional",
            competition_id="cesdwwnxbc5fmajgroc0hqzy2",
            season_id="dezv8l0fzgcxtejl0dwmy1gyc",
            usar_fase=False,
        ),
        CompeticionFIFA(
            codigo="mundial",
            nombre="Copa Mundial {temporada}",
            competition_id="17",
            season_id="285023",
        ),
    ),
)

CONFIG_UEFA = ConfigUEFA(
    team_id="122",
    team_name="Spain",
    uid_prefix=f"espana-{_anio}",
    uid_dominio="espana-calendario",
    temporada=_temporada,
    competiciones=(
        CompeticionUEFA(
            codigo="nations",
            nombre="UEFA Nations League {temporada}",
            competition_id="2014",
            season_year=str(_season_start + 1),
            slug="uefanationsleague",
        ),
        CompeticionUEFA(
            codigo="finalissima",
            nombre="Finalissima",
            competition_id="2020",
            season_year="2026",
            slug="finalissima",
        ),
    ),
)
