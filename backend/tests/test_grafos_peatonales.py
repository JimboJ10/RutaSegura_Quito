"""Regresiones candidatas separadas de las referencias originales, que se conservan."""
from pathlib import Path
import sys

import osmnx as ox
import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from auditar_acceso_peatonal import CASOS, GRAFOS, SALIDA, FUENTE, FuenteOSM, RANGO, ids_osm, CINCO
from ensayar_grafo_peatonal import crear_app

# Nuevas referencias del candidato; nunca reemplazan las distancias históricas.
REFERENCIAS = {
    "piloto": (3.255669, 3.346387, 3.293076),
    "norte_sur": (8.837156, 9.553508, 9.553508),
    "suroeste_noreste": (12.758242, 14.030624, 13.753327),
}


@pytest.fixture(scope="module")
def fuente_osm():
    import json
    return FuenteOSM(json.loads(FUENTE.read_text(encoding="utf-8")))


@pytest.fixture(scope="module", params=["demo", "ampliada"])
def ensayo(request):
    modo = request.param
    path = SALIDA / f"quito_{modo}_peatonal_filtrado.graphml"
    assert path.is_file(), "Genere primero las copias offline con scripts/auditar_acceso_peatonal.py"
    with TestClient(crear_app(path)) as client:
        yield modo, client


@pytest.mark.parametrize("caso", CASOS)
def test_rutas_candidatas_con_referencias_nuevas(ensayo, caso):
    modo, client = ensayo
    a, b = CASOS[caso]
    response = client.post("/rutas", json={"origen": {"lon": a[0], "lat": a[1]}, "destino": {"lon": b[0], "lat": b[1]}})
    permitido = caso in REFERENCIAS and (modo == "ampliada" or caso == "piloto")
    if not permitido:
        assert response.status_code == 422
        assert "demasiado lejos" in response.json()["detail"]
        return
    assert response.status_code == 200
    result = response.json()
    inicio, fin = [result["metadata"][k] for k in ("origen_ajustado", "destino_ajustado")]
    assert max(inicio["distancia_ajuste_m"], fin["distancia_ajuste_m"]) <= 300
    for f, referencia in zip(result["features"], REFERENCIAS[caso], strict=True):
        assert f["properties"]["distancia_km"] == pytest.approx(referencia, abs=.001, rel=0)
        assert 0 <= f["properties"]["desvio_pct"] <= 15
        partes = f["geometry"]["coordinates"]
        assert partes[0][0] == [inicio["lon"], inicio["lat"]]
        assert partes[-1][-1] == [fin["lon"], fin["lat"]]
        assert all(p[-1] == q[0] for p, q in zip(partes, partes[1:]))


def test_toda_la_copia_sin_vetos_y_sin_cambios_de_datos(ensayo, fuente_osm):
    modo, client = ensayo
    original = ox.load_graphml(GRAFOS[modo])
    g = client.app.state.grafo
    esperados = {"demo": (14686, 43248), "ampliada": (30693, 88704)}
    health = client.get("/health").raise_for_status().json()
    assert (health["nodos"], health["aristas"]) == esperados[modo]
    for u, v, k, d in g.edges(keys=True, data=True):
        assert original.has_edge(u, v, k)
        for campo in ("longitud_m", "score_historico", "score_lightgbm"):
            assert float(original[u][v][k][campo]) == d[campo]
        assert original[u][v][k].get("geometry") == d.get("geometry")
        assert not set(ids_osm(d)).intersection(CINCO)
        decision = fuente_osm.decidir(g, u, v, d)
        assert RANGO[decision["estado"]] < 2
        assert decision["pares_sin_fuente"] == 0


def test_punto_que_perdio_cobertura_no_se_fuerza(ensayo):
    _, client = ensayo
    _, distancia = ox.distance.nearest_nodes(client.app.state.grafo, X=-78.516, Y=-.199, return_dist=True)
    assert distancia == pytest.approx(333.796, abs=.001)
