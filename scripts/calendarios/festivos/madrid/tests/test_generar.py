"""Tests de la generación de eventos de festivos de Madrid."""

from __future__ import annotations

import unittest

from scripts.calendarios.festivos.madrid import generar
from scripts.calendarios.festivos.madrid.config import CONFIG


class TestEventos(unittest.TestCase):
    def _partido(self, **extra) -> dict:
        p = {
            "uid": "madrid-festivos-2026-12-08@madridfestivos-calendario",
            "acta": "https://openholidaysapi.org",
            "competicion": "festivo",
            "competicion_nombre": CONFIG.nombre_calendario,
            "casa": True,
            "rival": "Inmaculada Concepción",
            "estado": "pendiente",
            "inicio_madrid": "2026-12-08T00:00:00",
            "fin_madrid": "2026-12-08T23:59:00",
        }
        p.update(extra)
        return p

    def test_evento_basico(self):
        eventos = generar.a_eventos([self._partido()])
        self.assertEqual(len(eventos), 1)
        evento = eventos[0]
        self.assertEqual(evento.resumen, "🎉 Inmaculada Concepción")
        self.assertEqual(evento.estado, "CONFIRMED")
        self.assertEqual(evento.transparencia, "OPAQUE")

    def test_sin_acta_se_omite(self):
        p = self._partido()
        p.pop("acta")
        self.assertEqual(generar.a_eventos([p]), [])


class TestConfig(unittest.TestCase):
    def test_config(self):
        self.assertIs(generar.CONFIG, CONFIG)
        self.assertEqual(CONFIG.subdivision_code, "ES-MD-MD")


if __name__ == "__main__":
    unittest.main()
