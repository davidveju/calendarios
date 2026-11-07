# ⚽ Calendarios de fútbol

Calendarios independientes para equipos de fútbol. Cada calendario tiene su propio
código, estado y workflow, pero puede compartir esta carpeta con otra ICS.

- [Getafe CF 26/27](getafe.ics): LaLiga, Copa del Rey, Conference League y previas.
  URL: `https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/getafe.ics`
- [Real Madrid 26/27](madrid.ics): LaLiga, Champions League y Copa del Rey (fuente agregada).
  URL: `https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/madrid.ics`

## Publicación, estado y código

Los ficheros públicos (`.ics`) están en `deportes/futbol/`. El estado y código
están aparte:

```text
estado/deportes/futbol/getafe/
scripts/calendarios/deportes/futbol/getafe/
estado/deportes/futbol/madrid/
scripts/calendarios/deportes/futbol/madrid/
```

El `id` de cada calendario (`deportes/futbol/getafe`, `deportes/futbol/madrid`)
namespacea su código y su estado; la carpeta pública (`deportes/futbol/`) se
comparte sin riesgo de cruces.
