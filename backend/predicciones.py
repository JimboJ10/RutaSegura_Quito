"""Lectura y caché de las predicciones retrospectivas ya calculadas."""

from functools import lru_cache
import json
import math
from pathlib import Path
from threading import Lock

from pyproj import CRS
from shapely.geometry import shape

from config import COBERTURA, CRS_ESPERADO, PERIODO, PREDICCIONES
from datos_mvp import ROOT as DATOS_ROOT, RUTAS, verificar_archivo


class PrediccionesNoDisponibles(RuntimeError):
    """El archivo no se puede servir como la capa de la demostración."""


def validar_predicciones(datos):
    """Valida sin transformar propiedades ni geometrías; devuelve su bbox."""
    if not isinstance(datos, dict) or datos.get("type") != "FeatureCollection":
        raise ValueError("Se requiere una FeatureCollection")
    features = datos.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("La colección no contiene cuadrículas")

    if "crs" in datos:
        crs = datos["crs"]
        if not isinstance(crs, dict) or crs.get("type") != "name":
            raise ValueError("CRS de predicciones inválido")
        nombre = crs.get("properties", {}).get("name")
        # El archivo existente declara CRS84: WGS84 con orden longitud-latitud.
        if not CRS.from_user_input(nombre).equals(
            CRS.from_user_input(CRS_ESPERADO), ignore_axis_order=True
        ):
            raise ValueError("Las predicciones deben usar coordenadas WGS84/EPSG:4326")

    anio, mes = (int(parte) for parte in PERIODO.split("-"))
    limites = []
    for indice, feature in enumerate(features):
        try:
            if not isinstance(feature, dict) or feature.get("type") != "Feature":
                raise ValueError("Se requiere un Feature")
            propiedades = feature.get("properties")
            if not isinstance(propiedades, dict):
                raise ValueError("Faltan las propiedades")
            if (propiedades.get("anio"), propiedades.get("mes")) != (anio, mes):
                raise ValueError(f"El periodo debe ser {PERIODO}")
            for campo in ("pred_historico", "pred_lightgbm_v2"):
                valor = propiedades.get(campo)
                if isinstance(valor, bool) or not isinstance(valor, (int, float)):
                    raise ValueError(f"'{campo}' debe ser numérico y estar presente")
                if not math.isfinite(valor) or valor < 0:
                    raise ValueError(f"'{campo}' debe ser finito y no negativo")
            geometria = feature.get("geometry")
            if not isinstance(geometria, dict) or geometria.get("type") not in ("Polygon", "MultiPolygon"):
                raise ValueError("Se requiere una geometría Polygon o MultiPolygon")
            poligonos = ([geometria["coordinates"]] if geometria["type"] == "Polygon"
                         else geometria["coordinates"])
            if not poligonos:
                raise ValueError("Geometría vacía")
            for poligono in poligonos:
                if not poligono:
                    raise ValueError("Polígono vacío")
                for anillo in poligono:
                    if len(anillo) < 4 or anillo[0] != anillo[-1]:
                        raise ValueError("Anillo sin cerrar o con menos de cuatro posiciones")
                    for posicion in anillo:
                        if len(posicion) != 2 or not all(
                            not isinstance(v, bool) and isinstance(v, (int, float))
                            and math.isfinite(v) for v in posicion
                        ):
                            raise ValueError("Las coordenadas deben ser pares numéricos finitos")
                        lon, lat = posicion
                        if not (-180 <= lon <= 180 and -90 <= lat <= 90):
                            raise ValueError("Coordenadas fuera de EPSG:4326")
            poligono = shape(geometria)
            if poligono.is_empty or not poligono.is_valid or poligono.area <= 0:
                raise ValueError("Geometría poligonal inválida")
            limites.append(poligono.bounds)
        except Exception as exc:
            raise ValueError(f"Cuadrícula {indice}: {exc}") from exc

    # También detecta valores no JSON en propiedades adicionales, sin eliminarlas.
    json.dumps(datos, allow_nan=False)
    return [min(b[0] for b in limites), min(b[1] for b in limites),
            max(b[2] for b in limites), max(b[3] for b in limites)]


def completar_fechas_ampliadas(datos):
    """Expone año y mes del contrato a partir del periodo del archivo ampliado."""
    features = datos["features"]
    if not isinstance(features, list) or len(features) != 99:
        raise ValueError("La capa ampliada requiere 99 cuadrículas")
    anio, mes = map(int, PERIODO.split("-"))
    celdas = set()
    for indice, feature in enumerate(features):
        propiedades = feature["properties"]
        if propiedades.get("periodo") != PERIODO:
            raise ValueError(f"Cuadrícula {indice}: el periodo debe ser {PERIODO}")
        celda = (propiedades.get("cx"), propiedades.get("cy"))
        if any(type(valor) is not int for valor in celda) or celda in celdas:
            raise ValueError(f"Cuadrícula {indice}: identificador de celda inválido o duplicado")
        celdas.add(celda)
        propiedades.setdefault("anio", anio)
        propiedades.setdefault("mes", mes)


def leer_predicciones(ruta):
    ruta = Path(ruta)
    try:
        if ruta.resolve() == (DATOS_ROOT / RUTAS["predicciones"]).resolve():
            verificar_archivo("predicciones")
        datos = json.loads(ruta.read_text(encoding="utf-8-sig"))
        if COBERTURA == "ampliada":
            completar_fechas_ampliadas(datos)
        bbox = validar_predicciones(datos)
    except Exception as exc:
        raise PrediccionesNoDisponibles(f"Predicciones no disponibles en '{ruta}': {exc}") from exc
    return datos, bbox


@lru_cache(maxsize=1)
def _predicciones_en_cache():
    return leer_predicciones(PREDICCIONES)


_carga_lock = Lock()


def cargar_predicciones():
    # Evita lecturas simultáneas en las primeras peticiones; no cachea errores.
    with _carga_lock:
        return _predicciones_en_cache()
