"""Distancias de referencia independientes del cálculo del backend."""

import pytest


@pytest.mark.parametrize(
    ("ruta_id", "distancia_esperada_km"),
    [
        ("corta", 3.255669),
        ("historica", 3.306152),
        ("lightgbm", 3.297791),
    ],
)
def test_distancia_del_caso_conocido_con_tolerancia_de_un_metro(
    ruta_id, distancia_esperada_km, rutas_por_id
):
    distancia_km = rutas_por_id[ruta_id]["properties"]["distancia_km"]
    assert distancia_km == pytest.approx(distancia_esperada_km, rel=0, abs=0.001)
