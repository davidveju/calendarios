"""Configuración del calendario del Real Madrid."""

from __future__ import annotations

from datetime import datetime

from scripts.proveedores.transfermarkt.config import ConfigTM

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
