"""Descubrimiento de calendarios bajo ``scripts/calendarios``."""

from __future__ import annotations

from pathlib import Path

from scripts.comun.contexto import (
    MANIFIESTO,
    Contexto,
    ErrorCalendario,
    cargar_contexto,
)
from scripts.comun.log import warn


def _base_codigo(raiz: Path) -> Path:
    return raiz / "scripts" / "calendarios"


def descubrir_calendarios(raiz: Path, *, estricto: bool = False) -> list[Contexto]:
    """Busca todos los ``calendario.json`` de ``scripts/calendarios``.

    En modo no estricto un manifiesto roto se avisa y se omite, para que no
    bloquee a los demás calendarios. ``estricto=True`` falla al primer error
    (útil en tests y en ``listar --estricto``).
    """
    raiz = raiz.resolve()
    base = _base_codigo(raiz)
    if not base.is_dir():
        return []

    calendarios: list[Contexto] = []
    for manifiesto in sorted(base.rglob(MANIFIESTO)):
        rel = manifiesto.parent.relative_to(base)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        try:
            calendarios.append(
                cargar_contexto(rel.as_posix(), manifiesto.parent, raiz)
            )
        except ErrorCalendario as e:
            if estricto:
                raise
            warn(f"calendario omitido ({rel.as_posix()}): {e}")
    return sorted(calendarios, key=lambda c: c.id)


def obtener_calendario(raiz: Path, calendario_id: str) -> Contexto:
    """Devuelve el calendario con ese ``id`` o falla con la lista de disponibles."""
    calendarios = descubrir_calendarios(raiz, estricto=False)
    for calendario in calendarios:
        if calendario.id == calendario_id:
            return calendario
    disponibles = ", ".join(c.id for c in calendarios) or "(ninguno)"
    raise ErrorCalendario(
        f"no existe el calendario {calendario_id!r}; disponibles: {disponibles}"
    )
