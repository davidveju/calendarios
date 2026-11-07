"""Runner que ejecuta calendarios en subprocesos independientes.

Un fallo en un calendario se registra y se continúa con el siguiente. En GitHub
Actions cada calendario tiene además su propio workflow, así que un fallo local
nunca bloquea a los demás.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path

from calendarios.log import error, log, warn
from calendarios.registro import Calendario
from calendarios.validacion import validar_ics


@dataclass(frozen=True)
class Resultado:
    calendario: Calendario
    ok: bool
    duracion: float
    detalle: str = ""


def _validar_salidas(calendario: Calendario) -> list[str]:
    errores: list[str] = []
    if not calendario.ruta_ics.exists():
        errores.append(f"no se generó {calendario.ruta_ics}")
    else:
        errores.extend(validar_ics(calendario.ruta_ics))

    for rel in calendario.datos:
        ruta = calendario.directorio / rel
        if ruta.suffix != ".json" or not ruta.exists():
            continue
        try:
            json.loads(ruta.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            errores.append(f"JSON inválido {ruta}: {e}")
    return errores


def ejecutar_calendario(
    calendario: Calendario,
    raiz: Path,
    *,
    timeout: int = 1800,
) -> Resultado:
    """Ejecuta el generador de un calendario y valida sus salidas."""
    comando = [sys.executable, "-m", calendario.modulo]
    entorno = os.environ.copy()
    entorno["PYTHONUNBUFFERED"] = "1"
    entorno["CALENDARIO_ID"] = calendario.id
    inicio = time.monotonic()
    log("")
    log(f"==> {calendario.id} · {calendario.nombre}")
    log(f"    {' '.join(comando)}")

    try:
        proceso = subprocess.run(
            comando,
            cwd=raiz,
            env=entorno,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired:
        duracion = time.monotonic() - inicio
        error(f"{calendario.id}: tiempo agotado tras {timeout}s")
        return Resultado(calendario, False, duracion, f"timeout de {timeout}s")
    except OSError as e:
        duracion = time.monotonic() - inicio
        error(f"{calendario.id}: no se pudo ejecutar el generador: {e}")
        return Resultado(calendario, False, duracion, str(e))

    salida = (proceso.stdout or "") + (proceso.stderr or "")
    for linea in salida.rstrip().splitlines():
        print(f"[{calendario.id}] {linea}")

    duracion = time.monotonic() - inicio
    if proceso.returncode != 0:
        detalle = f"el generador terminó con código {proceso.returncode}"
        error(f"{calendario.id}: {detalle}")
        return Resultado(calendario, False, duracion, detalle)

    errores = _validar_salidas(calendario)
    if errores:
        for mensaje in errores:
            error(f"{calendario.id}: {mensaje}")
        return Resultado(calendario, False, duracion, "; ".join(errores))

    log(f"    OK en {duracion:.1f}s · {calendario.ruta_ics.relative_to(raiz)}")
    return Resultado(calendario, True, duracion)


def ejecutar_calendarios(
    calendarios: list[Calendario],
    raiz: Path,
    *,
    timeout: int = 1800,
) -> int:
    """Ejecuta todos los calendarios y devuelve 1 si alguno falló."""
    if not calendarios:
        warn("no hay calendarios que ejecutar")
        return 1

    resultados: list[Resultado] = []
    for calendario in calendarios:
        try:
            resultados.append(ejecutar_calendario(calendario, raiz, timeout=timeout))
        except Exception as e:  # noqa: BLE001 - un calendario no debe tumbar el resto
            error(f"{calendario.id}: error inesperado: {e}")
            resultados.append(Resultado(calendario, False, 0.0, str(e)))

    log("")
    log("==> Resumen")
    for resultado in resultados:
        estado = "OK" if resultado.ok else "FALLO"
        detalle = f" · {resultado.detalle}" if resultado.detalle else ""
        log(f"    {estado:<5} {resultado.calendario.id:<28} {resultado.duracion:6.1f}s{detalle}")

    fallos = [r for r in resultados if not r.ok]
    if fallos:
        error(f"{len(fallos)} de {len(resultados)} calendario(s) fallaron")
        return 1
    log(f"{len(resultados)} calendario(s) actualizados correctamente")
    return 0
