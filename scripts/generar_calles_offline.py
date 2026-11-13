"""Genera únicamente líneas OSM de referencia a partir de la demo filtrada local."""
import gzip
import json
import sys
from pathlib import Path

import networkx as nx
from shapely.geometry import LineString, MultiLineString
from shapely.ops import linemerge

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from datos_mvp import verificar_archivo
from geojson import partes_arista


def serializar(lineas):
    return json.dumps({"type": "MultiLineString", "coordinates": lineas},
                      separators=(",", ":"), allow_nan=False).encode()


def main():
    origen = ROOT / verificar_archivo("grafo")["ruta"]
    red = nx.read_graphml(origen)
    originales = []
    segmentos = set()
    for u, v, datos in red.edges(data=True):
        for linea in partes_arista(red, u, v, datos):
            originales.append(linea)
            for a, b in zip(linea, linea[1:]):
                if a != b:
                    segmentos.add(tuple(sorted((tuple(a), tuple(b)))))
    # Une piezas ya contiguas, conservando las bifurcaciones como extremos.
    cadenas = linemerge(MultiLineString(sorted(segmentos)))
    salida = []
    max_error = 0
    for linea in cadenas.geoms:
        puntos = [(round(x, 6), round(y, 6)) for x, y in linea.simplify(.000008).coords]
        if len(set(puntos)) < 2:
            puntos = list(linea.coords)
        max_error = max(max_error, linea.hausdorff_distance(LineString(puntos)) * 111400)
        salida.append(puntos)
    assert max_error < 1.1, max_error
    datos = serializar(salida)
    (ROOT / "frontend/public/calles-piloto.geojson").write_bytes(datos)
    print("GraphML / GeoJSON original / simplificado / gzip (bytes):",
          origen.stat().st_size, len(serializar(originales)), len(datos), len(gzip.compress(datos, mtime=0)))
    print("Aristas / segmentos únicos / cadenas / error máximo aproximado (m):",
          red.number_of_edges(), len(segmentos), len(salida), max_error)


if __name__ == "__main__":
    main()
