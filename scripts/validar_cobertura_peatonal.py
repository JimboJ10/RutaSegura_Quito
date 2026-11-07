"""Comparación offline, sin escribir grafos ni cambiar FastAPI.

Ejecutar desde la raíz con el Python del backend. --reanudar conserva las peticiones
ya registradas si coinciden la semilla, el código y todos los archivos de entrada.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from contextlib import ExitStack
import csv
import gzip
import json
import math
from pathlib import Path
import random
import statistics
import sys
import time

import networkx as nx
import numpy as np
import osmnx as ox
from shapely.geometry import Point, shape

from auditar_acceso_peatonal import (
    ROOT, GRAFOS, CAPAS, SALIDA, EVIDENCIA, CASOS, CINCO,
    hash_archivo, guardar_json, ids_osm,
)
from ensayar_grafo_peatonal import crear_app
from geojson import partes_arista

SEMILLA = 20261104
NUM_PARES = 100
DESTINO = ROOT / "backend/evidencias/validacion-cobertura"


def muestrear(capa, n=NUM_PARES, semilla=SEMILLA):
    """Cuotas por cuadrícula, independientes del grafo; no descarta puntos sin cobertura."""
    rng = random.Random(semilla)
    cells = sorted(capa["features"], key=lambda f: (f["properties"]["cx"], f["properties"]["cy"]))
    polygons = [shape(f["geometry"]) for f in cells]
    if not cells or any(p.is_empty or p.area <= 0 for p in polygons):
        raise ValueError("Cuadrículas vacías o inválidas")

    def quotas():
        ordered = []
        while len(ordered) < n:
            cycle = list(range(len(cells)))
            rng.shuffle(cycle)
            ordered.extend(cycle)
        return ordered[:n]

    def point(i):
        p = polygons[i]
        west, south, east, north = p.bounds
        for _ in range(100000):
            xy = (rng.uniform(west, east), rng.uniform(south, north))
            if p.covers(Point(xy)):
                return list(xy)
        raise RuntimeError("No se pudo muestrear una cuadrícula")

    a, b = quotas(), quotas()
    # No modificar cuotas ni condicionar por distancia a la red. Pares de celdas
    # iguales son válidos; el endpoint decide si caen en el mismo nodo.
    return [{"id": f"muestra_{i + 1:03d}", "grupo": "muestra",
             "origen": point(ca), "destino": point(cb),
             "celdas": [[cells[c]["properties"][k] for k in ("cx", "cy")] for c in (ca, cb)]}
            for i, (ca, cb) in enumerate(zip(a, b))]


def componentes(G):
    comps = sorted(nx.strongly_connected_components(G), key=lambda c: (-len(c), min(c)))
    asignacion = {n: i for i, c in enumerate(comps) for n in c}
    return comps, asignacion


def estadisticas_red(G, original=None):
    comps, _ = componentes(G)
    mayor = comps[0]
    longitud = sum(float(d["longitud_m"]) for *_, d in G.edges(data=True))
    lm = sum(float(d["longitud_m"]) for u, v, d in G.edges(data=True) if u in mayor and v in mayor)
    nn = len(original) if original is not None else len(G)
    ll = sum(float(d["longitud_m"]) for *_, d in original.edges(data=True)) if original is not None else longitud
    return {"nodos": len(G), "aristas": G.number_of_edges(),
            "componentes_fuertes": len(comps), "componentes_debiles": nx.number_weakly_connected_components(G),
            "mayor_scc_nodos": len(mayor), "longitud_dirigida_m": longitud, "mayor_scc_longitud_m": lm,
            "nodos_conservados_pct_original": 100 * len(G) / nn,
            "longitud_conservada_pct_original": 100 * longitud / ll,
            "mayor_scc_nodos_pct_original": 100 * len(mayor) / nn,
            "mayor_scc_longitud_pct_original": 100 * lm / ll,
            "mayor_scc_nodos_pct_filtrado": 100 * len(mayor) / len(G),
            "mayor_scc_longitud_pct_filtrado": 100 * lm / longitud}


def leer_decisiones(modo):
    with gzip.open(EVIDENCIA / f"{modo}-aristas.csv.gz", "rt", encoding="utf-8") as f:
        return {(int(r["u"]), int(r["v"]), int(r["key"])):
                {"estado": r["estado"], "motivos": json.loads(r["motivos_json"])} for r in csv.DictReader(f)}


def analisis_topologico(G, H, decisiones, tags):
    comps, asignacion = componentes(H)
    # Cociente exclusivamente analítico: aristas inciertas entre componentes.
    # No contiene aristas prohibidas y nunca se usa para calcular itinerarios.
    grupos = [set(c) for c in comps]
    for n in sorted(set(G) - set(H)):
        asignacion[n] = len(grupos)
        grupos.append({n})
    meta = nx.DiGraph()
    meta.add_nodes_from(range(len(grupos)))
    directas = defaultdict(set)
    incidencias = defaultdict(list)
    por_motivo = defaultdict(set)
    relaciones = Counter()
    fronteras = defaultdict(list)
    for edge, info in decisiones.items():
        u, v, k = edge
        a, b = asignacion[u], asignacion[v]
        if info["estado"] in ("restringida", "revision") and a != b:
            fronteras[a].append(edge)
            fronteras[b].append(edge)
        if info["estado"] != "revision":
            continue
        refs = {m[2] for m in info["motivos"] if m[0] == "revision"}
        if a != b:
            meta.add_edge(a, b)
        relacion = "dentro_misma_scc" if a == b else ("con_nodo_retirado" if u not in H or v not in H else "entre_scc_conservadas")
        relaciones[relacion] += 1
        for _, motivo, ref in info["motivos"]:
            if _ == "revision":
                por_motivo[motivo].add(edge)
        for ref in refs:
            incidencias[ref].append(edge)
            if len(refs) == 1 and a != b:
                directas[ref].add((a, b))

    potencial = nx.descendants(meta, 0).intersection(nx.ancestors(meta, 0)) | {0}
    fuentes = []
    for ref, edges in incidencias.items():
        ensayo = nx.DiGraph()
        ensayo.add_node(0)
        ensayo.add_edges_from(directas[ref])
        conectadas = nx.descendants(ensayo, 0).intersection(nx.ancestors(ensayo, 0))
        beneficio = sum(len(grupos[c]) for c in conectadas)
        tipo, ident = ref.split("/")
        etiquetas = tags["vias" if tipo == "way" else "nodos"].get(ident, {})
        affected = set(n for e in edges for n in e[:2])
        xs = [float(G.nodes[n]["x"]) for n in affected]
        ys = [float(G.nodes[n]["y"]) for n in affected]
        fuentes.append({"fuente": ref, "tags": etiquetas, "aristas": edges,
                        "centro": [sum(xs) / len(xs), sum(ys) / len(ys)],
                        "nodos_recuperables_si_solo_esta_fuente_se_autorizara": beneficio,
                        "componentes_enlazadas_individualmente": sorted(conectadas),
                        "componentes_afectadas": sorted({asignacion[n] for n in affected})})
    fuentes.sort(key=lambda f: (-f["nodos_recuperables_si_solo_esta_fuente_se_autorizara"], -len(f["aristas"]), f["fuente"]))

    resumen_comps, geo = [], []
    limites = [min(float(d["x"]) for _, d in G.nodes(data=True)), min(float(d["y"]) for _, d in G.nodes(data=True)),
               max(float(d["x"]) for _, d in G.nodes(data=True)), max(float(d["y"]) for _, d in G.nodes(data=True))]
    for i, c in enumerate(comps):
        sg = H.subgraph(c)
        xs = [float(H.nodes[n]["x"]) for n in c]
        ys = [float(H.nodes[n]["y"]) for n in c]
        centro = [sum(xs) / len(xs), sum(ys) / len(ys)]
        reasons = Counter()
        fuentes_frontera = Counter()
        # La frontera de la SCC principal se conserva en el registro, no se usa
        # como atribución causal exclusiva: varias restricciones pueden actuar juntas.
        for e in set(fronteras[i]):
            for state, motivo, ref in decisiones[e]["motivos"]:
                if state in ("revision", "restringida"):
                    reasons[state + "/" + motivo] += 1
                    fuentes_frontera[ref] += 1
        names = Counter()
        for *_, d in sg.edges(data=True):
            for name in d.get("name", []) if isinstance(d.get("name"), list) else [d.get("name")]:
                if name:
                    names[name] += 1
        registro = {"id": i, "nodos": len(c), "aristas": sg.number_of_edges(),
                    "longitud_m": sum(float(d["longitud_m"]) for *_, d in sg.edges(data=True)),
                    "centro": centro, "bbox": [min(xs), min(ys), max(xs), max(ys)],
                    "sector": ("norte" if centro[1] >= (limites[1] + limites[3]) / 2 else "sur") + "-" +
                              ("este" if centro[0] >= (limites[0] + limites[2]) / 2 else "oeste"),
                    "nombres_osm": [n for n, _ in names.most_common(5)],
                    "frontera_aristas_excluidas": sorted(set(fronteras[i])),
                    "motivos_frontera": dict(reasons), "fuentes_frontera": dict(fuentes_frontera),
                    "alcanzaria_principal_sin_vetos_si_todas_inciertas_se_autorizaran": i in potencial}
        resumen_comps.append(registro)
        if i:
            coords = [part for u, v, d in sg.edges(data=True) for part in partes_arista(H, u, v, d)]
            geo.append({"type": "Feature", "properties": registro,
                        "geometry": {"type": "MultiLineString", "coordinates": coords}})
    # Motivos por arista, sin duplicar las dos apariciones de un nodo en su registro.
    motivos = {}
    for razon, edges in por_motivo.items():
        motivos[razon] = {"aristas": len(edges),
                          "longitud_m": sum(float(G[u][v][k]["longitud_m"]) for u, v, k in edges),
                          "conectan_distintos_grupos": sum(asignacion[u] != asignacion[v] for u, v, _ in edges)}
    return {"componentes": resumen_comps, "fuentes_inciertas_priorizadas": fuentes,
            "inciertas_por_motivo": motivos, "inciertas_por_relacion": dict(relaciones),
            "cota_topologica_sin_prohibidas": {"nodos_alcanzables_ida_vuelta_principal": sum(len(grupos[i]) for i in potencial),
                "scc_filtradas_reunibles": sum(i < len(comps) for i in potencial),
                "nodos_retirados_reunibles": sum(len(grupos[i]) for i in potencial if i >= len(comps))}}, geo


def pares_diagnosticos(G, H):
    comps, _ = componentes(H)
    mayor = H.subgraph(comps[0]).copy()
    pares = []
    for i, c in enumerate(comps[1:11], 1):
        centro = [statistics.mean(float(H.nodes[n][key]) for n in c) for key in ("x", "y")]
        n = min(c, key=lambda n: (float(H.nodes[n]["x"]) - centro[0]) ** 2 + (float(H.nodes[n]["y"]) - centro[1]) ** 2)
        a = [float(H.nodes[n][key]) for key in ("x", "y")]
        destino = ox.distance.nearest_nodes(mayor, X=a[0], Y=a[1])
        b = [float(H.nodes[destino][key]) for key in ("x", "y")]
        pares.append({"id": f"isla_{i:02d}", "grupo": "islas", "scc": i, "origen": a, "destino": b})
    pares.extend({"id": nombre, "grupo": "conocidos", "origen": list(a), "destino": list(b)} for nombre, (a, b) in CASOS.items())
    return pares


def estado_respuesta(status, body, ajustes, nodos):
    if status == 200:
        return "evaluable"
    if status == 422:
        detail = body.get("detail", "")
        if max(ajustes) > 300 and isinstance(detail, str) and "demasiado lejos" in detail:
            return "fuera_cobertura"
        if nodos[0] == nodos[1] and isinstance(detail, str) and "mismo nodo" in detail:
            return "mismo_nodo"
        if detail == "No existe una ruta conectada.":
            return "sin_camino"
    return "error_tecnico"


def evaluar(client, par, version, snap, decisiones, captura):
    datos = {"origen": dict(zip(("lon", "lat"), par["origen"])),
             "destino": dict(zip(("lon", "lat"), par["destino"]))}
    captura.clear()
    out = {"id": par["id"], "grupo": par["grupo"], "version": version,
           "origen": par["origen"], "destino": par["destino"], **snap}
    inicio = time.perf_counter()
    try:
        response = client.post("/rutas", json=datos)
        out["tiempo_total_s"] = time.perf_counter() - inicio
        body = response.json()
        out["http"] = response.status_code
        out["estado"] = estado_respuesta(response.status_code, body, snap["ajustes_m"], snap["nodos"])
        out["tiempo_algoritmo_s"] = captura.get("tiempo_s")
        if out["estado"] != "evaluable":
            out["detalle"] = body.get("detail")
            if out["estado"] == "sin_camino":
                assert not nx.has_path(client.app.state.grafo, *snap["nodos"])
            return out
        assert max(snap["ajustes_m"]) <= 300
        assert [f["properties"]["id"] for f in body["features"]] == ["corta", "historica", "lightgbm"]
        exactas = captura["rutas"]
        geometries, routes = [], {}
        for feature, (metodo, ruta) in zip(body["features"], exactas, strict=True):
            assert feature["properties"]["id"] == metodo
            distance = ruta["distancia_m"]
            assert distance > 0 and distance <= exactas[0][1]["distancia_m"] * 1.15 + 1e-6
            assert abs(feature["properties"]["distancia_km"] * 1000 - distance) <= .051
            assert all(math.isfinite(ruta[k]) and ruta[k] >= 0 for k in ("indice_hist", "indice_ml"))
            geom = shape(feature["geometry"])
            assert geom.is_valid and not geom.is_empty
            lines = feature["geometry"]["coordinates"]
            assert all(a[-1] == b[0] for a, b in zip(lines, lines[1:]))
            g = client.app.state.grafo
            assert lines[0][0] == [g.nodes[snap["nodos"][0]][k] for k in ("x", "y")]
            assert lines[-1][-1] == [g.nodes[snap["nodos"][1]][k] for k in ("x", "y")]
            if not any(geom.equals(existing) for existing in geometries):
                geometries.append(geom)
            edges = [(u, v, next(k for k, value in g[u][v].items() if value is d)) for u, v, d in ruta["aristas"]]
            vets = [e for e in edges if decisiones[e]["estado"] == "restringida"]
            doubts = [e for e in edges if decisiones[e]["estado"] == "revision"]
            if version == "filtrado":
                assert not vets and not doubts
            routes[metodo] = {"distancia_m": distance, "desvio_pct": 100 * (distance / exactas[0][1]["distancia_m"] - 1),
                             "aristas": edges, "restringidas": vets, "inciertas": doubts,
                             "indice_historico": ruta["indice_hist"], "indice_lightgbm": ruta["indice_ml"]}
        out.update(rutas=routes, geometrias_distintas=len(geometries), verificaciones_correctas=True)
    except Exception as exc:
        out.update(estado="error_tecnico", detalle=f"{type(exc).__name__}: {exc}", tiempo_total_s=time.perf_counter() - inicio)
    return out


def resumen_pares(registros):
    resumen = {}
    for grupo in ("muestra", "islas", "conocidos"):
        datos = [r for r in registros if r["grupo"] == grupo]
        versions = {}
        for version in ("original", "filtrado"):
            records = [r for r in datos if r["version"] == version]
            validos = [r for r in records if r["estado"] == "evaluable"]
            t = [r["tiempo_total_s"] for r in validos]
            versions[version] = {"pares": len(records), "estados": dict(Counter(r["estado"] for r in records)),
                "evaluables_pct": 100 * len(validos) / len(records) if records else None,
                "geometrias_distintas": dict(Counter(r["geometrias_distintas"] for r in validos)),
                "tiempo_mediana_s": statistics.median(t) if t else None,
                "tiempo_p95_s": float(np.percentile(t, 95)) if t else None,
                "tiempo_max_s": max(t) if t else None,
                "pares_con_ruta_restringida": sum(any(v["restringidas"] for v in r["rutas"].values()) for r in validos),
                "pares_con_ruta_incierta": sum(any(v["inciertas"] for v in r["rutas"].values()) for r in validos)}
        lookup = {(r["id"], r["version"]): r for r in datos}
        transitions, perdidos, comunes = Counter(), [], []
        for ident in sorted({r["id"] for r in datos}):
            a, b = [lookup[ident, v] for v in ("original", "filtrado")]
            transitions[a["estado"] + " -> " + b["estado"]] += 1
            if a["estado"] == "evaluable" and b["estado"] != "evaluable":
                perdidos.append({"id": ident, "motivo": b["estado"]})
            if a["estado"] == b["estado"] == "evaluable":
                comunes.append((a, b))
        impacto = {}
        for metodo in ("corta", "historica", "lightgbm"):
            delta = [b["rutas"][metodo]["distancia_m"] - a["rutas"][metodo]["distancia_m"] for a, b in comunes]
            pct = [100 * d / a["rutas"][metodo]["distancia_m"] for d, (a, _) in zip(delta, comunes)]
            impacto[metodo] = {"pares_comunes": len(comunes), "cambiaron_mas_1m": sum(abs(v) > 1 for v in delta),
                               "delta_m_mediana": statistics.median(delta) if delta else None,
                               "delta_m_max": max(delta) if delta else None,
                               "delta_pct_mediana": statistics.median(pct) if pct else None,
                               "delta_pct_max": max(pct) if pct else None}
        resumen[grupo] = {"versiones": versions, "transiciones": dict(transitions), "perdidos": perdidos,
                          "distancias_pares_comunes": impacto,
                          "tiempos_mediana_pares_comunes": {v: statistics.median(p[j]["tiempo_total_s"] for p in comunes) if comunes else None
                              for j, v in enumerate(("original", "filtrado"))}}
    return resumen


def ejecutar(destino=DESTINO, reanudar=False):
    import api
    from fastapi.testclient import TestClient
    inputs = [*GRAFOS.values(), *CAPAS.values(), *[SALIDA / f"quito_{m}_peatonal_filtrado.graphml" for m in GRAFOS],
              *[EVIDENCIA / f"{m}-aristas.csv.gz" for m in GRAFOS], EVIDENCIA / "etiquetas-osm.json.gz"]
    manifest = {"semilla": SEMILLA, "pares_por_cobertura": NUM_PARES,
                "sha256_codigo": hash_archivo(__file__),
                "sha256_entradas": {str(p.relative_to(ROOT)): hash_archivo(p) for p in inputs}}
    if destino.exists():
        if not reanudar or json.loads((destino / "manifest.json").read_text(encoding="utf-8")) != manifest:
            raise SystemExit("Salida existente o entradas/código diferentes; no se sobrescribe. Use nueva carpeta o --reanudar.")
    else:
        destino.mkdir(parents=True)
        guardar_json(destino / "manifest.json", manifest)
    with gzip.open(EVIDENCIA / "etiquetas-osm.json.gz", "rt", encoding="utf-8") as f:
        tags = json.load(f)
    captura = {}
    funcion = api.calcular_recorridos

    def observar(*args):
        start = time.perf_counter()
        try:
            rutas = funcion(*args)
            captura["rutas"] = rutas
            return rutas
        finally:
            captura["tiempo_s"] = time.perf_counter() - start

    api.calcular_recorridos = observar
    try:
        for modo, path in GRAFOS.items():
            print(f"Cargando {modo}, originales y candidatos...", flush=True)
            with ExitStack() as stack:
                clients = {v: stack.enter_context(TestClient(crear_app(p), raise_server_exceptions=False)) for v, p in (
                    ("original", path), ("filtrado", SALIDA / f"quito_{modo}_peatonal_filtrado.graphml"))}
                G, H = [clients[v].app.state.grafo for v in ("original", "filtrado")]
                decisiones = leer_decisiones(modo)
                assert set(decisiones) == set(G.edges(keys=True))
                assert set(H.edges(keys=True)) == {e for e, d in decisiones.items() if d["estado"] not in ("revision", "restringida")}
                topology, geo = analisis_topologico(G, H, decisiones, tags)
                topology["redes"] = {"original": estadisticas_red(G), "filtrado": estadisticas_red(H, G)}
                guardar_json(destino / f"{modo}-conectividad.json", topology)
                guardar_json(destino / f"{modo}-componentes.geojson", {"type": "FeatureCollection", "features": geo})
                capa = json.loads(CAPAS[modo].read_text(encoding="utf-8-sig"))
                pares = muestrear(capa) + pares_diagnosticos(G, H)
                guardar_json(destino / f"{modo}-pares.json", pares)
                snaps = {}
                for version, g in (("original", G), ("filtrado", H)):
                    points = [xy for p in pares for xy in (p["origen"], p["destino"])]
                    nodes, dist = ox.distance.nearest_nodes(g, X=[p[0] for p in points], Y=[p[1] for p in points], return_dist=True)
                    snaps[version] = [{"nodos": [int(n) for n in nodes[i:i+2]], "ajustes_m": [float(d) for d in dist[i:i+2]]}
                                      for i in range(0, len(points), 2)]
                log = destino / f"{modo}-peticiones.jsonl"
                registros = [json.loads(line) for line in log.read_text(encoding="utf-8").splitlines()] if log.exists() else []
                hechas = {(r["id"], r["version"]) for r in registros}
                assert len(hechas) == len(registros)
                # Calentamiento idéntico, fuera de la medición. No se ajustan rutas ni umbrales.
                for version, client in clients.items():
                    client.post("/rutas", json={"origen": {"lon": -78.504, "lat": -.201}, "destino": {"lon": -78.486, "lat": -.184}})
                with log.open("a", encoding="utf-8") as out:
                    for i, par in enumerate(pares):
                        for version in (("original", "filtrado") if i % 2 == 0 else ("filtrado", "original")):
                            if (par["id"], version) in hechas:
                                continue
                            r = evaluar(clients[version], par, version, snaps[version][i], decisiones, captura)
                            out.write(json.dumps(r, ensure_ascii=False) + "\n")
                            out.flush()
                            registros.append(r)
                        if (i + 1) % 10 == 0 or i + 1 == len(pares):
                            print(f"{modo}: {i+1}/{len(pares)} pares comparados; errores técnicos=" + str(sum(r["estado"] == "error_tecnico" for r in registros)), flush=True)
                guardar_json(destino / f"{modo}-resumen.json", resumen_pares(registros))
                uso = Counter(tuple(e) for r in registros if r["version"] == "original" and r["estado"] == "evaluable"
                              for ruta in r["rutas"].values() for e in ruta["inciertas"])
                for fuente in topology["fuentes_inciertas_priorizadas"]:
                    fuente["usos_en_modalidades_originales"] = sum(uso[tuple(e)] for e in fuente["aristas"])
                guardar_json(destino / f"{modo}-conectividad.json", topology)
                print(modo, json.dumps(resumen_pares(registros)["muestra"]["transiciones"]), flush=True)
    finally:
        api.calcular_recorridos = funcion
    assert all(hash_archivo(ROOT / p) == h for p, h in manifest["sha256_entradas"].items())
    guardar_json(destino / "integridad.json", {"entradas_intactas": True, "archivos_verificados": len(inputs)})


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--salida", type=Path, default=DESTINO)
    parser.add_argument("--reanudar", action="store_true")
    args = parser.parse_args()
    ejecutar(args.salida.resolve(), args.reanudar)
