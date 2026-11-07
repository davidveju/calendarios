"""Tests del runner y del aislamiento entre calendarios."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from calendarios.registro import descubrir_calendarios
from calendarios.runner import ejecutar_calendario, ejecutar_calendarios

ICS_OK = (
    b"BEGIN:VCALENDAR\r\n"
    b"VERSION:2.0\r\n"
    b"PRODID:-//test//ES\r\n"
    b"CALSCALE:GREGORIAN\r\n"
    b"END:VCALENDAR\r\n"
)


class TestRunner(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self._crear("ok", exito=True)
        self._crear("falla", exito=False)
        self.calendarios = descubrir_calendarios(self.raiz)
        self.assertEqual(
            [c.id for c in self.calendarios], ["deportes/falla", "deportes/ok"]
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _crear(self, nombre: str, *, exito: bool) -> None:
        directorio = self.raiz / "deportes" / nombre
        directorio.mkdir(parents=True)
        (directorio / "__init__.py").write_text("", encoding="utf-8")
        (directorio / "datos").mkdir()
        (directorio / "calendario.json").write_text(
            json.dumps(
                {
                    "nombre": nombre,
                    "ics": "calendario.ics",
                    "datos": ["datos/estado.json"],
                }
            ),
            encoding="utf-8",
        )
        if exito:
            (directorio / "generar.py").write_text(
                "from pathlib import Path\n"
                "d = Path(__file__).resolve().parent\n"
                "(d / 'datos' / 'estado.json').write_text('{\"ok\": true}\\n', encoding='utf-8')\n"
                "(d / 'calendario.ics').write_bytes(" + repr(ICS_OK) + ")\n",
                encoding="utf-8",
            )
        else:
            (directorio / "generar.py").write_text(
                "import sys\nsys.exit(3)\n", encoding="utf-8"
            )

    def test_un_fallo_no_impide_el_resto(self):
        with contextlib.redirect_stdout(io.StringIO()):
            codigo = ejecutar_calendarios(self.calendarios, self.raiz, timeout=60)
        self.assertEqual(codigo, 1)
        # El calendario que falla no ha dejado salida; el siguiente sí se ejecutó.
        self.assertFalse((self.raiz / "deportes" / "falla" / "calendario.ics").exists())
        self.assertTrue((self.raiz / "deportes" / "ok" / "calendario.ics").exists())

    def test_ejecucion_individual_ok(self):
        calendario = next(c for c in self.calendarios if c.id == "deportes/ok")
        with contextlib.redirect_stdout(io.StringIO()):
            resultado = ejecutar_calendario(calendario, self.raiz, timeout=60)
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.detalle, "")

    def test_ics_invalido_falla(self):
        calendario = next(c for c in self.calendarios if c.id == "deportes/ok")
        (calendario.directorio / "generar.py").write_text(
            "from pathlib import Path\n"
            "d = Path(__file__).resolve().parent\n"
            "(d / 'datos' / 'estado.json').write_text('{}\\n', encoding='utf-8')\n"
            "(d / 'calendario.ics').write_text('BEGIN:VCALENDAR\\n', encoding='utf-8')\n",
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            resultado = ejecutar_calendario(calendario, self.raiz, timeout=60)
        self.assertFalse(resultado.ok)
        self.assertIn("CRLF", resultado.detalle)


if __name__ == "__main__":
    unittest.main()
