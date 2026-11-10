"""Configuración del calendario del Real Madrid."""

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
    team_name="Real Madrid",
    slug="real-madrid",
    team_id="418",
    temporada=_season,
    uid_prefix=_uid_prefix,
    uid_dominio="madrid-calendario",
    season_id=str(_season_start),
    casa_pabellon="Santiago Bernabéu, Madrid",
)

CONFIG_UEFA = ConfigUEFA(
    team_id="50051",
    team_name="Real Madrid",
    uid_prefix=_uid_prefix,
    uid_dominio="madrid-calendario",
    temporada=_season,
    competiciones=(
        CompeticionUEFA(
            codigo="champions",
            nombre="Champions League {temporada}",
            competition_id="1",
            season_year=str(_season_start + 1),
            slug="uefachampionsleague",
        ),
    ),
)

# Fallback cuando Transfermarkt bloquea (p. ej. CI): API pública sin clave.
CONFIG_ESPN = ConfigESPN(
    team_id="86",
    team_name="Real Madrid",
    temporada=_season,
    uid_prefix=_uid_prefix,
    uid_dominio="madrid-calendario",
    ligas=(
        LigaESPN(codigo="liga", slug="esp.1", nombre="LaLiga {temporada}"),
        LigaESPN(
            codigo="copa", slug="esp.copa_del_rey", nombre="Copa del Rey {temporada}"
        ),
    ),
    casa_estadio="Santiago Bernabéu, Madrid",
)

# Fuente oficial primaria (API pública de LALIGA; TM y ESPN quedan de fallback).
CONFIG_LALIGA = ConfigLaLiga(
    team_slug="real-madrid",
    team_name="Real Madrid",
    temporada=_season,
    uid_prefix=_uid_prefix,
    uid_dominio="madrid-calendario",
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
    casa_estadio="Santiago Bernabéu, Madrid",
)
