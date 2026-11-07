"""Auditoría offline y copias candidatas. Nunca cambia la configuración de FastAPI.

Desde la raíz: backend/.venv/Scripts/python.exe scripts/auditar_acceso_peatonal.py
Rechaza salidas existentes. Consulte backend/ACCESO_PEATONAL.md.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import csv
import gzip
import hashlib
import io
import json
from pathlib import Path
import sys

import networkx as nx
import osmnx as ox
from pyproj import Transformer, Geod
from shapely.geometry import shape, Point, MultiLineString
from shapely.ops import transform, unary_union

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from geojson import partes_arista, coleccion_geojson
from grafo import preparar_grafo
from rutas import calcular_recorridos

FUENTE = ROOT / "resultados/ampliacion/cache_osmnx/e275a3de6ac9e0fbd4a90530b29956a6a15357c6.json"
GRAFOS = {
    "demo": ROOT / "red_vial/quito_demo_con_predicciones.graphml",
    "ampliada": ROOT / "red_vial/ampliacion/quito_peatonal_ampliada_con_predicciones.graphml",
}
CAPAS = {
    "demo": ROOT / "resultados/predicciones_demo_junio2026.geojson",
    "ampliada": ROOT / "resultados/ampliacion/predicciones_99_celdas_junio2026.geojson",
}
SALIDA = ROOT / "red_vial/acceso_peatonal_v1"
EVIDENCIA = ROOT / "backend/evidencias/acceso"
CASOS = {
    "piloto": ((-78.504, -.201), (-78.486, -.184)),
    "norte_sur": ((-78.498, -.150), (-78.505, -.218)),
    "suroeste_noreste": ((-78.530, -.220), (-78.481, -.153)),
    "centro_este": ((-78.516, -.199), (-78.483, -.180)),
    "oeste_este": ((-78.532, -.186), (-78.481, -.188)),
}
CINCO = [1059162235, 149787548, 219886408, 431716070, 1171326264]
POSITIVOS = {"yes", "designated", "official", "permissive"}
NEGATIVOS = {"no", "private", "use_sidepath", "agricultural", "forestry", "military", "emergency"}
PEATONALES = {"footway", "pedestrian", "path", "steps", "living_street", "residential",
              "service", "unclassified", "road", "track", "primary", "primary_link",
              "secondary", "secondary_link", "tertiary", "tertiary_link", "corridor"}
BARRERAS_PASABLES = {"kerb", "bollard", "stile", "cycle_barrier", "entrance", "cattle_grid",
                      "bollard;kerb", "kerb;bollard", "no"}
RANGO = {"sin_restriccion_documentada": 0, "autorizacion_explicita": 1,
         "revision": 2, "restringida": 3}


def permiso(tags, nodo=False):
    """Política para tránsito peatonal público sin evaluar horarios ni permisos personales."""
    foot, access = tags.get("foot"), tags.get("access")
    if any(k.startswith(("foot:", "oneway:foot")) for k in tags):
        return "revision", "condicion_o_sentido_peatonal_no_evaluado"
    if foot is not None:
        if foot in POSITIVOS:
            if tags.get("opening_hours") or tags.get("locked") == "yes":
                return "revision", "horario_o_cierre_no_evaluado"
            return "autorizacion_explicita", f"foot={foot}"
        if foot in NEGATIVOS:
            return "restringida", f"foot={foot}"
        return "revision", f"foot={foot}"
    if any(k.startswith("access:") for k in tags):
        return "revision", "condicion_o_sentido_general_no_evaluado"
    if access in NEGATIVOS:
        return "restringida", f"access={access}_sin_excepcion_foot"
    if access is not None and access not in POSITIVOS:
        return "revision", f"access={access}_requiere_contexto"
    if tags.get("opening_hours") or tags.get("locked") == "yes":
        return "revision", "horario_o_cierre_no_evaluado"
    # No inferir acceso peatonal de psv, bus, bicycle ni motor_vehicle.
    if nodo:
        if access in POSITIVOS:
            return "autorizacion_explicita", f"access={access}"
        if tags.get("barrier") and tags["barrier"] not in BARRERAS_PASABLES:
            return "revision", f"barrier={tags['barrier']}_sin_permiso"
        return "sin_restriccion_documentada", "nodo_sin_restriccion_peatonal"
    if tags.get("highway") not in PEATONALES:
        return "revision", f"highway={tags.get('highway')}_sin_foot"
    if access in POSITIVOS:
        return "autorizacion_explicita", f"access={access}"
    return "sin_restriccion_documentada", "clase_vial_compatible_sin_prohibicion"


def ids_osm(datos):
    value = datos.get("osmid", [])
    return value if isinstance(value, list) else [value]


def par(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


class FuenteOSM:
    def __init__(self, datos):
        self.fecha = datos.get("osm3s", {}).get("timestamp_osm_base")
        self.nodos = {e["id"]: e for e in datos["elements"] if e["type"] == "node"}
        self.vias = {e["id"]: e for e in datos["elements"] if e["type"] == "way"}
        self.segmentos = defaultdict(list)
        for wid, way in self.vias.items():
            for u, v in zip(way["nodes"], way["nodes"][1:]):
                a, b = self.nodos[u], self.nodos[v]
                key = par((a["lon"], a["lat"]), (b["lon"], b["lat"]))
                self.segmentos[key].append((wid, u, v))

    def decidir(self, G, u, v, d):
        declaradas = set(ids_osm(d))
        vias, nodos, faltan = set(), set(), 0
        for linea in partes_arista(G, u, v, d):
            for a, b in zip(linea, linea[1:]):
                matches = [x for x in self.segmentos[par(a, b)] if x[0] in declaradas]
                if not matches:
                    faltan += 1
                for wid, na, nb in matches:
                    vias.add(wid)
                    nodos.update((na, nb))
        motivos = []
        if faltan or not declaradas or declaradas - vias:
            motivos.append(("revision", "sin_trazabilidad_osm_completa", "arista"))
        for wid in sorted(vias):
            estado, razon = permiso(self.vias[wid].get("tags", {}))
            motivos.append((estado, razon, f"way/{wid}"))
        for nid in sorted(nodos):
            tags = self.nodos[nid].get("tags", {})
            if any(k in tags for k in ("access", "foot", "barrier", "opening_hours", "locked")) or any(
                k.startswith(("foot:", "access:", "oneway:foot")) for k in tags
            ):
                estado, razon = permiso(tags, nodo=True)
                motivos.append((estado, razon, f"node/{nid}"))
        estado = max((m[0] for m in motivos), key=RANGO.get)
        return {"estado": estado, "motivos": motivos, "vias": sorted(vias),
                "nodos_osm": sorted(nodos), "pares_sin_fuente": faltan}


def filtrar(G, fuente):
    """Copia exacta menos aristas excluidas y nodos aislados; conserva todas las componentes."""
    decisiones = {(u, v, k): fuente.decidir(G, u, v, d) for u, v, k, d in G.edges(keys=True, data=True)}
    copia = G.copy()
    copia.remove_edges_from([e for e, info in decisiones.items() if RANGO[info["estado"]] >= 2])
    aislados = list(nx.isolates(copia))
    copia.remove_nodes_from(aislados)
    return copia, decisiones, aislados


def hash_archivo(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def metricas(G, capa):
    weak = sorted(map(len, nx.weakly_connected_components(G)), reverse=True)
    strong = sorted(map(len, nx.strongly_connected_components(G)), reverse=True)
    poligonos = [shape(f["geometry"]) for f in capa["features"]]
    geometria = unary_union(poligonos)
    nodos = [(d["x"], d["y"]) for _, d in G.nodes(data=True)]
    lineas = [p for u, v, d in G.edges(data=True) for p in partes_arista(G, u, v, d)]
    red = MultiLineString(lineas)
    proy = Transformer.from_crs(4326, 32717, always_xy=True).transform
    # Muestreo fijo de 100 m en UTM: alcance de ajuste a nodos, no acceso caminable.
    import numpy as np
    area_capa = transform(proy, geometria)
    oeste, sur, este, norte = area_capa.bounds
    puntos = [Point(x, y) for x in np.arange(oeste + 50, este, 100)
              for y in np.arange(sur + 50, norte, 100) if area_capa.covers(Point(x, y))]
    inv = Transformer.from_crs(32717, 4326, always_xy=True)
    xs, ys = inv.transform([p.x for p in puntos], [p.y for p in puntos])
    _, distancias = ox.distance.nearest_nodes(G, X=xs, Y=ys, return_dist=True)
    return {"nodos": len(G), "aristas_dirigidas": G.number_of_edges(),
            "componentes_debiles": len(weak), "mayor_debil": weak[0],
            "componentes_fuertes": len(strong), "mayor_fuerte": strong[0],
            "tamanos_componentes_debiles": weak, "tamanos_componentes_fuertes": strong,
            "longitud_dirigida_km": sum(float(d["longitud_m"]) for *_, d in G.edges(data=True)) / 1000,
            "bbox_nodos": [min(p[0] for p in nodos), min(p[1] for p in nodos), max(p[0] for p in nodos), max(p[1] for p in nodos)],
            "celdas_con_arista": sum(red.intersects(p) for p in poligonos),
            "area_predictiva_km2": abs(Geod(ellps="WGS84").geometry_area_perimeter(geometria)[0]) / 1e6,
            "muestras_100m": len(puntos), "muestras_ajuste_300m": int(sum(distancias <= 300)),
            "area_aprox_ajuste_300m_km2": float(sum(distancias <= 300) / len(puntos) * area_capa.area / 1e6)}


def evaluar_casos(G, decisiones, modo, fase, features):
    preparar_grafo(G)  # Fórmulas existentes, medianas calculadas sobre la red de cada ensayo.
    resultados = {}
    for caso, (a, b) in CASOS.items():
        inicio, da = ox.distance.nearest_nodes(G, X=a[0], Y=a[1], return_dist=True)
        fin, db = ox.distance.nearest_nodes(G, X=b[0], Y=b[1], return_dist=True)
        info = {"ajustes_m": [float(da), float(db)], "nodos": [int(inicio), int(fin)]}
        resultados[caso] = info
        if max(da, db) > 300 or inicio == fin:
            info.update(status=422, motivo="ajuste_mayor_300m" if max(da, db) > 300 else "mismo_nodo")
            continue
        try:
            rutas = calcular_recorridos(G, inicio, fin)
        except nx.NetworkXNoPath:
            info.update(status=422, motivo="sin_camino")
            continue
        geo = coleccion_geojson(G, rutas, inicio, fin, da, db)
        info.update(status=200, rutas={})
        firmas = []
        for (metodo, ruta), feature in zip(rutas, geo["features"]):
            aristas = [(u, v, next(k for k, datos in G[u][v].items() if datos is d)) for u, v, d in ruta["aristas"]]
            excluidas = [e for e in aristas if RANGO[decisiones[e]["estado"]] >= 2]
            assert ruta["distancia_m"] <= rutas[0][1]["distancia_m"] * 1.15 + 1e-6
            if fase == "despues":
                assert not excluidas
            geometria = feature["geometry"]
            firma = json.dumps(geometria, sort_keys=True)
            firmas.append(firma)
            info["rutas"][metodo] = {"distancia_km": ruta["distancia_m"] / 1000,
                "indicadores": [ruta["indice_hist"], ruta["indice_ml"]],
                "aristas": aristas, "aristas_excluidas": excluidas,
                "igual_corta": firma == firmas[0],
                "pares_sin_osm": sum(decisiones[e]["pares_sin_fuente"] for e in aristas)}
            feature["properties"].update(cobertura=modo, fase=fase, caso=caso)
            features.append(feature)
        info["geometrias_distintas"] = len(set(firmas))
    return resultados


def guardar_json(path, valor):
    datos = json.dumps(valor, ensure_ascii=False, indent=2).encode("utf-8")
    path.write_bytes(gzip.compress(datos, mtime=0) if path.suffix == ".gz" else datos)


def escribir_hallazgos(evidencia):
    """Índice de causas de los cambios, derivado de los registros completos por arista."""
    reporte = json.loads((evidencia / "informe.json").read_text(encoding="utf-8"))
    extra = {}
    for modo, data in reporte["coberturas"].items():
        with gzip.open(evidencia / f"{modo}-aristas.csv.gz", "rt", encoding="utf-8") as f:
            filas = {(int(r["u"]), int(r["v"]), int(r["key"])): r for r in csv.DictReader(f)}
        fuentes = defaultdict(set)
        detalles = {"rutas_antes_afectadas": {}, "nodo_origen_centro_este": []}
        for e, fila in filas.items():
            motivos = json.loads(fila["motivos_json"])
            for estado, _, ref in motivos:
                if RANGO[estado] >= 2:
                    fuentes[estado + "/" + ref.split("/")[0]].add(ref)
            if data["rutas_antes"]["centro_este"]["nodos"][0] in e[:2]:
                detalles["nodo_origen_centro_este"].append({"arista": e, "estado": fila["estado"], "motivos": motivos})
        for caso, r in data["rutas_antes"].items():
            for metodo, ruta in r.get("rutas", {}).items():
                if ruta["aristas_excluidas"]:
                    detalles["rutas_antes_afectadas"][caso + "/" + metodo] = [
                        {"arista": e, "motivos": [m for m in json.loads(filas[tuple(e)]["motivos_json"]) if RANGO[m[0]] >= 2]}
                        for e in ruta["aristas_excluidas"]]
        detalles["fuentes_por_estado"] = {k: len(v) for k, v in fuentes.items()}
        detalles["humboldt"] = [r for r in filas.values() if 1075574449 in json.loads(r["osmid"])]
        extra[modo] = detalles
    guardar_json(evidencia / "hallazgos-detallados.json", extra)


def ejecutar(salida=SALIDA, evidencia=EVIDENCIA):
    # No sobrescribir siquiera un candidato anterior. Nueva carpeta para cada revisión.
    if salida.exists() or evidencia.exists():
        raise SystemExit("La salida ya existe. Use --salida y --evidencia con carpetas nuevas.")
    entrada = [FUENTE, *GRAFOS.values(), *CAPAS.values()]
    hashes = {str(p.relative_to(ROOT)): hash_archivo(p) for p in entrada}
    fuente = FuenteOSM(json.loads(FUENTE.read_text(encoding="utf-8")))
    salida.mkdir(parents=True)
    evidencia.mkdir(parents=True)
    resumen = {"politica": "peatonal-v1", "fecha_osm": fuente.fecha, "sha256_entradas": hashes,
               "coberturas": {}, "sha256_salidas": {}}
    features, relevantes, nodos_relevantes = [], set(), set()
    cinco = {}
    geod = Geod(ellps="WGS84")
    for i in CINCO:
        nodes = [fuente.nodos[n] for n in fuente.vias[i]["nodes"]]
        cinco[str(i)] = {"tags": fuente.vias[i]["tags"], "nodos_osm": fuente.vias[i]["nodes"],
                        "longitud_via_osm_m": geod.line_length([n["lon"] for n in nodes], [n["lat"] for n in nodes]),
                        "coberturas": {}}
    for modo, path in GRAFOS.items():
        print(f"Auditando {modo}...", flush=True)
        G = ox.load_graphml(path)
        H, decisiones, aislados = filtrar(G, fuente)
        # Verificación independiente de conservación exacta de atributos y geometrías.
        assert all(d == G[u][v][k] for u, v, k, d in H.edges(keys=True, data=True))
        assert all(d == G.nodes[n] for n, d in H.nodes(data=True))
        destino = salida / f"quito_{modo}_peatonal_filtrado.graphml"
        ox.save_graphml(H, filepath=destino)
        resumen["sha256_salidas"][str(destino.relative_to(ROOT))] = hash_archivo(destino)
        capa = json.loads(CAPAS[modo].read_text(encoding="utf-8-sig"))
        info = {"antes": metricas(G, capa), "despues": metricas(H, capa),
                "estados": dict(Counter(x["estado"] for x in decisiones.values())),
                "nodos_aislados_retirados": aislados,
                "motivos_exclusion": dict(Counter(m[1] for x in decisiones.values() for m in x["motivos"] if RANGO[m[0]] >= 2))}
        resumen["coberturas"][modo] = info
        info["rutas_antes"] = evaluar_casos(G, decisiones, modo, "antes", features)
        info["rutas_despues"] = evaluar_casos(H, decisiones, modo, "despues", features)
        for wid in CINCO:
            edges = [(u, v, k) for u, v, k, d in G.edges(keys=True, data=True) if wid in ids_osm(d)]
            usos = [f"{caso}/{metodo}" for caso, r in info["rutas_antes"].items() for metodo, s in r.get("rutas", {}).items()
                    if set(edges).intersection(map(tuple, s["aristas"]))]
            cinco[str(wid)]["coberturas"][modo] = {"aristas": edges,
                "longitud_dirigida_m": sum(G[u][v][k]["longitud_m"] for u, v, k in edges), "rutas_antes": usos}
        with io.StringIO(newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["u", "v", "key", "osmid", "longitud_m", "estado", "motivos_json"])
            for (u, v, k), x in decisiones.items():
                writer.writerow([u, v, k, json.dumps(ids_osm(G[u][v][k])), G[u][v][k]["longitud_m"], x["estado"], json.dumps(x["motivos"], ensure_ascii=False)])
                relevantes.update(x["vias"])
                nodos_relevantes.update(n for n in x["nodos_osm"] if fuente.nodos[n].get("tags"))
            (evidencia / f"{modo}-aristas.csv.gz").write_bytes(gzip.compress(f.getvalue().encode("utf-8"), mtime=0))
        # Geometrías retiradas, para superponer a las rutas en la revisión visual.
        retiradas = [{"type": "Feature", "properties": {"u": u, "v": v, "key": k, "estado": x["estado"], "vias": x["vias"]},
                      "geometry": {"type": "MultiLineString", "coordinates": partes_arista(G, u, v, G[u][v][k])}}
                     for (u, v, k), x in decisiones.items() if RANGO[x["estado"]] >= 2]
        guardar_json(evidencia / f"{modo}-retiradas.geojson", {"type": "FeatureCollection", "features": retiradas})
        print(modo, info["estados"], "conservadas", H.number_of_edges(), flush=True)
    resumen["entradas_intactas"] = all(hash_archivo(p) == hashes[str(p.relative_to(ROOT))] for p in entrada)
    assert resumen["entradas_intactas"]
    guardar_json(evidencia / "informe.json", resumen)
    guardar_json(evidencia / "cinco-vias.json", cinco)
    guardar_json(evidencia / "rutas.geojson", {"type": "FeatureCollection", "features": features})
    guardar_json(evidencia / "etiquetas-osm.json.gz", {"fecha": fuente.fecha,
                 "vias": {i: fuente.vias[i]["tags"] for i in sorted(relevantes)},
                 "nodos": {i: fuente.nodos[i]["tags"] for i in sorted(nodos_relevantes)}})
    escribir_hallazgos(evidencia)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=SALIDA)
    parser.add_argument("--evidencia", type=Path, default=EVIDENCIA)
    args = parser.parse_args()
    ejecutar(args.salida.resolve(), args.evidencia.resolve())
