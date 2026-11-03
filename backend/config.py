"""Rutas de archivos y parámetros de la demostración validada."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
GRAFO = ROOT / "red_vial" / "quito_demo_con_predicciones.graphml"

ALPHAS = [0.25, 0.5, 1, 2, 4, 8, 16]
DESVIO_MAX = 0.15
MAX_AJUSTE_M = 300
PERIODO = "2026-06"

