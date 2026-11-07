"""Contrato HTTP, GeoJSON y restricciones del caso de demostración."""

import json
import math

import pytest
from shapely.geometry import shape
from config import RED


RUTAS = ("corta", "historica", "lightgbm")


def test_health_responde_200_con_el_grafo_demo(cliente):
    respuesta = cliente.get("/health")

    assert respuesta.status_code == 200, respuesta.text
    assert respuesta.json() == {
        "estado": "ok",
        "proyecto": "RutaInformada Quito",
        "nodos": 14686 if RED == "peatonal_filtrada" else 14934,
        "aristas": 43248 if RED == "peatonal_filtrada" else 44672,
        "periodo": "2026-06",
    }


def test_rutas_responde_200_en_json(respuesta_rutas):
    assert respuesta_rutas.status_code == 200, respuesta_rutas.text
    assert respuesta_rutas.headers["content-type"].split(";")[0] == "application/json"


def test_feature_collection_contiene_las_tres_rutas(coleccion_rutas):
    assert coleccion_rutas["type"] == "FeatureCollection"
    features = coleccion_rutas["features"]
    assert len(features) == 3
    assert {feature["properties"]["id"] for feature in features} == set(RUTAS)
    # JSON estándar: no permite NaN ni Infinity en métricas o coordenadas.
    json.dumps(coleccion_rutas, allow_nan=False)


@pytest.mark.parametrize("ruta_id", RUTAS)
def test_geometria_geojson_valida_y_continua(ruta_id, rutas_por_id, coleccion_rutas):
    feature = rutas_por_id[ruta_id]
    assert feature["type"] == "Feature"
    geometria = feature["geometry"]
    assert geometria["type"] == "MultiLineString"
    partes = geometria["coordinates"]
    assert partes

    for parte in partes:
        assert len(parte) >= 2
        for posicion in parte:
            assert len(posicion) == 2
            lon, lat = posicion
            assert math.isfinite(lon) and math.isfinite(lat)
            assert -180 <= lon <= 180
            assert -90 <= lat <= 90

    linea = shape(geometria)
    assert not linea.is_empty
    assert linea.is_valid
    assert linea.length > 0

    # Las partes deben seguir el recorrido, sin saltos entre sus extremos.
    for anterior, siguiente in zip(partes, partes[1:]):
        assert anterior[-1] == pytest.approx(siguiente[0], rel=0, abs=1e-9)

    metadata = coleccion_rutas["metadata"]
    origen = metadata["origen_ajustado"]
    destino = metadata["destino_ajustado"]
    assert partes[0][0] == pytest.approx(
        [origen["lon"], origen["lat"]], rel=0, abs=1e-9
    )
    assert partes[-1][-1] == pytest.approx(
        [destino["lon"], destino["lat"]], rel=0, abs=1e-9
    )


def test_indices_finitos_y_no_negativos(rutas_por_id):
    for feature in rutas_por_id.values():
        propiedades = feature["properties"]
        for campo in ("indice_historico", "indice_lightgbm"):
            assert math.isfinite(propiedades[campo])
            assert propiedades[campo] >= 0


@pytest.mark.parametrize("ruta_id", RUTAS)
def test_desvio_no_supera_el_quince_por_ciento(ruta_id, rutas_por_id):
    corta = rutas_por_id["corta"]["properties"]
    ruta = rutas_por_id[ruta_id]["properties"]
    assert math.isfinite(ruta["distancia_km"])
    assert ruta["distancia_km"] > 0
    assert 0 <= ruta["desvio_pct"] <= 15

    # La API redondea cada distancia a 0.0001 km. El error máximo al
    # comparar alternativa <= corta * 1.15 es (1 + 1.15) * 0.00005 km.
    tolerancia_redondeo_km = 0.000108
    assert ruta["distancia_km"] <= corta["distancia_km"] * 1.15 + tolerancia_redondeo_km
    if ruta_id == "corta":
        assert ruta["desvio_pct"] == 0


def test_metadata_conserva_periodo_ajustes_y_advertencia(coleccion_rutas):
    metadata = coleccion_rutas["metadata"]
    assert metadata["periodo"] == "2026-06"
    assert metadata["tipo"] == "demostracion_retrospectiva"
    assert metadata["desvio_maximo_pct"] == 15
    for extremo in ("origen_ajustado", "destino_ajustado"):
        assert 0 <= metadata[extremo]["distancia_ajuste_m"] <= 300
    assert "No incluyen el acceso" in metadata["advertencia"]
    assert "no representan probabilidad individual" in metadata["advertencia"]
