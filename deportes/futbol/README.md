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

Cada calendario combina fuentes oficiales cuando están disponibles, con
respaldo en cadena si la primaria falla:

| Calendario | Competición | Fuente primaria | Respaldos |
|---|---|---|---|
| Getafe CF | LaLiga, Copa del Rey | LALIGA (API oficial) | Transfermarkt → ESPN |
| Getafe CF | Conference League | UEFA (`match.uefa.com`) | Transfermarkt |
| Real Madrid | LaLiga, Copa del Rey | LALIGA (API oficial) | Transfermarkt → ESPN |
| Real Madrid | Champions League | UEFA (`match.uefa.com`) | Transfermarkt |
| Selección Española | Amistosos, Mundial | FIFA (`api.fifa.com`) | Transfermarkt |
| Selección Española | Nations League, Finalissima | UEFA (`match.uefa.com`) | Transfermarkt |

Transfermarkt no responde desde las IPs de GitHub Actions (bloqueo
anti-bots: sirve una página vacía), así que en CI la Liga/Copa se actualiza
vía LALIGA, con ESPN como último recurso. Los proveedores
(`scripts/proveedores/laliga/`, `uefa/`, `fifa/`, `transfermarkt/`,
`scripts/proveedores/espn/`) son genéricos: reciben una configuración y
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
