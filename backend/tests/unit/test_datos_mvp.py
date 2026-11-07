import hashlib
import json
from pathlib import Path
import sys

import pytest
import datos_mvp as datos
import grafo
import predicciones


@pytest.fixture
def entrega(tmp_path):
    manifest = {"version": datos.VERSION_DATOS, "periodo": "2026-06", "archivos": {}}
    for rol, nombre in datos.RUTAS.items():
        file = tmp_path / nombre
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_bytes(b"ejemplo")
        manifest["archivos"][rol] = {"ruta": nombre, "bytes": 7, "sha256": hashlib.sha256(b"ejemplo").hexdigest()}
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path, path


def test_entrega_verificada_desde_otro_directorio(entrega, monkeypatch, tmp_path):
    raiz, manifiesto = entrega
    monkeypatch.chdir(tmp_path.parent)
    for rol in datos.RUTAS:
        assert datos.verificar_archivo(rol, raiz, manifiesto)["version"] == datos.VERSION_DATOS


@pytest.mark.parametrize("defecto", ["ausente", "tamano", "sha256", "version", "periodo", "ruta", "manifiesto"])
def test_rechaza_entregas_incompatibles(entrega, defecto):
    raiz, manifiesto = entrega
    archivo = raiz / datos.RUTAS["grafo"]
    if defecto == "ausente":
        archivo.unlink()  # Sólo fixture temporal sintético.
    elif defecto in ("tamano", "sha256"):
        archivo.write_bytes(b"otro" if defecto == "tamano" else b"cambiado"[:7])
    elif defecto == "manifiesto":
        manifiesto.write_text("{", encoding="utf-8")
    else:
        d = json.loads(manifiesto.read_text())
        if defecto == "ruta":
            d["archivos"]["grafo"]["ruta"] = "otra.graphml"
        else:
            d[defecto] = "otra"
        manifiesto.write_text(json.dumps(d))
    with pytest.raises(RuntimeError, match="Datos MVP no válidos"):
        datos.verificar_archivo("grafo", raiz, manifiesto)


def test_cargadores_aplican_integridad_antes_de_leer(monkeypatch):
    def invalido(rol):
        raise RuntimeError(f"SHA-256 incorrecto: {rol}")
    monkeypatch.setattr(grafo, "verificar_archivo", invalido)
    monkeypatch.setattr(predicciones, "verificar_archivo", invalido)
    # __wrapped__ evita alterar la caché de integración del proceso de pytest.
    with pytest.raises(RuntimeError, match="SHA-256 incorrecto"):
        grafo.cargar_grafo.__wrapped__(datos.ROOT / datos.RUTAS["grafo"])
    with pytest.raises(predicciones.PrediccionesNoDisponibles, match="SHA-256 incorrecto"):
        predicciones.leer_predicciones(datos.ROOT / datos.RUTAS["predicciones"])


def test_empaquetado_no_sobrescribe_y_es_repetible(entrega, monkeypatch):
    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
    import distribuir_mvp
    raiz, manifiesto = entrega
    monkeypatch.setattr(distribuir_mvp, "MANIFIESTO", manifiesto)
    monkeypatch.setattr(distribuir_mvp, "verificar_archivo", lambda rol, root: datos.verificar_archivo(rol, root, manifiesto))
    uno, dos = raiz / "uno.zip", raiz / "dos.zip"
    assert distribuir_mvp.empaquetar(raiz, uno)["sha256"] == distribuir_mvp.empaquetar(raiz, dos)["sha256"]
    with pytest.raises(FileExistsError):
        distribuir_mvp.empaquetar(raiz, uno)
