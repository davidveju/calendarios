"""Logs compatibles con GitHub Actions y con la ejecución local."""

from __future__ import annotations


def log(mensaje: str) -> None:
    print(mensaje, flush=True)


def warn(mensaje: str) -> None:
    # GitHub Actions interpreta esta línea como un aviso; en local se ve como texto.
    print(f"::warning::{mensaje}", flush=True)


def error(mensaje: str) -> None:
    print(f"::error::{mensaje}", flush=True)
