r"""Validación EXPLORATORIA de las 3 rutas sobre el grafo ampliado.

Ejecución desde la raíz de RutaSegura_Quito:
    .\backend\.venv\Scripts\python.exe scripts\validar_rutas_red_ampliada.py

No altera grafos, predicciones, backend ni datasets. Usa NetworkX y
OSMnx para una evaluación independiente, no ejecuta la API FastAPI.
La equivalencia de los resultados con backend/rutas.py requiere pruebas
posteriores de integración, no está garantizada por este script.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from statistics import median

import networkx as nx
import osmnx as ox

ROOT = Path(__file__).resolve().parents[1]
GRAFO = ROOT / 'red_vial' / 'ampliacion' / 'quito_peatonal_ampliada_con_predicciones.graphml'
CARPETA_SALIDA = ROOT / 'resultados' / 'ampliacion'
ALPHAS = (0.25, 0.5, 1, 2, 4, 8, 16)
DESVIO_MAX = 0.15
SNAP_MAX_M = 300.0
# (lon, lat): casos experimentales en distintas direcciones del BBOX.
# Algunos pueden resultar fuera de la cobertura de la red y entonces
# se registran como no evaluables, en lugar de declararlos exitosos.
CASOS = [
    ('regresion_del_piloto', (-78.504, -0.201), (-78.486, -0.184)),
    ('norte_sur', (-78.498, -0.150), (-78.505, -0.218)),
    ('oeste_este', (-78.532, -0.186), (-78.481, -0.188)),
    ('suroeste_noreste', (-78.530, -0.220), (-78.481, -0.153)),
    ('centro_este', (-78.516, -0.199), (-78.483, -0.180)),
]


def validar_arista(d, ref):
    for nombre in ('longitud_m', 'score_historico', 'score_lightgbm'):
        try:
            val = float(d[nombre])
        except (KeyError, ValueError, TypeError) as e:
            raise ValueError(f'Arista {ref}: atributo {nombre} ausente o inválido') from e
        if not math.isfinite(val) or (val <= 0 if nombre == 'longitud_m' else val < 0):
            raise ValueError(f'Arista {ref}: atributo {nombre} fuera de rango: {val!r}')
        # GraphML puede almacenar valores numéricos como str. Normalizarlos
        # en la copia del grafo cargada en memoria evita fallos de NetworkX.
        d[nombre] = val


def preparar(g):
    if not isinstance(g, nx.MultiDiGraph):
        raise ValueError('Se esperaba un MultiDiGraph dirigido')
    crs = str(g.graph.get('crs', '')).lower().replace(' ', '')
    if crs != 'epsg:4326':
        raise ValueError(f'Sistema de coordenadas inesperado: {crs!r}')
    hist, ml = [], []
    for u, v, k, d in g.edges(keys=True, data=True):
        validar_arista(d, (u, v, k))
        hist.append(float(d['score_historico']))
        ml.append(float(d['score_lightgbm']))
    if not hist:
        raise ValueError('El grafo no tiene aristas')
    return {'historica': max(median(hist), 1e-6), 'lightgbm': max(median(ml), 1e-6)}


def peso_arista(d, metodo, alpha, medianas):
    largo = float(d['longitud_m'])
    if metodo == 'corta':
        return largo
    campo = 'score_historico' if metodo == 'historica' else 'score_lightgbm'
    return largo * (1 + alpha * float(d[campo]) / medianas[metodo])


def peso_camino(metodo, alpha, medianas):
    # Para MultiDiGraph, NX recibe un dict key -> atributos y debe escoger
    # la arista paralela con el menor peso del criterio seleccionado.
    def funcion(_u, _v, paralelas):
        return min(peso_arista(d, metodo, alpha, medianas) for d in paralelas.values())
    return funcion


def evaluar(g, nodos, metodo, alpha, medianas):
    longitud_m = indice_h = indice_m = 0.0
    sin_geometria = 0
    for u, v in zip(nodos[:-1], nodos[1:]):
        candidatos = g[u][v].values()
        d = min(candidatos, key=lambda e: peso_arista(e, metodo, alpha, medianas))
        m = float(d['longitud_m'])
        longitud_m += m
        indice_h += m / 1000 * float(d['score_historico'])
        indice_m += m / 1000 * float(d['score_lightgbm'])
        sin_geometria += int('geometry' not in d or d['geometry'] in ('', None))
    return {
        'distancia_km': round(longitud_m / 1000, 6),
        'indice_historico': round(indice_h, 6),
        'indice_lightgbm': round(indice_m, 6),
        'nodos': len(nodos),
        'tramos_sin_geometria_detallada': sin_geometria,
    }


def variantes(g, origen, destino, medianas):
    base = nx.shortest_path(g, origen, destino, weight='longitud_m')
    info_base = evaluar(g, base, 'corta', 0, medianas)
    resultados = {'corta': {**info_base, 'desvio_pct': 0., 'alpha': None}}
    max_m = info_base['distancia_km'] * 1000 * (1 + DESVIO_MAX)
    for metodo, campo in (('historica', 'indice_historico'), ('lightgbm', 'indice_lightgbm')):
        mejor = dict(info_base)
        mejor['alpha'] = None
        for alpha in ALPHAS:
            f = peso_camino(metodo, alpha, medianas)
            camino = nx.shortest_path(g, origen, destino, weight=f)
            candidato = evaluar(g, camino, metodo, alpha, medianas)
            if candidato['distancia_km'] * 1000 <= max_m + .005 and candidato[campo] < mejor[campo] - 1e-8:
                mejor = {**candidato, 'alpha': alpha}
        mejor['desvio_pct'] = round((mejor['distancia_km'] / info_base['distancia_km'] - 1) * 100, 4)
        resultados[metodo] = mejor
    return resultados


def distancia_a_nodo(g, punto, nodo):
    # Distancia de gran círculo para documentar snap en WGS84.
    from osmnx.distance import great_circle
    return float(great_circle(punto[1], punto[0], float(g.nodes[nodo]['y']), float(g.nodes[nodo]['x'])))


def main():
    if not GRAFO.is_file():
        raise SystemExit(f'No existe el grafo experimental: {GRAFO}')
    print('Cargando grafo experimental (no se modifica)...', flush=True)
    g = ox.load_graphml(GRAFO)
    medianas = preparar(g)
    print(f'Nodos: {g.number_of_nodes():,} | Aristas: {g.number_of_edges():,}', flush=True)
    print('Medianas de puntuación:', medianas, flush=True)
    resultados = []
    for nombre, a, b in CASOS:
        print(f'\nPrueba: {nombre}', flush=True)
        fila = {'nombre': nombre, 'origen_solicitado_lon_lat': list(a), 'destino_solicitado_lon_lat': list(b)}
        try:
            n_a = ox.distance.nearest_nodes(g, X=a[0], Y=a[1])
            n_b = ox.distance.nearest_nodes(g, X=b[0], Y=b[1])
            d_a = distancia_a_nodo(g, a, n_a)
            d_b = distancia_a_nodo(g, b, n_b)
            fila['distancia_ajuste_origen_m'] = round(d_a, 2)
            fila['distancia_ajuste_destino_m'] = round(d_b, 2)
            if max(d_a, d_b) > SNAP_MAX_M:
                fila['estado'] = 'no_evaluable_ajuste_superior_a_300m'
                print(f'  No evaluable: ajuste origen={d_a:.1f}m, destino={d_b:.1f}m')
            elif n_a == n_b:
                fila['estado'] = 'no_evaluable_mismo_nodo'
                print('  No evaluable: mismo nodo')
            elif not nx.has_path(g, n_a, n_b):
                fila['estado'] = 'no_evaluable_sin_ruta'
                print('  No evaluable: sin camino dirigido')
            else:
                rutas = variantes(g, n_a, n_b, medianas)
                fila['estado'] = 'evaluado'
                fila['rutas'] = rutas
                for tipo, d in rutas.items():
                    print(f'  {tipo:10s} {d["distancia_km"]:.3f} km | desvío {d["desvio_pct"]:.2f}% |'
                          f' índice histórico {d["indice_historico"]:.3f} | ML {d["indice_lightgbm"]:.3f}', flush=True)
                assert all(d['desvio_pct'] <= 15.001 for d in rutas.values())
        except (ValueError, KeyError, nx.NetworkXException) as e:
            fila['estado'] = 'error'
            fila['error'] = f'{type(e).__name__}: {e}'
            print('  ERROR:', fila['error'])
        resultados.append(fila)

    CARPETA_SALIDA.mkdir(parents=True, exist_ok=True)
    sello = datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')
    salida = CARPETA_SALIDA / f'pruebas_rutas_ampliadas_{sello}.json'
    informe = {
        'proyecto': 'RutaInformada Quito',
        'tipo': 'prueba_exploratoria_independiente_no_integracion_fastapi',
        'archivo_grafo': str(GRAFO.relative_to(ROOT)).replace('\\', '/'),
        'periodo': '2026-06',
        'parametros': {'alphas': ALPHAS, 'desvio_maximo_pct': 15, 'ajuste_maximo_m': SNAP_MAX_M},
        'nota': 'No demuestra seguridad individual ni equivalencia exacta con la API. No compara distancias de regresión entre diferentes redes.',
        'nodos': g.number_of_nodes(),
        'aristas': g.number_of_edges(),
        'cantidad_casos_evaluados': sum(1 for x in resultados if x['estado'] == 'evaluado'),
        'cantidad_casos_no_evaluables': sum(1 for x in resultados if x['estado'].startswith('no_evaluable')),
        'cantidad_errores': sum(1 for x in resultados if x['estado'] == 'error'),
        'casos': resultados,
    }
    salida.write_text(json.dumps(informe, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f'\nInforme generado: {salida}')
    print(f'Casos evaluados: {informe["cantidad_casos_evaluados"]}/{len(CASOS)} | '
          f'no evaluables: {informe["cantidad_casos_no_evaluables"]} | '
          f'errores: {informe["cantidad_errores"]}')
    if informe['cantidad_errores']:
        raise SystemExit('Hubo errores en los cálculos: revisa el informe antes de continuar.')


if __name__ == '__main__':
    main()
