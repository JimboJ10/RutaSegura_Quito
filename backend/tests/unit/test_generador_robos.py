import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))
import generar_capa_robos_historicos_quito as generador


@pytest.fixture
def capa_sintetica(monkeypatch):
    filas = []
    for i in range(25):
        clave = f"prueba-{i:02d}"
        filas.append({"type": "Feature", "id": clave,
                      "geometry": {"type": "Polygon", "coordinates": [
                          [[i, 0], [i + 1, 0], [i + 1, 1], [i, 0]]]},
                      "properties": {"celda_id": clave, "numero_registros": None,
                                     "rango_registros": "1-4"}})
    doc = {"type": "FeatureCollection", "features": filas,
           "metadata": {"periodo": "2019-2022", "fuente": generador.URL}}
    contenido = json.dumps(doc, sort_keys=True, separators=(",", ":")).encode()
    monkeypatch.setattr(generador, "HUELLA_CONTENIDO", hashlib.sha256(contenido).hexdigest())
    return doc


def test_verificar_otro_formato_sin_red(tmp_path, monkeypatch, capa_sintetica):
    ruta = tmp_path / "local.geojson"
    capa_sintetica["features"].reverse()
    ruta.write_text(json.dumps(capa_sintetica, indent=3), encoding="utf-8-sig")
    monkeypatch.setattr(sys, "argv", ["generador", "--salida", str(ruta), "--verificar"])
    monkeypatch.setattr(generador, "consultar", lambda *a, **kw: pytest.fail("Consulta inesperada"))
    assert generador.main() == 0


@pytest.mark.parametrize("cambio", ["periodo", "fuente", "cobertura", "conteo", "geometria", "duplicado"])
def test_no_admite_cambios_de_datos(capa_sintetica, cambio):
    doc = capa_sintetica
    fila = doc["features"][0]
    if cambio in ("periodo", "fuente"):
        doc["metadata"][cambio] = "otro"
    elif cambio == "cobertura":
        doc["features"].pop()
    elif cambio == "conteo":
        fila["properties"]["numero_registros"] = 2
    elif cambio == "geometria":
        fila["geometry"]["coordinates"][0][1][0] += 0.01
    else:
        doc["features"][1] = fila
    with pytest.raises(ValueError):
        generador.validar_demo(doc)


def test_rechaza_claves_ambiguas():
    with pytest.raises(ValueError, match="repetidas"):
        json.loads('{"id":"a","id":"b"}', object_pairs_hook=generador.claves_unicas)


def test_desacuerdo_en_control_conserva_archivos(tmp_path, monkeypatch):
    from shapely.geometry import box, mapping

    cuadricula = mapping(box(*generador.BBOX))
    monkeypatch.setattr(generador, "extraer_features", lambda _: [
        {"id": str(i), "geometry": cuadricula} for i in range(25)])
    monkeypatch.setattr(generador, "consultar", lambda *args: {
        "geometryType": "esriGeometryPoint", "name": "Robo_personas",
        "fields": [{"name": "FECHA_DEL_"}]})
    monkeypatch.setattr(generador, "consultar_conteo",
                        lambda geometria, tipo: 26 if tipo == "envelope" else 1)
    monkeypatch.setattr(generador.time, "sleep", lambda _: None)
    salida, informe = tmp_path / "local.geojson", tmp_path / "auditoria.json"
    for p in (salida, informe):
        p.write_bytes(b"anterior")
    monkeypatch.setattr(sys, "argv", ["generador", "--salida", str(salida), "--informe", str(informe)])
    with pytest.raises(ValueError, match="conteo de control"):
        generador.main()
    assert salida.read_bytes() == informe.read_bytes() == b"anterior"


@pytest.mark.parametrize("conteo", [True, 2.5, -1, None, "10"])
def test_arcgis_debe_devolver_un_entero(monkeypatch, conteo):
    def servicio(ruta, params, **kwargs):
        assert ruta == "/query" and params["returnCountOnly"] == "true"
        assert params["where"] == generador.FECHAS_SQL and "outFields" not in params
        return {"count": conteo}

    monkeypatch.setattr(generador, "consultar", servicio)
    with pytest.raises(ValueError, match="conteo"):
        generador.consultar_conteo("0,0,1,1", tipo="envelope")
