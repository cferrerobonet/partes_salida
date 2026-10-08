#!/usr/bin/env bash
# Gancho PreToolUse (Bash) de Partes de salida: bloquea antes de ejecutarlos los
# comandos que las instrucciones prohíben. Una regla escrita se olvida; esta no.
#   · git add -A / --all / .   · git commit --amend   · push forzado   · --no-verify
#   · Mensajes de commit con la palabra prohibida o línea de coautoría
#   · Compilar en local (PyInstaller, make app/dmg): se compila en GitHub
#   · Conexiones a mano (ssh, sftp, scp): esta app no usa servidor
# Salida 2 = bloqueado; el motivo llega al asistente por stderr.
set -uo pipefail

cmd=$(jq -r '.tool_input.command // empty' 2>/dev/null)
[ -z "$cmd" ] && exit 0

bloquear() { echo "BLOQUEADO por .claude/hooks/guardia_bash.sh: $1" >&2; exit 2; }

ini='(^|[;&|(`]|\$\()[[:space:]]*(sudo[[:space:]]+|env[[:space:]]+([A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*)?'
git_='git([[:space:]]+-C[[:space:]]+[^[:space:]]+)?[[:space:]]+'

if printf '%s' "$cmd" | grep -Eq "${ini}${git_}add[[:space:]]+(.*[[:space:]])?(-A|--all|\.)([[:space:]]|$)"; then
    bloquear "git add -A/--all/. no se usa aquí: añadir ficheros concretos (el repositorio es público y no debe colarse ningún dato)."
fi
if printf '%s' "$cmd" | grep -Eq "${ini}${git_}commit"; then
    printf '%s' "$cmd" | grep -Eq -- '--amend' \
        && bloquear "nunca --amend: hacer un commit nuevo."
    printf '%s' "$cmd" | grep -Eqi 'co-authored-by' \
        && bloquear "los commits de este proyecto no llevan línea de coautoría."
    printf '%s' "$cmd" | grep -Eq '\b[C]laude\b' \
        && bloquear "el mensaje contiene la palabra prohibida. Redactarlo sin ella (los nombres CLAUDE.md y .claude/ sí valen)."
fi
if printf '%s' "$cmd" | grep -Eq "${ini}${git_}push([[:space:]].*)?[[:space:]](-f|--force|--force-with-lease)([[:space:]=]|$)"; then
    bloquear "push forzado: solo si CarlosFB lo pide expresamente."
fi
if printf '%s' "$cmd" | grep -Eq -- '--no-verify'; then
    bloquear "--no-verify salta el gancho que impide subir datos del alumnado: solo con el visto bueno de CarlosFB."
fi

if printf '%s' "$cmd" | grep -Eiq "${ini}([^[:space:]]*python[0-9.]*[[:space:]]+-m[[:space:]]+)?pyinstaller([[:space:]]|$)" \
   || printf '%s' "$cmd" | grep -Eq "${ini}make[[:space:]]+(app|dmg)([[:space:]]|$)" \
   || printf '%s' "$cmd" | grep -Eq 'build_dmg\.sh|build_windows\.ps1'; then
    bloquear "no se compila en local (decisión de CarlosFB): se compila en GitHub al subir una etiqueta vX.Y.Z (skill publicar) o a mano en Actions → Compilar."
fi

if printf '%s' "$cmd" | grep -Eq "${ini}(sshpass|sftp|scp|ssh|rsync)([[:space:]]|$)"; then
    bloquear "conexión a mano: esta app no usa servidor, y IONOS cierra el puerto 22 con conexiones seguidas."
fi

exit 0
