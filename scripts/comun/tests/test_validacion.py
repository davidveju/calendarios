"""Tests del validador de ICS."""

from __future__ import annotations

import unittest
from datetime import datetime

from scripts.comun.ics import Evento, generar_ics
from scripts.comun.validacion import validar_bytes


class TestValidacion(unittest.TestCase):
    def _ics(self) -> bytes:
        return generar_ics(
            "Prueba",
            [
                Evento(
                    uid="a@x",
                    inicio=datetime(2027, 1, 1, 12, 0),
                    resumen="Partido",
                )
            ],
        ).encode("utf-8")

    def test_ics_valido(self):
        self.assertEqual(validar_bytes(self._ics()), [])

    def test_vacio(self):
        self.assertIn("vacío", validar_bytes(b"")[0])

    def test_lf_sin_cr(self):
        errores = validar_bytes(self._ics().replace(b"\r\n", b"\n"))
        self.assertTrue(any("LF sin CR" in e for e in errores))

    def test_sin_crlf_final(self):
        errores = validar_bytes(self._ics().removesuffix(b"\r\n"))
        self.assertTrue(any("no termina en CRLF" in e for e in errores))

    def test_linea_demasiado_larga(self):
        data = self._ics().replace(b"SUMMARY:Partido", b"SUMMARY:" + b"x" * 80)
        self.assertTrue(any(">75" in e for e in validar_bytes(data)))

    def test_uid_duplicado(self):
        data = self._ics().replace(b"UID:a@x", b"UID:a@x\r\nUID:a@x")
        self.assertTrue(any("UIDs duplicados" in e for e in validar_bytes(data)))

    def test_fecha_no_utc(self):
        data = self._ics().replace(b"DTSTART:20270101T110000Z", b"DTSTART:20270101T120000")
        self.assertTrue(any("fecha no UTC" in e for e in validar_bytes(data)))


if __name__ == "__main__":
    unittest.main()
