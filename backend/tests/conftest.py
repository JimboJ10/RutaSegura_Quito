"""Pruebas de integración con el GraphML local y la aplicación existente."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def cliente():
    # El contexto de TestClient inicia la aplicación y carga el grafo real.
    from main import app

    with TestClient(app, raise_server_exceptions=False) as client:
        yield client


@pytest.fixture(scope="session")
def solicitud_conocida():
    return {
        "origen": {"lat": -0.201, "lon": -78.504},
        "destino": {"lat": -0.184, "lon": -78.486},
    }


@pytest.fixture(scope="session")
def respuesta_rutas(cliente, solicitud_conocida):
    return cliente.post("/rutas", json=solicitud_conocida)


@pytest.fixture(scope="session")
def coleccion_rutas(respuesta_rutas):
    assert respuesta_rutas.status_code == 200, respuesta_rutas.text
    return respuesta_rutas.json()


@pytest.fixture(scope="session")
def rutas_por_id(coleccion_rutas):
    return {
        feature["properties"]["id"]: feature
        for feature in coleccion_rutas["features"]
    }
