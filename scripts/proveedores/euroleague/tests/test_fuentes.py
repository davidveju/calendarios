"""Tests sin red del proveedor EuroLeague."""

from __future__ import annotations

import json
import unittest

from scripts.proveedores.euroleague import fuentes
from scripts.proveedores.euroleague.config import ConfigEuroLeague, config_actual


CONFIG = ConfigEuroLeague(
    team_code="MAD",
    team_name="Real Madrid",
    temporada="26/27",
    uid_prefix="madrid-el-2026",
    uid_dominio="madridbaloncesto-calendario",
    season_code="E2026",
    casa_pabellon="Movistar Arena, Madrid",
)

PAYLOAD = json.dumps(
    {
        "data": [
            {
                "gameCode": 123,
                "round": 4,
                "roundName": "Round 4",
                "played": True,
                "utcDate": "2026-10-08T18:30:00Z",
                "local": {
                    "club": {"code": "MAD", "name": "Real Madrid"},
                    "score": 86,
                },
                "road": {
                    "club": {"code": "PAR", "name": "Parisan"},
                    "score": 76,
                },
                "venue": {"name": "Movistar Arena", "address": "Madrid"},
            },
            {
                "gameCode": 124,
                "round": 5,
                "roundName": "Round 5",
                "played": False,
                "utcDate": "2026-10-13T18:30:00Z",
                "local": {"club": {"code": "OLM", "name": "Milan"}, "score": 0},
                "road": {"club": {"code": "MAD", "name": "Real Madrid"}, "score": 0},
                "venue": {"name": "Unipol", "address": "Milan"},
            },
        ],
        "total": 2,
    }
)


class TestEuroLeague(unittest.TestCase):
    def test_parse_games(self):
        partidos = fuentes.parse_games(PAYLOAD, CONFIG)
        self.assertEqual(len(partidos), 2)
        jugado = next(p for p in partidos if p["uid"].endswith("el123@madridbaloncesto-calendario"))
        self.assertTrue(jugado["casa"])
        self.assertEqual(jugado["rival"], "Parisan")
        self.assertEqual(jugado["resultado_equipo"], 86)
        self.assertEqual(jugado["resultado_rival"], 76)
        self.assertTrue(jugado["victoria"])
        pend = next(p for p in partidos if p["uid"].endswith("el124@madridbaloncesto-calendario"))
        self.assertFalse(pend["casa"])
        self.assertEqual(pend["estado"], "pendiente")

    def test_invalido(self):
        self.assertEqual(fuentes.parse_games("{}", CONFIG), [])
        self.assertEqual(fuentes.parse_games("{no", CONFIG), [])

    def test_config_actual(self):
        cfg = config_actual("MAD", "Real Madrid", "madridbaloncesto-calendario")
        self.assertTrue(cfg.season_code.startswith("E"))
        self.assertEqual(cfg.team_code, "MAD")

    def test_reintenta_pagina_xml(self):
        """Si la API devuelve XML transitorio, se reintenta la página."""
        import time
        from unittest import mock

        pagina = json.dumps(
            {
                "data": [
                    {
                        "gameCode": 123,
                        "round": 4,
                        "roundName": "Round 4",
                        "played": True,
                        "utcDate": "2026-10-08T18:30:00Z",
                        "local": {"club": {"code": "MAD", "name": "Real Madrid"}, "score": 86},
                        "road": {"club": {"code": "PAR", "name": "Parisan"}, "score": 76},
                        "venue": {"name": "Movistar Arena", "address": "Madrid"},
                    }
                ],
                "total": 1,
            }
        )
        with (
            mock.patch(
                "scripts.comun.http.fetch",
                side_effect=["<xml/>", pagina],
            ),
            mock.patch.object(time, "sleep"),
        ):
            partidos = fuentes.fetch_partidos(CONFIG)
        self.assertEqual(len(partidos), 1)
        self.assertEqual(partidos[0]["rival"], "Parisan")


if __name__ == "__main__":
    unittest.main()
