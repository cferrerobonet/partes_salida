#!/bin/bash
# Crea imagenes/icono.icns (macOS) a partir de imagenes/icono.png. El .ico de
# Windows ya va en el repositorio. Sólo en macOS (sips e iconutil).
set -e
cd "$(dirname "$0")/../.."
[ -f imagenes/icono.png ] || { echo "Falta imagenes/icono.png"; exit 1; }
SET="imagenes/icono.iconset"
rm -rf "$SET" && mkdir -p "$SET"
for t in 16 32 128 256 512; do
    sips -z $t $t imagenes/icono.png --out "$SET/icon_${t}x${t}.png" >/dev/null
    d=$((t * 2))
    sips -z $d $d imagenes/icono.png --out "$SET/icon_${t}x${t}@2x.png" >/dev/null
done
iconutil -c icns "$SET" -o imagenes/icono.icns
rm -rf "$SET"
echo "Icono creado: imagenes/icono.icns"
