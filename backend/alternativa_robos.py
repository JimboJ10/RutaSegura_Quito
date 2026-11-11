"""Cuarta modalidad local. La preparación espacial se conserva solo en memoria."""
from dataclasses import dataclass
from functools import lru_cache
from threading import Lock

import networkx as nx
import numpy as np
import shapely as sh
from pyproj import Transformer

import robos_historicos
from config import ALPHAS, DESVIO_MAX
from geojson import coleccion_geojson, partes_arista
from rutas import calcular_recorridos, evaluar_camino


MIN_METROS = 10
MIN_FRACCION = 0.02
EPS = 1e-6
_preparando = Lock()


@dataclass
class Preparacion:
    original: nx.MultiDiGraph
    red: nx.MultiDiGraph
    ids_originales: dict
    metricas: np.ndarray
    geometrias: np.ndarray
    pesos: list[str]


def preparar(grafo, features):
    props = [f["properties"] for f in features]
    densidad = np.asarray([p["densidad_registros_periodo_km2"] for p in props], dtype=float)
    altas = np.array([p["nivel"] == robos_historicos.ALTA for p in props])
    conocidas = np.isfinite(densidad)
    if altas.sum() != 5 or not conocidas[altas].all() or np.median(densidad[conocidas]) <= 0:
        raise ValueError("Clasificación histórica incompleta")

    proyeccion = Transformer.from_crs(4326, 32717, always_xy=True)

    def metros(geometrias):
        return sh.length(sh.transform(geometrias, proyeccion.transform, interleaved=False))

    # Copia privada. Nunca se escriben pesos temporales en el grafo de FastAPI.
    red = grafo.copy()
    aristas = list(red.edges(keys=True, data=True))
    lineas = np.array([sh.MultiLineString(partes_arista(red, u, v, d)) for u, v, _, d in aristas])
    indice = sh.STRtree(lineas)
    matriz = np.zeros((len(lineas), len(features)))
    for columna, feature in enumerate(features):
        celda = sh.geometry.shape(feature["geometry"])
        ids = indice.query(celda, predicate="intersects")
        interiores = sh.difference(sh.intersection(lineas[ids], celda), celda.boundary)
        matriz[ids, columna] = metros(interiores)
    exterior = metros(lineas) - matriz.sum(axis=1)
    if exterior.min() < -0.001:
        raise ValueError("Intersecciones históricas solapadas")
    exterior[exterior < 1e-5] = 0
    sin_datos = np.column_stack((matriz[:, ~conocidas], exterior))
    h = matriz[:, altas].sum(axis=1)
    d = matriz[:, conocidas] @ densidad[conocidas] / 1000
    longitudes = np.array([datos["longitud_m"] for _, _, _, datos in aristas])
    metricas = np.column_stack((longitudes, h, d, sin_datos))
    if not np.isfinite(metricas).all():
        raise ValueError("Mediciones espaciales no finitas")
    desconocido = sin_datos.sum(axis=1)
    proxy = (d * 1000 + desconocido * densidad[conocidas].max()) / np.median(densidad[conocidas])
    pesos = {}
    for alpha in ALPHAS:
        for nombre, penalizacion in (("zonas", h + desconocido), ("densidad", proxy)):
            pesos[f"{nombre}_{alpha}"] = longitudes + alpha * penalizacion
    for i, (_, _, _, datos) in enumerate(aristas):
        datos["indice_espacial"] = i
        datos.update({k: float(valores[i]) for k, valores in pesos.items()})
    ids_originales = {id(grafo[u][v][k]): i for i, (u, v, k, _) in enumerate(aristas)}
    return Preparacion(grafo, red, ids_originales, metricas, lineas, list(pesos))


@lru_cache(maxsize=1)
def _preparacion_versionada(grafo, archivo, version):
    return preparar(grafo, robos_historicos.leer_capa()["features"])


def obtener_preparacion(grafo):
    archivo = robos_historicos.ARCHIVO
    with _preparando:
        estado = archivo.stat()
        return _preparacion_versionada(grafo, archivo, (estado.st_mtime_ns, estado.st_size))


def aceptable(base, candidata):
    distancia, altas, ponderado = candidata[:3]
    return (
        distancia <= base[0] * (1 + DESVIO_MAX) + EPS
        and base[1] - altas >= max(MIN_METROS, MIN_FRACCION * base[1])
        and base[2] > 0 and base[2] - ponderado >= MIN_FRACCION * base[2]
        and np.all(candidata[3:] <= base[3:] + EPS)
    )


def indices(ruta):
    return tuple(datos["indice_espacial"] for _, _, datos in ruta["aristas"])


def comparar(preparacion, inicio, fin, ajuste_a, ajuste_b):
    red = preparacion.red
    # Las referencias se resuelven sobre el mismo objeto que /rutas, incluidos sus desempates.
    original = preparacion.original
    nodos = nx.shortest_path(original, inicio, fin, weight="longitud_m")
    corta = evaluar_camino(original, nodos, "longitud_m")
    def indices_originales(ruta):
        return tuple(preparacion.ids_originales[id(d)] for _, _, d in ruta["aristas"])

    ids_base = indices_originales(corta)
    base = preparacion.metricas[list(ids_base)].sum(axis=0)
    mejor = None
    orden = None
    vistas = {ids_base}
    if base[1] >= MIN_METROS and base[2] > 0:
        for peso in preparacion.pesos:
            nodos = nx.shortest_path(red, inicio, fin, weight=peso)
            ruta = evaluar_camino(red, nodos, peso)
            ids = indices(ruta)
            if ids in vistas:
                continue
            vistas.add(ids)
            medida = preparacion.metricas[list(ids)].sum(axis=0)
            prioridad = (medida[1], medida[2], medida[0])
            if aceptable(base, medida) and (orden is None or prioridad < orden):
                orden = prioridad
                mejor = (ruta, ids, medida)
    if mejor is None:
        return {"estado": "sin_alternativa"}

    ruta, ids, medida = mejor
    forma = sh.union_all(preparacion.geometrias[list(ids)])
    for nombre, existente in calcular_recorridos(original, inicio, fin):
        if forma.equals(sh.union_all(preparacion.geometrias[list(indices_originales(existente))])):
            return {"estado": "coincidente", "modalidad": nombre}
    feature = coleccion_geojson(red, [("corta", corta), ("robos", ruta)], inicio, fin,
                                ajuste_a, ajuste_b)["features"][1]
    feature["properties"]["comparacion_robos"] = {
        "periodo": "2019-2022", "altas_corta_m": base[1], "altas_m": medida[1],
        "ponderado_corta": base[2], "ponderado": medida[2],
    }
    return {"estado": "disponible", "feature": feature}
