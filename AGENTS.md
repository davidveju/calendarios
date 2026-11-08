# Agent Guide for `calendarios`

This is the context a future coding-agent session needs to extend or debug this
repository. Read it before making changes.

## Repository purpose
Automated iCalendar (`.ics`) subscription calendars, one per team/category, each
updated by its own GitHub Actions. Public ICS files live in repo folders; internal
state and code live apart.

## Three layers (do not mix them)
- `scripts/` → all code and tests.
- `estado/<id>/` → internal state and cache (JSON). Never a published URL.
- `deportes/...` (or other public folders) → only published artifacts
  (`.ics`, README).

The `id` namespacea código y estado. The manifest declares the public ICS path.

## Naming
Calendar id example: `deportes/futbol/getafe`.
```
codigo:    scripts/calendarios/deportes/futbol/getafe/
módulo:    scripts.calendarios.deportes.futbol.getafe.generar
estado:     estado/deportes/futbol/getafe/
public ICS: deportes/futbol/getafe.ics
URL:       .../main/deportes/futbol/getafe.ics
```

## Manifest (`calendario.json`, next to the calendar code)
```json
{
  "nombre": "Visible name in ICS",
  "descripcion": "What it contains",
  "ics": "repo/relative/path.ics",
  "generador": "generar.py",
  "datos": ["partidos.json", "sedes.json"],
  "zona": "Europe/Madrid"
}
```
- `ics`: repo-relative public path. Must end with `.ics`.
- `datos`: paths relative to `estado/<id>/`.

## Key files
- `scripts/comun/contexto.py`: source of truth for paths.
  - `Contexto.id`, `.codigo`, `.estado`, `.publicacion`, `.ics`, `.ruta_ics`,
    `.ruta_estado(rel)`, `.modulo`.
- `scripts/comun/registro.py`: discovers manifests, rejects duplicate public ICS
  paths (soft or hard with `--estricto`).
- `scripts/comun/runner.py`: executes each generator in an isolated subprocess,
  validates ICS + state JSON.
- `scripts/comun/ics.py`: `Evento`, `generar_ics`.
- `scripts/comun/http.py`: `fetch`.

## Common commands
List calendars:
```bash
python3 -m scripts listar
```
Regenerate one:
```bash
python3 -m scripts actualizar --solo deportes/futbol/getafe
```
Regenerate all:
```bash
python3 -m scripts actualizar
```
Validate:
```bash
python3 -m scripts validar deportes/futbol/getafe.ics
```
Tests:
```bash
./scripts/test.sh
```

## Adding a new calendar
1. Create `scripts/calendarios/<id>/` with `__init__.py`, `calendario.json`,
   `config.py`, `generar.py`, `tests/`.
2. Reuse `scripts.comun` and (preferred) a provider in `scripts/proveedores/<fuente>`.
   Providers must be generic: they receive a config and return normalised data.
3. In the generator, obtain paths with `contexto_desde_ejecucion(__name__, __file__)`.
4. No extra workflow is needed. Sports calendars are picked up daily by
   `.github/workflows/actualizar-calendarios.yml` (00:00 UTC, excludes
   `festivos/*`). Monthly/low-frequency calendars (e.g. festivos) are added to
   `.github/workflows/actualizar-calendarios-mensual.yml`. Add the public README
   and an entry in the top `README.md`.

## Stable UIDs
Use a uid derived from a stable source id:
- Sports: `<prefix>-<stable-id>@<domain>`
Stable ids prevent duplicate events after updates and merges.

## Failure isolation
- Automatic fail-over: if one data source fails, generators try the historical
  state first.
- CLI and CI execute each generator in its own subprocess. The update workflows
  continue on calendar failures, publish what they can, and fail at the end.

## State
State files (`estado/<id>/`) are committed by the updater workflows together with
the public ICS. Do not commit generated files in public folders beyond the
declared ICS. Do not put internal JSON under the public ICS folder.

Optional enrichment caches (e.g. `sedes.json`/arena caches) may live under
`estado/<id>/` and be listed in `datos`. They must be non-fatal: if a venue
lookup fails, keep generating the calendar without that `LOCATION`.

## Development etiquette
- Run `./scripts/test.sh` before committing.
- Keep doc and comments in Spanish where existing style is Spanish.
- New provider tests should be offline (use fixture files / strings).
