"""Descarga de la actualización: sha256 contra el digest de la API de releases, con timeout. Sin red (mock)."""

import hashlib
import io
import json

import pytest

from partes_salida import actualizaciones as act

VERSION = "9.9.9"
NOMBRE = f"PartesDeSalida-{VERSION}-Windows-Setup.exe"
URL = f"{act.DESCARGAS_WEB}/v{VERSION}/{NOMBRE}"
API_TAG = f"https://api.github.com/repos/{act.REPO}/releases/tags/v{VERSION}"
CONTENIDO = b"instalador ficticio " * 5000


class _Respuesta(io.BytesIO):
    def __init__(self, datos: bytes, url: str):
        super().__init__(datos)
        self.headers = {"Content-Length": str(len(datos))}
        self._url = url

    def geturl(self):
        return self._url


@pytest.fixture
def red(monkeypatch):
    """Sustituye urlopen: la API da el digest que se pida y la descarga, el contenido que se pida."""
    estado = {"digest": "sha256:" + hashlib.sha256(CONTENIDO).hexdigest(), "contenido": CONTENIDO, "pedidas": []}

    def urlopen(req, timeout=None, context=None):
        url = req.full_url if hasattr(req, "full_url") else req
        estado["pedidas"].append((url, timeout))
        if url == API_TAG:
            assets = [{"name": NOMBRE, "browser_download_url": URL}]
            if estado["digest"] is not None:
                assets[0]["digest"] = estado["digest"]
            return _Respuesta(json.dumps({"tag_name": f"v{VERSION}", "assets": assets}).encode(), url)
        if url == URL:
            return _Respuesta(estado["contenido"], url)
        raise AssertionError(f"URL inesperada: {url}")

    monkeypatch.setattr(act.urllib.request, "urlopen", urlopen)
    return estado


def test_digest_del_asset_lee_la_api_de_releases(red):
    assert act.digest_del_asset(URL) == hashlib.sha256(CONTENIDO).hexdigest()


def test_digest_del_asset_sin_digest_o_con_formato_raro_es_vacio(red):
    red["digest"] = None
    assert act.digest_del_asset(URL) == ""
    red["digest"] = "md5:abc"
    assert act.digest_del_asset(URL) == ""


def test_digest_de_una_url_ajena_no_consulta_nada(red):
    assert act.digest_del_asset("https://ejemplo.example.com/v1/x.exe") == ""
    assert red["pedidas"] == []


def test_descarga_correcta_se_guarda_y_avanza(red, tmp_path):
    destino = tmp_path / NOMBRE
    avances = []
    assert act.descargar_verificado(URL, destino, avances.append) == destino
    assert destino.read_bytes() == CONTENIDO
    assert avances and avances[-1] == 100


def test_descarga_manipulada_se_borra_y_no_se_abre(red, tmp_path):
    red["contenido"] = CONTENIDO + b"cambiado"
    destino = tmp_path / NOMBRE
    with pytest.raises(act.DescargaNoVerificada, match="no coincide"):
        act.descargar_verificado(URL, destino)
    assert not destino.exists()


def test_sin_digest_no_se_descarga(red, tmp_path):
    red["digest"] = None
    destino = tmp_path / NOMBRE
    with pytest.raises(act.DescargaNoVerificada, match="comprobar"):
        act.descargar_verificado(URL, destino)
    assert not destino.exists()
    assert [u for u, _ in red["pedidas"]] == [API_TAG]


def test_toda_peticion_lleva_timeout(red, tmp_path):
    act.descargar_verificado(URL, tmp_path / NOMBRE)
    assert red["pedidas"] and all(t for _, t in red["pedidas"])


def test_url_no_de_confianza_se_rechaza(red, tmp_path):
    with pytest.raises(ValueError):
        act.descargar_verificado("http://github.com/x/releases/download/v1/x.exe", tmp_path / "x.exe")
    assert red["pedidas"] == []


@pytest.mark.ui
def test_el_dialogo_no_abre_un_instalador_manipulado(qtbot, red, tmp_path):
    from partes_salida.ui.dialogos import _Descargador

    red["contenido"] = CONTENIDO + b"cambiado"
    hilo = _Descargador(URL, tmp_path / NOMBRE)
    listos, errores = [], []
    hilo.listo.connect(listos.append)
    hilo.error.connect(errores.append)
    hilo.run()  # en este hilo: sin red ni espera
    assert listos == []
    assert errores and "no coincide" in errores[0]
    assert not (tmp_path / NOMBRE).exists()


def test_en_macos_la_descarga_sustituye_la_app_donde_esta(monkeypatch, tmp_path):
    """macOS ya no abre el DMG sin más: lo pasa a `actualizar_mac` con la carpeta de registros."""
    from partes_salida import actualizar_mac
    from partes_salida.rutas import carpeta_datos

    pedidas, abiertos = [], []
    monkeypatch.setattr(act.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(act, "abrir_instalador", abiertos.append)
    monkeypatch.setattr(
        actualizar_mac,
        "instalar",
        lambda dmg, registros: pedidas.append((dmg, registros)) or actualizar_mac.Resultado(False, "arrástrala"),
    )
    assert act.instalar_descarga(str(tmp_path / "x.dmg")) == "arrástrala"
    assert pedidas == [(tmp_path / "x.dmg", carpeta_datos() / "logs")]
    assert abiertos == []


def test_en_windows_la_descarga_abre_el_instalador(monkeypatch):
    abiertos = []
    monkeypatch.setattr(act.platform, "system", lambda: "Windows")
    monkeypatch.setattr(act, "abrir_instalador", abiertos.append)
    assert act.instalar_descarga("C:\\temp\\instalador.exe") == ""
    assert abiertos == ["C:\\temp\\instalador.exe"]
