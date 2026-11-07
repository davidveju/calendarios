"""Tests de la generación de eventos del calendario del Real Madrid CF."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.calendarios.deportes.futbol.madrid import generar
from scripts.calendarios.deportes.futbol.madrid.config import CONFIG


class TestEventos(unittest.TestCase):
    def _partido(self, **extra) -> dict:
        p = {
            "uid": "madrid-2627-123@madrid-calendario",
            "acta": "https://www.transfermarkt.com/x/1",
            "competicion": "liga",
            "competicion_nombre": "LaLiga 26/27",
            "ronda": "12",
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
        self.assertEqual(evento.uid, "madrid-2627-123@madrid-calendario")
        self.assertEqual(evento.resumen, "⚽ Real Madrid - Rival (J12)")
        self.assertEqual(evento.lugar, CONFIG.casa_pabellon)
        self.assertEqual(evento.estado, "CONFIRMED")
        self.assertEqual(evento.inicio.hour, 12)
        self.assertIn("LaLiga 26/27 · J12", evento.descripcion)
        self.assertIn("Acta:", evento.descripcion)

    def test_jugado(self):
        p = self._partido(
            estado="jugado",
            resultado_local=2,
            resultado_visitante=1,
            resultado_equipo=2,
            resultado_rival=1,
            victoria=True,
        )
        evento = generar.a_eventos([p])[0]
        self.assertIn("J12: 2-1 ✅", evento.resumen)
        self.assertIn("Resultado: Real Madrid 2-1 victoria ✅", evento.descripcion)

    def test_derrota(self):
        p = self._partido(
            casa=False,
            estado="jugado",
            resultado_local=1,
            resultado_visitante=0,
            resultado_equipo=0,
            resultado_rival=1,
            victoria=False,
            rival="Barcelona",
        )
        evento = generar.a_eventos([p])[0]
        self.assertIn("❌", evento.resumen)

    def test_sin_fecha_se_omite(self):
        p = self._partido()
        p.pop("inicio_madrid")
        self.assertEqual(generar.a_eventos([p]), [])

    def test_sin_acta_se_omite(self):
        p = self._partido()
        p.pop("acta")
        self.assertEqual(generar.a_eventos([p]), [])

    def test_conference(self):
        p = self._partido(
            uid="madrid-2627-2@madrid-calendario",
            acta="https://www.transfermarkt.com/x/2",
            competicion="conference",
            competicion_nombre="Conference League 26/27",
            ronda="Group Stage",
        )
        evento = generar.a_eventos([p])[0]
        self.assertEqual(
            evento.resumen, "⚽ Real Madrid - Rival (Conf Group Stage)"
        )


class TestCompatibilidad(unittest.TestCase):
    def test_carga_previo_ilegible(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "partidos.json"
            path.write_text("{no es json", encoding="utf-8")
            self.assertEqual(generar._cargar_previo(path), [])


class TestConfig(unittest.TestCase):
    def test_config(self):
        self.assertIs(generar.CONFIG, CONFIG)
        self.assertEqual(CONFIG.team_id, "418")
        self.assertEqual(CONFIG.uid_prefix, "madrid-2627")


if __name__ == "__main__":
    unittest.main()
