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

    # Historial y recurrentes de muestra (ficticios), para sus pantallas.
    from datetime import date, datetime, timedelta

    from partes_salida.seguimiento import CORREO, PAPEL, Recurrencia, Salida

    por = {a.nombre: a for a in ctx.alumnos}
    lunes = date.today() - timedelta(days=date.today().weekday())
    for i, (dias, hora, entrega, avisados) in enumerate((
        (1, "12:30", PAPEL, ["madre", "padre"]), (6, "10:15", CORREO, ["alumna"]), (13, "13:00", PAPEL, []),
        (20, "11:45", PAPEL, ["madre"]), (27, "09:30", CORREO, ["madre", "alumna"]),
    )):
        momento = datetime.combine(date.today() - timedelta(days=dias), datetime.strptime(hora, "%H:%M").time())
        s = Salida.nueva(momento, entrega, avisados, expedido=momento - timedelta(minutes=5 + i))
        s.correo = "enviado" if avisados else ""
        ctx.seguimiento.registrar(por["NEREA"].id, s)
    ctx.seguimiento.poner_recurrencia(por["MARC"].id, Recurrencia({0: "12:30", 2: "12:30", 4: "13:15"},
                                                                  motivo="Conservatorio", entrega=CORREO))
    ctx.seguimiento.poner_recurrencia(por["HUGO"].id, Recurrencia({d: "11:00" for d in range(5)},
                                                                  motivo="Deportista de élite", avisar_familia=True))
    ctx.seguimiento.poner_recurrencia(por["IVÁN"].id, Recurrencia({0: "13:00", 3: "13:00"}))

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

    from partes_salida.ui.seguimiento import DialogoHistorial, DialogoRecurrente, DialogoRecurrentes

    def capturar(dialogo, nombre: str, ancho: int, alto: int) -> None:
        dialogo.resize(ancho, alto)
        dialogo.show()
        for _ in range(4):
            app.processEvents()
        dialogo.grab().save(str(destino / nombre))
        dialogo.close()

    capturar(DialogoHistorial(ctx, por["NEREA"], ventana), "2-historial.png", 900, 580)
    capturar(DialogoRecurrente(ctx, por["MARC"], ventana), "3-parte-recurrente.png", 680, 470)
    capturar(DialogoRecurrentes(ctx, ventana, hoy=lunes), "4-recurrentes-de-hoy.png", 940, 600)
    ventana.buscador.setText("albert")
    ventana.actualizar_lista()
    ventana.entrega_correo.click()
    for _ in range(5):
        app.processEvents()
    ventana.vista._pintar()
    app.processEvents()
    ventana.grab().save(str(destino / "1-ventana-por-correo.png"))
    ventana.buscador.setText("beltran")
    ventana.actualizar_lista()
    app.processEvents()

    from partes_salida.parte import imagen_parte

    for orientacion in ("horizontal", "vertical"):
        ctx.gestor.poner(orientacion=orientacion)
        imagen_parte(ventana.datos_parte(), ctx.gestor, ctx.imagenes, 1200).save(
            str(destino / f"parte-{orientacion}.png"))
    ctx.gestor.poner(orientacion="horizontal")

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
