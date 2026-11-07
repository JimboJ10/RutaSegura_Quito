"""Muestreo y análisis offline; no cambian el grafo que usa la aplicación."""
from pathlib import Path
import sys

import networkx as nx
import pytest
from shapely.geometry import Point, shape

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from validar_cobertura_peatonal import muestrear, estadisticas_red, analisis_topologico, estado_respuesta


def capa():
    return {"features": [{"properties": {"cx": i, "cy": 0},
        "geometry": {"type": "Polygon", "coordinates": [[[i, 0], [i+1, 0], [i+1, 1], [i, 1], [i, 0]]]}}
        for i in range(4)]}


def test_semilla_repetible_y_no_dependiente_del_grafo():
    a = muestrear(capa(), n=100, semilla=42)
    assert a == muestrear(capa(), n=100, semilla=42)
    assert a != muestrear(capa(), n=100, semilla=43)
    assert len({p["id"] for p in a}) == 100


def test_ambos_extremos_representan_todas_las_celdas_y_quedan_dentro():
    from collections import Counter
    data = capa()
    muestras = muestrear(data, n=101)
    for j, extremo in enumerate(("origen", "destino")):
        cuentas = Counter(p["celdas"][j][0] for p in muestras)
        assert set(cuentas) == {0, 1, 2, 3}
        assert max(cuentas.values()) - min(cuentas.values()) <= 1
        for par in muestras:
            i = par["celdas"][j][0]
            assert shape(data["features"][i]["geometry"]).covers(Point(par[extremo]))


def test_capa_vacia_no_produce_muestra_ficticia():
    with pytest.raises(ValueError):
        muestrear({"features": []})


def test_componentes_fuertes_y_debiles_y_denominadores():
    g = nx.MultiDiGraph()
    g.add_nodes_from([1, 2, 3, 4])
    g.add_edge(1, 2, longitud_m=10)
    g.add_edge(2, 1, longitud_m=10)
    g.add_edge(2, 3, longitud_m=5)
    d = estadisticas_red(g)
    assert (d["componentes_fuertes"], d["componentes_debiles"]) == (3, 2)
    assert d["mayor_scc_nodos"] == 2
    assert d["mayor_scc_longitud_m"] == 20
    assert d["mayor_scc_nodos_pct_original"] == 50
    assert d["mayor_scc_longitud_pct_original"] == 80


def test_cota_de_incertidumbre_nunca_utiliza_veto_confirmado():
    g = nx.MultiDiGraph(crs="EPSG:4326")
    for n in range(1, 6):
        g.add_node(n, x=-78.5+n*.001, y=-.2)
    decisiones = {}
    for a, b, state, ref in [(1, 2, "sin_restriccion_documentada", "way/1"),
                             (2, 3, "revision", "node/100"),
                             (3, 4, "sin_restriccion_documentada", "way/2"),
                             (4, 5, "restringida", "node/101")]:
        for u, v in ((a, b), (b, a)):
            g.add_edge(u, v, key=0, longitud_m=100)
            decisiones[u, v, 0] = {"estado": state, "motivos": [[state, "causa", ref]]}
    h = g.copy()
    h.remove_edges_from([e for e, d in decisiones.items() if d["estado"] in ("revision", "restringida")])
    h.remove_nodes_from(list(nx.isolates(h)))
    before = list(h.edges(keys=True, data=True))
    d, _ = analisis_topologico(g, h, decisiones, {"nodos": {"100": {"barrier": "gate"}}, "vias": {}})
    assert d["cota_topologica_sin_prohibidas"]["nodos_alcanzables_ida_vuelta_principal"] == 4
    assert d["fuentes_inciertas_priorizadas"][0]["nodos_recuperables_si_solo_esta_fuente_se_autorizara"] == 2
    assert list(h.edges(keys=True, data=True)) == before
    assert all(f["fuente"] != "node/101" for f in d["fuentes_inciertas_priorizadas"])


@pytest.mark.parametrize(("http", "detail", "dist", "nodes", "esperado"), [
    (422, "Origen o destino demasiado lejos de la red con predicciones.", [301, 0], [1, 2], "fuera_cobertura"),
    (422, "No existe una ruta conectada.", [0, 0], [1, 2], "sin_camino"),
    (422, "Origen y destino coinciden en el mismo nodo.", [0, 0], [1, 1], "mismo_nodo"),
    (500, "fallo", [0, 0], [1, 2], "error_tecnico"),
    (422, "Origen o destino demasiado lejos de la red con predicciones.", [300, 0], [1, 2], "error_tecnico"),
    (200, None, [300, 0], [1, 2], "evaluable"),
])
def test_no_confunde_rechazos_esperados_con_errores(http, detail, dist, nodes, esperado):
    assert estado_respuesta(http, {"detail": detail}, dist, nodes) == esperado
