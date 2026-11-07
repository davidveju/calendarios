#!/usr/bin/env python3
"""Parsea las fuentes de la FEB: liga Primera FEB y Copa España.

Fuentes:
  - Liga: competiciones.feb.es/estadisticas/Calendario.aspx
      celda 'resultado' con marcador  => jugado
      celda 'fecha' con DIA dd/mm/aaaa hh:mm => pendiente (hora Madrid)
  - Copa (eliminatorias a partido único):
      www.feb.es/competiciones/resultados/copaespaa/73/2026
      tabla Equipos | Resultado (*-* = pendiente) | Fecha | Hora
      La FEB reutiliza "Jornada 1" en cada fase (1/16, 1/8...): la ronda real
      sale del desplegable de grupos ("Play-offs 1/8 Final"). "Por determinar"
      en fecha => pendiente con fecha provisional de la jornada.

Este módulo no escribe ficheros: solo devuelve partidos normalizados. La
orquestación y la generación del ICS viven en ``generar.py``.
"""

from __future__ import annotations

import html as _html
import re
from collections import Counter
from http.client import HTTPException
from urllib.error import URLError

from calendarios.http import fetch
from calendarios.log import log, warn

LIGA_URL = "https://competiciones.feb.es/estadisticas/Calendario.aspx"
COPA_URL = "https://www.feb.es/competiciones/resultados/copaespaa/73/2026"
PARTIDO_URL = "https://baloncestoenvivo.feb.es/Partido.aspx?p={pid}"

ESTU_ID = "1010493"
LIGA_NOMBRE = "Primera FEB 26/27"
COPA_NOMBRE = "Copa España 26/27"
RONDAS_COPA = {1: "1/16", 2: "1/8", 3: "1/4", 4: "Semifinal", 5: "Final"}
RONDA_A_JNUM = {v: k for k, v in RONDAS_COPA.items()}
CASA_PABELLON = "Movistar Arena, Madrid"
ESTU_RE = re.compile(r"[?&]i=" + re.escape(ESTU_ID) + r"\b", re.I)

# Resultados que significan "pendiente" aunque no haya marcador (FEB varía el texto).
PENDIENTE_TXT = {
    "*-*",
    "* - *",
    "-",
    "",
    "POR DETERMINAR",
    "PDT",
    "SUSP",
    "SUSP.",
    "SUSPENDIDO",
    "PP",
    "APL",
    "APLAZADO",
    "APLAZADA",
    "DESC",
    "DESCANSO",
}


def _limpia(txt: str) -> str:
    """Texto de celda: sin tags, entidades decodificadas, nbsp->espacio."""
    return _html.unescape(re.sub(r"<[^>]+>", " ", txt)).replace("\xa0", " ").strip()


def fetch_sede(pid: str, retries: int = 2, timeout: int = 15) -> dict:
    """Pabellón + dirección desde la ficha del partido. {} si no hay pista."""
    url = PARTIDO_URL.format(pid=pid)
    try:
        h = fetch(url, retries=retries, timeout=timeout)
    except Exception as e:  # noqa: BLE001 - se traduce a error de sede
        raise ValueError(f"sede pid={pid} falló ({e})") from e

    m = re.search(
        r'<div[^>]*\bclass\s*=\s*["\'][^"\']*\bpista\b[^"\']*["\'][^>]*>'
        r"(.*?)</div\s*>",
        h,
        re.S | re.I,
    )
    if not m:
        return {}
    pab = re.search(
        r'class\s*=\s*["\'][^"\']*\bpabellon\b[^"\']*["\'][^>]*>'
        r"(.*?)</(span|div)\s*>",
        m.group(1),
        re.S | re.I,
    )
    drc = re.search(
        r'class\s*=\s*["\'][^"\']*\bdireccion\b[^"\']*["\'][^>]*>'
        r"(.*?)</(span|div)\s*>",
        m.group(1),
        re.S | re.I,
    )
    pab_txt = title_case(_limpia(pab.group(1))) if pab and _limpia(pab.group(1)) else ""
    drc_txt = _limpia(drc.group(1)) if drc and _limpia(drc.group(1)) else ""
    if not pab_txt and not drc_txt:
        return {}
    return {"pabellon": pab_txt, "direccion": drc_txt}


def _cap_word(w: str, minus: set, siglas: set, is_first: bool) -> str:
    key = re.sub(r"[.\-'/·]", "", w).lower()
    if key in siglas:
        return re.sub(r"[.\-'/·]", "", w).upper()
    if key in minus and not is_first:
        return w.lower()

    # Capitaliza la primera letra alfabética, respeta guiones/apóstrofes.
    def _cap(seg: str) -> str:
        m = re.search(r"[A-Za-zÀ-ÿ]", seg)
        if not m:
            return seg
        i = m.start()
        return seg[:i] + seg[i].upper() + seg[i + 1 :].lower()

    return "".join(
        _cap(s) if j % 2 == 0 else s for j, s in enumerate(re.split(r"([-'/·])", w))
    )


def title_case(s: str) -> str:
    minus = {"de", "del", "la", "el", "los", "las", "en", "y", "a", "al"}
    siglas = {"cb", "cd", "ad", "sd", "xb", "alb", "bca", "hla"}
    palabras = s.strip().split()
    return " ".join(_cap_word(w, minus, siglas, i == 0) for i, w in enumerate(palabras))


def _score(texto: str) -> tuple[int, int] | None:
    # Evita que una fecha tipo 12-10-2026 se lea como marcador 12-10.
    m = re.search(
        r"(?<![\d/.-])(\d{1,3})\s*[-–—]\s*(\d{1,3})(?![\d/.-])", texto
    )
    return (int(m.group(1)), int(m.group(2))) if m else None


def _es_pendiente(texto: str) -> bool:
    u = texto.strip().upper()
    if u in PENDIENTE_TXT:
        return True
    # Variantes con hora o texto extra: "Por determinar 19:00", "Aplazado ...".
    return any(
        x in u for x in ("POR DETERMINAR", "APLAZ", "SUSPEND", "SUSP.", "PDT")
    )


def _dedup_uid(partidos: list[dict], ambito: str) -> dict[str, dict]:
    """Un UID por partido. Si la FEB duplica filas, nunca perder un resultado jugado."""
    por_uid: dict[str, dict] = {}
    for p in partidos:
        old = por_uid.get(p["uid"])
        if old is None:
            por_uid[p["uid"]] = p
            continue
        if old.get("estado") == "jugado" and p.get("estado") != "jugado":
            warn(f"{ambito}: fila duplicada {p['uid']}; conservo la jugada")
            continue
        if p.get("estado") == "jugado" and old.get("estado") != "jugado":
            if old.get("inicio_madrid") and "inicio_madrid" not in p:
                p["inicio_madrid"] = old["inicio_madrid"]
            warn(f"{ambito}: fila duplicada {p['uid']}; uso la jugada")
        elif old.get("feb_partido_id") != p.get("feb_partido_id"):
            warn(
                f"{ambito}: UID duplicado {p['uid']} pids "
                f"{old.get('feb_partido_id')} vs {p.get('feb_partido_id')}; me quedo con el último"
            )
        por_uid[p["uid"]] = p
    return por_uid


def parse_liga(html: str) -> list[dict]:
    h2 = _html.unescape(html).replace("\xa0", " ")
    blocks = re.findall(
        r"Jornada\s+(\d+)\s+(\d{1,2}[/-]\d{1,2}[/-]\d{4})(.*?)"
        r"(?=Jornada\s+\d+\s+\d{1,2}[/-]|$)",
        h2,
        re.S | re.I,
    )
    if not blocks:
        raise ValueError("liga: no se encontraron bloques de jornada (cambió la página FEB)")
    partidos = []
    for jnum, jdate_raw, body in blocks:
        jdate = re.sub(r"-", "/", jdate_raw)
        for r in re.findall(r"<tr[^>]*>(.*?)</tr\s*>", body, re.S | re.I):
            if not ESTU_RE.search(r):
                continue
            snippet = re.sub(r"\s+", " ", r)[:2000]
            m_pid = re.search(r"Partido\.aspx\?p=(\d+)\b", r, re.I)
            if not m_pid:
                raise ValueError(f"liga: sin partido id J{jnum}: {snippet[:500]}")
            pid = m_pid.group(1)
            equipos = re.findall(
                r"Equipo\.aspx\?i=(\d+)\b[^>]*>\s*([^<]+?)\s*</a>", r, re.I
            )
            if len(equipos) < 2:
                raise ValueError(f"liga: sin 2 equipos J{jnum} pid={pid}: {snippet[:500]}")
            ids = [e[0] for e in equipos]
            if ESTU_ID not in ids:
                raise ValueError(
                    f"liga: Estu no está entre los ids J{jnum} pid={pid}: {ids}"
                )
            casa = ids[0] == ESTU_ID
            rival_raw = equipos[1][1] if casa else equipos[0][1]
            m = re.search(
                r'<td[^>]*\bclass\s*=\s*["\']?[^"\'<>]*\b(resultado|fecha)\b[^"\'<>]*'
                r'["\']?[^>]*>\s*<a[^>]*>(.*?)</a>',
                r,
                re.S | re.I,
            )
            if not m:
                raise ValueError(
                    f"liga: celda resultado/fecha no encontrada J{jnum} pid={pid}: "
                    f"{snippet[:500]}"
                )
            cell = re.sub(r"\s+", " ", m.group(2)).strip()
            t = _limpia(cell)
            score = _score(t)
            p = {
                "jornada": int(jnum),
                "fecha_jornada": jdate,
                "uid": f"estu-2627-j{int(jnum):02d}@estudiantes-calendario",
                "competicion": "liga",
                "competicion_nombre": LIGA_NOMBRE,
                "casa": casa,
                "rival": title_case(_limpia(rival_raw)),
                "feb_partido_id": pid,
                "acta": f"https://baloncestoenvivo.feb.es/Partido.aspx?p={pid}",
                "estado": "jugado" if score else "pendiente",
            }
            if score:
                gl, gv = score
                p["resultado_local"], p["resultado_visitante"] = gl, gv
                pe, pr = (gl, gv) if casa else (gv, gl)
                p["resultado_estu"], p["resultado_rival"] = pe, pr
                p["victoria"] = pe > pr
                # La FEB borra la hora al publicar el resultado: sin hora conocida,
                # el evento va a las 12:00 y se marca provisional (TENTATIVE).
                if "inicio_madrid" not in p:
                    p["fecha_provisional"] = True
            else:
                dm = re.search(
                    r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})\s*"
                    r"(?:<br\s*/?>\s*)?(\d{1,2}:\d{2})?",
                    t,
                    re.I,
                )
                if dm:
                    d, mo, y = int(dm.group(1)), int(dm.group(2)), int(dm.group(3))
                    hhmm = dm.group(4) or "12:00"
                    hh, mm = map(int, hhmm.split(":"))
                    p["inicio_madrid"] = f"{y:04d}-{mo:02d}-{d:02d}T{hh:02d}:{mm:02d}:00"
                    if not dm.group(4):
                        p["fecha_provisional"] = True
                elif _es_pendiente(t) or not t:
                    # Aplazado/suspendido sin fecha en la celda: provisional con la semana.
                    d, mo, y = map(int, jdate.split("/"))
                    p["inicio_madrid"] = f"{y:04d}-{mo:02d}-{d:02d}T12:00:00"
                    p["fecha_provisional"] = True
                    warn(f"liga: J{jnum} pid={pid} sin fecha ({t!r}); provisional {jdate}")
                else:
                    raise ValueError(
                        f"liga: fecha no parseable J{jnum} pid={pid}: {cell!r} "
                        f"(fila: {snippet[:500]})"
                    )
            partidos.append(p)
    # Dedup por UID: la FEB a veces duplica/aplaza filas; nunca emitir duplicados.
    partidos = sorted(_dedup_uid(partidos, "liga").values(), key=lambda p: p["jornada"])
    return partidos


def _bloque_select(html: str, sufijo_id: str) -> str:
    """Contenido del <select> cuyo id/name termina en sufijo_id (acotado a su </select>)."""
    m = re.search(
        r'<select[^>]*(?:id|name)\s*=\s*["\'][^"\']*'
        + re.escape(sufijo_id)
        + r'[^"\']*["\'][^>]*>(.*?)</select\s*>',
        html,
        re.S | re.I,
    )
    return m.group(1) if m else ""


def _grupo_copa(html: str) -> str:
    """Texto del desplegable de grupos seleccionado, ej 'Play-offs 1/8 Final'."""
    bloque = _bloque_select(html, "gruposDropDownList")
    m = re.search(r"<option[^>]*\bselected\b[^>]*>(.*?)</option>", bloque, re.S | re.I)
    if m:
        return re.sub(
            r"\s+", " ", _html.unescape(m.group(1)).replace("\xa0", " ")
        ).strip()
    opciones = re.findall(r"<option[^>]*>(.*?)</option>", bloque, re.S | re.I)
    if not opciones:
        return ""
    if len(opciones) > 1:
        raise ValueError(
            "copa: grupo sin opción seleccionada y varias opciones; no se sabe la fase"
        )
    return re.sub(
        r"\s+", " ", _html.unescape(opciones[0]).replace("\xa0", " ")
    ).strip()


def _jornada_copa_seleccionada(html: str) -> tuple[int, str]:
    """(número, fecha dd/mm/aaaa o '') de la jornada seleccionada en la copa."""
    bloque = _bloque_select(html, "jornadasDropDownList")
    if not bloque:
        raise ValueError(
            "copa: no se encontró el desplegable de jornadas (cambió la página FEB)"
        )
    m = re.search(
        r'<option[^>]*\bselected\b[^>]*>\s*Jornada\s+(\d+)\s*'
        r"(?:\((\d{1,2}[/-]\d{1,2}[/-]\d{4})\))?",
        bloque,
        re.S | re.I,
    )
    if m:
        return int(m.group(1)), (m.group(2) or "")
    # Fallback: preferir la option marcada como selected, no la menor.
    mejor: tuple[int, str] | None = None
    for om in re.finditer(
        r"<option([^>]*)>\s*Jornada\s+(\d+)\s*"
        r"(?:\((\d{1,2}[/-]\d{1,2}[/-]\d{4})\))?",
        bloque,
        re.S | re.I,
    ):
        attrs, num, fec = om.group(1), int(om.group(2)), (om.group(3) or "")
        if re.search(r"\bselected\b", attrs, re.I):
            return num, fec
        if mejor is None:
            mejor = (num, fec)
    if mejor is not None:
        warn("copa: jornada sin selected; uso la primera encontrada")
        return mejor
    raise ValueError("copa: no se encontró ninguna jornada (cambió la página FEB)")


def _ronda_copa(grupo_txt: str, jnum_fallback: int) -> tuple[str, int]:
    """Ronda real desde el grupo. La FEB reutiliza Jornada 1 en cada fase."""
    g = grupo_txt.upper()
    if "1/16" in g or "DIECISEIS" in g:
        return "1/16", RONDA_A_JNUM["1/16"]
    if "1/8" in g or ("OCTAVOS" in g and "DIECISEIS" not in g):
        return "1/8", RONDA_A_JNUM["1/8"]
    if "1/4" in g or "CUARTO" in g:
        return "1/4", RONDA_A_JNUM["1/4"]
    if "SEMIFINAL" in g or re.search(r"\bSEMI\b", g):
        return "Semifinal", RONDA_A_JNUM["Semifinal"]
    if "FINAL" in g:
        return "Final", RONDA_A_JNUM["Final"]
    # Sin ronda fiable no se inventa un UID: J1 colisionaría con el 1/16 histórico.
    raise ValueError(
        f"copa: grupo no reconocido ({grupo_txt!r}) en J{jnum_fallback}; "
        "no se puede asignar ronda"
    )


def _celdas(r: str) -> list[str]:
    return [_limpia(c) for c in re.findall(r"<td[^>]*>(.*?)</td\s*>", r, re.S | re.I)]


def parse_copa(html: str) -> list[dict]:
    """Copa España: eliminatorias a partido único; fecha+hora en columnas propias.

    Acepta 'Por determinar' en fecha/hora: deja el partido pendiente con fecha
    provisional de la jornada (dropdown) para no tumbar toda la ejecución.
    Si el Estu no está en la fase actual (eliminado o aún no publicada), devuelve [].
    """
    grupo_txt = _grupo_copa(html)
    j_jornada, fecha_dropdown = _jornada_copa_seleccionada(html)
    ronda, jnum = _ronda_copa(grupo_txt, j_jornada)
    log(
        f"copa: fase={grupo_txt!r} jornada={j_jornada} "
        f"fecha_jornada={fecha_dropdown!r} => ronda={ronda} uid_j={jnum:02d}"
    )

    partidos = []
    filas = re.findall(r"<tr[^>]*>(.*?)</tr\s*>", html, re.S | re.I)
    if not filas:
        raise ValueError("copa: sin filas <tr> (cambió la página FEB)")
    for r in filas:
        if not ESTU_RE.search(r) or "equipo.aspx" not in r.lower():
            continue
        snippet = re.sub(r"\s+", " ", r)[:2000]
        eq = re.search(
            r"Equipo\.aspx\?i=(\d+)\b[^>]*>\s*([^<]+?)\s*</a>\s*-\s*"
            r"<a[^>]*Equipo\.aspx\?i=(\d+)\b[^>]*>\s*([^<]+?)\s*</a>",
            r,
            re.S | re.I,
        )
        rs = re.search(r"Partido\.aspx\?p=(\d+)\b[^>]*>(.*?)</a>", r, re.S | re.I)
        if not (eq and rs):
            raise ValueError(
                f"copa: fila del Estu no parseable (eq={bool(eq)} rs={bool(rs)}): "
                f"{snippet[:1000]}"
            )
        id_loc, nom_loc, id_vis, nom_vis = eq.groups()
        pid = rs.group(1)
        res_txt = _limpia(rs.group(2))
        celdas = _celdas(r)
        fecha_raw = next(
            (
                c
                for c in celdas
                if re.fullmatch(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", c)
                or c.upper().startswith("POR DETERMINAR")
            ),
            "",
        )
        hora_m = next(
            (re.search(r"(\d{1,2}:\d{2})", c) for c in celdas if re.search(r"\d{1,2}:\d{2}", c)),
            None,
        )
        hora_raw = hora_m.group(1) if hora_m else ""
        if not fecha_raw:
            raise ValueError(f"copa: sin fecha en la fila pid={pid}: {snippet[:1000]}")
        casa = id_loc == ESTU_ID
        score = _score(res_txt)
        if not (score or _es_pendiente(res_txt)):
            warn(
                f"copa: resultado desconocido pid={pid}: {res_txt!r}; "
                "se trata como pendiente"
            )
        tbd = fecha_raw.upper().startswith("POR DETERMINAR")
        fecha_jornada = fecha_dropdown or ("" if tbd else fecha_raw)
        if not fecha_jornada and tbd:
            warn(f"copa: {ronda} pid={pid} sin fecha ni fecha de jornada, se crea sin inicio")
            fecha_jornada = "Por determinar"
        p = {
            "jornada": jnum,
            "ronda": ronda,
            "fecha_jornada": fecha_jornada if fecha_jornada else fecha_raw,
            "uid": f"estu-2627-copa-j{jnum:02d}@estudiantes-calendario",
            "competicion": "copa",
            "competicion_nombre": COPA_NOMBRE,
            "casa": casa,
            "rival": title_case(_limpia(nom_vis if casa else nom_loc)),
            "feb_partido_id": pid,
            "acta": f"https://www.feb.es/competiciones/Partido.aspx?p={pid}",
            "estado": "jugado" if score else "pendiente",
        }
        if tbd:
            if fecha_dropdown:
                d, mo, y = map(int, re.split(r"[/-]", fecha_dropdown))
                p["inicio_madrid"] = f"{y:04d}-{mo:02d}-{d:02d}T12:00:00"
                p["fecha_provisional"] = True
            # else: sin inicio_madrid; la generación del ICS lo gestiona
        else:
            d, mo, y = map(int, re.split(r"[/-]", fecha_raw))
            hh, mm = map(int, (hora_raw or "12:00").split(":"))
            p["inicio_madrid"] = f"{y:04d}-{mo:02d}-{d:02d}T{hh:02d}:{mm:02d}:00"
            if not hora_raw:
                p["fecha_provisional"] = True
        if score:
            gl, gv = score
            p["resultado_local"], p["resultado_visitante"] = gl, gv
            pe, pr = (gl, gv) if casa else (gv, gl)
            p["resultado_estu"], p["resultado_rival"] = pe, pr
            p["victoria"] = pe > pr
        partidos.append(p)
    if not partidos:
        warn(
            "copa: el Estu no aparece en la fase actual (eliminado o fase nueva sin publicar); "
            "se conserva el histórico"
        )
    por_uid = _dedup_uid(partidos, "copa")
    return list(por_uid.values())
