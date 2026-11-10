# Pulso Legislativo

> Que cualquier persona pueda entender, en cinco minutos, qué se discutió hoy en el Congreso de Chile, qué tan rápido avanzan las leyes y cómo funcionan los poderes del Estado.

---

## 1. El problema

- Las sesiones del Senado y de la Cámara de Diputadas y Diputados son públicas, pero quedan registradas en documentos largos y técnicos: diarios de sesiones en PDF, tablas, boletines y votaciones.
- Casi nadie sabe en qué etapa va un proyecto, por qué se demora o quién votó qué.
- Los tiempos de tramitación son tema de debate, pero las cifras cambian mucho según cómo se midan. Un estudio habla de 265 días con el binominal contra 401 con el proporcional, y Segpres calculó 821 días antes del 18-O.

## 2. Qué queremos construir

Un sistema automático que:

1. **Lea todos los días** lo que publican el Senado y la Cámara: sesiones de Sala, votaciones, asistencia y movimientos de proyectos de ley.
2. **Guarde todo** en una base de datos propia, con historial.
3. **Traduzca** cada sesión a lenguaje simple con IA: qué se votó, qué significa y cuál es el próximo paso. Cada frase debe enlazar a la fuente oficial.
4. **Mida la velocidad** de cada proyecto: días en cada etapa, urgencias, comisiones mixtas y comparación con proyectos parecidos.
5. **Publique** los resultados en una web simple y, más adelante, como resumen diario por WhatsApp, Instagram o newsletter.

## 3. Para quién

- **Ciudadanía general:** "¿qué pasó hoy en el Congreso y me afecta?"
- **Estudiantes y profesores:** material para educación cívica.
- **Periodistas y ONG:** datos limpios sobre tiempos y votaciones.

## 4. Principios

| Principio | Qué significa en la práctica |
|---|---|
| **Neutralidad partidaria** | No favorecemos ni atacamos a ningún sector político. La crítica va al Congreso completo, con la misma vara para todos. |
| **Crítica con datos** | El tono es directo y crítico: si no trabajaron, se dice; si trabajaron, se reconoce. El juicio siempre sale de datos verificables (horas, asistencia, votaciones, proyectos). |
| **Trazabilidad** | Todo resumen enlaza al documento oficial. Nada se inventa. Si alguien "faltó", es porque lo dice el registro de asistencia. |
| **Datos abiertos** | Código y datos procesados públicos. |
| **Simple primero** | Lenguaje de 8° básico, sin jerga, con glosario. |

## 5. Fuentes de datos

| Fuente | Qué entrega | Formato | Uso |
|---|---|---|---|
| Cámara: Datos Abiertos Legislativos (camara.cl/transparencia/datosAbiertos.aspx) | Sesiones de Sala, asistencia, votaciones por año y por proyecto, comisiones | Servicios web XML | Estadísticas |
| Senado: datos abiertos legislativos / `wspublico` | Tramitación de proyectos, senadores, votaciones | XML | Estadísticas y tramitación |
| Senado: tramitacion.senado.cl | Ficha de cada boletín, sesiones celebradas | HTML | Complemento |
| Diarios de sesiones (Senado y Cámara) | Versión taquigráfica: quién habló y qué dijo | PDF | Resúmenes con IA |
| opendata.congreso.cl (BCN) | Datos legislativos generales | Variado | Complemento |
| Diario Oficial / LeyChile | Fecha de publicación de la ley | HTML | Cierre del ciclo |

> **Primera tarea:** probar cada servicio y anotar en `docs/fuentes.md` cuáles responden hoy, con qué campos y con qué frecuencia se actualizan.

## 6. Arquitectura

```
 ┌──────────────┐   diario    ┌─────────────┐    ┌──────────────┐    ┌───────────┐
 │  Fuentes     │ ──────────▶ │  scrapers/  │ ─▶ │  Base datos  │ ─▶ │ analisis/ │
 │ Senado/Cámara│  (cron)     │  (Python)   │    │ (SQLite→PG)  │    │ métricas  │
 └──────────────┘             └─────────────┘    └──────┬───────┘    └─────┬─────┘
                                                       │                  │
                                                 ┌─────▼──────┐     ┌─────▼─────┐
                                                 │ Resumen IA │ ──▶ │   web/    │
                                                 │ (por sesión)│     │ + canales │
                                                 └────────────┘     └───────────┘
```

- **Lenguaje:** Python (requests, lxml, pandas, pdfplumber).
- **Base de datos:** SQLite para empezar; Postgres/Supabase cuando haya web pública.
- **Automatización:** GitHub Actions con un cron diario.
- **IA:** API de Claude para resumir sesiones, siempre con citas a la fuente.
- **Web:** sitio estático primero (por ejemplo, Vercel o GitHub Pages).

## 7. Modelo de datos inicial

- `proyectos`: boletín, título, materia, origen (mensaje/moción), cámara de origen, fecha de ingreso, estado.
- `tramites`: boletín, etapa (1er trámite, 2º trámite, comisión mixta, TC, promulgación), fecha inicio y fin.
- `urgencias`: boletín, tipo (simple, suma, discusión inmediata), fecha y retiro o renovación.
- `sesiones`: cámara, número, legislatura, fecha, hora de inicio y término, tipo.
- `votaciones`: sesión, boletín, fecha, resultado, sí, no, abstenciones.
- `votos`: votación, parlamentario, voto.
- `parlamentarios`: id, nombre, cámara, partido, distrito o circunscripción, período.
- `resumenes`: sesión, texto simple, fuentes citadas, versión del modelo y revisión humana.

## 8. Métricas

1. **Tiempo total hasta ser ley,** separado por mensaje o moción, urgencia, materia y período legislativo.
2. **Tiempo por etapa:** dónde se atascan los proyectos (comisiones, Sala, comisión mixta).
3. **Supervivencia:** los proyectos que siguen en trámite también cuentan. Usamos curvas Kaplan-Meier para no sesgar hacia los que sí salieron.
4. **Efecto de las urgencias:** cuánto acelera de verdad una "discusión inmediata".
5. **Productividad por sesión:** proyectos votados, duración y asistencia.
6. **"Velocímetro" de cada proyecto:** si va más rápido o más lento que proyectos comparables.

## 9. Producto: qué ve la gente

**Canal de video: "¿Hicieron alguna wea por Chile?"**. Su tono es crítico y directo, con humor chileno. El blanco es el Congreso completo, nunca un sector político. Tiene tres formatos:
- **Capítulo 0, presentación:** qué somos, por qué existimos, de dónde sacamos los datos y cómo funciona el sistema. Guion en [guiones/00-presentacion.md](../guiones/00-presentacion.md).
- **Capítulo diario:** cuánto trabajaron, qué votaron, en qué te afecta, quiénes no votaron o faltaron y el cahuín.
- **Ranking semanal:** quiénes más faltan y menos trabajan, con nombre, apellido, distrito, partido y qué hacen. Necesita el historial de asistencia en la base.


- **"Hoy en el Congreso":** tres a cinco puntos en lenguaje simple por cada cámara.
- **Ficha de proyecto:** línea de tiempo visual del recorrido, velocímetro y cómo votó cada partido.
- **Cómo funciona:** explicadores del camino de una ley, qué hace cada poder, qué es una urgencia o una comisión mixta.
- **Estadísticas:** gráficos de tiempos y tendencias.

## 10. Hoja de ruta

| Fase | Objetivo | Entregable |
|---|---|---|
| **0. Exploración** (semana 1-2) | Probar las fuentes | `docs/fuentes.md` y scripts de prueba |
| **1. Datos** (semana 3-5) | Descargar un año completo de proyectos, trámites y votaciones | Base SQLite y scraper diario |
| **2. Métricas** (semana 6-7) | Primeras estadísticas de tiempos | Notebook en `analisis/` |
| **3. Resúmenes IA** (semana 8-9) | Resumir sesiones reales con citas | Resúmenes de 10 sesiones revisados a mano |
| **4. Web MVP** (semana 10-12) | "Hoy en el Congreso" y fichas de proyectos | Sitio público |
| **5. Difusión** | Canales y alianzas | Newsletter, redes, colegios |

## 11. Riesgos

- **Servicios caídos o que cambian de formato.** Guardar siempre el dato crudo en `data/raw` y escribir tests por fuente.
- **Errores de la IA.** Citar siempre la fuente, revisar a mano al inicio y nunca generar votos o cifras con IA: esos vienen solo de los datos estructurados.
- **Percepción de sesgo.** Metodología pública y mismo tratamiento para todos los sectores.
- **Duplicar lo que ya existe.** Revisar Transparentes.cl, Senador Virtual y los estudios de Faro UDD y UDALBA. Nuestra diferencia es el resumen diario simple más la velocidad en tiempo real.

## 12. Estructura del repositorio

```
pulso-legislativo/
├── README.md
├── docs/          # Este documento, fuentes, metodología, glosario
├── scrapers/      # Descarga desde Senado y Cámara
├── data/
│   ├── raw/       # Datos crudos (no se suben a git)
│   └── processed/ # Datos limpios
├── analisis/      # Notebooks y métricas
└── web/           # Sitio público
```

## 13. Próximos pasos inmediatos

- [ ] Probar el servicio de votaciones de la Cámara para 2026.
- [ ] Probar `wspublico` del Senado (tramitación por fecha).
- [ ] Descargar un diario de sesiones en PDF y extraer su texto.
- [ ] Definir el esquema SQLite.
- [ ] Hacer el primer resumen de una sesión real con IA.

---
*Documento vivo. Última actualización: noviembre 2026.*
