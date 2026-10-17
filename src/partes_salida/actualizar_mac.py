"""macOS: la actualización sustituye la app allí donde está instalada.

Procedencia: el mismo archivo en Partes de salida, Guardias de patio y Asistente
documental (2026-10-17); solo cambia quién lo llama. Si se corrige aquí, se
corrige en las tres.

Motivo: al abrir el DMG y arrastrar la app al acceso «Applications», la versión
nueva quedaba en /Applications mientras el Dock seguía abriendo la vieja de
/Applications/EPLA, y la app volvía a avisar de la misma actualización.

Cómo funciona:
1. El DMG, ya descargado (y comprobado, si la app lo comprueba), se monta sin
   enseñarlo en el Finder (`hdiutil attach -nobrowse -readonly -mountrandom`).
2. El bundle en uso sale de `sys.executable` (`…/X.app/Contents/MacOS/x`).
3. Un script auxiliar, separado del proceso, espera a que la app se cierre,
   copia la nueva con `ditto` a una carpeta hermana temporal, aparta la vieja,
   pone la nueva en su sitio con su propio nombre (puede haber cambiado entre
   versiones), le quita la cuarentena, borra la vieja, desmonta el DMG y abre
   la nueva. Deja un registro en la carpeta de registros de la app.
4. Si algo falla antes de que la nueva esté en su sitio, la vieja vuelve al
   suyo, se abre y se avisa. Nunca quedan dos copias.
5. Reserva (modo desarrollo, carpeta sin permiso de escritura, DMG que no se
   monta o que no trae esta app): se abre el DMG como antes y se dice a qué
   carpeta hay que arrastrar la app.
"""

from __future__ import annotations

import logging
import os
import plistlib
import shlex
import subprocess
import sys
import tempfile
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

#: Herramientas del sistema (las pruebas las sustituyen por simulaciones).
HDIUTIL = "/usr/bin/hdiutil"
DITTO = "/usr/bin/ditto"
OPEN = "/usr/bin/open"
XATTR = "/usr/bin/xattr"
OSASCRIPT = "/usr/bin/osascript"
#: Segundos que espera el script a que se cierre la app.
ESPERA_CIERRE = 120

_GUION = r"""#!/bin/bash
# Sustitución de la app tras una actualización (lo escribe actualizar_mac.py).
# Argumentos: PID, app nueva (en el DMG), app instalada, punto de montaje, DMG, registro.
set -u
PID="$1"; NUEVA="$2"; VIEJA="$3"; MONTAJE="$4"; DMG="$5"; REGISTRO="$6"
DITTO=@DITTO@; HDIUTIL=@HDIUTIL@; OPEN=@OPEN@; XATTR=@XATTR@; OSASCRIPT=@OSASCRIPT@
ESPERA=@ESPERA@
exec >>"$REGISTRO" 2>&1

anota() { echo "$(date '+%Y-%m-%d %H:%M:%S') $*"; }
desmonta() {
    "$HDIUTIL" detach "$MONTAJE" -quiet || "$HDIUTIL" detach "$MONTAJE" -force -quiet \
        || anota "AVISO: no se pudo desmontar $MONTAJE"
}
avisa() {
    "$OSASCRIPT" -e 'on run argv' \
        -e 'display alert (item 1 of argv) message (item 2 of argv) as critical' \
        -e 'end run' "No se pudo actualizar" \
        "$1 Sigue la versión anterior. Registro: $REGISTRO" || true
}

CARPETA="$(dirname "$VIEJA")"
NOMBRE_NUEVO="$(basename "$NUEVA")"
DESTINO="$CARPETA/$NOMBRE_NUEVO"
TEMPORAL="$CARPETA/.actualizando-$$-$NOMBRE_NUEVO"
APARTADA="$CARPETA/.anterior-$$-$(basename "$VIEJA")"
OTRA="$CARPETA/.anterior-$$-otra-$NOMBRE_NUEVO"

falla() {
    anota "ERROR: $1"
    rm -rf "$TEMPORAL"
    if [ -e "$APARTADA" ] && [ ! -e "$VIEJA" ]; then
        mv "$APARTADA" "$VIEJA" && anota "Restaurada $VIEJA"
    fi
    if [ -e "$OTRA" ] && [ ! -e "$DESTINO" ]; then
        mv "$OTRA" "$DESTINO" && anota "Restaurada $DESTINO"
    fi
    desmonta
    [ -e "$VIEJA" ] && "$OPEN" "$VIEJA"
    avisa "$1"
    exit 1
}

anota "Actualización: $VIEJA -> $DESTINO (espera al PID $PID)"
i=0
while kill -0 "$PID" 2>/dev/null; do
    i=$((i + 1))
    [ "$i" -gt $((ESPERA * 10)) ] && falla "La aplicación no llegó a cerrarse."
    sleep 0.1
done

rm -rf "$TEMPORAL"
"$DITTO" "$NUEVA" "$TEMPORAL" || falla "No se pudo copiar la versión nueva."
[ -d "$TEMPORAL/Contents" ] || falla "La copia de la versión nueva está incompleta."
mv "$VIEJA" "$APARTADA" || falla "No se pudo apartar la versión anterior."
if [ -e "$DESTINO" ]; then
    mv "$DESTINO" "$OTRA" || falla "Ya había otra copia en $DESTINO y no se pudo apartar."
fi
mv "$TEMPORAL" "$DESTINO" || falla "No se pudo poner la versión nueva en su sitio."
anota "Versión nueva en $DESTINO"

"$XATTR" -dr com.apple.quarantine "$DESTINO" || true
for resto in "$APARTADA" "$OTRA"; do
    [ -e "$resto" ] || continue
    rm -rf "$resto" || mv "$resto" "$HOME/.Trash/" \
        || anota "AVISO: no se pudo borrar $resto; hay que borrarla a mano"
done
desmonta
rm -f "$DMG"
"$OPEN" "$DESTINO" || anota "AVISO: no se pudo abrir $DESTINO"
anota "Actualización terminada"
rm -f "$0"
"""


@dataclass
class Resultado:
    """`sustituida`: el script ya espera y la app tiene que cerrarse ahora.

    Si no, se ha abierto el DMG (reserva) y `aviso` dice qué hacer con él.
    """

    sustituida: bool
    aviso: str = ""
    registro: Path | None = None


def bundle_en_uso(ejecutable: str | None = None, congelada: bool | None = None) -> Path | None:
    """El `.app` desde el que se ejecuta la aplicación; None en modo desarrollo."""
    congelada = getattr(sys, "frozen", False) if congelada is None else congelada
    if not congelada:
        return None
    ruta = Path(ejecutable or sys.executable).resolve()
    if len(ruta.parents) < 3 or ruta.parent.name != "MacOS" or ruta.parents[1].name != "Contents":
        return None
    app = ruta.parents[2]
    return app if app.suffix == ".app" else None


def identificador(app: Path) -> str:
    """`CFBundleIdentifier` del `.app`; vacío si no se puede leer."""
    try:
        with open(Path(app) / "Contents" / "Info.plist", "rb") as f:
            return str(plistlib.load(f).get("CFBundleIdentifier") or "")
    except (OSError, ValueError):
        return ""


def montar(dmg: Path) -> Path:
    """Monta el DMG en una carpeta aleatoria, de solo lectura y sin el Finder."""
    base = tempfile.mkdtemp(prefix="actualizacion-dmg-")
    orden = [HDIUTIL, "attach", "-nobrowse", "-readonly", "-mountrandom", base, "-plist", str(dmg)]
    salida = subprocess.run(orden, capture_output=True, check=True, timeout=180)  # nosec B603
    for entidad in plistlib.loads(salida.stdout).get("system-entities", []):
        if entidad.get("mount-point"):
            return Path(entidad["mount-point"])
    raise RuntimeError("hdiutil no ha dado ningún punto de montaje")


def desmontar(punto: Path) -> None:
    orden = [HDIUTIL, "detach", str(punto), "-quiet"]
    subprocess.run(orden, check=False, capture_output=True, timeout=60)  # nosec B603


def app_del_volumen(punto: Path, ident: str = "") -> Path | None:
    """El `.app` del DMG; con `ident`, solo el que tenga ese identificador."""
    apps = sorted(p for p in Path(punto).iterdir() if p.suffix == ".app" and p.is_dir())
    if ident:
        return next((a for a in apps if identificador(a) == ident), None)
    return apps[0] if apps else None


def _lanzar_separado(orden: list[str]) -> None:
    subprocess.Popen(  # noqa: S603  # nosec B603
        orden,
        start_new_session=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
        cwd="/",
    )


def _guion() -> str:
    texto = _GUION
    for marca, valor in (
        ("@DITTO@", DITTO),
        ("@HDIUTIL@", HDIUTIL),
        ("@OPEN@", OPEN),
        ("@XATTR@", XATTR),
        ("@OSASCRIPT@", OSASCRIPT),
        ("@ESPERA@", str(int(ESPERA_CIERRE))),
    ):
        texto = texto.replace(marca, shlex.quote(valor))
    return texto


def _reserva(dmg: Path, motivo: str, carpeta: Path | None) -> Resultado:
    logger.warning("Actualización en macOS por la vía manual: %s", motivo)
    subprocess.run([OPEN, str(dmg)], check=False)  # nosec B603
    if carpeta is not None:
        donde = (
            f"arrástrala a «{carpeta}», que es donde está instalada, y sustituye la anterior. "
            "No la arrastres al acceso «Applications» del DMG si no es ahí donde la tienes"
        )
    else:
        donde = "arrástrala a la carpeta donde la tengas instalada y sustituye la anterior"
    return Resultado(False, f"{motivo}\n\nSe abre el DMG: {donde}.")


def instalar(
    dmg: Path,
    carpeta_registros: Path,
    *,
    pid: int | None = None,
    ejecutable: str | None = None,
    congelada: bool | None = None,
    lanzar: Callable[[list[str]], None] | None = None,
) -> Resultado:
    """Prepara la sustitución de la app en uso por la del DMG y lanza el script.

    Con `sustituida`, quien llama cierra la app enseguida: el script espera a su
    PID. `pid`, `ejecutable`, `congelada` y `lanzar` solo los cambian las pruebas.
    """
    dmg = Path(dmg)
    vieja = bundle_en_uso(ejecutable, congelada)
    if vieja is None:
        return _reserva(dmg, "Esta copia no se ejecuta desde una app instalada.", None)
    carpeta = vieja.parent
    if "AppTranslocation" in vieja.parts or str(carpeta).startswith("/Volumes/"):
        return _reserva(dmg, "La aplicación se está ejecutando sin instalar.", None)
    if not (os.access(carpeta, os.W_OK) and os.access(vieja, os.W_OK)):
        return _reserva(dmg, f"No hay permiso para escribir en «{carpeta}».", carpeta)
    try:
        punto = montar(dmg)
    except (OSError, ValueError, AttributeError, RuntimeError, subprocess.SubprocessError) as e:
        logger.warning("No se pudo montar %s: %s", dmg, e)
        return _reserva(dmg, "No se ha podido abrir el DMG por dentro.", carpeta)
    nueva = app_del_volumen(punto, identificador(vieja))
    if nueva is None:
        desmontar(punto)
        return _reserva(dmg, "El DMG no trae esta aplicación.", carpeta)
    registros = Path(carpeta_registros)
    registros.mkdir(parents=True, exist_ok=True)
    registro = registros / f"actualizacion_mac_{datetime.now():%Y%m%d-%H%M%S}.log"
    script = Path(tempfile.mkdtemp(prefix="actualizacion-mac-")) / "sustituir.sh"
    script.write_text(_guion(), encoding="utf-8")
    orden = [
        "/bin/bash",
        str(script),
        str(pid or os.getpid()),
        str(nueva),
        str(vieja),
        str(punto),
        str(dmg),
        str(registro),
    ]
    try:
        (lanzar or _lanzar_separado)(orden)
    except OSError as e:
        logger.warning("No se pudo lanzar la sustitución: %s", e)
        desmontar(punto)
        return _reserva(dmg, "No se ha podido preparar la sustitución.", carpeta)
    logger.info("Sustitución preparada: %s -> %s (registro %s)", vieja, nueva.name, registro)
    return Resultado(True, registro=registro)
