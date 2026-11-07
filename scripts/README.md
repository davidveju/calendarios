# 🧩 Código de los calendarios

Todo el código vive en `scripts/`. Los directorios de datos (`<id>/`) solo
contienen el `.ics` publicado y su estado/caché.

## Capas

| Carpeta | Responsabilidad | Puede importar de |
|---|---|---|
| `scripts/comun/` | Motor genérico: ICS, HTTP, validación, escritura atómica, contexto, registro y runner. | Nada del repo salvo `scripts.comun`. |
| `scripts/proveedores/<fuente>/` | Parser y configuración de una fuente externa (por ahora la FEB). No conoce calendarios concretos. | `scripts.comun`. |
| `scripts/calendarios/<id>/` | Configuración, orquestación y tests de un calendario concreto. | `scripts.comun` y `scripts.proveedores`. |

Regla práctica: si una pieza sirve para dos equipos de la misma competición,
va a `proveedores`; si sirve para cualquier calendario, va a `comun`; si solo
tiene sentido para un calendario, se queda en `calendarios/<id>`.

## Cómo se resuelven las rutas

`scripts/comun/contexto.py` es la única fuente de verdad:

```python
from scripts.comun.contexto import contexto_desde_modulo

ctx = contexto_desde_modulo(__name__)
ctx.raiz          # raíz del repositorio
ctx.codigo        # scripts/calendarios/<id>
ctx.salida        # <id>
ctx.ruta_ics      # <id>/<ics del manifiesto>
ctx.ruta_dato("datos/partidos.json")  # <id>/datos/partidos.json
```

El `id` debe coincidir con la ruta bajo `scripts/calendarios/` y usar
minúsculas, números y guiones bajos separados por `/`. Un manifiesto inválido se
omite (con aviso) para no bloquear al resto de calendarios; `--estricto` lo
convierte en error.

## Añadir un equipo de la FEB

No hace falta duplicar `scripts/proveedores/feb/fuentes.py`. Crea el nuevo
calendario y una configuración:

```python
# scripts/calendarios/deportes/otro_equipo/config.py
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

El prefijo y el dominio de los UIDs deben ser propios de cada calendario para
que dos equipos no colisionen aunque compartan jornada y competición.

## Tests

```bash
./scripts/test.sh                                      # todo
python3 -m unittest discover -s scripts/comun/tests -t . -v
python3 -m unittest discover -s scripts/proveedores/feb/tests -t . -v
python3 -m unittest discover -s scripts/calendarios/deportes/baloncesto/tests -t . -v
```

Los tests no usan red: los parsers reciben HTML de ejemplo y los generadores se
prueban con partidos normalizados.
