"""CLI del monorepo: ``python3 -m calendarios <comando>``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from calendarios import __version__
from calendarios.log import error, log, warn
from calendarios.registro import ErrorCalendario, descubrir_calendarios, obtener_calendario
from calendarios.runner import ejecutar_calendarios
from calendarios.validacion import validar_ics

RAIZ = Path(__file__).resolve().parent.parent


def _cmd_listar(args: argparse.Namespace) -> int:
    calendarios = descubrir_calendarios(RAIZ, estricto=args.estricto)
    if not calendarios:
        warn("no se encontró ningún calendario")
        return 0
    log(f"{'ID':<28} {'NOMBRE':<36} ICS")
    log("-" * 90)
    for calendario in calendarios:
        log(f"{calendario.id:<28} {calendario.nombre:<36} {calendario.ruta_ics.relative_to(RAIZ)}")
    return 0


def _cmd_actualizar(args: argparse.Namespace) -> int:
    seleccionados = []
    errores = 0
    if args.solo:
        for calendario_id in args.solo:
            try:
                seleccionados.append(obtener_calendario(RAIZ, calendario_id))
            except ErrorCalendario as e:
                error(str(e))
                errores += 1
    else:
        seleccionados = descubrir_calendarios(RAIZ, estricto=args.estricto)

    codigo = ejecutar_calendarios(seleccionados, RAIZ, timeout=args.timeout)
    return codigo or (1 if errores else 0)


def _cmd_validar(args: argparse.Namespace) -> int:
    rutas: list[Path] = []
    for valor in args.rutas:
        ruta = Path(valor)
        if ruta.is_dir():
            rutas.extend(sorted(ruta.rglob("*.ics")))
        elif ruta.exists():
            rutas.append(ruta)
        else:
            error(f"no existe {ruta}")
            return 1
    if not rutas:
        error("no se encontró ningún fichero .ics")
        return 1

    fallos = 0
    for ruta in rutas:
        problemas = validar_ics(ruta)
        if problemas:
            fallos += 1
            for problema in problemas:
                error(f"{ruta}: {problema}")
        else:
            lineas = ruta.read_bytes().count(b"\r\n")
            log(f"ICS OK: {ruta} ({lineas} líneas, plegado <=75 octetos, CRLF)")
    return 1 if fallos else 0


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python3 -m calendarios",
        description="Genera y valida los calendarios iCalendar del repositorio.",
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="comando", required=True)

    listar = sub.add_parser("listar", help="lista los calendarios disponibles")
    listar.add_argument("--estricto", action="store_true", help="falla si un manifiesto es inválido")
    listar.set_defaults(func=_cmd_listar)

    actualizar = sub.add_parser("actualizar", help="genera uno o todos los calendarios")
    actualizar.add_argument(
        "--solo",
        action="append",
        metavar="ID",
        help="actualiza solo este calendario (repetible), p. ej. deportes/baloncesto",
    )
    actualizar.add_argument("--timeout", type=int, default=1800, help="timeout por calendario (s)")
    actualizar.add_argument("--estricto", action="store_true", help="falla si un manifiesto es inválido")
    actualizar.set_defaults(func=_cmd_actualizar)

    validar = sub.add_parser("validar", help="valida ficheros o directorios .ics")
    validar.add_argument("rutas", nargs="+", help="ficheros .ics o directorios")
    validar.set_defaults(func=_cmd_validar)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
