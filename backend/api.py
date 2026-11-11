"""Endpoints existentes y traducción de errores al contrato HTTP."""

import logging
import math

import networkx as nx
import osmnx as ox
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from config import COBERTURA, CORS_ORIGINS, CRS_ESPERADO, DESVIO_MAX, MAX_AJUSTE_M, PERIODO, PROYECTO, RED, VERSION_API, ZONA_DEMO
from alternativa_robos import comparar, obtener_preparacion
from geojson import coleccion_geojson
from predicciones import PrediccionesNoDisponibles, cargar_predicciones
from rutas import calcular_recorridos
from schemas import SolicitudRuta


router = APIRouter()
router_experimental = APIRouter()
logger = logging.getLogger(__name__)


def _valores_json_finitos(valor):
    # El parser JSON admite NaN/Infinity; el error 422 también debe ser JSON válido.
    if isinstance(valor, float) and not math.isfinite(valor):
        return str(valor)
    if isinstance(valor, dict):
        return {clave: _valores_json_finitos(item) for clave, item in valor.items()}
    if isinstance(valor, list):
        return [_valores_json_finitos(item) for item in valor]
    return valor


async def error_validacion(request, exc):
    contenido = jsonable_encoder({"detail": exc.errors()})
    return JSONResponse(status_code=422, content=_valores_json_finitos(contenido))


async def error_interno(request, exc):
    logger.error(
        "Error interno en %s %s", request.method, request.url.path,
        exc_info=(type(exc), exc, exc.__traceback__),
    )
    respuesta = JSONResponse(
        status_code=500,
        content={"detail": "No se pudo procesar la solicitud por un error interno."},
    )
    # El manejador 500 se ejecuta fuera del middleware CORS de FastAPI.
    # Conservamos la misma lista explícita para que React pueda leer este error.
    origen = request.headers.get("origin")
    if origen in CORS_ORIGINS:
        respuesta.headers["Access-Control-Allow-Origin"] = origen
        respuesta.headers.add_vary_header("Origin")
    return respuesta


def obtener_grafo(request):
    G = getattr(request.app.state, "grafo", None)
    if G is None:
        raise HTTPException(status_code=503, detail="La red de rutas no está disponible.")
    return G


class RespuestaGeoJSON(JSONResponse):
    media_type = "application/geo+json"


def obtener_predicciones():
    try:
        return cargar_predicciones()
    except PrediccionesNoDisponibles as exc:
        logger.error("No se pudo cargar la capa de predicciones", exc_info=True)
        raise HTTPException(
            status_code=503,
            detail="Las predicciones de la demostración no están disponibles.",
        ) from exc


@router.get(
    "/predicciones", response_class=RespuestaGeoJSON,
    summary="Cuadrículas de predicción retrospectiva de junio de 2026",
    responses={503: {"description": "Archivo de predicciones ausente o inválido"}},
)
def predicciones():
    datos, _ = obtener_predicciones()
    return datos


@router.get(
    "/config", summary="Configuración pública de la demostración",
    responses={503: {"description": "No está disponible la cobertura de predicciones"}},
)
def configuracion_publica():
    _, bbox = obtener_predicciones()
    advertencias = [
        "Predicciones de junio de 2026: demostración retrospectiva, no en tiempo real.",
        "Los indicadores no representan probabilidades individuales de accidente ni garantizan mayor seguridad.",
        "Las cuadrículas muestran conteos mensuales estimados por celda de 1 km²; el recorte visual no prorratea esos conteos.",
        "Las distancias y el desvío se calculan entre nodos ajustados y excluyen el acceso desde las coordenadas solicitadas.",
    ]
    if RED == "peatonal_filtrada":
        advertencias.append(
            "MVP de la demo peatonal filtrada: excluye restricciones e incertidumbres de acceso documentadas. "
            "Hay sectores desconectados; no se garantiza la transitabilidad física ni el acceso hasta los nodos."
        )
    if COBERTURA == "ampliada":
        advertencias.append(
            "Cobertura ampliada experimental. Dentro del rectángulo hay puntos a más de 300 m de la red peatonal."
        )
        advertencias.append(
            "Algunas alternativas incluyen vías con acceso restringido en OpenStreetMap. "
            "Compruebe el acceso peatonal antes de seguir el recorrido."
        )
    return {
        "proyecto": PROYECTO,
        "version_api": VERSION_API,
        "zona_demo": ZONA_DEMO,
        "bbox": bbox,
        "periodo": PERIODO,
        "tipo": "demostracion_retrospectiva",
        "metodos": ["corta", "historica", "lightgbm"],
        "desvio_maximo_pct": int(DESVIO_MAX * 100),
        "distancia_maxima_ajuste_m": MAX_AJUSTE_M,
        "crs": CRS_ESPERADO,
        "advertencias": advertencias,
    }


@router.get("/health")
def health(request: Request):
    G = obtener_grafo(request)
    return {
        "estado": "ok",
        "proyecto": PROYECTO,
        "nodos": G.number_of_nodes(),
        "aristas": G.number_of_edges(),
        "periodo": PERIODO
    }


def ajustar_extremos(G, solicitud):
    a = solicitud.origen
    b = solicitud.destino

    inicio, ajuste_a = ox.distance.nearest_nodes(
        G, X=a.lon, Y=a.lat, return_dist=True
    )

    fin, ajuste_b = ox.distance.nearest_nodes(
        G, X=b.lon, Y=b.lat, return_dist=True
    )

    if max(ajuste_a, ajuste_b) > MAX_AJUSTE_M:
        raise HTTPException(
            status_code=422,
            detail=(
                "Origen o destino demasiado lejos "
                "de la red con predicciones."
            )
        )

    if inicio == fin:
        raise HTTPException(
            status_code=422,
            detail="Origen y destino coinciden en el mismo nodo."
        )

    return inicio, fin, ajuste_a, ajuste_b


@router.post("/rutas")
def calcular_rutas(solicitud: SolicitudRuta, request: Request):
    G = obtener_grafo(request)
    inicio, fin, ajuste_a, ajuste_b = ajustar_extremos(G, solicitud)
    try:
        rutas = calcular_recorridos(G, inicio, fin)
    except nx.NetworkXNoPath:
        raise HTTPException(
            status_code=422,
            detail="No existe una ruta conectada."
        )

    return coleccion_geojson(G, rutas, inicio, fin, ajuste_a, ajuste_b)


@router_experimental.post("/robos-historicos/alternativa", summary="Comparar la concentración histórica de robos (2019–2022)",
             responses={200: {"description": "Alternativa disponible, coincidente o sin alternativa útil"},
                        422: {"description": "Extremos inválidos, fuera de cobertura o desconectados"},
                        503: {"description": "Comparación experimental no disponible"}})
def alternativa_historica(solicitud: SolicitudRuta, request: Request):
    if (COBERTURA, RED) != ("demo", "peatonal_filtrada"):
        raise HTTPException(503, "La comparación experimental requiere la demo peatonal filtrada.")
    grafo = obtener_grafo(request)
    extremos = ajustar_extremos(grafo, solicitud)
    try:
        resultado = comparar(obtener_preparacion(grafo), *extremos)
    except HTTPException:
        raise
    except nx.NetworkXNoPath as exc:
        raise HTTPException(422, "No existe una ruta conectada.") from exc
    except Exception as exc:
        logger.exception("Comparación histórica de robos no disponible")
        raise HTTPException(503, "No se pudo evaluar la modalidad experimental.") from exc
    return JSONResponse(resultado, headers={"Cache-Control": "no-store"})

