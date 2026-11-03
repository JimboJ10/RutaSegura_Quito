import pytest
from shapely.geometry import LineString

from geojson import coleccion_geojson
from grafo import preparar_grafo
from rutas import calcular_recorridos


def test_sin_alternativas_mejores_conserva_la_base(grafo_preparado):
    recorridos = calcular_recorridos(grafo_preparado, 1, 3)
    corta = recorridos[0][1]
    assert recorridos[1][1] is corta
    assert recorridos[2][1] is corta
    assert corta["distancia_m"] == 200


@pytest.mark.parametrize(("distancia", "aceptada"), [(230, True), (230.001, False), (250, False)])
def test_limite_del_quince_por_ciento_se_aplica_a_distancia_real(grafo_base, distancia, aceptada):
    grafo_base.add_edge(1, 3, longitud_m=distancia, score_historico=0, score_lightgbm=0)
    preparar_grafo(grafo_base)
    recorridos = calcular_recorridos(grafo_base, 1, 3)
    assert recorridos[0][1]["distancia_m"] == 200
    for _, alternativa in recorridos[1:]:
        assert alternativa["distancia_m"] == (distancia if aceptada else 200)
        if aceptada:
            assert alternativa["indice_hist"] == alternativa["indice_ml"] == 0


def test_aristas_paralelas_conservan_peso_distancia_indice_y_geometria(grafo_base):
    grafo_base[1][2][0].update(score_historico=9, score_lightgbm=9)
    punto_hist = (-78.4995, -0.1999)
    punto_ml = (-78.4995, -0.2001)
    for clave, longitud, historico, ml, punto in [
        (1, 110, 0.1, 9, punto_hist),
        (2, 112, 9, 0.1, punto_ml),
    ]:
        grafo_base.add_edge(
            1, 2, key=clave, longitud_m=longitud,
            score_historico=historico, score_lightgbm=ml,
            geometry=LineString([(-78.500, -0.2), punto, (-78.499, -0.2)]),
        )
    preparar_grafo(grafo_base)
    recorridos = calcular_recorridos(grafo_base, 1, 3)
    for (_, recorrido), clave, distancia in zip(recorridos, [0, 1, 2], [200, 210, 212]):
        assert recorrido["aristas"][0][2] is grafo_base[1][2][clave]
        assert recorrido["distancia_m"] == distancia
    assert recorridos[1][1]["indice_hist"] == pytest.approx(0.211)
    assert recorridos[2][1]["indice_ml"] == pytest.approx(0.3112)
    features = coleccion_geojson(grafo_base, recorridos, 1, 3, 0, 0)["features"]
    assert list(punto_hist) in features[1]["geometry"]["coordinates"][0]
    assert list(punto_ml) in features[2]["geometry"]["coordinates"][0]
    assert features[0]["geometry"] != features[1]["geometry"] != features[2]["geometry"]
