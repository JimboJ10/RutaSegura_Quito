import pytest

from config import leer_origenes_cors


def test_origenes_locales_predeterminados(monkeypatch):
    monkeypatch.delenv("RUTASEGURA_CORS_ORIGINS", raising=False)
    assert leer_origenes_cors() == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_origenes_de_despliegue_sustituyen_los_locales(monkeypatch):
    monkeypatch.setenv("RUTASEGURA_CORS_ORIGINS", " https://ruta.example/, https://ruta.example,https://demo.example ")
    assert leer_origenes_cors() == ("https://ruta.example", "https://demo.example")


def test_lista_vacia_deshabilita_acceso_cruzado(monkeypatch):
    monkeypatch.setenv("RUTASEGURA_CORS_ORIGINS", "")
    assert leer_origenes_cors() == ()


@pytest.mark.parametrize("valor", ["*", "https://*.example", "null", "ftp://ruta.example", "https://ruta.example/api", "https://ruta.example?x=1", "https://ruta.example#mapa", "https://usuario:clave@ruta.example", "http://localhost:abc", "http://localhost:99999"])
def test_rechaza_origenes_invalidos(monkeypatch, valor):
    monkeypatch.setenv("RUTASEGURA_CORS_ORIGINS", valor)
    with pytest.raises(ValueError, match="RUTASEGURA_CORS_ORIGINS"):
        leer_origenes_cors()
