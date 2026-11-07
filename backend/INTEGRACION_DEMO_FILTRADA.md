# Integración controlada de la demo peatonal filtrada

**Actualización del MVP:** este documento conserva el ensayo histórico. Las nuevas ejecuciones usan `demo` + `peatonal_filtrada` por defecto; para auditoría original hay que seleccionar `RUTAINFORMADA_RED=original` explícitamente. Consulta la [configuración y entrega actuales](MVP_FILTRADO.md).

Ensayo local ejecutado el 5 de noviembre y revisado al cerrar el **6 de noviembre de 2026**, en `feature/ampliacion-cobertura-quito`. Se integra la copia demo de 19,13 km² mediante la entrada normal **`main:app`**, sin sustituir el valor por defecto ni activar la ampliada filtrada. Se parte de [la auditoría de permisos](ACCESO_PEATONAL.md) y [la validación de cobertura](VALIDACION_COBERTURA_PEATONAL.md).

## Activación exacta y reversibilidad

En una consola PowerShell, desde `backend`, usando el entorno virtual existente:

```powershell
$env:RUTAINFORMADA_COBERTURA = 'demo'
$env:RUTAINFORMADA_RED = 'peatonal_filtrada'
.\.venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8802 --reload
```

La prueba automatizada inició el mismo comando sin `--reload` para evitar reinicios durante las verificaciones. `python -m uvicorn main:app --reload` sigue siendo válido con el entorno virtual activado y estas variables. No se requiere otro punto de entrada ni un servidor de ensayo que reemplace `main:app`.

| Configuración | Resultado |
|---|---|
| `demo` + `peatonal_filtrada` | `red_vial/acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml` |
| `demo` + `original` | Original demo, exclusivamente para comparación/auditoría |
| `ampliada` + `original` | Modo experimental anterior, sin cambios en su grafo |
| `ampliada` + `peatonal_filtrada` | Error explícito al iniciar; no se habilita esa integración |
| Valor vacío o desconocido de `RUTAINFORMADA_RED` | Error explícito de configuración |
| Variable `RUTAINFORMADA_RED` ausente | Conserva `original`; sustitución definitiva pendiente |

La selección se lee al iniciar el proceso. Para comparar con el original, detén el servidor y establece explícitamente `$env:RUTAINFORMADA_RED = 'original'` antes de volver a iniciarlo. Para retirar las variables del ensayo de esa consola, usa `Remove-Item Env:RUTAINFORMADA_RED,Env:RUTAINFORMADA_COBERTURA -ErrorAction SilentlyContinue`. No se guardó la selección en archivos `.env`, variables de usuario/sistema ni configuración pública permanente.

No existe fallback entre grafos: un archivo ausente o inválido impide el arranque; una ruta no calculable devuelve su error. Los originales contienen restricciones y no se ofrecen como alternativa para sortear ese rechazo. No se descargan ni regeneran archivos al iniciar.

## Conectar React y Leaflet

Con el backend anterior en marcha, abre una segunda consola desde `frontend`:

```powershell
node scripts/ensayo-acceso.mjs
```

Abre `http://127.0.0.1:5185`. Este script existente inicia Vite aislado, establece `VITE_API_BASE_URL=/api` sólo en su proceso y envía `/api/*` a `http://127.0.0.1:8802`. No cambia `.env.local`, ni ocupa los puertos habituales 5173/8000, ni necesita ampliar CORS. Ambos servidores escuchan únicamente en loopback. No se hizo despliegue público ni se implementó Offline First.

## Red cargada, permisos e indicadores

La aplicación conserva **14.686 nodos, 43.248 aristas y 61 componentes fuertes/débiles**. La mayor componente tiene 14.381 nodos; los 305 nodos de las otras componentes siguen disponibles para recorridos internos. No fue necesario modificar `grafo.py`, `main.py`, `rutas.py` ni `geojson.py`: no exigen conectividad global ni recortan silenciosamente la red.

Las pruebas contrastan todas las aristas activas con el registro de permisos. Permanecen excluidas las **802 restringidas y 622 inciertas**. Se verifican además las aristas efectivamente elegidas en el piloto. La suite conserva el cotejo completo de geometrías, longitudes e indicadores contra los originales. No se modificaron valores históricos, LightGBM ni sus predicciones. Las escalas de pesos se calculan sobre la red seleccionada mediante las mismas fórmulas existentes; no se fijaron manualmente para reproducir distancias anteriores.

La carga de `main:app` se realiza al iniciar y se reutiliza durante el proceso. La prueba de ciclo de vida comprueba la lectura única con un proceso aislado, tanto para la selección original como para la filtrada.

La capa de predicción es exactamente `resultados/predicciones_demo_junio2026.geojson`, con **25 cuadrículas**, periodo `2026-06` y EPSG:4326. Los indicadores representan concentración estimada ponderada por longitud; no probabilidad individual de accidente. Es una demostración retrospectiva.

## Endpoints y regresión

Las respuestas reales de Uvicorn se guardan en [endpoints-uvicorn.json](evidencias/integracion-demo-filtrada/endpoints-uvicorn.json).

| Petición | Resultado filtrado |
|---|---|
| `GET /health` | 200; 14.686 nodos y 43.248 aristas |
| `GET /config` | 200; métodos existentes, 15 %, 300 m, periodo y advertencia del ensayo |
| `GET /predicciones` | 200; GeoJSON de 25 cuadrículas, idéntico a la capa demo |
| `POST /rutas`, piloto | 200; tres modalidades y geometrías continuas |
| Centro–este | 422: `Origen o destino demasiado lejos de la red con predicciones.` |
| Entre la isla Páramo y la componente principal | 422: `No existe una ruta conectada.` |
| Entre nodos conectados dentro de esa isla de 109 nodos | 200; no se descarta la componente pequeña |

Piloto: origen `lat=-0.201, lon=-78.504`; destino `lat=-0.184, lon=-78.486`. Referencias independientes, con **tolerancia de ±1 m**:

| Modalidad | Original, km | Filtrada, km | Diferencia, m |
|---|---:|---:|---:|
| Corta | 3,255669 | 3,255669 | 0,000 |
| Histórica | 3,306152 | 3,346387 | +40,235 |
| LightGBM | 3,297791 | 3,293076 | −4,715 |

La API redondea las distancias a cuatro decimales: **3,2557 / 3,3464 / 3,2931 km**. El frontend muestra tres: **3,256 / 3,346 / 3,293 km**. Las referencias originales siguen comprobándose al elegir `original`; no se reemplazaron globalmente ni se forzó su reproducción en la red filtrada.

Centro–este pasa de un ajuste de origen de 194,45 m a **333,80 m**; el límite continúa en 300 m. Las tres modalidades aceptadas respetan el 15 % respecto a la corta de la red elegida. Las distancias excluyen el acceso desde las coordenadas solicitadas hasta los nodos. Un ajuste geográfico permitido no verifica físicamente ese acceso.

## Presentación de modalidades y comprobación visual

Se corrigió el título «Tres formas de llegar»: ahora dice **«Tres modalidades de comparación»**, acompañado de «Las modalidades pueden compartir el mismo recorrido». El panel contraído y el anuncio accesible usan el mismo criterio. Se mantienen las tres tarjetas, sus indicadores y el resaltado Leaflet; no se fusionan ni alteran resultados de la API.

Se comprueba un caso real del registro cuya geometría es idéntica en las tres modalidades, además de un fixture unitario. La coincidencia no se anuncia como tres caminos geográficamente distintos.

Playwright usa Chromium instalado en el proyecto y el backend real. Las pruebas cubren selección por toque/clic y coordenadas, piloto, resaltado de las tres modalidades, indicadores, cuadrículas, leyenda, atribución, intercambio/reinicio, panel, redimensionado, carga, errores reales de cobertura/desconexión y fallos de transporte simulados identificados como tales.

Las capturas esperan la carga y opacidad final de las teselas. Son **emulación móvil**, no pruebas con teléfonos Android o iPhone físicos ni verificación en Safari/WebKit. El navegador integrado no pudo conectarse por falta de su puente disponible; se utilizó Playwright independiente.

## Reproducir las pruebas

Desde `backend`, para la suite completa de comparación original:

```powershell
$env:RUTAINFORMADA_COBERTURA = 'demo'
$env:RUTAINFORMADA_RED = 'original'
.\.venv\Scripts\python.exe -m pytest -v
```

Para los endpoints, carga y regresiones de la integración real filtrada:

```powershell
$env:RUTAINFORMADA_RED = 'peatonal_filtrada'
.\.venv\Scripts\python.exe -m pytest -v tests/test_api.py tests/test_ciclo_vida.py tests/test_cobertura.py tests/test_frontend_api.py tests/test_regresion.py tests/test_integracion_demo_filtrada.py
```

Desde `frontend`, con ambos servidores de ensayo en marcha:

```powershell
npm run build
npm test
$env:RUTAINFORMADA_RED = 'peatonal_filtrada'
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8802'
npm run test:integration
$env:PLAYWRIGHT_TEST_BASE_URL = 'http://127.0.0.1:5185'
npm run test:e2e -- --config playwright.demo-filtrada.config.ts
```

Playwright requiere acceso a las teselas de `tile.openstreetmap.org`. No se reemplazan por imágenes ficticias para hacer pasar una comprobación visual.

## Resultados finales y evidencias

Al retomar el trabajo, los 36 casos responsive restantes ya habían terminado correctamente y estaban registrados. No se repitieron las suites aprobadas; se inspeccionaron sus resultados y capturas, se verificaron los hashes y se completó esta documentación. Los archivos de ejecución y de pruebas no presentan cambios posteriores que invaliden esas ejecuciones.

| Verificación | Aprobadas | Fallidas en el resultado final | Evidencia |
|---|---:|---:|---|
| Suite completa backend, selección original de auditoría | 315 | 0 | [pytest-original.txt](evidencias/integracion-demo-filtrada/pytest-original.txt) |
| Integración `main:app` con demo filtrada | 72 | 0 | [pytest-filtrada.txt](evidencias/integracion-demo-filtrada/pytest-filtrada.txt) |
| Unitarias frontend | 37 | 0 | Salida de Vitest de esta fase, conservada en la conversación |
| Integración HTTP del cliente React con Uvicorn filtrado | 7 | 0 | Salida de Vitest de esta fase, conservada en la conversación |
| Playwright, 390 × 844 | 6 | 0 | [playwright-390.json](evidencias/integracion-demo-filtrada/playwright-390.json) |
| Playwright, otros seis tamaños | 36 | 0 | [playwright.json](evidencias/integracion-demo-filtrada/playwright.json) |
| Compilación de producción TypeScript + Vite | Correcta | — | Comando completado antes de la interrupción |

Las 315 pruebas conservan las 303 previas y añaden 12 casos de integración/configuración. Las 72 del modo filtrado repiten intencionadamente el contrato y las regresiones sobre esa selección; no son 72 pruebas nuevas. No se suman ejecuciones repetidas como casos únicos. Se añadió una prueba unitaria de presentación de modalidades coincidentes en el frontend.

Incidencias durante la preparación, ya resueltas:

- La primera suite tuvo 314 aprobadas y un fallo en una aserción nueva de identidad de objetos: otra prueba había cargado grafos distintos y desplazado la caché de un elemento. Se retiró esa aserción ajena a la conectividad; la prueba de lectura única por proceso se conserva y pasó en ambos modos. La suite completa corregida terminó con 315 aprobadas. Se conserva [el log inicial](evidencias/integracion-demo-filtrada/pytest-original-inicial.txt).
- El primer intento móvil tuvo tres fallos al no cargar ninguna tesela en el entorno aislado. Tras autorizar la ejecución de Playwright con acceso a OpenStreetMap, las seis pruebas de ese tamaño pasaron y después las otras 36. Se conserva [el resultado sin acceso a teselas](evidencias/integracion-demo-filtrada/playwright-sin-red.json). No se ocultó el fallo ni se sustituyó el mapa por imágenes simuladas.
- Persiste el aviso previo de deprecación Starlette/httpx; no se cambiaron dependencias en esta fase.

### Pantallas y revisión visual

Se ejecutaron seis pruebas en cada tamaño, sin omisiones ni reintentos automáticos en las dos ejecuciones finales:

| Ancho × alto | Resultado |
|---|---|
| 360 × 800 | 6 aprobadas |
| 390 × 844 | 6 aprobadas |
| 430 × 932 | 6 aprobadas |
| 768 × 1024 | 6 aprobadas |
| 1024 × 768 | 6 aprobadas |
| 1280 × 800 | 6 aprobadas |
| 1920 × 1080 | 6 aprobadas |

Se generaron **42 capturas**, seis por tamaño: inicial, resultados, cuadrículas, rechazo por cobertura, rechazo por desconexión y modalidades coincidentes. La [galería local](evidencias/integracion-demo-filtrada/index.html) permite abrir cada PNG a su resolución original.

La inspección visual incluyó ejemplos de los siete tamaños y los seis estados, además de las comprobaciones DOM de Playwright. No se observaron nuevos defectos que exigieran modificar estilos o funcionalidad: no hay desbordamiento horizontal; el mapa conserva espacio, controles, leyenda y atribución; los textos se ajustan al ancho. En pantallas pequeñas y de poca altura, las tarjetas y formularios continúan dentro del panel desplazable, por lo que una captura no muestra todo su contenido simultáneamente. Los rechazos 422 muestran el mensaje correspondiente sin rutas ficticias. La comparación de modalidades coincidentes mantiene las tres tarjetas sin prometer tres trayectos distintos.

No se hizo una nueva auditoría cartográfica de terreno ni una prueba en teléfonos físicos. La inspección de capturas complementa las pruebas; no certifica cada calle de Quito.

### Archivos de esta fase

Modificados:

- `backend/config.py`: selección explícita de red y rechazo de combinaciones no autorizadas.
- `backend/api.py`: advertencia de ensayo filtrado en `/config`, conservando sus claves y el resto del contrato.
- `backend/tests/test_api.py`, `backend/tests/test_regresion.py`, `backend/tests/test_cobertura.py`: referencias separadas para cada red y aislamiento de la variable de selección.
- `frontend/src/App.tsx`, `frontend/src/components/RouteResults.tsx`: presentación de modalidades sin prometer geometrías distintas.
- `frontend/src/test/App.test.tsx`, `frontend/src/test/integration/backend.test.ts`, `frontend/e2e/responsive.spec.ts`: protección de la presentación y referencias explícitas por red.
- `frontend/scripts/audit-visual.mjs`: localizador actualizado al título nuevo.
- `backend/README.md`, `backend/FRONTEND_API.md`, `frontend/README.md`: instrucciones y enlace a este ensayo.

Creados:

- `backend/tests/test_integracion_demo_filtrada.py`: selección, componentes, permisos, errores y ausencia de fallback.
- `frontend/e2e/demo-filtrada.spec.ts`, `frontend/playwright.demo-filtrada.config.ts`: pruebas y configuración del ensayo móvil con evidencias separadas.
- Este informe y `backend/evidencias/integracion-demo-filtrada/`: logs, respuestas HTTP, hashes, resultados Playwright, galería y capturas.

Los demás cambios que ya figuraban en `git status` pertenecen a fases anteriores y se conservaron. En particular, no se modificaron en esta fase `backend/predicciones.py` ni `frontend/src/components/MapView.tsx`, aunque ya estaban pendientes en Git.

### Integridad y estado al cerrar

La [comprobación SHA-256 final](evidencias/integracion-demo-filtrada/integridad-despues.json) confirma **diez archivos intactos**: cuatro GraphML, dos capas predictivas, los dos registros de decisiones, las etiquetas OSM derivadas y el modelo `.joblib`. No se reentrenó LightGBM ni se regeneraron datos. Tampoco se modificaron las fórmulas, el algoritmo ni las geometrías. Los grafos siguen excluidos de Git.

Al cerrar, no hay servidores accesibles en los puertos de ensayo 8802/5185; los comandos anteriores permiten volver a iniciarlos. No se cambió el valor predeterminado de FastAPI. No se hizo commit ni push.

## Limitaciones y decisión

La validación anterior conserva su alcance: la demo filtrada resolvió **95 de 100 pares espaciales** y perdió cinco por desconexión. No se repitió innecesariamente esa muestra; sus archivos siguen verificados por hash. Existen islas, permisos aún inciertos y accesos hasta los nodos no calculados. No es una certificación de seguridad física ni de accesibilidad universal.

La demo filtrada es la candidata recomendada para reemplazar el original cuando se autorice la sustitución: mejora los permisos documentados y maneja sus rechazos sin resultados inventados. Esa recomendación se limita a la demo; la ampliación sigue experimental con sus limitaciones ya documentadas. La selección por defecto permanece pendiente de revisión.
