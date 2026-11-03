"""Geometrías, propiedades y metadatos de la respuesta de rutas."""

import math

from shapely import wkt
from shapely.errors import GEOSException
from shapely.geometry import LineString, MultiLineString

from config import PERIODO, TOLERANCIA_COORDENADAS


def _coinciden(a, b):
    return all(
        math.isclose(x, y, rel_tol=0, abs_tol=TOLERANCIA_COORDENADAS)
        for x, y in zip(a, b)
    )


def partes_arista(G, u, v, datos):
    """Orienta la geometría existente de u a v sin inventar tramos de unión."""
    inicio = [float(G.nodes[u]["x"]), float(G.nodes[u]["y"])]
    fin = [float(G.nodes[v]["x"]), float(G.nodes[v]["y"])]
    geom = datos.get("geometry")
    if isinstance(geom, str):
        try:
            geom = wkt.loads(geom)
        except (GEOSException, ValueError) as exc:
            raise ValueError("Geometría vial WKT inválida") from exc

    if geom is None:
        geom = LineString([inicio, fin])

    if isinstance(geom, LineString):
        geometria_partes = [geom]
    elif isinstance(geom, MultiLineString):
        geometria_partes = list(geom.geoms)
    else:
        raise ValueError("Geometría vial no compatible")
    if geom.is_empty:
        raise ValueError("Geometría vial vacía")

    pendientes = []
    for parte in geometria_partes:
        coordenadas = [list(posicion) for posicion in parte.coords]
        if len(coordenadas) < 2:
            raise ValueError("Geometría vial sin suficientes coordenadas")
        for posicion in coordenadas:
            if len(posicion) != 2 or not all(math.isfinite(valor) for valor in posicion):
                raise ValueError("Geometría vial: se requieren coordenadas 2D finitas")
            lon, lat = posicion
            if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                raise ValueError("Geometría vial fuera de EPSG:4326 (longitud, latitud)")
        if not parte.is_valid or parte.length <= 0:
            raise ValueError("Geometría vial inválida o de longitud cero")
        pendientes.append(coordenadas)

    lineas = []
    actual = inicio
    while pendientes:
        for indice, coordenadas in enumerate(pendientes):
            if _coinciden(coordenadas[0], actual):
                orientadas = coordenadas
                break
            if _coinciden(coordenadas[-1], actual):
                orientadas = coordenadas[::-1]
                break
        else:
            raise ValueError(f"Geometría vial discontinua o no alineada con el nodo {u}")
        pendientes.pop(indice)
        lineas.append(orientadas)
        actual = orientadas[-1]
    if not _coinciden(actual, fin):
        raise ValueError(f"Geometría vial no termina en el nodo {v}")
    return lineas


def geometria_camino(G, ruta):
    lineas = []
    for u, v, d in ruta["aristas"]:
        partes = partes_arista(G, u, v, d)
        if lineas and not _coinciden(lineas[-1][-1], partes[0][0]):
            raise ValueError("Ruta con segmentos discontinuos")
        lineas.extend(partes)
    if not lineas:
        raise ValueError("Ruta sin aristas")

    return {
        "type": "MultiLineString",
        "coordinates": lineas
    }


def coleccion_geojson(G, rutas, inicio, fin, ajuste_a, ajuste_b):
    # calcular_recorridos siempre devuelve primero la ruta corta de referencia.
    corta = rutas[0][1]
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
            "geometry": geometria_camino(G, ruta)
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "periodo": PERIODO,
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

