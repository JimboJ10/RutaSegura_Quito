"""RutaInformada Quito: capa exploratoria de robos históricos 2019-2022.

Consulta ÚNICAMENTE conteos espaciales al FeatureServer ArcGIS; nunca pide
puntos individuales, nombres, direcciones ni atributos personales.

IMPORTANTE: producto para análisis LOCAL. Derechos de redistribución y precisión
geográfica de la fuente NO verificados. No añadir a Git ni presentar como
alertas actuales. Mantiene el grafo y las tres rutas completamente intactos.

Uso (desde la raíz de RutaSegura_Quito):
    python scripts/generar_capa_robos_historicos_quito.py

Requisitos: shapely y pyproj (presentes normalmente en el entorno geoespacial).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

try:
    from pyproj import Transformer
    from shapely import transform
    from shapely.geometry import GeometryCollection, MultiPolygon, Polygon, box, mapping, shape
    from shapely.geometry.polygon import orient
except ImportError as e:
    raise SystemExit('Falta una dependencia: shapely y pyproj. Usa el .venv del backend. ' + str(e))

ROOT = Path(__file__).resolve().parent.parent
ORIGEN = ROOT / 'resultados' / 'predicciones_demo_junio2026.geojson'
SALIDA = ROOT / 'resultados' / 'delincuencia_exploratoria' / 'robos_historicos_2019_2022_cuadriculas.geojson'
INFORME = ROOT / 'resultados' / 'delincuencia_exploratoria' / 'auditoria_robos_historicos_2019_2022.json'
URL = ('https://services1.arcgis.com/UOl0yzPDLol8nS3m/ArcGIS/rest/services/'
       'Robo_personas_view/FeatureServer/0')
BBOX = (-78.515, -0.215, -78.478, -0.173)  # WGS84, zona piloto
BBOX_GEOM = box(*BBOX)
FECHAS_SQL = "FECHA_DEL_ >= DATE '2019-01-01' AND FECHA_DEL_ < DATE '2023-01-01'"
PROYECCION = Transformer.from_crs('EPSG:4326', 'EPSG:32717', always_xy=True).transform
UMBRAL_PRIVACIDAD = 5
VERSION = '1.0.0'
# SHA-256 del contenido JSON normalizado de la demo validada (no de sus bytes).
HUELLA_CONTENIDO = '7211aef82e6ee06c6caa9bb918709e51f93e7631315e28566799d612e054cd56'


def validar_demo(doc):
    if not isinstance(doc, dict) or doc.get('type') != 'FeatureCollection':
        raise ValueError('Se esperaba una colección GeoJSON')
    meta = doc.get('metadata')
    if not isinstance(meta, dict) or (meta.get('fuente'), meta.get('periodo')) != (URL, '2019-2022'):
        raise ValueError('Fuente o periodo distintos de la demo')
    filas = doc.get('features')
    if not isinstance(filas, list) or len(filas) != 25:
        raise ValueError('Se esperaban 25 cuadrículas')
    por_id = {}
    for f in filas:
        if not isinstance(f, dict) or not isinstance(f.get('properties'), dict):
            raise ValueError('Falta la ficha de una cuadrícula')
        celda = f['properties'].get('celda_id')
        if not isinstance(celda, str) or celda != f.get('id') or celda in por_id:
            raise ValueError('Identificador de cuadrícula inválido o duplicado')
        por_id[celda] = f
    # Incluye todas las coordenadas, conteos, rangos ocultos, densidades,
    # categorías y metadatos. Cambiar cualquiera exige auditar otra versión.
    normalizado = {**doc, 'features': [por_id[k] for k in sorted(por_id)]}
    contenido = json.dumps(normalizado, sort_keys=True, ensure_ascii=False,
                           allow_nan=False, separators=(',', ':')).encode('utf-8')
    if hashlib.sha256(contenido).hexdigest() != HUELLA_CONTENIDO:
        raise ValueError('El contenido difiere de la demo histórica validada. Revise la cuadrícula base y la fuente.')


def claves_unicas(pares):
    obj = dict(pares)
    if len(obj) != len(pares):
        raise ValueError('El documento JSON contiene claves repetidas')
    return obj


def guardar_json(destino, doc):
    destino.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile(dir=destino.parent, delete=False) as archivo:
        temporal = Path(archivo.name)
    try:
        temporal.write_text(json.dumps(doc, ensure_ascii=False, indent=2), encoding='utf-8')
        temporal.replace(destino)
    finally:
        temporal.unlink(missing_ok=True)


def consultar(ruta: str, params: dict, *, post: bool = False) -> dict:
    payload = {**params, 'f': 'json'}
    headers = {
        'User-Agent': 'RutaInformada-Quito-analisis-academico/1.0',
        'Accept': 'application/json',
    }
    if post:
        datos = urlencode(payload).encode('utf-8')
        headers['Content-Type'] = 'application/x-www-form-urlencoded'
        request = Request(URL + ruta, data=datos, headers=headers)
    else:
        request = Request(URL + ruta + '?' + urlencode(payload), headers=headers)
    for intento in range(3):
        try:
            with urlopen(request, timeout=30) as resp:
                respuesta = json.load(resp)
            if not isinstance(respuesta, dict):
                raise RuntimeError('Respuesta ArcGIS inesperada')
            if 'error' in respuesta:
                error = respuesta['error']
                raise RuntimeError(f"ArcGIS: {error.get('message', 'Error')} {error.get('details', [])}")
            return respuesta
        except (HTTPError, URLError, TimeoutError) as exc:
            if intento == 2:
                raise RuntimeError('No fue posible consultar ArcGIS: ' + str(exc)) from exc
            time.sleep(1.5 * (intento + 1))
    raise AssertionError('Inalcanzable')


def consultar_conteo(geometria: dict, *, tipo: str) -> int:
    data = consultar('/query', {
        'where': FECHAS_SQL,
        'returnCountOnly': 'true',
        'geometry': json.dumps(geometria, separators=(',', ':')) if tipo == 'polygon' else geometria,
        'geometryType': 'esriGeometryPolygon' if tipo == 'polygon' else 'esriGeometryEnvelope',
        'inSR': '4326',
        'spatialRel': 'esriSpatialRelIntersects',
    }, post=True)
    n = data.get('count')
    if type(n) is not int or n < 0:
        raise ValueError('ArcGIS no devolvió un conteo entero no negativo')
    return n


def poligonos(g):
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if isinstance(g, GeometryCollection):
        return [p for x in g.geoms for p in poligonos(x)]
    return []


def armar_geometria_esri(g):
    """Crea anillos ArcGIS: exterior horario, agujeros antihorarios."""
    rings = []
    for p in poligonos(g):
        p = orient(p, sign=-1.0)
        rings.append([[float(x), float(y)] for x, y in p.exterior.coords])
        for interior in p.interiors:
            rings.append([[float(x), float(y)] for x, y in interior.coords])
    return {'rings': rings, 'spatialReference': {'wkid': 4326}}


def percentil_ordenado(valores, fraccion):
    if not valores:
        return None
    valores = sorted(valores)
    return valores[math.ceil((len(valores)-1)*fraccion)]


def extraer_features(path: Path):
    if not path.is_file():
        raise FileNotFoundError(f'No encuentro las 25 cuadrículas: {path}')
    source = json.loads(path.read_text(encoding='utf-8-sig'))
    if source.get('type') != 'FeatureCollection':
        raise ValueError('El GeoJSON debe ser FeatureCollection')
    features = source.get('features', [])
    if len(features) != 25:
        raise ValueError(f'Se esperaban 25 cuadrículas de la demo; llegaron {len(features)}. No continuar sin revisión.')
    return features


def area_km2(g):
    return transform(g, PROYECCION, interleaved=False).area / 1_000_000


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--origen', type=Path, default=ORIGEN)
    parser.add_argument('--salida', type=Path, default=SALIDA)
    parser.add_argument('--informe', type=Path, default=INFORME)
    parser.add_argument('--verificar', action='store_true', help='Validar la capa local sin llamar a ArcGIS')
    args = parser.parse_args()
    if args.verificar:
        validar_demo(json.loads(args.salida.read_text(encoding='utf-8-sig'), object_pairs_hook=claves_unicas))
        print('Capa histórica validada: 25 cuadrículas, periodo 2019-2022.')
        return 0
    if len({p.resolve() for p in (args.origen, args.salida, args.informe)}) != 3:
        raise ValueError('Use archivos distintos para origen, salida e informe')
    print('PROYECTO: RutaInformada Quito — datos históricos de robos 2019-2022')
    print('FUENTE:', URL)
    print('Uso: exploratorio LOCAL, licencia para redistribución pendiente de verificar.')
    print('Privacidad: solo conteos por cuadrícula; no se descargan puntos ni direcciones.')
    features = extraer_features(args.origen)

    fuente = consultar('', {})
    if fuente.get('geometryType') != 'esriGeometryPoint' or fuente.get('name') != 'Robo_personas':
        raise RuntimeError('Cambió el servicio o su geometría: detener y revisar')
    campos = {f.get('name') for f in fuente.get('fields', [])}
    if 'FECHA_DEL_' not in campos:
        raise RuntimeError('No existe FECHA_DEL_ en la fuente')

    control = consultar_conteo(','.join(map(str, BBOX)), tipo='envelope')
    print('Total de robos 2019-2022 en la BBOX:', control)
    if control == 0:
        raise RuntimeError('La fuente no devolvió registros para el periodo; no generar capa')

    salidas = []
    conteo_sumado = 0
    seen = set()
    for indice, feature in enumerate(features, start=1):
        g = shape(feature.get('geometry'))
        if not g.is_valid or g.is_empty or not isinstance(g, (Polygon, MultiPolygon)):
            raise ValueError(f'Cuadrícula {indice}: geometría no poligonal, vacía o inválida')
        clipped = g.intersection(BBOX_GEOM)
        if not clipped.is_valid:
            raise ValueError(f'Cuadrícula {indice}: recorte inválido')
        props = feature.get('properties') or {}
        idc = str(feature.get('id', props.get('cell_id', props.get('celda_id', f'celda-{indice:02d}'))))
        if idc in seen:
            raise ValueError(f'Identificador repetido: {idc}')
        seen.add(idc)
        # El GeoJSON de salida solo contiene celdas recortadas al rectángulo piloto.
        a = area_km2(clipped) if not clipped.is_empty else 0.0
        if a <= 1e-8:
            # Las celdas sin intersección no pueden aparecer en este overlay.
            continue
        n = consultar_conteo(armar_geometria_esri(clipped), tipo='polygon')
        conteo_sumado += n
        print(f'  Cuadrícula {indice:02d}/25 consultada')
        salidas.append({'id': idc, 'g': clipped, 'n': n, 'a': a, 'densidad': n/a})
        time.sleep(0.15)

    if not salidas:
        raise RuntimeError('Las cuadrículas no intersecan la zona piloto')
    # Una cuadrícula puede compartir frontera con otra: las intersecciones en frontera
    # ocasionalmente cuentan dos veces un punto. También podemos detectar huecos.
    diferencia = conteo_sumado-control
    if diferencia:
        raise ValueError('La suma de las celdas difiere del conteo de control. Revise huecos y bordes compartidos.')

    # Densidad anualizada NO es riesgo: solo registros por km² durante cuatro años.
    densidades = [v['densidad'] for v in salidas if v['n'] >= UMBRAL_PRIVACIDAD and v['a'] >= 0.2]
    p50 = percentil_ordenado(densidades, 0.50)
    p75 = percentil_ordenado(densidades, 0.75)
    salida_features = []
    for v in salidas:
        n, area, den = v['n'], v['a'], v['densidad']
        if n == 0:
            categoria, color = 'sin_registros_en_esta_fuente', '#bec7c9'
        elif n < UMBRAL_PRIVACIDAD:
            categoria, color = 'uno_a_cuatro_registros', '#d6b2ad'
        elif area < 0.2:
            categoria, color = 'celda_parcial_no_comparable', '#a6a6a6'
        elif p75 is not None and den >= p75:
            categoria, color = 'mayor_concentracion_historica_relativa', '#bb2d28'
        elif p50 is not None and den >= p50:
            categoria, color = 'concentracion_historica_intermedia', '#e27d57'
        else:
            categoria, color = 'menor_concentracion_historica_relativa', '#f1c5a2'
        salida_features.append({
            'type': 'Feature', 'id': v['id'],
            'geometry': mapping(v['g']),
            'properties': {
                'celda_id': v['id'],
                'periodo': '2019-2022',
                'tipo': 'robo_a_personas',
                'numero_registros': n if n >= UMBRAL_PRIVACIDAD else (0 if n == 0 else None),
                'rango_registros': '1-4' if 0 < n < UMBRAL_PRIVACIDAD else None,
                'area_km2': round(area, 5),
                'densidad_registros_periodo_km2': round(den, 3) if n >= UMBRAL_PRIVACIDAD and area >= 0.2 else None,
                'nivel': categoria,
                'color_sugerido': color,
                'advertencia': 'Datos históricos 2019-2022; NO alertas de delito actual ni riesgo individual.',
            }
        })

    doc = {'type': 'FeatureCollection', 'features': salida_features, 'metadata': {
        'proyecto': 'RutaInformada Quito', 'periodo': '2019-2022',
        'fuente': URL, 'version_procesador': VERSION,
        'uso': 'ANALISIS LOCAL; redistribucion y calidad geoespacial no verificadas',
        'metodologia': 'Conteos ArcGIS de robos a personas por interseccion espacial con las cuadrículas de la demo recortadas a la BBOX',
        'privacidad': 'No se descargaron puntos individuales; los conteos de 1-4 se ocultan',
        'alerta': 'El color refleja concentraciones de registros antiguos, no probabilidades actuales ni calles peligrosas',
    }}
    informe = {
        'proyecto': 'RutaInformada Quito', 'fecha_consulta_utc': datetime.now(timezone.utc).isoformat(),
        'estado_licencia': 'NO_VERIFICADA_NO_PUBLICAR',
        'fuente': URL, 'periodo': '2019-2022', 'bboxes_wgs84': list(BBOX),
        'conteo_bbox': control, 'suma_conteos_celdas': conteo_sumado,
        'diferencia_control': diferencia, 'n_cuadriculas_salida': len(salidas),
        'n_celdas_con_1_a_4': sum(0 < v['n'] < 5 for v in salidas),
        'n_celdas_sin_registros': sum(v['n'] == 0 for v in salidas),
        'umbral_ocultacion': UMBRAL_PRIVACIDAD,
        'n_celdas_mayor_concentracion': sum(f['properties']['nivel'] == 'mayor_concentracion_historica_relativa' for f in salida_features),
        'nota': 'La suma puede diferir por puntos en límites compartidos. El mapa no refleja delincuencia actual.',
    }
    validar_demo(doc)
    guardar_json(args.informe, informe)
    guardar_json(args.salida, doc)
    print('\nGeoJSON creado:', args.salida)
    print('Auditoría creada:', args.informe)
    print('Cuadrículas:', len(salidas), ' | BBOX:', control, ' | suma celdas:', conteo_sumado)
    print('IMPORTANTE: NO SUBIR A GITHUB sin confirmar permisos y revisar resultados.')
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError) as exc:
        print('ERROR:', str(exc), file=sys.stderr)
        raise SystemExit(1)
