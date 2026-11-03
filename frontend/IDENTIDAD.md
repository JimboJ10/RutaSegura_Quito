# RutaInformada Quito · cambio de identidad pública

Verificación realizada el 3 de noviembre de 2026.

**Nombre:** RutaInformada Quito.  
**Eslogan:** Decide tu camino con datos.

Aplicación web experimental que permite comparar rutas peatonales en una zona del centro-norte de Quito utilizando información histórica de siniestros de tránsito e inteligencia artificial.

## Qué cambió

- Cabecera, nombre accesible del enlace de inicio, título de pestaña y descripción HTML.
- Presentación del planificador, estado inicial y diálogo informativo, con el eslogan y la descripción aprobados.
- El diálogo enfoca su título y comienza arriba al abrirse. Al agregar la descripción, la inspección visual detectó que el foco nativo en el botón de cierre podía ocultar inicialmente la advertencia; se corrigió sin cambiar el resto del flujo.
- `proyecto` en `/health` y `/config` devuelve **RutaInformada Quito**. Swagger muestra **RutaInformada Quito API**. No cambian claves JSON, endpoints, tipos ni versión de API.
- README del frontend, README del backend y contrato de integración.

La advertencia se conserva:

> Demostración retrospectiva con datos de junio de 2026. Los indicadores no representan probabilidades individuales de accidente ni garantizan la seguridad de los recorridos.

La cobertura limitada al centro-norte de Quito, el carácter retrospectivo y la exclusión de accesos hasta nodos ajustados siguen explicados. Las etiquetas «Ruta más corta», «Ruta histórica» y «Ruta LightGBM» ya eran neutrales y se mantienen. No se encontraron promesas de evitar accidentes ni garantizar seguridad.

El favicon y el símbolo de cabecera representan un recorrido y no contienen el nombre anterior: se conservaron. No fue necesario modificar estilos, breakpoints ni distribución.

## Referencias conservadas intencionalmente

- Carpeta raíz y repositorio `RutaSegura_Quito`.
- Identificador privado npm `rutasegura-quito`, lock y dependencias.
- Módulo interno `useRutaSegura.ts` y sus importaciones.
- Variable `RUTASEGURA_CORS_ORIGINS`, variables existentes y archivos de configuración de red.
- Nombres de módulos Python, datasets, GraphML, GeoJSON y modelos.
- `VERIFICACION.md`, el informe y las capturas de `evidencias/auditoria-responsive/`: son evidencias de la auditoría anterior con la identidad usada entonces.
- Archivos históricos de investigación y documentos externos.

La búsqueda final de referencias en el código activo solo encuentra los nombres internos del hook y de la variable CORS con sus pruebas. Las dos aserciones de backend actualizadas comparaban exclusivamente el nombre público anterior; las aserciones de algoritmos, contratos, distancias y geometrías se conservaron.

## Archivos modificados y creados

| Archivo | Cambio |
|---|---|
| `frontend/index.html` | Título y descripción |
| `frontend/src/App.tsx` | Cabecera, accesibilidad, descripción, eslogan y foco del diálogo |
| `frontend/src/components/Planner.tsx` | Eslogan en presentación |
| `frontend/src/test/fixtures.ts` | Nombre público en configuración de prueba |
| `frontend/README.md` | Identidad, alcance y ejecución de pruebas |
| `backend/config.py` | Valor de PROYECTO |
| `backend/api.py` | Health utiliza el mismo nombre público que config |
| `backend/main.py` | Nombre en docstring; el título Swagger ya deriva de PROYECTO |
| `backend/tests/test_api.py` | Nombre esperado en health |
| `backend/tests/test_frontend_api.py` | Nombre esperado en config |
| `backend/README.md` | Identidad y ejemplos |
| `backend/FRONTEND_API.md` | Identidad y valores de presentación de la API |
| `frontend/e2e/identity.spec.ts` — nuevo | Nombre, metadatos, cabecera, contenido científico, foco y capturas |
| `frontend/IDENTIDAD.md` — nuevo | Este informe |
| `frontend/evidencias/identidad-publica/` — nuevo | 21 PNG y 2 reportes JSON |

No se modificaron dependencias, algoritmo, parámetros, geometrías, predicciones, modelos, datos ni archivos de configuración de red.

## Pruebas y resultados

| Ejecución | Aprobadas | Fallidas |
|---|---:|---:|
| Frontend: `npm test` | 35 | 0 |
| Integración real: `npm run test:integration` | 7 | 0 |
| Backend: `.\.venv\Scripts\python.exe -m pytest -v` | 222 | 0 |
| Playwright completo: 28 escenarios existentes + 7 de identidad | 35 | 0 |
| Revisión dirigida tras ajustar el foco del diálogo | 14 | 0 |

Son **299 casos distintos**, más la repetición dirigida de 14 casos de identidad/redimensionado/diálogo después del último ajuste. La compilación final `npm run build` también aprobó, con TypeScript sin errores. Las 35 pruebas unitarias se repitieron después de ese ajuste. No se repitió la suite de backend porque el cambio posterior solo afectó al foco del diálogo.

Los reportes completos y dirigidos están en [pruebas-playwright.json](evidencias/identidad-publica/pruebas-playwright.json) y [pruebas-dialogo.json](evidencias/identidad-publica/pruebas-dialogo.json). Ambas ejecuciones de navegador terminaron sin reintentos ni casos omitidos.

La primera integración falló por una diferencia preexistente de entorno: `.env.local` apuntaba a una dirección Wi-Fi y la API local escuchaba en loopback. Para verificar se utilizó `VITE_API_BASE_URL=http://127.0.0.1:8000` únicamente en los procesos de Vite e integración. No se editó `.env.local`, CORS, firewall ni ninguna IP en el código. La ejecución inicial de navegador se interrumpió al identificar esa causa y se repitió con conexión real a FastAPI.

Uvicorn sigue iniciando desde `backend` con `python -m uvicorn main:app --reload`. Se verificó el nombre nuevo en health/config y el título de OpenAPI.

## Rutas y responsive

Las pruebas reales conservan selección manual, marcadores A/B, mapa, tres alternativas, resaltado, cuadrículas, panel expandible/contraíble, intercambio, reinicio, errores y carga.

| Ruta | Referencia (km) | API (km) | Diferencia (m) |
|---|---:|---:|---:|
| Corta | 3,255669 | 3,2557 | 0,031 |
| Histórica | 3,306152 | 3,3062 | 0,048 |
| LightGBM | 3,297791 | 3,2978 | 0,009 |

Las tres cumplen ±1 metro y el máximo del 15 % de desvío. Se conserva el orden GeoJSON longitud-latitud y las distancias de ajuste excluidas del recorrido.

Se verificaron **360×800, 390×844, 430×932, 768×1024, 1024×768, 1280×800 y 1920×1080** en Chromium 156 mediante Playwright 1.64.1. El nombre más largo cabe sin solaparse con el estado de conexión y no provoca desbordamiento horizontal. Se inspeccionaron capturas de celular, tablet y escritorio, incluyendo el diálogo corregido.

## Capturas de la nueva identidad

Cada carpeta contiene `01-inicio.png`, `02-presentacion.png` y `03-advertencias.png`: 21 capturas en total.

| Viewport | Inicio | Presentación | Advertencias |
|---|---|---|---|
| 360×800 | [Ver](evidencias/identidad-publica/360x800/01-inicio.png) | [Ver](evidencias/identidad-publica/360x800/02-presentacion.png) | [Ver](evidencias/identidad-publica/360x800/03-advertencias.png) |
| 390×844 | [Ver](evidencias/identidad-publica/390x844/01-inicio.png) | [Ver](evidencias/identidad-publica/390x844/02-presentacion.png) | [Ver](evidencias/identidad-publica/390x844/03-advertencias.png) |
| 430×932 | [Ver](evidencias/identidad-publica/430x932/01-inicio.png) | [Ver](evidencias/identidad-publica/430x932/02-presentacion.png) | [Ver](evidencias/identidad-publica/430x932/03-advertencias.png) |
| 768×1024 | [Ver](evidencias/identidad-publica/768x1024/01-inicio.png) | [Ver](evidencias/identidad-publica/768x1024/02-presentacion.png) | [Ver](evidencias/identidad-publica/768x1024/03-advertencias.png) |
| 1024×768 | [Ver](evidencias/identidad-publica/1024x768/01-inicio.png) | [Ver](evidencias/identidad-publica/1024x768/02-presentacion.png) | [Ver](evidencias/identidad-publica/1024x768/03-advertencias.png) |
| 1280×800 | [Ver](evidencias/identidad-publica/1280x800/01-inicio.png) | [Ver](evidencias/identidad-publica/1280x800/02-presentacion.png) | [Ver](evidencias/identidad-publica/1280x800/03-advertencias.png) |
| 1920×1080 | [Ver](evidencias/identidad-publica/1920x1080/01-inicio.png) | [Ver](evidencias/identidad-publica/1920x1080/02-presentacion.png) | [Ver](evidencias/identidad-publica/1920x1080/03-advertencias.png) |

Para repetir la verificación conservando el reporte histórico, desde `frontend` y con ambos servidores iniciados:

```powershell
$env:PLAYWRIGHT_JSON_OUTPUT_FILE = Join-Path (Get-Location) 'evidencias\identidad-publica\pruebas-playwright.json'
npm run test:e2e
```

Las capturas esperan fuentes y teselas completamente visibles. Las pruebas de identidad usan la API real y generan nuevas capturas al ejecutarse.

## Pendientes y límites

- Esta etapa se verificó mediante emulación en Chromium; no se repitieron pruebas en teléfonos físicos ni en Safari.
- La configuración Wi-Fi que ya existía se conserva; para volver a probar desde el teléfono, el arranque de API/Vite debe corresponder a esa configuración, según los README.
- Continúa un aviso previo de deprecación Starlette/httpx en pytest. No se actualizaron dependencias por estar fuera del alcance.
- No se detectaron fallos funcionales pendientes en las verificaciones finales.
- No se realizaron commits, push, cambios de repositorio ni despliegues.
