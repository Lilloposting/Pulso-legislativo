# Fuentes de datos

Probadas el 10-11-2026. Todas responden con XML, sin autenticación.

## Cámara de Diputadas y Diputados: `opendata.camara.cl/camaradiputados/WServices/`

| Servicio / método | Parámetro | Qué entrega | Lo usamos para |
|---|---|---|---|
| `WSLegislativo/retornarMocionesXAnno`, `retornarMensajesXAnno` | `prmAnno` | Todos los proyectos ingresados en el año, **de ambas cámaras de origen** (2025: 642 mociones y 65 mensajes) | Lista maestra de boletines |
| `WSLegislativo/retornarProyectoLey` | `prmNumeroBoletin` (`18551-04`) | Ministerios patrocinantes y votaciones con artículo, trámite constitucional y reglamentario | Enriquecer la ficha y las votaciones |
| `WSLegislativo/retornarVotacionesXAnno` | `prmAnno` | Todas las votaciones de Sala del año, con totales (2026: 1.207; 2022: 1.315) | `votaciones` |
| `WSLegislativo/retornarVotacionDetalle` | `prmVotacionId` | Voto de cada diputado (Afirmativo, En Contra, Abstención, Dispensado, No Vota) | `votos` |
| `WSLegislativo/retornarLegislaturas`, `retornarPeriodosLegislativos` | — | Legislaturas desde 1990 (actual: 374, desde el 11-03-2026) | `legislaturas` |
| `WSSala/retornarSesionesXAnno` | `prmAnno` | Sesiones de Sala con hora de inicio y término, tipo y estado (Citada o Celebrada) | `sesiones` |
| `WSSala/retornarSesionAsistencia` | `prmSesionId` | Asistencia por diputado | `asistencia` |
| `WSDiputado/retornarDiputadosPeriodoActual`, `retornarDiputadosXPeriodo` | `prmPeriodoID` | Diputados y su historial de militancias | `parlamentarios`, `militancias`, `mandatos` |
| `WSComision/*` | — | Comisiones y sus sesiones | *Pendiente* |

## Senado: `tramitacion.senado.cl/wspublico/`

| Endpoint | Parámetro | Qué entrega | Lo usamos para |
|---|---|---|---|
| `tramitacion.php` | `boletin=16621` (sin dígito verificador) | **Ficha completa**: etapa, estado, ley, fecha en el Diario Oficial, autores, materias, trámites en ambas cámaras, urgencias (con fechas de ingreso y retiro), informes, oficios, comparados e indicaciones con enlaces | `proyectos`, `tramites`, `urgencias`, `documentos` |
| `tramitacion.php` | `fecha=dd/mm/aaaa` | Fichas de todos los proyectos con movimiento desde esa fecha. **Máximo un mes hacia atrás.** | Carga diaria |
| `votaciones.php` | `boletin=16621` | Votaciones en Sala del Senado con el voto de cada senador por nombre. No trae id de votación. | `votaciones`, `votos` |
| `senadores_vigentes.php` | — | Senadores con id, región, circunscripción, partido y email | `parlamentarios` |

## Problemas conocidos de las fuentes

- **`senadores_vigentes.php` está desactualizado.** Devuelve 31 senadores (el Senado tiene 50) e incluye a algunos que salieron en marzo de 2026. Por eso los votos del Senado se guardan con el nombre tal como viene (`votos.votante`) y se vinculan a `parlamentario_id` solo cuando el nombre calza. En una prueba con el boletín 18551-04 calzaron 25 de 42. Hay que buscar otra fuente para los senadores del período 2026-2030.
- **Fechas de mandato de la Cámara.** `retornarDiputadosPeriodoActual` informa `FechaInicio = 2030-03-10` para el período actual. Se guarda tal cual. Para fechas confiables conviene usar las militancias o el período legislativo.
- **El Senado no tiene id de votación.** Generamos uno estable con un hash de boletín, sesión, fecha, tema, tipo, etapa y totales.
- El dato crudo de cada descarga se respalda comprimido en `data/raw/<fuente>/<fecha>/`. En GitHub Actions se guarda como artifact durante 30 días.

## Pendientes

- Diarios de sesiones en PDF (texto de los debates) para los resúmenes con IA.
- Sesiones de Sala del Senado (hoy solo tenemos el código `sesión/legislatura` dentro de trámites y votaciones).
- Comisiones (Cámara: `WSComision`).
- LeyChile / BCN para el texto final de la ley.
