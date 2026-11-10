# Pulso Legislativo

Entender el Congreso de Chile sin ser abogado.

Pulso Legislativo lee todos los días lo que pasa en el Senado y en la Cámara de Diputadas y Diputados, lo resume en lenguaje simple y mide qué tan rápido o lento avanzan las leyes.

📄 **Visión completa del proyecto:** [docs/PROYECTO.md](docs/PROYECTO.md)

## Estructura

| Carpeta | Contenido |
|---|---|
| `docs/` | Visión, fuentes, metodología |
| `scrapers/` | Descarga de datos del Senado y la Cámara |
| `data/` | Datos crudos (`raw/`, fuera de git) y procesados |
| `analisis/` | Métricas y notebooks |
| `web/` | Sitio público |

## Cómo correrlo

```bash
python -m venv .venv && .venv/Scripts/activate      # Windows (en Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env                                # completar DATABASE_URL de Supabase
python -m scrapers.historico --desde 2018            # carga inicial
python -m scrapers.diario                            # actualización diaria
```

- Fuentes probadas y sus problemas: [docs/fuentes.md](docs/fuentes.md)
- Modelo de datos (Supabase): [docs/datos.md](docs/datos.md)

## Estado

🟢 Fase 0: fuentes probadas.
🟡 Fase 1: scrapers diario e histórico escritos y esquema creado en Supabase. Falta la primera carga.
