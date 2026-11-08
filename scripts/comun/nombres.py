"""Normalización de nombres de equipos para comparar fuentes distintas.

Las fuentes oficiales y Transfermarkt no siempre escriben igual el mismo rival
(``Atleti`` / ``Atlético de Madrid``, ``Cabo Verde`` / ``Islas de Cabo Verde``).
Estas funciones permiten comparar sin depender de la forma exacta.
"""

from __future__ import annotations

import re
import unicodedata

_SUFIJOS = re.compile(
    r"\b(c\.?f\.?|f\.?c\.?|club|de futbol|s\.?a\.?d\.?|u\.?d\.?|c\.?d\.?)\b"
)


def normalizar(texto: str) -> str:
    """Minúsculas, sin acentos, sin sufijos societarios y sin puntuación."""
    texto = unicodedata.normalize("NFKD", texto or "")
    texto = texto.encode("ascii", "ignore").decode("ascii").lower()
    texto = _SUFIJOS.sub(" ", texto)
    texto = re.sub(r"[^a-z0-9 ]", " ", texto)
    return " ".join(texto.split())


def similitud(a: str, b: str) -> float:
    """Similitud sencilla entre dos nombres (0..1).

    No pretende ser un algoritmo difuso: solo resuelve los casos habituales
    (nombre idéntico, un nombre contenido en otro o palabras en común).
    """
    a, b = normalizar(a), normalizar(b)
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0
    if a in b or b in a:
        return 0.9
    palabras_a, palabras_b = set(a.split()), set(b.split())
    if not palabras_a or not palabras_b:
        return 0.0
    return len(palabras_a & palabras_b) / len(palabras_a | palabras_b)
