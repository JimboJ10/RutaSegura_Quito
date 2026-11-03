"""Endpoints existentes y traducción de errores al contrato HTTP."""

import logging
import math

import networkx as nx
import osmnx as ox
from fastapi import APIRouter, HTTPException, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from config import MAX_AJUSTE_M, PERIODO
from geojson import coleccion_geojson
from rutas import calcular_recorridos
from schemas import SolicitudRuta


router = APIRouter()
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
    return JSONResponse(
        status_code=500,
        content={"detail": "No se pudo procesar la solicitud por un error interno."},
    )


def obtener_grafo(request):
    G = getattr(request.app.state, "grafo", None)
    if G is None:
        raise HTTPException(status_code=503, detail="La red de rutas no está disponible.")
    return G


@router.get("/health")
def health(request: Request):
    G = obtener_grafo(request)
    return {
        "estado": "ok",
        "proyecto": "RutaSegura Quito",
        "nodos": G.number_of_nodes(),
        "aristas": G.number_of_edges(),
        "periodo": PERIODO
    }


@router.post("/rutas")
def calcular_rutas(solicitud: SolicitudRuta, request: Request):
    G = obtener_grafo(request)
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

    try:
        rutas = calcular_recorridos(G, inicio, fin)
    except nx.NetworkXNoPath:
        raise HTTPException(
            status_code=422,
            detail="No existe una ruta conectada."
        )

    return coleccion_geojson(G, rutas, inicio, fin, ajuste_a, ajuste_b)

