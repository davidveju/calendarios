# 🧩 Código de los calendarios

Todo el código vive en `scripts/`. El estado interno vive en `estado/<id>/` y en
las carpetas públicas (`deportes/...`) solo se publican los `.ics`.

## Capas

| Carpeta | Responsabilidad | Puede importar de |
|---|---|---|
| `scripts/comun/` | Motor genérico: ICS, HTTP, validación, escritura atómica, contexto, registro y runner. | Nada del repo salvo `scripts.comun`. |
| `scripts/proveedores/<fuente>/` | Parser y configuración de una fuente externa (FEB, ACB, EuroLeague, UEFA, FIFA, LALIGA, Transfermarkt, ESPN, OpenHolidays...). No conoce calendarios concretos. | `scripts.comun`. |
| `scripts/calendarios/<id>/` | Configuración, orquestación y tests de un calendario concreto. | `scripts.comun` y `scripts.proveedores`. |

Regla práctica: si una pieza sirve para dos equipos de la misma competición,
va a `proveedores`; si sirve para cualquier calendario, va a `comun`; si solo
tiene sentido para un calendario, se queda en `calendarios/<id>`.

## Cómo se resuelven las rutas

`scripts/comun/contexto.py` es la única fuente de verdad:

```python
from scripts.comun.contexto import contexto_desde_ejecucion

ctx = contexto_desde_ejecucion(__name__, __file__)
ctx.raiz          # raíz del repositorio
ctx.codigo        # scripts/calendarios/<id>
ctx.estado        # estado/<id>  (interno, persistente)
ctx.publicacion   # carpeta del ICS público
ctx.ruta_ics      # ruta pública declarada en el manifiesto
ctx.ruta_estado("partidos.json")  # estado/<id>/partidos.json
```

El `id` debe coincidir con la ruta bajo `scripts/calendarios/` y usar
minúsculas, números y guiones bajos separados por `/`. Un manifiesto inválido se
omite (con aviso) para no bloquear al resto de calendarios; `--estricto` lo
convierte en error. Dos calendarios tampoco pueden declarar el mismo `ics`.

## Manifiesto

```json
{
  "nombre": "Movistar Estudiantes 26/27",
  "descripcion": "Partidos de liga, Copa y playoffs",
  "ics": "deportes/baloncesto/estudiantes.ics",
  "generador": "generar.py",
  "datos": ["partidos.json", "sedes.json", "fechas_reales.json"],
  "zona": "Europe/Madrid"
}
```

- `ics`: ruta relativa al repositorio. Es el único artefacto público.
- `datos`: rutas relativas a `estado/<id>/`. No se publican como calendario.

La carpeta pública puede ser compartida por varios equipos; lo que no se
comparte es `estado/<id>/` ni el prefijo de UIDs.

## Añadir un equipo de la FEB

No hace falta duplicar `scripts/proveedores/feb/fuentes.py`. Crea el nuevo
calendario y una configuración:

```python
# scripts/calendarios/deportes/baloncesto/otro_equipo/config.py
from scripts.proveedores.feb.config import ConfigFEB

CONFIG = ConfigFEB(
    equipo_id="1234567",
    equipo_corto="Otro",
    temporada="26/27",
    uid_prefix="otro-2627",
    uid_dominio="otro-calendario",
    liga_url="https://competiciones.feb.es/estadisticas/Calendario.aspx",
    copa_url="https://www.feb.es/competiciones/resultados/copaespaa/73/2026",
    liga_nombre="Primera FEB 26/27",
    copa_nombre="Copa España 26/27",
    casa_pabellon="Pabellón, Ciudad",
)
```

Su manifiesto podría publicar el ICS junto al de Estudiantes:

```json
{
  "nombre": "Otro equipo 26/27",
  "ics": "deportes/baloncesto/otro_equipo.ics",
  "generador": "generar.py",
  "datos": ["partidos.json", "sedes.json"],
  "zona": "Europe/Madrid"
}
```

El código estaría en `scripts/calendarios/deportes/baloncesto/otro_equipo/` y su
estado en `estado/deportes/baloncesto/otro_equipo/`. El prefijo y el dominio de
los UIDs deben ser propios de cada calendario.

## Tests

```bash
./scripts/test.sh                                      # todo
python3 -m unittest discover -s scripts/comun/tests -t . -v
python3 -m unittest discover -s scripts/proveedores/feb/tests -t . -v
python3 -m unittest discover -s scripts/calendarios/deportes/baloncesto/estudiantes/tests -t . -v
```

`./scripts/test.sh` descubre automáticamente los tests de `scripts/comun/`,
cada proveedor con `tests/` y todos los calendarios.

Los tests no usan red: los parsers reciben HTML de ejemplo y los generadores se
prueban con partidos normalizados.
