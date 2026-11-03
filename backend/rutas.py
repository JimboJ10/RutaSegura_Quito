"""Cálculo y evaluación de las tres modalidades de recorrido."""

import networkx as nx

from config import ALPHAS, DESVIO_MAX


def evaluar_camino(G, nodos, peso):
    aristas = []

    for u, v in zip(nodos[:-1], nodos[1:]):
        k = min(
            G[u][v],
            key=lambda key: G[u][v][key][peso]
        )
        aristas.append((u, v, G[u][v][k]))

    distancia = sum(
        d["longitud_m"] for _, _, d in aristas
    )

    indice_hist = sum(
        d["longitud_m"] * d["score_historico"] / 1000
        for _, _, d in aristas
    )

    indice_ml = sum(
        d["longitud_m"] * d["score_lightgbm"] / 1000
        for _, _, d in aristas
    )

    return {
        "aristas": aristas,
        "distancia_m": distancia,
        "indice_hist": indice_hist,
        "indice_ml": indice_ml
    }


def buscar_alternativa(G, inicio, fin, base, tipo, indice):
    mejor = base
    limite = base["distancia_m"] * (1 + DESVIO_MAX)

    for i in range(len(ALPHAS)):
        peso = f"w_{tipo}_{i}"

        nodos = nx.shortest_path(
            G, inicio, fin, weight=peso
        )

        candidata = evaluar_camino(G, nodos, peso)

        if (
            candidata["distancia_m"] <= limite + 1e-6
            and candidata[indice] < mejor[indice] - 1e-9
        ):
            mejor = candidata

    return mejor


def calcular_recorridos(G, inicio, fin):
    nodos = nx.shortest_path(
        G, inicio, fin, weight="longitud_m"
    )

    corta = evaluar_camino(G, nodos, "longitud_m")

    historica = buscar_alternativa(
        G, inicio, fin, corta,
        "hist", "indice_hist"
    )

    lightgbm = buscar_alternativa(
        G, inicio, fin, corta,
        "ml", "indice_ml"
    )

    return [
        ("corta", corta),
        ("historica", historica),
        ("lightgbm", lightgbm)
    ]

