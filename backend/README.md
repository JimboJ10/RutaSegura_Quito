# RutaInformada Quito — backend

**Decide tu camino con datos.**

Aplicación web experimental que permite comparar rutas peatonales en una zona del centro-norte de Quito utilizando información histórica de siniestros de tránsito e inteligencia artificial.

API experimental de comparación de rutas peatonales para STEMergent Hacks 2026. A partir de un origen y destino dentro de la zona demo de Quito, devuelve una ruta corta y dos alternativas basadas en indicadores históricos y LightGBM.

La demostración utiliza predicciones **retrospectivas de junio de 2026**. No ofrece predicciones actuales, probabilidades individuales de accidente ni una garantía de mayor seguridad.

El nombre público es **RutaInformada Quito**; la carpeta `RutaSegura_Quito` y la variable `RUTASEGURA_CORS_ORIGINS` conservan sus nombres técnicos. Solo cambia el texto de presentación `proyecto` en `/health` y `/config`, además del título de Swagger; claves, endpoints y formatos siguen iguales.

Este README cubre instalación, operación y pruebas. [FRONTEND_API.md](FRONTEND_API.md) describe el contrato HTTP, los campos, ejemplos completos y su uso con React + Vite + Leaflet. El frontend React + Vite + Leaflet está documentado en [su README](../frontend/README.md).

## Arquitectura y archivos

```text
RutaSegura_Quito/
├── backend/
│   ├── main.py                  # FastAPI, ciclo de vida, CORS y errores
│   ├── config.py                # Rutas de datos, constantes y orígenes CORS
│   ├── grafo.py                 # Carga, validación y preparación del grafo
│   ├── schemas.py               # Validación Pydantic de las coordenadas
│   ├── rutas.py                 # Algoritmo y evaluación de recorridos
│   ├── geojson.py               # Geometrías, orientación y respuesta de rutas
│   ├── predicciones.py          # Validación y caché del GeoJSON existente
│   ├── api.py                   # Los cuatro endpoints
│   ├── requirements.txt         # Dependencias directas de ejecución
│   ├── requirements-dev.txt     # Ejecución más pytest y cliente HTTP
│   ├── requirements-lock.txt    # Versiones exactas del entorno validado
│   ├── pytest.ini
│   ├── README.md
│   ├── FRONTEND_API.md
│   └── tests/
│       ├── conftest.py
│       ├── test_api.py
│       ├── test_ciclo_vida.py
│       ├── test_frontend_api.py
│       ├── test_regresion.py
│       └── unit/                # Grafos pequeños y archivos temporales
├── red_vial/                    # Excluida de Git
│   ├── quito_demo_con_predicciones.graphml
│   └── quito_demo_peatonal.graphml
├── resultados/                 # Excluida de Git
│   └── predicciones_demo_junio2026.geojson
└── datos_originales/            # Excluida de Git
```

FastAPI prepara el GraphML al iniciar y reutiliza el grafo por proceso. Los endpoints de rutas no descargan calles, entrenan modelos ni cargan archivos `.joblib`. `scikit-learn` se utiliza para localizar nodos cercanos en coordenadas geográficas.

El optimizador conserva los alphas `[0.25, 0.5, 1, 2, 4, 8, 16]`, las penalizaciones y los criterios validados. La ruta corta minimiza `longitud_m`; las alternativas solo se aceptan si mejoran su indicador y no superan el 15 % adicional. Se elige la arista paralela según el peso correspondiente. Si no hay mejora admisible, la modalidad conserva la ruta corta.

`/config` y `/predicciones` comparten una carga diferida con caché. Los archivos cargados correctamente se mantienen en memoria hasta reiniciar el proceso; los fallos de lectura no quedan cacheados. Cada nuevo proceso creado por `--reload` vuelve a inicializar sus recursos.

## Requisitos y entorno reproducible

Entorno comprobado: **Windows de 64 bits, Python 3.14.6, pip 26.1.2**. Para reproducir la validación, utiliza esa versión de Python y la misma arquitectura. No se ha certificado una instalación limpia en otros sistemas o versiones.

| Dependencia directa | Versión del entorno validado | Uso |
|---|---|---|
| FastAPI | 0.162.0 | API y OpenAPI |
| Uvicorn | 0.54.0 | Servidor ASGI y recarga |
| OSMnx | 2.1.1 | Lectura GraphML y ajuste a nodos |
| NetworkX | 3.7 | Caminos ponderados |
| NumPy | 2.5.4 | Escalas de los indicadores |
| Shapely | 2.2.0 | Geometrías |
| scikit-learn | 1.9.1 | Búsqueda geográfica del nodo cercano |
| pyproj | 3.8.0 | Comprobación de CRS |
| pytest / httpx | 9.2.0 / 0.28.1 | Pruebas |

`requirements-lock.txt` registra las **47 versiones instaladas**, incluidas las dependencias transitivas y de pruebas. Los otros dos archivos siguen expresando las dependencias directas. El lock no incluye Python, pip ni los datos geográficos, y no reemplaza una verificación de instalación limpia. Su correspondencia con el entorno existente se comprueba sin reinstalarlo.

### Instalación con PowerShell

Desde la raíz del repositorio:

```powershell
Set-Location .\backend

# Solo en una copia nueva que todavía no tenga entorno virtual:
if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe')) {
    py -3.14 -m venv .venv
}

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip check
```

Conserva el `.venv` existente si ya funciona. Antes de instalar, comprueba la versión de Python mostrada. La instalación de paquetes necesita acceso al índice de Python; servir el GraphML y el GeoJSON locales no descarga datos geográficos.

Opcionalmente activa el entorno con `.\.venv\Scripts\Activate.ps1`. Si PowerShell impide ejecutar ese script, usa directamente `.\.venv\Scripts\python.exe`; no hace falta cambiar la política global de ejecución. Si `python` abre Microsoft Store o no se encuentra, utiliza también esa ruta explícita.

## Archivos de datos que no están en Git

Una clonación del repositorio no incluye los datos. Obtén los archivos del **respaldo validado del equipo** o de su responsable y colócalos sin cambiar sus nombres:

| Archivo relativo a la raíz | Necesidad |
|---|---|
| `red_vial/quito_demo_con_predicciones.graphml` | Obligatorio para iniciar y calcular rutas |
| `resultados/predicciones_demo_junio2026.geojson` | Obligatorio para servir `/config` y `/predicciones` |
| `red_vial/quito_demo_peatonal.graphml` | Respaldo de la red original; no lo carga la API actual |

No hay un enlace público de descarga definido en este repositorio. Solicita la versión de la demostración de junio de 2026; no la sustituyas por una descarga reciente de OpenStreetMap ni por nuevas predicciones. Conserva los archivos existentes y no los sobrescribas si ya están presentes. Los datos originales, métricas y modelos pueden permanecer en sus carpetas, pero no se necesitan para ejecutar los endpoints actuales.

Compara los SHA-256 del respaldo antes de usarlo. Desde `backend`:

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '..\red_vial\quito_demo_con_predicciones.graphml'
Get-FileHash -Algorithm SHA256 -LiteralPath '..\resultados\predicciones_demo_junio2026.geojson'
```

Valores de referencia de los archivos usados en la regresión:

```text
quito_demo_con_predicciones.graphml
73402173e4fc22f27555f4270bb22a6d766118fa0d3c830614c0e6a79258409c

predicciones_demo_junio2026.geojson
1a3fef11f33ddcd5b2720b69b3ff0ccc5d4d2719d6e4fb11e862defee353a2d0
```

Un hash distinto requiere revisar qué versión se recibió; no se debe cambiar la referencia de las pruebas para aceptar otro resultado. Las carpetas de datos están excluidas mediante `.gitignore`. Su distribución pública requiere revisar su procedencia, licencia y estrategia de entrega; esta fase no publica archivos.

## Ejecución local y Swagger

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m uvicorn main:app --reload
```

Con el entorno activado, el comando equivalente se conserva:

```powershell
python -m uvicorn main:app --reload
```

- API local: [http://127.0.0.1:8000](http://127.0.0.1:8000).
- Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).
- Esquema OpenAPI: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json).
- Cierre: Ctrl+C en la terminal del servidor.

La escucha predeterminada es local. `--reload` es para desarrollo. Si falta el GraphML o no supera las validaciones, la API no inicia. Si solo falta el GeoJSON de predicciones, las rutas siguen disponibles y los dos endpoints nuevos responden 503.

## Endpoints y comprobación con PowerShell

| Método | Ruta | Resultado |
|---|---|---|
| GET | `/health` | Estado del grafo, número de nodos/aristas y periodo |
| GET | `/config` | Métodos, restricciones, bbox y advertencias públicas |
| GET | `/predicciones` | GeoJSON completo con las 25 cuadrículas |
| POST | `/rutas` | Tres modalidades, geometrías, indicadores y ajustes |

Con el servidor activo, abre otra terminal:

```powershell
$baseApi = 'http://127.0.0.1:8000'
Invoke-RestMethod "$baseApi/health" | ConvertTo-Json

$configApi = Invoke-RestMethod "$baseApi/config"
$configApi | ConvertTo-Json -Depth 6

$predicciones = Invoke-RestMethod "$baseApi/predicciones"
$predicciones.features.Count
$predicciones.features[0].properties | ConvertTo-Json

$solicitud = @{
    origen = @{ lat = -0.201; lon = -78.504 }
    destino = @{ lat = -0.184; lon = -78.486 }
} | ConvertTo-Json -Depth 4
$rutas = Invoke-RestMethod "$baseApi/rutas" -Method Post -ContentType 'application/json' -Body $solicitud
$rutas.features | ForEach-Object { $_.properties } |
    Format-Table id,distancia_km,desvio_pct,indice_historico,indice_lightgbm
```

Respuesta completa de `/health`:

```json
{
  "estado": "ok",
  "proyecto": "RutaInformada Quito",
  "nodos": 14934,
  "aristas": 44672,
  "periodo": "2026-06"
}
```

Extracto real de `/config`:

```json
{
  "periodo": "2026-06",
  "metodos": ["corta", "historica", "lightgbm"],
  "desvio_maximo_pct": 15,
  "distancia_maxima_ajuste_m": 300,
  "crs": "EPSG:4326",
  "bbox": [-78.51500015930877, -0.215000011004652, -78.478, -0.173]
}
```

`/predicciones` devuelve `application/geo+json`, una FeatureCollection con 25 features Polygon. Estas son las propiedades de su primera cuadrícula:

```json
{
  "anio": 2026,
  "mes": 6,
  "cx": 776,
  "cy": 9976,
  "pred_historico": 0.6728535353535353,
  "pred_lightgbm_v2": 1.1314621528110718
}
```

`/rutas` devuelve una FeatureCollection con tres geometrías MultiLineString. Para la solicitud anterior:

| id | distancia_km | desvio_pct | indice_historico | indice_lightgbm |
|---|---:|---:|---:|---:|
| corta | 3.2557 | 0.000 | 9.7757 | 8.5263 |
| historica | 3.3062 | 1.551 | 9.3968 | 8.6266 |
| lightgbm | 3.2978 | 1.294 | 9.6312 | 8.4705 |

Los ajustes del ejemplo son **104,7 m en origen y 76,2 m en destino**. Son distancias geográficas a los nodos, no itinerarios de acceso. Las distancias mostradas y el límite del 15 % excluyen esos accesos.

GeoJSON utiliza `[longitud, latitud]`; la solicitud utiliza campos `lat` y `lon`. El bbox sigue `[oeste, sur, este, norte]`. Los índices de ruta son sumas de `longitud_km × score`; no representan probabilidad individual ni accidentes esperados durante un trayecto. Consulta el contrato para las geometrías completas, metadatos y ejemplos de `fetch` y `L.geoJSON`.

Los errores usan `detail`: lista de errores de campos o cadena descriptiva. Se conservan 422 para solicitudes inválidas/sin ruta, 503 para datos no disponibles y 500 para errores internos registrados. Un preflight CORS no autorizado devuelve 400.

## Pruebas automatizadas

Desde `backend`, en una consola con los orígenes CORS locales predeterminados:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
.\.venv\Scripts\python.exe -m pip check
```

La suite contiene **222 casos**: integración con el GraphML real, regresión, carga única, grafos sintéticos, geometrías, validaciones, errores, CORS y predicciones. Las pruebas de archivos ausentes/corruptos utilizan datos temporales.

Verificación de cierre de la Fase 5: **222 aprobadas, 0 fallidas**, en 21,79 s. Uvicorn inició y se detuvo correctamente en escucha local; los cuatro endpoints y Swagger respondieron HTTP 200. Se comprobaron las 25 cuadrículas y los diez ejemplos JSON de ambos documentos contra respuestas reales. Si configuraste CORS para el teléfono, utiliza otra consola con los valores predeterminados para ejecutar la suite.

Referencias de distancia: **3.255669, 3.306152 y 3.297791 km**, con tolerancia absoluta de **±1 metro**. No se deben ajustar para hacer pasar un cambio. La API mantiene su redondeo a cuatro decimales.

Existe un aviso de deprecación de Starlette por el cliente `httpx`; no hace fallar la suite. La compatibilidad está comprobada con las versiones fijadas. Una actualización del cliente requiere verificar de nuevo las pruebas.

## CORS

Por defecto se autorizan `http://localhost:5173` y `http://127.0.0.1:5173`, GET/POST y Content-Type. OPTIONS se atiende automáticamente y no se habilitan credenciales.

`RUTASEGURA_CORS_ORIGINS` recibe orígenes explícitos separados por comas y **sustituye** la lista predeterminada. Cambiarla requiere reiniciar el backend. El backend no carga `.env` automáticamente. CORS controla la lectura desde el navegador, no autentica usuarios ni bloquea clientes como PowerShell.

## Prueba desde Android o iPhone en la misma Wi-Fi

Estos pasos se documentan para desarrollo local; no publican un servicio. El teléfono y la computadora deben estar en una red de confianza que permita comunicación entre dispositivos.

### 1. Identificar la IPv4 de la computadora

En PowerShell:

```powershell
ipconfig
```

Busca la dirección IPv4 del adaptador Wi-Fi conectado, no la de una VPN o adaptador virtual. También se puede consultar en Configuración de Windows → Red e Internet → Wi-Fi → propiedades de la conexión. [Referencia de ipconfig](https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/ipconfig).

### 2. Iniciar el backend para la red local

Desde `backend`, en la terminal del servidor:

```powershell
$ipPc = Read-Host 'IPv4 Wi-Fi de esta computadora'
$env:RUTASEGURA_CORS_ORIGINS = "http://localhost:5173,http://127.0.0.1:5173,http://${ipPc}:5173"
.\.venv\Scripts\python.exe -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

`0.0.0.0` indica las interfaces donde escucha Uvicorn; no es una dirección para escribir en el teléfono. Abre **`http://<IP_LOCAL_PC>:8000/health`**, sustituyendo el marcador por la IPv4 obtenida. En el teléfono, `localhost` y `127.0.0.1` se refieren al propio teléfono, no a la computadora. [Opciones de escucha de Uvicorn](https://uvicorn.dev/settings/#socket-binding).

Usa esta escucha solo durante pruebas en la red local. No configures reenvío de puertos del router, túneles ni exposición a internet. Al terminar, detén el servidor y vuelve al comando predeterminado de escucha local.

### 3. Preparar el futuro frontend Vite

En `frontend`, utiliza `.env.local` en la raíz de Vite. Para probar solo desde la computadora:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Para que la misma interfaz funcione desde la computadora y el teléfono, cambia el valor por:

```dotenv
VITE_API_BASE_URL=http://<IP_LOCAL_PC>:8000
```

Reemplaza el marcador; no lo copies literalmente. No se fija ninguna IP personal en el código. El cliente lee `import.meta.env.VITE_API_BASE_URL`, como muestra [FRONTEND_API.md](FRONTEND_API.md). Reinicia Vite cuando cambies `.env.local`; sus variables son cadenas visibles para el navegador y no deben contener secretos. [Documentación de Vite](https://vite.dev/guide/env-and-mode).

Desde `frontend`:

```powershell
npm run dev -- --host 0.0.0.0 --port 5173 --strictPort
```

Abre **`http://<IP_LOCAL_PC>:5173`** en Android/iPhone. `--strictPort` evita que Vite cambie silenciosamente de puerto y deje de coincidir con CORS. El origen autorizado es la URL de la página del frontend en la computadora; **no es la IP del teléfono ni el puerto 8000 de la API**. [Opciones de servidor Vite](https://vite.dev/config/server-options).

### 4. Firewall y diagnóstico

Windows puede bloquear conexiones entrantes aunque ambos dispositivos estén en la misma Wi-Fi. En una red privada de confianza, revisa las autorizaciones de Python y Node en Seguridad de Windows → Firewall y protección de red. Si un administrador necesita reglas específicas, limítalas a TCP 8000/5173, perfil Privado y subred local. No desactives el firewall ni habilites perfiles públicos para esta prueba. Las políticas del equipo pueden impedir cambiar reglas. [Configuración del firewall de Windows](https://learn.microsoft.com/en-us/windows/security/operating-system-security/network-security/windows-firewall/configure).

| Síntoma | Comprobación |
|---|---|
| Ni la computadora abre `/health` | Terminal de Uvicorn, archivo GraphML, puerto y entorno Python |
| La computadora responde pero el teléfono no | Escucha en 0.0.0.0, IPv4 correcta, firewall y aislamiento de clientes de la Wi-Fi |
| El teléfono abre `/health`, pero React no consulta | URL VITE_API_BASE_URL, origen CORS y reinicio de ambos servidores |
| Vite no inicia en 5173 | Otro proceso usa el puerto; resolverlo o ajustar puerto y CORS de forma explícita |
| `/predicciones` o `/config` devuelve 503 | Ubicación, formato y periodo del GeoJSON |
| La ubicación del navegador no funciona | Permisos y contexto seguro; la selección manual debe seguir disponible |

Una red de invitados puede impedir comunicación entre dispositivos aunque compartan el mismo nombre de Wi-Fi. Revisa también VPN y que el teléfono permanezca conectado a esa red.

Para esta demo HTTP local, sirve frontend y API por HTTP. Una página HTTPS que llama a una API HTTP puede quedar bloqueada por contenido mixto. La geolocalización del navegador requiere contexto seguro y permiso: no se debe depender de ella sobre HTTP con una IP local. Mantén selección manual; el uso de HTTPS local confiable queda para una decisión posterior. [Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API).

### 5. Comprobación manual pendiente en dispositivos

Todavía no se ha probado físicamente un frontend en Android o iPhone. Cuando exista:

1. Abrir `/health` desde el teléfono y después la interfaz Vite.
2. Verificar las 25 cuadrículas, el periodo y las advertencias.
3. Reproducir la ruta conocida y revisar las tres modalidades y sus ajustes.
4. Probar puntos coincidentes, fuera de cobertura y errores de red.
5. Revisar orientación vertical/horizontal, teclado, zoom táctil, paneles y red lenta.

No hace falta abrir el servicio a internet para completar estas pruebas.

## Límites del prototipo

- La cobertura corresponde al rectángulo demo publicado por `/config`, no a todo Quito; su bbox no garantiza conectividad.
- El ajuste es al nodo más cercano y admite como máximo 300 m. No se calcula el acceso peatonal hasta ese nodo.
- La búsqueda compara candidatos con siete penalizaciones; no garantiza el óptimo global del indicador sujeto al límite del 15 %.
- Las tres modalidades pueden coincidir. Menor indicador no implica una ruta objetivamente más segura.
- Las cuadrículas muestran conteos mensuales estimados por celda original de 1 km². Recortar su geometría para visualizarla no prorratea esos valores.
- Junio de 2026 es una demostración retrospectiva, sin actualización en tiempo real.
- Una arista sin geometría conserva la unión recta entre nodos del comportamiento original.
- La validación estructural no certifica precisión del modelo, accesibilidad física ni condiciones actuales de una calle.
- No hay autenticación ni límites de uso para un despliegue público; este flujo está preparado para desarrollo y demostración local.
- No se han certificado dispositivos reales ni una reinstalación limpia del entorno. La suite y el contrato se verifican en el entorno Windows existente.

Para Mobile First, prioriza selección manual clara, controles táctiles amplios, mapa con altura definida, panel de resultados plegable, estados de carga/error y advertencias visibles. Reutiliza las capas y evita calcular una ruta con cada movimiento del mapa. Las recomendaciones concretas y ejemplos de integración están en el contrato del frontend.

