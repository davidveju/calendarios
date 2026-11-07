"""Tests del registro de calendarios."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from calendarios.registro import (
    ErrorCalendario,
    cargar_calendario,
    descubrir_calendarios,
    obtener_calendario,
)


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.dir = self.raiz / "deportes" / "baloncesto"
        self.dir.mkdir(parents=True)
        (self.dir / "generar.py").write_text("print('ok')\n", encoding="utf-8")
        self._manifest(
            {
                "nombre": "Baloncesto",
                "ics": "calendario.ics",
                "datos": ["datos/partidos.json"],
            }
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _manifest(self, datos: dict) -> None:
        (self.dir / "calendario.json").write_text(
            json.dumps(datos), encoding="utf-8"
        )

    def test_carga_y_propiedades(self):
        calendario = cargar_calendario(self.dir, self.raiz)
        self.assertEqual(calendario.id, "deportes/baloncesto")
        self.assertEqual(calendario.modulo, "deportes.baloncesto.generar")
        self.assertEqual(calendario.nombre, "Baloncesto")
        self.assertEqual(calendario.datos, ("datos/partidos.json",))
        self.assertEqual(calendario.zona, "Europe/Madrid")
        self.assertEqual(
            calendario.ruta_ics, self.dir / "calendario.ics"
        )

    def test_descubre(self):
        calendarios = descubrir_calendarios(self.raiz)
        self.assertEqual([c.id for c in calendarios], ["deportes/baloncesto"])
        self.assertEqual(obtener_calendario(self.raiz, "deportes/baloncesto").nombre, "Baloncesto")

    def test_id_invalido(self):
        (self.raiz / "Deportes").mkdir()
        dir_invalido = self.raiz / "Deportes" / "Baloncesto"
        dir_invalido.mkdir()
        (dir_invalido / "generar.py").write_text("", encoding="utf-8")
        (dir_invalido / "calendario.json").write_text(
            json.dumps({"nombre": "X"}), encoding="utf-8"
        )
        with self.assertRaises(ErrorCalendario):
            cargar_calendario(dir_invalido, self.raiz)
        self.assertEqual(
            [c.id for c in descubrir_calendarios(self.raiz)], ["deportes/baloncesto"]
        )

    def test_manifiesto_roto_se_omite_o_falla(self):
        self._manifest({"nombre": ""})
        self.assertEqual(descubrir_calendarios(self.raiz), [])
        with self.assertRaises(ErrorCalendario):
            descubrir_calendarios(self.raiz, estricto=True)

    def test_generador_inexistente(self):
        (self.dir / "generar.py").unlink()
        with self.assertRaises(ErrorCalendario):
            cargar_calendario(self.dir, self.raiz)

    def test_falta_ics_no_se_valida_al_descubrir(self):
        self._manifest({"nombre": "Baloncesto", "ics": "otro.ics"})
        calendario = cargar_calendario(self.dir, self.raiz)
        self.assertEqual(calendario.fichero_ics, "otro.ics")

    def test_zona_invalida(self):
        self._manifest({"nombre": "Baloncesto", "zona": "Marte/Olympus"})
        with self.assertRaises(ErrorCalendario):
            cargar_calendario(self.dir, self.raiz)

    def test_obtener_inexistente(self):
        with self.assertRaisesRegex(ErrorCalendario, "disponibles"):
            obtener_calendario(self.raiz, "no/existe")


if __name__ == "__main__":
    unittest.main()
