import json

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import api
import main


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("lat", -91), ("lat", 91), ("lon", -181), ("lon", 181)]
    + [(campo, valor) for campo in ["lat", "lon"]
       for valor in ["texto", None, {}, [], True, False, "NaN", "Infinity", "-Infinity"]],
)
def test_coordenada_invalida_devuelve_422(cliente_artificial, solicitud_artificial, campo, valor):
    solicitud_artificial["origen"][campo] = valor
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 422, respuesta.text
    contenido = respuesta.json()
    assert contenido["detail"][0]["loc"] == ["body", "origen", campo]
    json.dumps(contenido, allow_nan=False)


@pytest.mark.parametrize("campo", ["lat", "lon"])
@pytest.mark.parametrize("token", ["NaN", "Infinity", "-Infinity"])
def test_no_finitos_en_json_crudo_no_producen_500(cliente_artificial, solicitud_artificial, campo, token):
    solicitud_artificial["origen"][campo] = "REEMPLAZAR"
    contenido = json.dumps(solicitud_artificial).replace('"REEMPLAZAR"', token)
    respuesta = cliente_artificial.post(
        "/rutas", content=contenido, headers={"Content-Type": "application/json"}
    )
    assert respuesta.status_code == 422, respuesta.text
    assert respuesta.json()["detail"][0]["type"] == "finite_number"
    json.dumps(respuesta.json(), allow_nan=False)


@pytest.mark.parametrize("extremo", ["origen", "destino"])
def test_solicitud_incompleta(cliente_artificial, solicitud_artificial, extremo):
    del solicitud_artificial[extremo]
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 422
    assert respuesta.json()["detail"][0]["loc"] == ["body", extremo]


@pytest.mark.parametrize("desplazamiento", [0, 1e-7])
def test_extremos_iguales_o_ajustados_al_mismo_nodo(cliente_artificial, solicitud_artificial, desplazamiento):
    solicitud_artificial["destino"] = {
        "lat": -0.2, "lon": -78.500 + desplazamiento
    }
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": "Origen y destino coinciden en el mismo nodo."}


@pytest.mark.parametrize("extremo", ["origen", "destino"])
def test_extremo_demasiado_lejano(cliente_artificial, solicitud_artificial, extremo):
    solicitud_artificial[extremo] = {"lat": 0, "lon": 0}
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": "Origen o destino demasiado lejos de la red con predicciones."}


def test_sin_camino_en_grafo_dirigido(cliente_artificial, solicitud_artificial):
    solicitud_artificial["origen"], solicitud_artificial["destino"] = (
        solicitud_artificial["destino"], solicitud_artificial["origen"]
    )
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 422
    assert respuesta.json() == {"detail": "No existe una ruta conectada."}


def test_sin_mejora_devuelve_tres_modalidades_de_la_ruta_corta(cliente_artificial, solicitud_artificial):
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 200
    features = respuesta.json()["features"]
    assert [f["properties"]["id"] for f in features] == ["corta", "historica", "lightgbm"]
    for feature in features:
        assert feature["geometry"] == features[0]["geometry"]
        assert feature["properties"]["distancia_km"] == 0.2
        assert feature["properties"]["desvio_pct"] == 0


@pytest.mark.parametrize(("distancia", "estado"), [(300, 200), (300.01, 422)])
def test_limite_de_ajuste(cliente_artificial, solicitud_artificial, monkeypatch, distancia, estado):
    resultados = iter([(1, distancia), (3, 0)])
    monkeypatch.setattr(api.ox.distance, "nearest_nodes", lambda *args, **kwargs: next(resultados))
    assert cliente_artificial.post("/rutas", json=solicitud_artificial).status_code == estado


@pytest.mark.parametrize("endpoint", ["/health", "/rutas"])
def test_red_no_disponible_devuelve_503(solicitud_artificial, endpoint):
    app = FastAPI(exception_handlers=main.app.exception_handlers)
    app.include_router(api.router)
    with TestClient(app) as cliente:
        respuesta = cliente.get(endpoint) if endpoint == "/health" else cliente.post(endpoint, json=solicitud_artificial)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": "La red de rutas no está disponible."}


def test_error_interno_se_registra_y_no_se_oculta(cliente_artificial, solicitud_artificial, monkeypatch, caplog):
    def fallo(*args):
        raise RuntimeError("fallo interno de prueba")

    monkeypatch.setattr(api, "calcular_recorridos", fallo)
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 500
    assert respuesta.json() == {"detail": "No se pudo procesar la solicitud por un error interno."}
    assert "fallo interno de prueba" in caplog.text
    assert "features" not in respuesta.json()


def test_datos_corruptos_en_memoria_no_producen_ruta_ficticia(cliente_artificial, grafo_preparado, solicitud_artificial):
    del grafo_preparado[1][2][0]["score_lightgbm"]
    respuesta = cliente_artificial.post("/rutas", json=solicitud_artificial)
    assert respuesta.status_code == 500
    assert "features" not in respuesta.json()
