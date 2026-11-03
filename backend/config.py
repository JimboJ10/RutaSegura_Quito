"""Rutas de archivos y parámetros de la demostración validada."""

from pathlib import Path
import os
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
GRAFO = ROOT / "red_vial" / "quito_demo_con_predicciones.graphml"
PREDICCIONES = ROOT / "resultados" / "predicciones_demo_junio2026.geojson"
PROYECTO = "RutaInformada Quito"
VERSION_API = "0.1.0"

ALPHAS = [0.25, 0.5, 1, 2, 4, 8, 16]
DESVIO_MAX = 0.15
MAX_AJUSTE_M = 300
PERIODO = "2026-06"
CRS_ESPERADO = "EPSG:4326"
# Tolerancia numérica en grados; no permite unir tramos separados en la calle.
TOLERANCIA_COORDENADAS = 1e-9


def leer_origenes_cors():
    """La variable de entorno sustituye la lista local; requiere reiniciar la API."""
    valor = os.environ.get(
        "RUTASEGURA_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    origenes = []
    for entrada in valor.split(","):
        origen = entrada.strip().rstrip("/")
        if not origen:
            continue
        try:
            partes = urlsplit(origen)
            puerto = partes.port  # También valida puertos no numéricos o fuera de rango.
            valido = (
                partes.scheme in ("http", "https") and partes.hostname
                and not any((partes.path, partes.query, partes.fragment, partes.username,
                             partes.password, "*" in origen))
            )
        except ValueError:
            valido = False
        if not valido:
            raise ValueError("RUTASEGURA_CORS_ORIGINS debe contener orígenes HTTP(S) explícitos, sin rutas ni comodines")
        if origen not in origenes:
            origenes.append(origen)
    return tuple(origenes)


CORS_ORIGINS = leer_origenes_cors()

