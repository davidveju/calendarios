"""Proveedor ACB/Liga Endesa: calendario, resultados y sedes.

Obtiene partidos vía ``api2.acb.com`` (``team-matches``) y, opcionalmente,
enriquece la sede de cada partido con el pabellón del equipo local
(``homeTeam.clubId``) a partir del JSON-LD de la ficha de club en acb.com.
Las sedes son un enriquecimiento opcional: los generadores deben cachearlas
y no fallar si no se pueden resolver.
"""

from __future__ import annotations

import os

import html as _html
import re

MESES = {
    "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
    "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
    "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
}


def _limpia(s: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", " ", s)).replace("\\u0026", "&").strip()


def _normalizar(texto: str) -> str:
    return texto.encode("latin-1", "backslashreplace").decode("unicode_escape") if False else texto


def parse_arena(html: str) -> dict:
    """Extrae el pabellón de una ficha de equipo de acb.com (JSON-LD).

    Devuelve ``{"pabellon": ..., "direccion": ...}`` con las claves
    disponibles, o ``{}`` si no se puede determinar.
    """
    import json as _json

    for m in re.finditer(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html,
        re.S | re.I,
    ):
        try:
            data = _json.loads(m.group(1))
        except Exception:  # noqa: BLE001 - JSON-LD ajeno
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            loc = item.get("location")
            if not isinstance(loc, dict):
                continue
            nombre = str(loc.get("name") or "").strip()
            if not nombre:
                continue
            arena: dict = {"pabellon": _html.unescape(nombre)}
            addr = loc.get("address")
            if isinstance(addr, dict):
                calle = str(addr.get("streetAddress") or "").strip()
                if calle:
                    arena["direccion"] = _html.unescape(calle)
            return arena
    return {}


def fetch_arena(club_id: int, *, retries: int = 2, timeout: int = 20) -> dict:
    """Descarga la ficha de equipo de acb.com y devuelve su pabellón."""
    from scripts.comun.http import fetch

    url = f"https://www.acb.com/es/liga/equipos/{club_id}"
    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36"
    try:
        return parse_arena(fetch(url, user_agent=ua, retries=retries, timeout=timeout))
    except Exception as e:  # noqa: BLE001 - la sede es opcional
        raise ValueError(f"arena acb club {club_id} falló ({e})") from e


def extraer_partidos(html: str, config) -> list[dict]:
    texto = _limpia(html)
    # Entradas: **FECHA**. EQUIPO - EQUIPO, (con posibles comas dentro)
    dia_names = "lunes|martes|miércoles|jueves|viernes|sábado|domingo"
    patron = re.compile(
        rf"\*\*(?P<fecha>(?:{dia_names})[^*]+?\([^)]*\))\*\*\s*\.?\s*(?P<match>.+?)(?=\s*-\s*\*\*|\Z)",
        re.I | re.S,
    )
    partidos: list[dict] = []
    for m in patron.finditer(texto):
        fecha_raw = m.group("fecha").strip()
        match_txt = m.group("match").replace("\\r", " ").replace("\\n", " ")
        match_txt = _limpia(match_txt)
        match_txt = re.sub(r"###.*", "", match_txt).strip(" -·")
        match_txt = re.sub(r"\s+", " ", match_txt)
        if config.team_name not in match_txt:
            continue

        # día(s) / mes
        mfecha = re.search(
            r"(\d{1,2})(?:/\d+)*\s+de\s+(\w+)(?:\s+de\s+(\d{4}))?",
            fecha_raw,
            re.I,
        )
        if not mfecha:
            continue
        dias = [int(x) for x in re.findall(r"\d{1,2}", mfecha.group(1))]
        dia = dias[0] if dias else 1
        mes_txt = mfecha.group(2).lower()
        mes = MESES.get(mes_txt)
        if mes is None:
            continue
        anio = mfecha.group(3)
        if anio is None:
            anio_int = 2026 if mes >= 9 else 2027
        else:
            anio_int = int(anio)

        # hora
        mhora = re.search(r"\(([^)]*)\)", fecha_raw)
        hora_txt = (mhora.group(1) if mhora else "").strip()
        provisional = "sin confirmar" in hora_txt.lower() or hora_txt == "Horario sin confirmar"
        mtime = re.search(r"(\d{1,2}):(\d{2})", hora_txt)
        if mtime and not provisional:
            hh, mm = mtime.group(1), mtime.group(2)
            kickoff = f"{anio_int:04d}-{mes:02d}-{dia:02d}T{int(hh):02d}:{int(mm):02d}"
        else:
            kickoff = f"{anio_int:04d}-{mes:02d}-{dia:02d}T12:00"
            provisional = True

        # rivales
        match_txt = _html.unescape(match_txt).strip(" .-")
        _limpiar = lambda x: re.sub(r"\s+", " ", x.replace("\\r", " ").replace("\\n", " ").strip())
        partes = [_limpiar(x.strip()) for x in match_txt.split(" - ")]
        if len(partes) != 2:
            partes = [_limpiar(x.strip()) for x in re.split(r"\s+-\s+", match_txt)]
        if len(partes) != 2:
            continue
        local_txt, visit_txt = partes
        casa = config.team_name in local_txt
        rival = visit_txt if casa else local_txt

        uid = f"{config.uid_prefix}-{anio_int}{mes:02d}{dia:02d}-{rival.lower().replace(' ', '-')}"
        partidos.append(
            {
                "uid": f"{uid}@{config.uid_dominio}",
                "competicion": "acb",
                "competicion_nombre": f"Liga Endesa {config.temporada}",
                "estado": "pendiente",
                "casa": casa,
                "rival": rival,
                "inicio_madrid": kickoff,
                "fecha_provisional": provisional,
                "acta": config.url,
                "ronda": "Regular",
            }
        )
    # La página repite la tabla en HTML y en JSON embebido; nos quedamos con
    # una entrada por (día, rival).
    unicos = []
    vistos = set()
    for p in partidos:
        clave = (
            p["inicio_madrid"][:10]
            + "|"
            + re.sub(r"[^a-z0-9]", "", p["rival"].lower())
        )
        if clave in vistos:
            continue
        vistos.add(clave)
        unicos.append(p)
    return unicos


MESES_EN = {
    "january": 1, "february": 2, "march": 3, "april": 4,
    "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
}


def extraer_euroliga(html: str, config) -> list[dict]:
    """Parsea el calendario oficial de la EuroLeague del Real Madrid."""
    partidos: list[dict] = []
    vistos: set[str] = set()
    for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, re.S):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.S)
        if len(cells) < 2:
            continue
        date_cell = cells[0]
        match_cell = cells[1]
        mround = re.search(r"(\d+)", _limpia(date_cell))
        if not mround:
            continue
        round_num = int(mround.group(1))
        mdate = re.search(
            r"([A-Za-z]+)\s+(\d{1,2}),\s*(\d{1,2}):(\d{2})\s*(am|pm)",
            _limpia(date_cell),
            re.I,
        )
        if not mdate:
            continue
        mes_txt = mdate.group(1).lower()
        mes = MESES_EN.get(mes_txt)
        if mes is None:
            continue
        dia = int(mdate.group(2))
        hh = int(mdate.group(3))
        mm = int(mdate.group(4))
        ampm = mdate.group(5).lower()
        if ampm == "pm" and hh != 12:
            hh += 12
        if ampm == "am" and hh == 12:
            hh = 0
        anio_int = 2026 if mes >= 9 else 2027

        raw_match = match_cell
        home = re.search(r"<b>.{0,20}Real Madrid.{0,20}</b>\s*-", raw_match, re.I) is not None
        away = re.search(r"-\s*<b>.{0,20}Real Madrid.{0,20}</b>", raw_match, re.I) is not None
        if not (home ^ away):
            # Determinar dirección por marcado o por posición textual.
            texto = _limpia(match_cell)
            if "Real Madrid-" in texto.replace(" ", ""):
                home = True
            elif "-Real Madrid" in texto.replace(" ", ""):
                away = True
            else:
                continue
        casa = home

        # rival: todo el texto sin la marca Real Madrid
        rival = _limpia(match_cell).replace("Real Madrid", "").strip(" -")
        rival = re.sub(r"\s+", " ", rival).strip(" -")
        if not rival:
            continue

        uid_code = f"el-g{round_num}-{rival.lower().replace(' ', '-')}"
        uid = f"{config.uid_prefix}-{uid_code}@{config.uid_dominio}"
        if uid in vistos:
            continue
        vistos.add(uid)

        kickoff = f"{anio_int:04d}-{mes:02d}-{dia:02d}T{hh:02d}:{mm:02d}"
        partidos.append(
            {
                "uid": uid,
                "competicion": "euroliga",
                "competicion_nombre": "EuroLeague 26/27",
                "estado": "pendiente",
                "casa": casa,
                "rival": rival,
                "inicio_madrid": kickoff,
                "fecha_provisional": False,
                "acta": "https://www.realmadrid.com/en-US/news/basket/first-team/latest-news/el-calendario-del-real-madrid-para-la-euroliga-2026-27-29-07-2026",
                "ronda": f"G. {round_num}",
            }
        )
    return partidos


API_KEY_DEFAULT = "0dd94928-6f57-4c08-a3bd-b1b2f092976e"
ACB_DEFAULT_KEY = os.environ.get("ACB_API_KEY") if 'os' in globals() else None


def fetch_partidos(config) -> list[dict]:
    import json as _json
    from datetime import datetime
    from zoneinfo import ZoneInfo

    from scripts.comun.http import fetch

    if getattr(config, "club_id", None) is None:
        raise ValueError("ConfigACB requiere club_id")
    year = datetime.now().year
    season_end = year + 1 if datetime.now().month >= 9 else year
    url = (
        "https://api2.acb.com/api/seasondata/TeamProfile/team-matches"
        f"?clubId={config.club_id}&competitionId=1&season={season_end}"
    )
    import urllib.request

    ua = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "application/json", "X-APIKEY": API_KEY_DEFAULT})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = _json.load(resp)

    partidos: list[dict] = []
    Madrid = ZoneInfo("Europe/Madrid")
    for m in (data.get("matches") or []):
        match_id = m.get("id")
        home = m.get("homeTeam") or {}
        away = m.get("awayTeam") or {}
        casa = (home.get("clubId") == config.club_id)
        rival = (away if casa else home).get("shortName") or (away if casa else home).get("fullName") or "Rival"

        utc_raw = m.get("startDateTime") or m.get("delayedStartDateTime")
        if utc_raw is None:
            continue
        try:
            dt = datetime.fromisoformat(str(utc_raw).replace("Z", "+00:00"))
        except ValueError:
            continue
        inicio_local = dt.astimezone(Madrid).replace(tzinfo=None)

        played = (str(m.get("matchStatus", "")).upper() == "FINALIZED")
        home_score = m.get("homeScore")
        away_score = m.get("awayScore")

        estado = "jugado" if played else "pendiente"
        uid = f"{config.uid_prefix}-acb{match_id}@{config.uid_dominio}"
        sede_club_id = home.get("clubId")
        partido = {
            "uid": uid,
            "competicion": "acb",
            "competicion_nombre": f"Liga Endesa {config.temporada}",
            "estado": estado,
            "casa": casa,
            "rival": rival,
            "inicio_madrid": inicio_local.isoformat(timespec="minutes"),
            "fecha_provisional": False,
            "acta": "https://acb.com/es/liga/equipos/real-madrid-9/partidos",
            "ronda": f"J{m.get('roundNumber', '?')}",
        }
        if sede_club_id is not None:
            partido["sede_club_id"] = sede_club_id
        if played and (home_score is not None or away_score is not None):
            hs = 0 if home_score is None else int(home_score)
            as_ = 0 if away_score is None else int(away_score)
            if casa:
                victory = hs > as_
                partido["resultado_local"] = hs
                partido["resultado_visitante"] = as_
                partido["resultado_equipo"] = hs
                partido["resultado_rival"] = as_
            else:
                victory = as_ > hs
                partido["resultado_local"] = hs
                partido["resultado_visitante"] = as_
                partido["resultado_equipo"] = as_
                partido["resultado_rival"] = hs
            partido["victoria"] = bool(victory)
        partidos.append(partido)
    return partidos
