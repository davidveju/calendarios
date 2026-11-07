"""Tests de la generación de eventos del calendario de baloncesto."""

from __future__ import annotations

import unittest

from deportes.baloncesto import generar


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
            resultado_estu=80,
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


if __name__ == "__main__":
    unittest.main()
