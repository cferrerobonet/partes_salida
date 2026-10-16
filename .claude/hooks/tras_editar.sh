#!/usr/bin/env bash
# Gancho PostToolUse (Edit|Write|MultiEdit) común a los repositorios de CarlosFB.
# Copia común de la skill de usuario auditoria-apps (comun/tras_editar.sh): no se edita en el repositorio;
# se cambia en la skill y se reinstala con comun/instalar_en_repo.sh. Lo propio del repositorio va en
# tras_editar_extra.sh, en esta misma carpeta: se ejecuta después, con la misma entrada.
# Comprobaciones baratas justo después de editar, cada una solo si su herramienta está instalada:
#   · php -l (.php) · node --check (.js/.mjs/.cjs, no los .min.js) · bash -n (.sh/.bash) · zsh -n (.zsh)
#   · compilación de Python (.py; en una carpeta temporal: nada de __pycache__ en iCloud)
#   · JSON válido (.json, salvo los que admiten comentarios) · TOML válido (.toml)
#   · la palabra que nombra al asistente en cualquier archivo de texto; se admiten los nombres de su archivo
#     de instrucciones y de su carpeta, y no se mira la configuración del asistente (settings*.json)
# Silencioso si todo va bien. Salida 2 = aviso que llega al asistente por stderr.
set -uo pipefail

entrada=$(cat)
dir=$(cd "$(dirname "$0")" && pwd)
extra="$dir/tras_editar_extra.sh"
conf=$(cd "$dir/.." && pwd)   # carpeta de configuración del asistente del repositorio

f=$(printf '%s' "$entrada" | { jq -r '.tool_input.file_path // empty' 2>/dev/null \
    || python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("file_path") or "")' 2>/dev/null; })

problemas=""
hay() { command -v "$1" >/dev/null 2>&1; }
primera() { printf '%s' "$1" | grep -m1 -iE 'error|unexpected|invalid' || printf '%s' "$1" | head -1; }
palabra=$(printf '%s' c l a u d e)

if [ -n "$f" ] && [ -f "$f" ]; then
    case "$f" in
        *.php)
            hay php && { salida=$(php -l "$f" 2>&1) || problemas+="php -l: $(primera "$salida")"$'\n'; } ;;
        *.min.js|*.min.mjs) ;;
        *.js|*.mjs|*.cjs)
            hay node && { salida=$(node --check "$f" 2>&1) || problemas+="node --check: $(primera "$salida")"$'\n'; } ;;
        *.sh|*.bash)
            salida=$(bash -n "$f" 2>&1) || problemas+="bash -n: $(primera "$salida")"$'\n' ;;
        *.zsh)
            hay zsh && { salida=$(zsh -n "$f" 2>&1) || problemas+="zsh -n: $(primera "$salida")"$'\n'; } ;;
        *.py)
            hay python3 && { salida=$(python3 -I -c 'import os,py_compile,sys,tempfile
with tempfile.TemporaryDirectory() as d:
    try:
        py_compile.compile(sys.argv[1], cfile=os.path.join(d, "x.pyc"), doraise=True)
    except py_compile.PyCompileError as e:
        print(" ".join(e.msg.split())); sys.exit(1)' "$f" 2>&1) \
                || problemas+="compilación de Python: $salida"$'\n'; } ;;
        */tsconfig*.json|*/jsconfig*.json|*/.vscode/*.json|*/devcontainer.json) ;;   # JSON con comentarios
        *.json)
            if hay jq; then
                salida=$(jq empty "$f" 2>&1) || problemas+="JSON no válido: $(primera "$salida")"$'\n'
            elif hay python3; then
                salida=$(python3 -I -m json.tool "$f" 2>&1 >/dev/null) || problemas+="JSON no válido: $(primera "$salida")"$'\n'
            fi ;;
        *.toml)
            if hay python3 && python3 -I -c 'import tomllib' 2>/dev/null; then
                salida=$(python3 -I -c 'import sys,tomllib
try:
    tomllib.load(open(sys.argv[1], "rb"))
except tomllib.TOMLDecodeError as e:
    print(e); sys.exit(1)' "$f" 2>&1) \
                    || problemas+="TOML no válido: $(primera "$salida")"$'\n'
            fi ;;
    esac

    case "$f" in
        "$conf/settings.json"|"$conf/settings.local.json") ;;
        *.png|*.webp|*.jpg|*.jpeg|*.gif|*.avif|*.heic|*.ico|*.icns|*.pdf|*.zip|*.gz|*.woff|*.woff2|*.ttf|*.otf|*.glb|*.mp3|*.mp4|*.mov|*.wav|*.xls|*.xlsx|*.doc|*.docx|*.ppt|*.pptx|*.db|*.sqlite) ;;
        *)
            if hay perl; then
                lineas=$(PAL="$palabra" perl -ne 'BEGIN { exit 0 unless -T $ARGV[0] }
                    print "$.\n" if /(?<![.\w\/])\Q$ENV{PAL}\E(?!\w|\.(?:local\.)?md\b)/i' "$f" 2>/dev/null | head -5 | tr '\n' ' ')
            else
                lineas=$(grep -nE "(^|[^.[:alnum:]_/])[Cc]${palabra#c}([^[:alnum:]_.]|$)" "$f" 2>/dev/null | cut -d: -f1 | head -5 | tr '\n' ' ')
            fi
            [ -n "${lineas// /}" ] \
                && problemas+="palabra que nombra al asistente en $f (líneas ${lineas% }): reescribir sin ella («el archivo de instrucciones del asistente», «la carpeta de reglas del asistente»)."$'\n' ;;
    esac
fi

if [ -f "$extra" ]; then
    salida=$(printf '%s' "$entrada" | bash "$extra" 2>&1 >/dev/null) \
        || problemas+="${salida:-tras_editar_extra.sh terminó con error y sin mensaje.}"$'\n'
fi

if [ -n "$problemas" ]; then
    printf '%s' "$problemas" >&2
    exit 2
fi
exit 0
