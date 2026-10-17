"""macOS: la actualización sustituye la app allí donde está instalada (`actualizar_mac.py`).

Bundles falsos en `tmp_path` y `hdiutil`, `ditto`, `open`, `xattr` y `osascript`
simulados con scripts que apuntan lo que se les pide. El script auxiliar de
verdad se ejecuta (con bash), así que se prueba también la sustitución.
"""

import os
import plistlib
import stat
import subprocess
import sys
import threading

import pytest

from partes_salida import actualizar_mac as am

pytestmark = pytest.mark.skipif(sys.platform == "win32", reason="el script auxiliar es de bash")

IDENT = "es.example.app-de-prueba"

HDIUTIL_FALSO = r"""#!/bin/bash
echo "hdiutil $*" >> "$LLAMADAS"
case "$1" in
attach)
    base=""; previo=""
    for a in "$@"; do [ "$previo" = "-mountrandom" ] && base="$a"; previo="$a"; done
    punto="$base/volumen"
    mkdir -p "$punto"
    cp -R "$VOLUMEN_FALSO"/. "$punto"/
    cat <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict><key>system-entities</key><array>
<dict><key>content-hint</key><string>GUID_partition_scheme</string></dict>
<dict><key>mount-point</key><string>$punto</string></dict>
</array></dict></plist>
EOF
    ;;
esac
exit 0
"""

DITTO_BIEN = '#!/bin/bash\necho "ditto $*" >> "$LLAMADAS"\ncp -R "$1" "$2"\n'
#: Copia a medias y error: así falla de verdad una copia sin espacio en disco.
DITTO_MAL = '#!/bin/bash\necho "ditto $*" >> "$LLAMADAS"\nmkdir -p "$2"\nexit 1\n'
APUNTA = '#!/bin/bash\necho "{nombre} $*" >> "$LLAMADAS"\nexit 0\n'


def _ejecutable(ruta, texto):
    ruta.write_text(texto, encoding="utf-8")
    ruta.chmod(ruta.stat().st_mode | stat.S_IXUSR)
    return str(ruta)


def _bundle(carpeta, nombre, version, ident=IDENT):
    app = carpeta / nombre
    (app / "Contents" / "MacOS").mkdir(parents=True)
    with open(app / "Contents" / "Info.plist", "wb") as f:
        plistlib.dump({"CFBundleIdentifier": ident, "CFBundleShortVersionString": version}, f)
    ejecutable = app / "Contents" / "MacOS" / "ejecutable"
    ejecutable.write_text(version, encoding="utf-8")
    return app


def _version(app):
    with open(app / "Contents" / "Info.plist", "rb") as f:
        return plistlib.load(f)["CFBundleShortVersionString"]


def _pid_terminado():
    proceso = subprocess.Popen(["/bin/sh", "-c", "exit 0"])
    proceso.wait()
    return proceso.pid


def _en_el_sitio(orden):
    """Ejecuta el script auxiliar y espera a que acabe (en la app va separado)."""
    subprocess.run(orden, check=False, timeout=60)


@pytest.fixture
def entorno(tmp_path, monkeypatch):
    """Herramientas simuladas, una carpeta «EPLA» con la app vieja y un DMG con la nueva."""
    binarios = tmp_path / "bin"
    binarios.mkdir()
    llamadas = tmp_path / "llamadas.txt"
    llamadas.touch()
    monkeypatch.setenv("LLAMADAS", str(llamadas))
    monkeypatch.setattr(am, "HDIUTIL", _ejecutable(binarios / "hdiutil", HDIUTIL_FALSO))
    monkeypatch.setattr(am, "DITTO", _ejecutable(binarios / "ditto", DITTO_BIEN))
    for nombre in ("open", "xattr", "osascript"):
        ruta = _ejecutable(binarios / nombre, APUNTA.format(nombre=nombre))
        monkeypatch.setattr(am, nombre.upper(), ruta)
    monkeypatch.setattr(am, "ESPERA_CIERRE", 5)
    monkeypatch.setattr(am.tempfile, "tempdir", str(tmp_path / "temporal"))
    (tmp_path / "temporal").mkdir()

    instaladas = tmp_path / "Applications" / "EPLA"
    instaladas.mkdir(parents=True)
    volumen = tmp_path / "contenido-del-dmg"
    volumen.mkdir()
    (volumen / "Applications").symlink_to("/Applications")
    monkeypatch.setenv("VOLUMEN_FALSO", str(volumen))
    dmg = tmp_path / "temporal" / "App_v2_macOS.dmg"
    dmg.write_bytes(b"dmg de prueba")

    class Entorno:
        pass

    e = Entorno()
    e.instaladas, e.volumen, e.dmg, e.registros = instaladas, volumen, dmg, tmp_path / "logs"
    e.llamadas = lambda: llamadas.read_text(encoding="utf-8").splitlines()
    e.binarios = binarios
    return e


def _instalar(e, vieja, **extra):
    opciones = {
        "pid": _pid_terminado(),
        "ejecutable": str(vieja / "Contents" / "MacOS" / "ejecutable"),
        "congelada": True,
        "lanzar": _en_el_sitio,
    }
    opciones.update(extra)
    return am.instalar(e.dmg, e.registros, **opciones)


def _restos(carpeta):
    return sorted(p.name for p in carpeta.iterdir())


def test_bundle_en_uso_sale_del_ejecutable(tmp_path):
    app = _bundle(tmp_path, "App.app", "1.0")
    ejecutable = str(app / "Contents" / "MacOS" / "ejecutable")
    assert am.bundle_en_uso(ejecutable, congelada=True) == app.resolve()
    assert am.bundle_en_uso(ejecutable, congelada=False) is None
    assert am.bundle_en_uso(str(tmp_path / "python3"), congelada=True) is None


def test_sustituye_la_app_en_su_carpeta(entorno):
    vieja = _bundle(entorno.instaladas, "App de prueba.app", "1.0")
    _bundle(entorno.volumen, "App de prueba.app", "2.0")

    resultado = _instalar(entorno, vieja)

    assert resultado.sustituida, resultado.aviso
    assert _restos(entorno.instaladas) == ["App de prueba.app"], "ni copia temporal ni la vieja"
    assert _version(entorno.instaladas / "App de prueba.app") == "2.0"
    llamadas = entorno.llamadas()
    destino = str(entorno.instaladas / "App de prueba.app")
    assert any(ll.startswith("hdiutil attach -nobrowse -readonly -mountrandom") for ll in llamadas)
    assert f"xattr -dr com.apple.quarantine {destino}" in llamadas
    assert any(ll.startswith("hdiutil detach") for ll in llamadas)
    assert llamadas[-1] == f"open {destino}", "se abre la nueva al final, ya desmontado el DMG"
    assert not any(ll.startswith("osascript") for ll in llamadas)
    assert not entorno.dmg.exists()
    registro = resultado.registro.read_text(encoding="utf-8")
    assert "Actualización terminada" in registro


def test_el_nombre_cambia_y_la_vieja_se_retira(entorno):
    vieja = _bundle(entorno.instaladas, "App_De_Prueba.app", "1.0")
    _bundle(entorno.volumen, "App De Prueba Nueva.app", "2.0")

    assert _instalar(entorno, vieja).sustituida

    assert _restos(entorno.instaladas) == ["App De Prueba Nueva.app"], "no quedan las dos"
    assert _version(entorno.instaladas / "App De Prueba Nueva.app") == "2.0"
    assert entorno.llamadas()[-1] == f"open {entorno.instaladas / 'App De Prueba Nueva.app'}"


def test_si_falla_la_copia_se_queda_la_vieja_y_se_avisa(entorno, monkeypatch):
    monkeypatch.setattr(am, "DITTO", _ejecutable(entorno.binarios / "ditto", DITTO_MAL))
    vieja = _bundle(entorno.instaladas, "App_De_Prueba.app", "1.0")
    _bundle(entorno.volumen, "App De Prueba Nueva.app", "2.0")

    resultado = _instalar(entorno, vieja)

    assert resultado.sustituida, "el script se lanzó; el fallo llega después"
    assert _restos(entorno.instaladas) == ["App_De_Prueba.app"], "ni copia a medias ni nada borrado"
    assert _version(vieja) == "1.0"
    llamadas = entorno.llamadas()
    assert f"open {vieja}" in llamadas, "se vuelve a abrir la versión anterior"
    assert any(ll.startswith("osascript") and "No se pudo actualizar" in ll for ll in llamadas)
    assert any(ll.startswith("hdiutil detach") for ll in llamadas)
    assert "ERROR: No se pudo copiar" in resultado.registro.read_text(encoding="utf-8")


MV_QUE_FALLA_CON_LA_NUEVA = """#!/bin/bash
case "$(basename "$1")" in .actualizando-*) echo "mv: sin permiso" >&2; exit 1 ;; esac
exec /bin/mv "$@"
"""


def test_si_no_se_puede_poner_la_nueva_vuelve_la_vieja(entorno, monkeypatch):
    """La vieja ya estaba apartada: se restaura con su nombre y la otra copia también."""
    _ejecutable(entorno.binarios / "mv", MV_QUE_FALLA_CON_LA_NUEVA)
    monkeypatch.setenv("PATH", f"{entorno.binarios}{os.pathsep}{os.environ['PATH']}")
    vieja = _bundle(entorno.instaladas, "App_De_Prueba.app", "1.0")
    suelta = _bundle(entorno.instaladas, "App De Prueba Nueva.app", "1.5")
    _bundle(entorno.volumen, "App De Prueba Nueva.app", "2.0")

    resultado = _instalar(entorno, vieja)

    assert _restos(entorno.instaladas) == ["App De Prueba Nueva.app", "App_De_Prueba.app"]
    assert _version(vieja) == "1.0"
    assert _version(suelta) == "1.5"
    llamadas = entorno.llamadas()
    assert f"open {vieja}" in llamadas
    assert any(ll.startswith("osascript") for ll in llamadas)
    assert "Restaurada" in resultado.registro.read_text(encoding="utf-8")


def test_otra_copia_con_el_nombre_nuevo_no_se_queda(entorno):
    """Si ya había una copia suelta con el nombre nuevo, al final solo queda una."""
    vieja = _bundle(entorno.instaladas, "App_De_Prueba.app", "1.0")
    _bundle(entorno.instaladas, "App De Prueba Nueva.app", "1.5")
    _bundle(entorno.volumen, "App De Prueba Nueva.app", "2.0")

    assert _instalar(entorno, vieja).sustituida

    assert _restos(entorno.instaladas) == ["App De Prueba Nueva.app"]
    assert _version(entorno.instaladas / "App De Prueba Nueva.app") == "2.0"


def test_espera_a_que_la_app_se_cierre(entorno):
    vieja = _bundle(entorno.instaladas, "App de prueba.app", "1.0")
    _bundle(entorno.volumen, "App de prueba.app", "2.0")
    abierta = subprocess.Popen(["/bin/sleep", "1"])
    threading.Thread(target=abierta.wait, daemon=True).start()

    assert _instalar(entorno, vieja, pid=abierta.pid).sustituida

    assert abierta.poll() is not None, "no se tocó nada hasta que terminó el proceso"
    assert _version(entorno.instaladas / "App de prueba.app") == "2.0"


@pytest.mark.skipif(hasattr(os, "geteuid") and os.geteuid() == 0, reason="root escribe en todo")
def test_carpeta_sin_permiso_abre_el_dmg_y_dice_donde(entorno):
    vieja = _bundle(entorno.instaladas, "App de prueba.app", "1.0")
    _bundle(entorno.volumen, "App de prueba.app", "2.0")
    entorno.instaladas.chmod(0o555)
    try:
        resultado = _instalar(entorno, vieja)
    finally:
        entorno.instaladas.chmod(0o755)

    assert not resultado.sustituida
    assert str(entorno.instaladas) in resultado.aviso
    assert "Applications" in resultado.aviso
    assert entorno.llamadas() == [f"open {entorno.dmg}"], "como antes: solo se abre el DMG"
    assert _version(vieja) == "1.0"


def test_modo_desarrollo_abre_el_dmg(entorno):
    vieja = _bundle(entorno.instaladas, "App de prueba.app", "1.0")

    resultado = _instalar(entorno, vieja, congelada=False)

    assert not resultado.sustituida
    assert "carpeta donde la tengas instalada" in resultado.aviso
    assert entorno.llamadas() == [f"open {entorno.dmg}"]


def test_un_dmg_de_otra_app_no_sustituye_nada(entorno):
    vieja = _bundle(entorno.instaladas, "App de prueba.app", "1.0")
    _bundle(entorno.volumen, "Otra.app", "9.0", ident="es.example.otra")

    resultado = _instalar(entorno, vieja)

    assert not resultado.sustituida
    assert _restos(entorno.instaladas) == ["App de prueba.app"]
    llamadas = entorno.llamadas()
    assert any(ll.startswith("hdiutil detach") for ll in llamadas)
    assert llamadas[-1] == f"open {entorno.dmg}"
