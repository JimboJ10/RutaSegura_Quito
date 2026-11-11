"""Capa agregada local. Se carga solo al consultar el histórico."""
import json
import math
from typing import Annotated, Literal

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import Field, FiniteFloat
from shapely.geometry import MultiLineString, shape
from shapely.errors import ShapelyError

from config import ROOT

ARCHIVO = ROOT / "resultados/delincuencia_exploratoria/robos_historicos_2019_2022_cuadriculas.geojson"
ALTA = "mayor_concentracion_historica_relativa"
NIVELES = {ALTA, "concentracion_historica_intermedia", "menor_concentracion_historica_relativa",
           "uno_a_cuatro_registros", "sin_registros_en_esta_fuente", "celda_parcial_no_comparable"}
router = APIRouter(prefix="/robos-historicos")
Punto = tuple[Annotated[FiniteFloat, Field(ge=-180, le=180)], Annotated[FiniteFloat, Field(ge=-90, le=90)]]
Linea = Annotated[list[Punto], Field(min_length=2)]
Modalidad = Literal["corta", "historica", "lightgbm"]


def leer_capa():
    try:
        datos = json.loads(ARCHIVO.read_text(encoding="utf-8-sig"))
        features = []
        ids = set()
        if datos["type"] != "FeatureCollection" or len(datos["features"]) != 25:
            raise ValueError("Colección incompleta")
        for feature in datos["features"]:
            props = feature["properties"]
            celda = props["celda_id"]
            geom = shape(feature["geometry"])
            if (geom.geom_type != "Polygon" or geom.is_empty or not geom.is_valid or geom.has_z
                    or not isinstance(celda, str) or celda in ids):
                raise ValueError("Cuadrícula inválida")
            oeste, sur, este, norte = geom.bounds
            n, area, densidad = (props[k] for k in ("numero_registros", "area_km2", "densidad_registros_periodo_km2"))
            oculto = n is None and props["rango_registros"] == "1-4"
            if (not (-180 <= oeste < este <= 180 and -90 <= sur < norte <= 90)
                    or props["tipo"] != "robo_a_personas" or props["periodo"] != "2019-2022"
                    or props["nivel"] not in NIVELES or not math.isfinite(area) or area <= 0
                    or not (oculto or (type(n) is int and (n == 0 or n >= 5)))
                    or (oculto and densidad is not None)
                    or (densidad is not None and (not math.isfinite(densidad) or densidad < 0))):
                raise ValueError("Datos de cuadrícula inválidos")
            ids.add(celda)
            campos = ("celda_id", "periodo", "numero_registros", "rango_registros", "area_km2",
                      "densidad_registros_periodo_km2", "nivel")
            features.append({"type": "Feature", "geometry": geom.__geo_interface__,
                             "properties": {k: props[k] for k in campos}})
        return {"type": "FeatureCollection", "features": features}
    except (OSError, ValueError, TypeError, KeyError, AttributeError, IndexError, ShapelyError) as exc:
        raise HTTPException(503, "La capa local de robos históricos no está disponible.") from exc


class GeoJSONResponse(JSONResponse):
    media_type = "application/geo+json"


@router.get("", response_class=GeoJSONResponse, responses={503: {"description": "Capa local no disponible"}})
def cuadriculas():
    return GeoJSONResponse(leer_capa(), headers={"Cache-Control": "no-store"})


def partes_lineales(geom):
    """Extrae líneas con longitud positiva de una intersección, sin unir partes."""
    if geom.geom_type == "LineString" and geom.length > 0:
        yield list(geom.coords)
    elif geom.geom_type in ("GeometryCollection", "MultiLineString"):
        for parte in geom.geoms:
            yield from partes_lineales(parte)


@router.post("/cruces", responses={503: {"description": "Capa local no disponible"}})
def cruces(trazados: dict[Modalidad, Annotated[list[Linea], Field(min_length=1)]], detalle: bool = False):
    altas = [(f["properties"]["celda_id"], shape(f["geometry"])) for f in leer_capa()["features"]
             if f["properties"]["nivel"] == ALTA]
    resultado = {}
    for modalidad, lineas in trazados.items():
        ruta = MultiLineString(lineas)
        # DE-9IM: un tramo de longitud positiva en el interior; tocar el borde no cuenta.
        cruza = [(celda, zona) for celda, zona in altas if ruta.relate_pattern(zona, "1********")]
        zonas = [celda for celda, _ in cruza]
        if detalle:
            tramos = []
            for _, zona in cruza:
                interior = ruta.intersection(zona).difference(zona.boundary)
                tramos.extend(partes_lineales(interior))
            resultado[modalidad] = {"zonas": zonas, "tramos": tramos}
        else:
            resultado[modalidad] = zonas
    return resultado
