"""Esquemas de entrada de la API, con sus validaciones originales."""

from pydantic import BaseModel, Field, field_validator


class Coordenada(BaseModel):
    lat: float = Field(ge=-90, le=90, allow_inf_nan=False)
    lon: float = Field(ge=-180, le=180, allow_inf_nan=False)

    @field_validator("lat", "lon", mode="before")
    @classmethod
    def rechazar_booleanos(cls, valor):
        if isinstance(valor, bool):
            raise ValueError("La coordenada debe ser numérica, no un booleano")
        return valor


class SolicitudRuta(BaseModel):
    origen: Coordenada
    destino: Coordenada

