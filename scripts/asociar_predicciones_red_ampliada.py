"""Asocia predicciones de 99 cuadrículas a la red peatonal ampliada.

Ejecución desde la raíz del proyecto, en la rama experimental:
    python scripts/asociar_predicciones_red_ampliada.py

Entrada:
  red_vial/ampliacion/quito_peatonal_ampliada_base.graphml
  resultados/ampliacion/predicciones_99_celdas_junio2026.geojson
Salida:
  red_vial/ampliacion/quito_peatonal_ampliada_con_predicciones.graphml
  resultados/ampliacion/auditoria_integracion_predictiva.json

No modifica el grafo base ni los archivos utilizados por la aplicación actual.
"""
from __future__ import annotations

import json
import math
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import osmnx as ox
from pyproj import Transformer
from shapely.geometry import LineString, shape
from shapely.ops import transform, unary_union
from shapely.strtree import STRtree
from shapely import wkt

ROOT = Path(__file__).resolve().parents[1]
GRAFO_BASE = ROOT / 'red_vial' / 'ampliacion' / 'quito_peatonal_ampliada_base.graphml'
CAPA = ROOT / 'resultados' / 'ampliacion' / 'predicciones_99_celdas_junio2026.geojson'
GRAFO_SALIDA = ROOT / 'red_vial' / 'ampliacion' / 'quito_peatonal_ampliada_con_predicciones.graphml'
INFORME_SALIDA = ROOT / 'resultados' / 'ampliacion' / 'auditoria_integracion_predictiva.json'
CRS_RED = 'EPSG:4326'
CRS_METRICO = 'EPSG:32717'  # UTM zona 17 sur para Quito.
UMBRAL_COBERTURA = 0.995  # Conservamos únicamente aristas cubiertas >= 99,5 %.


def finito_no_negativo(valor: object, contexto: str) -> float:
    try:
        numero = float(valor)
    except (ValueError, TypeError) as exc:
        raise ValueError(f'{contexto}: valor no numérico: {valor!r}') from exc
    if not math.isfinite(numero) or numero < 0:
        raise ValueError(f'{contexto}: se requiere un número finito no negativo: {valor!r}')
    return numero


def cargar_cuadriculas(proyectar):
    data = json.loads(CAPA.read_text(encoding='utf-8'))
    if data.get('type') != 'FeatureCollection' or len(data.get('features', [])) != 99:
        raise ValueError('El GeoJSON debe tener exactamente 99 features de tipo FeatureCollection.')
    geometrias, indicadores, ids = [], [], set()
    for n, feat in enumerate(data['features']):
        propiedades = feat.get('properties') or {}
        if propiedades.get('periodo') != '2026-06':
            raise ValueError(f'Cuadrícula {n}: periodo incorrecto o faltante.')
        id_celda = (propiedades.get('cx'), propiedades.get('cy'))
        if None in id_celda or id_celda in ids:
            raise ValueError(f'Cuadrícula {n}: identificador ausente o duplicado: {id_celda!r}.')
        ids.add(id_celda)
        ph = finito_no_negativo(propiedades.get('pred_historico'), f'Cuadrícula {id_celda} histórica')
        pm = finito_no_negativo(propiedades.get('pred_lightgbm_v2'), f'Cuadrícula {id_celda} LightGBM')
        geom = shape(feat['geometry'])
        if not geom.is_valid or geom.is_empty or geom.geom_type not in {'Polygon', 'MultiPolygon'}:
            raise ValueError(f'Cuadrícula {id_celda}: geometría inválida.')
        geom_m = transform(proyectar, geom)
        if not geom_m.is_valid or geom_m.is_empty:
            raise ValueError(f'Cuadrícula {id_celda}: geometría inválida después de proyectar.')
        geometrias.append(geom_m)
        indicadores.append((ph, pm))
    return geometrias, indicadores


def construir_linea(grafo, u, v, datos, proyectar):
    """Devuelve (línea en metros, usada_geometria_real)."""
    geometria = datos.get('geometry')
    tiene_geometria = geometria is not None
    if geometria is None:
        # Las aristas OSMnx sin geometry son tramos rectos entre sus nodos.
        origen, destino = grafo.nodes[u], grafo.nodes[v]
        geometria = LineString([(float(origen['x']), float(origen['y'])),
                                (float(destino['x']), float(destino['y']))])
    elif isinstance(geometria, str):
        geometria = wkt.loads(geometria)
    if geometria.geom_type != 'LineString' or geometria.is_empty:
        raise ValueError(f'Arista {(u, v)}: geometría no admitida: {geometria.geom_type}')
    linea = transform(proyectar, geometria)
    if not linea.is_valid or not math.isfinite(linea.length) or linea.length <= 0:
        raise ValueError(f'Arista {(u, v)}: longitud métrica inválida.')
    return linea, tiene_geometria


def asociar_predicciones(grafo, geometrias, indicadores, proyectar):
    indice = STRtree(geometrias)
    conservadas, razones = [], Counter()
    longitudes_red = 0.0
    longitudes_cubiertas = 0.0
    total = grafo.number_of_edges()
    for n, (u, v, k, d) in enumerate(grafo.edges(keys=True, data=True), 1):
        if n % 10000 == 0:
            print(f'Procesadas {n:,}/{total:,} aristas...', flush=True)
        try:
            linea, tiene_geom = construir_linea(grafo, u, v, d, proyectar)
            longitud = float(linea.length)
            if not tiene_geom:
                razones['aristas_sin_geometria_detallada'] += 1
        except (TypeError, ValueError, KeyError) as exc:
            razones['geometria_invalida'] += 1
            if razones['geometria_invalida'] <= 5:
                print(f'Aviso: {exc}')
            continue

        longitudes_red += longitud
        indices = indice.query(linea)
        if len(indices) == 0:
            razones['sin_cuadriculas'] += 1
            continue
        longitudes_interseccion = []
        fragmentos = []
        for idx in indices:
            i = int(idx)
            parte = linea.intersection(geometrias[i])
            medida = float(parte.length)
            if medida > 1e-8:
                longitudes_interseccion.append((i, medida))
                fragmentos.append(parte)
        if not fragmentos:
            razones['solo_contacto_sin_longitud'] += 1
            continue
        cubierta = min(longitud, float(unary_union(fragmentos).length))
        fraccion = cubierta / longitud
        if fraccion + 1e-9 < UMBRAL_COBERTURA:
            razones['cobertura_insuficiente'] += 1
            continue
        denom = sum(long for _, long in longitudes_interseccion)
        score_h = sum(long * indicadores[i][0] for i, long in longitudes_interseccion) / denom
        score_m = sum(long * indicadores[i][1] for i, long in longitudes_interseccion) / denom
        if not all(math.isfinite(x) and x >= 0 for x in (score_h, score_m)):
            razones['scores_invalidos'] += 1
            continue
        # Preservar original length de OSMnx y usar la longitud de la geometría
        # proyectada para el enrutamiento nuevo: longitud_m.
        d['longitud_m'] = longitud
        d['score_historico'] = score_h
        d['score_lightgbm'] = score_m
        conservadas.append((u, v, k))
        longitudes_cubiertas += longitud
    return conservadas, razones, longitudes_red, longitudes_cubiertas


def main():
    for archivo in (GRAFO_BASE, CAPA):
        if not archivo.is_file():
            raise SystemExit(f'No existe el archivo requerido: {archivo}')
    for archivo in (GRAFO_SALIDA, INFORME_SALIDA):
        if archivo.exists():
            raise SystemExit(f'Ya existe {archivo}. No sobrescribiremos resultados anteriores.')
    transformer = Transformer.from_crs(CRS_RED, CRS_METRICO, always_xy=True)
    proyectar = transformer.transform
    cuadriculas, indicadores = cargar_cuadriculas(proyectar)
    print(f'Capa predictiva validada: {len(cuadriculas)} cuadrículas de junio de 2026.')
    print('Cargando grafo base...')
    grafo = ox.load_graphml(GRAFO_BASE)
    if not isinstance(grafo, nx.MultiDiGraph):
        raise SystemExit('El grafo debe ser un MultiDiGraph dirigido.')
    if str(grafo.graph.get('crs', '')).lower().replace(' ', '') not in {'epsg:4326'}:
        raise SystemExit(f'CRS del grafo inesperado: {grafo.graph.get("crs")}')
    nodos_base = grafo.number_of_nodes()
    aristas_base = grafo.number_of_edges()
    print(f'Red base: {nodos_base:,} nodos y {aristas_base:,} aristas.')
    conservadas, razones, total_m, cubierto_m = asociar_predicciones(
        grafo, cuadriculas, indicadores, proyectar
    )
    if not conservadas:
        raise SystemExit('Ninguna arista pasó los filtros de cobertura. No se crea un nuevo grafo.')
    candidato = grafo.edge_subgraph(conservadas).copy()
    componentes = sorted(nx.strongly_connected_components(candidato), key=len, reverse=True)
    integrado = candidato.subgraph(componentes[0]).copy()
    if integrado.number_of_nodes() < 2 or integrado.number_of_edges() < 1:
        raise SystemExit('Componente fuertemente conexa demasiado pequeña.')
    # No alteramos EPSG ni los atributos estándar de la red, conservando geometrías reales.
    integrado.graph['periodo_prediccion'] = '2026-06'
    integrado.graph['descripcion'] = 'RutaInformada Quito: piloto ampliado experimental, no integrado en la app'
    informe = {
        'proyecto': 'RutaInformada Quito',
        'estado': 'experimental: no integrado al backend',
        'periodo_predicciones': '2026-06',
        'crs_grafo': str(integrado.graph.get('crs')),
        'crs_metrico_para_intersecciones': CRS_METRICO,
        'umbral_cobertura_segmento': UMBRAL_COBERTURA,
        'cuadriculas': len(cuadriculas),
        'nodos_base': nodos_base,
        'aristas_base': aristas_base,
        'aristas_con_score_y_cobertura_suficiente': len(conservadas),
        'porcentaje_aristas_con_score': round(100 * len(conservadas) / aristas_base, 4),
        'longitud_cubierta_sobre_total_pct': round(100 * cubierto_m / total_m, 4) if total_m else None,
        'aristas_candidatas': candidato.number_of_edges(),
        'nodos_candidatos': candidato.number_of_nodes(),
        'componentes_fuertemente_conexas_candidatas': len(componentes),
        'nodos_mayor_componente_fuerte': integrado.number_of_nodes(),
        'aristas_mayor_componente_fuerte': integrado.number_of_edges(),
        'porcentaje_nodos_base_en_componente_final': round(100 * integrado.number_of_nodes() / nodos_base, 4),
        'razones_exclusion_y_observaciones': dict(razones),
        'notas': [
            'Las predicciones se ponderan por longitud geométrica de intersección con cada cuadrícula.',
            'Se excluyen aristas con cobertura insuficiente; nunca se imputan valores cero.',
            'Las puntuaciones corresponden a junio de 2026 retrospectivo, no a riesgo individual.',
            'La componente fuerte final es alcanzable en ambos sentidos, no garantiza rutas para todos los puntos del bbox.',
            'No se evaluó todavía rendimiento ni la regresión de las tres rutas en la nueva red.',
            'Aristas sin geometría detallada se representan como el segmento directo entre nodos, igual que en OSMnx.',
        ]
    }
    print('Guardando grafo integrado en archivo NUEVO...')
    GRAFO_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    INFORME_SALIDA.parent.mkdir(parents=True, exist_ok=True)
    ox.save_graphml(integrado, filepath=GRAFO_SALIDA)
    INFORME_SALIDA.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    print('Grafo experimental:', GRAFO_SALIDA)
    print('Informe:', INFORME_SALIDA)
    print(json.dumps(informe, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
