"""Esquemas de entrada de la API, con sus validaciones originales."""

from pydantic import BaseModel, Field


class Coordenada(BaseModel):
    lat: float = Field(ge=-90, le=90)
    lon: float = Field(ge=-180, le=180)


class SolicitudRuta(BaseModel):
    origen: Coordenada
    destino: Coordenada

