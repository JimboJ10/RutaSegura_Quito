"""Protege la carga diferida y la reutilización del grafo tras la extracción."""

from pathlib import Path
import subprocess
import sys
from textwrap import dedent


def test_grafo_se_carga_al_iniciar_y_se_reutiliza_en_el_proceso():
    # Un proceso aislado evita que la caché de otras pruebas oculte una recarga.
    # El espía observa la lectura real del GraphML; no sustituye sus datos.
    codigo = dedent("""
        from unittest.mock import patch

        import osmnx as ox
        from fastapi.testclient import TestClient

        with patch.object(ox, "load_graphml", wraps=ox.load_graphml) as lectura:
            import main

            assert lectura.call_count == 0, "Importar main no debe leer el GraphML"

            with TestClient(main.app) as cliente:
                assert lectura.call_count == 1
                grafo_inicial = main.app.state.grafo
                assert cliente.get("/health").status_code == 200
                respuesta = cliente.post("/rutas", json={
                    "origen": {"lat": -0.201, "lon": -78.504},
                    "destino": {"lat": -0.184, "lon": -78.486},
                })
                assert respuesta.status_code == 200, respuesta.text
                assert main.app.state.grafo is grafo_inicial
                assert lectura.call_count == 1, "Una petición no debe recargar el grafo"

            with TestClient(main.app) as cliente:
                assert main.app.state.grafo is grafo_inicial
                assert cliente.get("/health").status_code == 200

            assert lectura.call_count == 1, "El grafo debe reutilizarse en el proceso"
    """)
    resultado = subprocess.run(
        [sys.executable, "-B", "-X", "utf8", "-c", codigo],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
    )
    assert resultado.returncode == 0, resultado.stdout + resultado.stderr
