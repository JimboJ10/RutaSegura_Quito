r"""Auditoría aislada de geometrías de rutas sobre el grafo ampliado.

Ejecución desde la raíz de RutaSegura_Quito:
    .\backend\.venv\Scripts\python.exe scripts\auditar_geometrias_rutas_ampliadas.py

Requisitos: este script debe estar junto a validar_rutas_red_ampliada_corregido.py.
No modifica grafos, backend, modelos ni datos de entrada. Escribe archivos nuevos
exclusivamente en resultados/ampliacion/. No afirma que estas rutas sean más seguras.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

import networkx as nx
import osmnx as ox
from shapely import wkt
from shapely.geometry import LineString

import validar_rutas_red_ampliada_corregido as anterior

ROOT = Path(__file__).resolve().parents[1]
GRAFO = ROOT / 'red_vial' / 'ampliacion' / 'quito_peatonal_ampliada_con_predicciones.graphml'
SALIDA = ROOT / 'resultados' / 'ampliacion'
MAX_AJUSTE_M = 300.0
MAX_DESVIO_PCT = 15.0
TOLERANCIA_EXTREMO_M = 2.0


def distancia_m(a, b):
    """Coordenadas en orden (longitud, latitud)."""
    return float(ox.distance.great_circle(a[1], a[0], b[1], b[0]))


def coordenada_nodo(g, n):
    d = g.nodes[n]
    punto = [float(d['x']), float(d['y'])]
    if not all(math.isfinite(z) for z in punto):
        raise ValueError(f'Nodo {n} con coordenadas no finitas')
    return punto


def geometria_orientada(g, u, v, attrs):
    """Devuelve coordenadas [lon,lat] y si se usó una línea directa provisional."""
    origen, destino = coordenada_nodo(g, u), coordenada_nodo(g, v)
    dato = attrs.get('geometry')
    sin_detalle = dato is None or (isinstance(dato, str) and not dato.strip())
    if sin_detalle:
        coords = [origen, destino]
    else:
        if isinstance(dato, str):
            dato = wkt.loads(dato)
        if not isinstance(dato, LineString) or dato.is_empty or len(dato.coords) < 2:
            raise ValueError(f'Geometría inválida para arista {u!r}->{v!r}: {type(dato).__name__}')
        coords = [[float(x), float(y)] for x, y, *extra in dato.coords]
        if not all(math.isfinite(z) for p in coords for z in p):
            raise ValueError(f'Coordenadas no finitas en arista {u!r}->{v!r}')
        directo = distancia_m(coords[0], origen) + distancia_m(coords[-1], destino)
        invertido = distancia_m(coords[0], destino) + distancia_m(coords[-1], origen)
        if invertido < directo:
            coords.reverse()
    ajuste_a = distancia_m(coords[0], origen)
    ajuste_b = distancia_m(coords[-1], destino)
    if max(ajuste_a, ajuste_b) > TOLERANCIA_EXTREMO_M:
        raise ValueError(
            f'Arista {u!r}->{v!r} con extremos geométricos desalineados: '
            f'{ajuste_a:.2f} m y {ajuste_b:.2f} m'
        )
    return coords, sin_detalle, max(ajuste_a, ajuste_b)


def seleccionar_tramo(g, u, v, metodo, alpha, medianas):
    """Mismo criterio de aristas paralelas que usa la evaluación exploratoria."""
    opciones = g[u][v]
    return min(opciones.values(), key=lambda a: anterior.peso_arista(a, metodo, alpha, medianas))


def camino_elegido(g, nodo_a, nodo_b, metodo, resumen, medianas):
    alpha = resumen.get('alpha')
    if metodo == 'corta' or alpha is None:
        nodos = nx.shortest_path(g, nodo_a, nodo_b, weight='longitud_m')
        return nodos, 'corta', 0
    return (
        nx.shortest_path(g, nodo_a, nodo_b, weight=anterior.peso_camino(metodo, alpha, medianas)),
        metodo,
        alpha,
    )


def auditar_ruta(g, nodos, criterio, alpha, medianas):
    partes = []
    tramos_rectos = 0
    desalineacion_max = 0.0
    discontinuidad_max = 0.0
    anterior_fin = None
    for u, v in zip(nodos[:-1], nodos[1:]):
        attrs = seleccionar_tramo(g, u, v, criterio, alpha, medianas)
        coords, sin_detalle, error_extremo = geometria_orientada(g, u, v, attrs)
        if anterior_fin is not None:
            salto = distancia_m(anterior_fin, coords[0])
            discontinuidad_max = max(discontinuidad_max, salto)
            if salto > TOLERANCIA_EXTREMO_M:
                raise ValueError(f'Discontinuidad en la ruta {u!r}->{v!r}: {salto:.2f} m')
        partes.append(coords)
        anterior_fin = coords[-1]
        tramos_rectos += int(sin_detalle)
        desalineacion_max = max(desalineacion_max, error_extremo)
    if not partes:
        raise ValueError('Recorrido sin segmentos')
    return {
        'type': 'MultiLineString',
        'coordinates': partes,
    }, {
        'tramos_totales': len(partes),
        'tramos_sin_geometria_detallada': tramos_rectos,
        'porcentaje_tramos_rectos_de_respaldo': round(100 * tramos_rectos / len(partes), 2),
        'max_error_extremos_m': round(desalineacion_max, 4),
        'max_salto_entre_tramos_m': round(discontinuidad_max, 4),
    }


def main():
    if not GRAFO.is_file():
        raise SystemExit(f'No existe el grafo experimental: {GRAFO}')
    print('Cargando el grafo experimental (solo lectura)...', flush=True)
    inicio = time.perf_counter()
    g = ox.load_graphml(GRAFO)
    medianas = anterior.preparar(g)
    carga_s = round(time.perf_counter() - inicio, 2)
    print(f'Grafo cargado: {g.number_of_nodes():,} nodos, {g.number_of_edges():,} aristas')

    features, casos = [], []
    for nombre, a, b in anterior.CASOS:
        print(f'\nCaso: {nombre}', flush=True)
        fila = {'caso': nombre, 'origen_lon_lat': list(a), 'destino_lon_lat': list(b)}
        instante = time.perf_counter()
        try:
            na = ox.distance.nearest_nodes(g, X=a[0], Y=a[1])
            nb = ox.distance.nearest_nodes(g, X=b[0], Y=b[1])
            da = anterior.distancia_a_nodo(g, a, na)
            db = anterior.distancia_a_nodo(g, b, nb)
            fila['ajuste_origen_m'] = round(da, 2)
            fila['ajuste_destino_m'] = round(db, 2)
            if max(da, db) > MAX_AJUSTE_M:
                fila['estado'] = 'no_evaluable_fuera_de_cobertura'
                print(f'  No evaluable: distancias de ajuste {da:.1f} m / {db:.1f} m')
            elif na == nb:
                fila['estado'] = 'no_evaluable_mismo_nodo'
            elif not nx.has_path(g, na, nb):
                fila['estado'] = 'no_evaluable_sin_camino'
            else:
                resumen = anterior.variantes(g, na, nb, medianas)
                fila['estado'] = 'correcto'
                fila['rutas'] = {}
                for metodo, valores in resumen.items():
                    if valores['desvio_pct'] > MAX_DESVIO_PCT + 0.001:
                        raise ValueError(f'Desvío superior al 15 % en {metodo}')
                    nodos, criterio, alpha = camino_elegido(g, na, nb, metodo, valores, medianas)
                    geometria, auditoria = auditar_ruta(g, nodos, criterio, alpha, medianas)
                    verificado = anterior.evaluar(g, nodos, criterio, alpha, medianas)
                    if abs(verificado['distancia_km'] - valores['distancia_km']) > 1e-6:
                        raise ValueError(f'Distancia inconsistente en {metodo}')
                    fila['rutas'][metodo] = {**valores, **auditoria}
                    features.append({
                        'type': 'Feature',
                        'properties': {
                            'caso': nombre,
                            'tipo': metodo,
                            'distancia_km': valores['distancia_km'],
                            'desvio_pct': valores['desvio_pct'],
                            'indice_historico': valores['indice_historico'],
                            'indice_lightgbm': valores['indice_lightgbm'],
                            'ajuste_origen_m': round(da, 2),
                            'ajuste_destino_m': round(db, 2),
                            'periodo': '2026-06',
                            **auditoria,
                        },
                        'geometry': geometria,
                    })
                    print(
                        f'  {metodo:10s} {valores["distancia_km"]:.3f} km | '
                        f'{auditoria["tramos_sin_geometria_detallada"]}/{auditoria["tramos_totales"]} '
                        f'tramos sin detalle | salto máx. {auditoria["max_salto_entre_tramos_m"]:.3f} m'
                    )
        except Exception as exc:
            fila['estado'] = 'error'
            fila['detalle_error'] = f'{type(exc).__name__}: {exc}'
            print('  ERROR:', fila['detalle_error'])
        fila['duracion_calculo_s'] = round(time.perf_counter() - instante, 3)
        casos.append(fila)

    SALIDA.mkdir(parents=True, exist_ok=True)
    archivo_geo = SALIDA / 'auditoria_geometria_rutas_ampliadas.geojson'
    archivo_json = SALIDA / 'auditoria_geometria_rutas_ampliadas.json'
    archivo_geo.write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, ensure_ascii=False), encoding='utf-8')
    informe = {
        'proyecto': 'RutaInformada Quito',
        'estado': 'experimental, no integrado al backend',
        'grafo': str(GRAFO.relative_to(ROOT)).replace('\\', '/'),
        'periodo_predicciones': '2026-06',
        'tiempo_carga_grafo_s': carga_s,
        'casos_correctos': sum(c['estado'] == 'correcto' for c in casos),
        'casos_no_evaluables': sum(c['estado'].startswith('no_evaluable') for c in casos),
        'casos_con_error': sum(c['estado'] == 'error' for c in casos),
        'features_geojson_generados': len(features),
        'advertencia': 'Rutas experimentales. Los indicadores no son probabilidades individuales de accidente ni garantizan seguridad. Tramos sin geometría detallada usan líneas directas.',
        'casos': casos,
    }
    archivo_json.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nInforme: {archivo_json}')
    print(f'GeoJSON: {archivo_geo}')
    print(f'Casos correctos: {informe["casos_correctos"]} | no evaluables: {informe["casos_no_evaluables"]} | errores: {informe["casos_con_error"]}')
    if informe['casos_con_error']:
        raise SystemExit(1)


if __name__ == '__main__':
    main()
