# Auditoría visual responsive · RutaSegura Quito

Fecha: 3 de noviembre de 2026. Resultado final: cinco defectos de presentación corregidos, 28 pruebas de navegador aprobadas y 98 capturas conservadas.

## Herramienta y entorno

Se intentó primero el navegador integrado de Codex mediante la habilidad Browser. La inicialización falló con «privileged native pipe bridge is not available; browser-client is not trusted». Se utilizó el fallback solicitado: **Playwright Test 1.64.1 y Chromium 156.0.8078.4**, ejecutado sin interfaz visible, con renderizado real y acceso autorizado a OpenStreetMap.

Se reutilizaron inicialmente FastAPI en `127.0.0.1:8000` y Vite en `127.0.0.1:5173`. Tras la interrupción ambos estaban detenidos y se iniciaron de nuevo solo en loopback. No se modificó el backend ni se abrió el servicio a internet.

Las páginas se probaron con locale es-EC, escala de dispositivo 1 y movimiento reducido. El script espera las fuentes, teselas descargadas y opacidad final del fundido antes de capturar.

## Defectos encontrados antes de corregir

| Gravedad | Problema reproducido | Corrección |
|---|---|---|
| Alta | Al activar las cuadrículas, su relleno se dibujaba sobre las líneas de ruta y alteraba su color y lectura. | Panes independientes de Leaflet: cuadrículas debajo de las rutas. Las geometrías y los indicadores no cambian. |
| Media | Las letras A/B aparecían duplicadas y superpuestas por combinar texto con pseudoelementos. | Un único texto dentro de cada marcador, con orientación compensada. |
| Media | La leyenda de predicciones desaparecía al expandir el panel móvil. | Se conserva la leyenda y se reserva altura para el mapa. Las tarjetas del panel identifican las alternativas cuando su leyenda se oculta para evitar saturación. |
| Media | Cambiar las dimensiones del mapa podía dejar los extremos del recorrido fuera de la zona visible. | ResizeObserver actualiza el tamaño y reencuadra la zona o ruta enfocada, reservando espacio para controles y leyendas. |
| Media | Desde 768 px no existía un control visible para contraer el panel lateral. | El mismo control abre y cierra el panel en todos los tamaños, con nombre accesible y estado aria-expanded. |

Las observaciones se comunicaron antes de modificar la presentación. No se detectó desbordamiento horizontal en la línea base. Se revisaron visualmente las capturas antes y después, incluyendo marcadores, trazos, leyendas, texto, panel y atribución; el resultado no se deduce solo de pruebas DOM.

Ejemplos: [marcadores antes](antes/360/03-tres-rutas.png), [marcadores después](despues/360/03-tres-rutas.png), [leyenda ausente antes](antes/390/06-predicciones-panel.png), [leyenda visible después](despues/390/06-predicciones-panel.png), [panel lateral final](despues/1280/06-predicciones-panel.png).

## Tamaños y resultado responsive

| Viewport (px) | Contexto de Chromium | Resultado |
|---|---|---|
| 360 × 800 | Móvil emulado, táctil | Conforme en los estados probados |
| 390 × 844 | Móvil emulado, táctil | Conforme en los estados probados |
| 430 × 932 | Móvil emulado, táctil | Conforme en los estados probados |
| 768 × 1024 | Viewport tablet, capacidad táctil | Conforme en los estados probados |
| 1024 × 768 | Viewport tablet horizontal | Conforme en los estados probados |
| 1280 × 800 | Escritorio | Conforme en los estados probados |
| 1920 × 1080 | Monitor grande | Conforme en los estados probados |

En los siete tamaños se comprobó ausencia de desbordamiento horizontal de página y panel; mapa visible; panel expandible/contraíble; botones principales de al menos 44 px; controles sin obstrucciones en el área visible; atribución de OpenStreetMap accesible; predicciones con leyenda visible; advertencias legibles y cambio de tamaño conservando los extremos de la ruta.

En móviles el panel y el diálogo tienen scroll interno: no todo su contenido cabe simultáneamente. Se comprobó el acceso a las alternativas y al botón de cierre mediante desplazamiento. Cuando el diálogo modal está abierto, su fondo bloquea deliberadamente los controles del mapa.

## Interacciones y pruebas

Los cuatro escenarios se ejecutan en cada tamaño:

1. Carga del mapa con teselas reales; selección de A/B por toque en móvil o clic; ejemplo de regresión; petición real a FastAPI; tres alternativas y resaltado SVG; mostrar/ocultar 25 cuadrículas y cambiar de indicador; abrir/cerrar panel; intercambio y reinicio.
2. Estado de carga con respuesta real demorada; coordenadas fuera de cobertura con HTTP 422 real; fallo de red simulado y recuperación con respuesta real.
3. Cambio entre dimensiones de móvil/escritorio y vuelta al tamaño original; conservación de marcadores; advertencias mediante teclado, Escape y botón de cierre.
4. Fallo inicial de conexión simulado; reintento contra el backend real.

| Verificación | Aprobadas | Fallidas |
|---|---:|---:|
| Pruebas existentes de frontend | 35 | 0 |
| Integración HTTP con FastAPI | 7 | 0 |
| Playwright, última ejecución | 28 | 0 |
| **Total de casos verificados** | **70** | **0** |

La compilación de producción también terminó correctamente. Se conservaron la compilación y las 42 pruebas previas al retomar; el código de la aplicación no cambió después de esos resultados.

Hubo una ejecución intermedia de Playwright con 21 aprobadas y 7 fallidas al endurecer el medidor. Los fallos eran falsos positivos: Chromium conserva rectángulos de controles en un `details` cerrado y el medidor confundía un borde parcialmente recortado por scroll con un botón obstruido. Se usa `checkVisibility` para contenido pintado y se comprueba obstrucción completa en controles visibles. Las interacciones reales verifican el acceso a los botones desplazando el panel. Tras corregir el medidor, las 28 pruebas aprobaron sin reintentos ni casos omitidos.

Las mediciones finales no registran desbordamientos, superposiciones ni controles completos bloqueados en los estados de mapa. Las solicitudes canceladas `ERR_ABORTED` registradas durante el montaje de React StrictMode o cambios de teselas no equivalen a fallos HTTP de la API; no hubo excepciones JavaScript no controladas en el recorrido normal.

## Regresión de distancias

Origen (-0.201, -78.504) y destino (-0.184, -78.486), expresados aquí como latitud-longitud. GeoJSON se conserva en longitud-latitud.

| Ruta | Referencia (km) | API (km) | Diferencia (m) |
|---|---:|---:|---:|
| Corta | 3,255669 | 3,2557 | 0,031 |
| Histórica | 3,306152 | 3,3062 | 0,048 |
| LightGBM | 3,297791 | 3,2978 | 0,009 |

Las tres cumplen ±1 metro y el máximo de 15 % de desvío. La interfaz redondea a 3,256 / 3,306 / 3,298 km. Ajustes a nodos: 104,7 m y 76,2 m, excluidos del recorrido. Los indicadores siguen representando concentración estimada ponderada por longitud, no probabilidad individual de accidente. La advertencia de demostración retrospectiva de junio de 2026 permanece visible y desarrollada en el diálogo.

## Capturas y reproducción

[Galería local de las 98 capturas](index.html). Cada carpeta `antes/<ancho>/` y `despues/<ancho>/` contiene:

- `01-inicio.png`: pantalla inicial.
- `02-panel-expandido.png`: panel y selección de puntos.
- `03-tres-rutas.png`: resultados reales.
- `04-rutas-en-mapa.png`: recorrido con panel contraído cuando está disponible.
- `05-predicciones.png`: cuadrículas activadas.
- `06-predicciones-panel.png`: cuadrículas y panel abierto.
- `07-advertencias.png`: diálogo del proyecto.

Hay 49 capturas por fase. `antes/mediciones.json` conserva la línea base y `despues/mediciones.json` contiene las mediciones finales. Al retomar solo se actualizó este último JSON con `--solo-mediciones`: los PNG ya esperaban el fundido y no se regeneraron. El [reporte de Playwright](pruebas-playwright.json) corresponde a la última ejecución.

Desde `frontend`, con ambos servidores ejecutándose:

```powershell
npm run test:e2e
npm run audit:visual
```

La segunda orden vuelve a generar las capturas finales. Para actualizar únicamente mediciones: `npm run audit:visual -- --solo-mediciones`. Instalación, dependencias y servidores se detallan en el [README](../../README.md).

## Archivos de entrega

Modificados: `src/App.tsx`, `src/components/MapView.tsx`, `src/styles.css`, `package.json`, `package-lock.json`, `.gitignore`, `README.md` y `VERIFICACION.md`.

Creados: `playwright.config.ts`, `e2e/responsive.spec.ts`, `e2e/audit-helpers.mjs`, `scripts/run-playwright.mjs`, `scripts/audit-visual.mjs` y esta carpeta de evidencias con galería, informe, JSON y PNG.

Chromium descargado, node_modules, dist y trazas temporales están excluidos de Git. Los cambios quedan disponibles para revisión; no se preparó el índice de Git ni se hizo commit o push.

La revisión final de Git solo muestra cambios bajo `frontend/`. Los hashes SHA-256 de los 15 archivos originales de `red_vial`, `resultados` y `datos_originales` coinciden con los registrados al comenzar la auditoría.

## Límites pendientes

- No se probaron teléfonos Android/iPhone físicos, Safari/WebKit, teclado virtual ni barras dinámicas del navegador.
- Los viewports no certifican todos los tamaños posibles, zoom del navegador o ajustes de texto del sistema.
- La emulación táctil incluye toques; no certifica gestos multitáctiles ni rendimiento en hardware móvil.
- No es una auditoría completa de accesibilidad con lector de pantalla.
- Las teselas y las fuentes externas requieren conectividad; las condiciones reales de redes móviles quedan fuera de esta ejecución.
- No se observaron defectos responsive pendientes en los tamaños y estados auditados. Se mantiene el alcance retrospectivo y la cobertura limitada de la demo.
