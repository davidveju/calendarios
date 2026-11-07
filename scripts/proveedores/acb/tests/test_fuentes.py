"""Tests sin red del proveedor ACB."""

from __future__ import annotations

import unittest

from scripts.proveedores.acb import fuentes
from scripts.proveedores.acb.config import ConfigACB

CONFIG = ConfigACB(
    team_name="Real Madrid",
    temporada="26/27",
    uid_prefix="madrid-b-2627",
    uid_dominio="madridbaloncesto-calendario",
    casa_pabellon="Movistar Arena, Madrid",
)

HTML = """
<p>- **Domingo 27 de septiembre (19:00)**. Real Madrid - Unicaja</p>
<p>- **Domingo 4 de octubre (12:30)**. Monbus Obradoiro - Real Madrid</p>
<p>- **Domingo 25 de mayo (Horario sin confirmar)**. Barça - Real Madrid</p>
<p>- **Domingo 1 de noviembre (12:30)**. Real Madrid - Recoletas Salud San Pablo Burgos</p>
"""


class TestACB(unittest.TestCase):
    def test_extrae_partidos(self):
        partidos = fuentes.extraer_partidos(HTML, CONFIG)
        self.assertEqual(len(partidos), 4)

    def test_casa_y_rival(self):
        partidos = fuentes.extraer_partidos(HTML, CONFIG)
        local = next(p for p in partidos if p["rival"] == "Unicaja")
        self.assertTrue(local["casa"])
        self.assertEqual(local["inicio_madrid"], "2026-09-27T19:00")
        self.assertFalse(local["fecha_provisional"])
        visit = next(p for p in partidos if p["rival"] == "Monbus Obradoiro")
        self.assertFalse(visit["casa"])
        self.assertEqual(visit["inicio_madrid"], "2026-10-04T12:30")

    def test_horario_sin_confirmar(self):
        partidos = fuentes.extraer_partidos(HTML, CONFIG)
        prov = next(p for p in partidos if p["rival"] == "Barça")
        self.assertTrue(prov["fecha_provisional"])
        self.assertEqual(prov["inicio_madrid"], "2027-05-25T12:00")

    def test_invalido(self):
        self.assertEqual(fuentes.extraer_partidos("sin nada", CONFIG), [])


if __name__ == "__main__":
    unittest.main()
