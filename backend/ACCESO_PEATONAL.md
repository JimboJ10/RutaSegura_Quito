# Auditoría de acceso peatonal

Revisión posterior: [validación de conectividad y muestra origen–destino](VALIDACION_COBERTURA_PEATONAL.md). Amplía la prueba a 100 pares espaciales por cobertura y registra nuevos usos del Sendero de Humboldt; los resultados de esta auditoría inicial permanecen como referencia.

Revisión del 4 de noviembre de 2026 en `feature/ampliacion-cobertura-quito`. Se generaron **dos copias candidatas**, sin sustituir los grafos de `main:app`. La configuración normal de FastAPI sigue apuntando a los originales y sigue reproduciendo sus referencias anteriores. No se modificaron LightGBM, predicciones, algoritmos, geometrías originales ni datos históricos.

Las copias excluyen las prohibiciones documentadas y ponen en cuarentena los permisos que necesitan aclaración. Están preparadas para revisión técnica. No constituyen una certificación de transitabilidad física ni de acceso desde las coordenadas del usuario hasta la red.

## Fuente y decisiones reproducibles

Se usó la descarga Overpass local `resultados/ampliacion/cache_osmnx/e275a3de6ac9e0fbd4a90530b29956a6a15357c6.json`, con fecha OSM `2026-11-04T05:06:56Z`. No se volvió a descargar la red. Las 14.737 vías referenciadas por la demo y las 29.926 de la ampliada están presentes en ese extracto.

Los GraphML conservan algunas etiquetas `access`, pero no `foot`. Por eso no bastaba filtrar sus atributos. Se cotejó cada par consecutivo de coordenadas de cada arista con su propia vía OSM, incluidos los nodos intermedios que la simplificación había quitado del grafo. No se confundieron aristas paralelas ni vías que coinciden geométricamente. Las etiquetas `access` existentes en 1.364 aristas demo y 4.712 ampliadas coincidieron con la fuente.

La política `peatonal-v1` está implementada en [el script offline](../scripts/auditar_acceso_peatonal.py).

| Evidencia | Decisión del ensayo |
|---|---|
| `foot=yes`, `designated`, `official` o `permissive` | Respeta la autorización específica frente a `access` general |
| `foot=no`, `private`, `use_sidepath` u otros usos restringidos | Excluye ese tramo del tránsito peatonal público general |
| `access=no/private` sin excepción peatonal | Excluye; `bus` y `psv` no autorizan a caminar |
| `destination`, `customers`, `permit`, `delivery`, valores desconocidos | Revisión; la API no conoce destino autorizado, permiso personal ni finalidad |
| Condiciones o sentidos de acceso peatonal no evaluados, horarios o cierres | Revisión; no se inventa una autorización permanente |
| Portón, barrera u obstáculo sin información suficiente | Revisión; se excluyen las aristas que lo atraviesan |
| Aceras, senderos y calles compatibles sin prohibición | Conserva como «sin restricción documentada», sin afirmar permiso explícito |
| Troncal, enlace troncal, escalera vertical o camino de caballos sin `foot` | Revisión conservadora, no declaración de ilegalidad |
| `motor_vehicle=no`, `bicycle=no`, ausencia de acera o bordillo | No equivalen por sí solos a prohibición peatonal |

La prioridad modal sigue la documentación de [access](https://wiki.openstreetmap.org/wiki/Key:access) y [foot](https://wiki.openstreetmap.org/wiki/Key:foot). Las [restricciones condicionales](https://wiki.openstreetmap.org/wiki/Conditional_restrictions) necesitan contexto que esta API no recibe. Una autorización `foot` incondicional prevalece sobre una condición general `access`; una condición específica `foot` se deja en revisión. No se encontraron condiciones de acceso ni sentidos peatonales específicos en las vías/nodos usados por estos grafos; se protegieron esos casos con pruebas sintéticas.

Se respetaron **48 vías demo y 113 ampliadas con `access=no` y autorización `foot` positiva** al clasificar el permiso de la vía. Una barrera independiente puede seguir impidiendo su uso. Los bordillos con `wheelchair=no` no se trataron como prohibiciones para todo peatón. Esto no es una auditoría de accesibilidad universal.

Los estados de cada arista son excluyentes. «Autorización explícita» en el registro significa que al menos una fuente de esa arista contiene una autorización y ninguna contiene veto/incertidumbre; no implica que todos sus puntos tengan autorización expresa. Si hay un veto y una incertidumbre simultáneos, prevalece el veto. Los motivos individuales se conservan completos.

## Las cinco vías iniciales

Todas tienen `highway=service`, `access=no` y **no tienen `name`, `foot`, `motor_vehicle`, `sidewalk` ni restricciones condicionales** en el extracto. Por tanto se clasificaron como restringidas para tránsito peatonal público según esos datos, sin trasladar la autorización de buses a peatones.

| Vía OSM | Longitud de la vía OSM, m | `psv` | `bus` | Demo / ampliada, aristas afectadas | Rutas anteriores |
|---|---:|---|---|---|---|
| [1059162235](https://www.openstreetmap.org/way/1059162235) | 339,340 | yes | designated | 6 / 6 | Histórica del piloto, ambas coberturas |
| [149787548](https://www.openstreetmap.org/way/149787548) | 1.107,975 | yes | ausente | 28 / 28 | LightGBM del piloto, ambas |
| [219886408](https://www.openstreetmap.org/way/219886408) | 118,693 | yes | ausente | 2 / 2 | LightGBM del piloto, ambas |
| [431716070](https://www.openstreetmap.org/way/431716070) | 29,727 | yes | ausente | 2 / 2 | LightGBM del piloto, ambas |
| [1171326264](https://www.openstreetmap.org/way/1171326264) | 94,467 | ausente | designated | 0 / 4 | Histórica y LightGBM de norte–sur, ampliada |

Longitudes de esta tabla medidas geodésicamente sobre la vía fuente, una sola vez. Las aristas simplificadas pueden agrupar varios ID OSM, y se cuentan ambos sentidos. Por ello las filas no deben sumarse para obtener aristas únicas ni sus longitudes sustituir las distancias del algoritmo. Por ejemplo, `219886408` y `431716070` están en la misma arista entre `347396199` y `9461878432`, junto con parte de `149787548`.

[cinco-vias.json](evidencias/acceso/cinco-vias.json) enumera **todos** los nodos OSM y cada `(u,v,key)` afectado, la presencia en ambas coberturas, las etiquetas completas y las rutas usuarias. Los CSV comprimidos detallan la longitud exacta de cada arista. Ninguna de esas cinco vías aparece en las copias filtradas.

## Resultado de la revisión completa

Todas las cifras de aristas son dirigidas e incluyen las paralelas. No deben sumarse demo y ampliada como si fueran territorios independientes.

| Medida | Demo | Ampliada |
|---|---:|---:|
| Aristas originales | 44.672 | 91.708 |
| Aristas con restricción confirmada en OSM | **802** | **1.702** |
| Aristas apartadas por incertidumbre | **622** | **1.302** |
| Total de aristas retiradas | 1.424 | 3.004 |
| Aristas conservadas | **43.248** | **88.704** |
| Vías fuente con veto | 53 | 168 |
| Nodos fuente con veto | 290 | 640 |
| Vías fuente con incertidumbre | 11 | 40 |
| Nodos fuente con incertidumbre | 355 | 690 |

Se encontraron prohibiciones generales en vías y portones privados, además de **tres nodos `foot=no`, que afectan a diez aristas dirigidas en cada cobertura**. Los permisos inciertos incluyen portones sin etiquetas de acceso, bloques/cadenas/barreras no especificadas, permisos por finalidad, horarios y clases viales sin autorización suficiente. No se dedujo una prohibición solamente por falta de etiqueta `foot` en una calle corriente.

La revisión de nodos amplió el hallazgo inicial: diez de las doce alternativas originales de la ampliada usaban alguna arista ahora excluida por veto **o** incertidumbre. En la demo resultaron afectadas cinco de las seis alternativas evaluables de piloto y centro–este. Esto es más amplio que las cuatro alternativas relacionadas con las cinco vías iniciales.

## Conectividad y cobertura

Se retiraron exclusivamente aristas clasificadas y los nodos que quedaron aislados. Se conservaron todas las otras componentes, aceras, geometrías, longitudes e indicadores. No se añadieron conexiones ni puntuaciones. La prueba independiente recorre todas las aristas candidatas y compara sus datos con el original.

| Medida antes → después | Demo | Ampliada |
|---|---|---|
| Nodos | 14.934 → 14.686 | 31.270 → 30.693 |
| Componentes débiles y fuertes | 1 → 61, en ambos casos | 1 → 110, en ambos casos |
| Nodos de la componente mayor | 14.934 → 14.381 | 31.270 → 30.153 |
| Longitud dirigida total, km | 1.642,916 → 1.554,962 | 3.717,735 → 3.519,750 |
| Celdas que intersectan alguna arista | 25 → 25, de 25 | 85 → 85, de 99 |
| Superficie de polígonos predictivos, km² | 19,1282, intacta | 77,5468, intacta |
| Área aproximada a ≤300 m de algún nodo, km² | 19,1192 → 19,1091 | 63,2907 → 63,2310 |

La última fila usa una malla fija de 100 m en UTM 17S, 1.886/7.800 muestras dentro de los polígonos y distancia geodésica al nodo más cercano. Es una **aproximación**, no un polígono de cobertura exacto ni prueba de acceso caminable. Tener cuadrícula predictiva o nodo cercano no garantiza camino entre componentes. Se conserva el HTTP 422 existente para ausencia de conexión.

## Recorridos antes y después

Distancias en km, calculadas por las funciones originales y registradas con precisión completa en [informe.json](evidencias/acceso/informe.json). Las nuevas referencias se mantienen en un archivo de pruebas separado de las antiguas. El algoritmo conserva sus penalizaciones, criterios y 15 % de desvío. Su preparación recalcula las medianas sobre el grafo de cada ensayo mediante la función existente.

| Cobertura y caso | Corta antes → después | Histórica antes → después | LightGBM antes → después |
|---|---|---|---|
| Ambas, piloto | 3,255669 → **3,255669** | 3,306152 → **3,346387** | 3,297791 → **3,293076** |
| Ampliada, norte–sur | 8,837156 → **8,837156** | 9,538431 → **9,553508** | 9,538431 → **9,553508** |
| Ampliada, suroeste–noreste | 12,487147 → **12,758242** | 13,669665 → **14,030624** | 13,669665 → **13,753327** |
| Ampliada, centro–este | 5,220112 → **422** | 5,351498 → **422** | 5,351498 → **422** |
| Demo, centro–este | 5,220112 → **422** | 5,352630 → **422** | 5,352630 → **422** |
| Demo, norte–sur y suroeste–noreste | 422 → 422 | — | — |
| Ambas, oeste–este | 422 → 422 | — | — |

Centro–este pierde las tres alternativas porque el origen pasa de 194,45 a **333,80 m** del nodo disponible más próximo. Su antigua arista de acceso a la red atraviesa el portón OSM `9993809459`, sin permiso documentado, en la vía `1091123920`. Se apartó para revisión, no se declaró prohibición confirmada. No se elevó el límite de 300 m ni se buscó artificialmente otro recorrido para forzar el caso.

Oeste–este sigue fuera del límite, con **375,83 m** en ampliada y **1.900,15 m** en demo. En demo, norte–sur tiene ajustes de 2.557,86/344,03 m y suroeste–noreste de 1.844,46/2.229,79 m, iguales antes/después. Los otros casos aceptados conservan sus nodos ajustados. Las alternativas histórica y LightGBM de norte–sur coinciden; en suroeste–noreste dejan de coincidir. El piloto conserva tres geometrías distintas.

Todas las alternativas devueltas respetan el 15 % respecto a su nueva ruta corta y todos los ajustes aceptados son ≤300 m. Se mantiene la advertencia de que las distancias excluyen el acceso desde las coordenadas hasta los nodos. Los indicadores siguen siendo concentración estimada ponderada por longitud, no probabilidad individual de accidente.

## Revisión geográfica y móvil

Los 30 GeoJSON de antes/después son válidos. Los 3.525 pares consecutivos de posiciones de las rutas candidatas —incluidas repeticiones entre alternativas y coberturas— coinciden con su vía OSM. La verificación completa del grafo candidato también comprueba esa correspondencia para **todas** sus aristas. Las geometrías mantienen sentido, continuidad y orden longitud-latitud. No se modificó su forma.

Se renderizaron comparaciones en Leaflet con Playwright/Chromium y se inspeccionaron visualmente. Vías excluidas rojas, incertidumbres ocres y rutas de ambos escenarios superpuestas a los vectores de la descarga OSM. Las imágenes de React usaron también teselas de OpenStreetMap. Son pruebas de fidelidad a esa fuente, no verificación independiente en terreno.

- [Piloto antes/después](evidencias/acceso/capturas/osm-piloto.png).
- [Norte–sur](evidencias/acceso/capturas/osm-norte_sur.png).
- [Suroeste–noreste](evidencias/acceso/capturas/osm-suroeste_noreste.png).
- [Centro–este y pérdida de acceso evaluable](evidencias/acceso/capturas/osm-centro_este.png).
- [Sendero de Humboldt](evidencias/acceso/capturas/osm-humboldt.png).
- [Demo móvil](evidencias/acceso/capturas/demo-360x800.png) y [ampliada móvil](evidencias/acceso/capturas/ampliada-360x800.png).

Se generaron además capturas de ambas coberturas en **390×844, 430×932 y 1280×800**, en la misma carpeta. Son **13 PNG** en total, todos revisados. Se verificaron selección de las tres rutas, resaltado, apertura/cierre del panel, predicciones 25/99, atribución, ausencia de desbordamiento y mensaje 422 real para centro–este. No se necesitó cambiar el diseño del frontend. Fue emulación de tamaño/tacto con Chromium, sin Android/iPhone físico ni Safari.

**Sendero de Humboldt.** La vía `1075574449` tiene únicamente `highway=path` y su nombre, sin permiso explícito ni prohibición en la fuente. El tramo entre `4615266609` y `4615266656` sigue midiendo 766,47358 m y consta de dos posiciones consecutivas OSM. Se conserva, en ambos sentidos, como sendero sin restricción documentada en la ampliada; no existe en demo. No aparece en las rutas ensayadas. No se inventaron curvas ni se confirmó físicamente su transitabilidad. Se requiere comprobar trazado, señalización y condiciones de terreno antes de presentarlo como sendero verificado.

## Reproducir y ensayar sin activar

Desde la raíz, el generador usa exclusivamente archivos locales y rechaza carpetas de salida existentes. Los candidatos entregados están en `red_vial/acceso_peatonal_v1/`, excluidos de Git.

```powershell
.\backend\.venv\Scripts\python.exe scripts\auditar_acceso_peatonal.py
# Para una reproducción sin sobrescribir la entrega ya existente:
.\backend\.venv\Scripts\python.exe scripts\auditar_acceso_peatonal.py --salida red_vial/acceso_reproduccion --evidencia backend/evidencias/acceso_reproduccion
```

El informe conserva SHA-256 de los dos grafos originales, las dos capas, la descarga fuente y los candidatos. Se comprobó que las cinco entradas permanecieron intactas. Los CSV `.gz` contienen una fila por arista original con `(u,v,key)`, ID OSM, longitud, decisión y motivos. `etiquetas-osm.json.gz` conserva las etiquetas de las vías y nodos usados; `hallazgos-detallados.json` relaciona decisiones con los cambios de rutas.

Para el servidor de ensayo, en una terminal desde la raíz:

```powershell
.\backend\.venv\Scripts\python.exe scripts\ensayar_grafo_peatonal.py --cobertura demo
# Detener con Ctrl+C y ensayar el otro perfil:
.\backend\.venv\Scripts\python.exe scripts\ensayar_grafo_peatonal.py --cobertura ampliada
```

El servidor aislado escucha solamente en `127.0.0.1:8802`. Reutiliza los endpoints existentes y carga una copia validada una sola vez. No cambia `config.py`, `main.py` ni la selección normal por `RUTAINFORMADA_COBERTURA`. `/config` conserva los avisos de la aplicación actual, incluido el aviso general de restricciones de la ampliada. Volver al proceso habitual `python -m uvicorn main:app --reload` conserva los grafos originales; **esta vuelta no corrige sus problemas de acceso**.

En otra terminal:

```powershell
cd frontend
node scripts/ensayo-acceso.mjs
```

React queda en `http://127.0.0.1:5185` con proxy al servidor de ensayo, sin editar `.env`. Detener ambos procesos termina el ensayo. No se expuso la API a internet.

## Pruebas ejecutadas

| Ejecución | Aprobadas | Fallidas finales |
|---|---:|---:|
| Backend completo con demo predeterminada, incluye ambas copias | **290** | **0** |
| Contrato/regresión original ampliado, proceso separado | **14** | **0** |
| Playwright, copia demo, cuatro tamaños | **4** | **0** |
| Playwright, copia ampliada, cuatro tamaños | **4** | **0** |

Las 233 pruebas previas se conservaron. Se añadieron 43 casos unitarios de permisos/protección contra sobrescritura y cinco casos de recorridos por cada cobertura, más integridad total y pérdida de ajuste por cobertura (14 casos de integración nuevos). Las regresiones candidatas usan ±1 m y no sustituyen las referencias originales. La ejecución final completa tardó 62,86 s y quedó registrada en [pytest-demo.txt](evidencias/acceso/pytest-demo.txt). Los ensayos de Uvicorn arrancaron correctamente en ambos modos, con `/health`, `/config`, `/predicciones` y `/rutas` reales.

```powershell
cd backend
Remove-Item Env:RUTAINFORMADA_COBERTURA -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -v
$env:RUTAINFORMADA_COBERTURA = 'ampliada'
.\.venv\Scripts\python.exe -m pytest tests/test_cobertura.py -q
```

Para Playwright, desde `frontend` con los servidores de ensayo activos, seleccionar el perfil que está corriendo:

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH = Join-Path (Get-Location) '.playwright-browsers'
$env:PLAYWRIGHT_TEST_BASE_URL = 'http://127.0.0.1:5185'
$env:RUTAINFORMADA_ENSAYO = 'demo' # o ampliada tras reiniciar el servidor aislado
$env:PLAYWRIGHT_JSON_OUTPUT_FILE = "../backend/evidencias/acceso/playwright-$env:RUTAINFORMADA_ENSAYO.json"
node node_modules/@playwright/test/cli.js test e2e/acceso-peatonal.spec.ts --project=360x800 --project=390x844 --project=430x932 --project=1280x800 --reporter=list,json --output=test-results/acceso
node scripts/visualizar-acceso.mjs
```

El escenario nuevo se omite sin `RUTAINFORMADA_ENSAYO`, para no aplicar referencias filtradas a un servidor original. El primer intento de navegador falló por un selector de prueba («Ruta corta» en vez de «Ruta más corta»), que se corrigió; se interrumpió esa ejecución. La red restringida tampoco cargaba las teselas y la repetición autorizada las obtuvo. Las dos ejecuciones finales aprobaron completas. Persiste el aviso de deprecación Starlette/httpx anterior; la medición geográfica emitió además una advertencia de deprecación de la función Shapely de transformación. No se cambiaron dependencias.

## Archivos de esta fase y decisión pendiente

- Nuevos `scripts/auditar_acceso_peatonal.py` y `scripts/ensayar_grafo_peatonal.py`.
- Nuevos `backend/tests/unit/test_acceso_peatonal.py` y `backend/tests/test_grafos_peatonales.py`.
- Nuevos `frontend/e2e/acceso-peatonal.spec.ts`, `frontend/scripts/ensayo-acceso.mjs` y `frontend/scripts/visualizar-acceso.mjs`.
- Este informe, enlace desde `COBERTURAS.md` y evidencias bajo `backend/evidencias/acceso/`.
- Dos GraphML candidatos en `red_vial/acceso_peatonal_v1/`, **fuera de Git**.

Los archivos de código, pruebas, documentación y evidencias están preparados para revisar junto con los cambios previos todavía sin commit. No se añadieron al índice ni se ejecutaron commits/push. Los otros scripts y archivos sin seguimiento que ya existían no se modificaron.

**Pendiente antes de sustituir los grafos activos:** revisar la cuarentena conservadora y las nuevas desconexiones, confirmar accesos relevantes en campo o con señalización/documentación independiente y decidir la política para el sendero largo. Las copias no contienen vetos ni incertidumbres reconocidos por esta política, pero la ausencia de etiquetas no demuestra legalidad o transitabilidad en terreno. El acceso desde el punto solicitado al nodo ajustado sigue sin calcularse. Las relaciones de restricciones no están incluidas en la descarga utilizada y no se auditaron. Se espera la revisión del usuario antes de activar cualquier candidato.
