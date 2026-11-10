"""Tests sin red del proveedor ESPN (fixtures recortadas de la API real)."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.proveedores.espn import fuentes
from scripts.proveedores.espn.config import ConfigESPN, LigaESPN

FIXTURES = Path(__file__).parent / "fixtures"

CONFIG = ConfigESPN(
    team_id="2922",
    team_name="Getafe",
    temporada="26/27",
    uid_prefix="getafe-2627",
    uid_dominio="getafe-calendario",
    ligas=(LigaESPN(codigo="liga", slug="esp.1", nombre="LaLiga {temporada}"),),
    casa_estadio="Coliseum, Getafe",
)
LIGA = CONFIG.ligas[0]


def _carga(nombre: str) -> dict:
    return json.loads((FIXTURES / nombre).read_text(encoding="utf-8"))


class TestParse(unittest.TestCase):
    def test_post_fuera(self):
        p = fuentes.parse_evento(_carga("liga_post.json"), CONFIG, LIGA)
        self.assertEqual(p["uid"], "getafe-2627-espn401882807@getafe-calendario")
        self.assertEqual(p["competicion"], "liga")
        self.assertEqual(p["competicion_nombre"], "LaLiga 26/27")
        self.assertEqual(p["estado"], "jugado")
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "Villarreal")
        self.assertEqual(p["inicio_madrid"], "2026-11-08T18:30")
        self.assertFalse(p["fecha_provisional"])
        self.assertEqual(p["resultado_local"], 2)
        self.assertEqual(p["resultado_visitante"], 0)
        self.assertEqual(p["resultado_equipo"], 0)
        self.assertEqual(p["resultado_rival"], 2)
        self.assertFalse(p["victoria"])
        self.assertEqual(p["fuente"], "espn")
        self.assertIn("gameId/401882807", p["acta"])
        self.assertEqual(
            p["sede"], {"pabellon": "Estadio de la Cerámica", "ciudad": "Villarreal"}
        )

    def test_pre_casa(self):
        p = fuentes.parse_evento(_carga("liga_pre.json"), CONFIG, LIGA)
        self.assertEqual(p["estado"], "pendiente")
        self.assertTrue(p["casa"])
        self.assertEqual(p["rival"], "Atlético Madrid")
        self.assertEqual(p["inicio_madrid"], "2026-11-22T21:00")
        self.assertFalse(p["fecha_provisional"])
        self.assertNotIn("resultado_local", p)
        self.assertEqual(p["sede"], {"pabellon": "Estadio Coliseum", "ciudad": "Getafe"})

    def test_hora_sin_confirmar(self):
        evento = _carga("liga_pre.json")
        evento["competitions"][0]["timeValid"] = False
        p = fuentes.parse_evento(evento, CONFIG, LIGA)
        self.assertTrue(p["fecha_provisional"])
        self.assertEqual(p["inicio_madrid"], "2026-11-22T12:00")

    def test_otro_equipo_se_ignora(self):
        evento = _carga("liga_post.json")
        for c in evento["competitions"][0]["competitors"]:
            c["team"]["id"] = "9999"
        self.assertIsNone(fuentes.parse_evento(evento, CONFIG, LIGA))

    def test_liga_vacia_no_falla_si_hay_eventos(self):
        """Equipo aún sin partidos (p. ej. copa sin empezar) -> []."""
        from unittest import mock

        eventos = [_carga("liga_post.json")]
        for c in eventos[0]["competitions"][0]["competitors"]:
            c["team"]["id"] = "9999"
        payload = json.dumps({"events": eventos})
        with mock.patch(
            "scripts.comun.http.fetch", return_value=payload
        ):
            liga = LIGA
            self.assertEqual(fuentes.fetch_liga(CONFIG, liga), [])

    def test_respuesta_vacia_falla(self):
        from unittest import mock

        with mock.patch(
            "scripts.comun.http.fetch", return_value=json.dumps({"events": []})
        ):
            with self.assertRaises(ValueError):
                fuentes.fetch_liga(CONFIG, LIGA)

    def test_copa(self):
        liga_copa = LigaESPN(
            codigo="copa", slug="esp.copa_del_rey", nombre="Copa del Rey {temporada}"
        )
        p = fuentes.parse_evento(_carga("copa_post.json"), CONFIG, liga_copa)
        self.assertEqual(p["competicion"], "copa")
        self.assertEqual(p["estado"], "jugado")
        self.assertFalse(p["casa"])
        self.assertEqual(p["rival"], "UB Lebrijana")
        self.assertEqual(p["resultado_local"], 2)
        self.assertEqual(p["resultado_visitante"], 3)
        self.assertTrue(p["victoria"])


class TestVentana(unittest.TestCase):
    def test_temporada_anios(self):
        self.assertEqual(fuentes._temporada_anios("26/27"), (2026, 2027))

    def test_filtra_temporada_anterior(self):
        evento = _carga("liga_post.json")
        evento["date"] = "2026-01-09T20:00Z"
        evento["competitions"][0]["date"] = "2026-01-09T20:00Z"
        p = fuentes.parse_evento(evento, CONFIG, LIGA)
        # Parsear sí funciona; el filtro por ventana vive en fetch_liga.
        self.assertEqual(p["inicio_madrid"], "2026-01-09T21:00")
        inicio, fin = fuentes._ventana("26/27")
        self.assertFalse(inicio <= p["inicio_madrid"][:10] < fin)


if __name__ == "__main__":
    unittest.main()
