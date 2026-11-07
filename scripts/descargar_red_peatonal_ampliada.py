r"""Descarga y audita la red peatonal base del piloto ampliado de RutaInformada Quito.

Ejecución desde la raíz del repositorio:
    .\backend\.venv\Scripts\python.exe scripts\descargar_red_peatonal_ampliada.py

Este script NO modifica el grafo activo ni ejecuta predicciones.
Requiere conexión a Internet para obtener datos de OpenStreetMap vía Overpass.
"""
from __future__ import annotations

import json
from pathlib import Path

import networkx as nx
import osmnx as ox

ROOT = Path(__file__).resolve().parents[1]
PREDICCIONES = ROOT / "resultados" / "ampliacion" / "predicciones_99_celdas_junio2026.geojson"
SALIDA_DIR = ROOT / "red_vial" / "ampliacion"
GRAFO_SALIDA = SALIDA_DIR / "quito_peatonal_ampliada_base.graphml"
INFORME_SALIDA = ROOT / "resultados" / "ampliacion" / "auditoria_red_peatonal_base.json"

# Zona de análisis: (oeste, sur, este, norte) — EPSG:4326.
BBOX = (-78.54, -0.23, -78.47, -0.14)


def main() -> None:
    if not PREDICCIONES.is_file():
        raise SystemExit(f"No existe la capa predictiva: {PREDICCIONES}")
    with PREDICCIONES.open("r", encoding="utf-8") as f:
        capa = json.load(f)
    features = capa.get("features", [])
    if capa.get("type") != "FeatureCollection" or len(features) != 99:
        raise SystemExit("La capa de predicciones debe contener 99 features GeoJSON.")
    for f in features:
        p = f.get("properties", {})
        if p.get("periodo") != "2026-06" or "pred_historico" not in p or "pred_lightgbm_v2" not in p:
            raise SystemExit("Alguna cuadrícula carece del periodo o de los dos indicadores.")

    if GRAFO_SALIDA.exists():
        raise SystemExit(
            f"Ya existe {GRAFO_SALIDA}. No se sobrescribirá. "
            "Revisa ese archivo antes de volver a descargar."
        )

    SALIDA_DIR.mkdir(parents=True, exist_ok=True)
    INFORME_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    ox.settings.use_cache = True
    ox.settings.cache_folder = str(ROOT / "resultados" / "ampliacion" / "cache_osmnx")
    ox.settings.requests_timeout = 180
    print("Descargando red peatonal de OpenStreetMap para el BBOX:", BBOX, flush=True)
    # retain_all=True para no descartar componentes antes de auditarlos.
    G = ox.graph_from_bbox(
        BBOX,
        network_type="walk",
        simplify=True,
        retain_all=True,
    )
    if not isinstance(G, nx.MultiDiGraph):
        raise RuntimeError("OSMnx no devolvió un MultiDiGraph.")
    if not G.nodes or not G.edges:
        raise RuntimeError("La red descargada no contiene nodos o aristas.")
    crs = str(G.graph.get("crs", ""))
    if crs.upper() not in ("EPSG:4326", "EPSG: 4326"):
        raise RuntimeError(f"CRS no esperado: {crs}")
    weak = sorted((len(c) for c in nx.weakly_connected_components(G)), reverse=True)
    strong = sorted((len(c) for c in nx.strongly_connected_components(G)), reverse=True)
    lengths = [d.get("length") for _, _, _, d in G.edges(keys=True, data=True)]
    valid_lengths = sum(
        isinstance(x, (int, float)) and 0 < float(x) < float("inf")
        for x in lengths
    )
    reporte = {
        "proyecto": "RutaInformada Quito",
        "tipo": "red peatonal base sin indicadores predictivos",
        "bbox_wgs84_oeste_sur_este_norte": list(BBOX),
        "crs": crs,
        "nodos": G.number_of_nodes(),
        "aristas_dirigidas": G.number_of_edges(),
        "componentes_debilmente_conexas": len(weak),
        "nodos_componente_debil_mayor": weak[0],
        "componentes_fuertemente_conexas": len(strong),
        "nodos_componente_fuerte_mayor": strong[0],
        "aristas_con_longitud_valida": valid_lengths,
        "aristas_sin_longitud_valida": len(lengths) - valid_lengths,
        "cuadriculas_de_predicciones_disponibles": len(features),
        "limitaciones": [
            "No se han asociado puntuaciones a las aristas.",
            "No se ha verificado todavía la cobertura predictiva de cada segmento.",
            "No se ha integrado la red al backend ni validado rutas ampliadas.",
        ],
    }
    ox.save_graphml(G, filepath=GRAFO_SALIDA)
    INFORME_SALIDA.write_text(json.dumps(reporte, indent=2, ensure_ascii=False), encoding="utf-8")
    print("\nRed guardada:", GRAFO_SALIDA)
    print("Auditoría guardada:", INFORME_SALIDA)
    print(json.dumps(reporte, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
