"""Combinación de partidos de varias fuentes conservando su identidad.

La regla importante es que un partido que ya estaba en el estado mantenga su
``uid`` aunque cambie la fuente que lo publica. Así los suscriptores del ICS no
ven un evento duplicado al pasar de Transfermarkt a UEFA o FIFA.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime

from scripts.comun.log import warn
from scripts.comun.nombres import similitud


def _elegir_previo(
    previos: Sequence[dict],
    *,
    nuevos_indice: set[int],
    partido: dict,
    tolerancia: int,
) -> int | None:
    """Busca el partido previo equivalente, tolerando sede neutral si hace falta."""

    def candidatos(exigir_casa: bool) -> list[tuple[float, float, int]]:
        out: list[tuple[float, float, int]] = []
        for indice, previo in enumerate(previos):
            if indice in nuevos_indice:
                continue
            if not _mismo_partido(previo, partido, tolerancia, exigir_casa=exigir_casa):
                continue
            dias = _dias(previo, partido) or 0.0
            sim = similitud(previo.get("rival", ""), partido.get("rival", ""))
            out.append((dias, -sim, indice))
        out.sort()
        return out

    for exigir_casa, sim_minima in ((True, 0.5), (False, 0.75)):
        lista = candidatos(exigir_casa)
        if not lista:
            continue
        dias, negativo, indice = lista[0]
        segundo = lista[1] if len(lista) > 1 else None
        if exigir_casa:
            # Si hay una fecha claramente más cercana, no hace falta que el
            # nombre coincida. Si están empatados, exigimos similitud.
            if segundo is None or dias < segundo[0] or -negativo >= sim_minima:
                return indice
        elif -negativo >= sim_minima and (segundo is None or dias < segundo[0] or -negativo > -segundo[1]):
            # Al relajar la sede (campo neutral) exigimos siempre similitud.
            return indice
    return None


def _fecha(partido: dict) -> datetime | None:
    raw = (partido.get("inicio_madrid") or "").strip()
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None


def _dias(a: dict, b: dict) -> float | None:
    fecha_a, fecha_b = _fecha(a), _fecha(b)
    if fecha_a is None or fecha_b is None:
        return None
    return abs((fecha_a - fecha_b).total_seconds()) / 86400


def _mismo_partido(
    previo: dict, nuevo: dict, tolerancia_dias: int, *, exigir_casa: bool = True
) -> bool:
    if previo.get("competicion") != nuevo.get("competicion"):
        return False
    if exigir_casa and bool(previo.get("casa")) != bool(nuevo.get("casa")):
        return False
    dias = _dias(previo, nuevo)
    return dias is not None and dias <= tolerancia_dias


def fusionar(
    previos: Sequence[dict],
    nuevos: Sequence[dict],
    *,
    tolerancia_dias: int = 7,
) -> list[dict]:
    """Devuelve ``nuevos`` reutilizando el ``uid`` del partido equivalente.

    Un partido se considera el mismo si coincide la competición, la condición
    de local/visitante y la fecha (con una tolerancia). Si hay varios
    candidatos, se desempata por similitud del nombre del rival.
    """
    usados: set[int] = set()
    salida: list[dict] = []
    for original in nuevos:
        nuevo = dict(original)
        elegido = _elegir_previo(previos, nuevos_indice=usados, partido=nuevo, tolerancia=tolerancia_dias)
        if elegido is not None:
            nuevo["uid"] = previos[elegido]["uid"]
            usados.add(elegido)
        salida.append(nuevo)
    return salida


def _deduplicar(partidos: Sequence[dict], *, tolerancia_dias: int = 1) -> list[dict]:
    """Elimina el mismo partido si llega por dos fuentes distintas.

    Se conserva el primero, que es el de la fuente oficial porque
    :func:`recolectar` la coloca delante de Transfermarkt.
    """
    salida: list[dict] = []
    for partido in partidos:
        duplicado = False
        for previo in salida:
            if previo.get("competicion") != partido.get("competicion"):
                continue
            dias = _dias(previo, partido)
            if dias is None or dias > tolerancia_dias:
                continue
            misma_sede = bool(previo.get("casa")) == bool(partido.get("casa"))
            sim = similitud(previo.get("rival", ""), partido.get("rival", ""))
            if misma_sede or sim >= 0.75:
                duplicado = True
                break
        if duplicado:
            warn(
                "fusión: se ignora un partido duplicado "
                f"({partido.get('competicion')}, {partido.get('rival')}, "
                f"{partido.get('inicio_madrid')})"
            )
            continue
        salida.append(partido)
    return salida


def recolectar(
    tm_partidos: Sequence[dict] | None,
    fuentes: Sequence[tuple[str, set[str], Callable[[], list[dict]]]],
) -> list[dict]:
    """Combina Transfermarkt con fuentes oficiales y aplica *fallback*.

    ``fuentes`` contiene ``(nombre, competiciones, obtener)``. ``obtener`` debe
    devolver una lista de partidos o lanzar una excepción. Si una fuente falla,
    se usan los partidos de Transfermarkt para sus competiciones.
    """
    oficiales: list[dict] = []
    fallidas: set[str] = set()
    cubiertas: set[str] = set()
    for nombre, competiciones, obtener in fuentes:
        cubiertas.update(competiciones)
        try:
            partidos = obtener()
        except Exception as e:  # noqa: BLE001 - la fuente se sustituye por TM
            warn(f"{nombre}: fallo ({e}); se intenta Transfermarkt")
            fallidas.update(competiciones)
            continue
        if not partidos:
            warn(f"{nombre}: sin partidos; se intenta Transfermarkt")
            fallidas.update(competiciones)
            continue
        oficiales.extend(partidos)

    combinados = list(oficiales)
    if tm_partidos is not None:
        combinados.extend(
            partido
            for partido in tm_partidos
            if partido.get("competicion") not in cubiertas
            or partido.get("competicion") in fallidas
        )
    combinados = _deduplicar(combinados)
    if not combinados:
        raise ValueError("ninguna fuente devolvió partidos")
    return combinados


def pendientes_pasados(partidos: Sequence[dict], *, ahora: datetime | None = None) -> list[dict]:
    """Partidos con fecha pasada que siguen en estado pendiente.

    Un pendiente con fecha pasada indica que la fuente aún no publica el
    resultado (o que la fuente falló y se conservó el histórico). Sirve para
    avisar en logs en lugar de dejar el ICS desactualizado en silencio.
    """
    ref = ahora or datetime.now()
    return [
        p
        for p in partidos
        if p.get("estado") == "pendiente"
        and (f := _fecha(p)) is not None
        and f < ref
    ]
