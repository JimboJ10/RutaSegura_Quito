"""Carga local del grafo y preparación de los pesos de enrutamiento."""

from functools import lru_cache
import math
from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox
from pyproj import CRS
from pyproj.exceptions import CRSError

from config import ALPHAS, CRS_ESPERADO, GRAFO
from geojson import partes_arista


@lru_cache(maxsize=1)
def cargar_grafo(ruta=GRAFO):
    """Reutiliza el grafo preparado durante toda la vida del proceso."""
    ruta = Path(ruta)
    if not ruta.exists():
        raise RuntimeError(f"No existe el grafo: {ruta}")
    if not ruta.is_file():
        raise RuntimeError(f"La ruta del grafo no es un archivo: {ruta}")

    try:
        # Validar nosotros x/y permite identificar el nodo y atributo inválidos.
        G = ox.load_graphml(ruta, node_dtypes={"x": str, "y": str})
    except Exception as exc:
        raise RuntimeError(f"No se pudo leer el GraphML '{ruta}': {exc}") from exc

    return preparar_grafo(G)


def _numero(datos, campo, contexto):
    if campo not in datos:
        raise ValueError(f"{contexto}: falta el atributo '{campo}'")
    valor = datos[campo]
    try:
        if isinstance(valor, bool):
            raise ValueError("booleano")
        numero = float(valor)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{contexto}: '{campo}' debe ser numérico") from exc
    if not math.isfinite(numero):
        raise ValueError(f"{contexto}: '{campo}' debe ser finito")
    return numero


def validar_grafo(G):
    """Rechaza datos incompletos; nunca imputa cero a un indicador ausente."""
    if not isinstance(G, nx.MultiDiGraph):
        raise ValueError("La red debe ser un MultiDiGraph dirigido con aristas paralelas")
    if G.number_of_nodes() < 2 or G.number_of_edges() == 0:
        raise ValueError("Grafo insuficiente: se requieren al menos dos nodos y una arista")
    try:
        crs = CRS.from_user_input(G.graph.get("crs"))
    except (CRSError, TypeError, ValueError) as exc:
        raise ValueError(f"CRS ausente o inválido; se requiere {CRS_ESPERADO}") from exc
    if not crs.equals(CRS.from_user_input(CRS_ESPERADO)):
        raise ValueError(f"CRS incompatible: {crs.to_string()}; se requiere {CRS_ESPERADO}")

    for nodo, datos in G.nodes(data=True):
        contexto = f"Nodo {nodo!r}"
        for campo, minimo, maximo in [("x", -180, 180), ("y", -90, 90)]:
            numero = _numero(datos, campo, contexto)
            if not minimo <= numero <= maximo:
                raise ValueError(f"{contexto}: '{campo}' fuera del rango [{minimo}, {maximo}]")
            datos[campo] = numero

    for u, v, k, datos in G.edges(keys=True, data=True):
        contexto = f"Arista ({u}, {v}, {k})"
        for campo in ["longitud_m", "score_historico", "score_lightgbm"]:
            numero = _numero(datos, campo, contexto)
            if campo == "longitud_m" and numero <= 0:
                raise ValueError(f"{contexto}: 'longitud_m' debe ser estrictamente positiva")
            if campo != "longitud_m" and numero < 0:
                raise ValueError(f"{contexto}: '{campo}' debe ser no negativo")
            datos[campo] = numero
        try:
            partes_arista(G, u, v, datos)
        except ValueError as exc:
            raise ValueError(f"{contexto}: {exc}") from exc


def preparar_grafo(G):
    """Valida el grafo y conserva las fórmulas originales de los pesos."""
    validar_grafo(G)

    # Conservar las mismas escalas y penalizaciones del optimizador validado.
    medianas = {
        "hist": float(np.median([
            d["score_historico"]
            for _, _, d in G.edges(data=True)
        ])),
        "ml": float(np.median([
            d["score_lightgbm"]
            for _, _, d in G.edges(data=True)
        ]))
    }
    if not all(math.isfinite(valor) for valor in medianas.values()):
        raise ValueError("Los indicadores desbordan el cálculo de las medianas")

    for u, v, k, d in G.edges(keys=True, data=True):
        L = d["longitud_m"]

        for i, alpha in enumerate(ALPHAS):
            d[f"w_hist_{i}"] = L * (
                1 + alpha * d["score_historico"]
                / max(medianas["hist"], 1e-6)
            )
            d[f"w_ml_{i}"] = L * (
                1 + alpha * d["score_lightgbm"]
                / max(medianas["ml"], 1e-6)
            )
            if not all(math.isfinite(d[campo]) for campo in [f"w_hist_{i}", f"w_ml_{i}"]):
                raise ValueError(f"Arista ({u}, {v}, {k}): desbordamiento de los pesos")

    return G

