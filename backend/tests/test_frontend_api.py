import json

import pytest
from shapely.geometry import shape

import api
from config import PREDICCIONES, VERSION_API
from predicciones import PrediccionesNoDisponibles


ORIGENES = ("http://localhost:5173", "http://127.0.0.1:5173")


@pytest.mark.parametrize("origen", ORIGENES)
@pytest.mark.parametrize("endpoint", ["/health", "/config", "/predicciones"])
def test_get_permitido_por_cors(cliente, origen, endpoint):
    respuesta = cliente.get(endpoint, headers={"Origin": origen})
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert "origin" in respuesta.headers["vary"].lower()
    assert "access-control-allow-credentials" not in respuesta.headers


@pytest.mark.parametrize("origen", ORIGENES)
def test_post_rutas_permitido_por_cors(cliente, solicitud_conocida, origen):
    respuesta = cliente.post("/rutas", json=solicitud_conocida, headers={"Origin": origen})
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert "access-control-allow-credentials" not in respuesta.headers


@pytest.mark.parametrize("origen", ORIGENES)
@pytest.mark.parametrize(("endpoint", "metodo"), [("/health", "GET"), ("/config", "GET"), ("/predicciones", "GET"), ("/rutas", "POST")])
def test_preflight_permitido(cliente, origen, endpoint, metodo):
    respuesta = cliente.options(endpoint, headers={
        "Origin": origen,
        "Access-Control-Request-Method": metodo,
        "Access-Control-Request-Headers": "content-type",
    })
    assert respuesta.status_code == 200
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert set(respuesta.headers["access-control-allow-methods"].split(", ")) == {"GET", "POST"}
    assert "content-type" in respuesta.headers["access-control-allow-headers"].lower()
    assert "access-control-allow-credentials" not in respuesta.headers


@pytest.mark.parametrize("origen", ["http://localhost:5174", "https://no-autorizado.example", "null"])
def test_origen_no_permitido_no_recibe_autorizacion_cors(cliente, origen):
    # CORS limita la lectura del navegador, no sustituye la autenticación.
    respuesta = cliente.get("/health", headers={"Origin": origen})
    assert respuesta.status_code == 200
    assert "access-control-allow-origin" not in respuesta.headers
    preflight = cliente.options("/rutas", headers={
        "Origin": origen, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "Content-Type",
    })
    assert preflight.status_code == 400
    assert "access-control-allow-origin" not in preflight.headers


@pytest.mark.parametrize(("metodo", "cabecera"), [("DELETE", "Content-Type"), ("POST", "Authorization")])
def test_preflight_rechaza_metodo_o_cabecera_no_habilitados(cliente, metodo, cabecera):
    respuesta = cliente.options("/rutas", headers={
        "Origin": ORIGENES[0], "Access-Control-Request-Method": metodo,
        "Access-Control-Request-Headers": cabecera,
    })
    assert respuesta.status_code == 400


def test_sin_origin_no_se_agregan_cabeceras_cors(cliente):
    assert "access-control-allow-origin" not in cliente.get("/health").headers


@pytest.mark.parametrize("origen", ORIGENES)
def test_error_422_es_legible_desde_react(cliente, origen):
    respuesta = cliente.post("/rutas", json={}, headers={"Origin": origen})
    assert respuesta.status_code == 422
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert "detail" in respuesta.json()


@pytest.mark.parametrize("origen", [*ORIGENES, "https://no-autorizado.example"])
def test_error_500_respeta_la_misma_lista_cors(cliente, solicitud_conocida, origen, monkeypatch):
    def fallo(*args):
        raise RuntimeError("fallo controlado para comprobar CORS")

    monkeypatch.setattr(api, "calcular_recorridos", fallo)
    respuesta = cliente.post("/rutas", json=solicitud_conocida, headers={"Origin": origen})
    assert respuesta.status_code == 500
    assert respuesta.headers.get("access-control-allow-origin") == (origen if origen in ORIGENES else None)
    assert "access-control-allow-credentials" not in respuesta.headers
    assert respuesta.json()["detail"] == "No se pudo procesar la solicitud por un error interno."


@pytest.mark.parametrize("origen", ORIGENES)
@pytest.mark.parametrize("endpoint", ["/config", "/predicciones"])
def test_error_503_de_predicciones_es_legible_desde_react(cliente, origen, endpoint, monkeypatch):
    def no_disponibles():
        raise PrediccionesNoDisponibles("archivo ausente de prueba")

    monkeypatch.setattr(api, "cargar_predicciones", no_disponibles)
    respuesta = cliente.get(endpoint, headers={"Origin": origen})
    assert respuesta.status_code == 503
    assert respuesta.headers["access-control-allow-origin"] == origen
    assert "detail" in respuesta.json()


def test_predicciones_conserva_el_geojson_completo(cliente):
    original = json.loads(PREDICCIONES.read_text(encoding="utf-8-sig"))
    respuesta = cliente.get("/predicciones")
    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"] == "application/geo+json"
    datos = respuesta.json()
    assert datos == original
    assert datos["type"] == "FeatureCollection"
    assert len(datos["features"]) == 25
    for feature in datos["features"]:
        assert shape(feature["geometry"]).is_valid
        assert set(feature["properties"]) >= {"pred_historico", "pred_lightgbm_v2"}
        assert (feature["properties"]["anio"], feature["properties"]["mes"]) == (2026, 6)
    json.dumps(datos, allow_nan=False)


def test_config_publica_coincide_con_la_cobertura_real(cliente):
    respuesta = cliente.get("/config")
    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["proyecto"] == "RutaInformada Quito"
    assert datos["version_api"] == VERSION_API
    assert datos["zona_demo"] == "Zona de demostración de Quito"
    assert datos["periodo"] == "2026-06"
    assert datos["tipo"] == "demostracion_retrospectiva"
    assert datos["metodos"] == ["corta", "historica", "lightgbm"]
    assert datos["desvio_maximo_pct"] == 15
    assert datos["distancia_maxima_ajuste_m"] == 300
    assert datos["crs"] == "EPSG:4326"
    predicciones = cliente.get("/predicciones").json()
    limites = [shape(f["geometry"]).bounds for f in predicciones["features"]]
    assert datos["bbox"] == [min(b[0] for b in limites), min(b[1] for b in limites),
                             max(b[2] for b in limites), max(b[3] for b in limites)]
    avisos = " ".join(datos["advertencias"])
    for texto in ["retrospectiva", "no en tiempo real", "probabilidades individuales", "recorte visual", "excluyen el acceso"]:
        assert texto in avisos
    assert "C:\\" not in respuesta.text
    assert "red_vial" not in respuesta.text
    assert "resultados/" not in respuesta.text


def test_openapi_conserva_endpoints_y_documenta_los_nuevos(cliente):
    paths = cliente.get("/openapi.json").json()["paths"]
    assert set(paths) == {"/health", "/rutas", "/config", "/predicciones"}
    assert "application/geo+json" in paths["/predicciones"]["get"]["responses"]["200"]["content"]
    assert "503" in paths["/config"]["get"]["responses"]
