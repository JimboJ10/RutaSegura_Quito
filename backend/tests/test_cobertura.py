"""Contrato de la zona activa. Ejecutar también este archivo en un proceso con modo ampliada."""
import json
import os
import subprocess
import sys

import osmnx as ox
import pytest

from config import COBERTURA, RED, ROOT
from grafo import cargar_grafo
from predicciones import completar_fechas_ampliadas


@pytest.mark.parametrize(("valor", "grafo", "capa"), [
    (None, "acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml", "predicciones_demo_junio2026.geojson"),
    ("demo", "acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml", "predicciones_demo_junio2026.geojson"),
    ("ampliada", "ampliacion/quito_peatonal_ampliada_con_predicciones.graphml",
     "ampliacion/predicciones_99_celdas_junio2026.geojson"),
    ("otro", None, None),
    ("", None, None),
])
def test_seleccion_al_iniciar(valor, grafo, capa):
    entorno = os.environ.copy()
    entorno.pop("RUTAINFORMADA_RED", None)
    if valor == "ampliada":
        entorno["RUTAINFORMADA_RED"] = "original"  # Auditoría explícita, nunca fallback.
    if valor is None:
        entorno.pop("RUTAINFORMADA_COBERTURA", None)
    else:
        entorno["RUTAINFORMADA_COBERTURA"] = valor
    proceso = subprocess.run(
        [sys.executable, "-c", "import config; print(config.GRAFO); print(config.PREDICCIONES)"],
        cwd=ROOT / "backend", env=entorno, capture_output=True, text=True, timeout=15,
    )
    if grafo is None:
        assert proceso.returncode != 0
        assert "RUTAINFORMADA_COBERTURA" in proceso.stderr
        assert "'demo' o 'ampliada'" in proceso.stderr
    else:
        assert proceso.returncode == 0, proceso.stderr
        assert proceso.stdout.splitlines() == [str(ROOT / "red_vial" / grafo), str(ROOT / "resultados" / capa)]


def test_perfil_real_y_predicciones_sin_alteraciones(cliente):
    if COBERTURA == "ampliada":
        red, cantidad = (31270, 91708), 99
        bbox = [-78.54, -0.23, -78.47, -0.14]
        nombre = "Zona ampliada · Quito"
        archivo = "ampliacion/predicciones_99_celdas_junio2026.geojson"
    else:
        red, cantidad = ((14686, 43248) if RED == "peatonal_filtrada" else (14934, 44672)), 25
        bbox = [-78.51500015930877, -0.215000011004652, -78.478, -0.173]
        nombre = "Zona de demostración de Quito"
        archivo = "predicciones_demo_junio2026.geojson"
    health = cliente.get("/health").raise_for_status().json()
    assert (health["nodos"], health["aristas"]) == red
    config = cliente.get("/config").raise_for_status().json()
    assert config["zona_demo"] == nombre
    assert config["bbox"] == pytest.approx(bbox, rel=0, abs=1e-9)
    assert (config["periodo"], config["crs"]) == ("2026-06", "EPSG:4326")
    assert (config["desvio_maximo_pct"], config["distancia_maxima_ajuste_m"]) == (15, 300)
    assert config["metodos"] == ["corta", "historica", "lightgbm"]
    if COBERTURA == "ampliada":
        assert any("acceso restringido" in aviso for aviso in config["advertencias"])

    original = json.loads((ROOT / "resultados" / archivo).read_text(encoding="utf-8-sig"))
    if COBERTURA == "ampliada":
        for feature in original["features"]:
            feature["properties"].update(anio=2026, mes=6)
    respuesta = cliente.get("/predicciones").raise_for_status()
    assert respuesta.headers["content-type"] == "application/geo+json"
    assert len(respuesta.json()["features"]) == cantidad
    assert respuesta.json() == original
    assert cliente.app.state.grafo is cargar_grafo()


PILOTO = ((-78.504, -0.201), (-78.486, -0.184),
          (3.255669, 3.346387, 3.293076) if RED == "peatonal_filtrada" else (3.255669, 3.306152, 3.297791))
# Referencias congeladas de la auditoría independiente de noviembre de 2026.
CASOS = [pytest.param(*PILOTO, id="piloto")]
if COBERTURA == "ampliada":
    CASOS.extend([
        pytest.param((-78.498, -0.150), (-78.505, -0.218), (8.837156, 9.538431, 9.538431), id="norte_sur"),
        pytest.param((-78.530, -0.220), (-78.481, -0.153), (12.487147, 13.669665, 13.669665), id="suroeste_noreste"),
        pytest.param((-78.516, -0.199), (-78.483, -0.180), (5.220112, 5.351498, 5.351498), id="centro_este"),
    ])


@pytest.mark.parametrize(("origen", "destino", "referencias"), CASOS)
def test_distancias_y_sentido_entre_nodos(cliente, origen, destino, referencias):
    solicitud = {"origen": {"lon": origen[0], "lat": origen[1]}, "destino": {"lon": destino[0], "lat": destino[1]}}
    datos = cliente.post("/rutas", json=solicitud).raise_for_status().json()
    assert [f["properties"]["id"] for f in datos["features"]] == ["corta", "historica", "lightgbm"]
    a, b = (datos["metadata"][k] for k in ["origen_ajustado", "destino_ajustado"])
    for feature, km in zip(datos["features"], referencias, strict=True):
        props = feature["properties"]
        assert props["distancia_km"] == pytest.approx(km, abs=0.001, rel=0)
        assert 0 <= props["desvio_pct"] <= 15
        assert feature["geometry"]["type"] == "MultiLineString"
        partes = feature["geometry"]["coordinates"]
        assert partes[0][0] == [a["lon"], a["lat"]]
        assert partes[-1][-1] == [b["lon"], b["lat"]]
        assert all(p[-1] == q[0] for p, q in zip(partes, partes[1:]))


def test_oeste_este_respeta_ajuste(cliente):
    solicitud = {"origen": {"lon": -78.532, "lat": -0.186}, "destino": {"lon": -78.481, "lat": -0.188}}
    if COBERTURA == "ampliada":
        _, metros = ox.distance.nearest_nodes(cliente.app.state.grafo, X=-78.532, Y=-0.186, return_dist=True)
        assert metros == pytest.approx(375.83, abs=1)
    respuesta = cliente.post("/rutas", json=solicitud)
    assert respuesta.status_code == 422
    assert "demasiado lejos" in respuesta.json()["detail"]


@pytest.mark.parametrize("defecto", ["duplicada", "periodo", "cantidad"])
def test_rechaza_capa_ampliada_inconsistente(defecto):
    features = [{"properties": {"cx": i, "cy": 0, "periodo": "2026-06"}} for i in range(99)]
    if defecto == "duplicada":
        features[-1]["properties"]["cx"] = 0
    elif defecto == "periodo":
        features[-1]["properties"]["periodo"] = "2025-06"
    else:
        features.pop()
    with pytest.raises(ValueError):
        completar_fechas_ampliadas({"features": features})
