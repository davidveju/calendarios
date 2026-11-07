# ⚽ Getafe CF 26/27

Partidos del Getafe CF en LaLiga 26/27 —directos en tu calendario. Los
partidos jugados aparecen con el resultado y los horarios se actualizan solos.

| | |
|---|---|
| 📅 Fichero | [`getafe.ics`](getafe.ics) — LaLiga 26/27 |
| 📡 Fuente | [Transfermarkt](https://www.transfermarkt.com/getafe-cf/spielplan/verein/3709/saison_id/2026): LaLiga, Copa del Rey, Conference League y previas |
| 🔄 Actualización | lunes, miércoles y viernes 12:00 UTC |
| 🆔 ID | `deportes/futbol/getafe` |

## 📲 Suscribirse

Pega esta URL en Google Calendar, Apple Calendar u Outlook:

```text
https://raw.githubusercontent.com/davidveju/calendarios/main/deportes/futbol/getafe.ics
```

## 🗃️ Publicación, estado y código

```text
deportes/futbol/
├── getafe.ics
└── README.md
```

Estado y caché:

```text
estado/deportes/futbol/getafe/
└── partidos.json
```

Código:

```text
scripts/calendarios/deportes/futbol/getafe/
├── calendario.json
├── config.py
├── generar.py
└── tests/
```

Cada calendario tiene su propio `id`, que namespacea su código y su estado. La
carpeta pública puede compartirse: otro equipo de fútbol podría publicar
`deportes/futbol/rayo.ics` junto a este.
