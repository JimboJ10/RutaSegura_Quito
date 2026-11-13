"""Repite la muestra local sobre los insumos auditados sin escribir datos ni geometrías."""
import hashlib
import json
import statistics
import sys
import time
from collections import Counter
from pathlib import Path

import networkx as nx
import osmnx as ox

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from alternativa_robos import comparar, obtener_preparacion
from config import COBERTURA, GRAFO, MAX_AJUSTE_M, RED
from grafo import cargar_grafo


def main():
    assert (COBERTURA, RED) == ("demo", "peatonal_filtrada")
    fuente = ROOT / "resultados/viabilidad_modalidad_robos/resultados.json"
    registro = json.loads(fuente.read_text(encoding="utf8"))
    huellas = registro["resumen"]["archivos_sha256"]
    assert GRAFO.resolve() in {(ROOT / ruta).resolve() for ruta in huellas}
    for ruta, huella in huellas.items():
        assert hashlib.sha256((ROOT / ruta).read_bytes()).hexdigest() == huella
    muestra = [p for p in registro["pares"] if p["id"] != "piloto"]
    previas = [p for p in muestra if p["estado"] == "alternativa"]
    print("Muestra original", len(muestra), Counter(p["estado"] for p in muestra))
    print("Distintas, máximo desvío y preparación original (s)",
          sum(not p["coincide_con"] for p in previas), max(p["desvio_pct"] for p in previas),
          registro["resumen"]["preparacion_s"])
    grafo = cargar_grafo()
    inicio = time.perf_counter()
    preparada = obtener_preparacion(grafo)
    print("Preparación actual (s)", time.perf_counter() - inicio, flush=True)
    tiempos = []
    conteos = Counter()
    descartadas = []
    for par in registro["pares"]:
        extremos = [par["origen"], par["destino"]]
        nodos, ajustes = ox.distance.nearest_nodes(grafo, X=[p[0] for p in extremos],
                                                  Y=[p[1] for p in extremos], return_dist=True)
        assert max(ajustes) <= MAX_AJUSTE_M
        inicio = time.perf_counter()
        try:
            resultado = comparar(preparada, *nodos, *ajustes)
        except nx.NetworkXNoPath:
            assert par["estado"] == "desconectado"
            conteos["desconectado"] += 1
            continue
        segundos = time.perf_counter() - inicio
        if par["id"] == "piloto":
            print("Piloto", resultado["feature"]["properties"], flush=True)
            continue
        tiempos.append(segundos)
        estado = resultado["estado"]
        conteos[estado] += 1
        if estado in ("disponible", "coincidente"):
            assert par["estado"] == "alternativa"
        elif par["estado"] == "alternativa":
            descartadas.append(par["id"])
    print("Muestra actual", conteos, "Descartadas", descartadas)
    print("Mediana y máximo de cálculo, pares conectados (s)", statistics.median(tiempos), max(tiempos))


if __name__ == "__main__":
    main()
