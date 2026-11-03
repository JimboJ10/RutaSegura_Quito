"""Geometrías, propiedades y metadatos de la respuesta de rutas."""

from shapely import wkt
from shapely.geometry import LineString, MultiLineString

from config import PERIODO


def geometria_camino(G, ruta):
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

