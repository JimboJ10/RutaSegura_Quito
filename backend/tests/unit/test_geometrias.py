import json

import pytest
from shapely.geometry import LineString, MultiLineString, Point, shape

from geojson import geometria_camino, partes_arista


A = (-78.500, -0.2)
B = (-78.499, -0.2)
C = (-78.498, -0.2)


@pytest.mark.parametrize("como_wkt", [False, True])
def test_corrige_orientacion_invertida_sin_mutar_el_grafo(grafo_base, como_wkt):
    geom = LineString([B, A])
    datos = grafo_base[1][2][0]
    datos["geometry"] = geom.wkt if como_wkt else geom
    original = datos["geometry"]
    resultado = geometria_camino(grafo_base, {"aristas": [(1, 2, datos)]})
    assert resultado == {"type": "MultiLineString", "coordinates": [[list(A), list(B)]]}
    assert datos["geometry"] is original
    assert shape(resultado).is_valid


def test_ordena_y_orienta_partes_de_una_misma_arista(grafo_base):
    datos = {"geometry": MultiLineString([[C, B], [B, A]])}
    resultado = partes_arista(grafo_base, 1, 3, datos)
    assert resultado == [[list(A), list(B)], [list(B), list(C)]]


def test_geometria_correcta_conserva_todas_sus_coordenadas(grafo_base):
    intermedio = (-78.4995, -0.1999)
    geom = LineString([A, intermedio, B])
    assert partes_arista(grafo_base, 1, 2, {"geometry": geom}) == [
        [list(A), list(intermedio), list(B)]
    ]


def test_sin_geometria_conserva_union_entre_nodos(grafo_base):
    resultado = geometria_camino(grafo_base, {
        "aristas": [(1, 2, grafo_base[1][2][0]), (2, 3, grafo_base[2][3][0])]
    })
    assert resultado["coordinates"] == [[list(A), list(B)], [list(B), list(C)]]
    json.dumps(resultado, allow_nan=False)


@pytest.mark.parametrize(
    "geom",
    [
        Point(A),
        LineString(),
        "WKT INVÁLIDO",
        LineString([(*A, 1), (*B, 1)]),
        LineString([A, (181, -0.2)]),
        LineString([A, (-78.499, float("inf"))]),
        LineString([A, A]),
        LineString([A, C]),
        LineString([B, C]),
        # Longitud/latitud intercambiadas: dentro del rango global pero sin
        # correspondencia con los nodos reales de la arista.
        LineString([(A[1], A[0]), (B[1], B[0])]),
        MultiLineString([[A, (-78.4998, -0.2)], [(-78.4992, -0.2), B]]),
    ],
)
def test_rechaza_geometria_invalida_sin_inventar_conectores(grafo_base, geom):
    with pytest.raises(ValueError, match="Geometría vial"):
        partes_arista(grafo_base, 1, 2, {"geometry": geom})


def test_rechaza_ruta_vacia(grafo_base):
    with pytest.raises(ValueError, match="Ruta sin aristas"):
        geometria_camino(grafo_base, {"aristas": []})


def test_rechaza_saltos_entre_aristas(grafo_base):
    with pytest.raises(ValueError, match="Ruta con segmentos discontinuos"):
        geometria_camino(grafo_base, {
            "aristas": [(1, 2, grafo_base[1][2][0]), (1, 2, grafo_base[1][2][0])]
        })
