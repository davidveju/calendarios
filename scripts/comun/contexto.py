"""Contexto de un calendario: código, manifiesto y rutas de salida.

Convención del repo:

- **Código:** ``scripts/calendarios/<id>/``.
- **Datos/caché y .ics publicado:** ``<id>/`` en la raíz del repositorio.

El ``id`` (por ejemplo ``deportes/baloncesto``) es la única clave que une ambas
rutas. Así cada calendario tiene su propio espacio de nombres y dos calendarios
nunca comparten ficheros de estado por accidente.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

ID_RE = re.compile(r"^[a-z][a-z0-9_]*(/[a-z][a-z0-9_]*)*$")
MODULO_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
MANIFIESTO = "calendario.json"
PREFIJO_MODULO = "scripts.calendarios."

RAIZ_REPO = Path(__file__).resolve().parents[2]
RAIZ_CODIGO = RAIZ_REPO / "scripts" / "calendarios"


class ErrorCalendario(ValueError):
    """Manifiesto o estructura de calendario incorrectos."""


@dataclass(frozen=True)
class Contexto:
    """Todo lo que un calendario necesita saber de sí mismo."""

    id: str
    raiz: Path
    codigo: Path
    salida: Path
    nombre: str
    descripcion: str
    fichero_ics: str
    generador: str
    datos: tuple[str, ...]
    zona: str

    @property
    def ruta_ics(self) -> Path:
        return self.salida / self.fichero_ics

    def ruta_dato(self, relativa: str) -> Path:
        return self.salida / relativa

    @property
    def datos_json(self) -> tuple[str, ...]:
        return tuple(d for d in self.datos if Path(d).suffix == ".json")

    @property
    def modulo(self) -> str:
        return f"{PREFIJO_MODULO}{self.id.replace('/', '.')}.{Path(self.generador).stem}"


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
        raise ErrorCalendario(
            f"{campo} debe ser una ruta relativa dentro del calendario: {valor!r}"
        )
    return ruta.as_posix()


def _base_codigo(raiz: Path) -> Path:
    return raiz / "scripts" / "calendarios"


def cargar_contexto(calendario_id: str, directorio_codigo: Path, raiz: Path) -> Contexto:
    """Carga y valida ``directorio_codigo/calendario.json``."""
    if not ID_RE.fullmatch(calendario_id):
        raise ErrorCalendario(
            f"id de calendario no válido: {calendario_id!r}; usa minúsculas, números "
            "y guiones bajos (por ejemplo deportes/baloncesto)"
        )

    raiz = raiz.resolve()
    directorio_codigo = directorio_codigo.resolve()
    try:
        rel = directorio_codigo.relative_to(_base_codigo(raiz).resolve()).as_posix()
    except ValueError as e:
        raise ErrorCalendario(
            f"el código debe estar dentro de scripts/calendarios/: {directorio_codigo}"
        ) from e
    if rel != calendario_id:
        raise ErrorCalendario(
            f"el id {calendario_id!r} no coincide con la ruta de código {rel!r}"
        )

    manifiesto = directorio_codigo / MANIFIESTO
    try:
        datos = json.loads(manifiesto.read_text(encoding="utf-8"))
    except FileNotFoundError as e:
        raise ErrorCalendario(f"no existe {manifiesto}") from e
    except (OSError, json.JSONDecodeError) as e:
        raise ErrorCalendario(f"{manifiesto} ilegible: {e}") from e
    if not isinstance(datos, dict):
        raise ErrorCalendario(f"{manifiesto} debe contener un objeto JSON")

    nombre = _texto(datos, "nombre", obligatorio=True)
    descripcion = _texto(datos, "descripcion")
    fichero_ics = _texto(datos, "ics", defecto="calendario.ics")
    if Path(fichero_ics).name != fichero_ics or not fichero_ics.endswith(".ics"):
        raise ErrorCalendario(f"ics debe ser un nombre de fichero .ics: {fichero_ics!r}")

    generador = _ruta_relativa(
        _texto(datos, "generador", defecto="generar.py"), "generador"
    )
    if Path(generador).suffix != ".py" or not MODULO_RE.fullmatch(Path(generador).stem):
        raise ErrorCalendario(f"generador debe ser un módulo Python: {generador!r}")
    if not (directorio_codigo / generador).is_file():
        raise ErrorCalendario(f"no existe el generador {directorio_codigo / generador}")

    datos_raw = datos.get("datos", [])
    if not isinstance(datos_raw, list) or not all(isinstance(x, str) for x in datos_raw):
        raise ErrorCalendario("datos debe ser una lista de rutas relativas")
    datos_rel = tuple(_ruta_relativa(x, "datos") for x in datos_raw)

    zona = _texto(datos, "zona", defecto="Europe/Madrid")
    try:
        ZoneInfo(zona)
    except ZoneInfoNotFoundError as e:
        raise ErrorCalendario(f"zona horaria desconocida: {zona!r}") from e

    return Contexto(
        id=calendario_id,
        raiz=raiz,
        codigo=directorio_codigo,
        salida=raiz / calendario_id,
        nombre=nombre,
        descripcion=descripcion,
        fichero_ics=fichero_ics,
        generador=generador,
        datos=datos_rel,
        zona=zona,
    )


def contexto(calendario_id: str, raiz: Path = RAIZ_REPO) -> Contexto:
    """Carga un calendario por su id."""
    raiz = raiz.resolve()
    return cargar_contexto(calendario_id, _base_codigo(raiz) / calendario_id, raiz)


def id_desde_modulo(modulo: str) -> str:
    """``scripts.calendarios.deportes.baloncesto.generar`` -> ``deportes/baloncesto``."""
    if not modulo.startswith(PREFIJO_MODULO):
        raise ErrorCalendario(f"módulo fuera de scripts.calendarios: {modulo!r}")
    partes = modulo[len(PREFIJO_MODULO) :].split(".")
    if len(partes) < 2:
        raise ErrorCalendario(f"módulo de calendario incompleto: {modulo!r}")
    return "/".join(partes[:-1])


def contexto_desde_modulo(modulo: str, raiz: Path = RAIZ_REPO) -> Contexto:
    """Carga el contexto del calendario desde el ``__name__`` de su generador."""
    calendario_id = id_desde_modulo(modulo)
    ctx = contexto(calendario_id, raiz)
    if Path(ctx.generador).stem != modulo.rsplit(".", 1)[-1]:
        raise ErrorCalendario(
            f"el generador {ctx.generador!r} no coincide con el módulo {modulo!r}"
        )
    return ctx


def contexto_desde_ejecucion(
    modulo: str,
    fichero: str | Path,
    raiz: Path = RAIZ_REPO,
) -> Contexto:
    """Contexto del generador, tanto con ``python -m`` como ejecutándolo directo.

    Con ``python -m`` el módulo ya es ``scripts.calendarios.<id>.<generador>``.
    Al ejecutar el fichero, ``__name__`` es ``__main__`` y el id se deduce de la
    ruta ``scripts/calendarios/<id>/<generador>.py``.
    """
    if modulo != "__main__":
        return contexto_desde_modulo(modulo, raiz)

    fichero = Path(fichero).resolve()
    raiz = raiz.resolve()
    try:
        rel = fichero.parent.relative_to(_base_codigo(raiz).resolve()).as_posix()
    except ValueError as e:
        raise ErrorCalendario(
            f"el generador debe estar dentro de scripts/calendarios/: {fichero}"
        ) from e
    ctx = cargar_contexto(rel, fichero.parent, raiz)
    if Path(ctx.generador).name != fichero.name:
        raise ErrorCalendario(
            f"el generador {ctx.generador!r} no coincide con {fichero.name!r}"
        )
    return ctx
