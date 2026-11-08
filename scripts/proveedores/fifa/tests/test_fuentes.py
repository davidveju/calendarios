"""Tests sin red del proveedor FIFA."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.proveedores.fifa import fuentes
from scripts.proveedores.fifa.config import CompeticionFIFA, ConfigFIFA

FIXTURE = Path(__file__).parent / "fixtures" / "amistosos.json"

CONFIG = ConfigFIFA(
    team_id="43969",
    team_name="Spain",
    uid_prefix="espana-2026",
    uid_dominio="espana-calendario",
    temporada="2026",
)

AMISTOSO = CompeticionFIFA(
    codigo="amistoso",
    nombre="Amistoso internacional",
    competition_id="cesdwwnxbc5fmajgroc0hqzy2",
    season_id="dezv8l0fzgcxtejl0dwmy1gyc",
    usar_fase=False,
)


class TestFIFA(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.partidos = fuentes.parse_partidos(
            FIXTURE.read_text(encoding="utf-8"), CONFIG, AMISTOSO
        )

    def test_filtra_por_equipo(self):
        self.assertEqual(len(self.partidos), 2)

    def test_partido_pendiente(self):
        p = next(x for x in self.partidos if x["estado"] == "pendiente")
        self.assertEqual(p["uid"], "espana-2026-fifa-400021001@espana-calendario")
        self.assertEqual(p["rival"], "Irak")
        self.assertTrue(p["casa"])
        self.assertEqual(p["inicio_madrid"], "2026-06-04T21:00")
        self.assertFalse(p["fecha_provisional"])
        self.assertEqual(p["ronda"], "")
        self.assertIn("/match-centre/match/", p["acta"])
        self.assertEqual(p["fuente"], "fifa")

    def test_partido_jugado(self):
        p = next(x for x in self.partidos if x["estado"] == "jugado")
        self.assertEqual(p["rival"], "Serbia")
        self.assertEqual(p["resultado_local"], 2)
        self.assertEqual(p["resultado_visitante"], 0)
        self.assertTrue(p["victoria"])

    def test_payload_invalido(self):
        self.assertEqual(fuentes.parse_partidos("{no", CONFIG, AMISTOSO), [])


if __name__ == "__main__":
    unittest.main()
