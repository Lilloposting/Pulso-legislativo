# Arquitectura de datos

Base: **Supabase** (Postgres), proyecto `pulso-legislativo` (`elyunblhidzgaowzljmx`, región São Paulo).
Todas las tablas tienen RLS con **lectura pública** (son datos abiertos). Solo los scrapers escriben, mediante `DATABASE_URL`.

```
                      ┌──────────────┐
                      │ legislaturas │
                      └──────────────┘
┌────────────────┐    ┌──────────────┐    ┌───────────┐
│ parlamentarios │◀───│  mandatos    │    │ sesiones  │──┐
│  D-803 / S-1110│◀───│  militancias │    └───────────┘  │
└───────▲────────┘    └──────────────┘          ▲        │
        │                                       │   ┌────▼──────┐
        │ (votos.parlamentario_id)              └───│ asistencia│
        │                                           └───────────┘
┌───────┴──┐    ┌────────────┐    ┌───────────────────────────────┐
│  votos   │───▶│ votaciones │···▶│ proyectos (boletin = llave)   │
└──────────┘    └────────────┘    └──┬──────────┬──────────┬──────┘
                                     │          │          │
                                ┌────▼───┐ ┌────▼────┐ ┌───▼────────┐
                                │tramites│ │urgencias│ │ documentos │
                                └────────┘ └─────────┘ └────────────┘
                                ┌───────────┐   ┌─────────────┐
                                │ resumenes │   │ ejecuciones │ (log de cada corrida)
                                └───────────┘   └─────────────┘
```

## Llaves

| Tabla | Llave | Nota |
|---|---|---|
| `proyectos` | `boletin` (`16621-05`) | La Cámara aporta id, admisibilidad y ministerios. El Senado aporta etapa, estado, ley, Diario Oficial y materias. Ninguna fuente pisa con NULL lo que entregó la otra. |
| `tramites`, `urgencias`, `documentos` | `(boletin, orden)` | Se reemplazan completos cada vez que se baja la ficha. |
| `votaciones` | `id` interno + único `(camara, id_fuente)` | `boletin` no tiene FK, porque una votación puede llegar antes que su ficha. |
| `votos` | `(votacion_id, votante)` | `votante` es `D-803` en la Cámara o el nombre tal cual en el Senado. |
| `parlamentarios` | `D-<id Cámara>` / `S-<PARLID Senado>` | |
| `sesiones` | `C-<id Cámara>` | Las del Senado quedan pendientes. |

## Scripts

```bash
pip install -r requirements.txt
cp .env.example .env          # completar DATABASE_URL

python -m scrapers.historico --desde 2018              # carga inicial (horas; reanudable)
python -m scrapers.historico --desde 2018 --solo fichas  # retomar solo un paso
python -m scrapers.diario                              # lo de los últimos 3 días
```

- **Diario** (GitHub Actions, 06:00 Chile): parlamentarios, proyectos nuevos del año, fichas con movimiento en los últimos 3 días, votaciones y voto a voto nuevos, sesiones y asistencia nuevas.
- **Histórico** (manual, desde Actions → *Run workflow* → `historico`): recorre año por año. Las fichas ya sincronizadas se saltan, así que si se corta basta con volver a correrlo.

## Volumen y límite gratuito (500 MB)

| Dato | Filas aproximadas |
|---|---|
| Proyectos 2018-2026 | ~7.000 (unos 700 al año) |
| Trámites | ~150.000 (unos 20 por proyecto) |
| Votaciones de la Cámara | unas 1.300 al año |
| Votos de la Cámara | unos 200.000 al año |

Por eso el voto a voto y la asistencia se bajan **desde 2022** por defecto (`--votos-desde`). Las votaciones agregadas se bajan para todos los años.
