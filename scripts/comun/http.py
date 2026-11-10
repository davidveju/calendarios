"""Descargas HTTP con reintentos solo para fallos transitorios."""

from __future__ import annotations

import time
import urllib.error
import urllib.request

from scripts.comun.log import log

USER_AGENT = "Mozilla/5.0 (calendarios)"


class ErrorDescarga(RuntimeError):
    """La descarga no se pudo completar después de los reintentos."""


def _no_reintentable(e: Exception) -> bool:
    return (
        isinstance(e, urllib.error.HTTPError)
        and e.code not in (408, 425, 429, 500, 502, 503, 504)
    )


def fetch(
    url: str,
    *,
    retries: int = 3,
    timeout: int = 30,
    user_agent: str = USER_AGENT,
    headers: dict[str, str] | None = None,
) -> str:
    """Descarga ``url`` y devuelve el texto decodificado.

    Reintenta únicamente errores transitorios (red, timeout, 5xx, 429). Un 404
    falla en el primer intento para no perder tiempo. Se envían cabeceras de
    navegador (``Accept``, ``Accept-Language``) para que los sitios con
    protección anti-bots no devuelvan una página vacía; ``headers`` permite
    añadir o sobrescribir cabeceras (p. ej. ``Referer``).
    """
    cabeceras = {
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;q=0.9,"
            "application/json;q=0.8,*/*;q=0.7"
        ),
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "User-Agent": user_agent,
    }
    if headers:
        cabeceras.update(headers)
    ultimo: Exception | None = None
    for intento in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=cabeceras)
            with urllib.request.urlopen(req, timeout=timeout) as respuesta:
                charset = respuesta.headers.get_content_charset() or "utf-8"
                return respuesta.read().decode(charset, "replace")
        except Exception as e:  # noqa: BLE001 - se reintenta y se informa al final
            ultimo = e
            log(f"fetch {url}: intento {intento}/{retries} falló ({e})")
            if _no_reintentable(e) or intento >= retries:
                break
            time.sleep(2 * intento)
    raise ErrorDescarga(f"fetch: {url} falló tras {retries} intentos ({ultimo})")
