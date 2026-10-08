#!/usr/bin/env bash
# Gancho PostToolUse (Edit|Write|MultiEdit) de Partes de salida: comprobaciones
# baratas justo después de editar, para no descubrir el error en la suite.
#   · .py: compilación (en una carpeta temporal: nada de __pycache__ en iCloud) y ruff
#   · .sh: bash -n · .json: válido · .toml: válido
#   · la palabra prohibida de la bóveda en cualquier archivo de texto editado
# Silencioso si todo va bien. Salida 2 = aviso que llega al asistente por stderr.
set -uo pipefail

f=$(jq -r '.tool_input.file_path // empty' 2>/dev/null)
[ -z "$f" ] || [ ! -f "$f" ] && exit 0
P="$HOME/.venvs/partes-salida/bin/python"
[ -x "$P" ] || P="$(command -v python3)"

problemas=""
primera() { printf '%s' "$1" | grep -m1 -iE 'error|unexpected|invalid' || printf '%s' "$1" | head -1; }

case "$f" in
    *.py)
        salida=$("$P" -c "import py_compile,sys,tempfile,os; d=tempfile.mkdtemp(); py_compile.compile(sys.argv[1], cfile=os.path.join(d,'x.pyc'), doraise=True)" "$f" 2>&1) \
            || problemas+="py_compile: $(primera "$salida")"$'\n'
        if "$P" -m ruff --version >/dev/null 2>&1; then
            salida=$(cd "$(dirname "$f")" && "$P" -m ruff check --quiet --output-format concise "$f" 2>&1) \
                || problemas+="ruff: $(printf '%s' "$salida" | head -3)"$'\n'
        fi ;;
    *.sh)
        salida=$(bash -n "$f" 2>&1) || problemas+="bash -n: $(primera "$salida")"$'\n' ;;
    *.json)
        salida=$("$P" -m json.tool "$f" 2>&1 >/dev/null) || problemas+="JSON no válido: $(primera "$salida")"$'\n' ;;
    *.toml)
        salida=$("$P" -c "import tomllib,sys; tomllib.load(open(sys.argv[1],'rb'))" "$f" 2>&1) || problemas+="TOML no válido: $(primera "$salida")"$'\n' ;;
esac

case "$f" in
    *.png|*.jpg|*.jpeg|*.ico|*.icns|*.ttf|*.pdf|*.zip|*.xls|*.xlsx) ;;
    *)
        if lineas=$(grep -nE '\b[C]laude\b' "$f" | cut -d: -f1 | head -5 | tr '\n' ' ') && [ -n "$lineas" ]; then
            problemas+="palabra prohibida en $f (líneas $lineas): reescribir sin ella; los nombres CLAUDE.md y .claude/ sí valen."$'\n'
        fi ;;
esac

if [ -n "$problemas" ]; then
    printf '%s' "$problemas" >&2
    exit 2
fi
exit 0
