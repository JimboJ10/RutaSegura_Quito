"""Verifica la evidencia guardada sin repetir cientos de cálculos de rutas."""
from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
from validar_cobertura_peatonal import DESTINO, muestrear, CAPAS
from auditar_acceso_peatonal import hash_archivo


@pytest.mark.parametrize("modo", ["demo", "ampliada"])
def test_muestra_evidencia_y_grafos_siguen_correspondiendo(modo):
    manifest = json.loads((DESTINO / "manifest.json").read_text(encoding="utf-8"))
    for file, digest in manifest["sha256_entradas"].items():
        assert hash_archivo(ROOT / file) == digest
    assert hash_archivo(ROOT / "scripts/validar_cobertura_peatonal.py") == manifest["sha256_codigo"]
    capa = json.loads(CAPAS[modo].read_text(encoding="utf-8-sig"))
    pares = json.loads((DESTINO / f"{modo}-pares.json").read_text(encoding="utf-8"))
    assert [p for p in pares if p["grupo"] == "muestra"] == muestrear(capa)
    registros = [json.loads(line) for line in (DESTINO / f"{modo}-peticiones.jsonl").read_text(encoding="utf-8").splitlines()]
    assert len(registros) == 230
    assert {(r["id"], r["version"]) for r in registros} == {(p["id"], v) for p in pares for v in ("original", "filtrado")}
    for r in registros:
        assert r["estado"] != "error_tecnico", r
        if r["estado"] == "evaluable":
            assert r["http"] == 200 and r["verificaciones_correctas"]
            assert len(r["rutas"]) == 3
            assert 1 <= r["geometrias_distintas"] <= 3
            assert max(r["ajustes_m"]) <= 300
            for route in r["rutas"].values():
                assert 0 <= route["desvio_pct"] <= 15 + 1e-6
                if r["version"] == "filtrado":
                    assert not route["restringidas"] and not route["inciertas"]
        else:
            assert r["http"] == 422
