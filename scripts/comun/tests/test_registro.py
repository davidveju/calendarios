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

PUBLICACION = "deportes/baloncesto"


class TestRegistro(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.raiz = Path(self._tmp.name)
        self.dir = (
            self.raiz
            / "scripts"
            / "calendarios"
            / "deportes"
            / "baloncesto"
            / "estudiantes"
        )
        self.dir.mkdir(parents=True)
        (self.dir / "generar.py").write_text("print('ok')\n", encoding="utf-8")
        self._manifest(
            {
                "nombre": "Baloncesto",
                "ics": "deportes/baloncesto/estudiantes.ics",
                "datos": ["partidos.json", "sedes.json"],
            }
        )

    def tearDown(self):
        self._tmp.cleanup()

    def _manifest(self, datos: dict, directorio: Path | None = None) -> None:
        destino = directorio or self.dir
        (destino / "calendario.json").write_text(
            json.dumps(datos), encoding="utf-8"
        )

    def _crear_calendario(
        self,
        nombre: str,
        *,
        ics: str | None = None,
    ) -> Path:
        directorio = self.raiz / "scripts" / "calendarios" / "deportes" / nombre
        directorio.mkdir(parents=True)
        (directorio / "generar.py").write_text("print('ok')\n", encoding="utf-8")
        self._manifest(
            {
                "nombre": nombre,
                "ics": ics or f"{PUBLICACION}/{nombre}.ics",
                "datos": ["estado.json"],
            },
            directorio,
        )
        return directorio

    def test_carga_codigo_estado_y_publicacion_separados(self):
        calendario = cargar_contexto(
            "deportes/baloncesto/estudiantes", self.dir, self.raiz
        )
        self.assertEqual(calendario.id, "deportes/baloncesto/estudiantes")
        self.assertEqual(
            calendario.modulo,
            "scripts.calendarios.deportes.baloncesto.estudiantes.generar",
        )
        self.assertEqual(calendario.codigo, self.dir)
        self.assertEqual(
            calendario.estado,
            self.raiz / "estado" / "deportes" / "baloncesto" / "estudiantes",
        )
        self.assertEqual(
            calendario.publicacion, self.raiz / "deportes" / "baloncesto"
        )
        self.assertEqual(
            calendario.ruta_ics,
            self.raiz / "deportes" / "baloncesto" / "estudiantes.ics",
        )
        self.assertEqual(
            calendario.ruta_estado("partidos.json"),
            calendario.estado / "partidos.json",
        )
        self.assertEqual(calendario.nombre, "Baloncesto")
        self.assertEqual(calendario.datos, ("partidos.json", "sedes.json"))
        self.assertEqual(calendario.zona, "Europe/Madrid")
        self.assertNotEqual(calendario.codigo, calendario.estado)
        self.assertNotEqual(calendario.publicacion, calendario.estado)

    def test_descubre_y_obtiene(self):
        calendarios = descubrir_calendarios(self.raiz)
        self.assertEqual(
            [c.id for c in calendarios], ["deportes/baloncesto/estudiantes"]
        )
        self.assertEqual(
            obtener_calendario(
                self.raiz, "deportes/baloncesto/estudiantes"
            ).nombre,
            "Baloncesto",
        )

    def test_dos_calendarios_comparten_publicacion_pero_no_estado(self):
        self._crear_calendario("otro")
        calendarios = descubrir_calendarios(self.raiz)
        self.assertEqual(
            [c.id for c in calendarios],
            ["deportes/baloncesto/estudiantes", "deportes/otro"],
        )
        estudiantes, otro = calendarios
        self.assertEqual(estudiantes.publicacion, otro.publicacion)
        self.assertNotEqual(estudiantes.ruta_ics, otro.ruta_ics)
        self.assertNotEqual(estudiantes.estado, otro.estado)
        self.assertEqual(otro.ruta_ics.name, "otro.ics")
        self.assertEqual(
            otro.estado, self.raiz / "estado" / "deportes" / "otro"
        )

    def test_ics_duplicado_se_omite_o_falla(self):
        self._crear_calendario(
            "otro", ics="deportes/baloncesto/estudiantes.ics"
        )
        self.assertEqual(
            [c.id for c in descubrir_calendarios(self.raiz)],
            ["deportes/baloncesto/estudiantes"],
        )
        with self.assertRaisesRegex(ErrorCalendario, "duplicado"):
            descubrir_calendarios(self.raiz, estricto=True)

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
            ["deportes/baloncesto/estudiantes"],
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
            cargar_contexto(
                "deportes/baloncesto/estudiantes", self.dir, self.raiz
            )

    def test_ics_por_defecto(self):
        self._manifest({"nombre": "Baloncesto"})
        calendario = cargar_contexto(
            "deportes/baloncesto/estudiantes", self.dir, self.raiz
        )
        self.assertEqual(calendario.ics, "calendario.ics")
        self.assertEqual(calendario.ruta_ics, self.raiz / "calendario.ics")

    def test_ics_invalido(self):
        for ruta in ("deportes/baloncesto/foo.txt", "estado/foo.ics"):
            with self.subTest(ruta=ruta):
                self._manifest({"nombre": "Baloncesto", "ics": ruta})
                with self.assertRaises(ErrorCalendario):
                    cargar_contexto(
                        "deportes/baloncesto/estudiantes", self.dir, self.raiz
                    )

    def test_ruta_estado_absoluta_o_con_parentesis_falla(self):
        for ruta in ("/etc/passwd", "../fuera.json"):
            with self.subTest(ruta=ruta):
                self._manifest({"nombre": "Baloncesto", "datos": [ruta]})
                with self.assertRaises(ErrorCalendario):
                    cargar_contexto(
                        "deportes/baloncesto/estudiantes", self.dir, self.raiz
                    )

    def test_zona_invalida(self):
        self._manifest({"nombre": "Baloncesto", "zona": "Marte/Olympus"})
        with self.assertRaises(ErrorCalendario):
            cargar_contexto(
                "deportes/baloncesto/estudiantes", self.dir, self.raiz
            )

    def test_obtener_inexistente(self):
        with self.assertRaisesRegex(ErrorCalendario, "disponibles"):
            obtener_calendario(self.raiz, "no/existe")

    def test_contexto_del_repositorio_real(self):
        calendario = contexto("deportes/baloncesto/estudiantes")
        self.assertEqual(
            calendario.codigo,
            RAIZ_REPO
            / "scripts"
            / "calendarios"
            / "deportes"
            / "baloncesto"
            / "estudiantes",
        )
        self.assertEqual(
            calendario.ruta_ics,
            RAIZ_REPO / "deportes" / "baloncesto" / "estudiantes.ics",
        )
        self.assertEqual(
            calendario.estado,
            RAIZ_REPO / "estado" / "deportes" / "baloncesto" / "estudiantes",
        )
        self.assertEqual(calendario.publicacion, RAIZ_REPO / "deportes" / "baloncesto")

    def test_contexto_desde_ejecucion_directa(self):
        fichero = self.dir / "generar.py"
        ctx = contexto_desde_ejecucion("__main__", fichero, self.raiz)
        self.assertEqual(ctx.id, "deportes/baloncesto/estudiantes")
        self.assertEqual(ctx.codigo, self.dir)
        self.assertEqual(
            ctx.estado,
            self.raiz / "estado" / "deportes" / "baloncesto" / "estudiantes",
        )
        self.assertEqual(
            ctx.ruta_ics,
            self.raiz / "deportes" / "baloncesto" / "estudiantes.ics",
        )

    def test_contexto_desde_ejecucion_con_modulo(self):
        fichero = self.dir / "generar.py"
        ctx = contexto_desde_ejecucion(
            "scripts.calendarios.deportes.baloncesto.estudiantes.generar",
            fichero,
            self.raiz,
        )
        self.assertEqual(ctx.id, "deportes/baloncesto/estudiantes")

    def test_contexto_desde_ejecucion_directa_fuera_del_arbol(self):
        fichero = self.raiz / "generar.py"
        fichero.write_text("", encoding="utf-8")
        with self.assertRaises(ErrorCalendario):
            contexto_desde_ejecucion("__main__", fichero, self.raiz)

    def test_id_desde_modulo(self):
        self.assertEqual(
            id_desde_modulo(
                "scripts.calendarios.deportes.baloncesto.estudiantes.generar"
            ),
            "deportes/baloncesto/estudiantes",
        )
        with self.assertRaises(ErrorCalendario):
            id_desde_modulo("deportes.baloncesto.generar")


if __name__ == "__main__":
    unittest.main()
