"""Escritura atómica de ficheros generados."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def escritura_atomica(path: Path, data: bytes) -> None:
    """Escribe ``data`` en ``path`` sin dejar el fichero a medias si hay un fallo."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f".{path.name}.tmp")
    try:
        tmp.write_bytes(data)
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def escribir_json(path: Path, datos: Any) -> None:
    """Serializa JSON estable (UTF-8, indentado, claves ordenadas) de forma atómica."""
    texto = json.dumps(datos, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    escritura_atomica(path, texto.encode("utf-8"))
