"""Tests sin red del proveedor de festivos de Madrid."""

from __future__ import annotations

import unittest

from scripts.proveedores.openholidays import fuentes
from scripts.proveedores.openholidays.config import ConfigFestivos

CONFIG = ConfigFestivos(
    nombre_calendario="Festivos de Madrid",
    subdivision_code="ES-MD-MD",
    uid_prefix="madrid-festivos",
    uid_dominio="madridfestivos-calendario",
)


class TestFestivos(unittest.TestCase):
    def test_genera_festivos(self):
        partidos = fuentes.generar_festivos(CONFIG, 2027, 2027)
        self.assertTrue(len(partidos) >= 14)
        self.assertTrue(all(p.get("acta") for p in partidos))
        self.assertTrue(all("2027" in p["inicio_madrid"] for p in partidos))

    def test_sin duplicados(self):
        partidos = fuentes.generar_festivos(CONFIG, 2027, 2027)
        uids = [p["uid"] for p in partidos]
        self.assertEqual(len(uids), len(set(uids)))


if __name__ == "__main__":
    unittest.main()
