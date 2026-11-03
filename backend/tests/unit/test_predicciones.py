from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
import json

import pytest

import api
import predicciones
from predicciones import PrediccionesNoDisponibles, leer_predicciones, validar_predicciones


@pytest.fixture
def cuadricula():
    return {
        "type": "FeatureCollection",
        "features": [{
            "type": "Feature",
            "properties": {"anio": 2026, "mes": 6, "pred_historico": 2.0, "pred_lightgbm_v2": 1.5},
            "geometry": {"type": "Polygon", "coordinates": [[[-78.5, -0.2], [-78.49, -0.2], [-78.49, -0.19], [-78.5, -0.19], [-78.5, -0.2]]]},
        }],
    }


def test_validacion_no_modifica_datos_y_calcula_bbox(cuadricula):
    original = deepcopy(cuadricula)
    assert validar_predicciones(cuadricula) == [-78.5, -0.2, -78.49, -0.19]
    assert cuadricula == original


@pytest.mark.parametrize("campo", ["pred_historico", "pred_lightgbm_v2"])
@pytest.mark.parametrize("valor", [None, -1, "texto", True, float("nan"), float("inf")])
def test_rechaza_indicadores_invalidos(cuadricula, campo, valor):
    cuadricula["features"][0]["properties"][campo] = valor
    with pytest.raises(ValueError, match=campo):
        validar_predicciones(cuadricula)


@pytest.mark.parametrize("campo", ["pred_historico", "pred_lightgbm_v2"])
def test_no_imputa_ceros_a_indicadores_ausentes(cuadricula, campo):
    del cuadricula["features"][0]["properties"][campo]
    with pytest.raises(ValueError, match=campo):
        validar_predicciones(cuadricula)
    assert campo not in cuadricula["features"][0]["properties"]


@pytest.mark.parametrize("defecto", ["tipo", "vacio", "periodo", "geometria", "anillo_abierto", "fuera_rango", "crs", "nan_extra"])
def test_archivo_invalido_se_rechaza(tmp_path, cuadricula, defecto):
    feature = cuadricula["features"][0]
    if defecto == "tipo": cuadricula["type"] = "Feature"
    elif defecto == "vacio": cuadricula["features"] = []
    elif defecto == "periodo": feature["properties"]["mes"] = 7
    elif defecto == "geometria": feature["geometry"] = {"type": "Point", "coordinates": [-78.5, -0.2]}
    elif defecto == "anillo_abierto": feature["geometry"]["coordinates"][0].pop()
    elif defecto == "fuera_rango": feature["geometry"]["coordinates"][0][1][0] = 181
    elif defecto == "crs": cuadricula["crs"] = {"type": "name", "properties": {"name": "EPSG:3857"}}
    elif defecto == "nan_extra": feature["properties"]["extra"] = float("nan")
    ruta = tmp_path / "invalido.geojson"
    ruta.write_text(json.dumps(cuadricula), encoding="utf-8")
    with pytest.raises(PrediccionesNoDisponibles):
        leer_predicciones(ruta)


@pytest.mark.parametrize("estado", ["ausente", "corrupto", "invalido"])
@pytest.mark.parametrize("endpoint", ["/predicciones", "/config"])
def test_archivo_no_disponible_devuelve_503_sin_romper_rutas(tmp_path, monkeypatch, cliente_artificial, solicitud_artificial, estado, endpoint):
    ruta = tmp_path / "predicciones.geojson"
    if estado == "corrupto": ruta.write_text("{json incompleto", encoding="utf-8")
    if estado == "invalido": ruta.write_text('{"type":"FeatureCollection","features":[]}', encoding="utf-8")
    monkeypatch.setattr(api, "cargar_predicciones", lambda: leer_predicciones(ruta))
    respuesta = cliente_artificial.get(endpoint)
    assert respuesta.status_code == 503
    assert respuesta.json() == {"detail": "Las predicciones de la demostración no están disponibles."}
    assert str(tmp_path) not in respuesta.text
    assert cliente_artificial.get("/health").status_code == 200
    assert cliente_artificial.post("/rutas", json=solicitud_artificial).status_code == 200


@pytest.fixture
def cache_temporal(tmp_path, monkeypatch):
    ruta = tmp_path / "cache.geojson"
    predicciones._predicciones_en_cache.cache_clear()
    monkeypatch.setattr(predicciones, "PREDICCIONES", ruta)
    try:
        yield ruta
    finally:
        predicciones._predicciones_en_cache.cache_clear()


def test_cache_lee_una_vez_incluso_con_peticiones_simultaneas(cache_temporal, cuadricula, monkeypatch):
    cache_temporal.write_text(json.dumps(cuadricula), encoding="utf-8")
    original = predicciones.leer_predicciones
    lecturas = []

    def contar(ruta):
        lecturas.append(ruta)
        return original(ruta)

    monkeypatch.setattr(predicciones, "leer_predicciones", contar)
    with ThreadPoolExecutor(max_workers=4) as pool:
        resultados = list(pool.map(lambda _: predicciones.cargar_predicciones(), range(8)))
    assert len(lecturas) == 1
    assert all(resultado is resultados[0] for resultado in resultados)
    assert resultados[0][0] == cuadricula


def test_fallo_de_carga_no_queda_cacheado(cache_temporal, cuadricula):
    with pytest.raises(PrediccionesNoDisponibles):
        predicciones.cargar_predicciones()
    cache_temporal.write_text(json.dumps(cuadricula), encoding="utf-8")
    assert predicciones.cargar_predicciones()[0] == cuadricula
