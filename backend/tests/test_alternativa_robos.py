"""La red y las cuadrículas de prueba son sintéticas e independientes de la capa local."""
import networkx as nx
import numpy as np
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shapely.geometry import LineString, box, mapping

import alternativa_robos as experimento
import api
import robos_historicos as capa
from config import ALPHAS

URL = "/robos-historicos/alternativa"
PUNTOS = {"origen": {"lon": -78.50, "lat": -.20}, "destino": {"lon": -78.49, "lat": -.20}}


def celda(poligono, alta):
    return {"geometry": mapping(poligono), "properties": {
        "nivel": capa.ALTA if alta else "otro", "densidad_registros_periodo_km2": 100 if alta else 10}}


@pytest.fixture
def escenario(monkeypatch, tmp_path):
    red = nx.MultiDiGraph(crs="EPSG:4326")
    a, b = (-78.50, -.20), (-78.49, -.20)
    for nodo, (x, y) in enumerate((a, b)):
        red.add_node(nodo, x=x, y=y)
    # Dos aristas paralelas. Solo el interior de una franja al inicio corta la directa.
    for clave, (longitud, coords) in enumerate(((1100, [a, b]),
                                                (1230, [a, (a[0], -.199), (b[0], -.199), b]))):
        datos = dict(longitud_m=longitud, score_historico=1, score_lightgbm=1,
                     geometry=LineString(coords))
        for i in range(len(ALPHAS)):
            datos.update({f"w_hist_{i}": longitud, f"w_ml_{i}": longitud})
        red.add_edge(0, 1, key=clave, **datos)
    zonas = [celda(box(-78.4995, -.201, -78.498, -.1995), True)]
    zonas.extend(celda(box(-78.48 + i, -.21, -78.479 + i, -.20), True) for i in range(4))
    # Cobertura conocida de ambas calles, salvo el rectángulo de concentración alta.
    cobertura = box(-78.51, -.21, -78.48, -.19).difference(box(-78.4995, -.201, -78.498, -.1995))
    zonas.append(celda(cobertura, False))
    archivo = tmp_path / "capa.geojson"
    archivo.touch()
    monkeypatch.setattr(capa, "ARCHIVO", archivo)
    monkeypatch.setattr(capa, "leer_capa", lambda: {"features": zonas})
    monkeypatch.setattr(api, "RED", "peatonal_filtrada")
    monkeypatch.setattr(api, "COBERTURA", "demo")
    app = FastAPI()
    app.include_router(api.router)
    app.include_router(api.router_experimental)
    app.state.grafo = red
    return TestClient(app), red, archivo


@pytest.mark.parametrize("medida,esperado", [
    ([1150, 190, 98, 0, 1], True),
    ([1151, 180, 80, 0, 1], False),
    ([1050, 191, 80, 0, 1], False),
    ([1050, 180, 99, 0, 1], False),
    ([1050, 180, 80, 0.5, 0], False),
    ([1050, 180, 80, 0, 1.1], False),
])
def test_limites(medida, esperado):
    assert bool(experimento.aceptable(np.array([1000, 200, 100, 0, 1]), np.array(medida))) == esperado


def test_minimo_relativo_para_tramos_largos():
    assert not experimento.aceptable(np.array([2000, 1000, 100]), np.array([2100, 985, 80]))


def test_intersecciones_paralelas_cache_y_referencia(escenario):
    cliente, red, _ = escenario
    base = cliente.post("/rutas", json=PUNTOS).json()
    respuesta = cliente.post(URL, json=PUNTOS)
    assert respuesta.status_code == 200
    f = respuesta.json()["feature"]
    assert f["geometry"]["coordinates"][0][1] == [-78.50, -.199]
    m = f["properties"]["comparacion_robos"]
    assert 165 < m["altas_corta_m"] < 170  # El punto medio de la arista directa queda fuera.
    assert m["altas_m"] == 0 and m["ponderado"] < m["ponderado_corta"]
    assert experimento.obtener_preparacion(red) is experimento.obtener_preparacion(red)
    assert "indice_espacial" not in red[0][1][0]
    assert cliente.post("/rutas", json=PUNTOS).json() == base


def test_geometria_ya_disponible(escenario):
    cliente, red, _ = escenario
    red[0][1][1].update(w_hist_0=1, score_historico=0.5)
    assert cliente.post(URL, json=PUNTOS).json() == {"estado": "coincidente", "modalidad": "historica"}


@pytest.mark.parametrize("caso", ["sin_otro_camino", "desvio"])
def test_sin_alternativa(escenario, caso):
    cliente, red, _ = escenario
    if caso == "desvio":
        red[0][1][1]["longitud_m"] = 1300
    else:
        red.remove_edge(0, 1, 1)
    assert cliente.post(URL, json=PUNTOS).json() == {"estado": "sin_alternativa"}


@pytest.mark.parametrize("fallo", ["archivo", "calculo", "red_original"])
def test_fallo_opcional_no_impide_rutas(escenario, monkeypatch, fallo):
    cliente, _, archivo = escenario
    if fallo == "archivo":
        assert cliente.post(URL, json=PUNTOS).status_code == 200
        archivo.unlink()
    elif fallo == "red_original":
        monkeypatch.setattr(api, "RED", "original")
    else:
        monkeypatch.setattr(capa, "leer_capa", lambda: {"features": []})
    assert cliente.post(URL, json=PUNTOS).status_code == 503
    assert len(cliente.post("/rutas", json=PUNTOS).json()["features"]) == 3


def test_ajuste_y_desconexion(escenario):
    cliente, _, _ = escenario
    for puntos in ({"origen": PUNTOS["destino"], "destino": PUNTOS["origen"]},
                   {**PUNTOS, "origen": {"lat": 0, "lon": 0}}):
        assert cliente.post(URL, json=puntos).status_code == 422
