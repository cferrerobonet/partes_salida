#!/usr/bin/env bash
# Barrera común contra secretos y datos personales (versión 3, 2026-10-16).
# Misma copia en cada repositorio de CarlosFB; la original vive en la skill de usuario
# «barrera-secretos» y se instala con su `instalar_en_repo.sh`. No editar aquí: editar allí y reinstalar.
#
# Qué bloquea:
#   1. Secretos: contraseñas, claves privadas, tokens, hashes de contraseña.
#   2. Datos de infraestructura: servidores SMTP/SFTP/MySQL del alojamiento, usuarios y rutas del hosting,
#      el buzón de servicio de las apps.
#   3. Datos personales: DNI/NIE con letra válida, varios móviles reales en un archivo, correos personales
#      (gmail, hotmail…) que no sean de ejemplo, volcados SQL con datos.
#   4. Archivos que no van nunca en un repositorio: .env, bases de datos, Excel/CSV, PDF y Word,
#      registros, copias, claves y certificados.
#   5. Lo que detecte gitleaks, si está instalado (capa extra; en la CI siempre lo está).
# Modos:
#   --preparado   lo que se va a confirmar (gancho pre-commit)
#   --todo        todo el árbol versionado (CI en cada push)
#   --historial   todos los objetos de todas las ramas y etiquetas (antes de hacer público un repositorio,
#                 tras una purga, o como auditoría). Más lento.
#   --rango A..B  los commits de un rango (gancho pre-push)
#   --historial-gitleaks  solo gitleaks sobre todo el historial (rápido; CI en cada push)
# Excepciones: una ruta (glob de bash) por línea en .secretos-ignorar, SIEMPRE con un comentario que diga por qué.
# Versiones antiguas ya revisadas (solo --historial): el SHA del blob en .secretos-historial, uno por línea y con
# su motivo. Así lo que se dejó a conciencia en el historial no salta cada semana y lo nuevo se sigue revisando.
# Datos de prueba ficticios que pasan sin excepción: móviles 600…, DNI 12345678Z/00000000T, correos
# @example.com, @ejemplo.*, *.test, *.invalid, *.local, o con tu_/usuario/ejemplo/prueba en el nombre.
# Nunca muestra el valor encontrado: solo archivo, línea y tipo (el registro de la CI puede ser público).
# Los patrones se escriben con [.] [_] [ ] para que este archivo no se detecte a sí mismo.
set -uo pipefail

Q="[\"']"      # comilla simple o doble
NQ="[^\"']"    # cualquier carácter que no sea comilla
P='-----BEGIN[ ][A-Z ]*PRIVATE[ ]KEY'                                        # clave privada
P+='|smtp[.][a-z0-9-]+[.][a-z]{2,}'                                           # servidor SMTP
P+='|no[_]contestar@'                                                         # buzón de servicio de las apps
P+='|[a-z0-9.-]+:(465|587|2525)\b'                                            # servidor:puerto de correo
P+='|(smtp|sftp|ftp|mail|correo|db|mysql)[_a-z]*(usuario|user|servidor|server|host|remitente)[_a-z]*[ ]*(:[ ]*[a-z]+[ ]*)?=[ ]*'"$Q$NQ"'+'"$Q"  # valor escrito en código
P+='|(password|passwd|pwd|contrasena|contraseña|secret|token|api[_-]?key)[_a-z]*[ ]*[:=][ ]*'"$Q"'[^"'"'"' ]{6,}'"$Q"  # secreto entre comillas (el estilo JSON lo mira Python)
P+='|(password|pass)[_]?hash'"$Q"'?[ ]*[:=][ ]*'"$Q"'[0-9a-f]{64}'"$Q"            # hash SHA-256 de contraseña
P+='|[$]2[aby][$][0-9]{2}[$][./A-Za-z0-9]{53}'                                # hash bcrypt real
P+='|\bgh[pousr][_][A-Za-z0-9]{36}\b|\bsk-[A-Za-z0-9_-]{20,}|\bAIza[0-9A-Za-z_-]{35}\b|\bxox[bap]-[A-Za-z0-9-]{10,}|\b0x4AAAA[A-Za-z0-9_-]{20,}'  # tokens conocidos (GitHub, OpenAI, Google, Slack, Turnstile)
# Identificadores del hosting: nunca son ejemplos, así que ningún marcador los disculpa (tampoco un ${VAR:-…})
H='[a-z0-9-]+[.]1and1-data[.]host|hosting-data[.]io'                         # servidores del alojamiento
H+='|\bu[0-9]{8}\b|\bdb[su][0-9]{6,}\b|\bacc-[0-9]{6,}\b'                     # usuarios, bases y cuentas del hosting
H+='|/homepages/[0-9]+/|/kunden/homepages/[0-9]+'                             # rutas absolutas del servidor
# Reglas que distinguen mayúsculas (variables de entorno y constantes de PHP)
S='^[ ]*(export[ ]+)?[A-Z_]*(PASS|PASSWORD|SECRET|TOKEN|API_KEY|CLAVE)[A-Z_]*[ ]*=[ ]*[^ "'"'"'$(]{6,}'   # secreto en .env
S+='|^[ #]*(export[ ]+)?[A-Z_]*(HOST|SERVER|SERVIDOR|USER|USUARIO)[A-Z_]*[ ]*=[ ]*'"$Q"'?[a-z0-9-]+([.][a-z0-9-]+)+[.][a-z]{2,}'  # servidor en .env
S+='|define[(][ ]*'"$Q"'[A-Z_]*(PASSWORD|PASS|SECRET|TOKEN|API_KEY|CLAVE)[A-Z_]*'"$Q"'[ ]*,[ ]*'"$Q$NQ"'{6,}'"$Q"  # define('X_PASSWORD', '…') de PHP
MARCADORES='CAMBIAR|QUITADO|cambiame|changeme|ejemplo|example|placeholder|xxxx|tu_|<[a-z_ ]+>|[$][{]|getenv|os[.]environ|leer_secreto|prueba|dummy|fake|ficticio|contrase[ñn]a-de|[=:][ ]*contrase[ñn]a|[=:][ ]*[a-z]+_(password|pass|token|override)[ ]*$|smtp[.](gmail|office365)[.]com|smtp-mail[.]outlook[.]com|[.](test|local|invalid)[.]?[a-z]*\b|127[.]0[.]0[.]1|localhost|writable|readonly|data-[a-z-]+=|[.](css|js|php|md|py|ts|json|html|sh|yml):[0-9]+|\bnull\b|None\b'
MARCADORES+="|${Q}[\$][A-Za-z_(]|${Q}<[?]|[:=][ ]*${Q}/"   # valor que es una variable ($x), una plantilla (<?=) o una ruta
# Archivos que no se versionan nunca (salvo excepción justificada en .secretos-ignorar)
PROHIBIDOS='(^|/)[.]env$|(^|/)[.]env[.](local|production|prod|deploy|backup|bak|old|save)$|[.](sqlite3?|db|sql[.]gz|dump|bak|log|csv|tsv|xlsx?|xlsm|ods|pdf|docx?|odt|accdb|mdb|pst|eml|msg|vcf|p12|pfx|pem|key|kdbx|ovpn|zip|tgz|tar[.]gz|7z|rar)$|(^|/)id_(rsa|ed25519|ecdsa)$|(^|/)[.]vscode/sftp[.]json$|(^|/)sftp-config[.]json$|[.]htpasswd$'

YO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/$(basename "${BASH_SOURCE[0]}")"
modo="${1:---todo}"
raiz=$(git rev-parse --show-toplevel)
cd "$raiz" || exit 2
ignorar=()
revisados=" "
[ -f .secretos-historial ] && while IFS= read -r l; do l="${l%%[[:space:]]#*}"; l="${l%"${l##*[![:space:]]}"}"; [[ "$l" =~ ^[0-9a-f]{40}$ ]] && revisados+="$l "; done < .secretos-historial
[ -f .secretos-ignorar ] && while IFS= read -r l; do l="${l%%[[:space:]]#*}"; l="${l%"${l##*[![:space:]]}"}"; [[ -n "$l" && "$l" != \#* ]] && ignorar+=("$l"); done < .secretos-ignorar
# Código de terceros y recursos generados: ni datos ni secretos propios (su tipo prohibido sí se comprueba antes)
TERCEROS='(^|/)(vendor|node_modules|bower_components)/|(^|/)(composer[.]lock|package-lock[.]json|yarn[.]lock|pnpm-lock[.]yaml|Pipfile[.]lock|poetry[.]lock)$|[.]min[.](js|css)$|[.](map|ttf|otf|woff2?|eot|png|jpe?g|gif|webp|avif|ico|svg|mp3|mp4|webm|wav|ogg)$'
saltar() {
    case "$1" in scripts/comprobar_secretos.sh|.secretos-ignorar|.secretos-historial|.github/workflows/secretos.yml) return 0 ;; esac
    local g; for g in "${ignorar[@]+"${ignorar[@]}"}"; do [[ "$1" == $g ]] && return 0; done
    return 1
}
fallo=0
informar() {  # $1 ruta, $2 tipo, $3 líneas
    echo "secretos: $1 — $2${3:+ (líneas: $3)}" >&2
    fallo=1
}

# Datos personales: Python si lo hay (comprueba la letra del DNI y descarta lo ficticio).
PY_PERSONALES='
import re,sys
L="TRWAGMYFPDXBNJZSQVHLCKE"
t=sys.stdin.read()
if "\0" in t[:8000]: sys.exit(0)
ficticio=re.compile(r"(\d)\1{4}|12345|23456|34567|45678|56789|98765|87654|00000")
def linea(i): return t.count("\n",0,i)+1
out=[]
d=[]
for m in re.finditer(r"\b([0-9]{8}[A-HJ-NP-TV-Z]|[XYZ][0-9]{7}[A-HJ-NP-TV-Z])\b",t):
    v=m.group(1); n=v[:-1].replace("X","0").replace("Y","1").replace("Z","2")
    if L[int(n)%23]==v[-1] and not ficticio.search(v): d.append(linea(m.start()))
if d: out.append(("DNI/NIE real",d))
tel={}
svg=re.compile(r"<path|<polyline|<polygon|\bd=\\?[\"\x27][Mm]|points=|viewBox")
for m in re.finditer(r"(?<![0-9A-Za-z.,:/#-])(?:\+34[ ]?)?([67][0-9]{2}(?:[0-9]{6}|([ .-])[0-9]{3}\2[0-9]{3}|([ .-])[0-9]{2}\3[0-9]{2}\3[0-9]{2}))(?![0-9A-Za-z.,:/-]|[ ][0-9])",t):
    v=re.sub(r"\D","",m.group(1))
    if v.startswith("600") or ficticio.search(v): continue
    i=t.rfind("\n",0,m.start())+1; j=t.find("\n",m.end()); j=len(t) if j<0 else j
    if svg.search(t[max(i,m.start()-300):min(j,m.end()+300)]): continue
    tel.setdefault(v,linea(m.start()))
if len(tel)>=2: out.append(("móviles reales (%d)"%len(tel),sorted(tel.values())))
c=[]
for m in re.finditer(r"\b([A-Za-z0-9._%+-]+)@(gmail|googlemail|hotmail|yahoo|outlook|icloud|me|live|msn|telefonica|ono|terra)[.][a-z.]+",t,re.I):
    if not re.search(r"tu[_.]?|tuemail|usuario|user|ejemplo|example|nombre|test|prueba|fake|ficticio|demo|foo|bar|alumno|tutor|profe|apellido|correo|email|mail",m.group(1),re.I): c.append(linea(m.start()))
if c: out.append(("correo personal",c))
todos={m.group(0).lower():linea(m.start()) for m in re.finditer(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:[.][A-Za-z0-9-]+)+",t) if not re.search(r"@(example|ejemplo|test|localhost)|[.](test|invalid|local|example)$",m.group(0),re.I)}
if len(todos)>=15: out.append(("listado de %d correos de personas"%len(todos),sorted(todos.values())[:5]))
import math
def entropia(s): return -sum(s.count(ch)/len(s)*math.log2(s.count(ch)/len(s)) for ch in set(s))
js=[]
for m in re.finditer(r"[\"\x27]([A-Za-z_]*(?:password|passwd|secret|token|api_?key|clave|contrase)[A-Za-z_]*)[\"\x27]\s*:\s*[\"\x27]([^\"\x27\s]{10,})[\"\x27]",t,re.I):
    v=m.group(2)
    if re.search(r"prueba|test|ejemplo|example|dummy|fake|ficticio|changeme|cambiar|xxx|secreto|desarrollo|\$\{|<",v,re.I): continue
    clases=sum(bool(re.search(x,v)) for x in (r"[a-z]",r"[A-Z]",r"[0-9]",r"[^A-Za-z0-9]"))
    if clases>=3 and entropia(v)>=3.3: js.append(linea(m.start()))
if js: out.append(("secreto en JSON o diccionario",js))
ins=len(re.findall(r"^\s*INSERT\s+INTO",t,re.I|re.M))
if ins>20: out.append(("volcado SQL con datos (%d INSERT)"%ins,[]))
for tipo,ls in out: print(tipo+"\t"+",".join(map(str,sorted(set(ls))[:12])))
'
TMPF=$(mktemp) || exit 2
trap '[ -n "$TMPF" ] && [ -f "$TMPF" ] && rm -f -- "$TMPF"' EXIT
revisar() {  # $1 = ruta; contenido por stdin. Se vuelca a un temporal: bash pierde los bytes nulos y los binarios se confundirían con texto
    local salida tipo lin
    cat > "$TMPF"
    grep -Iq . "$TMPF" 2>/dev/null || return 0     # binario o vacío: solo cuenta su tipo
    salida=$( { { grep -n -I -i -E -e "$P" "$TMPF"; grep -n -I -E -e "$S" "$TMPF"; } 2>/dev/null | grep -v -i -E -e "$MARCADORES"; grep -n -I -i -E -e "$H" "$TMPF" 2>/dev/null; } | sort -t: -k1,1n -u)
    [ -n "$salida" ] && informar "$1" "secreto o dato de infraestructura" "$(echo "$salida" | cut -d: -f1 | paste -sd, -)"
    if command -v python3 >/dev/null 2>&1; then
        while IFS=$'\t' read -r tipo lin; do [ -n "$tipo" ] && informar "$1" "$tipo" "$lin"; done \
            < <(python3 -I -c "$PY_PERSONALES" < "$TMPF" 2>/dev/null)
    fi
}
tipo_prohibido() { [[ "$1" =~ $PROHIBIDOS ]] && ! [[ "$1" =~ [.]example$|[.]sample$ ]]; }

# gitleaks con las mismas excepciones (las rutas de .secretos-ignorar, pasadas a expresión regular)
gitleaks_config() {
    local cfg="$1" g re
    {
        echo '[extend]'; echo 'useDefault = true'
        echo '[[allowlists]]'; echo 'description = "excepciones del repositorio"'
        printf 'paths = ['
        printf "'''%s''', " '[.](css|scss|svg|map)$' '(^|/)(package-lock[.]json|composer[.]lock|yarn[.]lock)$' '(^|/)vendor/' '(^|/)node_modules/' '(^|/)scripts/comprobar_secretos[.]sh$'
        for g in "${ignorar[@]+"${ignorar[@]}"}"; do
            re=$(printf '%s' "$g" | sed -e 's/[.^$+(){}|]/\\&/g' -e 's/\*\*/§/g' -e 's/\*/[^\/]*/g' -e 's/§/.*/g' -e 's/?/./g')
            printf "'''^%s\$''', " "$re"
        done
        echo ']'
        echo 'stopwords = ["YOUR_TOKEN", "your_token", "tu_token", "TU_TOKEN", "example", "ejemplo", "changeme", "CAMBIAR"]'
    } > "$cfg"
}
pasar_gitleaks() {  # $@ = argumentos de gitleaks tras el subcomando
    command -v gitleaks >/dev/null 2>&1 || { [ "${CI:-}" = "true" ] && { echo "secretos: gitleaks no está instalado en la CI" >&2; fallo=1; }; return 0; }
    local tmp; tmp=$(mktemp -d) || return 0
    gitleaks_config "$tmp/cfg.toml"
    gitleaks "$@" --config "$tmp/cfg.toml" --redact --no-banner -l error --exit-code 0 --report-format json --report-path "$tmp/inf.json" >/dev/null 2>&1
    if [ -s "$tmp/inf.json" ] && command -v python3 >/dev/null 2>&1; then
        while IFS=$'\t' read -r f t l; do [ -n "$f" ] && { saltar "$f" || informar "$f" "gitleaks: $t" "$l"; }; done < <(python3 -I -c '
import json,sys,collections
d=json.load(open(sys.argv[1])) or []
g=collections.defaultdict(set)
for x in d: g[(x["File"],x["RuleID"])].add(str(x["StartLine"])+("@"+x["Commit"][:8] if x.get("Commit") else ""))
for (f,r),ls in sorted(g.items()): print(f+"\t"+r+"\t"+",".join(sorted(ls)[:8]))' "$tmp/inf.json")
    fi
    [ -n "$tmp" ] && [ -d "$tmp" ] && rm -r -- "$tmp"
}

pasar_gitleaks_arbol() {  # gitleaks sobre los archivos versionados (no sobre .env ni otros ignorados)
    command -v gitleaks >/dev/null 2>&1 || { [ "${CI:-}" = "true" ] && { echo "secretos: gitleaks no está instalado en la CI" >&2; fallo=1; }; return 0; }
    local arbol; arbol=$(mktemp -d) || return 0
    git ls-files -z | xargs -0 tar -cf - 2>/dev/null | tar -xf - -C "$arbol" 2>/dev/null
    local antes=$fallo
    ( cd "$arbol" && git init -q && git add -A >/dev/null 2>&1 && git -c user.name=b -c user.email=b@b.invalid commit -q -m arbol --no-verify >/dev/null 2>&1 )
    cp .secretos-ignorar "$arbol/" 2>/dev/null
    while IFS= read -r l; do echo "$l" >&2; fallo=1; done < <(cd "$arbol" && bash "$YO" --historial-gitleaks 2>&1 >/dev/null | grep '^secretos: .* — gitleaks')
    [ -n "$arbol" ] && [ -d "$arbol" ] && rm -r -f -- "$arbol"
    return 0
}

case "$modo" in
    --preparado)
        while IFS= read -r -d '' f; do
            saltar "$f" && continue
            tipo_prohibido "$f" && informar "$f" "tipo de archivo que no se versiona (datos, copias, claves o documentos)"
            [[ "$f" =~ $TERCEROS ]] && continue
            revisar "$f" < <(git show ":$f")
        done < <(git diff --cached --name-only --diff-filter=ACM -z)
        pasar_gitleaks git --pre-commit --staged . ;;
    --todo)
        while IFS= read -r -d '' f; do
            saltar "$f" && continue
            tipo_prohibido "$f" && informar "$f" "tipo de archivo que no se versiona (datos, copias, claves o documentos)"
            [[ "$f" =~ $TERCEROS ]] && continue
            [ -f "$f" ] && revisar "$f" < "$f"
        done < <(git ls-files -z)
        pasar_gitleaks_arbol ;;
    --rango)
        [ $# -ge 2 ] || { echo "uso: $0 --rango A..B | --rango SHA --not --remotes" >&2; exit 2; }
        shift; rango_args=("$@"); rango="$*"
        while IFS= read -r f; do
            [ -z "$f" ] && continue; saltar "$f" && continue
            tipo_prohibido "$f" && informar "$f" "tipo de archivo que no se versiona (en $rango)"
        done < <(git log --format= --name-only --diff-filter=ACM "${rango_args[@]}" | sort -u)
        while IFS= read -r f; do   # contenido tal como queda en el último commit del rango
            [ -z "$f" ] && continue; saltar "$f" && continue; [[ "$f" =~ $TERCEROS ]] && continue
            revisar "$f" < <(git show "${rango_args[0]##*..}:$f" 2>/dev/null)
        done < <(git log --format= --name-only --diff-filter=ACM "${rango_args[@]}" | sort -u)
        pasar_gitleaks git --log-opts="$rango" . ;;
    --historial)
        echo "secretos: revisando todos los objetos de todas las ramas y etiquetas…" >&2
        while read -r sha ruta; do
            [ -z "${ruta:-}" ] && continue
            saltar "$ruta" && continue
            [[ "$revisados" == *" $sha "* ]] && continue
            [ "$(git cat-file -t "$sha")" = blob ] || continue
            tipo_prohibido "$ruta" && informar "$ruta" "tipo de archivo que no se versiona (en el historial)"
            [[ "$ruta" =~ $TERCEROS ]] && continue
            revisar "$ruta" < <(git cat-file -p "$sha")
        done < <(git rev-list --all --objects | awk 'NF>1 && !v[$1]++')
        pasar_gitleaks git --log-opts="--all" . ;;
    --historial-gitleaks)
        pasar_gitleaks git --log-opts="--all" . ;;
    *) echo "uso: $0 [--preparado|--todo|--rango A..B|--historial|--historial-gitleaks]" >&2; exit 2 ;;
esac
if [ "$fallo" -ne 0 ]; then
    echo "secretos: las credenciales y los datos del servidor van en .env, en Ajustes de cada equipo o en el llavero; los datos reales (alumnado, claustro, familias) y los documentos del centro, fuera del repositorio. Los tests, con datos ficticios. Si es un falso positivo, añade la ruta a .secretos-ignorar con su motivo." >&2
    exit 1
fi
exit 0
