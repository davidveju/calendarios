# 📅 Calendarios automáticos

Calendarios personales en formato iCalendar (`.ics`) generados desde sus fuentes
originales y actualizados solos con GitHub Actions. Te suscribes una vez por
calendario y los cambios (horarios, resultados, nuevas citas…) llegan sin hacer
nada.

## Calendarios publicados

| Calendario | Fichero | Actualización |
|---|---|---|
| 🏀 [Movistar Estudiantes 26/27](deportes/baloncesto/) | [estudiantes.ics](deportes/baloncesto/estudiantes.ics) | lunes, miércoles y viernes 12:00 UTC |

> El antiguo repo `davidveju/estudiantes-calendario` queda archivado. La nueva
> URL de suscripción es:
>
> ```text
> https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/baloncesto/estudiantes.ics
> ```
>
> Si ya estabas suscrito, elimina el calendario antiguo y añade esta URL.

## 📲 Suscribirse

### Google Calendar

1. Abre [Google Calendar](https://calendar.google.com).
2. En `Otros calendarios`, pulsa `+` → `Desde URL`.
3. Pega la URL del `.ics` y pulsa `Añadir calendario`.

### Apple Calendar (iPhone / Mac)

1. Ajustes → Calendario → Cuentas → Añadir cuenta → Otra → Añadir calendario
   suscrito.
2. Pega la URL y pulsa Siguiente.

### Outlook

1. Calendario → Añadir calendario → Suscribirse desde la web.
2. Pega la URL, ponle nombre e importa.

> Google y Apple refrescan los calendarios suscritos cada 12–24 h. No sirven
> para seguir un evento en directo.

## 🗂️ Estructura: código separado de datos

El repositorio tiene dos zonas con responsabilidades distintas:

```text
calendarios/
├── scripts/                        # TODO el código
│   ├── comun/                      # motor reutilizable y agnóstico de fuentes
│   │   ├── ics.py                  # generación iCalendar
│   │   ├── validacion.py           # validador RFC 5545 byte a byte
│   │   ├── http.py                 # descargas con reintentos
│   │   ├── archivos.py             # escritura atómica de JSON/ICS
│   │   ├── contexto.py             # rutas de código y salida de cada calendario
│   │   ├── registro.py             # descubre y valida los calendario.json
│   │   ├── runner.py               # ejecuta calendarios aislados entre sí
│   │   └── tests/                  # tests del motor
│   ├── proveedores/                # lógica compartida de fuentes externas
│   │   └── feb/                    # parser configurable de la FEB
│   │       ├── config.py           # ConfigFEB (equipo, URLs, UIDs…)
│   │       ├── fuentes.py          # parsers de liga y Copa
│   │       └── tests/
│   ├── calendarios/                # código y configuración de cada calendario
│   │   └── deportes/
│   │       └── baloncesto/
│   │           ├── calendario.json # manifiesto
│   │           ├── config.py       # instancia de ConfigFEB para el Estu
│   │           ├── generar.py      # orquestación + eventos ICS
│   │           └── tests/
│   ├── __main__.py                 # CLI: listar / actualizar / validar
│   ├── actualizar.sh               # atajo local del runner
│   └── test.sh                     # tests de todo el monorepo
├── deportes/                       # SOLO datos, caché y .ics publicados
│   └── baloncesto/
│       ├── estudiantes.ics         # fichero publicado
│       ├── datos/                  # estado, sedes y horas verificadas
│       └── README.md
└── .github/workflows/
    ├── _calendario.yml             # workflow reutilizable
    ├── deportes-baloncesto.yml     # schedule propio de este calendario
    └── tests.yml                   # tests en push/PR
```

### El `id` lo namespacea todo

Cada calendario se identifica con un `id` estable, por ejemplo
`deportes/baloncesto`. Ese mismo id determina, sin ambigüedad:

| Uso | Ruta |
|---|---|
| Código | `scripts/calendarios/deportes/baloncesto/` |
| Módulo Python | `scripts.calendarios.deportes.baloncesto.generar` |
| Datos/caché y `.ics` | `deportes/baloncesto/` |
| URL pública | `…/main/deportes/baloncesto/estudiantes.ics` |

Así dos equipos o competiciones no comparten directorios de estado por
accidente, aunque usen el mismo proveedor. El código de la FEB es común; la
configuración (equipo, temporada, URLs y prefijo de UIDs) es de cada calendario.

Cada calendario se describe con un `calendario.json` que vive junto a su código:

```json
{
  "nombre": "Nombre visible en el ICS",
  "descripcion": "Qué contiene",
  "ics": "calendario.ics",
  "generador": "generar.py",
  "datos": ["datos/estado.json"],
  "zona": "Europe/Madrid"
}
```

Las rutas de `datos` son relativas a la salida `<id>/`, nunca al código. El
runner valida que existan y que sean JSON correctos después de generar.

## ➕ Añadir un calendario

1. Crea el paquete `scripts/calendarios/<id>/` con `__init__.py`, su
   `calendario.json`, su generador y sus tests.
2. Reutiliza el motor de `scripts.comun`. Si la fuente es la FEB, crea una
   instancia de `ConfigFEB` en `config.py` y usa
   `scripts.proveedores.feb.fuentes`; no copies el parser.
3. En el generador, obtén las rutas con `contexto_desde_modulo(__name__)` y
   escribe en `ctx.ruta_ics` / `ctx.ruta_dato(...)`. Nunca escribas junto al
   código.
4. Añade `.github/workflows/<categoria>-<nombre>.yml` con su propio `schedule`,
   `workflow_dispatch` y `concurrency`, llamando al workflow reutilizable:

```yaml
name: Calendario · Categoría · Nombre

on:
  schedule:
    - cron: "0 9 * * 1" # el horario que necesite
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: calendario-categoria-nombre
  cancel-in-progress: false

jobs:
  actualizar:
    uses: ./.github/workflows/_calendario.yml
    with:
      id: categoria/nombre
      ics: calendario.ics
```

5. Comprueba que aparece y se ejecuta:

```bash
python3 -m scripts listar
python3 -m scripts actualizar --solo categoria/nombre
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
python3 -m scripts actualizar --solo deportes/baloncesto
python3 -m scripts actualizar

# Valida un ICS (o un directorio con .ics)
python3 -m scripts validar deportes/baloncesto/estudiantes.ics

# Tests de todo el monorepo
./scripts/test.sh
```

## 🛡️ Aislamiento de fallos

- **GitHub Actions:** cada calendario tiene su propio workflow y su propio
  `schedule`. Si la FEB cambia o un calendario falla, solo falla ese workflow;
  los demás siguen ejecutándose.
- **Código y tests:** el workflow deriva `scripts/calendarios/$ID/tests` de su
  propio id y no ejecuta los tests de otros calendarios.
- **Commit:** cada workflow hace `git add` únicamente de su directorio de salida
  `<id>/`. Un calendario nunca publica cambios de otro.
- **Runner local:** cada generador se ejecuta en un subproceso independiente.
  `python3 -m scripts actualizar` captura el fallo, lo muestra en el resumen y
  continúa con el siguiente.
- **Dentro de un calendario:** las fuentes que fallan usan el histórico guardado
  cuando es posible (por ejemplo, la liga o la Copa de la FEB), y las sedes son
  opcionales: nunca tumban la generación del ICS.
- **Publicación concurrente:** si dos calendarios terminan a la vez, el workflow
  reintenta `pull --rebase` + `push` antes de darse por vencido.

## 🔄 Cómo funciona una actualización

1. El workflow del calendario se lanza por `schedule` o a mano.
2. Se ejecutan los tests del motor, los proveedores y ese calendario.
3. El generador descarga sus fuentes, actualiza su estado en `<id>/datos/` y
   escribe el `.ics` en `<id>/`.
4. Se valida el ICS a nivel de bytes (CRLF, plegado ≤75 octetos, UIDs únicos).
5. Si hay cambios reales (se ignora un `DTSTAMP` nuevo), se hace commit y push.
6. GitHub sirve el `.ics` por `raw.githubusercontent.com` y tu calendario se
   actualiza en la siguiente sincronización.

## 📄 Licencia

[MIT](LICENSE)
