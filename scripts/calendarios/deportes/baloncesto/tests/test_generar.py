"""Tests de la generación de eventos del calendario de baloncesto."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.calendarios.deportes.baloncesto import generar
from scripts.calendarios.deportes.baloncesto.config import CONFIG


class TestEventos(unittest.TestCase):
    def _partido(self, **extra) -> dict:
        p = {
            "uid": "estu-2627-j01@estudiantes-calendario",
            "acta": "https://example.com/1",
            "competicion": "liga",
            "competicion_nombre": "Primera FEB 26/27",
            "jornada": 1,
            "fecha_jornada": "01/01/2027",
            "casa": True,
            "rival": "Rival",
            "estado": "pendiente",
            "inicio_madrid": "2027-01-01T12:00:00",
        }
        p.update(extra)
        return p

    def test_evento_basico(self):
        eventos = generar.a_eventos([self._partido()])
        self.assertEqual(len(eventos), 1)
        evento = eventos[0]
        self.assertEqual(evento.uid, "estu-2627-j01@estudiantes-calendario")
        self.assertEqual(evento.resumen, "🏀 Estu - Rival (J1)")
        self.assertEqual(evento.lugar, "Movistar Arena, Madrid")
        self.assertEqual(evento.estado, "CONFIRMED")
        self.assertEqual(evento.inicio.hour, 12)
        self.assertIn("Inicio: 01/01/2027 12:00 (Madrid)", evento.descripcion)
        self.assertIn("Acta FEB:", evento.descripcion)

    def test_provisional(self):
        eventos = generar.a_eventos([self._partido(fecha_provisional=True)])
        self.assertEqual(eventos[0].estado, "TENTATIVE")

    def test_jugado(self):
        p = self._partido(
            estado="jugado",
            resultado_local=80,
            resultado_visitante=70,
            resultado_equipo=80,
            resultado_rival=70,
            victoria=True,
        )
        evento = generar.a_eventos([p])[0]
        self.assertIn("J1: 80-70 ✅", evento.resumen)
        self.assertIn("Resultado: Estu 80-70 victoria ✅", evento.descripcion)

    def test_sin_fecha_se_omite(self):
        p = self._partido()
        p.pop("inicio_madrid")
        p["fecha_jornada"] = "Por determinar"
        self.assertEqual(generar.a_eventos([p]), [])

    def test_sin_acta_se_omite(self):
        p = self._partido()
        p.pop("acta")
        self.assertEqual(generar.a_eventos([p]), [])

    def test_copa_usa_emoji_y_ronda(self):
        p = self._partido(
            uid="estu-2627-copa-j02@estudiantes-calendario",
            competicion="copa",
            competicion_nombre="Copa España 26/27",
            ronda="1/8",
            casa=False,
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(evento.resumen, "🏆 Rival - Estu (Copa 1/8)")
        self.assertIn("Copa España 26/27 · Copa 1/8", evento.descripcion)


class TestCompatibilidad(unittest.TestCase):
    def test_carga_previo_normaliza_resultado_estu(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partidos.json"
            path.write_text(
                json.dumps([{"uid": "x", "resultado_estu": 80}]),
                encoding="utf-8",
            )
            datos = generar._cargar_previo(path)
        self.assertEqual(datos[0]["resultado_equipo"], 80)
        self.assertNotIn("resultado_estu", datos[0])

    def test_carga_previo_ilegible_no_tumba_la_generacion(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partidos.json"
            path.write_text("{no es json", encoding="utf-8")
            self.assertEqual(generar._cargar_previo(path), [])


class TestConfig(unittest.TestCase):
    def test_el_generador_usa_la_configuracion_del_calendario(self):
        self.assertIs(generar.CONFIG, CONFIG)
        self.assertEqual(CONFIG.equipo_id, "1010493")
        self.assertEqual(CONFIG.uid_prefix, "estu-2627")


if __name__ == "__main__":
    unittest.main()
