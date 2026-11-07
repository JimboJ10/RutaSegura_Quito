# MVP con demo peatonal filtrada

Preparación del **6 de noviembre de 2026**, exclusivamente en `feature/ampliacion-cobertura-quito`. El MVP usa por defecto la demo de 19,13 km² con la red peatonal filtrada y las 25 cuadrículas retrospectivas de junio de 2026. No se ha publicado, hecho commit ni push. La ampliación de 77,55 km² continúa como experimental.

## Selección al iniciar

| `RUTAINFORMADA_COBERTURA` | `RUTAINFORMADA_RED` | Resultado |
|---|---|---|
| Sin definir | Sin definir | Demo filtrada, predeterminado del MVP |
| `demo` | Sin definir o `peatonal_filtrada` | Demo filtrada |
| Sin definir o `demo` | `original` | Demo original, únicamente para auditoría |
| `ampliada` | `original` | Ampliada original experimental, únicamente para auditoría |
| `ampliada` | Sin definir o `peatonal_filtrada` | Error de configuración; no inicia |
| Valor vacío o desconocido | Cualquier valor | Error si la cobertura es inválida |
| Cobertura válida | Valor vacío o desconocido | Error si la red es inválida |

Las variables se leen al iniciar el proceso, no por petición. Un recorrido rechazado **nunca** selecciona automáticamente el original. El original puede contener vías restringidas y no debe usarse para recomendar recorridos peatonales. Una variable heredada de una terminal anterior prevalece sobre el valor predeterminado: elimínala para iniciar el MVP.

## Ejecución local

Con las dependencias existentes y los datos verificados, desde la raíz del proyecto:

```powershell
.\backend\.venv\Scripts\python.exe scripts/distribuir_mvp.py verificar
if ($LASTEXITCODE -ne 0) { throw 'Revisar la entrega de datos antes de iniciar' }
Set-Location .\backend
Remove-Item Env:RUTAINFORMADA_COBERTURA,Env:RUTAINFORMADA_RED -ErrorAction SilentlyContinue
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Swagger: `http://127.0.0.1:8000/docs`. Con el entorno activado, `python -m uvicorn main:app --reload` sigue siendo válido desde `backend`.

En otra terminal, desde la raíz:

```powershell
Set-Location .\frontend
$env:VITE_API_BASE_URL = 'http://127.0.0.1:8000'
npm run dev
```

Abre `http://127.0.0.1:5173`. Para instalar en un equipo nuevo, sigue [README del backend](README.md#requisitos-y-entorno-reproducible) y [README del frontend](../frontend/README.md); conserva un entorno virtual existente si funciona. No se instalaron nuevas dependencias en esta fase. El backend no carga archivos `.env` automáticamente.

## Entrega a otro integrante

La ejecución del MVP necesita exactamente estos dos archivos de datos, relativos a la raíz del proyecto:

| Archivo | Bytes | SHA-256 |
|---|---:|---|
| `red_vial/acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml` | 24 937 786 | `d41c22b44b4a445ecf899633b52011d5002d272707be07bc3c67e59baceba824` |
| `resultados/predicciones_demo_junio2026.geojson` | 11 284 | `1a3fef11f33ddcd5b2720b69b3ff0ccc5d4d2719d6e4fb11e862defee353a2d0` |

Versión: **`demo-peatonal-v1-2026-11-04`**, periodo `2026-06`. La identidad está registrada en [datos_mvp.manifest.json](datos_mvp.manifest.json). El manifiesto y su verificador deben acompañar al código. No hacen falta los grafos originales, la ampliación, datasets históricos ni modelos `.joblib` para ejecutar el MVP.

Ya se preparó localmente `entregas/demo-peatonal-v1-2026-11-04.zip`: **2 625 523 bytes**, SHA-256 **`fb3add9a750a4726d84e09676cd04a8763f955cc9262e87a2f868c75b9d480e8`**. Contiene los dos datos y una copia del manifiesto; no contiene código ni dependencias. `entregas/`, `red_vial/` y `resultados/` están excluidos de Git. No se ha subido el paquete a ningún servicio.

Para preparar la misma entrega en otra copia que ya tenga los datos validados:

```powershell
.\backend\.venv\Scripts\python.exe scripts/distribuir_mvp.py empaquetar
```

El empaquetador valida los datos, fija el orden y las fechas de las entradas y **rechaza sobrescribir** un ZIP existente. En este equipo ya existe: no es necesario repetirlo. La prueba con archivos temporales comprueba que dos empaquetados producen el mismo hash.

Comparte el ZIP por un canal del equipo, por ejemplo una carpeta compartida o USB, junto con la versión y el hash. El código de esta fase aún está sin commit: una clonación remota por sí sola **todavía no incluye estos cambios**. Hasta autorizar su publicación, entrega también una copia del código revisado, sin `.venv`, `node_modules` ni datos duplicados. Después de publicar con autorización, el código y el manifiesto podrán obtenerse de Git y los datos del canal elegido.

En el equipo receptor:

1. Comprueba `Get-FileHash -Algorithm SHA256 <ruta-del-zip>` contra el hash comunicado por el equipo.
2. Extrae el ZIP en una carpeta nueva, conservando su estructura. No extraigas encima de datos existentes.
3. Desde la raíz del código revisado, valida la carpeta extraída contra el manifiesto del código:

```powershell
$carpetaEntrega = Read-Host 'Ruta de la carpeta nueva donde se extrajo el ZIP'
.\backend\.venv\Scripts\python.exe scripts/distribuir_mvp.py verificar --raiz $carpetaEntrega
if ($LASTEXITCODE -ne 0) { throw 'Entrega incompatible: no copiar ni iniciar' }
```

4. Copia los dos archivos a sus rutas relativas dentro del proyecto, creando las carpetas necesarias. Si una ruta ya existe, verifica primero su contenido; no la sobrescribas. La copia del manifiesto del ZIP es informativa: no reemplaces el manifiesto del código ni cambies hashes para aceptar archivos distintos.
5. Ejecuta de nuevo `scripts/distribuir_mvp.py verificar` sin `--raiz` y arranca con los comandos anteriores.

Las rutas se resuelven desde la ubicación del código, no desde una ruta personal. Se comprobó el ZIP extraído fuera del repositorio y el arranque de una copia temporal del backend con **solo esos dos datos**, sin originales ni modelos: cuatro endpoints HTTP 200. Se reutilizaron las dependencias instaladas; esto no certifica una instalación limpia en otro equipo.

Los cargadores comprueban existencia, versión, tamaño y SHA-256 además de las validaciones estructurales existentes. Un grafo inválido impide iniciar; un GeoJSON inválido conserva el error 503 de `/config` y `/predicciones`, sin inventar datos ni cambiar la red. Los recursos válidos se reutilizan por proceso; reinicia después de restaurar archivos. La suite histórica completa necesita datos adicionales de auditoría que no forman parte de este paquete mínimo.

## Verificación ejecutada

| Comprobación de esta fase | Aprobadas | Fallidas |
|---|---:|---:|
| Backend afectado, sin variables de selección | 180 | 0 |
| Auditoría explícita de demo original: health y tres regresiones | 4 | 0 |
| Integración HTTP desde frontend | 7 | 0 |
| Playwright Chromium, proyecto 390 × 844 | 7 | 0 |

Son **198 ejecuciones aprobadas**, sin fallos; las cuatro de auditoría ejercitan pruebas también incluidas en la selección de 180, pero con otra configuración. Las diez pruebas nuevas del manifiesto y empaquetado están incluidas en esas 180. Hay una advertencia de deprecación de Starlette/httpx ya existente; no impidió las pruebas.

Selección exacta del backend, desde `backend` y sin variables de selección:

```powershell
.\.venv\Scripts\python.exe -m pytest -v tests/test_api.py tests/test_ciclo_vida.py tests/test_cobertura.py tests/test_frontend_api.py tests/test_regresion.py tests/test_integracion_demo_filtrada.py tests/unit/test_datos_mvp.py tests/unit/test_grafo.py tests/unit/test_predicciones.py
```

Se verificó el arranque de Uvicorn sin variables de selección en `127.0.0.1:8802` y React/Vite en `127.0.0.1:5185` con proxy local. Los puertos aislados evitaron interferir con otros servidores. [Evidencias de esta fase](evidencias/mvp-predeterminado/): logs pytest/Vitest, informe Playwright JSON, respuestas HTTP, entrega mínima e integridad.

| Endpoint/caso | Resultado |
|---|---|
| `/health` | 200; 14 686 nodos y 43 248 aristas |
| `/config` | 200; demo, tres modalidades, 15 %, 300 m, junio de 2026 y avisos peatonales |
| `/predicciones` | 200; 25 cuadrículas GeoJSON |
| `/rutas`, piloto | 200; tres modalidades, geometrías e indicadores |
| Centro–este | 422; ajuste del origen 333,796 m, superior a 300 m |
| Entre componentes desconectadas | 422; `No existe una ruta conectada.` |
| Dentro de una componente aislada | 200; se conserva la cobertura local |

| Modalidad piloto | Original, solo auditoría (km) | Filtrada MVP (km) | API redondeada (km) |
|---|---:|---:|---:|
| Corta | 3,255669 | 3,255669 | 3,2557 |
| Histórica | 3,306152 | 3,346387 | 3,3464 |
| LightGBM | 3,297791 | 3,293076 | 3,2931 |

Regresiones con tolerancia de ±1 m. Desvíos filtrados publicados: 0 %, 2,786 % y 1,149 %. Se mantienen fórmulas, penalizaciones, selección y límite del 15 %. Las distancias excluyen los accesos desde las coordenadas solicitadas hasta los nodos; esos accesos no se calculan como caminos.

La prueba contrasta **todas** las aristas activas con el registro de auditoría y comprueba las aristas realmente usadas por el piloto: ninguna corresponde a las 802 restringidas ni a las 622 inciertas excluidas. Se conservan las 61 componentes, sin recortarlas a la mayor. Los SHA-256 de diez archivos protegidos —originales, filtrados, predicciones, registros y modelo— coinciden con la referencia anterior: [integridad.json](evidencias/mvp-predeterminado/integridad.json).

### Revisión visual

Se inspeccionaron las seis capturas nuevas de Chromium: [inicio](evidencias/mvp-predeterminado/capturas/390x844-01-inicial.png), [resultados](evidencias/mvp-predeterminado/capturas/390x844-02-resultados.png), [cuadrículas](evidencias/mvp-predeterminado/capturas/390x844-03-cuadriculas.png), [cobertura 422](evidencias/mvp-predeterminado/capturas/390x844-04-cobertura-422.png), [desconexión 422](evidencias/mvp-predeterminado/capturas/390x844-05-desconexion-422.png) y [modalidades coincidentes](evidencias/mvp-predeterminado/capturas/390x844-06-coincidentes.png).

Mapa, controles, leyendas, atribución, panel plegable y errores permanecen legibles y utilizables. El panel de resultados tiene desplazamiento interno: las tres tarjetas no necesitan caber simultáneamente en 844 px. Se conserva el texto «Tres modalidades de comparación» y el aviso de que pueden compartir recorrido; no se anuncian tres caminos diferentes. No se encontró un defecto visual nuevo que justificara modificar React o CSS.

Esta ejecución emula 390 × 844 e incluye el cambio de tamaño a 1280 × 844 y regreso. La validación anterior de 360 × 800, 390 × 844, 430 × 932, 768 × 1024, 1024 × 768, 1280 × 800 y 1920 × 1080 permanece documentada en [la integración previa](INTEGRACION_DEMO_FILTRADA.md). No se repitieron las 42 pruebas completas de navegador, las 37 unitarias ni la compilación de producción: no cambió el código de producción del frontend. Tampoco se repitió la suite completa del backend; se eligieron configuración, cargadores, endpoints, contrato y regresiones afectados.

## Prueba en teléfono físico

Preparado para una prueba supervisada en la misma Wi-Fi; **todavía no validado en Android o iPhone reales**. La emulación Chromium no certifica Safari/iOS, gestos reales ni la red del teléfono.

Obtén la IPv4 Wi-Fi de la computadora con `ipconfig`. Desde `backend`:

```powershell
Remove-Item Env:RUTAINFORMADA_COBERTURA,Env:RUTAINFORMADA_RED -ErrorAction SilentlyContinue
$ipPc = Read-Host 'IPv4 Wi-Fi de esta computadora'
$env:RUTASEGURA_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://${ipPc}:5173"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

En otra terminal, desde `frontend`:

```powershell
$ipPc = Read-Host 'La misma IPv4 de la computadora'
$env:VITE_API_BASE_URL = "http://${ipPc}:8000"
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

En el teléfono abre `http://<IP_PC>:8000/health` y después `http://<IP_PC>:5173`, sustituyendo el marcador. `localhost` en el teléfono apunta al teléfono. Si Windows bloquea la conexión, revisa Python/Node y los puertos 8000/5173 solo para red privada y subred local; no desactives el firewall. No uses reenvío de puertos ni exposición a internet. Nada de esto se activó automáticamente en esta fase.

Comprueba selección manual, piloto, cuadrículas, error de cobertura, panel con desplazamiento, orientación y zoom táctil. Se requiere conexión para las teselas; no hay Offline First. Al finalizar, detén ambos servidores. Hay más diagnóstico de CORS/Wi-Fi en [README](README.md#prueba-desde-android-o-iphone-en-la-misma-wi-fi).

## Archivos de esta fase y pendientes

- Configuración y carga: `config.py`, `api.py`, `grafo.py`, `predicciones.py`; nuevos `datos_mvp.py` y `datos_mvp.manifest.json`.
- Distribución: nuevo `../scripts/distribuir_mvp.py`, exclusión `entregas/` en `../.gitignore` y ZIP local fuera de Git.
- Pruebas: `tests/test_cobertura.py`, `tests/test_integracion_demo_filtrada.py`, nuevo `tests/unit/test_datos_mvp.py`; `../frontend/src/test/integration/backend.test.ts`, `../frontend/e2e/responsive.spec.ts`, `../frontend/e2e/cobertura.spec.ts`, `../frontend/e2e/demo-filtrada.spec.ts` y `../frontend/playwright.demo-filtrada.config.ts`.
- Documentación: este informe, `README.md`, `FRONTEND_API.md`, notas de estado en `COBERTURAS.md` e `INTEGRACION_DEMO_FILTRADA.md`, y `../frontend/README.md`. Evidencias nuevas en `evidencias/mvp-predeterminado/`.

El árbol de trabajo contiene además cambios de fases anteriores: esta lista distingue la preparación del MVP de todo lo que aparece en `git status`. No se modificaron `main.py`, el algoritmo, grafos, modelos ni indicadores en esta fase. No se cambió de rama ni se hizo commit o push.

La demo filtrada está preparada como predeterminada para el **MVP local revisable**. Persisten desconexiones y acceso incierto excluido; no es una garantía de transitabilidad física ni de seguridad. Los índices expresan concentración estimada ponderada por longitud, no probabilidades individuales. La ampliación continúa experimental. Quedan pendientes la prueba física en Android/iPhone, una instalación limpia en otro equipo y la revisión del equipo antes de compartir/publicar cambios. El Sendero de Humboldt conserva la limitación geométrica documentada en la auditoría; no se inventaron curvas ni se verificó físicamente.
