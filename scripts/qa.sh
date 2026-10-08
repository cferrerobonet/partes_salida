#!/bin/bash
# Comprobaciones con la salida completa en /tmp/partes-qa-<tarea>.log y solo el
# resumen en pantalla (patrón de Web Pedidos y AutoExam): un fallo se lee con
# grep en el log, nunca relanzando la suite entera.
#   scripts/qa.sh lint | test | rapido | navegador | todo
set -uo pipefail
cd "$(dirname "$0")/.."
PY="${PY:-$HOME/.venvs/partes-salida/bin/python}"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-offscreen}"
tarea="${1:-todo}"
log="/tmp/partes-qa-${tarea}.log"

case "$tarea" in
    lint) "$PY" -m ruff check src tests scripts >"$log" 2>&1 ;;
    test) "$PY" -m pytest >"$log" 2>&1 ;;
    rapido) "$PY" -m pytest -m "not ui and not navegador" >"$log" 2>&1 ;;
    navegador) "$PY" -m pytest -m navegador >"$log" 2>&1 ;;
    todo) { "$PY" -m ruff check src tests scripts && "$PY" -m pytest; } >"$log" 2>&1 ;;
    *) echo "Uso: scripts/qa.sh lint|test|rapido|navegador|todo"; exit 64 ;;
esac
codigo=$?
tail -n 6 "$log"
[ $codigo -eq 0 ] && echo "QA $tarea: OK (log: $log)" || echo "QA $tarea: FALLA ($codigo) — grep -n -B2 -A15 FAILED $log"
exit $codigo
