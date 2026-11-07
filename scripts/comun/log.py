"""Logs compatibles con GitHub Actions y con la ejecución local."""

from __future__ import annotations

import os


def _anotaciones_actions() -> bool:
    """No convertir avisos de tests en anotaciones ruidosas del workflow."""
    return os.environ.get("GITHUB_ACTIONS") == "true" and os.environ.get("CALENDARIOS_TEST") != "1"


def log(mensaje: str) -> None:
    print(mensaje, flush=True)


def warn(mensaje: str) -> None:
    # GitHub Actions interpreta esta línea como un aviso; en local se ve como texto.
    print(f"::warning::{mensaje}" if _anotaciones_actions() else f"AVISO: {mensaje}", flush=True)


def error(mensaje: str) -> None:
    print(f"::error::{mensaje}" if _anotaciones_actions() else f"ERROR: {mensaje}", flush=True)
