import math

import networkx as nx
import osmnx as ox
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from shapely.geometry import Point

import grafo
import main
from grafo import preparar_grafo, validar_grafo


@pytest.mark.parametrize("tipo", [nx.Graph, nx.DiGraph, nx.MultiGraph])
def test_rechaza_tipo_de_grafo_incompatible(tipo):
    with pytest.raises(ValueError, match="MultiDiGraph"):
        validar_grafo(tipo())


@pytest.mark.parametrize("numero_nodos", [0, 1, 2])
def test_rechaza_grafo_sin_datos_suficientes(numero_nodos):
    G = nx.MultiDiGraph(crs="epsg:4326")
    G.add_nodes_from(range(numero_nodos))
    with pytest.raises(ValueError, match="Grafo insuficiente"):
        validar_grafo(G)


@pytest.mark.parametrize("crs", [None, "no-es-un-crs", "EPSG:3857", "EPSG:32617"])
def test_rechaza_crs_incorrecto(grafo_base, crs):
    grafo_base.graph["crs"] = crs
    with pytest.raises(ValueError, match="CRS.*EPSG:4326"):
        validar_grafo(grafo_base)


@pytest.mark.parametrize("campo", ["x", "y"])
def test_identifica_coordenada_ausente(grafo_base, campo):
    del grafo_base.nodes[1][campo]
    with pytest.raises(ValueError, match=f"Nodo 1: falta el atributo '{campo}'"):
        validar_grafo(grafo_base)


@pytest.mark.parametrize(
    ("campo", "valor"),
    [("x", 181), ("x", -181), ("y", 91), ("y", -91)]
    + [(campo, valor) for campo in ["x", "y"]
       for valor in [float("nan"), float("inf"), float("-inf"), "texto", None, True]],
)
def test_identifica_coordenada_invalida(grafo_base, campo, valor):
    grafo_base.nodes[1][campo] = valor
    with pytest.raises(ValueError, match=f"Nodo 1: '{campo}'"):
        validar_grafo(grafo_base)


@pytest.mark.parametrize("campo", ["longitud_m", "score_historico", "score_lightgbm"])
def test_identifica_atributo_de_arista_ausente_sin_imputar_cero(grafo_base, campo):
    datos = grafo_base[1][2][0]
    del datos[campo]
    with pytest.raises(ValueError, match=rf"Arista \(1, 2, 0\): falta el atributo '{campo}'"):
        preparar_grafo(grafo_base)
    assert campo not in datos


@pytest.mark.parametrize("valor", [0, -1, float("nan"), float("inf"), float("-inf"), "texto", None, True])
def test_rechaza_longitud_invalida(grafo_base, valor):
    grafo_base[1][2][0]["longitud_m"] = valor
    with pytest.raises(ValueError, match=r"Arista \(1, 2, 0\).*longitud_m"):
        preparar_grafo(grafo_base)


@pytest.mark.parametrize("campo", ["score_historico", "score_lightgbm"])
@pytest.mark.parametrize("valor", [-1, float("nan"), float("inf"), float("-inf"), "texto", None, True])
def test_rechaza_indicador_invalido(grafo_base, campo, valor):
    grafo_base[1][2][0][campo] = valor
    with pytest.raises(ValueError, match=rf"Arista \(1, 2, 0\).*{campo}"):
        preparar_grafo(grafo_base)


def test_acepta_cero_explicito_y_convierte_numeros_serializados(grafo_base):
    grafo_base.nodes[1]["x"] = "-78.500"
    for _, _, datos in grafo_base.edges(data=True):
        datos.update(longitud_m="100", score_historico="0", score_lightgbm="0")
    G = preparar_grafo(grafo_base)
    for _, _, datos in G.edges(data=True):
        assert datos["score_historico"] == datos["score_lightgbm"] == 0
        for campo, valor in datos.items():
            if campo.startswith("w_"):
                assert math.isfinite(valor) and valor == 100


def test_rechaza_desbordamiento_de_pesos(grafo_base):
    grafo_base[1][2][0]["longitud_m"] = 1e308
    with pytest.raises(ValueError, match="desbordamiento de los pesos"):
        preparar_grafo(grafo_base)


def test_identifica_arista_con_geometria_incompatible(grafo_base):
    grafo_base[1][2][0]["geometry"] = Point(-78.5, -0.2)
    with pytest.raises(ValueError, match=r"Arista \(1, 2, 0\): Geometría vial no compatible"):
        validar_grafo(grafo_base)


def test_archivo_ausente(tmp_path):
    with pytest.raises(RuntimeError, match="No existe el grafo:.*ausente.graphml"):
        grafo.cargar_grafo.__wrapped__(tmp_path / "ausente.graphml")


def test_ruta_es_directorio(tmp_path):
    with pytest.raises(RuntimeError, match="no es un archivo"):
        grafo.cargar_grafo.__wrapped__(tmp_path)


def test_graphml_malformado(tmp_path):
    ruta = tmp_path / "corrupto.graphml"
    ruta.write_text("<graphml><graph", encoding="utf-8")
    with pytest.raises(RuntimeError, match="No se pudo leer el GraphML.*corrupto.graphml") as error:
        grafo.cargar_grafo.__wrapped__(ruta)
    assert error.value.__cause__ is not None


def test_error_de_lectura_conserva_causa(tmp_path, monkeypatch):
    ruta = tmp_path / "sin_permiso.graphml"
    ruta.touch()

    def sin_permiso(*args, **kwargs):
        raise PermissionError("lectura denegada")

    monkeypatch.setattr(grafo.ox, "load_graphml", sin_permiso)
    with pytest.raises(RuntimeError, match="sin_permiso.graphml.*lectura denegada") as error:
        grafo.cargar_grafo.__wrapped__(ruta)
    assert isinstance(error.value.__cause__, PermissionError)


def test_carga_graphml_temporal_valido(tmp_path, grafo_base):
    ruta = tmp_path / "valido.graphml"
    ox.save_graphml(grafo_base, ruta)
    G = grafo.cargar_grafo.__wrapped__(ruta)
    assert isinstance(G, nx.MultiDiGraph)
    assert (G.number_of_nodes(), G.number_of_edges()) == (3, 2)
    assert G[1][2][0]["w_hist_0"] > 0


def test_nodo_invalido_en_graphml_temporal(tmp_path, grafo_base):
    grafo_base.nodes[1]["x"] = "texto"
    ruta = tmp_path / "nodo_invalido.graphml"
    ox.save_graphml(grafo_base, ruta)
    with pytest.raises(ValueError, match="Nodo 1: 'x' debe ser numérico"):
        grafo.cargar_grafo.__wrapped__(ruta)


def test_graphml_no_dirigido_no_se_convierte_silenciosamente(tmp_path, grafo_base):
    ruta = tmp_path / "no_dirigido.graphml"
    ox.save_graphml(grafo_base.to_undirected(), ruta)
    with pytest.raises(ValueError, match="MultiDiGraph"):
        grafo.cargar_grafo.__wrapped__(ruta)


def test_fallo_de_carga_impide_iniciar_la_aplicacion(monkeypatch):
    def carga_invalida():
        raise ValueError("Grafo insuficiente")

    monkeypatch.setattr(main, "cargar_grafo", carga_invalida)
    with pytest.raises(ValueError, match="Grafo insuficiente"):
        with TestClient(FastAPI(lifespan=main.lifespan)):
            pytest.fail("La aplicación no debe iniciar sin un grafo válido")
