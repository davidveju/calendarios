"""Tests sin red de los parsers de la FEB."""

from __future__ import annotations

import unittest
from dataclasses import replace

from scripts.proveedores.feb import fuentes
from scripts.proveedores.feb.config import ConfigFEB

CONFIG = ConfigFEB(
    equipo_id="1010493",
    equipo_corto="Estu",
    temporada="26/27",
    uid_prefix="estu-2627",
    uid_dominio="estudiantes-calendario",
    liga_url="https://competiciones.feb.es/estadisticas/Calendario.aspx",
    copa_url="https://www.feb.es/competiciones/resultados/copaespaa/73/2026",
    liga_nombre="Primera FEB 26/27",
    copa_nombre="Copa España 26/27",
    casa_pabellon="Movistar Arena, Madrid",
    jornadas_liga=34,
)


LIGA_FECHA = """Jornada 1 23/10/2026
<table>
<tr>
  <td><a href="Equipo.aspx?i=1010493">ESTU</a></td>
  <td><a href="Equipo.aspx?i=111">RIVAL</a></td>
  <td class="fecha"><a>25/10/2026&nbsp;<br/>18:00</a></td>
  <td><a href="Partido.aspx?p=123">x</a></td>
</tr>
</table>"""

LIGA_JUGADO = """Jornada 1 23/10/2026
<table>
<tr>
  <td><a href="Equipo.aspx?i=1010493">ESTU</a></td>
  <td><a href="Equipo.aspx?i=111">RIVAL</a></td>
  <td class="resultado"><a>80-70</a></td>
  <td><a href="Partido.aspx?p=123">x</a></td>
</tr>
</table>"""

COPA_TBD = """<select id="_ctl0_gruposDropDownList">
<option selected="selected" value="1">Play-offs 1/8 Final</option>
</select>
<select id="_ctl0_jornadasDropDownList">
<option selected="selected" value="2">Jornada 1(17/11/2026)</option>
</select>
<table><tr>
  <td><a href="Equipo.aspx?i=222">CACERES</a> -
      <a href="Equipo.aspx?i=1010493">ESTU</a></td>
  <td><a href="Partido.aspx?p=2550809">*-*</a></td>
  <td>Por determinar</td>
  <td></td>
</tr></table>"""

COPA_JUGADO = """<select id="_ctl0_gruposDropDownList">
<option selected="selected" value="1">Play-offs 1/16 Final</option>
</select>
<select id="_ctl0_jornadasDropDownList">
<option selected="selected" value="2">Jornada 1(20/10/2026)</option>
</select>
<table><tr>
  <td><a href="Equipo.aspx?i=333">COVIRAN GRANADA</a> -
      <a href="Equipo.aspx?i=1010493">ESTU</a></td>
  <td><a href="Partido.aspx?p=2543131">76-86</a></td>
  <td>20/10/2026</td>
  <td>20:30</td>
</tr></table>"""


class TestScore(unittest.TestCase):
    def test_marcador(self):
        self.assertEqual(fuentes._score("78-65"), (78, 65))
        self.assertEqual(fuentes._score("78 - 65"), (78, 65))
        self.assertEqual(fuentes._score("106–76 (prórroga)"), (106, 76))

    def test_fecha_no_es_marcador(self):
        self.assertIsNone(fuentes._score("12-10-2026"))
        self.assertIsNone(fuentes._score("2026-10-12"))
        self.assertIsNone(fuentes._score("*-*"))


class TestTitleCase(unittest.TestCase):
    def test_nombres(self):
        self.assertEqual(fuentes.title_case("C.B. STARLABS MORÓN"), "CB Starlabs Morón")
        self.assertEqual(
            fuentes.title_case("PARTIZÁN DE FUENLABRADA"), "Partizán de Fuenlabrada"
        )
        self.assertEqual(
            fuentes.title_case("PABELLÓN MUNICIPAL DE DEPORTES (PALENCIA)"),
            "Pabellón Municipal de Deportes (Palencia)",
        )


class TestRondaCopa(unittest.TestCase):
    def test_rondas(self):
        self.assertEqual(fuentes._ronda_copa("Play-offs 1/16 Final", 1), ("1/16", 1))
        self.assertEqual(fuentes._ronda_copa("Play-offs 1/8 Final", 1), ("1/8", 2))
        self.assertEqual(fuentes._ronda_copa("Play-offs 1/4 Final", 1), ("1/4", 3))
        self.assertEqual(fuentes._ronda_copa("Semifinal", 1), ("Semifinal", 4))
        self.assertEqual(fuentes._ronda_copa("Final", 1), ("Final", 5))

    def test_grupo_desconocido_no_inventa_ronda(self):
        with self.assertRaises(ValueError):
            fuentes._ronda_copa('FASE DE GRUPOS "A"', 1)


class TestSelects(unittest.TestCase):
    def test_grupo_no_lee_el_select_de_jornadas(self):
        html = """<select id="x_gruposDropDownList">
        <option value="1">Play-offs 1/8 Final</option></select>
        <select id="x_jornadasDropDownList">
        <option selected="selected">Jornada 1(17/11/2026)</option></select>"""
        self.assertEqual(fuentes._grupo_copa(html), "Play-offs 1/8 Final")

    def test_grupo_ambiguo_falla(self):
        html = """<select id="x_gruposDropDownList">
        <option>Play-offs 1/8 Final</option>
        <option>Play-offs 1/4 Final</option></select>"""
        with self.assertRaises(ValueError):
            fuentes._grupo_copa(html)


class TestPendiente(unittest.TestCase):
    def test_variantes(self):
        self.assertTrue(fuentes._es_pendiente("Por determinar 19:00"))
        self.assertTrue(fuentes._es_pendiente("APLAZADO"))
        self.assertFalse(fuentes._es_pendiente("78-65"))


class TestParseLiga(unittest.TestCase):
    def test_fecha_con_nbsp(self):
        p = fuentes.parse_liga(LIGA_FECHA, CONFIG)[0]
        self.assertEqual(p["inicio_madrid"], "2026-10-25T18:00:00")
        self.assertEqual(p["jornada"], 1)
        self.assertTrue(p["casa"])
        self.assertEqual(p["estado"], "pendiente")
        self.assertNotIn("fecha_provisional", p)

    def test_fecha_con_guiones_no_se_lee_como_marcador(self):
        html = LIGA_FECHA.replace("25/10/2026&nbsp;<br/>18:00", "25-10-2026<br/>18:00")
        p = fuentes.parse_liga(html, CONFIG)[0]
        self.assertEqual(p["inicio_madrid"], "2026-10-25T18:00:00")
        self.assertEqual(p["estado"], "pendiente")

    def test_jugado_marca_hora_provisional(self):
        p = fuentes.parse_liga(LIGA_JUGADO, CONFIG)[0]
        self.assertEqual(p["estado"], "jugado")
        self.assertEqual((p["resultado_equipo"], p["resultado_rival"]), (80, 70))
        self.assertTrue(p["victoria"])
        self.assertTrue(p.get("fecha_provisional"))

    def test_duplicado_prefiere_jugado(self):
        html = LIGA_JUGADO.replace(
            "</table>",
            """<tr>
  <td><a href="Equipo.aspx?i=1010493">ESTU</a></td>
  <td><a href="Equipo.aspx?i=111">RIVAL</a></td>
  <td class="fecha"><a>25/10/2026<br/>18:00</a></td>
  <td><a href="Partido.aspx?p=123">x</a></td>
</tr></table>""",
        )
        p = fuentes.parse_liga(html, CONFIG)[0]
        self.assertEqual(p["estado"], "jugado")
        self.assertEqual((p["resultado_equipo"], p["resultado_rival"]), (80, 70))

    def test_otra_configuracion_no_reutiliza_uids_ni_equipo(self):
        otro = replace(
            CONFIG,
            equipo_id="999",
            equipo_corto="Otro",
            uid_prefix="otro-2627",
            uid_dominio="otro-calendario",
        )
        p = fuentes.parse_liga(LIGA_JUGADO.replace("1010493", "999"), otro)[0]
        self.assertEqual(p["uid"], "otro-2627-j01@otro-calendario")
        self.assertEqual((p["resultado_equipo"], p["resultado_rival"]), (80, 70))


class TestParseCopa(unittest.TestCase):
    def test_tbd_usa_fecha_de_jornada(self):
        p = fuentes.parse_copa(COPA_TBD, CONFIG)[0]
        self.assertEqual(p["uid"], "estu-2627-copa-j02@estudiantes-calendario")
        self.assertEqual(p["ronda"], "1/8")
        self.assertEqual(p["estado"], "pendiente")
        self.assertEqual(p["inicio_madrid"], "2026-11-17T12:00:00")
        self.assertTrue(p["fecha_provisional"])
        self.assertFalse(p["casa"])

    def test_jugado(self):
        p = fuentes.parse_copa(COPA_JUGADO, CONFIG)[0]
        self.assertEqual(p["uid"], "estu-2627-copa-j01@estudiantes-calendario")
        self.assertEqual(p["ronda"], "1/16")
        self.assertEqual(p["estado"], "jugado")
        self.assertEqual((p["resultado_equipo"], p["resultado_rival"]), (86, 76))
        self.assertTrue(p["victoria"])
        self.assertNotIn("fecha_provisional", p)


if __name__ == "__main__":
    unittest.main()
