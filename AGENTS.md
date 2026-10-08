# Partes de salida — instrucciones para agentes

App de escritorio (macOS y Windows, Python 3.11 + PyQt6) que imprime en DIN-A6 el pase de salida del alumnado de EPLA y avisa a la familia por correo. Sin servidor; datos cifrados en local. Repositorio **público**: `github.com/cferrerobonet/partes_salida`. Fuente única de instrucciones: `CLAUDE.md` solo la importa.

## Forma de trabajar

- Español. Usuario: **CarlosFB**. Respuestas cortas; sin explicaciones ni código no pedidos.
- **Nunca escribir la palabra prohibida de la bóveda** (el nombre del asistente) en ningún archivo ni commit; los nombres `CLAUDE.md` y `.claude/` sí valen. Los ganchos lo vigilan.
- **Ningún dato del alumnado ni foto en el repositorio** (prioridad absoluta de CarlosFB). Datos reales solo en `../Material de pruebas` (fuera) y datos de tests en `tests/ficticios.py`.
- **No se compila en local**: se compila en GitHub (skill `publicar`). El gancho lo bloquea.
- **Sin datos, no se implementa**: si falta un dato del que depende algo, se apunta en `docs/PENDIENTE.md` y se pide.
- «Verificado» = hay una prueba que falla al revertir el cambio. La impresora real no se prueba en la suite: tras tocar `parte.py` o `impresion.py`, pedir un parte de prueba impreso.
- Leer por rangos (`grep -n`), no releer, no listar `src/` (usar el mapa).

## Mapa

| Qué | Dónde |
| --- | --- |
| Arranque, instancia única, bandeja, prueba de arranque | `src/partes_salida/app.py` (entrada `src/main.py`) |
| Estado compartido y señales | `contexto.py` |
| Ventana principal (buscar · ficha · imprimir) | `ui/ventana.py` |
| Ajustes (8 apartados, importaciones en hilo) | `ui/ajustes.py` · diálogos en `ui/dialogos.py` |
| Tokens, hoja de estilos, tipografías, iconos | `ui/estilo.py` |
| Dibujo del parte (mm) e impresión | `parte.py` · `impresion.py` |
| Excel · fotos · búsqueda | `importar_excel.py` (`COLUMNAS`) · `importar_fotos.py` · `busqueda.py` |
| Cifrado · almacén · firma del QR | `cifrado.py` · `almacen.py` · `firma.py` |
| Correo · ajustes · actualizaciones · registro | `correo.py` · `ajustes.py` · `actualizaciones.py` · `sistema.py` |
| Compilación | `PartesSalida.spec`, `installer_windows.iss`, `scripts/build/`, `.github/workflows/compilar.yml` |
| App del vigilante y contrato del QR | `android/` |
| Documentación | `docs/README.md` (mapa) |

Arquitectura completa: `docs/ARQUITECTURA.md`. Diseño: `DESIGN.md`. Decisiones: `docs/DECISIONES.md`.

## Comandos

```bash
PY=~/.venvs/partes-salida/bin/python      # fuera de iCloud, obligatorio
scripts/qa.sh todo                         # ruff + suite; log completo en /tmp/partes-qa-todo.log
scripts/qa.sh rapido                       # sin interfaz ni navegador
QT_QPA_PLATFORM=offscreen $PY -m pytest tests/test_x.py -x
make capturas · make vectores · make run
```

## Reglas por zona (`.claude/rules/`, se cargan solas al tocar la zona)

| Al tocar… | Regla |
| --- | --- |
| `tests/`, `pyproject.toml`, `scripts/qa.sh` | `tests.md` |
| spec, instalador, Makefile, workflows, actualizaciones, arranque | `empaquetado.md` |
| cifrado, almacén, importadores, firma, correo, ajustes, `.gitignore` | `seguridad-y-datos.md` |
| `ui/`, `parte.py`, `DESIGN.md` | `interfaz.md` |
| documentación y `.claude/` | `documentacion.md` |
| `android/`, `firma.py` | `android.md` |

## Cada cambio publicado es una versión

SemVer en `pyproject.toml` **y** `src/partes_salida/__init__.py` (test), entrada en `CHANGELOG.md`, commit con ficheros concretos (Conventional Commits en español, sin coautoría), push y etiqueta `vX.Y.Z`: skill `publicar`, que además sigue la compilación de GitHub y anota la versión en la ficha de la bóveda (`../PARTES DE SALIDA — Índice.md`).

## Skills y agentes del proyecto

Skills: `publicar` · `tests` · `auditar`. Agentes: `revisor` (solo lectura, hallazgos con fichero:línea) · `verificador` (pasa `qa.sh` y devuelve solo el resultado).

## Entorno

- Intérprete en `~/.venvs/partes-salida` (`make venv`). Dentro de iCloud, Qt deja de arrancar.
- `make ganchos` activa `.githooks/pre-commit`.
- Datos de este equipo de desarrollo: `~/Library/Application Support/PartesSalida`.
