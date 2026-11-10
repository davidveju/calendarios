# 📅 Calendarios automáticos

Calendarios personales en formato iCalendar (`.ics`) generados desde sus fuentes
originales y actualizados con GitHub Actions. Te suscribes una vez por
calendario y los cambios (horarios, resultados, nuevas citas…) llegan sin hacer
nada.

## Calendarios publicados

| Calendario | Fichero | Actualización |
|---|---|---|
| 🏀 Movistar Estudiantes | [estudiantes.ics](https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/baloncesto/estudiantes.ics) | lunes, miércoles y viernes 12:00 UTC |
| 🏀 Real Madrid Baloncesto | [madrid.ics](https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/baloncesto/madrid.ics) | lunes, miércoles y viernes 12:00 UTC |
| ⚽ Getafe CF | [getafe.ics](https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/getafe.ics) | lunes, miércoles y viernes 12:00 UTC |
| ⚽ Real Madrid | [madrid.ics](https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/madrid.ics) | lunes, miércoles y viernes 12:00 UTC |
| ⚽ Selección Española | [espana.ics](https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/espana.ics) | lunes, miércoles y viernes 12:00 UTC |
| 🎉 Festivos de Madrid | [madrid.ics](https://raw.githubusercontent.com/davidveju/calendarios/main/festivos/madrid.ics) | el 1 de cada mes 08:00 UTC |


## 📲 Suscribirse

Copia el enlace directo del calendario que quieres (columna **Fichero** de la tabla,
ya es una URL del tipo `raw.githubusercontent.com/.../<fichero>.ics`) y añádelo como
calendario por URL en Google Calendar, Apple Calendar u Outlook.

De Google Calendar en concreto: `Otros calendarios` → `+` → `Desde URL` y pega la
URL directa del `.ics`.

### Apple Calendar (iPhone / Mac)

1. Ajustes → Calendario → Cuentas → Añadir cuenta → Otra → Añadir calendario
   suscrito.
2. Pega la URL y pulsa Siguiente.

### Outlook

1. Calendario → Añadir calendario → Suscribirse desde la web.
2. Pega la URL, ponle nombre e importa.

> Google y Apple refrescan los calendarios suscritos cada 12–24 h. No sirven
> para seguir un evento en directo.

## 🗂️ Estructura: código, estado y publicación separados

El repositorio tiene tres zonas con responsabilidades distintas:

```text
calendarios/
├── scripts/                        # TODO el código
│   ├── comun/                      # motor reutilizable y agnóstico de fuentes
│   │   ├── ics.py                  # generación iCalendar
│   │   ├── validacion.py           # validador RFC 5545 byte a byte
│   │   ├── http.py                 # descargas con reintentos
│   │   ├── archivos.py             # escritura atómica de JSON/ICS
│   │   ├── contexto.py             # rutas de código, estado y publicación
│   │   ├── registro.py             # descubre y valida los calendario.json
│   │   ├── runner.py               # ejecuta calendarios aislados entre sí
│   │   └── tests/                  # tests del motor
│   ├── proveedores/                # lógica compartida de fuentes externas
│   │   ├── feb/ acb/ euroleague/   # baloncesto
│   │   ├── transfermarkt/ laliga/ espn/ uefa/ fifa/  # fútbol (oficiales + respaldos)
│   │   └── openholidays/           # festivos
│   ├── calendarios/                # código y configuración de cada calendario
│   │   └── deportes/
│   │       └── baloncesto/
│   │           └── estudiantes/
│   │               ├── calendario.json
│   │               ├── config.py   # instancia de ConfigFEB para el Estu
│   │               ├── generar.py  # orquestación + eventos ICS
│   │               └── tests/
│   ├── __main__.py                 # CLI: listar / actualizar / validar
│   ├── actualizar.sh               # atajo local del runner
│   └── test.sh                     # tests de todo el monorepo
├── estado/                         # estado y caché interno, por calendario
│   └── deportes/
│       └── baloncesto/
│           └── estudiantes/
│               ├── partidos.json
│               ├── sedes.json
│               └── fechas_reales.json
├── deportes/                       # SOLO artefactos públicos (.ics)
│   └── baloncesto/
│       ├── estudiantes.ics
│       └── README.md
└── .github/workflows/
    ├── actualizar-calendarios.yml          # cron diario (00:00 UTC), deportes
    ├── actualizar-calendarios-mensual.yml  # cron mensual (día 1), festivos/consulta mensual
    └── tests.yml                           # tests en push/PR
```

### El `id` namespacea código y estado; el manifiesto declara la ruta pública

Cada calendario se identifica con un `id` estable. Para Estudiantes:

```text
deportes/baloncesto/estudiantes
```

| Uso | Ruta |
|---|---|
| Código | `scripts/calendarios/deportes/baloncesto/estudiantes/` |
| Módulo Python | `scripts.calendarios.deportes.baloncesto.estudiantes.generar` |
| Estado/caché | `estado/deportes/baloncesto/estudiantes/` |
| ICS publicado | `deportes/baloncesto/estudiantes.ics` |
| URL pública | `…/main/deportes/baloncesto/estudiantes.ics` |

La ruta del ICS se declara en el manifiesto, así que **varios calendarios pueden
compartir una carpeta pública friendly** (por ejemplo
`deportes/baloncesto/estudiantes.ics` y `deportes/baloncesto/madrid.ics`) sin
compartir estado ni caché. El registro rechaza dos calendarios que intenten
publicar exactamente el mismo fichero.

Cada calendario se describe con un `calendario.json` que vive junto a su código:

```json
{
  "nombre": "Nombre visible en el ICS",
  "descripcion": "Qué contiene",
  "ics": "deportes/baloncesto/estudiantes.ics",
  "generador": "generar.py",
  "datos": ["partidos.json", "sedes.json"],
  "zona": "Europe/Madrid"
}
```

- `ics` es una ruta relativa al repositorio: el artefacto público.
- `datos` son rutas relativas a `estado/<id>/`: estado y caché internos.

El runner valida el ICS y los JSON de estado después de generar.

## ➕ Añadir un calendario

1. Crea el paquete `scripts/calendarios/<id>/` con `__init__.py`, su
   `calendario.json`, su generador y sus tests.
2. Reutiliza el motor de `scripts.comun`. Si la fuente es la FEB, crea una
   instancia de `ConfigFEB` en `config.py` y usa
   `scripts.proveedores.feb.fuentes`; no copies el parser.
3. En el generador, obtén las rutas con `contexto_desde_ejecucion(__name__, __file__)`:
   - `ctx.ruta_ics` → ICS público.
   - `ctx.ruta_estado("partidos.json")` → estado interno.
4. No hace falta añadir un workflow propio:
   - Calendarios de actualización frecuente (deportes): `actualizar-calendarios.yml`
     los descubre y actualiza a diario (00:00 UTC, excluye `festivos/*`).
   - Calendarios de consulta mensual (festivos o similares): añádelos en
     `actualizar-calendarios-mensual.yml` (otro `--solo <id>` en el paso de
     generación). Se ejecuta el día 1 de cada mes.
   Ambos pueden lanzarse a mano desde *Actions* (`workflow_dispatch`).

5. Comprueba que aparece y se ejecuta:

```bash
python3 -m scripts listar
python3 -m scripts actualizar --solo deportes/baloncesto/estudiantes
```

Si el calendario usa un proveedor nuevo, créalo en
`scripts/proveedores/<fuente>/` con su configuración y tests. El proveedor no
debe conocer equipos concretos: recibe una configuración y devuelve datos
normalizados.

> Detalles de las capas de código y de cómo añadir un proveedor:
> [`scripts/README.md`](scripts/README.md).

## 🧪 Ejecución local

Requiere Python 3.10+ (solo librería estándar; el CI usa 3.12).

```bash
# Lista los calendarios detectados
python3 -m scripts listar

# Genera uno o todos (si uno falla, sigue con el resto)
python3 -m scripts actualizar --solo deportes/baloncesto/estudiantes
python3 -m scripts actualizar

# Valida un ICS (o un directorio con .ics)
python3 -m scripts validar deportes/baloncesto/estudiantes.ics

# Tests de todo el monorepo
./scripts/test.sh
```

## 🛡️ Aislamiento de fallos

- **GitHub Actions:** dos workflows con comportamiento *best-effort*:
  `actualizar-calendarios.yml` (diario, 00:00 UTC, calendarios deportivos) y
  `actualizar-calendarios-mensual.yml` (día 1, calendarios de consulta mensual).
  Si un calendario falla, el run continúa con el resto, publica los cambios
  reales que se hayan podido generar y marca el workflow como fallido al final
  indicando qué pasos/calendarios fallaron.
- **Runner:** cada generador se ejecuta en un subproceso independiente.
  `python3 -m scripts actualizar` captura el fallo, lo muestra en el resumen y
  continúa con el siguiente.
- **Dentro de un calendario:** las fuentes que fallan usan el histórico guardado
  cuando es posible, y los datos opcionales (sedes, etc.) no tumban la generación
  del ICS.
- **Commit:** solo se publican cambios reales (se ignora un `DTSTAMP` nuevo) en
  las carpetas del workflow (`deportes/`, `festivos/`, `estado/`), con reintentos
  de `pull --rebase` + `push`.

## 🔄 Cómo funciona una actualización

1. `actualizar-calendarios.yml` se lanza a diario (00:00 UTC) para deportes, o
   `actualizar-calendarios-mensual.yml` el día 1 para festivos/consulta mensual
   (ambos también a mano).
2. Se ejecutan los tests de todo el monorepo (`scripts/test.sh`).
3. Se generan los calendarios de ese workflow. El runner ejecuta cada generador
   en un subproceso aislado y continúa aunque alguno falle.
4. Se validan los `.ics` (CRLF, plegado ≤75 octetos, RFC 5545) y los JSON de
   `estado/`.
5. Si hay cambios reales (se ignora un `DTSTAMP` nuevo), se hace commit y push.
6. Si hubo fallos de generación o validación, el workflow termina en error tras
   publicar lo posible, para notificar qué falló.
7. GitHub sirve los `.ics` por `raw.githubusercontent.com` y tu calendario se
   actualiza en la siguiente sincronización.

## 📄 Licencia

[MIT](LICENSE)
