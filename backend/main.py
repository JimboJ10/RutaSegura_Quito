"""Punto de entrada de FastAPI para RutaSegura Quito."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from api import error_interno, error_validacion, router
from grafo import cargar_grafo


@asynccontextmanager
async def lifespan(app: FastAPI):
    # La carga y preparación se completan antes de aceptar peticiones.
    # cargar_grafo conserva el resultado si se reinicia este ciclo en el proceso.
    app.state.grafo = cargar_grafo()
    yield


app = FastAPI(
    title="RutaSegura Quito API",
    version="0.1.0",
    description="Comparador experimental de rutas peatonales",
    lifespan=lifespan,
    exception_handlers={
        RequestValidationError: error_validacion,
        Exception: error_interno,
    },
)
app.include_router(router)
