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

1. Ajustes → Calendario → Cuentas → Añadir cuenta → Otra → Añadir calendario suscrito.
2. Pega la URL y pulsa Siguiente.

### Outlook

1. Calendario → Añadir calendario → Suscribirse desde la web.
2. Pega la URL, ponle nombre e importa.

> Google y Apple refrescan los calendarios suscritos cada 12–24 h. No sirven
> para seguir un evento en directo.

## 🗂️ Estructura

```text
calendarios/
├── calendarios/                  # paquete común (sin dependencias externas)
│   ├── ics.py                    # generación iCalendar: escapado, plegado, UTC
│   ├── validacion.py             # validador RFC 5545 byte a byte
│   ├── http.py                   # descargas con reintentos
│   ├── registro.py               # descubre y valida los calendario.json
│   ├── runner.py                 # ejecuta calendarios aislados entre sí
│   └── __main__.py               # CLI: listar / actualizar / validar
├── deportes/
│   └── baloncesto/               # 🏀 Movistar Estudiantes
│       ├── calendario.json       # manifiesto del calendario
│       ├── generar.py            # orquestación + eventos ICS
│       ├── fuentes.py            # parsers de la FEB
│       ├── estudiantes.ics       # fichero publicado
│       ├── datos/                # estado, sedes y horas verificadas
│       └── tests/                # tests sin red
├── scripts/
│   ├── actualizar.sh             # atajo local del runner
│   └── test.sh                   # tests de todo el monorepo
└── .github/workflows/
    ├── _calendario.yml           # workflow reutilizable
    └── deportes-baloncesto.yml   # schedule propio de este calendario
```

Cada calendario vive en `<categoría>/<nombre>/` y se describe con un
`calendario.json`:

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

El `id` es la ruta relativa (`deportes/baloncesto`) y debe ser un nombre de
paquete Python válido: el runner ejecuta `python3 -m deportes.baloncesto.generar`.

## ➕ Añadir un calendario

1. Crea `categoria/nombre/` con su `calendario.json`, su `generar.py` y sus tests.
2. Importa las piezas comunes (`calendarios.ics`, `calendarios.http`,
   `calendarios.registro`…) para no duplicar lógica.
3. Añade `.github/workflows/categoria-nombre.yml` con su propio `schedule`,
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
      directorio: categoria/nombre
      ics: calendario.ics
```

4. Comprueba que aparece y se ejecuta:

```bash
python3 -m calendarios listar
python3 -m calendarios actualizar --solo categoria/nombre
```

## 🧪 Ejecución local

Requiere Python 3.10+ (solo librería estándar; el CI usa 3.12).

```bash
# Lista los calendarios detectados
python3 -m calendarios listar

# Genera uno o todos (si uno falla, sigue con el resto)
python3 -m calendarios actualizar --solo deportes/baloncesto
python3 -m calendarios actualizar

# Valida un ICS (o un directorio con .ics)
python3 -m calendarios validar deportes/baloncesto/estudiantes.ics

# Tests de todo el monorepo
./scripts/test.sh
```

## 🛡️ Aislamiento de fallos

- **GitHub Actions:** cada calendario tiene su propio workflow y su propio
  `schedule`. Si la FEB cambia o un calendario falla, solo falla ese workflow;
  los demás siguen ejecutándose.
- **Commit:** cada workflow hace `git add` únicamente de su directorio. Un
  calendario nunca publica cambios de otro.
- **Runner local:** cada generador se ejecuta en un subproceso independiente.
  `python3 -m calendarios actualizar` captura el fallo, lo muestra en el resumen
  y continúa con el siguiente.
- **Dentro de un calendario:** las fuentes que fallan usan el histórico guardado
  cuando es posible (por ejemplo, la liga o la Copa de la FEB), y las sedes son
  opcionales: nunca tumban la generación del ICS.
- **Publicación concurrente:** si dos calendarios terminan a la vez, el workflow
  reintenta `pull --rebase` + `push` antes de darse por vencido.

## 🔄 Cómo funciona una actualización

1. El workflow del calendario se lanza por `schedule` o a mano.
2. Se ejecutan los tests comunes y los del calendario.
3. El generador descarga sus fuentes, actualiza el estado y escribe el `.ics`.
4. Se valida el ICS a nivel de bytes (CRLF, plegado ≤75 octetos, UIDs únicos).
5. Si hay cambios reales (se ignora un `DTSTAMP` nuevo), se hace commit y push.
6. GitHub sirve el `.ics` por `raw.githubusercontent.com` y tu calendario se
   actualiza en la siguiente sincronización.

## 📄 Licencia

[MIT](LICENSE)
