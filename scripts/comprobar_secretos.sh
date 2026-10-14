#!/usr/bin/env bash
# Comprobación común a todas las apps de CarlosFB (misma copia en cada repositorio).
# Ningún secreto ni dato de infraestructura entra en el repositorio: contraseñas,
# claves, tokens, servidores SMTP/SFTP/MySQL del alojamiento, usuarios del hosting,
# ni buzones de servicio. Se usa en dos sitios:
#   .githooks/pre-commit              → --preparado (lo que se va a confirmar)
#   .github/workflows/secretos.yml    → --todo (todo el árbol, en cada push)
# Falsos positivos: una ruta por línea (glob de bash) en .secretos-ignorar.
# Los patrones se escriben con [.] [_] [ ] para que este archivo no se detecte a sí mismo.
set -uo pipefail

Q="[\"']"      # comilla simple o doble
NQ="[^\"']"    # cualquier carácter que no sea comilla
P='-----BEGIN[ ][A-Z ]*PRIVATE[ ]KEY'                                        # clave privada
P+='|smtp[.][a-z0-9-]+[.][a-z]{2,}'                                           # servidor SMTP
P+='|[a-z0-9-]+[.]1and1-data[.]host|hosting-data[.]io'                       # servidores del alojamiento
P+='|\bu[0-9]{8}\b|\bdb[su][0-9]{6,}\b|\bacc-[0-9]{6,}\b'                     # usuarios y bases del hosting
P+='|/homepages/[0-9]+/|/kunden/homepages/[0-9]+'                                    # rutas absolutas del servidor
P+='|no[_]contestar@'                                                         # buzón de servicio de las apps
P+='|[a-z0-9.-]+:(465|587|2525)\b'                                            # servidor:puerto de correo
P+='|(smtp|sftp|ftp|mail|correo|db|mysql)[_a-z]*(usuario|user|servidor|server|host|remitente)[_a-z]*[ ]*(:[ ]*[a-z]+[ ]*)?=[ ]*'"$Q$NQ"'+'"$Q"  # valor escrito en código
P+='|(password|passwd|pwd|contrasena|contraseña|secret|token|api[_-]?key)[_a-z]*[ ]*[:=][ ]*'"$Q"'[^"'"'"' ]{6,}'"$Q"  # secreto entre comillas
P+='|[$]2[aby][$][0-9]{2}[$][./A-Za-z0-9]{53}'                                # hash bcrypt real
P+='|\bgh[pousr][_][A-Za-z0-9]{36}\b|\bsk-[A-Za-z0-9_-]{20,}|\bAIza[0-9A-Za-z_-]{35}\b|\bxox[bap]-[A-Za-z0-9-]{10,}'  # tokens conocidos
# Reglas que distinguen mayúsculas (variables de entorno y constantes de PHP)
S='^[ ]*(export[ ]+)?[A-Z_]*(PASS|PASSWORD|SECRET|TOKEN|API_KEY|CLAVE)[A-Z_]*[ ]*=[ ]*[^ "'"'"'$(]{6,}'   # secreto en .env
S+='|^[ #]*(export[ ]+)?[A-Z_]*(HOST|SERVER|SERVIDOR|USER|USUARIO)[A-Z_]*[ ]*=[ ]*'"$Q"'?[a-z0-9-]+([.][a-z0-9-]+)+[.][a-z]{2,}'  # servidor en .env
S+='|define[(][ ]*'"$Q"'[A-Z_]*(PASSWORD|PASS|SECRET|TOKEN|API_KEY|CLAVE)[A-Z_]*'"$Q"'[ ]*,[ ]*'"$Q$NQ"'{6,}'"$Q"  # define('X_PASSWORD', '…') de PHP
MARCADORES='CAMBIAR|cambiame|changeme|ejemplo|example|placeholder|xxxx|tu_|<[a-z_ ]+>|[$][{]|getenv|os[.]environ|leer_secreto|prueba|dummy|fake|ficticio|contrase[ñn]a-de|[=:][ ]*contrase[ñn]a|[=:][ ]*[a-z]+_(password|pass|token|override)[ ]*$|smtp[.](gmail|office365)[.]com|smtp-mail[.]outlook[.]com|[.](test|local|invalid)[.]?[a-z]*\b|127[.]0[.]0[.]1|localhost|writable|readonly|data-[a-z-]+=|[.](css|js|php|md|py|ts|json|html|sh|yml):[0-9]+|\bnull\b|None\b'
MARCADORES+="|${Q}[\$][A-Za-z_(]|${Q}<[?]|[:=][ ]*${Q}/"   # valor que es una variable ($x), una plantilla (<?=) o una ruta

modo="${1:---todo}"
raiz=$(git rev-parse --show-toplevel)
ignorar=()
[ -f "$raiz/.secretos-ignorar" ] && while IFS= read -r l; do [[ -n "$l" && "$l" != \#* ]] && ignorar+=("$l"); done < "$raiz/.secretos-ignorar"
saltar() {
    [ "$1" = "scripts/comprobar_secretos.sh" ] && return 0
    [ "$1" = ".secretos-ignorar" ] && return 0
    local g; for g in "${ignorar[@]+"${ignorar[@]}"}"; do [[ "$1" == $g ]] && return 0; done
    return 1
}
fallo=0
revisar() {  # $1 = ruta; contenido por stdin (sin tuberías: en una subcapa se perdería «fallo»)
    local salida
    local contenido; contenido=$(cat)
    salida=$( { printf '%s\n' "$contenido" | grep -n -I -i -E -e "$P"; printf '%s\n' "$contenido" | grep -n -I -E -e "$S"; } 2>/dev/null | grep -v -i -E -e "$MARCADORES" | sort -t: -k1,1n -u)
    [ -z "$salida" ] && return 0
    echo "secretos: $1 contiene un secreto o un dato de infraestructura:" >&2
    echo "    líneas: $(echo "$salida" | cut -d: -f1 | paste -sd, -)" >&2   # nunca el contenido: el registro de la CI puede ser público
    fallo=1
}
case "$modo" in
    --preparado)
        while IFS= read -r -d '' f; do saltar "$f" && continue; revisar "$f" < <(git show ":$f"); done \
            < <(git diff --cached --name-only --diff-filter=ACM -z) ;;
    --todo)
        while IFS= read -r -d '' f; do saltar "$f" && continue; [ -f "$raiz/$f" ] && revisar "$f" < "$raiz/$f"; done \
            < <(git -C "$raiz" ls-files -z) ;;
    *) echo "uso: $0 [--preparado|--todo]" >&2; exit 2 ;;
esac
if [ "$fallo" -ne 0 ]; then
    echo "secretos: las credenciales y los datos del servidor van en .env, en Ajustes de cada equipo o en el llavero, nunca en el repositorio. Si es un falso positivo, añade la ruta a .secretos-ignorar." >&2
    exit 1
fi
exit 0
