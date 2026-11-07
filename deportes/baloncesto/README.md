# 🏀 Movistar Estudiantes 26/27

Todos los partidos del Movistar Estudiantes masculino 26/27 —liga Primera FEB,
Copa España y playoffs— directos en tu calendario. Los partidos jugados
aparecen con el resultado y los horarios se actualizan solos.

| | |
|---|---|
| 📅 Fichero | [`estudiantes.ics`](estudiantes.ics) — 34 jornadas de liga + Copa España (y playoffs si se clasifica) |
| 📡 Fuentes | Liga en [competiciones.feb.es](https://competiciones.feb.es/estadisticas/Calendario.aspx) · Copa en [feb.es](https://www.feb.es/competiciones/resultados/copaespaa/73/2026) |
| 🔄 Actualización | lunes, miércoles y viernes 12:00 UTC |
| 🆔 ID | `deportes/baloncesto` |

## 📲 Suscribirse

Pega esta URL en Google Calendar (`Otros calendarios` → `+` → `Desde URL`),
Apple Calendar (`Añadir calendario suscrito`) u Outlook (`Suscribirse desde la web`):

```text
https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/baloncesto/estudiantes.ics
```

> El antiguo repo `davidveju/estudiantes-calendario` está archivado. Si tenías
> suscrita su URL, elimina ese calendario y añade el nuevo.

## 🔍 Cómo se ven los eventos

| Estado | Ejemplo |
|---|---|
| Pendiente (liga) | 🏀 Fibwi Mallorca - Estu (J5) — hora real de Madrid |
| Victoria fuera | 🏀 Caja Rural CB Zamora - Estu (J2: 73-80 ✅) |
| Derrota | 🏀 Rival - Estu (J7: 85-78 ❌) |
| Copa | 🏆 Cáceres Patrimonio de la Humanidad - Estu (Copa 1/8, fecha por confirmar) |

- Cada evento lleva la sede (pabellón + dirección) y el enlace al acta oficial de la FEB.
- Los partidos no bloquean tu disponibilidad (se marcan como libres).
- Si la FEB aún no ha confirmado fecha u hora, el evento se marca como
  provisional (`TENTATIVE`).

## ⚙️ Cómo funciona

El código está separado de los datos publicados:

- [`config.py`](../../scripts/calendarios/deportes/baloncesto/config.py) define
  los parámetros del Estu (id FEB, temporada, URLs y prefijo de UIDs).
- [`generar.py`](../../scripts/calendarios/deportes/baloncesto/generar.py)
  mantiene el estado, aplica las horas verificadas, cachea las sedes y genera
  `estudiantes.ics` con UIDs estables por jornada/ronda.
- [`fuentes.py`](../../scripts/proveedores/feb/fuentes.py) es el parser común de
  la FEB: sirve para cualquier equipo creando otra `ConfigFEB`. La Copa conserva
  las rondas anteriores aunque la FEB ya solo muestre la fase actual.
- [`calendario.json`](../../scripts/calendarios/deportes/baloncesto/calendario.json)
  declara el nombre, el ICS de salida y los ficheros de estado que el runner
  debe validar.
- El motor compartido de ICS, HTTP, validación y runner vive en
  [`scripts/comun/`](../../scripts/comun/).
- El workflow `.github/workflows/deportes-baloncesto.yml` se ejecuta lunes,
  miércoles y viernes; si no hay cambios reales (ni horarios nuevos ni
  resultados) no se publica nada.

## 🗃️ Datos y estado

Este directorio solo contiene datos y el fichero publicado:

```text
deportes/baloncesto/
├── estudiantes.ics            # el fichero al que te suscribes
├── datos/partidos.json        # horarios, resultados y actas
├── datos/sedes.json           # caché de pabellones por partido
├── datos/fechas_reales.json   # horas verificadas que mandan sobre la FEB
└── README.md
```

El código y los tests están en:

```text
scripts/calendarios/deportes/baloncesto/
├── calendario.json            # manifiesto para el runner
├── config.py                  # configuración de este equipo
├── generar.py                 # orquesta fuentes + estado + ICS
└── tests/                     # tests sin red
```

Cada calendario tiene su propio `id` (`deportes/baloncesto`), que namespacea su
código (`scripts/calendarios/<id>/`) y su salida (`<id>/`). Así se pueden añadir
más equipos sin que compartan caché ni UIDs.

## 🧪 Uso local

```bash
# Desde la raíz del repo
python3 -m scripts actualizar --solo deportes/baloncesto
python3 -m scripts validar deportes/baloncesto/estudiantes.ics
python3 -m unittest discover -s scripts/calendarios/deportes/baloncesto/tests -t . -v
```

Si una fuente falla, se reutiliza el histórico guardado y se avisa en el log;
la ejecución solo falla si no hay ningún dato previo con el que continuar.
