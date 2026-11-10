"""Configuración del calendario del Getafe CF."""

from __future__ import annotations

from datetime import datetime

from scripts.proveedores.espn.config import ConfigESPN, LigaESPN
from scripts.proveedores.laliga.config import ConfigLaLiga, LigaOficial
from scripts.proveedores.transfermarkt.config import ConfigTM
from scripts.proveedores.uefa.config import CompeticionUEFA, ConfigUEFA

_now = datetime.now()
_season_start = _now.year if _now.month >= 8 else _now.year - 1
_season = f"{_season_start % 100:02d}/{(_season_start + 1) % 100:02d}"
_uid_prefix = f"{'getafe' if 'getafe' in __file__ else 'madrid'}-{_season_start % 100:02d}{(_season_start + 1) % 100:02d}"

CONFIG = ConfigTM(
    team_name="Getafe",
    slug="getafe-cf",
    team_id="3709",
    temporada=_season,
    uid_prefix=_uid_prefix,
    uid_dominio="getafe-calendario",
    season_id=str(_season_start),
    casa_pabellon="Coliseum, Getafe",
)

CONFIG_UEFA = ConfigUEFA(
    team_id="87960",
    team_name="Getafe",
    uid_prefix=_uid_prefix,
    uid_dominio="getafe-calendario",
    temporada=_season,
    competiciones=(
        CompeticionUEFA(
            codigo="conference",
            nombre="Conference League {temporada}",
            competition_id="2019",
            season_year=str(_season_start + 1),
            slug="uefaconferenceleague",
        ),
    ),
)

# Fallback cuando Transfermarkt bloquea (p. ej. CI): API pública sin clave.
CONFIG_ESPN = ConfigESPN(
    team_id="2922",
    team_name="Getafe",
    temporada=_season,
    uid_prefix=_uid_prefix,
    uid_dominio="getafe-calendario",
    ligas=(
        LigaESPN(codigo="liga", slug="esp.1", nombre="LaLiga {temporada}"),
        LigaESPN(
            codigo="copa", slug="esp.copa_del_rey", nombre="Copa del Rey {temporada}"
        ),
    ),
    casa_estadio="Coliseum, Getafe",
)

# Fuente oficial primaria (API pública de LALIGA; TM y ESPN quedan de fallback).
CONFIG_LALIGA = ConfigLaLiga(
    team_slug="getafe-cf",
    team_name="Getafe",
    temporada=_season,
    uid_prefix=_uid_prefix,
    uid_dominio="getafe-calendario",
    ligas=(
        LigaOficial(
            codigo="liga",
            base="laliga-easports",
            nombre="LaLiga {temporada}",
            acta="https://www.laliga.com/laliga-easports/resultados",
        ),
        LigaOficial(
            codigo="copa",
            base="copa-del-rey",
            nombre="Copa del Rey {temporada}",
            acta="https://www.laliga.com/otras-competiciones/copa-del-rey",
        ),
    ),
    casa_estadio="Coliseum, Getafe",
)
