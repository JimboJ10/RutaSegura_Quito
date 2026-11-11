import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import robos_historicos as robos


@pytest.fixture
def cliente(tmp_path, monkeypatch):
    def celda(i):
        return {"type": "Feature",
                "geometry": {"type": "Polygon", "coordinates": [[[i, 0], [i+1, 0], [i+1, 1], [i, 1], [i, 0]]]},
                "properties": {"celda_id": str(i), "tipo": "robo_a_personas", "periodo": "2019-2022",
                               "numero_registros": None if i else 8, "rango_registros": "1-4" if i else None,
                               "area_km2": 1, "densidad_registros_periodo_km2": None if i else 8,
                               "nivel": "uno_a_cuatro_registros" if i else robos.ALTA}}
    archivo = tmp_path / "local.geojson"
    archivo.write_text(json.dumps({"type": "FeatureCollection", "features": [celda(i) for i in range(25)]}))
    monkeypatch.setattr(robos, "ARCHIVO", archivo)
    app = FastAPI()
    app.include_router(robos.router)
    return TestClient(app)


def test_celdas_agregadas_sin_revelar_conteos_pequenos(cliente):
    respuesta = cliente.get("/robos-historicos")
    assert respuesta.status_code == 200
    features = respuesta.json()["features"]
    assert len(features) == 25
    assert features[1]["properties"]["numero_registros"] is None
    assert features[1]["properties"]["rango_registros"] == "1-4"
    assert features[1]["properties"]["densidad_registros_periodo_km2"] is None


def test_cruce_interior_compartido_y_contacto_con_limite(cliente):
    linea = [[[-1, .5], [2, .5]]]
    respuesta = cliente.post("/robos-historicos/cruces", json={
        "corta": linea, "historica": [[[4, 4], [3, 3]], *linea], "lightgbm": [[[-1, 0], [2, 0]]]})
    assert respuesta.json() == {"corta": ["0"], "historica": ["0"], "lightgbm": []}


def test_coordenadas_invalidas(cliente):
    assert cliente.post("/robos-historicos/cruces", json={"corta": [[[0, 0], [0, 91]]]}).status_code == 422


@pytest.mark.parametrize("defecto", ["ausente", "ilegible", "privacidad"])
def test_archivo_opcional_no_disponible(cliente, defecto):
    if defecto == "ausente":
        robos.ARCHIVO.unlink()
    elif defecto == "ilegible":
        robos.ARCHIVO.write_text("!")
    else:
        datos = json.loads(robos.ARCHIVO.read_text())
        datos["features"][1]["properties"]["numero_registros"] = 2
        robos.ARCHIVO.write_text(json.dumps(datos))
    assert cliente.get("/robos-historicos").status_code == 503
    assert cliente.post("/robos-historicos/cruces", json={"corta": [[[0, 0], [1, 1]]]}).status_code == 503


def test_detalle_recorta_sin_unir_tramos_ni_incluir_el_borde(cliente):
    # Primer tramo sobre el borde, luego entra, sale y regresa por otro lado.
    peticion = {"corta": [[[-1, 0], [.25, 0], [.25, .5], [2, .5]],
                          [[2, .75], [.5, .75]]],
                "historica": [[[-1, 0], [2, 0]]],
                "lightgbm": [[[-1, -1], [0, 0]]]}
    datos = cliente.post("/robos-historicos/cruces?detalle=true", json=peticion).json()
    assert datos["corta"]["zonas"] == ["0"]
    from shapely.geometry import MultiLineString
    tramos = MultiLineString(datos["corta"]["tramos"])
    esperado = MultiLineString([[(.25, 0), (.25, .5), (1, .5)], [(1, .75), (.5, .75)]])
    assert tramos.equals(esperado)
    assert datos["historica"] == datos["lightgbm"] == {"zonas": [], "tramos": []}


def test_detalle_respeta_huecos_y_archivo_ausente(cliente):
    datos = json.loads(robos.ARCHIVO.read_text())
    datos["features"][0]["geometry"]["coordinates"].append(
        [[.25, .25], [.25, .75], [.75, .75], [.75, .25], [.25, .25]])
    robos.ARCHIVO.write_text(json.dumps(datos))
    peticion = {"corta": [[[0, .5], [1, .5]]]}
    endpoint = "/robos-historicos/cruces?detalle=true"
    from shapely.geometry import MultiLineString
    tramos = cliente.post(endpoint, json=peticion).json()["corta"]["tramos"]
    assert MultiLineString(tramos).equals(MultiLineString([[(0, .5), (.25, .5)], [(.75, .5), (1, .5)]]))
    robos.ARCHIVO.unlink()
    assert cliente.post(endpoint, json=peticion).status_code == 503
