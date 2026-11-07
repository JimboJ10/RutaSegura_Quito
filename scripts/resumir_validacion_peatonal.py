"""Deriva tablas, causas y geometrías de evidencia sin recalcular las rutas."""
from collections import Counter, defaultdict
import csv
import gzip
import json

import osmnx as ox

from auditar_acceso_peatonal import ROOT, GRAFOS, SALIDA, FUENTE, EVIDENCIA, CINCO, guardar_json
from validar_cobertura_peatonal import DESTINO, componentes, leer_decisiones
from geojson import partes_arista


def ejecutar(destino=DESTINO):
    with gzip.open(EVIDENCIA / "etiquetas-osm.json.gz", "rt", encoding="utf-8") as f:
        tags = json.load(f)
    fuente = json.loads(FUENTE.read_text(encoding="utf-8"))
    nodos_fuente = {n["id"]: [n["lon"], n["lat"]] for n in fuente["elements"] if n["type"] == "node"}
    resultado, features = {}, []
    for modo in GRAFOS:
        G = ox.load_graphml(GRAFOS[modo])
        H = ox.load_graphml(SALIDA / f"quito_{modo}_peatonal_filtrado.graphml")
        _, mapa_comp = componentes(H)
        decisiones = leer_decisiones(modo)
        topo = json.loads((destino / f"{modo}-conectividad.json").read_text(encoding="utf-8"))
        registros = [json.loads(line) for line in (destino / f"{modo}-peticiones.jsonl").read_text(encoding="utf-8").splitlines()]
        lookup = {(r["id"], r["version"]): r for r in registros}
        def causas(edges):
            refs = defaultdict(set)
            for edge in edges:
                for state, reason, ref in decisiones[tuple(edge)]["motivos"]:
                    if state in ("restringida", "revision"):
                        refs[(state, reason)].add(ref)
            return [{"estado": k[0], "motivo": k[1], "fuentes": sorted(v)} for k, v in refs.items()]

        d = {"perdidos": [], "mayores_cambios": [], "corredores": {}, "motivos_inciertos_usados": {},
             "prioridad_topologica": topo["fuentes_inciertas_priorizadas"][:20], "casos_conocidos": []}
        rows, candidatos = [], []
        for ident in sorted({r["id"] for r in registros}):
            a, b = [lookup[ident, v] for v in ("original", "filtrado")]
            row = {"id": ident, "grupo": a["grupo"], "origen_lon": a["origen"][0], "origen_lat": a["origen"][1],
                   "destino_lon": a["destino"][0], "destino_lat": a["destino"][1],
                   "estado_antes": a["estado"], "estado_despues": b["estado"],
                   "ajuste_origen_antes_m": a["ajustes_m"][0], "ajuste_destino_antes_m": a["ajustes_m"][1],
                   "ajuste_origen_despues_m": b["ajustes_m"][0], "ajuste_destino_despues_m": b["ajustes_m"][1],
                   "tiempo_antes_s": a["tiempo_total_s"], "tiempo_despues_s": b["tiempo_total_s"],
                   "geometrias_antes": a.get("geometrias_distintas"), "geometrias_despues": b.get("geometrias_distintas")}
            for metodo in ("corta", "historica", "lightgbm"):
                for version, record in (("antes", a), ("despues", b)):
                    row[f"{metodo}_{version}_m"] = record.get("rutas", {}).get(metodo, {}).get("distancia_m")
            rows.append(row)
            if a["grupo"] == "conocidos":
                d["casos_conocidos"].append(row)
            if a["estado"] == "evaluable" and b["estado"] != "evaluable":
                d["perdidos"].append({**row, "componentes_despues": [mapa_comp[n] for n in b["nodos"]],
                    "causas_en_rutas_originales": causas([e for route in a["rutas"].values() for e in route["aristas"]])})
            if a["grupo"] == "muestra" and a["estado"] == b["estado"] == "evaluable":
                delta = b["rutas"]["corta"]["distancia_m"] - a["rutas"]["corta"]["distancia_m"]
                candidatos.append({**row, "incremento_corta_m": delta,
                    "incremento_corta_pct": 100 * delta / a["rutas"]["corta"]["distancia_m"],
                    "mismos_nodos": a["nodos"] == b["nodos"],
                    "causas_corta_original": causas(a["rutas"]["corta"]["aristas"])})
        d["mayores_cambios"] = sorted(candidatos, key=lambda r: -r["incremento_corta_m"])[:5]
        for extra in d["mayores_cambios"]:
            for version in ("original", "filtrado"):
                record = lookup[extra["id"], version]
                for metodo, ruta in record["rutas"].items():
                    features.append({"type": "Feature", "properties": {"cobertura": modo, "id": extra["id"],
                        "version": version, "metodo": metodo, "distancia_m": ruta["distancia_m"]},
                        "geometry": {"type": "MultiLineString", "coordinates": [part for u, v, k in ruta["aristas"]
                                     for part in partes_arista(G, u, v, G[u][v][k])]}})
        with (destino / f"{modo}-pares-comparados.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(rows[0]))
            writer.writeheader()
            writer.writerows(rows)
        for wid in [*CINCO, 1075574449]:
            edge_ids = {e for e, dec in decisiones.items() if any(m[2] == f"way/{wid}" for m in dec["motivos"])}
            usos = {v: [] for v in ("original", "filtrado")}
            for r in registros:
                for metodo, ruta in r.get("rutas", {}).items():
                    if edge_ids.intersection(map(tuple, ruta["aristas"])):
                        usos[r["version"]].append(r["id"] + "/" + metodo)
            d["corredores"][str(wid)] = {"aristas_originales": len(edge_ids), "aristas_filtradas": sum(H.has_edge(*e) for e in edge_ids), "usos": usos}
        grupos = {"portones_privados": set(), "foot_no": set()}
        for e, dec in decisiones.items():
            for st, reason, ref in dec["motivos"]:
                if st != "restringida":
                    continue
                if reason == "foot=no":
                    grupos["foot_no"].add((e, ref))
                if ref.startswith("node/") and tags["nodos"][ref[5:]].get("access") == "private" and tags["nodos"][ref[5:]].get("barrier") in ("gate", "lift_gate", "swing_gate"):
                    grupos["portones_privados"].add((e, ref))
        d["prohibiciones_especiales"] = {}
        for nombre, valores in grupos.items():
            edges = {e for e, _ in valores}
            d["prohibiciones_especiales"][nombre] = {"fuentes": sorted({r for _, r in valores}), "aristas": len(edges),
                "usos_originales": [r["id"] + "/" + metodo for r in registros if r["version"] == "original"
                    for metodo, ruta in r.get("rutas", {}).items() if edges.intersection(map(tuple, ruta["aristas"]))],
                "aristas_filtradas": sum(H.has_edge(*e) for e in edges)}
        motivos_pares, motivos_rutas = defaultdict(set), defaultdict(set)
        for r in registros:
            if r["grupo"] != "muestra" or r["version"] != "original":
                continue
            for metodo, ruta in r.get("rutas", {}).items():
                for edge in ruta["inciertas"]:
                    for state, reason, ref in decisiones[tuple(edge)]["motivos"]:
                        if state == "revision":
                            motivos_pares[reason].add(r["id"])
                            motivos_rutas[reason].add(r["id"] + "/" + metodo)
        d["motivos_inciertos_usados"] = {k: {"pares": len(v), "modalidades": len(motivos_rutas[k]), "ids": sorted(v)} for k, v in motivos_pares.items()}
        d["fuentes_outliers"] = {}
        for r in d["mayores_cambios"]:
            for causa in r["causas_corta_original"]:
                for ref in causa["fuentes"]:
                    tipo, ident = ref.split("/")
                    d["fuentes_outliers"][ref] = {"tags": tags["vias" if tipo == "way" else "nodos"][ident],
                        "coordenadas": nodos_fuente.get(int(ident)) if tipo == "node" else None}
        d["validaciones"] = {"peticiones": len(registros), "http_200": sum(r["http"] == 200 for r in registros),
            "rechazos_esperados": sum(r["estado"] in ("fuera_cobertura", "sin_camino", "mismo_nodo") for r in registros),
            "errores_tecnicos": sum(r["estado"] == "error_tecnico" for r in registros),
            "max_desvio_filtrado_pct": max(route["desvio_pct"] for r in registros if r["version"] == "filtrado" for route in r.get("rutas", {}).values()),
            "puntos_muestra_ajustables": {v: sum(d <= 300 for r in registros if r["grupo"] == "muestra" and r["version"] == v for d in r["ajustes_m"])
                                          for v in ("original", "filtrado")}}
        resultado[modo] = d
    guardar_json(destino / "revision-detallada.json", resultado)
    guardar_json(destino / "mayores-desvios.geojson", {"type": "FeatureCollection", "features": features})


if __name__ == "__main__":
    ejecutar()
