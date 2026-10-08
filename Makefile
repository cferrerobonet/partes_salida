.PHONY: help venv test test-rapido lint qa icono app dmg capturas vectores ganchos limpiar run

# El entorno vive FUERA del repositorio: iCloud duplica los binarios y deja a Qt
# sin complementos (lección de Guardias de patio).
VENV := $(HOME)/.venvs/partes-salida
PY := $(VENV)/bin/python
export QT_QPA_PLATFORM ?= offscreen

help:
	@echo "Partes de salida — órdenes"
	@echo "  make venv        Crear o actualizar el entorno ($(VENV)) y el navegador de Playwright"
	@echo "  make ganchos     Activar los ganchos de git del repositorio (.githooks)"
	@echo "  make run         Abrir la aplicación"
	@echo "  make test        Suite completa (unitarios, interfaz, correo en navegador)"
	@echo "  make test-rapido Sin interfaz ni navegador"
	@echo "  make lint        ruff"
	@echo "  make qa          lint + test, con la salida completa en /tmp/partes-qa-*.log"
	@echo "  make capturas    Capturas de la interfaz con datos ficticios en docs/capturas/"
	@echo "  make vectores    Regenerar android/vectores_qr.json"
	@echo "  make app|dmg     Solo para la CI de GitHub: en local no se compila"
	@echo "  make limpiar     Borrar build/, dist/ y cachés"

venv:
	@test -x "$(PY)" || python3.11 -m venv "$(VENV)"
	$(PY) -m pip install --upgrade pip setuptools
	$(PY) -m pip install -r requirements-dev.txt
	$(PY) -m playwright install chromium

ganchos:
	git config core.hooksPath .githooks
	chmod +x .githooks/* .claude/hooks/*.sh scripts/*.sh scripts/build/*.sh
	@echo "Ganchos activos: .githooks/pre-commit"

run:
	QT_QPA_PLATFORM= $(PY) src/main.py

test:
	$(PY) -m pytest

test-rapido:
	$(PY) -m pytest -m "not ui and not navegador"

lint:
	$(PY) -m ruff check src tests scripts

qa:
	scripts/qa.sh todo

capturas:
	$(PY) scripts/capturas.py

vectores:
	$(PY) scripts/generar_vectores_qr.py

icono:
	scripts/build/crear_icono.sh

app: icono
	$(PY) -m PyInstaller PartesSalida.spec --noconfirm --clean

dmg: icono
	SKIP_RELEASE=1 PY="$(PY)" scripts/build/build_dmg.sh

limpiar:
	rm -rf build dist Output *.dmg test-results imagenes/*.iconset
	find . -path ./.git -prune -o -name "__pycache__" -type d -print0 | xargs -0 rm -rf
