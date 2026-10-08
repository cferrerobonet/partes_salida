# Cómo trabajar en Partes de salida

## Entorno

```bash
make venv      # ~/.venvs/partes-salida (fuera de iCloud) + Chromium para Playwright
make ganchos   # .githooks/pre-commit: bloquea datos del alumnado, imágenes fuera de sitio y secretos
make run
```

La carpeta del repositorio está en iCloud: el entorno virtual, las cachés y los artefactos van fuera (`~/.venvs`, `/tmp`). Los datos reales de prueba están en `../Material de pruebas`, fuera del repositorio, y **nunca se copian dentro**.

## Ciclo de un cambio

1. Leer la especificación y la regla de la zona (`docs/`, `DESIGN.md`, `.claude/rules/`).
2. Cambiar el código **y su test** (una regresión debe fallar al revertir el arreglo).
3. `scripts/qa.sh todo` en verde.
4. Actualizar el documento que toque (tabla en `.claude/rules/documentacion.md`) o anotar «sin impacto documental».
5. Commit con ficheros concretos (nunca `git add -A`), push y, si va a los equipos, versión y etiqueta (skill `publicar`).

## Ramas y PR

- `main` siempre publicable. Para cambios grandes, rama `tipo/descripcion-corta` y PR con la plantilla (`.github/pull_request_template.md`); la CI `Comprobar` tiene que estar en verde.
- Un cambio pequeño de una persona puede ir directo a `main` si pasa `qa.sh todo`.

## Commits

[Conventional Commits](https://www.conventionalcommits.org/es/) en español, minúscula tras los dos puntos:

`feat(ui): …` · `fix(correo): …` · `docs: …` · `test: …` · `refactor(parte): …` · `chore(release): v0.2.0`

Zonas habituales: `ui`, `parte`, `importar`, `cifrado`, `correo`, `qr`, `build`, `android`. Sin línea de coautoría.

## Versiones

SemVer en `pyproject.toml` y `src/partes_salida/__init__.py` (un test vigila que coincidan): arreglo → patch, función o cambio visible → minor, cambio de formato de datos, ajustes o QR → major. Cada versión publicada lleva su entrada en `CHANGELOG.md`.

## Código

- Ruff (`pyproject.toml`), 120 columnas. Comentarios que explican **por qué**, no qué.
- Dominio sin Qt (`modelo`, `importar_*`, `cifrado`, `almacen`, `firma`, `correo`, `ajustes`); la interfaz solo en `ui/` y el dibujo del parte en `parte.py`.
- Trabajo largo (importar, correo) siempre en `ui.componentes.Tarea`.
- Colores solo de `ui/estilo.py`.
- Ningún dato personal en el registro.
