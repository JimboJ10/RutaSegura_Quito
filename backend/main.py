"""Punto de entrada de FastAPI para RutaInformada Quito."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from api import error_interno, error_validacion, router, router_experimental
from config import CORS_ORIGINS, PROYECTO, VERSION_API
from grafo import cargar_grafo
from robos_historicos import router as robos_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # La carga y preparación se completan antes de aceptar peticiones.
    # cargar_grafo conserva el resultado si se reinicia este ciclo en el proceso.
    app.state.grafo = cargar_grafo()
    yield


app = FastAPI(
    title=f"{PROYECTO} API",
    version=VERSION_API,
    description="Comparador experimental de rutas peatonales",
    lifespan=lifespan,
    exception_handlers={
        RequestValidationError: error_validacion,
        Exception: error_interno,
    },
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(CORS_ORIGINS),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)
app.include_router(router)
app.include_router(robos_router)
app.include_router(router_experimental)
