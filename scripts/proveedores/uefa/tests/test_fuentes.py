"""Tests sin red del proveedor UEFA."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.proveedores.uefa import fuentes
from scripts.proveedores.uefa.config import CompeticionUEFA, ConfigUEFA

FIXTURE = Path(__file__).parent / "fixtures" / "partidos.json"

CONFIG = ConfigUEFA(
    team_id="50051",
    team_name="Real Madrid",
    uid_prefix="madrid-2627",
    uid_dominio="madrid-calendario",
    temporada="26/27",
)

CHAMPIONS = CompeticionUEFA(
    codigo="champions",
    nombre="Champions League {temporada}",
    competition_id="1",
    season_year="2027",
    slug="uefachampionsleague",
)


class TestUEFA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.partidos = fuentes.parse_partidos(
            FIXTURE.read_text(encoding="utf-8"), CONFIG, CHAMPIONS
        )

    def test_filtra_por_equipo(self):
        self.assertEqual(len(self.partidos), 3)

    def test_partido_jugado(self):
        p = next(x for x in self.partidos if x["estado"] == "jugado")
        self.assertEqual(p["uid"], "madrid-2627-uefa-2047742@madrid-calendario")
        self.assertEqual(p["rival"], "Inter")
        self.assertTrue(p["casa"])
        self.assertEqual(p["inicio_madrid"], "2026-09-08T21:00")
        self.assertEqual(p["resultado_local"], 2)
        self.assertEqual(p["resultado_visitante"], 1)
        self.assertTrue(p["victoria"])
        self.assertEqual(p["ronda"], "Jornada 1")
        self.assertIn("/uefachampionsleague/match/2047742/", p["acta"])
        self.assertEqual(p["fuente"], "uefa")

    def test_partido_pendiente_fuera(self):
        p = next(x for x in self.partidos if x["estado"] == "pendiente")
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "Roma")
        self.assertNotIn("resultado_local", p)

    def test_partido_cancelado(self):
        p = next(x for x in self.partidos if x["estado"] == "aplazado")
        self.assertEqual(p["rival"], "Barcelona")

    def test_nombre_competicion(self):
        self.assertEqual(
            self.partidos[0]["competicion_nombre"], "Champions League 26/27"
        )

    def test_payload_invalido(self):
        self.assertEqual(fuentes.parse_partidos("{no", CONFIG, CHAMPIONS), [])


if __name__ == "__main__":
    unittest.main()
