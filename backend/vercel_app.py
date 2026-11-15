"""Vercel forwards the original path to the container."""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from main import app as api, lifespan


@asynccontextmanager
async def startup(_app):
    # Mounted applications do not receive ASGI lifespan events themselves.
    async with lifespan(api):
        yield


app = FastAPI(lifespan=startup, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/api", api)
