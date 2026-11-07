r"""Genera 99 cuadrículas predictivas de junio 2026 (EPSG:4326) para el piloto ampliado.

No entrena modelos ni modifica el grafo o la capa de demostración existentes.
Ejemplo desde la raíz del proyecto:
    .\backend\.venv\Scripts\python.exe scripts\generar_capa_ampliada.py

Requiere pyproj y shapely (incluidos en el entorno actual del backend).
"""
from __future__ import annotations

import argparse
import csv
import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import box, mapping
from shapely.ops import transform, unary_union

# Rectángulo original de análisis (lon_min, lat_min, lon_max, lat_max).
BBOX_AMPLIADA = (-78.54, -0.23, -78.47, -0.14)
BBOX_DEMO = (-78.515, -0.215, -78.478, -0.173)
PERIODO = (2026, 6)


def generar(origen: Path, destino: Path) -> None:
    if not origen.is_file():
        raise FileNotFoundError(f"Falta el CSV: {origen}")

    transformer = Transformer.from_crs("EPSG:32717", "EPSG:4326", always_xy=True)
    bbox = box(*BBOX_AMPLIADA)
    demo = box(*BBOX_DEMO)
    celdas = {}

    with origen.open("r", encoding="utf-8-sig", newline="") as archivo:
        reader = csv.DictReader(archivo)
        requeridas = {"anio", "mes", "cx", "cy", "pred_historico", "pred_lightgbm_v2"}
        if not reader.fieldnames or not requeridas.issubset(reader.fieldnames):
            raise ValueError(f"Faltan columnas: {sorted(requeridas - set(reader.fieldnames or []))}")
        for fila in reader:
            if (int(fila["anio"]), int(fila["mes"])) != PERIODO:
                continue
            clave = (int(fila["cx"]), int(fila["cy"]))
            if clave in celdas:
                raise ValueError(f"Celda duplicada en junio 2026: {clave}")
            historico = float(fila["pred_historico"])
            lightgbm = float(fila["pred_lightgbm_v2"])
            if not all(math.isfinite(x) and x >= 0 for x in (historico, lightgbm)):
                raise ValueError(f"Predicción inválida en celda {clave}")
            celdas[clave] = (historico, lightgbm)

    if len(celdas) != 99:
        raise ValueError(f"Se esperaban 99 celdas en junio 2026; encontradas {len(celdas)}")

    features = []
    originales = []
    celdas_demo = 0
    for (cx, cy), (historico, lightgbm) in sorted(celdas.items()):
        # cx,cy son los índices de la malla de 1 km en EPSG:32717.
        cuadro_utm = box(cx * 1000, cy * 1000, (cx + 1) * 1000, (cy + 1) * 1000)
        cuadro_wgs84 = transform(transformer.transform, cuadro_utm)
        recorte = cuadro_wgs84.intersection(bbox)
        if recorte.is_empty or recorte.area <= 0:
            raise ValueError(f"La celda {(cx, cy)} no intersecta el área de análisis")
        if not recorte.is_valid:
            raise ValueError(f"Geometría inválida en celda {(cx, cy)}")
        if cuadro_wgs84.intersection(demo).area > 0:
            celdas_demo += 1
        originales.append(cuadro_wgs84)
        features.append({
            "type": "Feature",
            "id": f"{cx}_{cy}",
            "properties": {
                "cx": cx,
                "cy": cy,
                "periodo": "2026-06",
                "pred_historico": historico,
                "pred_lightgbm_v2": lightgbm,
            },
            "geometry": mapping(recorte),
        })

    # Comprobar cobertura espacial: unión de los 99 cuadrados recubre el bbox.
    union = unary_union(originales)
    if bbox.difference(union).area > 1e-10:
        raise ValueError("La malla no cubre completamente el rectángulo original")
    if celdas_demo != 25:
        raise ValueError(f"Se esperaban 25 celdas que intersectan la demo; hay {celdas_demo}")

    geojson = {
        "type": "FeatureCollection",
        "features": features,
    }
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(json.dumps(geojson, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"GeoJSON generado: {destino}")
    print(f"Cuadrículas: {len(features)} | intersecan zona demo: {celdas_demo}")
    print("Periodo: junio de 2026 (retrospectivo, no pronóstico actual)")
    print("Se conservan los archivos del MVP; este resultado es experimental.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("resultados/predicciones_predictivas_2026.csv"))
    parser.add_argument("--output", type=Path, default=Path("resultados/ampliacion/predicciones_99_celdas_junio2026.geojson"))
    argumentos = parser.parse_args()
    generar(argumentos.input, argumentos.output)
