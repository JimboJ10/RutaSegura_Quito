"""Servidor de ensayo aislado. main:app y config.GRAFO permanecen intactos."""
import argparse
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))


def crear_app(ruta):
    from contextlib import asynccontextmanager
    from fastapi import FastAPI
    from fastapi.exceptions import RequestValidationError
    from fastapi.middleware.cors import CORSMiddleware
    from api import router, error_interno, error_validacion
    from config import CORS_ORIGINS
    from grafo import cargar_grafo

    @asynccontextmanager
    async def lifespan(app):
        app.state.grafo = cargar_grafo(ruta)
        yield

    app = FastAPI(title="Ensayo local de acceso peatonal", lifespan=lifespan,
                  exception_handlers={RequestValidationError: error_validacion, Exception: error_interno})
    app.add_middleware(CORSMiddleware, allow_origins=list(CORS_ORIGINS), allow_credentials=False,
                       allow_methods=["GET", "POST"], allow_headers=["Content-Type"])
    app.include_router(router)
    return app


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cobertura", choices=["demo", "ampliada"], required=True)
    parser.add_argument("--puerto", type=int, default=8802)
    args = parser.parse_args()
    os.environ["RUTAINFORMADA_COBERTURA"] = args.cobertura
    ruta = ROOT / f"red_vial/acceso_peatonal_v1/quito_{args.cobertura}_peatonal_filtrado.graphml"
    import uvicorn
    uvicorn.run(crear_app(ruta), host="127.0.0.1", port=args.puerto)
