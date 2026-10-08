---
name: publicar
description: Cierra y publica una versión de Partes de salida — sube la versión (SemVer), escribe el CHANGELOG, pasa lint y tests, hace commit con ficheros concretos, push, etiqueta vX.Y.Z y sigue la compilación de GitHub hasta que el release tiene el DMG de macOS y el instalador y el portable de Windows; después anota la versión en la ficha de la bóveda. Usar tras cada cambio que se quiera llevar a los equipos, o cuando CarlosFB diga «publica», «sube versión», «commit y push» o «compila».
---

# Publicar una versión

Sin pedir confirmación en cada paso: es el flujo acordado. Se compila **solo en GitHub** (nunca en local).

## 1. Situarse

- `git status --short` y `git log --oneline -5`. Si hay cambios de otra tarea sin terminar, preguntarlo antes de mezclarlos.
- Versión actual: `sed -n 's/^version = "\(.*\)"/\1/p' pyproject.toml`.
- Decidir el salto (SemVer): arreglo → patch · función nueva o cambio visible → minor · rompe datos, formato del QR o ajustes → major.

## 2. Preparar

1. Subir la versión en **los dos sitios**: `pyproject.toml` (`version = "X.Y.Z"`) y `src/partes_salida/__init__.py` (`__version__`). Un test vigila que coincidan.
2. `CHANGELOG.md`: entrada nueva **arriba** con `## [X.Y.Z] - AAAA-MM-DD`, escrita para quien usa la app (qué cambia en su pantalla), con secciones `Añadido`, `Cambiado`, `Corregido` o `Seguridad` según toque. Es la nota del release en GitHub.
3. Impacto documental (regla `documentacion.md`): actualizar lo que toque o decir «sin impacto documental».
4. `scripts/qa.sh todo` → tiene que acabar en `QA todo: OK`. Si falla, leer el log con `grep`, no relanzar.

## 3. Commit, push y etiqueta

- **Nunca `git add -A` ni `git add .`** (el gancho lo bloquea): ficheros concretos. Lista de candidatos: `git status --short`.
- **Antes del commit, revisar que no entra ningún dato**: `git diff --cached --name-only` no puede tener `.xls`, `.zip`, `.bin`, `.jpg`, imágenes fuera de `imagenes/`, `src/partes_salida/recursos/` o `docs/capturas/`, ni nombres con coma. El gancho `.githooks/pre-commit` lo vigila también (activo con `make ganchos`).
- Mensaje: Conventional Commits en español, minúscula tras los dos puntos: `feat(ui): …`, `fix(correo): …`, `docs: …`, `chore(release): vX.Y.Z`. Sin línea de coautoría ni la palabra prohibida.

```bash
git add <ficheros>
git commit -m "tipo(zona): descripción"
git push origin main
git tag vX.Y.Z
git push origin vX.Y.Z
```

## 4. Seguir la compilación

```bash
gh run list --workflow compilar.yml --limit 1
gh run watch <id> --exit-status
gh release view vX.Y.Z --json assets --jq '.assets[].name'
```

Tienen que estar los tres: `PartesSalida_vX.Y.Z_macOS.dmg`, `PartesDeSalida-X.Y.Z-Windows-Setup.exe` y `PartesDeSalida-X.Y.Z-Windows-Portable.zip`. Si un job falla: `gh run view <id> --log-failed | tail -60`, arreglar, subir **patch nuevo** (nunca reescribir una etiqueta publicada).

## 5. Cerrar

- Ficha de la bóveda `../PARTES DE SALIDA — Índice.md`: actualizar «Versión vigente» y añadir arriba la fila del historial (fecha, versión, una línea). `fecha_actualizacion` del frontmatter a hoy.
- Responder a CarlosFB en dos o tres líneas: versión, qué cambia, enlace del release. Los equipos reciben el aviso de versión nueva al abrir la app.
