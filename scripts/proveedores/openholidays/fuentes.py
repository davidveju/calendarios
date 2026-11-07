"""Genera festivos oficiales de la provincia/comunidad de Madrid."""

from __future__ import annotations

import json

from datetime import date, timedelta


MESES_EN = {}


def _pascua(anio: int) -> date:
    """Calcula el Domingo de Pascua ortodoxo/gregoriano para ``anio``."""
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)


def _base(anio: int) -> list[tuple[int, int, str]]:
    pascua = _pascua(anio)
    jueves_santo = pascua - timedelta(days=3)
    viernes_santo = pascua - timedelta(days=2)
    return [
        (1, 1, "Año Nuevo"),
        (1, 6, "Epifanía del Señor"),
        (jueves_santo.month, jueves_santo.day, "Jueves Santo"),
        (viernes_santo.month, viernes_santo.day, "Viernes Santo"),
        (5, 1, "Día del Trabajador"),
        (5, 2, "Fiesta de la Comunidad de Madrid"),
        (5, 15, "San Isidro Labrador (fiesta local de Madrid)"),
        (7, 25, "Santiago Apóstol"),
        (8, 15, "Asunción de la Virgen"),
        (10, 12, "Fiesta Nacional de España"),
        (11, 1, "Todos los Santos"),
        (11, 9, "Nuestra Señora de la Almudena (fiesta local de Madrid)"),
        (12, 6, "Día de la Constitución Española"),
        (12, 8, "Inmaculada Concepción"),
        (12, 25, "Navidad"),
    ]


def generar_festivos(config, desde: int, hasta: int) -> list[dict]:
    partidos: list[dict] = []
    vistos: set[str] = set()
    for year in range(desde, hasta + 1):
        items = list(_base(year))
        for extra_mes, extra_dia, extra_nombre in (config.extra_city or ()):
            items.append((extra_mes, extra_dia, extra_nombre))
        for (mes, dia, nombre) in items:
            fecha = date(year, mes, dia)
            iso = fecha.isoformat()
            kickoff = f"{iso}T00:00"
            fin = f"{iso}T23:59"
            # mover al lunes si cae en domingo
            if fecha.weekday() == 6:  # domingo
                fecha = fecha + timedelta(days=1)
                iso = fecha.isoformat()
                kickoff = f"{iso}T00:00"
                fin = f"{iso}T23:59"
                nombre_prev = nombre
                nombre = f"Lunes siguiente a {nombre}" if False else nombre_prev
            uid = f"{config.uid_prefix}-{iso}@{config.uid_dominio}"
            if uid in vistos:
                continue
            vistos.add(uid)
            partidos.append(
                {
                    "uid": uid,
                    "competicion": "festivo",
                    "competicion_nombre": config.nombre_calendario,
                    "estado": "pendiente",
                    "casa": True,
                    "rival": nombre,
                    "inicio_madrid": kickoff,
                    "fin_madrid": fin,
                    "fecha_provisional": False,
                    "acta": "https://www.madrid.es/",
                    "ronda": nombre,
                }
            )
    return partidos


def obtener_festivos(texto: str, config) -> list[dict]:
    try:
        data = json.loads(texto)
    except Exception:
        return []
    partidos = []
    vistos = set()
    for h in data:
        iso = h.get("startDate")
        if not iso:
            continue
        nombre = h.get("name", [{}])[0].get("text", "Festivo") if isinstance(h.get("name"), list) else "Festivo"
        for n in (h.get("name") or []):
            if n.get("language") == "ES":
                nombre = n.get("text", nombre)
        uid = f"{config.uid_prefix}-{iso}@{config.uid_dominio}"
        if uid in vistos:
            continue
        vistos.add(uid)
        partidos.append(
            {
                "uid": uid,
                "competicion": "festivo",
                "competicion_nombre": config.nombre_calendario,
                "estado": "pendiente",
                "casa": True,
                "rival": nombre,
                "inicio_madrid": f"{iso}T00:00",
                "fin_madrid": f"{iso}T23:59",
                "fecha_provisional": False,
                "acta": "https://openholidaysapi.org",
                "ronda": nombre,
            }
        )
    return partidos
