"""Tests del runner y del aislamiento entre calendarios."""

from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from scripts.comun.registro import descubrir_calendarios
from scripts.comun.runner import ejecutar_calendario, ejecutar_calendarios

ICS_OK = (
    b"BEGIN:VCALENDAR\r\n"
    b"VERSION:2.0\r\n"
    b"PRODID:-//test//ES\r\n"
    b"CALSCALE:GREGORIAN\r\n"
    b"END:VCALENDAR\r\n"
)

GENERADOR_OK = """\
from pathlib import Path

raiz = Path(__file__).resolve().parents[4]
salida = raiz / "deportes" / "{nombre}"
estado = raiz / "estado" / "deportes" / "{nombre}"
salida.mkdir(parents=True, exist_ok=True)
estado.mkdir(parents=True, exist_ok=True)
(estado / "estado.json").write_text('{{"ok": true}}\\n', encoding="utf-8")
(salida / "calendario.ics").write_bytes({ics!r})
"""


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
        base = self.raiz / "scripts" / "calendarios"
        for paquete in (
            self.raiz / "scripts",
            base,
            base / "deportes",
            base / "deportes" / nombre,
        ):
            paquete.mkdir(parents=True, exist_ok=True)
            (paquete / "__init__.py").write_text("", encoding="utf-8")

        codigo = base / "deportes" / nombre
        (codigo / "calendario.json").write_text(
            json.dumps(
                {
                    "nombre": nombre,
                    "ics": f"deportes/{nombre}/calendario.ics",
                    "datos": ["estado.json"],
                }
            ),
            encoding="utf-8",
        )
        if exito:
            contenido = GENERADOR_OK.format(nombre=nombre, ics=ICS_OK)
        else:
            contenido = "import sys\nsys.exit(3)\n"
        (codigo / "generar.py").write_text(contenido, encoding="utf-8")

    def test_un_fallo_no_impide_el_resto(self):
        with contextlib.redirect_stdout(io.StringIO()):
            codigo = ejecutar_calendarios(self.calendarios, self.raiz, timeout=60)
        self.assertEqual(codigo, 1)
        # El calendario que falla no ha dejado salida; el siguiente sí se ejecutó.
        self.assertFalse(
            (self.raiz / "deportes" / "falla" / "calendario.ics").exists()
        )
        self.assertTrue((self.raiz / "deportes" / "ok" / "calendario.ics").exists())
        self.assertTrue(
            (
                self.raiz
                / "estado"
                / "deportes"
                / "ok"
                / "estado.json"
            ).exists()
        )

    def test_ejecucion_individual_ok(self):
        calendario = next(c for c in self.calendarios if c.id == "deportes/ok")
        with contextlib.redirect_stdout(io.StringIO()):
            resultado = ejecutar_calendario(calendario, self.raiz, timeout=60)
        self.assertTrue(resultado.ok)
        self.assertEqual(resultado.detalle, "")

    def test_salidas_aisladas_por_calendario(self):
        with contextlib.redirect_stdout(io.StringIO()):
            ejecutar_calendario(
                next(c for c in self.calendarios if c.id == "deportes/ok"),
                self.raiz,
                timeout=60,
            )
        # El estado y la salida de otro calendario siguen intactos.
        self.assertFalse(
            (
                self.raiz
                / "estado"
                / "deportes"
                / "falla"
                / "estado.json"
            ).exists()
        )
        self.assertTrue(
            (
                self.raiz
                / "estado"
                / "deportes"
                / "ok"
                / "estado.json"
            ).exists()
        )
        self.assertFalse(
            (self.raiz / "deportes" / "falla" / "calendario.ics").exists()
        )

    def test_ics_invalido_falla(self):
        calendario = next(c for c in self.calendarios if c.id == "deportes/ok")
        (calendario.codigo / "generar.py").write_text(
            "from pathlib import Path\n"
            "raiz = Path(__file__).resolve().parents[4]\n"
            "salida = raiz / 'deportes' / 'ok'\n"
            "estado = raiz / 'estado' / 'deportes' / 'ok'\n"
            "salida.mkdir(parents=True, exist_ok=True)\n"
            "estado.mkdir(parents=True, exist_ok=True)\n"
            "(estado / 'estado.json').write_text('{}\\n', encoding='utf-8')\n"
            "(salida / 'calendario.ics').write_text('BEGIN:VCALENDAR\\n', encoding='utf-8')\n",
            encoding="utf-8",
        )
        with contextlib.redirect_stdout(io.StringIO()):
            resultado = ejecutar_calendario(calendario, self.raiz, timeout=60)
        self.assertFalse(resultado.ok)
        self.assertIn("CRLF", resultado.detalle)


if __name__ == "__main__":
    unittest.main()
