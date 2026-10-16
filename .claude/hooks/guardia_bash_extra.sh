#!/usr/bin/env bash
# Gancho propio de Partes de salida. Lo lanza guardia_bash.sh (copia común de la skill auditoria-apps)
# después de sus comprobaciones, con la misma entrada.
#   · Compilar en local (PyInstaller, make app/dmg, build_dmg.sh, build_windows.ps1): se compila en GitHub
# Salida 2 = bloqueado; el motivo llega al asistente por stderr.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$cmd" ] && exit 0

bloquear() { echo "BLOQUEADO por el gancho guardia_bash_extra.sh: $1" >&2; exit 2; }

ini='(^|[;&|(`]|\$\()[[:space:]]*(sudo[[:space:]]+|env[[:space:]]+([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*)?'

if printf '%s' "$cmd" | grep -Eiq "${ini}([^[:space:]]*python[0-9.]*[[:space:]]+-m[[:space:]]+)?pyinstaller([[:space:]]|$)" \
   || printf '%s' "$cmd" | grep -Eq "${ini}make[[:space:]]+(app|dmg)([[:space:]]|$)" \
   || printf '%s' "$cmd" | grep -Eq 'build_dmg\.sh|build_windows\.ps1'; then
    bloquear "no se compila en local (decisión de CarlosFB): se compila en GitHub al subir una etiqueta vX.Y.Z (skill publicar) o a mano en Actions → Compilar."
fi

exit 0
