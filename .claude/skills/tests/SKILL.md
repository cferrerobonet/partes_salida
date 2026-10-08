---
name: tests
description: Ejecutar y depurar las pruebas de Partes de salida — unitarios, interfaz con pytest-qt sin pantalla, correo HTML en Chromium con Playwright, datos reales en local y capturas de la interfaz. Usar cuando se pida «pasa los tests», antes de publicar, o para diagnosticar un fallo.
---

# Pruebas

Reglas para escribirlas: `.claude/rules/tests.md`.

## Intérprete

`~/.venvs/partes-salida/bin/python` (fuera de iCloud: dentro, iCloud duplica binarios y Qt deja de arrancar). Recrear con `make venv` (instala también Chromium para Playwright).

## Comandos (la salida completa queda en `/tmp/partes-qa-<tarea>.log`)

| Qué | Comando |
| --- | --- |
| Lint + suite (lo de antes de publicar) | `scripts/qa.sh todo` |
| Solo ruff | `scripts/qa.sh lint` |
| Sin interfaz ni navegador (segundos) | `scripts/qa.sh rapido` |
| Correo en el navegador | `scripts/qa.sh navegador` |
| Un fichero | `QT_QPA_PLATFORM=offscreen ~/.venvs/partes-salida/bin/python -m pytest tests/test_x.py -x` |
| Con los datos reales de `../Material de pruebas` | `… -m pytest -m datos_reales` (se salta si la carpeta no está) |
| Capturas de la interfaz con datos ficticios | `make capturas` → `docs/capturas/` |

Un fallo se lee en el log: `grep -n -B2 -A15 FAILED /tmp/partes-qa-todo.log`. **No relanzar la suite entera para ver un error.**

## Diagnóstico de fallos que no son del código

| Síntoma | Causa y arreglo |
| --- | --- |
| `Could not load the Qt platform plugin` | Falta `QT_QPA_PLATFORM=offscreen` (o, en Linux, las librerías `libxcb-*` de `comprobar.yml`) |
| Qt aborta al crear la aplicación | Intérprete dentro de iCloud: usar el de `~/.venvs/partes-salida` |
| Tests de navegador omitidos o «Executable doesn't exist» | `~/.venvs/partes-salida/bin/python -m playwright install chromium` |
| Ventana del llavero al pasar tests | Algún test sin la barrera: `conftest.py` pone `PARTES_SALIDA_SIN_LLAVERO=1` antes de importar nada |
| `timeout` no existe en macOS | `perl -e 'alarm N; exec @ARGV' <orden>` |

## Lo que la suite no prueba

La app compilada (eso lo hace la CI: arranque del exe y del `.app`) ni la impresora real: tras tocar `parte.py` o `impresion.py`, pedir a CarlosFB un **parte de prueba impreso** (Ajustes → Impresión) antes de dar el cambio por bueno.
