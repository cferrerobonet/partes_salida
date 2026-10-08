---
paths:
  - "PartesSalida.spec"
  - "installer_windows.iss"
  - "Makefile"
  - "scripts/build/**"
  - "scripts/*.ps1"
  - ".github/workflows/**"
  - "src/partes_salida/actualizaciones.py"
  - "src/partes_salida/app.py"
  - "src/partes_salida/rutas.py"
---

# Empaquetado y publicación

- **No se compila en local** (decisión de CarlosFB, 2026-10-08): se compila en GitHub. Etiqueta `vX.Y.Z` → `.github/workflows/compilar.yml` pasa las pruebas, compila Windows (instalador + portable) y macOS (DMG) y los adjunta al release. El gancho `guardia_bash.sh` bloquea PyInstaller y `make app|dmg` en local.
- **Un solo spec** (`PartesSalida.spec`) para las dos plataformas. Lleva `collect_submodules("keyring.backends")` y los recursos de `src/partes_salida/recursos`; lo vigila `tests/test_proyecto.py`.
- **Nombres ASCII** dentro de la app: un archivo con acento rompe la firma del `.app` (lección de Guardias, BLD-010). `test_proyecto.py` lo comprueba en `recursos/`.
- **Prueba de arranque** en la CI de las dos plataformas: `PARTES_PRUEBA_DE_ARRANQUE=ventana` abre la ventana, escribe `PRUEBA DE ARRANQUE: ventana principal a la vista` en el registro y sale. No quitarla: un exe que existe no es un exe que arranca.
- **Nombres fijos de los instaladores** (`PartesSalida_v<v>_macOS.dmg`, `PartesDeSalida-<v>-Windows-Setup.exe`): `actualizaciones.py` los usa para el plan B sin API. Si cambian aquí, cambian allí.
- Versión: `pyproject.toml` y `src/partes_salida/__init__.py` coinciden (test) y la CI rechaza una etiqueta que no case con `pyproject.toml`.
- Registro de la app instalada: macOS `~/Library/Application Support/PartesSalida/logs/`, Windows `%APPDATA%\PartesSalida\logs\`. Si «la app no abre», pedir antes ese registro.
