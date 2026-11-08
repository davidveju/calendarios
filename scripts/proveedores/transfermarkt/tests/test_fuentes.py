"""Tests sin red del proveedor Transfermarkt."""

from __future__ import annotations

import unittest
from pathlib import Path

from scripts.proveedores.transfermarkt import fuentes
from scripts.proveedores.transfermarkt.config import CompeticionTM, ConfigTM

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

CONFIG_ESPANA = ConfigTM(
    team_name="Spain",
    slug="spanien",
    team_id="3375",
    temporada="2026",
    uid_prefix="espana-2026",
    uid_dominio="espana-calendario",
    season_id="2026",
    competiciones=(
        CompeticionTM("amistoso", "Amistoso internacional", ("international friendlies",)),
        CompeticionTM("mundial", "Copa Mundial {temporada}", ("world cup",)),
        CompeticionTM("nations", "UEFA Nations League {temporada}", ("nations league",)),
        CompeticionTM(
            "finalissima",
            "Finalissima",
            ("conmebol-uefa cup of champions",),
        ),
    ),
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


class TestSeleccion(unittest.TestCase):
    def _leer(self, nombre: str) -> str:
        return (FIXTURES / nombre).read_text(encoding="utf-8")

    def test_amistoso_sin_columna_jornada(self):
        p = fuentes.parse_partido(
            self._leer("espana_amistoso.html"), CONFIG_ESPANA, "amistoso"
        )
        self.assertIsNotNone(p)
        self.assertEqual(p["rival"], "Serbia")
        self.assertTrue(p["casa"])
        self.assertEqual(p["competicion"], "amistoso")
        self.assertEqual(p["competicion_nombre"], "Amistoso internacional")
        self.assertEqual(p["inicio_madrid"], "2026-03-27T21:00")
        self.assertEqual(p["estado"], "jugado")
        self.assertEqual(p["resultado_equipo"], 3)
        self.assertEqual(p["resultado_rival"], 0)
        self.assertTrue(p["victoria"])

    def test_mundial(self):
        p = fuentes.parse_partido(
            self._leer("espana_mundial.html"), CONFIG_ESPANA, "mundial"
        )
        self.assertIsNotNone(p)
        self.assertEqual(p["ronda"], "Round of 32")
        self.assertEqual(p["competicion_nombre"], "Copa Mundial 2026")
        self.assertEqual(p["rival"], "Austria")

    def test_nations_pendiente(self):
        p = fuentes.parse_partido(
            self._leer("espana_nations.html"), CONFIG_ESPANA, "nations"
        )
        self.assertIsNotNone(p)
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "Czechia")
        self.assertEqual(p["estado"], "pendiente")
        self.assertEqual(p["inicio_madrid"], "2026-11-12T20:45")

    def test_aplazado(self):
        p = fuentes.parse_partido(
            self._leer("espana_aplazado.html"), CONFIG_ESPANA, "finalissima"
        )
        self.assertIsNotNone(p)
        self.assertEqual(p["estado"], "aplazado")
        self.assertNotIn("resultado_equipo", p)

    def test_extraer_competiciones_por_cabecera(self):
        html = (
            "<h2>International Friendlies</h2><table><tbody>"
            + self._leer("espana_amistoso.html")
            + "</tbody></table>"
            + "<h2>World Cup</h2><table><tbody>"
            + self._leer("espana_mundial.html")
            + "</tbody></table>"
        )
        partidos = fuentes.extraer_partidos(html, CONFIG_ESPANA)
        self.assertEqual(
            [p["competicion"] for p in partidos], ["amistoso", "mundial"]
        )


class TestRondas(unittest.TestCase):
    def test_traducciones(self):
        casos = {
            "Group Stage": "Fase de grupos",
            "Group H": "Grupo H",
            "Group 3": "Grupo 3",
            "Qualifying Round 1st leg": "Ronda previa, ida",
            "Qualifying Round 2nd leg": "Ronda previa, vuelta",
            "Round of 16 1st leg": "Octavos, ida",
            "First Round": "Primera ronda",
            "Round of 32": "Dieciseisavos",
            "Round of 16": "Octavos",
            "Quarter-Finals": "Cuartos",
            "Semi-Finals": "Semifinales",
            "Final": "Final",
            "League Phase": "Fase de liga",
            "Play-off Round": "Ronda de play-off",
            "": "",
            "Ronda inventada": "Ronda inventada",
        }
        for original, esperado in casos.items():
            with self.subTest(original=original):
                self.assertEqual(fuentes.traducir_ronda(original), esperado)


if __name__ == "__main__":
    unittest.main()
