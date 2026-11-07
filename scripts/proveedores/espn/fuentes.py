"""Parsea fuentes de fútbol vía la API pública por día de ESPN.

No se usan créditos ni claves: el endpoint estándar ``site.api.espn.com``
devuelve los partidos de un día en JSON. Un calendario de liga entero sale de

  1. pedir la vista sin fecha y leer ``leagues[0].calendar`` (fechas del año), y
  2. pedir el scoreboard con cada fecha.

El parser es genérico: recibe una :class:`ConfigESPN` con el equipo, la
competición y el prefijo de UIDs. No escribe ficheros.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

MADRID = ZoneInfo("Europe/Madrid")
ESPN_BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer"


def _score(competitor: dict, jugado: bool) -> int | None:
    raw = competitor.get("score")
    if not jugado or raw is None:
        return None
    try:
        return int(float(raw))
    except (TypeError, ValueError):
        return None


def _mandrid(dt_iso: str) -> str:
    """Convierte un timestamp ISO con 'Z' en texto 'naive' de Madrid."""
    raw = (dt_iso or "").strip()
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(MADRID).replace(tzinfo=None).isoformat(timespec="minutes")


def _acta_url(event: dict) -> str:
    for link in event.get("links") or []:
        if link.get("rel") and "summary" in link.get("rel", []):
            href = link.get("href")
            if href:
                return href
    event_id = str(event.get("id", "")).strip()
    if event_id:
        return f"https://www.espn.com/soccer/match/_/gameId/{event_id}"
    return ""


def _sede(comp: dict) -> dict | None:
    venue = comp.get("venue") or {}
    nombre = (venue.get("fullName") or "").strip()
    addr = venue.get("address") or {}
    city = (addr.get("city") or "").strip()
    country = (addr.get("country") or "").strip()
    trozos = [x for x in (city, country) if x]
    direccion = ", ".join(trozos)
    if not nombre and not direccion:
        return None
    return {"pabellon": nombre, "direccion": direccion}


def normalizar_evento(evento: dict, config) -> dict | None:
    """Convierte un evento ESPN en dict normalizado si interviene nuestro equipo."""

    competicion = (evento.get("competitions") or [{}])[0]
    competitors = competicion.get("competitors") or []
    nuestro = None
    rival = None
    for c in competitors:
        team = c.get("team") or {}
        team_id = team.get("id")
        if team_id is None:
            team_id = c.get("id")
        if str(team_id) == str(config.team_id):
            nuestro = c
        else:
            rival = c
    if nuestro is None:
        return None

    status = (competicion.get("status") or evento.get("status") or {}).get("type", {}) or {}
    jugado = bool(status.get("completed"))
    try:
        state_txt = (status.get("name") or "").upper()
    except Exception:
        state_txt = ""
    if "POSTPON" in state_txt or "CANCEL" in state_txt:
        jugado = False

    home_away = nuestro.get("homeAway")
    casa = home_away == "home"
    rival_name = ((rival or {}).get("team") or {}).get("displayName") or "Rival"

    event_id = str(evento.get("id", "")).strip()
    uid = f"{config.uid_prefix}-e{event_id}@{config.uid_dominio}"

    equipo_score = _score(nuestro, jugado)
    rival_score = _score(rival or {}, jugado)
    estado = "jugado" if jugado else "pendiente"
    victoria = None
    if jugado and equipo_score is not None and rival_score is not None:
        victoria = equipo_score > rival_score

    data = {
        "uid": uid,
        "competicion": "liga",
        "competicion_nombre": f"{config.liga_nombre} {config.temporada}",
        "estado": estado,
        "casa": casa,
        "rival": rival_name,
        "inicio_madrid": _mandrid(evento.get("date") or competicion.get("date", "")),
        "uid_evento": event_id,
        "acta": _acta_url(evento),
        "sede": _sede(competicion) or {},
    }
    if victoria is not None:
        data["victoria"] = victoria
    if jugado and equipo_score is not None and rival_score is not None:
        data["resultado_equipo"] = equipo_score
        data["resultado_rival"] = rival_score
        if casa:
            data["resultado_local"] = equipo_score
            data["resultado_visitante"] = rival_score
        else:
            data["resultado_local"] = rival_score
            data["resultado_visitante"] = equipo_score
    return data


def extraer_eventos(payload: str, config) -> list[dict]:
    """Extrae los partidos de nuestro equipo de un payload de scoreboard ESPN."""

    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return []
    eventos = data.get("events") or []
    resultado = []
    for ev in eventos:
        n = normalizar_evento(ev, config)
        if n is not None:
            resultado.append(n)
    return resultado


def fechas_calendario(payload: str) -> list[str]:
    """Extrae las fechas (YYYYMMDD) del calendario de una liga."""
    try:
        data = json.loads(payload)
    except (TypeError, ValueError):
        return []
    out: list[str] = []
    vistas: set[str] = set()
    for league in (data.get("leagues") or [{}]):
        cal = league.get("calendar") or []
        for entry in cal:
            iso = entry if isinstance(entry, str) else (entry or {}).get("startDate")
            if not iso or not isinstance(iso, str):
                continue
            compacto = iso.replace("-", "")[:8]
            if len(compacto) == 8 and compacto not in vistas:
                vistas.add(compacto)
                out.append(compacto)
    return out
