# Validación final de cobertura peatonal

Informe cerrado el **5 de noviembre de 2026**, en `feature/ampliacion-cobertura-quito`. Se compararon los dos grafos originales con las dos copias de `red_vial/acceso_peatonal_v1/`. No se modificó ninguno de los cuatro GraphML, las predicciones, el modelo ni la configuración de FastAPI.

**Recomendación.** El candidato filtrado demo ofrece cobertura suficiente para un MVP limitado a su zona, con rechazo explícito de recorridos desconectados. Para ampliada, el candidato filtrado es la opción admisible para continuar los ensayos de permisos, pero **no recomiendo activar todavía una oferta general de cobertura de 77,55 km²**. En la muestra sólo resultan evaluables 52 de 100 pares, hay un rodeo nuevo de 6,367 km y dos alternativas utilizan el Sendero de Humboldt aún sin verificación física. Los originales sirven como comparación histórica, no como alternativa para evitar esos rechazos, porque siguen permitiendo vías restringidas.

Esta recomendación es un juicio técnico basado en la muestra y las restricciones documentadas. No existía un umbral de aceptación acordado ni esta auditoría certifica la transitabilidad en terreno. La decisión de activar sigue pendiente del usuario.

## Diseño de la prueba

- **100 pares distintos por cobertura**, 200 en total. Semilla fija **20261104** con `random.Random`. Cada extremo se distribuye por cuotas entre todas las cuadrículas, ordenadas por `(cx,cy)` y barajadas en ciclos. Cada una de las 25/99 celdas recibe puntos de origen y destino. Se extrae un punto uniforme dentro del polígono mediante rechazo dentro de su bbox.
- Las cuotas por celda difieren como máximo en uno. No se utiliza el grafo para elegir, descartar o recolocar puntos. No se eliminan ubicaciones alejadas de calles ni pares incómodos. Los puntos son idénticos para original y filtrado.
- Otros **10 pares por cobertura** van de las diez mayores componentes secundarias a la componente principal. Se escoge un nodo cercano al centro de cada componente y el nodo más próximo de la principal. Son pruebas dirigidas de desconexión, separadas del porcentaje de la muestra.
- Se repiten los **cinco casos conocidos** en cada cobertura. En total se comparan **230 pares**, con **460 peticiones reales a `POST /rutas` mediante TestClient**. Los casos conocidos pueden coincidir entre coberturas y no se incluyen en la estimación de 100 pares.
- Se carga cada grafo una vez en su aplicación de ensayo. Hay un calentamiento por grafo fuera de las cifras. Se alterna qué versión corre primero por par, en secuencia y sin cálculos de rutas paralelos. Se mide tiempo total de TestClient y tiempo del algoritmo por separado. El registro de aristas se hace en memoria sin modificar la función de selección ni los archivos de la API.
- Cada éxito comprueba las tres modalidades, indicadores finitos, distancia exacta, límite del 15 %, ajuste ≤300 m, geometría válida y continua, extremos correctos y ausencia de aristas excluidas en el candidato. Se cuentan geometrías geográficamente iguales con igualdad topológica de Shapely.

La muestra representa las **cuadrículas**, no población, demanda de viajes ni una distribución uniforme por superficie cuando los recortes tienen áreas distintas. Los porcentajes son descriptivos de estos puntos, no tasas garantizadas para toda Quito. Una celda predictiva no equivale a una celda completamente caminable. Se mantiene la distinción entre demostración retrospectiva de junio de 2026 y fuente vial OSM de noviembre.

## Conectividad y red aprovechable

Las longitudes siguientes cuentan aristas dirigidas y paralelas. «Principal» significa la mayor componente fuertemente conexa (SCC), dentro de la cual existe camino de ida y vuelta entre cualquier par de nodos. Las componentes menores conservan utilidad interna, aunque no comunican con la principal.

| Medida | Demo original → filtrada | Ampliada original → filtrada |
|---|---|---|
| Nodos | 14.934 → 14.686 | 31.270 → 30.693 |
| Aristas | 44.672 → 43.248 | 91.708 → 88.704 |
| Componentes débiles | 1 → 61 | 1 → 110 |
| Componentes fuertes | 1 → 61 | 1 → 110 |
| Nodos de la SCC principal | 14.934 → 14.381 | 31.270 → 30.153 |
| Longitud total dirigida, km | 1.642,916 → 1.554,962 | 3.717,735 → 3.519,750 |
| Longitud de la principal, km | 1.642,916 → 1.535,215 | 3.717,735 → 3.479,914 |
| Nodos conservados / nodos originales | 100 % → **98,34 %** | 100 % → **98,15 %** |
| Longitud conservada / longitud original | 100 % → **94,65 %** | 100 % → **94,67 %** |
| Nodos de la principal / nodos originales | 100 % → **96,30 %** | 100 % → **96,43 %** |
| Longitud de la principal / longitud original | 100 % → **93,44 %** | 100 % → **93,60 %** |
| Nodos de la principal / nodos filtrados | **97,92 %** | **98,24 %** |
| Longitud de la principal / longitud filtrada | **98,73 %** | **98,87 %** |

La fragmentación produce muchas componentes pequeñas, no 61/110 sectores de tamaño comparable. Fuera de la principal quedan 305 nodos conservados demo y 540 ampliados. Los nodos retirados por quedar aislados son 248 y 577, respectivamente. No se volvió a introducir ninguno.

## Sectores desconectados y prioridad de revisión

Los identificadores C corresponden al orden por tamaño en los archivos `*-conectividad.json`; pueden variar entre coberturas. Los nombres son referencias presentes en OSM, no límites oficiales de barrios. Coordenadas de los centros de componente en **longitud, latitud**.

| Sector | Cobertura | Nodos / longitud dirigida | Centro | Causa documentada en la frontera |
|---|---|---|---|---|
| C1, vía «Páramo» | Ambas | 109 / 4,742 km | -78,485655; -0,186283 | Portón `5039392605`, `access=delivery`; sin excepción peatonal general |
| C2, «Bicentenario (Ingreso)» | Ampliada | 23 / 2,321 km | -78,488632; -0,148257 | Barreras `11168766119` y `11168766120`, sin permiso documentado |
| C3, sector norte | Ampliada | 13 / 1,983 km | -78,490854; -0,143923 | Peajes `11895986246` y `11895986247`; autorizaciones para vehículos y dato `wheelchair=yes`, sin aclaración suficiente de tránsito peatonal general |
| C2 demo / C4 ampliada, sector sur | Ambas | 12 / 0,776 km | -78,493914; -0,212893 | Barreras `11133483951`, `11133483952`, `11234884554` |
| C4 demo, sector noroeste | Ambas, diferente ID | 9 / 1,401 km | -78,510059; -0,180269 | Portón `8318516831`, sin permiso |
| C7 ampliada, N32 / Av. Mariana de Jesus | Ampliada | 9 / 1,435 km | -78,515167; -0,178856 | Portón sin autorización documentada |
| C15 demo / C38 ampliada, Francisco Hernández Girón | Ambas | 3 nodos | -78,501797; -0,178322 | Portón `10004687292`; aparece en pérdidas de la muestra |

La prioridad no depende sólo del tamaño de una componente. **La barrera `266845282` debe revisarse con prioridad alta**, aunque sus dos lados siguen en la SCC principal: su exclusión produce el mayor rodeo observado. Está en `(-78,5145261; -0,1926394)`, etiquetada únicamente como `barrier=lift_gate`. También se priorizan el portón `9993809459` por el caso centro–este y las fuentes de las ocho pérdidas de la muestra.

Las pérdidas demo corresponden a C11 (4 nodos, referencias Juan Villalengua/Oe8A), C15 (3 nodos, dos pares), C1 (109 nodos) y C7 (6 nodos, cadena sin permiso). Las ampliadas corresponden a C38 (3 nodos), C74 (3 nodos, centro `(-78,4860921; -0,1671336)`) y C33 (4 nodos, centro `(-78,4819675; -0,1691795)`). Cada par, sus componentes y las restricciones de sus rutas anteriores figuran en [revision-detallada.json](evidencias/validacion-cobertura/revision-detallada.json).

Se exportaron [las 60 componentes secundarias demo](evidencias/validacion-cobertura/demo-componentes.geojson) y [las 109 ampliadas](evidencias/validacion-cobertura/ampliada-componentes.geojson). Cada geometría conserva centro, bbox, tamaño, nombres y fuentes de restricción en su frontera. Son datos EPSG:4326 para revisión cartográfica, sin conexiones nuevas.

## Las 622 / 1.302 aristas inciertas

Todas siguen excluidas. No se obtuvo nueva evidencia que permita habilitarlas. Se respetan las autorizaciones peatonales específicas de la auditoría anterior; no se declara prohibida una calle ordinaria únicamente por carecer de `foot=yes`.

Esta tabla cuenta **aristas únicas por motivo cuya decisión final es «revisión»**. Una arista puede tener varios motivos; las columnas no se suman para obtener el total. Se evita así contar como incertidumbre adicional una arista ya excluida por una prohibición confirmada.

| Motivo | Demo | Ampliada |
|---|---:|---:|
| Portón `gate` sin permiso | 392 | 766 |
| Barrera `lift_gate` sin permiso | 92 | 138 |
| Bloque `block` sin información suficiente | 50 | 158 |
| Barrera no especificada `yes` | 38 | 78 |
| Horario o cierre no evaluado | 24 | 24 |
| Acceso de clientes `customers` | 22 | 28 |
| Cadena sin permiso | 16 | 24 |
| `foot=destination` | 6 | 6 |
| Barrera giratoria `swing_gate` | 6 | 6 |
| Acceso con permiso `permit` | 2 | 22 |
| Acceso de entregas `delivery` | 2 | 2 |
| Acceso desconocido `unknown` | 2 | 2 |
| Peaje sin aclaración peatonal | 0 | 10 |
| Troncal sin autorización suficiente | 0 | 22 |
| Enlace troncal sin autorización suficiente | 0 | 8 |
| Camino de caballos sin aclaración peatonal | 0 | 38 |
| Escalera vertical sin aclaración peatonal | 0 | 8 |
| Baranda `handrail` sin aclaración | 0 | 2 |

Por relación topológica, sí se obtienen categorías excluyentes:

| Ubicación de las aristas inciertas | Demo | Ampliada |
|---|---:|---:|
| Entre nodos de la misma SCC conservada | 246 | 528 |
| Entre SCC distintas conservadas | 134 | 240 |
| Con algún extremo retirado por aislamiento | 242 | 534 |
| **Total** | **622** | **1.302** |

Las 246/528 aristas internas pueden afectar distancias aunque no separen componentes. El caso de la barrera `266845282` demuestra por qué no basta revisar únicamente los puentes entre componentes.

En las rutas originales de la muestra, **40 pares demo y 26 ampliados** usan alguna incertidumbre. Los portones afectan a 24/9 pares; las barreras de brazo a 8/5; los bloques a 5/5. Los horarios o cierres afectan a siete pares demo; las escaleras verticales a cuatro ampliados y los enlaces troncales a tres ampliados. Estos conteos se solapan. Los candidatos devuelven cero rutas sobre aristas clasificadas como inciertas.

Se calculó además una **cota analítica**, mediante un grafo de componentes, que nunca se usó para enrutar ni se guardó como red vial. Si todas las incertidumbres llegaran a autorizarse tras verificación, sin permitir ninguna prohibición confirmada, la principal podría alcanzar como máximo 14.775 nodos demo y 30.885 ampliados en ese modelo. Reuniría 51 de 61 SCC demo y 92 de 110 ampliadas, contando la principal, además de algunos nodos hoy aislados. Las otras 10/18 SCC no pueden reconectarse por incertidumbres únicamente.

La prioridad individual evalúa una fuente a la vez y sólo cuenta aristas sin otras incertidumbres pendientes. Hay 168 fuentes demo y 346 ampliadas con beneficio individual positivo sobre nodos alcanzables. Los beneficios de distintas fuentes **no son sumables**, porque pueden habilitar el mismo sector. Estas cifras priorizan trabajo de campo; no son autorización de acceso ni un resultado de reintegración.

## Resultado origen–destino

Sólo la muestra espacial de 100 pares por cobertura se usa en esta tabla.

| Resultado | Demo original | Demo filtrada | Ampliada original | Ampliada filtrada |
|---|---:|---:|---:|---:|
| Extremos a ≤300 m, de 200 | 200 | 200 | 152 | 152 |
| Pares con ambos extremos a ≤300 m | 100 | 100 | 55 | 55 |
| Pares evaluables | **100 (100 %)** | **95 (95 %)** | **55 (55 %)** | **52 (52 %)** |
| Fuera del límite de ajuste | 0 | 0 | 45 | 45 |
| Sin camino entre nodos ajustados | 0 | 5 | 0 | 3 |
| Mismo nodo | 0 | 0 | 0 | 0 |
| Errores técnicos | 0 | 0 | 0 | 0 |
| Pares aceptados con alguna ruta restringida | 29 | **0** | 17 | **0** |
| Pares aceptados con alguna ruta incierta | 40 | **0** | 26 | **0** |

El filtrado pierde cinco pares demo y tres ampliados por desconexión. No genera nuevos fallos de ajuste en esta muestra. En ampliada, el 45 % de pares fuera de cobertura **ya fallaba en el original**. Entre los 55 pares ampliados ajustables, el candidato resuelve 52, es decir **94,55 %**. No debe confundirse esa cifra condicionada con el 52 % de toda la muestra.

Los diez casos dirigidos de islas son evaluables en cada original y pasan a HTTP 422 por falta de camino en cada filtrado. Los veinte resultados son esperados y muestran pérdidas reales; no se ocultan dentro del porcentaje de la muestra ni se califican como errores de software.

### Modalidades y recorridos distintos

Cada respuesta aceptada contiene tres modalidades, pero no necesariamente tres geometrías:

| Geometrías diferentes por par | Demo original | Demo filtrada | Ampliada original | Ampliada filtrada |
|---|---:|---:|---:|---:|
| Una | 24 | 22 | 9 | 8 |
| Dos | 42 | 38 | 30 | 29 |
| Tres | 34 | 35 | 16 | 15 |

En los candidatos sólo **50 de los 147 pares aceptados de la muestra** ofrecen tres recorridos geográficamente diferentes. Las coincidencias son el comportamiento existente cuando no aparecen alternativas que mejoren el indicador bajo las reglas actuales.

## Distancias y tiempos

Se comparan únicamente los pares aceptados por ambas versiones: 95 demo y 52 ampliados. El cambio mediano de distancia es cero en las tres modalidades y ambas coberturas, pero hay diferencias importantes en la cola de la distribución.

| Modalidad | Demo: pares con cambio >1 m / aumento máximo | Ampliada: pares con cambio >1 m / aumento máximo |
|---|---|---|
| Corta | 38 / +495,818 m | 21 / **+6.367,436 m** |
| Histórica | 38 / +802,507 m | 26 / **+6.724,162 m** |
| LightGBM | 38 / +922,100 m | 23 / **+6.724,162 m** |

**Caso ampliado `muestra_071`.** Origen `(-78,49006175; -0,16212800)`, destino `(-78,51571851; -0,19336148)`. Los mismos nodos se ajustan a 50,82 y 126,29 m en ambas versiones. La corta cambia de **6,204145 a 12,571581 km (+102,63 %)**. Histórica y LightGBM pasan de 6,204145 a 12,928307 km. La ruta corta original atravesaba una única fuente excluida: la barrera sin permiso `266845282`. La existencia de un camino alternativo largo mantiene ambos extremos en la principal, pero empeora mucho el servicio.

**Caso demo `muestra_049`.** La corta pasa de 5,048907 a 5,544725 km. La fuente excluida en la corta original es `13389959013`, un portón con `locked=yes`, sin autorización peatonal aclarada. No se interpreta un cierre como permiso.

Los cinco mayores cambios por cobertura y sus causas se guardan en [revision-detallada.json](evidencias/validacion-cobertura/revision-detallada.json), con las [60 geometrías antes/después](evidencias/validacion-cobertura/mayores-desvios.geojson). No se cambiaron los puntos, las longitudes ni el algoritmo para reducir esas diferencias.

**El aumento respecto al grafo original no es el desvío del 15 %.** Ese límite se aplica a cada alternativa respecto a la ruta corta de su propio grafo. Se comprobó con distancias sin redondear en todas las respuestas. Los máximos de los candidatos fueron **14,9062 % demo y 14,9143 % ampliada**.

| Tiempo total por par, mediana en pares comunes | Original | Filtrado |
|---|---:|---:|
| Demo | 0,585 s | 0,542 s |
| Ampliada | 1,105 s | 1,112 s |

Entre todos los éxitos de cada versión, el percentil 95 fue 1,118 → 1,038 s en demo y 2,317 → 2,259 s en ampliada. Esos percentiles usan conjuntos de éxitos ligeramente diferentes. Son medidas locales de una ejecución secuencial, con calentamiento; no una prueba de carga ni una garantía de latencia. Los tiempos por cada petición, incluidos rechazos, se conservan. El tiempo total acumulado medido de peticiones fue 118,39 s demo y 160,74 s ampliada, excluyendo carga y análisis estructural.

## Casos problemáticos

**Centro–este.** Vuelve a confirmarse el cambio del ajuste de origen de 194,45 a **333,80 m**, con destino a 36,20 m. Se rechaza en ambos candidatos. La vía anterior atraviesa el portón incierto `9993809459`; su exclusión retira un nodo aislado y hace que el origen supere el umbral. No se subió el límite ni se eligió un nodo lejano para forzar el éxito. En demo, norte–sur y suroeste–noreste siguen fuera de alcance. Oeste–este sigue fuera por 375,83 m en ampliada y 1.900,15 m en demo.

Las distancias de los casos conocidos reproducen las referencias de la auditoría filtrada. Cada terna está en kilómetros, en orden **corta / histórica / LightGBM**. Las referencias originales se mantienen separadas.

| Caso | Cobertura | Original | Filtrada |
|---|---|---|---|
| Piloto | Ambas | 3,255669 / 3,306152 / 3,297791 | 3,255669 / 3,346387 / 3,293076 |
| Norte–sur | Demo | HTTP 422: ajuste | HTTP 422: ajuste |
| Norte–sur | Ampliada | 8,837156 / 9,538431 / 9,538431 | 8,837156 / 9,553508 / 9,553508 |
| Suroeste–noreste | Demo | HTTP 422: ajuste | HTTP 422: ajuste |
| Suroeste–noreste | Ampliada | 12,487147 / 13,669665 / 13,669665 | 12,758242 / 14,030624 / 13,753327 |
| Centro–este | Demo | 5,220112 / 5,352630 / 5,352630 | HTTP 422: ajuste |
| Centro–este | Ampliada | 5,220112 / 5,351498 / 5,351498 | HTTP 422: ajuste |
| Oeste–este | Ambas | HTTP 422: ajuste | HTTP 422: ajuste |

Las distancias excluyen el acceso entre el punto solicitado y el nodo ajustado. Un ajuste menor de 300 m mide proximidad geográfica; no demuestra que ese acceso sea caminable ni atraviese terreno permitido. Los indicadores siguen representando concentración estimada ponderada por longitud, no probabilidades individuales de accidente.

**Cinco corredores inicialmente restringidos.** Los cinco continúan ausentes de los candidatos. La tabla cuenta modalidades originales que los utilizan en los 115 casos por cobertura, incluyendo conocidos y pruebas dirigidas; un recorrido puede usar varias vías y las filas no son sumables.

| ID OSM | Usos originales demo / ampliada | Usos filtrados |
|---|---:|---:|
| 1059162235 | 7 / 1 | 0 / 0 |
| 149787548 | 10 / 2 | 0 / 0 |
| 219886408 | 1 / 2 | 0 / 0 |
| 431716070 | 1 / 2 | 0 / 0 |
| 1171326264 | 0 / 2 | 0 / 0 |

Se conserva su exclusión por `access=no` sin excepción peatonal; la autorización `bus/psv` no autoriza a caminar. El examen completo mantiene **802 aristas demo y 1.702 ampliadas con veto documentado**, además de las inciertas.

**Portones privados.** Dentro de las restricciones documentadas, se identifican 122 nodos de portón privado demo y 275 ampliados, que afectan a 250/558 aristas dirigidas. Se cuentan sólo `gate`, `lift_gate` y `swing_gate` privados sin excepción peatonal efectiva. Doce modalidades originales demo y diez ampliadas los usan en el conjunto completo; cero modalidades candidatas. Otros nodos `access=private` de distinto tipo se mantienen en el registro general y no se suman a este subconjunto.

**Nodos `foot=no`.** `4333688043`, `4333896851` y `9524819114` afectan a diez aristas dirigidas en cada red. Todas están excluidas. Ningún recorrido de esta muestra los utilizó, pero esa ausencia no justifica habilitarlos ni reduce la validez del veto.

**Sendero de Humboldt.** La limitación dejó de ser puramente hipotética para esta muestra: la histórica de `muestra_002` y de `muestra_038` usa la vía `1075574449` en el candidato ampliado. Conserva la recta de **766,47358 m** entre `4615266609` y `4615266656`. La fuente sólo aporta `highway=path` y su nombre, sin permiso explícito ni prohibición. No se declara ilegal por faltar `foot=yes`, pero tampoco se confirma físicamente el sendero. Su forma y transitabilidad requieren revisión independiente antes de presentarlo como itinerario verificado. No se dibujaron curvas ni se modificó el candidato.

## Pruebas y reproducción

**303 pruebas pytest aprobadas, cero fallidas**, incluidas las 290 previas y 13 nuevas. Las nuevas comprueban muestreo, cuotas, coordenadas dentro de polígonos, componentes fuertes frente a débiles, denominadores, ausencia de vetos en el análisis hipotético, clasificación de errores y coherencia de todas las peticiones guardadas con los archivos de entrada.

Además, las **460 peticiones de comparación** produjeron 332 respuestas HTTP 200 y 128 rechazos HTTP 422 esperados, con **cero errores técnicos**. Se verificaron 996 modalidades en los éxitos. Las negativas por ajuste/desconexión son resultados funcionales de la cobertura, no fallos de pytest. Todos los GeoJSON exportados son válidos.

No se repitieron las pruebas de navegador ni se modificó el frontend en esta fase: la API, el diseño y los cuatro grafos eran los ya verificados. Esta validación fue offline y no necesitó servidores, descargas de calles, instalaciones ni reentrenamiento.

Desde la raíz del proyecto:

```powershell
# Crear una nueva comparación; rechaza una carpeta existente.
.\backend\.venv\Scripts\python.exe scripts\validar_cobertura_peatonal.py --salida backend/evidencias/validacion-repetida
# La entrega existente puede comprobarse/reanudarse sin repetir peticiones guardadas.
.\backend\.venv\Scripts\python.exe scripts\validar_cobertura_peatonal.py --reanudar
# Derivar tablas/causas del registro, sin recalcular recorridos.
.\backend\.venv\Scripts\python.exe scripts\resumir_validacion_peatonal.py
cd backend
Remove-Item Env:RUTAINFORMADA_COBERTURA -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m pytest -v
```

La reanudación requiere que coincidan la semilla, el hash del código y los nueve archivos de entrada. Los registros se escriben después de cada petición para no perder trabajo completado. Reanudar sí recarga grafos y recalcula metadatos estructurales/calienta el proceso, pero omite las peticiones registradas. No debe mezclarse una ejecución nueva con la anterior para comparar tiempos de equipos diferentes.

Se verificaron los SHA-256 de los cuatro grafos, dos capas, dos registros de decisiones y las etiquetas OSM derivadas. Permanecen intactos. El log completo está en [pytest.txt](evidencias/validacion-cobertura/pytest.txt); sólo persiste el aviso anterior de deprecación Starlette/httpx.

## Entrega y selección propuesta

- **Demo:** proponer `red_vial/acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml`, tras autorización, con comunicación clara de islas desconectadas y HTTP 422. Conserva el 93,44 % de la longitud original en la principal y resuelve 95/100 pares espaciales sin usar las restricciones identificadas.
- **Ampliada:** conservar `red_vial/acceso_peatonal_v1/quito_ampliada_peatonal_filtrado.graphml` como candidato experimental. Antes de integración general, revisar el rodeo de `muestra_071`, Humboldt y las principales incertidumbres, y definir una presentación de cobertura real. El 77,55 km² describe polígonos predictivos, no servicio continuo. El original no resuelve ese déficit de cobertura y añade rutas restringidas.
- No recomiendo sustituir el candidato por sólo su SCC principal sin una nueva evaluación: cambiaría el ajuste de puntos y los rechazos ya medidos. Tampoco recomiendo restaurar aristas para mejorar el porcentaje sin evidencia de permiso.

Archivos nuevos de esta fase:

- [validar_cobertura_peatonal.py](../scripts/validar_cobertura_peatonal.py), ejecución reproducible de topología y peticiones.
- [resumir_validacion_peatonal.py](../scripts/resumir_validacion_peatonal.py), causas, tablas y geometrías derivadas.
- `backend/tests/unit/test_validacion_cobertura.py` y `backend/tests/test_validacion_cobertura_registrada.py`.
- Este informe y `backend/evidencias/validacion-cobertura/`, con JSON completos, GeoJSON y CSV [demo](evidencias/validacion-cobertura/demo-pares-comparados.csv) / [ampliada](evidencias/validacion-cobertura/ampliada-pares-comparados.csv).

Se añadió un enlace desde `ACCESO_PEATONAL.md`. Los cambios de fases anteriores presentes en el árbol de trabajo se conservaron. **FastAPI sigue con su configuración anterior. No se hizo commit, push ni reintegración de aristas. Se espera la revisión del usuario.**
