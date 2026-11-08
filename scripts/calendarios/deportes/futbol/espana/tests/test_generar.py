"""Tests de la generación de eventos del calendario de la Selección Española."""

from __future__ import annotations

import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from scripts.calendarios.deportes.futbol.espana import generar
from scripts.calendarios.deportes.futbol.espana.config import CONFIG


class TestEventos(unittest.TestCase):
    def _partido(self, **extra) -> dict:
        p = {
            "uid": "espana-2026-4844808@espana-calendario",
            "acta": "https://www.transfermarkt.com/x/1",
            "competicion": "amistoso",
            "competicion_nombre": "Amistoso internacional",
            "ronda": "",
            "casa": True,
            "rival": "Serbia",
            "estado": "pendiente",
            "inicio_madrid": "2026-11-12T20:45:00",
        }
        p.update(extra)
        return p

    def test_evento_basico(self):
        eventos = generar.a_eventos([self._partido()])
        self.assertEqual(len(eventos), 1)
        evento = eventos[0]
        self.assertEqual(evento.uid, "espana-2026-4844808@espana-calendario")
        self.assertEqual(evento.resumen, "⚽ España - Serbia (Amistoso)")
        self.assertEqual(evento.lugar, "")
        self.assertEqual(evento.estado, "CONFIRMED")
        self.assertEqual(evento.inicio.hour, 20)
        self.assertIn("Amistoso internacional", evento.descripcion)
        self.assertNotIn("· Amistoso", evento.descripcion)
        self.assertIn("Acta:", evento.descripcion)

    def test_empate_y_traduccion(self):
        p = self._partido(
            rival="Egypt",
            estado="jugado",
            resultado_local=0,
            resultado_visitante=0,
            resultado_equipo=0,
            resultado_rival=0,
            victoria=False,
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(evento.resumen, "⚽ España - Egipto (Amistoso: 0-0 🤝)")
        self.assertIn("Resultado: España 0-0 empate 🤝", evento.descripcion)

    def test_mundial_jugado(self):
        p = self._partido(
            competicion="mundial",
            competicion_nombre="Copa Mundial 2026",
            ronda="Round of 32",
            rival="Austria",
            estado="jugado",
            resultado_local=3,
            resultado_visitante=0,
            resultado_equipo=3,
            resultado_rival=0,
            victoria=True,
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(
            evento.resumen, "⚽ España - Austria (Mundial · Dieciseisavos: 3-0 ✅)"
        )
        self.assertIn("Resultado: España 3-0 victoria ✅", evento.descripcion)

    def test_nations_fuera(self):
        p = self._partido(
            competicion="nations",
            competicion_nombre="UEFA Nations League 2026",
            ronda="Group 3",
            casa=False,
            rival="Czechia",
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(
            evento.resumen, "⚽ Chequia - España (Nations · Grupo 3)"
        )
        self.assertIn("España fuera vs Chequia", evento.descripcion)

    def test_finalissima(self):
        p = self._partido(
            competicion="finalissima",
            competicion_nombre="Finalissima",
            ronda="Final",
            rival="Argentina",
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(evento.resumen, "⚽ España - Argentina (Finalissima)")

    def test_euro_y_clasificacion(self):
        p = self._partido(
            competicion="euro",
            competicion_nombre="Eurocopa 2028",
            ronda="Group A",
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(evento.resumen, "⚽ España - Serbia (Euro · Grupo A)")

        p = self._partido(
            competicion="clasificacion",
            competicion_nombre="Clasificación 2028",
            ronda="Group A",
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(
            evento.resumen, "⚽ España - Serbia (Clasificación · Grupo A)"
        )

    def test_aplazado_se_omite(self):
        p = self._partido(estado="aplazado")
        self.assertEqual(generar.a_eventos([p]), [])

    def test_sin_fecha_se_omite(self):
        p = self._partido()
        p.pop("inicio_madrid")
        self.assertEqual(generar.a_eventos([p]), [])

    def test_sin_acta_se_omite(self):
        p = self._partido()
        p.pop("acta")
        self.assertEqual(generar.a_eventos([p]), [])


class TestCompatibilidad(unittest.TestCase):
    def test_carga_previo_ilegible(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partidos.json"
            path.write_text("{no es json", encoding="utf-8")
            self.assertEqual(generar._cargar_previo(path), [])


class TestConfig(unittest.TestCase):
    def test_config(self):
        self.assertIs(generar.CONFIG, CONFIG)
        self.assertEqual(CONFIG.team_id, "3375")
        anio = datetime.now().year
        self.assertEqual(CONFIG.season_id, str(anio))
        self.assertEqual(CONFIG.uid_prefix, f"espana-{anio}")
        codigos = {c.codigo for c in CONFIG.competiciones}
        self.assertIn("mundial", codigos)
        self.assertIn("nations", codigos)
        self.assertIn("finalissima", codigos)


if __name__ == "__main__":
    unittest.main()
