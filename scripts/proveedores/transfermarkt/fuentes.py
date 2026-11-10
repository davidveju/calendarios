"""Parsea el calendario agregado de un equipo desde Transfermarkt.

La página ``spielplan`` con ``plus/1`` incluye todas las competiciones del año:
liga doméstica, Copa del Rey, Conference League, previas, etc., con fechas,
horas, rivales, resultados y un enlace estable por partido.

El parser no conoce equipos concretos; solo un :class:`ConfigTM`.
"""

from __future__ import annotations

import html as _html
import re
from datetime import datetime, timezone

MADRID = None  # usamos Europe/Madrid al desplazar; importado en generador
URL_TMPL = (
    "https://www.transfermarkt.com/{slug}/spielplan/verein/"
    "{team_id}/saison_id/{season_id}/plus/1"
)

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# Transfermarkt sirve una página vacía (sin filas de partidos) a clientes que
# no parecen un navegador. El ``Referer`` propio ayuda a superarlo.
HEADERS = {"Referer": "https://www.transfermarkt.com/"}


def diagnostico(html: str) -> str:
    """Resume qué devolvió Transfermarkt cuando no se pudo extraer nada.

    Sirve para distinguir en los logs un bloqueo (página de consentimiento o
    anti-bots) de un simple cambio de formato.
    """
    titulo = re.search(r"<title>(.*?)</title>", html or "", re.S | re.I)
    texto = _limpia_cell(titulo.group(1)) if titulo else "sin <title>"
    return f"{len(html or '')} bytes, título {texto[:80]!r}"


def _limpia_cell(html_fragment: str) -> str:
    return _html.unescape(re.sub(r"<[^>]+>", " ", html_fragment)).replace("\xa0", " ").strip()


def _parse_date(text: str) -> str | None:
    # "Thu 26/11/2026" o "Sat 15/08/2026"
    text = text.strip()
    m = re.search(r"\d{1,2}/\d{1,2}/\d{4}", text)
    if not m:
        return None
    try:
        dt = datetime.strptime(m.group(0), "%d/%m/%Y")
    except ValueError:
        return None
    return dt.date().isoformat()


def _parse_time(text: str, date_text: str) -> tuple[str, bool]:
    """Devuelve (ISO sin tz, provisional). provisional=True si no hay hora."""
    text = text.strip()
    m = re.search(r"(\d{1,2}:\d{2})(?:\s*(AM|PM))?", text, re.I)
    date_only = _parse_date(date_text)
    if not m:
        if date_only is None:
            return "", True
        return f"{date_only}T12:00", True
    hora = m.group(1)
    ampm = (m.group(2) or "").upper()
    try:
        if ampm:
            dt = datetime.strptime(f"{hora} {ampm}", "%I:%M %p")
        else:
            dt = datetime.strptime(hora, "%H:%M")
        # Combina con fecha
        date_only = _parse_date(date_text)
        if date_only is None:
            return "", True
        y, mo, d = date_only.split("-")
        hhmm = dt.strftime("%H:%M")
        return f"{y}-{mo}-{d}T{hhmm}", False
    except ValueError:
        return "", True


def _competicion_por_etapa(etapa: str) -> str:
    etapa = (etapa or "").lower()
    if "qual" in etapa:
        return "conference"
    if "group" in etapa:
        return "conference"
    if "round" in etapa or "final" in etapa or "semi" in etapa:
        # identificar copa: si no es numérico, suele ser copa o copa de rey
        return "copa"
    if re.fullmatch(r"\d+", (etapa or "").strip()):
        return "liga"
    # fallback: cualquier otra cosa, liga por defecto
    return "liga"


def _competicion_oculta(config, etapa: str) -> str:
    # resolvemos el nombre competicion
    return _competicion_por_etapa(etapa)


COMPETICIONES_CLUB = {
    "liga": "LaLiga {temporada}",
    "copa": "Copa del Rey {temporada}",
    "champions": "Champions League {temporada}",
    "europa": "Europa League {temporada}",
    "conference": "Conference League {temporada}",
}


def _nombre_competicion(config, codigo: str) -> str:
    """Nombre visible de la competición según la configuración del calendario."""
    for comp in getattr(config, "competiciones", ()):
        if comp.codigo == codigo:
            return comp.nombre.format(temporada=config.temporada)
    return COMPETICIONES_CLUB.get(codigo, "Fútbol {temporada}").format(
        temporada=config.temporada
    )


def _competicion_configurada(texto: str, config) -> str | None:
    """Código de la competición configurada cuya clave aparece más a la derecha.

    Se usa la última aparición porque el HTML incluye estadísticas anteriores y
    la cabecera real de la tabla es lo más cercano al partido.
    """
    texto = (texto or "").lower()
    candidatos: list[tuple[int, str]] = []
    for comp in getattr(config, "competiciones", ()):
        for clave in comp.claves:
            pos = texto.rfind(clave.lower())
            if pos != -1:
                candidatos.append((pos, comp.codigo))
    if not candidatos:
        return None
    candidatos.sort()
    return candidatos[-1][1]


def _competicion_club(texto: str) -> str:
    """Heurística histórica para las competiciones de clubes."""
    texto = (texto or "").lower()
    candidatos: list[tuple[int, str]] = []
    for key, comp in (
        ("champions", "champions"),
        ("conference", "conference"),
        ("europa league", "europa"),
        ("copa", "copa"),
        ("laliga", "liga"),
    ):
        pos = texto.rfind(key)
        if pos != -1:
            candidatos.append((pos, comp))
    if not candidatos:
        return "liga"
    candidatos.sort()
    return candidatos[-1][1]


RONDAS = {
    "group stage": "Fase de grupos",
    "league phase": "Fase de liga",
    "knockout phase play-offs": "Play-offs de eliminatorias",
    "play-off round": "Ronda de play-off",
    "play-offs": "Play-offs",
    "qualifying round": "Ronda previa",
    "1st qualifying round": "Primera ronda previa",
    "first qualifying round": "Primera ronda previa",
    "2nd qualifying round": "Segunda ronda previa",
    "second qualifying round": "Segunda ronda previa",
    "3rd qualifying round": "Tercera ronda previa",
    "third qualifying round": "Tercera ronda previa",
    "first round": "Primera ronda",
    "second round": "Segunda ronda",
    "third round": "Tercera ronda",
    "round of 32": "Dieciseisavos",
    "round of 16": "Octavos",
    "quarter-finals": "Cuartos",
    "semi-finals": "Semifinales",
    "final": "Final",
    "regular season": "Temporada regular",
    "championship round": "Ronda por el título",
    "relegation round": "Ronda por la permanencia",
}


def traducir_ronda(ronda: str) -> str:
    """Traduce al español las rondas que publica Transfermarkt.

    Si no reconoce el texto, devuelve el original para no perder información.
    """
    ronda = (ronda or "").strip()
    if not ronda:
        return ""
    bajo = ronda.lower()

    grupo = re.fullmatch(r"group\s+(.+)", bajo)
    if grupo:
        valor = grupo.group(1).strip()
        if valor.startswith("stage"):
            return "Fase de grupos"
        return f"Grupo {valor.upper()}"

    # "Qualifying Round 1st leg", "Round of 16 2nd leg"...
    pierna = re.fullmatch(r"(.*?)\s+(1st|2nd)\s+leg", bajo)
    if pierna:
        base = traducir_ronda(pierna.group(1))
        vuelta = "ida" if pierna.group(2) == "1st" else "vuelta"
        return f"{base}, {vuelta}" if base else vuelta

    return RONDAS.get(bajo, ronda)


def parse_partido(row_html: str, config, competicion_override: str | None = None) -> dict | None:
    """Normaliza una fila HTML de Transfermarkt. None si no es partido del equipo."""
    cells = re.findall(r"<td[^>]*>(.*?)</td>", row_html, re.S)
    if len(cells) < 8:
        return None
    # La tabla de amistosos no tiene columna de jornada; la de competiciones sí.
    if _parse_date(_limpia_cell(cells[0])) is not None:
        etapa_txt = ""
        fecha_txt = _limpia_cell(cells[0])
        hora_txt = _limpia_cell(cells[1])
        home_name = _limpia_cell(cells[3])
        away_name = _limpia_cell(cells[5])
    elif len(cells) >= 11:
        etapa_txt = _limpia_cell(cells[0])
        fecha_txt = _limpia_cell(cells[1])
        hora_txt = _limpia_cell(cells[2])
        home_name = _limpia_cell(cells[4])
        away_name = _limpia_cell(cells[6])
    else:
        return None
    resultado_td = cells[-1] if cells else ""
    resultado_txt = _limpia_cell(resultado_td)
    # url estable del partido
    enlace = None
    m = re.search(r'href="([^"]*spielbericht/index/spielbericht/\d+)"', resultado_td)
    if m:
        enlace = "https://www.transfermarkt.com" + m.group(1)
    if enlace is None:
        m2 = re.search(r'href="([^"]*spielbericht/index/spielbericht/\d+)"', row_html)
        if m2:
            enlace = "https://www.transfermarkt.com" + m2.group(1)
    if not enlace:
        return None

    if config.team_name.lower() not in home_name.lower() and config.team_name.lower() not in away_name.lower():
        return None

    casa = config.team_name.lower() in home_name.lower()
    rival = away_name if casa else home_name
    rival = re.sub(r"\s*\(\d+\.?\)\s*$", "", rival).strip()

    fecha_iso = _parse_date(fecha_txt)
    if fecha_iso is None:
        return None
    kickoff, provisional = _parse_time(hora_txt, fecha_txt)

    # resultado
    estado = "pendiente"
    result_match = re.search(r"(\d+)\s*:\s*(\d+)", resultado_txt)
    res_local = None
    res_visit = None
    if re.search(r"\b(?:ppd|canc|postponed|cancelled|canceled|abd)\b", resultado_txt, re.I):
        estado = "aplazado"
    elif result_match:
        estado = "jugado"
        res_local = int(result_match.group(1))
        res_visit = int(result_match.group(2))

    uid_code = enlace.rsplit("/", 1)[-1]
    uid = f"{config.uid_prefix}-{uid_code}@{config.uid_dominio}"

    competicion = competicion_override or _competicion_por_etapa(etapa_txt)
    competicion_nombre = _nombre_competicion(config, competicion)

    data = {
        "uid": uid,
        "competicion": competicion,
        "competicion_nombre": competicion_nombre,
        "estado": estado,
        "casa": casa,
        "rival": rival,
        "inicio_madrid": kickoff,
        "fecha_provisional": provisional,
        "uid_evento": uid_code,
        "fuente": "transfermarkt",
        "acta": enlace,
        "ronda": etapa_txt,
    }
    if estado == "jugado" and res_local is not None and res_visit is not None:
        victoria = None
        if casa:
            victoria = res_local > res_visit
            data["resultado_local"] = res_local
            data["resultado_visitante"] = res_visit
            data["resultado_equipo"] = res_local
            data["resultado_rival"] = res_visit
        else:
            victoria = res_visit > res_local
            data["resultado_local"] = res_local
            data["resultado_visitante"] = res_visit
            data["resultado_equipo"] = res_visit
            data["resultado_rival"] = res_local
        data["victoria"] = bool(victoria)
    return data


def extraer_partidos(html: str, config) -> list[dict]:
    """Extrae partidos de nuestro equipo de una página HTML de Transfermarkt."""
    out: list[dict] = []
    vistos: set[str] = set()
    # El HTML puede tener varias tablas o cabeceras; reconstruiremos el contexto
    # por tabla/competición.
    for table_match in re.finditer(r"<table\b[^>]*>(.*?)</table>", html, re.S):
        content = table_match.group(1)
        if "spielbericht/index/spielbericht/" not in content:
            continue
        preceding = html[max(0, table_match.start() - 2500):table_match.start()]
        current_comp = _competicion_configurada(preceding, config)
        if current_comp is None:
            current_comp = _competicion_club(preceding)
        for tag_match in re.finditer(r"<(thead|tr)\b[^>]*>(.*?)</\1>", content, re.S):
            tag = tag_match.group(1)
            inner = tag_match.group(2)
            if tag == "thead":
                configurada = _competicion_configurada(inner, config)
                if configurada is not None:
                    current_comp = configurada
                    continue
                low = inner.lower()
                if "champions" in low or "champions-league" in low:
                    current_comp = "champions"
                elif "europa league" in low:
                    current_comp = "europa"
                elif "conference" in low:
                    current_comp = "conference"
                elif "copa" in low or "copa-del-rey" in low:
                    current_comp = "copa"
                elif "laliga" in low or "primera" in low or ("la liga" in low):
                    current_comp = "liga"
                continue
            if "spielbericht/index/spielbericht/" not in inner:
                continue
            p = parse_partido(inner, config, current_comp)
            if p is not None and p["uid"] not in vistos:
                vistos.add(p["uid"])
                out.append(p)
    return out


def parse_sede(html: str) -> dict:
    """Extrae el estadio de una ficha ``spielbericht`` de Transfermarkt.

    Devuelve ``{"pabellon": ...}`` o ``{}`` si no se puede determinar.
    """
    zona = re.search(
        r'class="[^"]*\bsb-zusatzinfos\b[^"]*"[^>]*>(.*?)</p\s*>',
        html,
        re.S | re.I,
    )
    fuente = zona.group(1) if zona else html
    m = re.search(r'href="[^"]*/stadion/[^"]*"[^>]*>([^<]+)</a>', fuente, re.I)
    if not m:
        m = re.search(r'Stadium:.*?<a[^>]*>([^<]+)</a>', html, re.S | re.I)
    if not m:
        return {}
    pabellon = _html.unescape(m.group(1)).replace("\xa0", " ").strip()
    return {"pabellon": pabellon} if pabellon else {}


def fetch_sede(acta: str, *, retries: int = 2, timeout: int = 20) -> dict:
    """Descarga la ficha del partido y devuelve su sede.

    ``acta`` puede ser la URL completa o un id de ``spielbericht``.
    """
    if str(acta).isdigit():
        url = f"https://www.transfermarkt.com/spielbericht/index/spielbericht/{acta}"
    else:
        url = str(acta)
    try:
        from scripts.comun.http import fetch

        return parse_sede(fetch(url, user_agent=USER_AGENT, headers=HEADERS, retries=retries, timeout=timeout))
    except Exception as e:  # noqa: BLE001 - la sede es opcional
        raise ValueError(f"sede tm {acta} falló ({e})") from e


def fechas() -> list[str]:
    return []
