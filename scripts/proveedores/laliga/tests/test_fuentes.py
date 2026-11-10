"""Tests sin red del proveedor LALIGA (fixtures recortadas de APIM)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.proveedores.laliga import fuentes
from scripts.proveedores.laliga.config import ConfigLaLiga, LigaOficial

FIXTURES = Path(__file__).parent / "fixtures"

CONFIG = ConfigLaLiga(
    team_slug="getafe-cf",
    team_name="Getafe",
    temporada="26/27",
    uid_prefix="getafe-2627",
    uid_dominio="getafe-calendario",
    ligas=(
        LigaOficial(
            codigo="liga",
            base="laliga-easports",
            nombre="LaLiga {temporada}",
            acta="https://www.laliga.com/laliga-easports/resultados",
        ),
    ),
    casa_estadio="Coliseum, Getafe",
)
LIGA = CONFIG.ligas[0]


def _carga(nombre: str) -> dict:
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


class TestParse(unittest.TestCase):
    def test_post_fuera(self):
        p = fuentes.parse_partido(_carga("liga_post.json"), CONFIG, LIGA)
        self.assertEqual(p["uid"], "getafe-2627-102368@getafe-calendario")
        self.assertEqual(p["competicion"], "liga")
        self.assertEqual(p["competicion_nombre"], "LaLiga 26/27")
        self.assertEqual(p["estado"], "jugado")
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "Villarreal")
        self.assertEqual(p["inicio_madrid"], "2026-11-08T18:30")
        self.assertFalse(p["fecha_provisional"])
        self.assertEqual(p["ronda"], "12")
        self.assertEqual(p["resultado_local"], 2)
        self.assertEqual(p["resultado_visitante"], 0)
        self.assertEqual(p["resultado_equipo"], 0)
        self.assertEqual(p["resultado_rival"], 2)
        self.assertFalse(p["victoria"])
        self.assertEqual(p["fuente"], "laliga")
        self.assertEqual(
            p["sede"], {"pabellon": "Estadio de la Cerámica", "ciudad": "Vila-real"}
        )

    def test_pre_fuera_con_hora(self):
        p = fuentes.parse_partido(_carga("liga_pre.json"), CONFIG, LIGA)
        self.assertEqual(p["estado"], "pendiente")
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "RCD Espanyol de Barcelona")
        self.assertEqual(p["inicio_madrid"], "2026-11-30T21:00")
        self.assertFalse(p["fecha_provisional"])
        self.assertEqual(p["ronda"], "14")
        self.assertNotIn("resultado_local", p)

    def test_hora_sin_confirmar(self):
        match = _carga("liga_pre.json")
        match["date"] = "2026-11-22T00:00:00+00:00"
        match["time"] = "2026-11-22T00:00:00+00:00"
        p = fuentes.parse_partido(match, CONFIG, LIGA)
        self.assertTrue(p["fecha_provisional"])
        self.assertEqual(p["inicio_madrid"], "2026-11-22T12:00")

    def test_otro_equipo_se_ignora(self):
        match = _carga("liga_post.json")
        match["home_team"]["slug"] = "otro"
        match["away_team"]["slug"] = "otro-mas"
        self.assertIsNone(fuentes.parse_partido(match, CONFIG, LIGA))

    def test_copa(self):
        liga_copa = LigaOficial(
            codigo="copa",
            base="copa-del-rey",
            nombre="Copa del Rey {temporada}",
            acta="https://www.laliga.com/otras-competiciones/copa-del-rey",
        )
        p = fuentes.parse_partido(_carga("copa_post.json"), CONFIG, liga_copa)
        self.assertEqual(p["competicion"], "copa")
        self.assertEqual(p["estado"], "jugado")
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "Lebrijana")
        self.assertEqual(p["ronda"], "1º eliminatoria")
        self.assertEqual(p["resultado_local"], 2)
        self.assertEqual(p["resultado_visitante"], 3)
        self.assertTrue(p["victoria"])
        self.assertEqual(
            p["sede"], {"pabellon": "Municipal de Lebrija", "ciudad": "Lebrija"}
        )


class TestClave(unittest.TestCase):
    def test_extraer_clave(self):
        html = (FIXTURES / "clave.html").read_text(encoding="utf-8")
        self.assertEqual(
            fuentes.extraer_clave(html), "c13c3a8e2f6b46da9c5c425cf61fab3e"
        )

    def test_sin_clave_falla(self):
        with self.assertRaises(ValueError):
            fuentes.extraer_clave("<html></html>")

    def test_temporada_anio(self):
        self.assertEqual(fuentes._temporada_anio("26/27"), "2026")


if __name__ == "__main__":
    unittest.main()
