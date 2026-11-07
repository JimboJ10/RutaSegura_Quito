"""Ensaya main:app real con ambas selecciones, en procesos separados por entorno."""
import csv
import gzip
import json
import os
import subprocess
import sys

import networkx as nx
import osmnx as ox
import pytest
from fastapi.testclient import TestClient

import api
import main
from config import RED, ROOT
from grafo import cargar_grafo


@pytest.mark.parametrize(("cobertura", "red", "esperado"), [
    (None, None, "acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml"),
    (None, "original", "quito_demo_con_predicciones.graphml"),
    ("demo", None, "acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml"),
    ("demo", "original", "quito_demo_con_predicciones.graphml"),
    ("demo", "peatonal_filtrada", "acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml"),
    ("ampliada", "original", "ampliacion/quito_peatonal_ampliada_con_predicciones.graphml"),
    ("ampliada", "peatonal_filtrada", None),
    ("ampliada", None, None),
    ("demo", "", None),
    ("demo", "otra", None),
])
def test_seleccion_explicita_sin_activar_ampliada(cobertura, red, esperado):
    env = os.environ.copy()
    env.pop("RUTAINFORMADA_COBERTURA", None)
    if cobertura is not None:
        env["RUTAINFORMADA_COBERTURA"] = cobertura
    env.pop("RUTAINFORMADA_RED", None)
    if red is not None:
        env["RUTAINFORMADA_RED"] = red
    p = subprocess.run([sys.executable, "-X", "utf8", "-c",
                        "import config; print(config.GRAFO); print(config.PREDICCIONES)"],
                       cwd=ROOT / "backend", env=env, capture_output=True, text=True, encoding="utf-8", timeout=15)
    if esperado is None:
        assert p.returncode != 0
        assert "RUTAINFORMADA_RED" in p.stderr
    else:
        assert p.returncode == 0, p.stderr
        assert p.stdout.splitlines()[0] == str(ROOT / "red_vial" / esperado)
        if cobertura == "demo":
            assert p.stdout.splitlines()[1] == str(ROOT / "resultados/predicciones_demo_junio2026.geojson")


def test_grafo_activo_conserva_todas_las_componentes(cliente):
    g = cliente.app.state.grafo
    esperado = (14686, 43248, 61) if RED == "peatonal_filtrada" else (14934, 44672, 1)
    assert (len(g), g.number_of_edges(), nx.number_strongly_connected_components(g)) == esperado
    assert nx.number_weakly_connected_components(g) == esperado[2]
    avisos = " ".join(cliente.get("/config").json()["advertencias"])
    assert ("demo peatonal filtrada" in avisos) == (RED == "peatonal_filtrada")


def test_aristas_activas_corresponden_al_registro_de_acceso(cliente, monkeypatch, solicitud_conocida):
    with gzip.open(ROOT / "backend/evidencias/acceso/demo-aristas.csv.gz", "rt", encoding="utf-8") as f:
        decisiones = {(int(r["u"]), int(r["v"]), int(r["key"])): r["estado"] for r in csv.DictReader(f)}
    g = cliente.app.state.grafo
    permitidas = {e for e, estado in decisiones.items() if estado not in ("revision", "restringida")}
    assert set(g.edges(keys=True)) == (permitidas if RED == "peatonal_filtrada" else set(decisiones))
    original = api.calcular_recorridos
    observadas = []

    def observar(*args):
        rutas = original(*args)
        for _, ruta in rutas:
            for u, v, datos in ruta["aristas"]:
                k = next(k for k, d in g[u][v].items() if d is datos)
                observadas.append((u, v, k))
        return rutas

    monkeypatch.setattr(api, "calcular_recorridos", observar)
    assert cliente.post("/rutas", json=solicitud_conocida).status_code == 200
    assert observadas
    assert all(g.has_edge(*e) for e in observadas)
    if RED == "peatonal_filtrada":
        assert set(observadas) <= permitidas


def solicitud(par):
    return {k: dict(zip(("lon", "lat"), par[k])) for k in ("origen", "destino")}


def test_centro_este_cambia_por_ajuste_y_no_recurre_al_original(cliente):
    datos = {"origen": {"lon": -78.516, "lat": -.199}, "destino": {"lon": -78.483, "lat": -.180}}
    response = cliente.post("/rutas", json=datos)
    if RED == "peatonal_filtrada":
        assert response.status_code == 422
        assert response.json() == {"detail": "Origen o destino demasiado lejos de la red con predicciones."}
        _, metros = ox.distance.nearest_nodes(cliente.app.state.grafo, X=-78.516, Y=-.199, return_dist=True)
        assert metros == pytest.approx(333.796186, abs=.001)
    else:
        assert response.status_code == 200


def test_entre_componentes_rechaza_y_dentro_de_una_isla_permite(cliente):
    pares = json.loads((ROOT / "backend/evidencias/validacion-cobertura/demo-pares.json").read_text(encoding="utf-8"))
    par = next(p for p in pares if p["id"] == "isla_01")
    response = cliente.post("/rutas", json=solicitud(par))
    g = cliente.app.state.grafo
    a, b = ox.distance.nearest_nodes(g, X=[par[k][0] for k in ("origen", "destino")],
                                    Y=[par[k][1] for k in ("origen", "destino")])
    if RED == "peatonal_filtrada":
        assert not nx.has_path(g, a, b)
        assert response.status_code == 422
        assert response.json() == {"detail": "No existe una ruta conectada."}
        assert len(nx.node_connected_component(g.to_undirected(), a)) == 109
    else:
        assert response.status_code == 200
    # El origen de la isla conserva conexiones internas: no se elimina el sector.
    vecino = next(n for n in g.successors(a) if n != a)
    dentro = {"origen": {"lon": g.nodes[a]["x"], "lat": g.nodes[a]["y"]},
              "destino": {"lon": g.nodes[vecino]["x"], "lat": g.nodes[vecino]["y"]}}
    respuesta = cliente.post("/rutas", json=dentro)
    assert respuesta.status_code == 200, respuesta.text
    assert len(respuesta.json()["features"]) == 3


def test_archivo_no_disponible_detiene_arranque_sin_fallback(tmp_path, monkeypatch):
    # Simula ausencia únicamente en memoria; no mueve ni borra GraphML reales.
    ausente = tmp_path / "quito_demo_peatonal_filtrado.graphml"
    monkeypatch.setattr(main, "cargar_grafo", lambda: cargar_grafo(ausente))
    with pytest.raises(RuntimeError, match="No existe el grafo"):
        with TestClient(main.app):
            pytest.fail("No debe arrancar usando una copia distinta de la seleccionada")
