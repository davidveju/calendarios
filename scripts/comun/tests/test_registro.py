"""Tests del contexto y del registro de calendarios."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.comun.contexto import (
    RAIZ_REPO,
    ErrorCalendario,
    cargar_contexto,
    contexto,
    contexto_desde_ejecucion,
    id_desde_modulo,
)
from scripts.comun.registro import descubrir_calendarios, obtener_calendario


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.dir = self.raiz / "scripts" / "calendarios" / "deportes" / "baloncesto"
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

    def _manifest(self, datos: dict, directorio: Path | None = None) -> None:
        destino = directorio or self.dir
        (destino / "calendario.json").write_text(
            json.dumps(datos), encoding="utf-8"
        )

    def _crear_calendario(self, nombre: str, descripcion: str = "") -> Path:
        directorio = self.raiz / "scripts" / "calendarios" / "deportes" / nombre
        directorio.mkdir(parents=True)
        (directorio / "generar.py").write_text("print('ok')\n", encoding="utf-8")
        self._manifest(
            {
                "nombre": descripcion or nombre,
                "ics": f"{nombre}.ics",
                "datos": ["datos/estado.json"],
            },
            directorio,
        )
        return directorio

    def test_carga_codigo_y_salida_separados(self):
        calendario = cargar_contexto("deportes/baloncesto", self.dir, self.raiz)
        self.assertEqual(calendario.id, "deportes/baloncesto")
        self.assertEqual(
            calendario.modulo, "scripts.calendarios.deportes.baloncesto.generar"
        )
        self.assertEqual(calendario.codigo, self.dir)
        self.assertEqual(calendario.salida, self.raiz / "deportes" / "baloncesto")
        self.assertEqual(calendario.nombre, "Baloncesto")
        self.assertEqual(calendario.datos, ("datos/partidos.json",))
        self.assertEqual(calendario.zona, "Europe/Madrid")
        self.assertEqual(
            calendario.ruta_ics,
            self.raiz / "deportes" / "baloncesto" / "calendario.ics",
        )
        self.assertEqual(
            calendario.ruta_dato("datos/partidos.json"),
            self.raiz / "deportes" / "baloncesto" / "datos" / "partidos.json",
        )

    def test_descubre_y_obtiene(self):
        calendarios = descubrir_calendarios(self.raiz)
        self.assertEqual([c.id for c in calendarios], ["deportes/baloncesto"])
        self.assertEqual(
            obtener_calendario(self.raiz, "deportes/baloncesto").nombre,
            "Baloncesto",
        )

    def test_dos_calendarios_no_comparten_salida(self):
        self._crear_calendario("otro", "Otro")
        calendarios = descubrir_calendarios(self.raiz)
        self.assertEqual(
            [c.id for c in calendarios], ["deportes/baloncesto", "deportes/otro"]
        )
        salidas = {c.id: c.salida for c in calendarios}
        self.assertEqual(len(set(salidas.values())), 2)
        self.assertEqual(salidas["deportes/otro"], self.raiz / "deportes" / "otro")
        self.assertEqual(calendarios[1].ruta_ics.name, "otro.ics")
        self.assertNotEqual(calendarios[0].codigo, calendarios[0].salida)

    def test_id_invalido(self):
        dir_invalido = (
            self.raiz / "scripts" / "calendarios" / "Deportes" / "Baloncesto"
        )
        dir_invalido.mkdir(parents=True)
        (dir_invalido / "generar.py").write_text("", encoding="utf-8")
        self._manifest({"nombre": "X"}, dir_invalido)
        with self.assertRaises(ErrorCalendario):
            cargar_contexto("Deportes/Baloncesto", dir_invalido, self.raiz)
        self.assertEqual(
            [c.id for c in descubrir_calendarios(self.raiz)],
            ["deportes/baloncesto"],
        )

    def test_id_no_coincide_con_la_ruta(self):
        with self.assertRaises(ErrorCalendario):
            cargar_contexto("deportes/otro", self.dir, self.raiz)

    def test_codigo_fuera_de_scripts_calendarios(self):
        fuera = self.raiz / "deportes" / "baloncesto"
        fuera.mkdir(parents=True)
        (fuera / "generar.py").write_text("", encoding="utf-8")
        self._manifest({"nombre": "X"}, fuera)
        with self.assertRaises(ErrorCalendario):
            cargar_contexto("deportes/baloncesto", fuera, self.raiz)

    def test_manifiesto_roto_se_omite_o_falla(self):
        self._manifest({"nombre": ""})
        self.assertEqual(descubrir_calendarios(self.raiz), [])
        with self.assertRaises(ErrorCalendario):
            descubrir_calendarios(self.raiz, estricto=True)

    def test_generador_inexistente(self):
        (self.dir / "generar.py").unlink()
        with self.assertRaises(ErrorCalendario):
            cargar_contexto("deportes/baloncesto", self.dir, self.raiz)

    def test_falta_ics_no_se_valida_al_descubrir(self):
        self._manifest({"nombre": "Baloncesto", "ics": "otro.ics"})
        calendario = cargar_contexto("deportes/baloncesto", self.dir, self.raiz)
        self.assertEqual(calendario.fichero_ics, "otro.ics")

    def test_ruta_dato_absoluta_o_con_parentesis_falla(self):
        for ruta in ("/etc/passwd", "../fuera.json"):
            with self.subTest(ruta=ruta):
                self._manifest({"nombre": "Baloncesto", "datos": [ruta]})
                with self.assertRaises(ErrorCalendario):
                    cargar_contexto("deportes/baloncesto", self.dir, self.raiz)

    def test_zona_invalida(self):
        self._manifest({"nombre": "Baloncesto", "zona": "Marte/Olympus"})
        with self.assertRaises(ErrorCalendario):
            cargar_contexto("deportes/baloncesto", self.dir, self.raiz)

    def test_obtener_inexistente(self):
        with self.assertRaisesRegex(ErrorCalendario, "disponibles"):
            obtener_calendario(self.raiz, "no/existe")

    def test_contexto_del_repositorio_real(self):
        calendario = contexto("deportes/baloncesto")
        self.assertEqual(
            calendario.codigo,
            RAIZ_REPO
            / "scripts"
            / "calendarios"
            / "deportes"
            / "baloncesto",
        )
        self.assertEqual(calendario.ruta_ics.name, "estudiantes.ics")

    def test_contexto_desde_ejecucion_directa(self):
        fichero = self.dir / "generar.py"
        ctx = contexto_desde_ejecucion("__main__", fichero, self.raiz)
        self.assertEqual(ctx.id, "deportes/baloncesto")
        self.assertEqual(ctx.codigo, self.dir)
        self.assertEqual(ctx.salida, self.raiz / "deportes" / "baloncesto")

    def test_contexto_desde_ejecucion_con_modulo(self):
        fichero = self.dir / "generar.py"
        ctx = contexto_desde_ejecucion(
            "scripts.calendarios.deportes.baloncesto.generar",
            fichero,
            self.raiz,
        )
        self.assertEqual(ctx.id, "deportes/baloncesto")

    def test_contexto_desde_ejecucion_directa_fuera_del_arbol(self):
        fichero = self.raiz / "generar.py"
        fichero.write_text("", encoding="utf-8")
        with self.assertRaises(ErrorCalendario):
            contexto_desde_ejecucion("__main__", fichero, self.raiz)

    def test_id_desde_modulo(self):
        self.assertEqual(
            id_desde_modulo("scripts.calendarios.deportes.baloncesto.generar"),
            "deportes/baloncesto",
        )
        with self.assertRaises(ErrorCalendario):
            id_desde_modulo("deportes.baloncesto.generar")


if __name__ == "__main__":
    unittest.main()
