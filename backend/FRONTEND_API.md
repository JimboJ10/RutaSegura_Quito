# Contrato de integración: RutaSegura Quito

API experimental para React y Leaflet. Los ejemplos de datos siguientes se obtuvieron del backend local; las predicciones corresponden exclusivamente a junio de 2026.

La instalación, arquitectura, archivos de datos y pruebas por Wi-Fi desde celulares se explican en [README.md](README.md). Este documento mantiene el contrato HTTP y la interpretación de sus datos.

## Inicio y configuración de acceso

Desde `backend`, con el entorno existente activado, sigue funcionando:

```powershell
python -m uvicorn main:app --reload
```

Sin activar el entorno se puede usar `.\.venv\Scripts\python.exe -m uvicorn main:app --reload`. Base local: `http://127.0.0.1:8000`. Swagger: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

CORS permite `http://localhost:5173` y `http://127.0.0.1:5173`, métodos GET/POST y la cabecera Content-Type. No se habilitan credenciales. OPTIONS preflight se atiende automáticamente. CORS regula la lectura desde navegadores; no es autenticación. Un GET de otro origen puede devolver 200 sin autorización CORS, mientras que su preflight devuelve 400. Véase [CORS de FastAPI](https://fastapi.tiangolo.com/tutorial/cors/).

Para otro despliegue, establece una lista explícita separada por comas **antes de iniciar** el proceso:

```powershell
$env:RUTASEGURA_CORS_ORIGINS = 'https://frontend.example,https://demo.example'
python -m uvicorn main:app --reload
```

La variable sustituye la lista local. Una cadena vacía deshabilita el acceso cruzado; los comodines, credenciales dentro de URLs y rutas se rechazan. Reinicia la API al cambiarla. No se carga un archivo `.env` automáticamente. El ejemplo de dominio debe sustituirse por el origen real.

## Endpoints

| Método y ruta | Entrada | Salida satisfactoria |
|---|---|---|
| GET `/health` | Sin cuerpo | Estado y tamaño del grafo, JSON |
| GET `/config` | Sin cuerpo | Configuración pública, JSON |
| GET `/predicciones` | Sin cuerpo | FeatureCollection, `application/geo+json` |
| POST `/rutas` | JSON con origen y destino | FeatureCollection con tres rutas, `application/json` |

### GET /health

Respuesta completa HTTP 200:

```json
{
  "estado": "ok",
  "proyecto": "RutaSegura Quito",
  "nodos": 14934,
  "aristas": 44672,
  "periodo": "2026-06"
}
```

`estado: ok` verifica la disponibilidad del grafo de rutas. No garantiza que el archivo independiente de predicciones esté disponible.

### GET /config

Respuesta completa HTTP 200:

```json
{
  "proyecto": "RutaSegura Quito",
  "version_api": "0.1.0",
  "zona_demo": "Zona de demostración de Quito",
  "bbox": [
    -78.51500015930877,
    -0.215000011004652,
    -78.478,
    -0.173
  ],
  "periodo": "2026-06",
  "tipo": "demostracion_retrospectiva",
  "metodos": [
    "corta",
    "historica",
    "lightgbm"
  ],
  "desvio_maximo_pct": 15,
  "distancia_maxima_ajuste_m": 300,
  "crs": "EPSG:4326",
  "advertencias": [
    "Predicciones de junio de 2026: demostración retrospectiva, no en tiempo real.",
    "Los indicadores no representan probabilidades individuales de accidente ni garantizan mayor seguridad.",
    "Las cuadrículas muestran conteos mensuales estimados por celda de 1 km²; el recorte visual no prorratea esos conteos.",
    "Las distancias y el desvío se calculan entre nodos ajustados y excluyen el acceso desde las coordenadas solicitadas."
  ]
}
```

`bbox` procede de las geometrías de predicciones y sigue `[oeste, sur, este, norte]`, en grados. Sirve para encuadrar el mapa, no garantiza conectividad entre cualquier par de puntos. No se exponen rutas de archivos ni configuración privada.

### GET /predicciones

La respuesta completa contiene 25 features. Este es el **primer feature real**, extraído de `respuesta.features[0]`:

```json
{
  "type": "Feature",
  "properties": {
    "anio": 2026,
    "mes": 6,
    "cx": 776,
    "cy": 9976,
    "pred_historico": 0.6728535353535353,
    "pred_lightgbm_v2": 1.1314621528110718
  },
  "geometry": {
    "type": "Polygon",
    "coordinates": [
      [
        [
          -78.51144271512392,
          -0.207890639066526
        ],
        [
          -78.51144158247574,
          -0.215000003930643
        ],
        [
          -78.515,
          -0.215
        ],
        [
          -78.51500009330917,
          -0.207891203417195
        ],
        [
          -78.51144271512392,
          -0.207890639066526
        ]
      ]
    ]
  }
}
```

Se conserva todo el GeoJSON original, incluido su miembro `crs` con `urn:ogc:def:crs:OGC:1.3:CRS84`. Las posiciones son WGS84 en orden longitud-latitud, compatibles con EPSG:4326. `cx` y `cy` identifican la cuadrícula; no son coordenadas para colocar marcadores.

Usa `pred_historico` para la capa histórica y `pred_lightgbm_v2` para la capa LightGBM. Son **conteos mensuales estimados de siniestros por cuadrícula de 1 km²**, no porcentajes. Los polígonos recortados para mostrar la zona demo mantienen el conteo de la celda original: no representan exclusivamente el área visible ni deben reinterpretarse como densidad sobre el recorte.

El archivo se valida y carga al primer GET de `/config` o `/predicciones`; ambos reutilizan una caché por proceso, también ante llamadas simultáneas. Para adoptar cambios de un archivo cargado correctamente hay que reiniciar el proceso. Los fallos de carga no se cachean.

Si el archivo falta, no se puede leer o contiene datos inválidos, ambos endpoints nuevos responden HTTP 503 sin revelar rutas locales. `/health` y `/rutas` siguen disponibles si su grafo está operativo.

### POST /rutas

Envía grados geográficos, con nombres `lat` y `lon`:

```json
{
  "origen": {
    "lat": -0.201,
    "lon": -78.504
  },
  "destino": {
    "lat": -0.184,
    "lon": -78.486
  }
}
```

La respuesta es una FeatureCollection. Cada elemento de `features` contiene `type: Feature`, `properties` y `geometry` de tipo MultiLineString. Estas son las propiedades completas obtenidas en el ejemplo:

```json
[
  {
    "id": "corta",
    "distancia_km": 3.2557,
    "desvio_pct": 0,
    "indice_historico": 9.7757,
    "indice_lightgbm": 8.5263
  },
  {
    "id": "historica",
    "distancia_km": 3.3062,
    "desvio_pct": 1.551,
    "indice_historico": 9.3968,
    "indice_lightgbm": 8.6266
  },
  {
    "id": "lightgbm",
    "distancia_km": 3.2978,
    "desvio_pct": 1.294,
    "indice_historico": 9.6312,
    "indice_lightgbm": 8.4705
  }
]
```

| Propiedad | Uso y unidad |
|---|---|
| `id` | `corta`, `historica` o `lightgbm`; sirve para elegir color y etiqueta |
| `distancia_km` | Longitud del recorrido en la red, kilómetros; cuatro decimales |
| `desvio_pct` | Distancia adicional frente a la ruta corta; máximo 15 %, tres decimales |
| `indice_historico` | Suma de `longitud_km × score_historico` |
| `indice_lightgbm` | Suma de `longitud_km × score_lightgbm` |

Los índices son concentración estimada ponderada por longitud, en puntuación × kilómetro. No son probabilidades personales ni conteos esperados de accidentes durante un trayecto. Las modalidades pueden compartir geometría si ninguna candidata mejora su indicador dentro del límite.

`metadata` completo de la misma respuesta:

```json
{
  "periodo": "2026-06",
  "tipo": "demostracion_retrospectiva",
  "desvio_maximo_pct": 15,
  "origen_ajustado": {
    "lat": -0.200826,
    "lon": -78.5030749,
    "distancia_ajuste_m": 104.7
  },
  "destino_ajustado": {
    "lat": -0.1844072,
    "lon": -78.4854486,
    "distancia_ajuste_m": 76.2
  },
  "advertencia": "Distancias calculadas entre nodos ajustados. No incluyen el acceso desde las coordenadas solicitadas. Los indicadores no representan probabilidad individual de accidente."
}
```

Conserva en React las coordenadas solicitadas, porque la respuesta actual devuelve las ajustadas. `distancia_ajuste_m` es la distancia geográfica al nodo elegido, en metros; no es un itinerario de acceso. El ejemplo ajusta origen 104,7 m y destino 76,2 m. La API rechaza ajustes mayores de 300 m.

Las distancias e índices de rutas excluyen esos accesos. El 15 % se aplica únicamente entre los mismos nodos ajustados. Si dibujas enlaces entre el punto solicitado y el nodo, identifícalos como ajustes y no como tramos calculados.

## Consumo desde React

Fragmentos de integración, sin crear componentes ni una aplicación frontend:

En la raíz del futuro proyecto Vite, configura `.env.local`. Para probar solo en la computadora:

```dotenv
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Para Android o iPhone en la misma Wi-Fi, sustituye el valor por `http://<IP_LOCAL_PC>:8000`, reemplazando el marcador por la IPv4 de la computadora. `localhost` o `127.0.0.1` en el teléfono apuntan al propio teléfono. Reinicia Vite después de cambiar la variable; en una compilación, el valor queda incorporado al construirla. Las variables `VITE_` son públicas y no deben contener secretos. Véase [variables de entorno de Vite](https://vite.dev/guide/env-and-mode).

```javascript
const API_BASE = import.meta.env.VITE_API_BASE_URL?.replace(/\/+$/, '');
if (!API_BASE) throw new Error('Falta configurar VITE_API_BASE_URL');

async function apiJson(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    credentials: 'omit',
    headers: { Accept: 'application/json, application/geo+json', ...options.headers },
  });
  const body = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = body?.detail;
    const message = Array.isArray(detail)
      ? detail.map(error => `${error.loc.join('.')}: ${error.msg}`).join('; ')
      : detail || `Error HTTP ${response.status}`;
    throw new Error(message);
  }
  return body;
}

const config = await apiJson('/config');
const cuadriculas = await apiJson('/predicciones');
const rutas = await apiJson('/rutas', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    origen: { lat: -0.201, lon: -78.504 },
    destino: { lat: -0.184, lon: -78.486 },
  }),
});
```

Captura los errores con `try/catch` y presenta `error.message` como texto. Un fallo de red o bloqueo CORS puede impedir que `fetch` entregue una respuesta HTTP: comprueba que el servidor esté activo y que el origen exacto del navegador figure en la lista.

En Wi-Fi, el origen que debe autorizar el backend es `http://<IP_LOCAL_PC>:5173`, porque allí se sirve el frontend; no es la IP del teléfono ni la URL del backend en el puerto 8000. Los pasos para escuchar en la red local y revisar el firewall están en el README.

## Geometrías y Leaflet

GeoJSON usa `[longitud, latitud]`. `L.geoJSON` hace la conversión; entrégale la colección sin invertir sus coordenadas. En cambio, `L.latLng`, los marcadores y `fitBounds` usan `[latitud, longitud]`. Los ejemplos utilizan la [API de Leaflet 1.9.4](https://leafletjs.com/reference-1.9.4.html#geojson).

Con `map` y `L` ya disponibles:

```javascript
const colores = { corta: '#374151', historica: '#2563eb', lightgbm: '#9333ea' };
L.geoJSON(rutas, {
  style: feature => ({ color: colores[feature.properties.id], weight: 5 }),
}).addTo(map);

const [oeste, sur, este, norte] = config.bbox;
map.fitBounds([[sur, oeste], [norte, este]]);

const campo = 'pred_lightgbm_v2'; // O 'pred_historico'.
const valores = cuadriculas.features.map(feature => feature.properties[campo]);
const minimo = Math.min(...valores);
const maximo = Math.max(...valores);
L.geoJSON(cuadriculas, {
  style: feature => {
    const valor = feature.properties[campo];
    const intensidad = maximo > minimo ? (valor - minimo) / (maximo - minimo) : 0.5;
    return { color: '#1d4ed8', weight: 1, fillColor: '#2563eb', fillOpacity: 0.2 + 0.6 * intensidad };
  },
}).addTo(map);
```

Esta capa colorea polígonos. Muestra una leyenda con el indicador elegido, sus valores mínimo/máximo y la unidad de conteos mensuales estimados por celda; la opacidad relativa no es una probabilidad. Mantén las advertencias visibles al cambiar de indicador.

## Recomendaciones para Mobile First

- Mantener una selección manual de origen/destino con confirmación explícita; mostrar los dos puntos solicitados y sus ajustes a la red.
- Diseñar controles táctiles de al menos 44–48 px, etiquetas legibles y un panel de resultados plegable que deje espacio al mapa. No depender exclusivamente del color para distinguir rutas.
- Dar altura explícita al contenedor del mapa. Considerar barras del navegador y áreas seguras del teléfono; ejecutar `map.invalidateSize()` cuando un cambio de panel u orientación altere su tamaño.
- Consultar `/config` y `/predicciones` al iniciar y reutilizar las capas. Calcular rutas al confirmar los puntos, no con cada movimiento del mapa; evitar que una respuesta antigua reemplace la solicitud más reciente.
- Mostrar estados de carga, errores y el periodo retrospectivo. Conservar las tres modalidades aunque sus geometrías coincidan.
- La geolocalización del navegador necesita un contexto seguro y permiso del usuario. Una página HTTP servida mediante la IP de la computadora no debe depender de ese acceso; mantener selección manual para la demo por Wi-Fi. Véase [Geolocation API](https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API).
- Antes de dar por validado el frontend, probar físicamente Android y iPhone, orientación vertical/horizontal, zoom táctil, teclado abierto, red lenta y recuperación de errores. Estas comprobaciones todavía no se han realizado: el frontend no existe en esta fase.

## Errores HTTP y mensajes

| Estado | Situación | Acción del frontend |
|---|---|---|
| 422 | Coordenadas inválidas, mismo nodo, ajuste excesivo o falta de camino | Mostrar `detail` y permitir corregir los puntos |
| 503 | Red no disponible o archivo de predicciones ausente/inválido | Mostrar indisponibilidad; no sustituir la capa por ceros |
| 500 | Error interno registrado por el backend | Mostrar el mensaje; no presentar rutas como si la operación hubiera funcionado |
| 400 en OPTIONS | Origen, método o cabeceras no autorizados por CORS | Revisar configuración de integración |

Ejemplo existente para extremos coincidentes:

```json
{ "detail": "Origen y destino coinciden en el mismo nodo." }
```

Para validaciones de campos, `detail` es una lista con `loc`, `msg` y `type`. Para errores de operación es una cadena. Los errores 422, 503 y 500 permiten lectura CORS únicamente desde los orígenes autorizados.

## Advertencias que deben mostrarse

- Demostración retrospectiva de **junio de 2026**, sin predicciones actuales ni en tiempo real.
- Indicadores estimados, sin probabilidad individual de accidente ni garantía de mayor seguridad.
- Conteos de la celda de 1 km² original, aunque su geometría se muestre recortada.
- Distancias de rutas entre nodos ajustados; accesos desde los puntos solicitados excluidos.

Usa `config.advertencias` y `rutas.metadata.advertencia` como textos de referencia. No cambies el significado de los indicadores al presentarlos.

## Verificación

Desde `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

La regresión conserva 3,255669 km, 3,306152 km y 3,297791 km como referencias, con tolerancia de ±1 metro. Los datos originales, GraphML y resultados no se modifican al servir estos endpoints.

