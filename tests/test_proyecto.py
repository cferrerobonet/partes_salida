"""Invariantes del proyecto: versión, empaquetado y lo que no puede entrar en el repositorio."""

import re
import tomllib
from pathlib import Path

import partes_salida

RAIZ = Path(__file__).resolve().parents[1]
PALABRA = "C" + "laude"  # la palabra prohibida de la bóveda, sin escribirla aquí
TEXTO = {".py", ".md", ".toml", ".txt", ".yml", ".yaml", ".json", ".sh", ".ps1", ".iss", ".spec", ".kts", ".kt", ".xml", ""}


def test_version_coherente():
    pyproject = tomllib.loads((RAIZ / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["version"] == partes_salida.__version__


def test_changelog_tiene_la_version_actual():
    assert f"## [{partes_salida.__version__}]" in (RAIZ / "CHANGELOG.md").read_text(encoding="utf-8")


def test_spec_empaqueta_recursos_y_llavero():
    spec = (RAIZ / "PartesSalida.spec").read_text(encoding="utf-8")
    assert 'collect_submodules("keyring.backends")' in spec
    assert '"src/partes_salida/recursos"' in spec
    assert "upx=False" in spec


def test_recursos_con_nombres_ascii():
    """Un nombre con acento dentro del .app rompe su firma (lección de Guardias)."""
    raros = [str(f) for f in (RAIZ / "src" / "partes_salida" / "recursos").rglob("*") if not f.name.isascii()]
    assert not raros


def test_nombres_de_instaladores_coinciden_con_el_actualizador():
    from partes_salida.actualizaciones import INSTALADOR_POR_SISTEMA

    flujo = (RAIZ / ".github" / "workflows" / "compilar.yml").read_text(encoding="utf-8")
    dmg = (RAIZ / "scripts" / "build" / "build_dmg.sh").read_text(encoding="utf-8")
    iss = (RAIZ / "installer_windows.iss").read_text(encoding="utf-8")
    assert INSTALADOR_POR_SISTEMA["Darwin"].replace("{v}", "${VERSION}") in dmg
    assert "PartesDeSalida-{#MyAppVersion}-Windows-Setup" in iss
    assert INSTALADOR_POR_SISTEMA["Windows"] == "PartesDeSalida-{v}-Windows-Setup.exe"
    assert "PRUEBA DE ARRANQUE: ventana principal a la vista" in flujo


def test_sin_palabra_prohibida():
    patron = re.compile(rf"\b{PALABRA}\b")
    culpables = []
    for f in RAIZ.rglob("*"):
        partes = f.relative_to(RAIZ).parts
        if not f.is_file() or partes[0] in (".git", ".ruff_cache", "build", "dist", "test-results") or "__pycache__" in partes:
            continue
        if f.suffix.lower() not in TEXTO:
            continue
        if patron.search(f.read_text(encoding="utf-8", errors="ignore")):
            culpables.append(str(f.relative_to(RAIZ)))
    assert not culpables, f"Palabra prohibida en: {culpables}"
