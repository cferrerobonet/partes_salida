"""Cifrado en reposo, firma del QR y que el repositorio público no lleve datos."""

import json
import subprocess
from datetime import datetime
from pathlib import Path

import pytest

from partes_salida.almacen import Almacen, DatosIlegibles
from partes_salida.cifrado import Cifrador, ErrorDeCifrado, guardar_secreto, leer_secreto
from partes_salida.firma import Firmante, de_b64url, verificar

RAIZ = Path(__file__).resolve().parents[1]


def test_cifrado_ida_y_vuelta_y_contexto():
    c = Cifrador.del_llavero()
    blob = c.cifrar(b"hola", b"a")
    assert c.descifrar(blob, b"a") == b"hola"
    with pytest.raises(ErrorDeCifrado):
        c.descifrar(blob, b"b")
    with pytest.raises(ErrorDeCifrado):
        Cifrador(b"\0" * 32).descifrar(blob, b"a")


def test_la_clave_se_reutiliza():
    assert Cifrador.del_llavero().huella("x") == Cifrador.del_llavero().huella("x")


def test_padron_cifrado_sin_texto_plano(datos, alumnos):
    almacen = Almacen(datos, Cifrador.del_llavero())
    almacen.guardar_padron(alumnos, "x.xls")
    crudo = (datos / "alumnado.bin").read_bytes()
    assert b"NEREA" not in crudo and b"ejemplo.es" not in crudo
    assert len(almacen.cargar_padron().alumnos) == len(alumnos)


def test_padron_con_otra_clave_avisa(datos, alumnos):
    Almacen(datos, Cifrador.del_llavero()).guardar_padron(alumnos, "x")
    with pytest.raises(DatosIlegibles):
        Almacen(datos, Cifrador(b"\1" * 32)).cargar_padron()


def test_limpiar_fotos_de_bajas(datos):
    almacen = Almacen(datos, Cifrador.del_llavero())
    almacen.guardar_foto("1", b"a")
    almacen.guardar_foto("2", b"b")
    assert almacen.limpiar_fotos(["1"]) == 1
    assert almacen.tiene_foto("1") and not almacen.tiene_foto("2")


def test_secretos_fuera_del_codigo():
    guardar_secreto("prueba", "valor")
    assert leer_secreto("prueba") == "valor"


def test_qr_firmado_y_verificable():
    f = Firmante.del_llavero()
    salida, exp = datetime(2026, 10, 8, 12, 30), datetime(2026, 10, 8, 9, 14)
    qr = f.contenido_qr("10519873", salida, exp)
    assert qr.startswith(f"PS1|{f.id_clave}|10519873|202610081230|202610080914|")
    v = verificar(qr, {f.id_clave: f.publica})
    assert v.valido and v.salida == salida and v.id_alumno == "10519873"


@pytest.mark.parametrize("cambio", [("1230", "1430"), ("10519873", "10519874")])
def test_qr_alterado_no_vale(cambio):
    f = Firmante.del_llavero()
    qr = f.contenido_qr("10519873", datetime(2026, 10, 8, 12, 30), datetime(2026, 10, 8, 9, 14))
    v = verificar(qr.replace(*cambio, 1), {f.id_clave: f.publica})
    assert not v.valido


def test_qr_de_otro_equipo_es_desconocido():
    f = Firmante.del_llavero()
    otro = Firmante(__import__("cryptography.hazmat.primitives.asymmetric.ed25519", fromlist=["x"]).Ed25519PrivateKey.generate())
    qr = otro.contenido_qr("1", datetime(2026, 1, 1), datetime(2026, 1, 1))
    assert verificar(qr, {f.id_clave: f.publica}).motivo.startswith("Firmado por un equipo desconocido")
    assert not verificar("hola", {}).valido


def test_vectores_para_la_app_android_siguen_valiendo():
    """`android/vectores_qr.json` es el contrato con la app del vigilante."""
    vectores = json.loads((RAIZ / "android" / "vectores_qr.json").read_text(encoding="utf-8"))
    claves = {vectores["id_clave"]: de_b64url(vectores["clave_publica"])}
    for caso in vectores["casos"]:
        assert verificar(caso["qr"], claves).valido is caso["valido"], caso["descripcion"]


def test_el_repositorio_no_lleva_datos_del_alumnado():
    try:
        salida = subprocess.run(["git", "ls-files"], cwd=RAIZ, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        pytest.skip("Sin git")
    archivos = salida.splitlines()
    datos = [f for f in archivos if f.lower().endswith((".xls", ".xlsx", ".zip", ".bin", ".jpg", ".jpeg", ".webp", ".heic"))]
    assert not datos, f"Archivos de datos en el repositorio: {datos}"
    permitidas = ("imagenes/", "src/partes_salida/recursos/", "docs/capturas/")
    imagenes = [f for f in archivos if f.lower().endswith((".png", ".gif", ".bmp", ".tif", ".tiff")) and not f.startswith(permitidas)]
    assert not imagenes, f"Imágenes fuera de las carpetas permitidas (¿fotos del alumnado?): {imagenes}"
    con_coma = [f for f in archivos if "," in Path(f).name]
    assert not con_coma, f"Archivos con forma «APELLIDOS, NOMBRE»: {con_coma}"
