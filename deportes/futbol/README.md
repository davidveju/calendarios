# ⚽ Calendarios de fútbol

Calendarios independientes para equipos y selecciones de fútbol. Cada calendario
tiene su propio código, estado y workflow, pero puede compartir esta carpeta con
otra ICS.

- [Getafe CF 26/27](getafe.ics): LaLiga, Copa del Rey, Conference League y previas.
  URL: `https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/getafe.ics`
- [Real Madrid 26/27](madrid.ics): LaLiga, Champions League y Copa del Rey (fuente agregada).
  URL: `https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/madrid.ics`
- [Selección Española](espana.ics): amistosos y competiciones oficiales
  (Mundial, Nations League, Finalissima).
  URL: `https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/espana.ics`

## Fuentes de datos

Cada calendario combina fuentes oficiales cuando están disponibles y conserva
Transfermarkt como respaldo:

| Calendario | Competición | Fuente primaria | Respaldo |
|---|---|---|---|
| Getafe CF | LaLiga, Copa del Rey | Transfermarkt | estado previo |
| Getafe CF | Conference League | UEFA (`match.uefa.com`) | Transfermarkt |
| Real Madrid | LaLiga | Transfermarkt | estado previo |
| Real Madrid | Champions League | UEFA (`match.uefa.com`) | Transfermarkt |
| Selección Española | Amistosos, Mundial | FIFA (`api.fifa.com`) | Transfermarkt |
| Selección Española | Nations League, Finalissima | UEFA (`match.uefa.com`) | Transfermarkt |

Los proveedores (`scripts/proveedores/uefa/`, `scripts/proveedores/fifa/`,
`scripts/proveedores/transfermarkt/`) son genéricos: reciben una configuración y
devuelven partidos normalizados. Al cambiar de fuente se conservan los `uid` del
estado previo para no duplicar eventos en los calendarios suscritos.

## Publicación, estado y código

Los ficheros públicos (`.ics`) están en `deportes/futbol/`. El estado y código
están aparte:

```text
estado/deportes/futbol/getafe/
scripts/calendarios/deportes/futbol/getafe/
estado/deportes/futbol/madrid/
scripts/calendarios/deportes/futbol/madrid/
estado/deportes/futbol/espana/
scripts/calendarios/deportes/futbol/espana/
```

El `id` de cada calendario (`deportes/futbol/getafe`,
`deportes/futbol/madrid`, `deportes/futbol/espana`) namespacea su código y su
estado; la carpeta pública (`deportes/futbol/`) se comparte sin riesgo de cruces.
