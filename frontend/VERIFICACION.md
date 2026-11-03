# Verificación del frontend de RutaSegura Quito

Fecha: 3 de noviembre de 2026. Auditoría responsive completada, conservando los cambios y resultados de la sesión interrumpida.

## Resultado comprobado

| Comprobación | Resultado |
|---|---|
| Compilación: `npm run build` | Correcta; TypeScript sin errores |
| `npm test` | 35 aprobadas, 0 fallidas |
| `npm run test:integration` | 7 aprobadas, 0 fallidas, contra FastAPI real |
| `npm run test:e2e` | 28 aprobadas, 0 fallidas, Chromium real |
| Cuadrículas | 25; GeoJSON en longitud-latitud |
| CORS local | Preflight autorizado desde 127.0.0.1:5173 |
| Capturas | 98 PNG: 49 antes y 49 después |
| Archivos protegidos | Sin cambios en backend, GraphML, datos, resultados ni modelos |

La compilación y las 42 pruebas unitarias/de integración finalizaron correctamente antes de la interrupción. Después solo se ajustaron las herramientas de auditoría y la documentación: se conservaron esos resultados y se repitió la suite de navegador por el cambio en su medidor compartido. Las 222 pruebas del backend corresponden a la fase anterior y no se repitieron en esta auditoría.

## Regresión con FastAPI real

Origen: latitud -0.201, longitud -78.504. Destino: latitud -0.184, longitud -78.486.

| Ruta | Referencia (km) | API (km) | Diferencia (m) |
|---|---:|---:|---:|
| Corta | 3,255669 | 3,2557 | 0,031 |
| Histórica | 3,306152 | 3,3062 | 0,048 |
| LightGBM | 3,297791 | 3,2978 | 0,009 |

Todas cumplen ±1 metro y el límite del 15 %. Ajustes al nodo: 104,7 m en origen y 76,2 m en destino; excluidos de la distancia de recorrido. La interfaz muestra 3,256, 3,306 y 3,298 km al redondear a tres decimales.

## Alcance

- Las 35 pruebas unitarias/de componentes cubren el cliente HTTP, validaciones, cancelación, respuestas antiguas, formularios y estados. Usan datos sintéticos; jsdom no verifica píxeles.
- Las 7 pruebas de integración consultan los cuatro endpoints reales y comprueban GeoJSON, continuidad, indicadores, regresión, errores y preflight CORS.
- Las 28 pruebas de Chromium ejecutan cuatro escenarios en cada uno de los siete tamaños: mapa, puntos, tres rutas reales, resaltado, panel, cuadrículas, intercambio, reinicio, dimensiones, atribución, controles, redimensionado, errores, carga y recuperación.
- La demora de respuesta y los cortes de red se simulan en Playwright. La respuesta demorada conserva el contenido real de FastAPI; el error de cobertura HTTP 422 también es real.
- Se inspeccionaron visualmente capturas de los estados principales en todos los tamaños, además de comprobar DOM e interacciones.

| Viewport probado | Resultado final |
|---|---|
| 360 × 800 | Sin desbordamiento horizontal; mapa, panel y leyenda utilizables |
| 390 × 844 | Sin desbordamiento horizontal; mapa, panel y leyenda utilizables |
| 430 × 932 | Sin desbordamiento horizontal; mapa, panel y leyenda utilizables |
| 768 × 1024 | Panel lateral contraíble; mapa y controles visibles |
| 1024 × 768 | Panel lateral contraíble; mapa y controles visibles |
| 1280 × 800 | Mapa y panel de rutas verificados |
| 1920 × 1080 | Mapa y panel de rutas verificados |

## Evidencias y límites

Consulta el [informe de auditoría](evidencias/auditoria-responsive/INFORME.md), la [galería antes/después](evidencias/auditoria-responsive/index.html) y el [reporte de Playwright](evidencias/auditoria-responsive/pruebas-playwright.json). La reproducción está documentada en [README.md](README.md).

El navegador integrado no pudo inicializar su puente nativo. Se utilizó la alternativa Playwright + Chromium solicitada por el usuario, con los permisos de instalación y red correspondientes. Las capturas finales esperan las fuentes y el fundido de las teselas; al retomar se conservaron los PNG y solo se actualizaron las mediciones.

Las pruebas móviles son **emulación en Chromium**, con toque automatizado en los tamaños de celular. Quedan pendientes Android/iPhone físicos, Safari/WebKit, teclado virtual, barras dinámicas, áreas seguras reales, gestos multitáctiles y auditoría completa con lector de pantalla. Se probó apertura/cierre del diálogo con teclado y botón, incluido el desplazamiento necesario en pantallas pequeñas.

No se realizaron commits, push, despliegues ni cambios de firewall.
