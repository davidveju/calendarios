"""Tests del generador ICS común."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone

from scripts.comun.ics import Evento, esc, fold_line, generar_ics


class TestEscapado(unittest.TestCase):
    def test_texto(self):
        self.assertEqual(esc("a,b;c\\d\ne"), "a\\,b\\;c\\\\d\\ne")


class TestFold(unittest.TestCase):
    def test_limites_y_multibyte(self):
        for s in ("A" * 74, "A" * 75, "A" * 76, "ñ" * 40, "🏀" * 30, "x" * 73 + "ñ"):
            line = "SUMMARY:" + s
            folded = fold_line(line)
            for trozo in folded.split("\r\n"):
                self.assertLessEqual(len(trozo.encode("utf-8")), 75)
            self.assertEqual(folded.replace("\r\n ", ""), line)


class TestGenerarICS(unittest.TestCase):
    def _evento(self, uid: str, **extra) -> Evento:
        datos = {
            "uid": uid,
            "inicio": datetime(2027, 1, 1, 12, 0),
            "resumen": "Partido",
            "descripcion": "Línea 1\nLínea 2",
            "url": "https://example.com/1",
            "lugar": "Pabellón, Madrid",
        }
        datos.update(extra)
        return Evento(**datos)

    def test_estructura_crlf_y_plegado(self):
        ics = generar_ics(
            "Calendario de prueba",
            [
                self._evento("b@x", inicio=datetime(2027, 1, 2, 12, 0)),
                self._evento("a@x"),
            ],
            ahora=datetime(2026, 1, 1, tzinfo=timezone.utc),
        )
        data = ics.encode("utf-8")
        self.assertTrue(data.endswith(b"\r\n"))
        self.assertNotIn(b"\r\r\n", data)
        for linea in data.split(b"\r\n"):
            self.assertLessEqual(len(linea), 75)
        self.assertEqual(data.count(b"BEGIN:VEVENT"), 2)
        self.assertEqual(data.count(b"UID:"), 2)
        self.assertEqual(data.count(b"DTSTART:"), 2)
        self.assertIn(b"DTSTAMP:20260101T000000Z", data)
        # Ordenados por inicio y fechas en UTC (enero en Madrid es UTC+1).
        self.assertLess(ics.index("UID:a@x"), ics.index("UID:b@x"))
        self.assertIn("DTSTART:20270101T110000Z", ics)
        self.assertIn("LOCATION:Pabellón\\, Madrid", ics)

    def test_estado_provisional_y_fin_por_defecto(self):
        ics = generar_ics("Prueba", [self._evento("a@x", estado="TENTATIVE")])
        self.assertIn("STATUS:TENTATIVE", ics)
        self.assertIn("DTEND:20270101T130000Z", ics)

    def test_uid_duplicado_falla(self):
        with self.assertRaisesRegex(ValueError, "UIDs duplicados"):
            generar_ics("Prueba", [self._evento("a@x"), self._evento("a@x")])

    def test_resumen_vacio_falla(self):
        with self.assertRaisesRegex(ValueError, "SUMMARY vacío"):
            generar_ics("Prueba", [self._evento("a@x", resumen="  ")])

    def test_estado_invalido_falla(self):
        with self.assertRaisesRegex(ValueError, "STATUS"):
            generar_ics("Prueba", [self._evento("a@x", estado="OK")])

    def test_fin_anterior_falla(self):
        with self.assertRaisesRegex(ValueError, "DTEND"):
            generar_ics(
                "Prueba",
                [self._evento("a@x", fin=datetime(2026, 12, 31, 12, 0))],
            )

    def test_calendario_vacio_es_valido(self):
        ics = generar_ics("Vacío", [])
        self.assertIn("BEGIN:VCALENDAR", ics)
        self.assertIn("END:VCALENDAR", ics)
        self.assertNotIn("BEGIN:VEVENT", ics)


if __name__ == "__main__":
    unittest.main()
