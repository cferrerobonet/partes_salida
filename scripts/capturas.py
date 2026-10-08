"""Capturas de la interfaz con datos ficticios, para la documentación.

    QT_QPA_PLATFORM=offscreen ~/.venvs/partes-salida/bin/python scripts/capturas.py [carpeta]

Monta una carpeta de datos temporal con el alumnado de `tests/ficticios.py`, abre
la ventana principal y cada apartado de Ajustes y guarda un PNG de cada uno
(por defecto en `docs/capturas/`). Nunca usa datos reales.
"""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(RAIZ / "src"), str(RAIZ)]


def main() -> None:
    destino = Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "docs" / "capturas"
    destino.mkdir(parents=True, exist_ok=True)
    temporal = Path(tempfile.mkdtemp(prefix="partes-capturas-"))
    os.environ["PARTES_SALIDA_DATOS"] = str(temporal)
    os.environ["PARTES_SALIDA_SIN_LLAVERO"] = "1"

    from PyQt6.QtCore import QTime
    from PyQt6.QtWidgets import QApplication

    app = QApplication([])
    from tests import ficticios

    from partes_salida.contexto import Contexto
    from partes_salida.importar_excel import importar_excel
    from partes_salida.importar_fotos import importar_fotos
    from partes_salida.modelo import sin_tildes
    from partes_salida.ui import estilo
    from partes_salida.ui.ajustes import APARTADOS, DialogoAjustes
    from partes_salida.ui.ventana import VentanaPrincipal

    estilo.cargar_fuentes()
    estilo.aplicar(app)
    ctx = Contexto(temporal)
    ctx.nuevo_padron(importar_excel(ficticios.excel(temporal / "alumnos.xlsx")).alumnos, "ExportacionDatosAlumnos.xls")
    informe = importar_fotos([ficticios.zip_fotos(temporal / "fotos.zip")], ctx.alumnos, ctx.almacen)
    ctx.fotos_cambiadas()
    sello = os.environ.get("PARTES_SELLO_PRUEBA")
    if sello and Path(sello).exists():
        ctx.gestor.poner_imagen("sello", sello)

    ventana = VentanaPrincipal(ctx)
    ventana.resize(1100, 700)
    ventana.show()
    ventana.hora.setTime(QTime(12, 30))
    ventana.buscador.setText("beltran")
    ventana.actualizar_lista()
    ventana.buscador.clear()
    ventana.actualizar_lista()
    for _ in range(5):
        app.processEvents()
    ventana.vista._pintar()
    app.processEvents()
    ventana.grab().save(str(destino / "1-ventana-principal.png"))

    dialogo = DialogoAjustes(ctx, ventana)
    dialogo.ultimo_informe = informe
    dialogo._refrescar_datos()
    dialogo.resize(980, 640)
    dialogo.show()
    for i, nombre in enumerate(APARTADOS):
        dialogo.nav.setCurrentRow(i)
        for _ in range(3):
            app.processEvents()
        dialogo.grab().save(str(destino / f"ajustes-{i + 1}-{sin_tildes(nombre.split()[0]).lower()}.png"))
    print(f"Capturas en {destino}")


if __name__ == "__main__":
    main()
