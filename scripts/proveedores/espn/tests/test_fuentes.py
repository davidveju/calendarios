"""Tests sin red del proveedor ESPN."""

from __future__ import annotations

import unittest

from scripts.proveedores.espn import fuentes
from scripts.proveedores.espn.config import ConfigESPN

CONFIG = ConfigESPN(
    team_id="2922",
    team_name="Getafe",
    equipo_corto="Getafe",
    temporada="26/27",
    uid_prefix="getafe-2627",
    uid_dominio="getafe-calendario",
    liga_slug="esp.1",
    liga_nombre="LaLiga",
)

# Mini payload reutilizando las claves que consume el parser.
PAGINA = """{
  "leagues": [{"calendar": ["2026-11-08T08:00Z", "2026-11-21T08:00Z"]}],
  "events": [
    {
      "id": "401882807",
      "date": "2026-11-08T17:30Z",
      "name": "Getafe at Villarreal",
      "status": {"type": {"completed": false, "name": "STATUS_SCHEDULED"}},
      "links": [{"rel": ["summary", "desktop", "event"],
                 "href": "https://www.espn.com/soccer/match/_/gameId/401882807/getafe-villarreal"}],
      "competitions": [{
        "date": "2026-11-08T17:30Z",
        "status": {"type": {"completed": false, "name": "STATUS_SCHEDULED"}},
        "venue": {"fullName": "Estadio de la Cerámica",
                  "address": {"city": "Villarreal", "country": "Spain"}},
        "competitors": [
          {"id": "102", "homeAway": "home", "team": {"displayName": "Villarreal"}, "score": "0"},
          {"id": "2922", "homeAway": "away", "team": {"displayName": "Getafe"}, "score": "0"}
        ]
      }]
    },
    {
      "id": "401882899",
      "date": "2026-11-21T15:00Z",
      "name": "Getafe vs Alavés",
      "status": {"type": {"completed": true, "name": "STATUS_FULL_TIME"}},
      "links": [{"rel": ["summary", "desktop", "event"],
                 "href": "https://www.espn.com/soccer/match/_/gameId/401882899/getafe-alaves"}],
      "competitions": [{
        "date": "2026-11-21T15:00Z",
        "status": {"type": {"completed": true, "name": "STATUS_FULL_TIME"}},
        "venue": {"fullName": "Coliseum", "address": {"city": "Getafe", "country": "Spain"}},
        "competitors": [
          {"id": "2922", "homeAway": "home", "team": {"displayName": "Getafe"}, "score": "2"},
          {"id": "200", "homeAway": "away", "team": {"displayName": "Alavés"}, "score": "1"}
        ]
      }]
    }
  ]
}"""
PAGINA_VACIA = '{"leagues": [{"calendar": []}], "events": []}'


class TestESPN(unittest.TestCase):
    def test_extrae_partidos_del_equipo(self):
        partidos = fuentes.extraer_eventos(PAGINA, CONFIG)
        self.assertEqual(len(partidos), 2)
        uids = {p["uid"] for p in partidos}
        self.assertIn("getafe-2627-e401882807@getafe-calendario", uids)
        self.assertIn("getafe-2627-e401882899@getafe-calendario", uids)

    def test_partido_pendiente(self):
        partidos = fuentes.extraer_eventos(PAGINA, CONFIG)
        pend = next(p for p in partidos if p["uid"].endswith("e401882807@getafe-calendario"))
        self.assertEqual(pend["estado"], "pendiente")
        self.assertFalse(pend["casa"])
        self.assertEqual(pend["rival"], "Villarreal")
        self.assertEqual(pend["acta"], "https://www.espn.com/soccer/match/_/gameId/401882807/getafe-villarreal")
        self.assertEqual(pend["sede"]["pabellon"], "Estadio de la Cerámica")
        self.assertEqual(pend["inicio_madrid"], "2026-11-08T18:30")
        self.assertNotIn("resultado_equipo", pend)

    def test_partido_jugado(self):
        partidos = fuentes.extraer_eventos(PAGINA, CONFIG)
        jug = next(p for p in partidos if p["uid"].endswith("e401882899@getafe-calendario"))
        self.assertEqual(jug["estado"], "jugado")
        self.assertTrue(jug["casa"])
        self.assertTrue(jug["victoria"])
        self.assertEqual(jug["resultado_equipo"], 2)
        self.assertEqual(jug["resultado_rival"], 1)
        self.assertEqual(jug["resultado_local"], 2)
        self.assertEqual(jug["resultado_visitante"], 1)

    def test_ignora_eventos_de_otro(self):
        otro = fuentes.extraer_eventos(PAGINA_VACIA, CONFIG)
        self.assertEqual(otro, [])

    def test_fechas_calendario(self):
        fechas = fuentes.fechas_calendario(PAGINA)
        self.assertEqual(fechas, ["20261108", "20261121"])

    def test_normaliza_parseo_inválido(self):
        self.assertEqual(fuentes.extraer_eventos("{no json}", CONFIG), [])


if __name__ == "__main__":
    unittest.main()
