"""Identidad de los dos archivos del MVP; no descarga, transforma ni imputa datos."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFIESTO = Path(__file__).with_name("datos_mvp.manifest.json")
VERSION_DATOS = "demo-peatonal-v1-2026-11-04"
RUTAS = {
    "grafo": "red_vial/acceso_peatonal_v1/quito_demo_peatonal_filtrado.graphml",
    "predicciones": "resultados/predicciones_demo_junio2026.geojson",
}


def verificar_archivo(rol, raiz=ROOT, manifiesto=MANIFIESTO):
    """Comprueba la entrega contra el manifiesto del código, incluso desde otro cwd."""
    try:
        datos = json.loads(Path(manifiesto).read_text(encoding="utf-8"))
        if datos["version"] != VERSION_DATOS or datos["periodo"] != "2026-06":
            raise ValueError(f"versión incompatible; se requiere {VERSION_DATOS}, periodo 2026-06")
        entrada = datos["archivos"][rol]
        if entrada["ruta"] != RUTAS[rol]:
            raise ValueError(f"ruta incompatible para {rol}")
        ruta = Path(raiz) / RUTAS[rol]
        if not ruta.is_file():
            raise ValueError(f"falta el archivo {ruta}")
        if ruta.stat().st_size != entrada["bytes"]:
            raise ValueError(f"tamaño incorrecto: {ruta}")
        with ruta.open("rb") as archivo:
            digest = hashlib.file_digest(archivo, "sha256").hexdigest()
        if digest != entrada["sha256"]:
            raise ValueError(f"SHA-256 incorrecto: {ruta}")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise RuntimeError(f"Datos MVP no válidos ({rol}): {exc}. Obtenga la entrega {VERSION_DATOS} del equipo; no se usará otra red.") from exc
    return {"ruta": RUTAS[rol], "sha256": digest, "version": VERSION_DATOS}
