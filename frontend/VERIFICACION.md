# Verificación del MVP · Frontend Fase 1

Fecha: 3 de noviembre de 2026.

## Resultado comprobado

| Comprobación | Resultado |
|---|---|
| `npm run build` | Correcto; TypeScript sin errores |
| `npm test` | 35 aprobadas, 0 fallidas |
| `npm run test:integration` | 7 aprobadas, 0 fallidas, contra FastAPI real |
| Backend: `.venv\\Scripts\\python.exe -m pytest -q` | 222 aprobadas, 0 fallidas; aviso previo de deprecación Starlette/httpx |
| Cuadrículas reales | 25, GeoJSON en longitud-latitud |
| CORS local | Preflight autorizado desde 127.0.0.1:5173 |
| Archivos protegidos | Backend, datos, resultados, GraphML y modelo sin modificaciones |

Las pruebas HTTP de integración ejecutan el cliente real del frontend con el servidor Uvicorn local. Confirman las siguientes distancias:

| Ruta | Referencia (km) | Respuesta API (km) | Diferencia (m) |
|---|---:|---:|---:|
| Corta | 3,255669 | 3,2557 | 0,031 |
| Histórica | 3,306152 | 3,3062 | 0,048 |
| LightGBM | 3,297791 | 3,2978 | 0,009 |

Todas cumplen ±1 metro. Ajustes al nodo: 104,7 m en origen y 76,2 m en destino. No están incluidos en las distancias de recorrido.

## Alcance de las pruebas

- Serialización exacta de origen/destino; coordenadas numéricas con campos `lat` y `lon`.
- GeoJSON válido para el cliente, polígonos de un anillo y rutas MultiLineString. Rechazo de resultados incompletos e indicadores ausentes.
- Validaciones de puntos, errores HTTP 422/503/500, falta de URL, pérdida de conexión, cancelación y timeout.
- Respuestas antiguas ignoradas aunque el transporte no respete la cancelación.
- Panel: ejemplo, comparación, elección de alternativa, reinicio, coordenadas manuales y reintentos.
- Montaje de Leaflet real en jsdom, controles, activación de cuadrículas, cambio de indicador y reintento de capa.
- Integración real: salud, configuración, 25 cuadrículas, continuidad, métricas, límite del 15 %, regresión, errores y preflight CORS.

Las pruebas de componentes utilizan datos sintéticos aislados. Las pruebas de App sustituyen el componente de mapa; las pruebas de MapView montan Leaflet real en un DOM simulado con SVG y ResizeObserver habilitados. **Ninguna de esas pruebas verifica píxeles, teselas de OpenStreetMap, gestos táctiles ni ausencia de desbordamiento.**

Se corrigió una carrera detectada por las pruebas: la selección inicial de «Ruta más corta» podía sobrescribir una alternativa que el usuario acababa de elegir. Ahora esa selección se establece al iniciar el cálculo.

## Revisión visual pendiente

No se pudo abrir el navegador para inspeccionar la aplicación: la revisión automática rechazó Chrome y se rechazó la autorización para la URL local en la vista previa integrada. No se usaron mecanismos alternativos para sortear ese bloqueo.

El CSS implementa diseño Mobile First, ancho flexible, panel inferior hasta 767 px, panel lateral desde 768 px, safe areas y altura dinámica. Estos cambios **no certifican** el resultado visual sin inspección del navegador.

| Ancho solicitado | Comprobación visual de desbordamiento |
|---:|---|
| 360 px | Pendiente |
| 390 px | Pendiente |
| 768 px | Pendiente |
| 1280 px | Pendiente |

Lista para la revisión manual autorizada:

1. En cada ancho, comprobar que no se requiere desplazamiento horizontal y que todos los botones se alcanzan.
2. Abrir y cerrar el panel; verificar atribución OSM, controles de zoom, leyendas y mapa sin áreas vacías.
3. Seleccionar ambos puntos con toque/clic, cambiar uno, intercambiar, restablecer y comparar.
4. Usar el ejemplo conocido; elegir cada tarjeta y centrar su recorrido.
5. Activar las 25 cuadrículas, cambiar indicador y comprobar leyenda y colores.
6. Probar coordenadas fuera de cobertura y pérdida/recuperación de conexión.
7. Navegar con Tab/Enter, revisar foco visible, formulario manual, diálogo y lector de pantalla.
8. En Android/iPhone físicos: revisar orientación, teclado virtual, áreas seguras y gestos. No se han probado dispositivos físicos.

No se han realizado commits, push, despliegues ni cambios de firewall.
