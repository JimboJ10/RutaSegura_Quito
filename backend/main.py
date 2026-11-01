from pathlib import Path

import networkx as nx
import numpy as np
import osmnx as ox

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from shapely.geometry import LineString, MultiLineString
from shapely import wkt

# ==========================================
# RUTASEGURA - API DE RUTAS V1
# ==========================================

ROOT = Path(__file__).resolve().parents[1]
GRAFO = ROOT / "red_vial" / "quito_demo_con_predicciones.graphml"

if not GRAFO.exists():
    raise RuntimeError(f"No existe el grafo: {GRAFO}")

G = ox.load_graphml(GRAFO)

ALPHAS = [0.25, 0.5, 1, 2, 4, 8, 16]
DESVIO_MAX = 0.15
MAX_AJUSTE_M = 300

# Recuperar los atributos numéricos
for _, _, _, d in G.edges(keys=True, data=True):
    for campo in [
        "longitud_m",
        "score_historico",
        "score_lightgbm"
    ]:
        d[campo] = float(d[campo])

# Escalas utilizadas por el optimizador
MEDIANAS = {
    "hist": float(np.median([
        d["score_historico"]
        for _, _, d in G.edges(data=True)
    ])),
    "ml": float(np.median([
        d["score_lightgbm"]
        for _, _, d in G.edges(data=True)
    ]))
}

# Preparar los mismos pesos de la prueba
for _, _, _, d in G.edges(keys=True, data=True):
    L = d["longitud_m"]

    for i, alpha in enumerate(ALPHAS):
        d[f"w_hist_{i}"] = L * (
            1 + alpha * d["score_historico"]
            / max(MEDIANAS["hist"], 1e-6)
        )

        d[f"w_ml_{i}"] = L * (
            1 + alpha * d["score_lightgbm"]
            / max(MEDIANAS["ml"], 1e-6)
        )

app = FastAPI(
    title="RutaSegura Quito API",
    version="0.1.0",
    description="Comparador experimental de rutas peatonales"
)

class Coordenada(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)

class SolicitudRuta(BaseModel):
    origen: Coordenada
    destino: Coordenada


def evaluar_camino(nodos, peso):
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


def buscar_alternativa(inicio, fin, base, tipo, indice):
    mejor = base
    limite = base["distancia_m"] * (1 + DESVIO_MAX)

    for i in range(len(ALPHAS)):
        peso = f"w_{tipo}_{i}"

        nodos = nx.shortest_path(
            G, inicio, fin, weight=peso
        )

        candidata = evaluar_camino(nodos, peso)

        if (
            candidata["distancia_m"] <= limite + 1e-6
            and candidata[indice] < mejor[indice] - 1e-9
        ):
            mejor = candidata

    return mejor


def geometria_camino(ruta):
    lineas = []

    for u, v, d in ruta["aristas"]:
        geom = d.get("geometry")

        if isinstance(geom, str):
            geom = wkt.loads(geom)

        if geom is None:
            geom = LineString([
                (float(G.nodes[u]["x"]), float(G.nodes[u]["y"])),
                (float(G.nodes[v]["x"]), float(G.nodes[v]["y"]))
            ])

        if isinstance(geom, LineString):
            geometria_partes = [geom]
        elif isinstance(geom, MultiLineString):
            geometria_partes = list(geom.geoms)
        else:
            raise ValueError("Geometría vial no compatible")

        for parte in geometria_partes:
            lineas.append([
                [float(x), float(y)]
                for x, y in parte.coords
            ])

    return {
        "type": "MultiLineString",
        "coordinates": lineas
    }


@app.get("/health")
def health():
    return {
        "estado": "ok",
        "proyecto": "RutaSegura Quito",
        "nodos": G.number_of_nodes(),
        "aristas": G.number_of_edges(),
        "periodo": "2026-06"
    }


@app.post("/rutas")
def calcular_rutas(solicitud: SolicitudRuta):
    a = solicitud.origen
    b = solicitud.destino

    inicio, ajuste_a = ox.distance.nearest_nodes(
        G, X=a.lon, Y=a.lat, return_dist=True
    )

    fin, ajuste_b = ox.distance.nearest_nodes(
        G, X=b.lon, Y=b.lat, return_dist=True
    )

    if max(ajuste_a, ajuste_b) > MAX_AJUSTE_M:
        raise HTTPException(
            status_code=422,
            detail=(
                "Origen o destino demasiado lejos "
                "de la red con predicciones."
            )
        )

    if inicio == fin:
        raise HTTPException(
            status_code=422,
            detail="Origen y destino coinciden en el mismo nodo."
        )

    try:
        nodos = nx.shortest_path(
            G, inicio, fin, weight="longitud_m"
        )

        corta = evaluar_camino(nodos, "longitud_m")

        historica = buscar_alternativa(
            inicio, fin, corta,
            "hist", "indice_hist"
        )

        lightgbm = buscar_alternativa(
            inicio, fin, corta,
            "ml", "indice_ml"
        )

    except nx.NetworkXNoPath:
        raise HTTPException(
            status_code=422,
            detail="No existe una ruta conectada."
        )

    rutas = [
        ("corta", corta),
        ("historica", historica),
        ("lightgbm", lightgbm)
    ]

    features = []

    for nombre, ruta in rutas:
        distancia = ruta["distancia_m"]

        features.append({
            "type": "Feature",
            "properties": {
                "id": nombre,
                "distancia_km": round(distancia / 1000, 4),
                "desvio_pct": round(
                    100 * (distancia / corta["distancia_m"] - 1),
                    3
                ),
                "indice_historico": round(
                    ruta["indice_hist"], 4
                ),
                "indice_lightgbm": round(
                    ruta["indice_ml"], 4
                )
            },
            "geometry": geometria_camino(ruta)
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "periodo": "2026-06",
            "tipo": "demostracion_retrospectiva",
            "desvio_maximo_pct": 15,
            "origen_ajustado": {
                "lat": float(G.nodes[inicio]["y"]),
                "lon": float(G.nodes[inicio]["x"]),
                "distancia_ajuste_m": round(float(ajuste_a), 1)
            },
            "destino_ajustado": {
                "lat": float(G.nodes[fin]["y"]),
                "lon": float(G.nodes[fin]["x"]),
                "distancia_ajuste_m": round(float(ajuste_b), 1)
            },
            "advertencia": (
                "Distancias calculadas entre nodos ajustados. "
                "No incluyen el acceso desde las coordenadas solicitadas. "
                "Los indicadores no representan probabilidad individual de accidente."
            )
        }
    }
