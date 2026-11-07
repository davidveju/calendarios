"""Descubrimiento y validación de los manifiestos de cada calendario.

Un calendario vive en ``<categoría>/<nombre>/`` y se describe con
``calendario.json``. El ``id`` es la ruta relativa (``deportes/baloncesto``) y
debe ser un nombre de paquete Python válido para poder ejecutar su generador
con ``python3 -m <id>.generar``.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from calendarios.log import warn

ID_RE = re.compile(r"^[a-z][a-z0-9_]*(/[a-z][a-z0-9_]*)*$")
MODULO_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MANIFIESTO = "calendario.json"


class ErrorCalendario(ValueError):
    """Manifiesto o estructura de calendario incorrectos."""


@dataclass(frozen=True)
class Calendario:
    id: str
    directorio: Path
    nombre: str
    descripcion: str
    fichero_ics: str
    generador: str
    datos: tuple[str, ...]
    zona: str

    @property
    def ruta_ics(self) -> Path:
        return self.directorio / self.fichero_ics

    @property
    def modulo(self) -> str:
        return f"{self.id.replace('/', '.')}.{Path(self.generador).stem}"


def _texto(datos: dict, clave: str, *, obligatorio: bool = False, defecto: str = "") -> str:
    valor = datos.get(clave, defecto)
    if not isinstance(valor, str):
        raise ErrorCalendario(f"{clave} debe ser un texto")
    valor = valor.strip()
    if obligatorio and not valor:
        raise ErrorCalendario(f"falta {clave}")
    return valor


def _ruta_relativa(valor: str, campo: str) -> str:
    ruta = Path(valor)
    if ruta.is_absolute() or ".." in ruta.parts or not ruta.parts:
        raise ErrorCalendario(f"{campo} debe ser una ruta relativa dentro del calendario: {valor!r}")
    return ruta.as_posix()


def cargar_calendario(directorio: Path, raiz: Path) -> Calendario:
    """Lee y valida ``directorio/calendario.json``."""
    try:
        datos = json.loads((directorio / MANIFIESTO).read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ErrorCalendario(f"no existe {directorio / MANIFIESTO}") from e
    except (OSError, json.JSONDecodeError) as e:
        raise ErrorCalendario(f"{directorio / MANIFIESTO} ilegible: {e}") from e
    if not isinstance(datos, dict):
        raise ErrorCalendario(f"{directorio / MANIFIESTO} debe contener un objeto JSON")

    rel = directorio.resolve().relative_to(raiz.resolve()).as_posix()
    if not ID_RE.fullmatch(rel):
        raise ErrorCalendario(
            f"id de calendario no válido: {rel!r}; usa minúsculas, números y guiones bajos "
            "(por ejemplo deportes/baloncesto)"
        )

    nombre = _texto(datos, "nombre", obligatorio=True)
    descripcion = _texto(datos, "descripcion")
    fichero_ics = _texto(datos, "ics", defecto="calendario.ics")
    if Path(fichero_ics).name != fichero_ics or not fichero_ics.endswith(".ics"):
        raise ErrorCalendario(f"ics debe ser un nombre de fichero .ics: {fichero_ics!r}")

    generador = _ruta_relativa(_texto(datos, "generador", defecto="generar.py"), "generador")
    if Path(generador).suffix != ".py" or not MODULO_RE.fullmatch(Path(generador).stem):
        raise ErrorCalendario(f"generador debe ser un módulo Python: {generador!r}")
    if not (directorio / generador).is_file():
        raise ErrorCalendario(f"no existe el generador {directorio / generador}")

    datos_raw = datos.get("datos", [])
    if not isinstance(datos_raw, list) or not all(isinstance(x, str) for x in datos_raw):
        raise ErrorCalendario("datos debe ser una lista de rutas relativas")
    datos_rel = tuple(_ruta_relativa(x, "datos") for x in datos_raw)

    zona = _texto(datos, "zona", defecto="Europe/Madrid")
    try:
        ZoneInfo(zona)
    except ZoneInfoNotFoundError as e:
        raise ErrorCalendario(f"zona horaria desconocida: {zona!r}") from e

    return Calendario(
        id=rel,
        directorio=directorio,
        nombre=nombre,
        descripcion=descripcion,
        fichero_ics=fichero_ics,
        generador=generador,
        datos=datos_rel,
        zona=zona,
    )


def descubrir_calendarios(raiz: Path, *, estricto: bool = False) -> list[Calendario]:
    """Busca todos los ``calendario.json`` del repositorio.

    En modo no estricto un manifiesto roto se avisa y se omite, para que no
    bloquee a los demás calendarios. ``estricto=True`` falla al primer error
    (útil en tests y en el comando ``listar --estricto``).
    """
    raiz = raiz.resolve()
    calendarios: list[Calendario] = []
    for manifiesto in sorted(raiz.rglob(MANIFIESTO)):
        rel = manifiesto.relative_to(raiz)
        if any(part.startswith(".") or part == "__pycache__" for part in rel.parts):
            continue
        try:
            calendarios.append(cargar_calendario(manifiesto.parent, raiz))
        except ErrorCalendario as e:
            if estricto:
                raise
            warn(f"calendario omitido ({rel}): {e}")
    return sorted(calendarios, key=lambda c: c.id)


def obtener_calendario(raiz: Path, calendario_id: str) -> Calendario:
    """Devuelve el calendario con ese ``id`` o falla con la lista de disponibles."""
    calendarios = descubrir_calendarios(raiz, estricto=False)
    for calendario in calendarios:
        if calendario.id == calendario_id:
            return calendario
    disponibles = ", ".join(c.id for c in calendarios) or "(ninguno)"
    raise ErrorCalendario(f"no existe el calendario {calendario_id!r}; disponibles: {disponibles}")
