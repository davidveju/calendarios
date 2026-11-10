"""Resultados y calendario desde la API pública de LALIGA (fuente oficial).

``laliga.com`` publica los partidos en ``__NEXT_DATA__`` y los sirve vía
``apim.laliga.com/public-service`` con la clave de suscripción que la propia
web expone en el HTML. Este proveedor extrae esa clave en cada ejecución
(aguanta rotaciones) y descarga cada competición con una sola petición por
equipo (``teamSlug`` + ``limit``), sin depender de Transfermarkt ni de ESPN.

Es la fuente primaria de Liga y Copa en los calendarios de fútbol: los datos
son los oficiales (jornada, hora, resultado, estadio). Si falla, los
generadores recurren a Transfermarkt y después a ESPN; la fusión conserva los
UIDs históricos en cualquier caso.

El proveedor no conoce equipos concretos; solo un :class:`ConfigLaLiga`.
"""

from __future__ import annotations

import json as _json
import re
from datetime import datetime
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
FUENTE = "laliga"

KEY_URL = "https://www.laliga.com/en-GB/laliga-easports/results"
APIM = "https://apim.laliga.com/public-service/api/v1/matches"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124 Safari/537.36"
)
HEADERS = {"Referer": "https://www.laliga.com/"}

ESTADO_JUGADO = {"FullTime"}
ESTADO_APLAZADO = {"Postponed", "Suspended", "Cancelled", "Abandoned"}


def _temporada_anio(temporada: str) -> str:
    """``"26/27"`` -> ``"2026"`` (año de inicio, el que usa el subscriptionSlug)."""
    return str(2000 + int(temporada.split("/")[0]))


def extraer_clave(html: str) -> str:
    """Saca la ``backendSubscription`` del ``__NEXT_DATA__`` de laliga.com."""
    m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>', html or "", re.S)
    if m:
        try:
            data = _json.loads(m.group(1))
            clave = (
                (data.get("props", {}).get("pageProps", {}) or {})
                if isinstance(data, dict)
                else {}
            )
            runtime = data.get("runtimeConfig", {}) if isinstance(data, dict) else {}
            if isinstance(runtime, dict) and runtime.get("backendSubscription"):
                return str(runtime["backendSubscription"])
        except (TypeError, ValueError):
            pass
    m = re.search(r'"backendSubscription"\s*:\s*"([a-f0-9]{16,})"', html or "")
    if not m:
        raise ValueError("laliga: no se encontró la clave en laliga.com")
    return m.group(1)


def obtener_clave(*, retries: int = 2, timeout: int = 30) -> str:
    """Descarga la página de resultados y devuelve su clave de suscripción."""
    from scripts.comun.http import fetch

    try:
        html = fetch(KEY_URL, user_agent=USER_AGENT, headers=HEADERS,
                     retries=retries, timeout=timeout)
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"laliga: no se pudo leer {KEY_URL} ({e})") from e
    return extraer_clave(html)


def _inicio_madrid(utc_raw: str) -> tuple[str, bool]:
    """Devuelve (ISO Madrid sin tz, provisional). 00:00 = hora sin confirmar."""
    dt = datetime.fromisoformat(str(utc_raw).replace("Z", "+00:00"))
    provisional = dt.hour == 0 and dt.minute == 0
    inicio = dt.astimezone(MADRID).replace(tzinfo=None)
    if provisional:
        return inicio.date().isoformat() + "T12:00", True
    return inicio.isoformat(timespec="minutes"), False


def _rival(nickname: str) -> str:
    nombre = str(nickname or "").strip()
    if nombre.upper().endswith(" CF"):
        nombre = nombre[:-3].strip()
    return nombre


def parse_partido(match: dict, config, liga) -> dict | None:
    """Normaliza un partido de APIM. None si no es del equipo o sin fecha."""
    eid = match.get("id")
    if eid is None:
        return None
    home = match.get("home_team") or {}
    away = match.get("away_team") or {}
    if home.get("slug") == config.team_slug:
        casa, otro = True, away
    elif away.get("slug") == config.team_slug:
        casa, otro = False, home
    else:
        return None
    rival = _rival((otro.get("nickname") or otro.get("name")))
    if not rival:
        return None
    try:
        inicio, provisional = _inicio_madrid(match.get("date") or "")
    except (TypeError, ValueError):
        return None

    estado_raw = str(match.get("status") or "")
    if estado_raw in ESTADO_JUGADO:
        estado = "jugado"
    elif estado_raw in ESTADO_APLAZADO:
        estado = "aplazado"
    else:
        estado = "pendiente"

    gw = match.get("gameweek") or {}
    ronda = gw.get("name") if liga.codigo == "copa" else gw.get("week", "")
    ronda = "" if ronda is None else str(ronda)

    partido = {
        "uid": f"{config.uid_prefix}-{eid}@{config.uid_dominio}",
        "competicion": liga.codigo,
        "competicion_nombre": liga.nombre.format(temporada=config.temporada),
        "estado": estado,
        "casa": casa,
        "rival": rival,
        "inicio_madrid": inicio,
        "fecha_provisional": provisional,
        "uid_evento": str(eid),
        "fuente": FUENTE,
        "acta": liga.acta,
        "ronda": ronda,
    }
    venue = match.get("venue") or {}
    pabellon = str(venue.get("name") or "").strip()
    ciudad = str(venue.get("city") or "").strip()
    if pabellon or ciudad:
        sede = {}
        if pabellon:
            sede["pabellon"] = pabellon
        if ciudad:
            sede["ciudad"] = ciudad
        partido["sede"] = sede
    elif casa and config.casa_estadio:
        partido["sede"] = {"pabellon": config.casa_estadio}

    if estado == "jugado":
        try:
            res_local = int(match["home_score"])
            res_visit = int(match["away_score"])
        except (KeyError, TypeError, ValueError):
            return None
        if casa:
            victoria = res_local > res_visit
            equipo, rival_goles = res_local, res_visit
        else:
            victoria = res_visit > res_local
            equipo, rival_goles = res_visit, res_local
        partido.update(
            {
                "resultado_local": res_local,
                "resultado_visitante": res_visit,
                "resultado_equipo": equipo,
                "resultado_rival": rival_goles,
                "victoria": bool(victoria),
            }
        )
    return partido


def fetch_liga(config, liga, *, clave: str, retries: int = 2, timeout: int = 30) -> list[dict]:
    """Descarga una competición completa del equipo (una sola petición)."""
    from scripts.comun.http import fetch

    anio = _temporada_anio(config.temporada)
    url = (
        f"{APIM}?subscriptionSlug={liga.base}-{anio}"
        f"&teamSlug={config.team_slug}&limit=100"
    )
    try:
        datos = _json.loads(
            fetch(url, user_agent=USER_AGENT, headers={**HEADERS, "Ocp-Apim-Subscription-Key": clave},
                  retries=retries, timeout=timeout)
        )
    except Exception as e:  # noqa: BLE001
        raise ValueError(f"laliga {liga.base} falló ({e})") from e
    partidos = []
    for match in datos.get("matches") or []:
        p = parse_partido(match, config, liga)
        if p is not None:
            partidos.append(p)
    return partidos


def fetch_competiciones(config, *, clave: str | None = None) -> list[dict]:
    """Descarga todas las ligas de la config (falla si alguna falla)."""
    if clave is None:
        clave = obtener_clave()
    partidos: list[dict] = []
    for liga in config.ligas:
        partidos.extend(fetch_liga(config, liga, clave=clave))
    if not partidos:
        raise ValueError("laliga: no se obtuvo ningún partido")
    return partidos
