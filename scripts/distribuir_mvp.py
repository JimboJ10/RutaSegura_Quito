"""Verifica datos locales o empaqueta una entrega reproducible, sin sobrescribirla."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from datos_mvp import MANIFIESTO, RUTAS, VERSION_DATOS, verificar_archivo


def empaquetar(raiz, destino):
    for rol in RUTAS:
        verificar_archivo(rol, raiz)
    destino = Path(destino)
    destino.parent.mkdir(parents=True, exist_ok=True)
    # Modo x: jamás sobrescribe una entrega anterior. Sólo se leen los datos.
    with ZipFile(destino, "x", compression=ZIP_DEFLATED, compresslevel=6) as paquete:
        for nombre in sorted([*RUTAS.values(), "backend/datos_mvp.manifest.json"]):
            archivo = MANIFIESTO if nombre.startswith("backend/") else Path(raiz) / nombre
            info = ZipInfo(nombre, date_time=(2026, 11, 4, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            paquete.writestr(info, archivo.read_bytes(), compresslevel=6)
    with destino.open("rb") as archivo:
        digest = hashlib.file_digest(archivo, "sha256").hexdigest()
    return {"archivo": str(destino), "sha256": digest, "version": VERSION_DATOS}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("accion", choices=["verificar", "empaquetar"])
    parser.add_argument("--raiz", type=Path, default=ROOT, help="Raíz del repositorio o de la entrega extraída")
    args = parser.parse_args()
    try:
        resultado = ([verificar_archivo(rol, args.raiz) for rol in RUTAS] if args.accion == "verificar"
                     else empaquetar(args.raiz, ROOT / "entregas" / f"{VERSION_DATOS}.zip"))
    except (RuntimeError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")
    print(json.dumps(resultado, indent=2, ensure_ascii=False))
