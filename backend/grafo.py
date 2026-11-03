"""Carga local del grafo y preparación de los pesos de enrutamiento."""

from functools import lru_cache

import numpy as np
import osmnx as ox

from config import ALPHAS, GRAFO


@lru_cache(maxsize=1)
def cargar_grafo():
    """Reutiliza el grafo preparado durante toda la vida del proceso."""
    if not GRAFO.exists():
        raise RuntimeError(f"No existe el grafo: {GRAFO}")

    G = ox.load_graphml(GRAFO)

    # Recuperar los atributos numéricos.
    for _, _, _, d in G.edges(keys=True, data=True):
        for campo in ["longitud_m", "score_historico", "score_lightgbm"]:
            d[campo] = float(d[campo])

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

    for _, _, _, d in G.edges(keys=True, data=True):
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

    return G

