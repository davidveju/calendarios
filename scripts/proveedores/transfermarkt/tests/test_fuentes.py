"""Tests sin red del proveedor Transfermarkt."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.proveedores.transfermarkt import fuentes
from scripts.proveedores.transfermarkt.config import ConfigTM

CONFIG = ConfigTM(
    team_name="Getafe",
    slug="getafe-cf",
    team_id="3709",
    temporada="26/27",
    uid_prefix="getafe-2627",
    uid_dominio="getafe-calendario",
    season_id="2026",
    casa_pabellon="Coliseum, Getafe",
)

FIXTURES = Path(__file__).parent / "fixtures"


class TestFuentes(unittest.TestCase):
    def _leer(self, nombre: str) -> str:
        return (FIXTURES / nombre).read_text(encoding="utf-8")

    def test_alaves(self):
        row = self._leer("alaves.html")
        p = fuentes.parse_partido(row, CONFIG)
        self.assertIsNotNone(p)
        self.assertEqual(p["rival"], "Alavés")
        self.assertFalse(p["casa"])
        self.assertEqual(p["competicion"], "liga")
        self.assertEqual(p["inicio_madrid"], "2026-08-15T19:30")
        self.assertEqual(p["estado"], "jugado")
        self.assertEqual(p["resultado_equipo"], 0)
        self.assertEqual(p["resultado_rival"], 3)
        self.assertFalse(p["victoria"])

    def test_iberia(self):
        row = self._leer("iberia.html")
        p = fuentes.parse_partido(row, CONFIG)
        self.assertIsNotNone(p)
        self.assertEqual(p["rival"], "Iberia Tbilisi")
        self.assertFalse(p["casa"])
        self.assertEqual(p["competicion"], "conference")
        self.assertEqual(p["inicio_madrid"], "2026-11-26T18:45")
        self.assertEqual(p["estado"], "pendiente")

    def test_extraer_partidos(self):
        html = "<table><tbody>" + self._leer("alaves.html") + self._leer("iberia.html") + "</tbody></table>"
        partidos = fuentes.extraer_partidos(html, CONFIG)
        self.assertEqual(len(partidos), 2)
        self.assertEqual(len({p["uid"] for p in partidos}), 2)

    def test_parse_invalid(self):
        self.assertIsNone(fuentes.parse_partido("nonsense", CONFIG))
        self.assertEqual(fuentes.extraer_partidos("nonsense", CONFIG), [])


if __name__ == "__main__":
    unittest.main()
