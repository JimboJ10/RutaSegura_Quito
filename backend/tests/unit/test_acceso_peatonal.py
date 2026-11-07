"""Política offline de acceso: prioridad modal, incertidumbre y nodos intermedios."""
from pathlib import Path
import sys

import networkx as nx
import pytest
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
from auditar_acceso_peatonal import FuenteOSM, filtrar, permiso, ejecutar


@pytest.mark.parametrize(("tags", "estado"), [
    ({"access": "no", "psv": "yes", "bus": "designated"}, "restringida"),
    ({"access": "private"}, "restringida"),
    ({"foot": "no", "access": "yes"}, "restringida"),
    ({"foot": "private"}, "restringida"),
    ({"foot": "use_sidepath"}, "restringida"),
    *[({"access": "no", "foot": v}, "autorizacion_explicita")
      for v in ("yes", "designated", "permissive", "official")],
    ({"access": "private", "foot": "yes", "motor_vehicle": "no"}, "autorizacion_explicita"),
    ({"highway": "footway", "motor_vehicle": "no"}, "sin_restriccion_documentada"),
    ({"highway": "footway", "footway": "sidewalk"}, "sin_restriccion_documentada"),
    ({"highway": "path"}, "sin_restriccion_documentada"),
    ({"highway": "residential", "sidewalk": "no"}, "sin_restriccion_documentada"),
    ({"highway": "residential", "sidewalk": "both", "foot": "no"}, "restringida"),
    ({"access": "no", "bicycle": "yes"}, "restringida"),
    ({"foot": "destination"}, "revision"),
    *[({"access": v}, "revision") for v in ("customers", "permit", "delivery", "unknown")],
    ({"foot": "yes;no"}, "revision"),
    ({"foot": "yes", "foot:conditional": "no @ (night)"}, "revision"),
    ({"access": "yes", "access:conditional": "no @ (night)"}, "revision"),
    ({"foot": "yes", "access:conditional": "no @ (night)"}, "autorizacion_explicita"),
    ({"foot": "yes", "opening_hours": "08:00-18:00"}, "revision"),
    ({"foot": "yes", "oneway:foot": "yes"}, "revision"),
    ({"highway": "trunk"}, "revision"),
    ({"highway": "trunk", "foot": "yes"}, "autorizacion_explicita"),
    ({"highway": "service", "psv": "yes"}, "sin_restriccion_documentada"),
])
def test_prioridad_y_datos_insuficientes(tags, estado):
    assert permiso(tags)[0] == estado


@pytest.mark.parametrize(("tags", "estado"), [
    ({"barrier": "gate", "access": "private"}, "restringida"),
    ({"barrier": "gate", "access": "private", "foot": "yes"}, "autorizacion_explicita"),
    ({"barrier": "gate"}, "revision"),
    ({"barrier": "bollard"}, "sin_restriccion_documentada"),
    ({"barrier": "kerb", "wheelchair": "no"}, "sin_restriccion_documentada"),
    ({"barrier": "gate", "foot": "yes", "locked": "yes"}, "revision"),
])
def test_barreras_y_excepciones(tags, estado):
    assert permiso(tags, nodo=True)[0] == estado


def ejemplo(tags_way=None, tags_nodo=None):
    nodos = [{"type": "node", "id": i, "lon": -78.5 + i * .001, "lat": -.2,
              "tags": (tags_nodo or {}) if i == 2 else {}} for i in (1, 2, 3)]
    way = {"type": "way", "id": 10, "nodes": [1, 2, 3], "tags": {"highway": "footway", **(tags_way or {})}}
    fuente = FuenteOSM({"elements": [*nodos, way]})
    g = nx.MultiDiGraph(crs="EPSG:4326")
    for n in (nodos[0], nodos[-1]):
        g.add_node(n["id"], x=n["lon"], y=n["lat"])
    geom = LineString([(n["lon"], n["lat"]) for n in nodos])
    g.add_edge(1, 3, key=7, osmid=10, geometry=geom, longitud_m=222,
               score_historico=4, score_lightgbm=7)
    return g, fuente


def test_barrera_intermedia_perdida_en_simplificacion():
    g, fuente = ejemplo(tags_nodo={"barrier": "gate", "access": "private"})
    h, decisiones, aislados = filtrar(g, fuente)
    assert h.number_of_edges() == 0
    assert decisiones[1, 3, 7]["estado"] == "restringida"
    assert any(m[2] == "node/2" for m in decisiones[1, 3, 7]["motivos"])
    assert set(aislados) == {1, 3}
    assert g.number_of_edges() == 1


def test_excepcion_en_porton_conserva_acera_y_todos_sus_datos():
    g, fuente = ejemplo(tags_nodo={"barrier": "gate", "access": "private", "foot": "yes"})
    h, _, _ = filtrar(g, fuente)
    assert h[1][3][7] == g[1][3][7]
    assert h.nodes == g.nodes


def test_via_paralela_permitida_no_se_borra_por_la_restringida():
    g, fuente = ejemplo({"access": "no"})
    fuente.vias[11] = {"type": "way", "id": 11, "nodes": [1, 2, 3], "tags": {"highway": "footway", "foot": "yes"}}
    fuente = FuenteOSM({"elements": [*fuente.nodos.values(), *fuente.vias.values()]})
    g.add_edge(1, 3, key=8, **{**g[1][3][7], "osmid": 11})
    h, decisiones, _ = filtrar(g, fuente)
    assert list(h.edges(keys=True)) == [(1, 3, 8)]
    assert decisiones[1, 3, 7]["estado"] == "restringida"


def test_osmid_ausente_y_geometria_sin_respaldo_se_cuarentenan():
    g, fuente = ejemplo()
    g[1][3][7]["osmid"] = 999
    h, decisiones, _ = filtrar(g, fuente)
    assert h.number_of_edges() == 0
    assert decisiones[1, 3, 7]["estado"] == "revision"


def test_condicional_de_bus_no_restringe_al_peaton():
    assert permiso({"highway": "footway", "bus:conditional": "yes @ (Mo-Fr)"})[0] == "sin_restriccion_documentada"


@pytest.mark.parametrize("existente", ["grafo", "informe"])
def test_generador_rechaza_sobrescribir_una_entrega(tmp_path, existente):
    salida, evidencia = tmp_path / "grafo", tmp_path / "informe"
    protegido = tmp_path / existente
    protegido.mkdir()
    contenido = protegido / "conservar.txt"
    contenido.write_text("original", encoding="utf-8")
    with pytest.raises(SystemExit, match="ya existe"):
        ejecutar(salida, evidencia)
    assert contenido.read_text(encoding="utf-8") == "original"
