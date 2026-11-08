"""Tests de la fusión de fuentes y conservación de UIDs."""

from __future__ import annotations

import unittest

from scripts.comun import fusion


class TestFusion(unittest.TestCase):
    def _previo(self, **extra) -> dict:
        p = {
            "uid": "madrid-2627-5035860@madrid-calendario",
            "competicion": "champions",
            "casa": True,
            "rival": "Inter",
            "inicio_madrid": "2026-09-08T21:00",
            "uid_evento": "5035860",
        }
        p.update(extra)
        return p

    def _nuevo(self, **extra) -> dict:
        p = {
            "uid": "madrid-2627-uefa-2047742@madrid-calendario",
            "competicion": "champions",
            "casa": True,
            "rival": "Internazionale",
            "inicio_madrid": "2026-09-08T21:00",
            "uid_evento": "2047742",
            "fuente": "uefa",
        }
        p.update(extra)
        return p

    def test_reutiliza_uid_del_estado(self):
        prev = [self._previo()]
        nuevos = fusion.fusionar(prev, [self._nuevo()])
        self.assertEqual(nuevos[0]["uid"], "madrid-2627-5035860@madrid-calendario")
        self.assertEqual(nuevos[0]["uid_evento"], "2047742")

    def test_no_fusiona_otra_competicion(self):
        prev = [self._previo()]
        nuevos = fusion.fusionar(prev, [self._nuevo(competicion="liga")])
        self.assertTrue(nuevos[0]["uid"].endswith("uefa-2047742@madrid-calendario"))

    def test_tolerancia_de_fecha(self):
        prev = [self._previo(inicio_madrid="2026-09-08T21:00")]
        nuevo = self._nuevo(inicio_madrid="2026-09-10T21:00")
        fusionado = fusion.fusionar(prev, [nuevo], tolerancia_dias=3)
        self.assertEqual(fusionado[0]["uid"], prev[0]["uid"])

        sin_fusion = fusion.fusionar(prev, [nuevo], tolerancia_dias=1)
        self.assertNotEqual(sin_fusion[0]["uid"], prev[0]["uid"])

    def test_fuera_de_casa_no_fusiona_con_rival_distinto(self):
        prev = [self._previo(casa=True, rival="Inter")]
        nuevos = fusion.fusionar(prev, [self._nuevo(casa=False, rival="Roma")])
        self.assertNotEqual(nuevos[0]["uid"], prev[0]["uid"])

    def test_sede_neutral_fusiona_si_rival_coincide(self):
        prev = [self._previo(casa=False, competicion="finalissima", rival="Argentina")]
        nuevo = self._nuevo(
            casa=True,
            competicion="finalissima",
            rival="Argentina",
            uid="espana-2026-uefa-2047745@espana-calendario",
        )
        fusionado = fusion.fusionar(prev, [nuevo])
        self.assertEqual(fusionado[0]["uid"], prev[0]["uid"])


class TestRecolectar(unittest.TestCase):
    def test_fallback_por_competicion(self):
        tm = [
            {"competicion": "liga", "rival": "A", "uid": "tm-liga"},
            {"competicion": "champions", "rival": "B", "uid": "tm-ucl"},
        ]
        oficiales = [
            ("uefa", {"champions"}, lambda: [{"competicion": "champions", "uid": "uefa"}]),
        ]
        partidos = fusion.recolectar(tm, oficiales)
        uids = {p["uid"] for p in partidos}
        self.assertEqual(uids, {"tm-liga", "uefa"})

    def test_fallback_si_falla_oficial(self):
        tm = [{"competicion": "champions", "uid": "tm-ucl"}]

        def boom():
            raise RuntimeError("red")

        partidos = fusion.recolectar(tm, [("uefa", {"champions"}, boom)])
        self.assertEqual([p["uid"] for p in partidos], ["tm-ucl"])

    def test_error_si_no_hay_nada(self):
        with self.assertRaises(ValueError):
            fusion.recolectar(None, [])

    def test_deduplica_misma_fecha(self):
        oficial = {
            "competicion": "champions",
            "casa": True,
            "rival": "Inter",
            "inicio_madrid": "2026-09-08T21:00",
            "uid": "uefa",
        }
        tm = dict(oficial, uid="tm", rival="Internazionale Milano")
        partidos = fusion.recolectar([tm], [("uefa", {"champions"}, lambda: [oficial])])
        self.assertEqual([p["uid"] for p in partidos], ["uefa"])


if __name__ == "__main__":
    unittest.main()
