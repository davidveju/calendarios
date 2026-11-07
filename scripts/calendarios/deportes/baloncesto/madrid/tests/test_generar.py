"""Tests de la generación de eventos del calendario del Real Madrid de baloncesto."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.calendarios.deportes.baloncesto.madrid import generar
from scripts.calendarios.deportes.baloncesto.madrid.config import CONFIG


class TestEventos(unittest.TestCase):
    def _partido(self, **extra) -> dict:
        p = {
            "uid": "madrid-b-2627-2026-09-27-unicaja@madridbaloncesto-calendario",
            "acta": "https://acb.com/x",
            "competicion": "acb",
            "competicion_nombre": "Liga Endesa 26/27",
            "casa": True,
            "rival": "Unicaja",
            "estado": "pendiente",
            "inicio_madrid": "2026-09-27T19:00:00",
        }
        p.update(extra)
        return p

    def test_evento_basico(self):
        eventos = generar.a_eventos([self._partido()])
        self.assertEqual(len(eventos), 1)
        evento = eventos[0]
        self.assertEqual(evento.resumen, "🏀 Real Madrid - Unicaja (Liga Endesa)")
        self.assertEqual(evento.estado, "CONFIRMED")
        self.assertEqual(evento.lugar, "Movistar Arena, Madrid")

    def test_sin_acta_se_omite(self):
        p = self._partido()
        p.pop("acta")
        self.assertEqual(generar.a_eventos([p]), [])


class TestConfig(unittest.TestCase):
    def test_config(self):
        self.assertIs(generar.CONFIG, CONFIG)
        self.assertEqual(CONFIG.uid_dominio, "madridbaloncesto-calendario")


if __name__ == "__main__":
    unittest.main()
