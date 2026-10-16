#!/usr/bin/env bash
# Gancho propio de Partes de salida. Lo lanza tras_editar.sh (copia común de la skill auditoria-apps)
# después de sus comprobaciones, con la misma entrada.
#   · .py: ruff con el entorno virtual de la app (su versión y su configuración)
# Silencioso si todo va bien. Salida 2 = aviso que llega al asistente por stderr.
set -uo pipefail

f=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
{ [ -z "$f" ] || [ ! -f "$f" ]; } && exit 0
P="$HOME/.venvs/partes-salida/bin/python"
[ -x "$P" ] || P="$(command -v python3)"

case "$f" in
    *.py)
        if "$P" -m ruff --version >/dev/null 2>&1; then
            if ! salida=$(cd "$(dirname "$f")" && "$P" -m ruff check --quiet --output-format concise "$f" 2>&1); then
                printf 'ruff: %s\n' "$(printf '%s' "$salida" | head -3)" >&2
                exit 2
            fi
        fi ;;
esac
exit 0
