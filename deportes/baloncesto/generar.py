#!/usr/bin/env python3
"""Movistar Estudiantes (masculino, 26/27) -> partidos.json + estudiantes.ics.

Orquesta las fuentes de la FEB, conserva el histórico de Copa, aplica las horas
verificadas manualmente y genera el ICS con el paquete común ``calendarios``.

Solo stdlib. Los UIDs son estables por jornada/ronda para que Google/Apple
actualicen cada partido en su sitio, sin duplicados.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# Permite ejecutar tanto `python3 -m deportes.baloncesto.generar` como
# `python3 deportes/baloncesto/generar.py` desde la raíz del repo.
BASE_REPO = Path(__file__).resolve().parents[2]
if str(BASE_REPO) not in sys.path:
    sys.path.insert(0, str(BASE_REPO))

from calendarios.archivos import escribir_json, escritura_atomica  # noqa: E402
from calendarios.ics import MADRID, Evento, generar_ics  # noqa: E402
from calendarios.log import log, warn  # noqa: E402
from deportes.baloncesto import fuentes  # noqa: E402

DIRECTORIO = Path(__file__).resolve().parent
JSON_PATH = DIRECTORIO / "datos" / "partidos.json"
SEDES_PATH = DIRECTORIO / "datos" / "sedes.json"
FECHAS_PATH = DIRECTORIO / "datos" / "fechas_reales.json"
ICS_PATH = DIRECTORIO / "estudiantes.ics"

CALENDARIO_NOMBRE = "Movistar Estudiantes 26/27"


def etiqueta(p: dict) -> str:
    if p.get("competicion") == "copa":
        return f"Copa {p.get('ronda') or ('J' + str(p.get('jornada', '?')))}"
    return f"J{p.get('jornada', '?')}"


def resumen(p: dict) -> str:
    emoji = "🏆" if p.get("competicion") == "copa" else "🏀"
    tag = etiqueta(p)
    local = "Estu" if p.get("casa") else p.get("rival", "Rival")
    visitante = p.get("rival", "Rival") if p.get("casa") else "Estu"
    if (
        p.get("estado") == "jugado"
        and "resultado_local" in p
        and "resultado_visitante" in p
    ):
        marca = "✅" if p.get("victoria") else "❌"
        gl, gv = p["resultado_local"], p["resultado_visitante"]
        return f"{emoji} {local} - {visitante} ({tag}: {gl}-{gv} {marca})"
    return f"{emoji} {local} - {visitante} ({tag})"


def descripcion(p: dict) -> str:
    ambito = f"{p.get('competicion_nombre', '')} · {etiqueta(p)}"
    lineas = [
        ambito,
        (("Estu en casa" if p.get("casa") else "Estu fuera")
         + f" vs {p.get('rival', 'Rival')}"),
    ]
    if (
        p.get("estado") == "jugado"
        and "resultado_estu" in p
        and "resultado_rival" in p
    ):
        lineas.append(
            f"Resultado: Estu {p['resultado_estu']}-{p['resultado_rival']} "
            + ("victoria ✅" if p.get("victoria") else "derrota ❌")
        )
    else:
        dt_raw = p.get("inicio_madrid") or ""
        try:
            dt = datetime.fromisoformat(dt_raw) if dt_raw else None
        except (TypeError, ValueError):
            dt = None
        if dt is not None:
            if p.get("fecha_provisional"):
                lineas.append(
                    f"Inicio provisional: {dt.strftime('%d/%m/%Y %H:%M')} "
                    "(Madrid, por confirmar FEB)"
                )
            else:
                lineas.append(f"Inicio: {dt.strftime('%d/%m/%Y %H:%M')} (Madrid)")
        else:
            fj = p.get("fecha_jornada", "")
            if re.match(r"\d{1,2}[/-]\d{1,2}[/-]\d{4}", str(fj or "")):
                lineas.append(f"Fecha por determinar (semana del {fj}, por confirmar FEB)")
            else:
                lineas.append("Fecha por determinar (por confirmar FEB)")
    lineas.append(f"Acta FEB: {p.get('acta', '')}")
    return "\n".join(lineas)


def sede_txt(p: dict) -> str:
    s = p.get("sede") or {}
    return ", ".join(x for x in (s.get("pabellon"), s.get("direccion")) if x)


def _inicio_evento(p: dict) -> datetime | None:
    """Fecha del evento: inicio real, o fecha_jornada a las 12:00, o None si no hay nada."""
    dt_raw = p.get("inicio_madrid") or ""
    if dt_raw:
        try:
            dt = datetime.fromisoformat(dt_raw)
        except (TypeError, ValueError):
            return None
        if dt.tzinfo is None:
            return dt.replace(tzinfo=MADRID)
        return dt.astimezone(MADRID)
    fj = p.get("fecha_jornada", "")
    m = re.match(r"(\d{1,2})[/-](\d{1,2})[/-](\d{4})", str(fj or ""))
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return datetime(y, mo, d, 12, 0, tzinfo=MADRID)
        except ValueError:
            return None
    return None


def a_eventos(partidos: list[dict]) -> list[Evento]:
    """Convierte partidos normalizados en eventos ICS; omite los irrecuperables."""
    eventos: list[Evento] = []
    omitidos = 0
    for p in partidos:
        try:
            uid = str(p.get("uid") or "").strip()
            acta = str(p.get("acta") or "").strip()
            if not uid or not acta:
                raise KeyError(f"uid/acta ausentes ({uid!r})")
            inicio = _inicio_evento(p)
            if inicio is None:
                raise ValueError("sin fecha (TBD sin provisional)")
            lugar = sede_txt(p) or (fuentes.CASA_PABELLON if p.get("casa") else "")
            eventos.append(
                Evento(
                    uid=uid,
                    inicio=inicio,
                    fin=inicio + timedelta(hours=2),
                    resumen=resumen(p),
                    descripcion=descripcion(p),
                    url=acta,
                    lugar=lugar,
                    estado="TENTATIVE" if p.get("fecha_provisional") else "CONFIRMED",
                    transparencia="TRANSPARENT",
                )
            )
        except Exception as e:  # noqa: BLE001 - un partido roto no debe tumbar el ICS
            warn(f"ics: se omite {p.get('uid', '?')}: {e}")
            omitidos += 1
    if omitidos:
        warn(f"ics: {omitidos} evento(s) omitido(s)")
    return eventos


def _cargar_previo() -> list[dict]:
    if not JSON_PATH.exists():
        return []
    try:
        data = json.loads(JSON_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception as e:  # noqa: BLE001 - se puede regenerar desde cero
        warn(f"previo {JSON_PATH} ilegible ({e}); se sigue sin histórico")
        return []


def main() -> None:
    prev = _cargar_previo()
    prev_by_uid = {p["uid"]: p for p in prev if isinstance(p, dict) and p.get("uid")}
    prev_liga = [
        p
        for p in prev
        if isinstance(p, dict) and p.get("uid") and p.get("competicion") == "liga"
    ]
    prev_copa = [
        p
        for p in prev
        if isinstance(p, dict) and p.get("uid") and p.get("competicion") == "copa"
    ]
    feb_fallback = False

    try:
        liga = fuentes.parse_liga(fuentes.fetch(fuentes.LIGA_URL))
        if len(liga) != 34:
            raise ValueError(f"liga: esperaba 34 jornadas, hay {len(liga)}")
    except Exception as e:  # noqa: BLE001 - fallback al histórico
        if prev_liga:
            warn(
                f"liga: fallo ({e}); se reutilizan {len(prev_liga)} partidos previos "
                "y no se tumba la ejecución"
            )
            liga = prev_liga
            feb_fallback = True
        else:
            raise

    try:
        copa_nueva = fuentes.parse_copa(fuentes.fetch(fuentes.COPA_URL))
    except Exception as e:  # noqa: BLE001 - fallback al histórico
        if prev_copa:
            warn(
                f"copa: fallo ({e}); se conserva el histórico ({len(prev_copa)}) "
                "y no se tumba la ejecución"
            )
            copa_nueva = []
            feb_fallback = True
        else:
            raise

    # Histórico de copa: la página FEB solo muestra la fase actual; conservar rondas viejas
    uids_nuevos = {p["uid"] for p in copa_nueva}
    duplicadas = [u for u in uids_nuevos if u in {p["uid"] for p in liga}]
    if duplicadas:
        raise ValueError(f"UIDs de copa colisionan con liga: {duplicadas}")
    copa_hist = [
        p
        for p in prev_copa
        if isinstance(p, dict) and p.get("uid") and p.get("uid") not in uids_nuevos
    ]
    if copa_nueva:
        log(f"copa: nueva={len(copa_nueva)} histórico_conservado={len(copa_hist)}")
    elif copa_hist:
        log(f"copa: sin novedades, histórico={len(copa_hist)}")
    copa = copa_hist + copa_nueva

    partidos = liga + copa
    hoy = datetime.now(MADRID).date()
    # Conservar inicio_madrid de pendientes que pasan a jugados (fecha real del evento)
    for p in partidos:
        old = prev_by_uid.get(p["uid"])
        if old and p.get("estado") == "jugado" and old.get("inicio_madrid") and "inicio_madrid" not in p:
            p["inicio_madrid"] = old["inicio_madrid"]
            if old.get("fecha_provisional"):
                p["fecha_provisional"] = True
            else:
                p.pop("fecha_provisional", None)
        # No pisar una hora real ya publicada con un provisional TBD, salvo que
        # esa hora sea de un partido ya pasado (probable aplazamiento).
        if old and not old.get("fecha_provisional") and p.get("fecha_provisional"):
            if old.get("inicio_madrid"):
                try:
                    dt_viejo = datetime.fromisoformat(old["inicio_madrid"])
                    if dt_viejo.tzinfo is not None:
                        dt_viejo = dt_viejo.astimezone(MADRID)
                    vieja = dt_viejo.date()
                except (TypeError, ValueError):
                    vieja = None
                if vieja is not None and vieja >= hoy:
                    p["inicio_madrid"] = old["inicio_madrid"]
                    p.pop("fecha_provisional", None)

    # Rescates manuales verificados (partidos jugados antes del primer scrape): mandan sobre todo
    if FECHAS_PATH.exists():
        try:
            seed = json.loads(FECHAS_PATH.read_text(encoding="utf-8"))
        except Exception as e:  # noqa: BLE001
            warn(f"seed {FECHAS_PATH} ilegible ({e})")
            seed = {}
        if isinstance(seed, dict):
            for k, v in seed.items():
                if k.startswith("_"):
                    continue
                try:
                    datetime.fromisoformat(v)
                except Exception:  # noqa: BLE001
                    warn(f"seed: {k} con fecha inválida ({v!r}); se ignora")
                    continue
                for p in partidos:
                    if p.get("uid") == k:
                        p["inicio_madrid"] = v
                        p.pop("fecha_provisional", None)

    # Validar UIDs antes de tocar el disco: nada de JSON nuevo + ICS viejo.
    conteo = Counter(p.get("uid", "?") for p in partidos)
    dups = sorted(u for u, n in conteo.items() if n > 1)
    if dups:
        raise ValueError(f"UIDs duplicados {dups}")

    # Sedes: caché por partido (un fallo de sede nunca tumba la ejecución)
    try:
        sedes = json.loads(SEDES_PATH.read_text(encoding="utf-8")) if SEDES_PATH.exists() else {}
        if not isinstance(sedes, dict):
            warn(f"sedes {SEDES_PATH} no es un objeto; se empieza vacío")
            sedes = {}
        else:
            sedes = {k: v for k, v in sedes.items() if isinstance(v, dict)}
    except Exception as e:  # noqa: BLE001
        warn(f"sedes {SEDES_PATH} ilegible ({e}); se empieza vacío")
        sedes = {}
    for p in partidos:
        pid = p.get("feb_partido_id")
        if not pid:
            warn(f"sede: {p.get('uid', '?')} sin feb_partido_id; se omite la sede")
            continue
        if not sedes.get(pid):
            tag = etiqueta(p)
            try:
                sedes[pid] = fuentes.fetch_sede(pid)
                log(f"sede {tag}: {sedes[pid]}")
            except Exception as e:  # noqa: BLE001 - la sede es opcional
                warn(f"sede {tag} pid={pid}: ERROR {e}")
                sedes[pid] = sedes.get(pid, {})
    for p in partidos:
        pid = p.get("feb_partido_id")
        if pid and sedes.get(pid):
            p["sede"] = sedes[pid]

    eventos = a_eventos(partidos)
    ics = generar_ics(CALENDARIO_NOMBRE, eventos, zona=MADRID)

    escribir_json(JSON_PATH, partidos)
    sedes = {k: v for k, v in sedes.items() if v}
    escribir_json(SEDES_PATH, sedes)
    escritura_atomica(ICS_PATH, ics.encode("utf-8"))

    jug = sum(1 for p in partidos if p.get("estado") == "jugado")
    log(
        f"liga={len(liga)} copa={len(copa)} jugados={jug} "
        f"pendientes={len(partidos) - jug} eventos_ics={len(eventos)}"
    )
    log(f"json={JSON_PATH.relative_to(BASE_REPO)} ics={ICS_PATH.relative_to(BASE_REPO)}")
    if feb_fallback:
        warn("FEB_FALLBACK=true: una fuente falló y se usó histórico; revisar logs")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # noqa: BLE001
        print(f"ERROR: {e}", file=sys.stderr, flush=True)
        raise
