"""Endpoints existentes y traducción de errores al contrato HTTP."""

import networkx as nx
import osmnx as ox
from fastapi import APIRouter, HTTPException, Request

from config import MAX_AJUSTE_M, PERIODO
from geojson import coleccion_geojson
from rutas import calcular_recorridos
from schemas import SolicitudRuta


router = APIRouter()


@router.get("/health")
def health(request: Request):
    G = request.app.state.grafo
    return {
        "estado": "ok",
        "proyecto": "RutaSegura Quito",
        "nodos": G.number_of_nodes(),
        "aristas": G.number_of_edges(),
        "periodo": PERIODO
    }


@router.post("/rutas")
def calcular_rutas(solicitud: SolicitudRuta, request: Request):
    G = request.app.state.grafo
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

