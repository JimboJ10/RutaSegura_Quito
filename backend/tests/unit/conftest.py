"""Datos sintéticos independientes de los GraphML de la demostración."""

import networkx as nx
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import main
from api import router
from grafo import preparar_grafo


@pytest.fixture
def grafo_base():
    G = nx.MultiDiGraph(crs="epsg:4326")
    for nodo, lon in [(1, -78.500), (2, -78.499), (3, -78.498)]:
        G.add_node(nodo, x=lon, y=-0.2)
    for u, v in [(1, 2), (2, 3)]:
        G.add_edge(u, v, key=0, longitud_m=100, score_historico=2, score_lightgbm=3)
    return G


@pytest.fixture
def grafo_preparado(grafo_base):
    return preparar_grafo(grafo_base)


@pytest.fixture
def solicitud_artificial():
    return {
        "origen": {"lat": -0.2, "lon": -78.500},
        "destino": {"lat": -0.2, "lon": -78.498},
    }


@pytest.fixture
def cliente_artificial(grafo_preparado, monkeypatch):
    # Otra app evita reemplazar el grafo de las pruebas de integración.
    monkeypatch.setattr(main, "cargar_grafo", lambda: grafo_preparado)
    app = FastAPI(lifespan=main.lifespan, exception_handlers=main.app.exception_handlers)
    app.include_router(router)
    with TestClient(app, raise_server_exceptions=False) as cliente:
        yield cliente
