# Coberturas de RutaInformada Quito

**Actualización del MVP:** este documento conserva el ensayo histórico. Las nuevas ejecuciones usan `demo` + `peatonal_filtrada` por defecto; para auditoría original hay que seleccionar `RUTAINFORMADA_RED=original` explícitamente. Consulta la [configuración y entrega actuales](MVP_FILTRADO.md).

Actualización posterior: [auditoría completa de acceso peatonal y copias candidatas](ACCESO_PEATONAL.md). Los resultados originales de este documento se conservan como referencia; las copias filtradas aún no sustituyen los grafos de FastAPI.

Verificación local del 4 de noviembre de 2026 en la rama `feature/ampliacion-cobertura-quito`. La zona original es la predeterminada. La ampliación queda disponible para evaluación explícita.

**Hallazgo para la decisión sobre el MVP.** Cuatro de las doce alternativas ampliadas recorren cinco vías que OpenStreetMap etiqueta con `access=no` y uso de transporte público. Además, el Sendero de Humboldt tiene una arista de 766,47 m sin vértices intermedios. Ambos hallazgos requieren revisión de acceso o trazado antes de recomendar estos recorridos a peatones.

## Elegir la cobertura

Desde `backend`, en PowerShell, inicia la demo así.

```powershell
$env:RUTAINFORMADA_COBERTURA = 'demo'
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Para el ensayo, detén ese proceso, selecciona la ampliación y vuelve a iniciarlo.

```powershell
$env:RUTAINFORMADA_COBERTURA = 'ampliada'
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Para comprobar el comportamiento predeterminado, detén Uvicorn y ejecuta lo siguiente.

```powershell
Remove-Item Env:RUTAINFORMADA_COBERTURA -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

La selección se lee al importar la configuración de cada proceso. El ciclo de vida carga y valida un grafo y el lector de predicciones guarda la primera carga válida en caché. Un valor vacío o distinto de los dos nombres exactos impide el arranque con un error de configuración. En React se sigue usando la URL de API habitual.

## Archivos y contrato

| Propiedad | Demo | Ampliada |
|---|---|---|
| GraphML, bajo `red_vial/` | `quito_demo_con_predicciones.graphml` | `ampliacion/quito_peatonal_ampliada_con_predicciones.graphml` |
| GeoJSON, bajo `resultados/` | `predicciones_demo_junio2026.geojson` | `ampliacion/predicciones_99_celdas_junio2026.geojson` |
| Superficie geodésica de la unión de polígonos WGS84 | 19,1282 km² | 77,5468 km² |
| Cuadrículas de junio de 2026 | 25 | 99 |
| Nodos / aristas dirigidas | 14.934 / 44.672 | 31.270 / 91.708 |
| Bbox oeste, sur, este, norte | [-78.51500015930877, -0.215000011004652, -78.478, -0.173] | [-78.54, -0.23, -78.47, -0.14] |
| Etiqueta de mapa | Zona demo · Quito | Zona ampliada · Quito |

Se leyeron los cuatro archivos locales. Ambos grafos son dirigidos y usan EPSG:4326. En cada arista se validaron longitud positiva, indicadores finitos y geometría con el cargador existente. Las dos capas contienen polígonos en longitud-latitud. La demo declara CRS84 y guarda `anio` y `mes`. La capa ampliada guarda `periodo` y carece del miembro opcional `crs`. Al leer las 99 celdas se comprueban las claves `cx,cy` únicas y el periodo. En memoria se exponen también año y mes. La prueba compara toda la respuesta con el archivo original, incluidas coordenadas, propiedades adicionales y valores predictivos.

`GET /health` cuenta los nodos y aristas del grafo cargado. `GET /config` calcula el bbox de la capa activa y publica sus advertencias. `GET /predicciones` sirve el GeoJSON de esa zona. `POST /rutas` utiliza el grafo preparado en el arranque. Se conservan el límite de ajuste de 300 m, el desvío máximo del 15 % entre nodos, las penalizaciones y los criterios de selección. Los indicadores son estimaciones retrospectivas de concentración de siniestros ponderadas por longitud. Las distancias excluyen los accesos a los nodos.

## Regresiones y rendimiento

Valores en kilómetros tal como los devuelve la API, con cuatro decimales. Se usaron las coordenadas y referencias independientes de `resultados/ampliacion/pruebas_rutas_ampliadas_20261104_150157.json`. La tolerancia fue de ±1 m por alternativa.

| Modo y recorrido | Corta | Histórica | LightGBM | Mediana POST |
|---|---:|---:|---:|---:|
| Demo, original | 3,2557 | 3,3062 | 3,2978 | 0,943 s |
| Ampliada, original | 3,2557 | 3,3062 | 3,2978 | 1,186 s |
| Ampliada, norte–sur | 8,8372 | 9,5384 | 9,5384 | 2,562 s |
| Ampliada, suroeste–noreste | 12,4871 | 13,6697 | 13,6697 | 2,447 s |
| Ampliada, centro–este | 5,2201 | 5,3515 | 5,3515 | 1,555 s |
| Ampliada, oeste–este | HTTP 422 | — | — | 0,164 s |

El origen de oeste–este requirió 375,83 m de ajuste. Las pruebas verificaron el rechazo y su mensaje. Las tres geometrías del piloto coincidieron también entre ambos grafos. En los otros tres casos aceptados las alternativas histórica y LightGBM coincidieron entre sí.

| Medición local | Demo | Ampliada |
|---|---:|---:|
| Carga y preparación del grafo | 6,32 s | 11,10 s |
| GET /health | 28,8 ms | 56,0 ms |
| GET /config | 2,6 ms | 2,8 ms |
| GET /predicciones | 3,9 ms | 7,7 ms |

Se midió cada modo en un proceso independiente, en secuencia, con FastAPI TestClient y el grafo real. La carga mide la entrada al ciclo de vida después de importar Python. Para cada endpoint se tomó la mediana de tres peticiones consecutivas después de la primera. La primera petición a `/config`, que también lee y valida el GeoJSON, tardó 94 y 27 ms respectivamente. La primera petición del piloto tardó 1,68 y 1,20 s. Son tiempos de este equipo para un solo cliente.

## Superposición geográfica y acceso

Se renderizaron en Leaflet con Chromium tanto las rutas devueltas por FastAPI como las vías de la descarga Overpass guardada en `resultados/ampliacion/cache_osmnx/`. El extracto tiene fecha OSM 2026-11-04 05:06:56 UTC e incluye 33.002 vías con etiqueta `highway`. Se inspeccionaron cuatro vistas generales y tres acercamientos con y sin superposición.

- Las doce geometrías coinciden con el GeoJSON de la auditoría anterior. Cada ruta comienza y termina en sus nodos ajustados, y los segmentos encajan en su sentido de recorrido.
- Los **4.002 pares consecutivos de posiciones** de las doce geometrías coinciden con segmentos presentes en el extracto OSM, contando repeticiones entre alternativas. Es una comprobación adicional a la continuidad topológica.
- La red final tiene **45.600 aristas dirigidas sin geometría detallada**. Para cada una se cotejaron ID de vía, coordenadas y adyacencia de los dos nodos en OSM. Todas coinciden con nodos consecutivos de su propia vía. Entre ellas hay 1.982 de al menos 100 m, contando ambos sentidos cuando existen.
- El máximo de toda la red es el **Sendero de Humboldt**, vía 1075574449, entre los nodos 4615266609 y 4615266656. El extracto representa esos 766,47 m mediante una recta. Su forma y transitabilidad en terreno siguen pendientes de comprobación. En las rutas ensayadas los máximos observados fueron 208,77 m en la vía de servicio 149787548 y 204,92 m en la avenida Mariscal Sucre para norte–sur.
- Se cotejaron las etiquetas de las vías correspondientes a cada par de posiciones. En los tramos indicados todas las vías coincidentes tenían `access=no` y carecían de una excepción peatonal explícita. La histórica del piloto usa la vía 1059162235. LightGBM del piloto usa 149787548, 219886408 y 431716070. Histórica y LightGBM de norte–sur usan 1171326264. Las etiquetas incluyen `psv=yes` o `bus=designated`. Los trazados del piloto son iguales en demo y ampliada. El modo ampliado publica el aviso de acceso en `/config` para que React lo presente en «Sobre los datos».
- La geometría de comparación proviene de la misma fuente cartográfica que el grafo. La coincidencia respalda su fidelidad a ese extracto. Para la incorporación oficial queda revisar los permisos peatonales, los pasos o aceras disponibles y los tramos largos con información independiente o trabajo de campo.

[Cuatro recorridos superpuestos a OSM](evidencias/cobertura/recorridos-osm.png) · [Tres tramos largos con comparación lado a lado](evidencias/cobertura/tramos-largos-osm.png)

## Verificación ejecutada

| Proceso y alcance | Aprobadas | Fallidas |
|---|---:|---:|
| Backend completo, variable ausente, incluidas las 222 anteriores | 233 | 0 |
| Backend ampliado, `tests/test_cobertura.py` | 14 | 0 |
| Frontend, componentes y cliente | 36 | 0 |
| Integración HTTP con la demo restablecida | 7 | 0 |
| Chromium en modo ampliado, escenario de cobertura a 360 y 1280 px | 2 | 0 |
| Chromium con la demo restablecida, suite completa en siete tamaños | 42 | 0 |

La compilación de producción aprobó. El escenario de cobertura seleccionó las cuadrículas, envió coordenadas desde React, verificó las tres distancias reales y seleccionó LightGBM. En la ampliación usó el recorrido norte–sur. La demo se verificó tras detener el proceso ampliado y arrancar otro sin la variable. Volvió a servir las 25 celdas y su red original.

Para el navegador se usó una instancia temporal de Vite con proxy local a Uvicorn, separada de la sesión habitual. Las peticiones llegaron a FastAPI real. La integración HTTP de demo comprobó también el preflight CORS directamente. La primera salida temporal de Playwright fue rechazada por Windows al crear la carpeta. Las ejecuciones de la tabla usaron una carpeta de pruebas con escritura permitida. Pytest conserva el aviso de deprecación de Starlette/httpx.

Para reproducir el backend, desde `backend`:

```powershell
Remove-Item Env:RUTAINFORMADA_COBERTURA -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -q
$env:RUTAINFORMADA_COBERTURA = 'ampliada'
.\.venv\Scripts\python.exe -m pytest tests/test_cobertura.py -q
```

La suite histórica incluye referencias exclusivas de la demo. Para reproducir el recorrido de navegador en el modo elegido, arranca FastAPI y Vite y ejecuta `npm run test:e2e -- e2e/cobertura.spec.ts` desde `frontend`.

## Archivos de la integración

| Archivos | Finalidad |
|---|---|
| `backend/config.py`, `backend/api.py`, `backend/predicciones.py` | Seleccionar el par de archivos al inicio, identificar la zona y adaptar la fecha de la capa ampliada |
| `backend/tests/test_cobertura.py` | Selección y errores de configuración, integridad de la capa, conectividad, regresiones y orientación |
| `frontend/src/components/MapView.tsx`, `frontend/src/test/MapView.test.tsx` | Mostrar la etiqueta de la zona activa y verificarla |
| `frontend/e2e/cobertura.spec.ts`, `frontend/playwright.config.ts` | Probar los dos perfiles y permitir un servidor local aislado |
| `backend/README.md`, `backend/FRONTEND_API.md`, `frontend/README.md`, este informe y los dos PNG | Operación, contrato y evidencias de revisión |

Los GraphML siguen excluidos de Git. La activación oficial de la cobertura ampliada queda pendiente de revisión.
