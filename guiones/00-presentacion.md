# Capítulo 0 · ¿Hicieron alguna wea por Chile?

<!-- Capítulo de presentación del canal. Borrador para iterar; todavía no se renderiza.
     Formato: igual que los guiones diarios (las líneas con > son notas de producción, no se leen).
     Duración objetivo: 90 a 120 s. Vertical 1080x1920. -->

> **Nombre del canal:** "¿Hicieron alguna wea por Chile?". Es un guiño al nombre de "Algo habrán hecho por la historia de Chile": tomamos solo el juego de palabras. No copiamos su intro, su música, su gráfica ni sus personajes. Todo lo visual es propio (hemiciclo, bandera, estilo 1810 de la página explicativa).
> **Por verificar antes de publicar:** la dieta parlamentaria ("8 palitos") necesita la cifra exacta y su fuente oficial en guion/contexto.json. Si no está verificada, la frase pasa a "ganan millones al mes".

## GANCHO
> Pantalla: el título "¿Hicieron alguna wea por Chile?" escrito a mano sobre papel antiguo; la cámara entra al Congreso como en la intro diaria.
¿Hicieron alguna wea por Chile? Esa es la pregunta. Y todos los días la vamos a responder.

## QUE SOMOS
> Pantalla: el logo de Pulso Legislativo, la sala que se ilumina y un contador "155 diputados · 50 senadores".
Somos un canal que mira lo que hace el Congreso todos los días. Ciento cincuenta y cinco diputados y cincuenta senadores. Les pagamos todos, así que tenemos derecho a saber si trabajan.

## POR QUE
> Pantalla: billetes cayendo sobre el hemiciclo y la cifra de la dieta con su fuente (solo si está verificada).
Porque ganar 8 palitos al mes por rascarse las bolas… chupámelo. Si no trabajan, los vamos a funar. Con nombre, apellido y partido.

## QUE HACEMOS
> Pantalla: maqueta de un capítulo diario en cuatro tarjetas: "¿Cuánto trabajaron?", "Qué votaron", "¿En qué te afecta?" y "Cahuín".
Cada día te contamos cuántas horas estuvieron en la Sala, qué votaron, en qué te afecta y quiénes no votaron o faltaron. Si hay cahuín, también. Y una vez a la semana, el ranking de los que más faltan.

## DE DONDE SALEN LOS DATOS
> Pantalla: logos o capturas de camara.cl, senado.cl y el Diario Oficial, con flechas hacia una base de datos.
Nada es inventado. Todo sale de fuentes públicas: los datos abiertos de la Cámara, la tramitación del Senado y el Diario Oficial. En cada video dejamos los links pa que lo revises tú.

## COMO FUNCIONA
> Pantalla: diagrama animado del sistema, como en docs/datos.md:
> fuentes → robot diario (Python, GitHub Actions, 6 de la mañana) → base de datos (Supabase / Postgres) → cruce de votos con partidos y asistencia → borrador del guion (Claude) → revisión humana → voz → video (Remotion).
Todas las mañanas, a las seis, un robot baja lo que pasó en el Congreso y lo guarda en una base de datos. Ahí cruzamos cada voto con el partido y la asistencia de cada parlamentario. Una inteligencia artificial escribe el borrador, pero las cifras salen directo de los datos oficiales y las revisamos nosotros antes de publicar.

## LA REGLA
> Pantalla: una balanza con todos los partidos en el mismo platillo.
Una sola regla: misma vara para todos. Nos da lo mismo si son de izquierda o de derecha. Y si un día trabajan de verdad, lo vamos a decir: "hoy por fin hicieron algo".

## CIERRE
> Pantalla: el logo y "Síguenos". Las fuentes y el link al código, que es abierto, van en la descripción.
Síguenos pa que no se nos escape ni un weón. ¿Hicieron alguna wea por Chile? Mañana te cuento.
