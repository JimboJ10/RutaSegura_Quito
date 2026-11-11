"""Diagnostico SOLO LECTURA de fuente publica ArcGIS de robos en Quito.

No descarga direcciones ni puntos individuales; solo conteos agregados.
Es un servicio de tercero no controlado por RutaInformada.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

BASE = (
    'https://services1.arcgis.com/UOl0yzPDLol8nS3m/ArcGIS/rest/'
    'services/Robo_personas_view/FeatureServer/0'
)
# Envolvente aproximada de la demo original de RutaInformada Quito, WGS84.
BBOX = '-78.515,-0.215,-78.478,-0.173'


def pedir_json(ruta: str, params: dict[str, str]) -> dict:
    query = urlencode({**params, 'f': 'json'})
    url = f'{BASE}{ruta}?{query}'
    req = Request(url, headers={'User-Agent': 'RutaInformada-Quito-auditoria-academica/1.0'})
    with urlopen(req, timeout=18) as resp:
        data = json.load(resp)
    if 'error' in data:
        err = data['error']
        raise RuntimeError(f"ArcGIS: {err.get('message', 'Error')}; {err.get('details', [])}")
    return data


def contar(where: str = '1=1', bbox: bool = False) -> int:
    args = {'where': where, 'returnCountOnly': 'true'}
    if bbox:
        args.update({
            'geometry': BBOX,
            'geometryType': 'esriGeometryEnvelope',
            'inSR': '4326',
            'spatialRel': 'esriSpatialRelIntersects',
        })
    return int(pedir_json('/query', args)['count'])


def main():
    print('FUENTE: ArcGIS Robo_personas_view — Quito')
    print('URL:', BASE)
    print('DEMOSTRACION: BBOX WGS84', BBOX)
    print('Comprobacion en linea:', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC'))
    print('Privacidad: solo se consultan conteos; NO se guardan puntos o direcciones.\n')
    try:
        m = pedir_json('', {})
        print('Nombre capa:', m.get('name'))
        raw = m.get('editingInfo', {}).get('lastEditDate')
        if raw:
            print('Ultima edicion declarada:', datetime.fromtimestamp(raw/1000, tz=timezone.utc).isoformat())
        print('Registros de todo el servicio:', contar())
        print('Registros dentro de la BBOX de la demo:', contar(bbox=True))
    except (URLError, HTTPError, TimeoutError, ValueError, KeyError, RuntimeError) as e:
        print('ERROR en servicio o conexion:', str(e)[:350])
        print('No se pudo validar la disponibilidad real. No usar el dataset sin verificar.')
        return

    print('\nConteos por fecha del hecho (FECHA_DEL_), dentro de la BBOX:')
    for year in range(2019, 2027):
        where = f"FECHA_DEL_ >= DATE '{year}-01-01' AND FECHA_DEL_ < DATE '{year+1}-01-01'"
        try:
            print(f'  {year}: {contar(where, bbox=True)}')
        except (URLError, HTTPError, TimeoutError, ValueError, KeyError, RuntimeError) as e:
            print(f'  {year}: consulta no disponible ({str(e)[:110]})')
    print('\nINTERPRETACION: esta verificacion no comprueba exactitud de ubicacion ni licencia')
    print('de redistribucion. No usar puntos como advertencias de delito actual.')


if __name__ == '__main__':
    main()
