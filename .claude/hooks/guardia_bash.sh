#!/usr/bin/env bash
# Gancho PreToolUse (Bash) común a los repositorios de CarlosFB.
# Copia común de la skill de usuario auditoria-apps (comun/guardia_bash.sh): no se edita en el repositorio;
# se cambia en la skill y se reinstala con comun/instalar_en_repo.sh. Lo propio del repositorio va en
# guardia_bash_extra.sh, en esta misma carpeta: se ejecuta después, con la misma entrada.
# Bloquea antes de ejecutarlas las órdenes que las instrucciones prohíben. Una regla escrita se olvida; esta no.
#   · git add -A / --all / . / :/   · git commit --amend   · push forzado (-f, --force, --force-with-lease, +rama)
#   · --no-verify   · línea de coautoría o la palabra que nombra al asistente en el commit
#   · conexiones a mano (ssh, sftp, scp, sshpass, lftp, ssh-keyscan, sshfs, rsync a otra máquina) y sondeos
#     al puerto 22: IONOS lo cierra con conexiones seguidas. Solo el script de despliegue de la app, que lleva
#     el presupuesto de conexiones (lo que conecte por dentro de ese script no lo ve este gancho).
#   · scripts/deploy.sh con algo delante (cd, variables, bash, ./, $(…)): no casaría con la regla de permisos
#   · composer update / npm install / npm update sin paquete: reescriben los archivos de bloqueo
# Salida 2 = bloqueado; el motivo llega al asistente por stderr.
set -uo pipefail

entrada=$(cat)
extra="$(dirname "$0")/guardia_bash_extra.sh"

seguir() {
    if [ -f "$extra" ]; then
        printf '%s' "$entrada" | bash "$extra"
        exit $?
    fi
    exit 0
}

bloquear() { echo "BLOQUEADO por el gancho guardia_bash.sh: $1" >&2; exit 2; }

cmd=$(printf '%s' "$entrada" | { jq -r '.tool_input.command // empty' 2>/dev/null \
    || python3 -I -c 'import json,sys; print(json.load(sys.stdin).get("tool_input",{}).get("command") or "")' 2>/dev/null; })
[ -z "$cmd" ] && seguir

hay() { printf '%s' "$cmd" | grep -Eq -- "$1"; }

# La palabra que nombra al asistente, sin escribirla. Se admiten los nombres de su archivo de instrucciones
# (<PALABRA>.md, <PALABRA>.local.md), su carpeta (.<palabra>/, …/<palabra>…) y las variables (<PALABRA>_…).
palabra=$(printf '%s' c l a u d e)
tiene_palabra() {
    if command -v perl >/dev/null 2>&1; then
        PAL="$palabra" perl -0777 -ne 'exit(/(?<![.\w\/])\Q$ENV{PAL}\E(?!\w|\.(?:local\.)?md\b)/i ? 0 : 1)'
    else
        grep -Eq "(^|[^.[:alnum:]_/])[Cc]${palabra#c}([^[:alnum:]_.]|$)"
    fi
}

# Inicio de una orden: principio de línea, tras ; & | ( { ` $( o dentro de bash -c '…', con prefijos
# opcionales (sudo, env, VAR=valor, command, exec, nohup, time, nice, timeout N, xargs) y ruta delante.
q="'"
pre='((sudo|doas)([[:space:]]+-[^[:space:]]+)*[[:space:]]+|env([[:space:]]+-[^[:space:]]+)*[[:space:]]+|(command|exec|nohup|time|nice)[[:space:]]+|timeout[[:space:]]+[^[:space:]]+[[:space:]]+|xargs([[:space:]]+-[^[:space:]]+)*[[:space:]]+|[A-Za-z_][A-Za-z0-9_]*=[^[:space:]]*[[:space:]]+)*'
ini="(^|[;&|({\`]|\\\$\\(|(^|[[:space:];&|(])(ba|z)?sh[[:space:]]+-l?c[[:space:]]+[\"$q])[[:space:]]*${pre}([^[:space:];&|()\`\"$q]*/)?"
# git con sus opciones globales (-C "ruta con espacios", -c clave=valor, --no-pager, -P…)
gopt="([[:space:]]+(-C[[:space:]]+(\"[^\"]*\"|$q[^$q]*$q|[^[:space:]]+)|-c[[:space:]]+[^[:space:]]+|--[a-z-]+(=[^[:space:]]+)?|-[pP]))*"
git_="${ini}git${gopt}[[:space:]]+"
fin='([[:space:]]|$|[;&|)])'

# --- Git ---
if hay "${git_}add([[:space:]][^;&|]*)?[[:space:]](-A|--all|\\.|\\./|:/|-[[:alnum:]]*A[[:alnum:]]*)${fin}"; then
    bloquear "git add -A/--all/. no se usa: añadir archivos concretos (git add -- ruta1 ruta2…)."
fi
if hay "${git_}commit([[:space:]]|$)"; then
    hay '--amend' \
        && bloquear "nunca --amend: puede reescribir el commit de otra sesión que ya está en HEAD. Hacer un commit nuevo."
    printf '%s' "$cmd" | grep -Eqi 'co-authored-by' \
        && bloquear "los commits no llevan línea de coautoría."
    printf '%s' "$cmd" | tiene_palabra \
        && bloquear "el mensaje contiene la palabra que nombra al asistente. Redactarlo sin ella («el archivo de instrucciones del asistente», «la carpeta de reglas del asistente»)."
fi
if hay "${git_}push([[:space:]][^;&|]*)?[[:space:]](--force|--force-with-lease|-[[:alnum:]]*f[[:alnum:]]*|\\+[^[:space:]]+)([[:space:]=]|$|[;&|)])"; then
    bloquear "push forzado: solo si CarlosFB lo pide expresamente."
fi
if hay '--no-verify'; then
    bloquear "--no-verify salta los ganchos de git (la barrera de secretos, las pruebas): solo con el visto bueno de CarlosFB."
fi

# --- Conexiones (IONOS cierra el puerto 22 con conexiones seguidas) ---
despliegue="A IONOS solo se conecta con el script de despliegue de la app (scripts/deploy.sh o el que diga su AGENTS.md), que lleva el presupuesto de conexiones; si tiene --presupuesto, dice sin conectar si se puede."
if hay "${ini}(sshpass([[:space:]]+-[^[:space:]]+([[:space:]]+[^[:space:]-][^[:space:]]*)?)*[[:space:]]+)?sftp${fin}"; then
    bloquear "sftp a mano (además, en IONOS da Permission denied con credenciales buenas). $despliegue"
fi
if hay "${ini}(sshpass([[:space:]]+-[^[:space:]]+([[:space:]]+[^[:space:]-][^[:space:]]*)?)*[[:space:]]+)?scp${fin}"; then
    bloquear "scp a mano (además, sin -O falla en silencio en IONOS). $despliegue"
fi
if hay "${ini}(sshpass|ssh|lftp|ssh-keyscan|sshfs|mosh)${fin}"; then
    bloquear "conexión a mano. $despliegue"
fi
if hay "${ini}rsync([[:space:]]|$)" \
   && hay "rsync[^;&|]*([[:space:]](-e|--rsh)([[:space:]=]|$)|rsync://|[[:space:]][\"$q]?[A-Za-z0-9._@-]+:)"; then
    bloquear "rsync a otra máquina es una conexión a mano. $despliegue (rsync entre carpetas locales sí vale.)"
fi
if hay "${ini}(nc|ncat|netcat|telnet|nmap|socat)[[:space:]][^;&|]*\\b22\\b" \
   || hay "(curl|wget|s_client)[^;&|]*:22([/[:space:]\"$q]|$)" \
   || hay '/dev/(tcp|udp)/[^[:space:]/]+/22([^0-9]|$)'; then
    bloquear "sondear el puerto 22 cuenta como conexión y puede cerrarlo. $despliegue"
fi

# --- scripts/deploy.sh: al principio de la orden, tal cual (leerlo sí vale) ---
if hay "(^|[^[:alnum:]_.-])scripts/deploy\\.sh([[:space:]\"$q;&|)]|$)"; then
    if ! [[ "$cmd" =~ ^[[:space:]]*scripts/deploy\.sh([[:space:]]|$) ]] \
       && ! [[ "$cmd" =~ ^[[:space:]]*(cat|less|head|tail|grep|rg|sed|awk|wc|diff|git|shellcheck|bash[[:space:]]+-n|ls|cmp|stat|file|md5|shasum|echo|printf)[[:space:]] ]]; then
        bloquear "scripts/deploy.sh se lanza solo, al principio de la orden y sin cd, ./, bash, variables ni \$(…) delante (las opciones, detrás). Así casa con la regla de permisos."
    fi
fi

# --- Dependencias: sin paquete, reescriben el archivo de bloqueo ---
solo_opciones="([[:space:]]+-[^[:space:];&|]*)*[[:space:]]*($|[;&|)])"
if hay "${ini}composer([[:space:]]+-[^[:space:]]+)*[[:space:]]+(update|upgrade|u)${solo_opciones}"; then
    bloquear "composer update sin paquete reescribe composer.lock. Instalar con composer install; un cambio de dependencias, paquete a paquete (composer update vendor/paquete) y documentado."
fi
if hay "${ini}npm([[:space:]]+-[^[:space:]]+)*[[:space:]]+(install|i|update|up|upgrade)${solo_opciones}"; then
    bloquear "npm install/update sin paquete puede reescribir package-lock.json. Instalar con npm ci; un cambio de dependencias, paquete a paquete (npm install paquete@versión)."
fi

seguir
