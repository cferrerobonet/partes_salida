"""Entrega por correo, historial y partes recurrentes con pytest-qt (sin pantalla)."""

from datetime import date, datetime

import pytest
from PyQt6.QtCore import Qt, QTime

from partes_salida.seguimiento import CORREO, PAPEL, Recurrencia, Salida

pytestmark = pytest.mark.ui
LUNES = date(2026, 10, 12)


@pytest.fixture
def ventana(qtbot, contexto):
    from partes_salida.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal(contexto)
    qtbot.addWidget(v)
    v.show()
    return v


@pytest.fixture
def correo(monkeypatch):
    """Sustituye impresora y SMTP: lo impreso y lo enviado quedan en listas."""
    hechos = {"impresos": [], "enviados": [], "trabajos": 0}

    def imprimir_varios(partes, ctx, padre):
        hechos["trabajos"] += 1
        hechos["impresos"].extend(partes)
        return True

    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios", imprimir_varios)
    monkeypatch.setattr("partes_salida.ui.envios.contrasena_smtp", lambda a: "clave")
    monkeypatch.setattr("partes_salida.ui.envios.enviar", lambda msg, a, c: hechos["enviados"].append(msg))
    return hechos


def elegir(qtbot, v, texto):
    v.buscador.setText(texto)
    v.actualizar_lista()
    qtbot.wait(10)
    return v.ficha.alumno


def test_por_correo_al_alumno_no_imprime_y_queda_en_el_historial(qtbot, ventana, correo, contexto):
    marc = elegir(qtbot, ventana, "albert")
    assert ventana.entrega_papel.isChecked(), "papel de serie"
    assert ventana.entrega_correo.isEnabled() and "marc.albert@" in ventana.entrega_detalle.text()
    qtbot.mouseClick(ventana.entrega_correo, Qt.MouseButton.LeftButton)
    assert ventana.boton_imprimir.text().startswith("Enviar parte")
    ventana.hora.setTime(QTime(12, 30))
    ventana.imprimir()
    qtbot.waitUntil(lambda: contexto.seguimiento.salidas(marc.id)[0].correo == "enviado", timeout=3000)
    assert correo["impresos"] == [], "por correo no se imprime"
    al_alumno = next(m for m in correo["enviados"] if m["To"] == "marc.albert@ejemplo.es")
    assert any(p.get_content_type() == "application/pdf" for p in al_alumno.iter_attachments())
    registro = contexto.seguimiento.salidas(marc.id)[0]
    assert registro.entrega == CORREO and "alumno" in registro.avisados and f"{registro.momento_salida:%H:%M}" == "12:30"
    assert "1 salida" in ventana.ficha.seg_historial.text()


def test_sin_correo_del_alumno_solo_papel_y_al_cambiar_de_alumno_vuelve_a_papel(qtbot, ventana):
    elegir(qtbot, ventana, "albert")
    qtbot.mouseClick(ventana.entrega_correo, Qt.MouseButton.LeftButton)
    assert ventana.entrega() == CORREO
    elegir(qtbot, ventana, "navarro")
    assert ventana.entrega_papel.isChecked() and not ventana.entrega_correo.isEnabled()
    assert "Sin correo del alumno" in ventana.entrega_detalle.text()
    assert ventana.boton_imprimir.text().startswith("Imprimir parte")


def test_imprimir_apunta_la_salida_y_cancelar_no(qtbot, ventana, correo, contexto, monkeypatch):
    nerea = elegir(qtbot, ventana, "beltran")
    ventana.imprimir()
    registro = contexto.seguimiento.salidas(nerea.id)[0]
    assert registro.entrega == PAPEL and registro.avisados == ["madre", "padre"] and not registro.recurrente
    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios", lambda *a: False)
    ventana.imprimir()
    assert len(contexto.seguimiento.salidas(nerea.id)) == 1, "si se cancela la impresión no se apunta"


def test_sin_contrasena_el_parte_por_correo_se_ofrece_en_papel(qtbot, ventana, correo, contexto, monkeypatch):
    from PyQt6.QtWidgets import QMessageBox

    monkeypatch.setattr("partes_salida.ui.envios.contrasena_smtp", lambda a: None)
    monkeypatch.setattr("partes_salida.ui.ventana.QMessageBox.question",
                        lambda *a, **k: QMessageBox.StandardButton.Yes)
    monkeypatch.setattr("partes_salida.ui.envios.QMessageBox.warning", lambda *a: None)
    marc = elegir(qtbot, ventana, "albert")
    qtbot.mouseClick(ventana.entrega_correo, Qt.MouseButton.LeftButton)
    ventana.imprimir()
    assert len(correo["impresos"]) == 1 and contexto.seguimiento.salidas(marc.id)[0].entrega == PAPEL


def test_historial_pagina_imprime_y_se_vacia(qtbot, contexto, monkeypatch):
    from partes_salida.ui import seguimiento as ui_seg

    a = contexto.alumnos[0]
    for minuto in range(12):
        contexto.seguimiento.registrar(a.id, Salida.nueva(datetime(2026, 10, 1, 9, minuto), PAPEL, []))
    d = ui_seg.DialogoHistorial(contexto, a)
    qtbot.addWidget(d)
    assert d.tabla.total == 12 and d.tabla.recuento.text() == "Mostrando 1–10 de 12 salidas"
    assert d.tabla.paginacion.isVisibleTo(d)
    impresos = []
    monkeypatch.setattr(ui_seg, "imprimir_documento", lambda html, titulo, padre: impresos.append(html) or True)
    qtbot.mouseClick(d.boton_imprimir, Qt.MouseButton.LeftButton)
    assert impresos and impresos[0].count("<tr>") == 12, "una fila por salida"
    d.tabla.buscador.setText("09:05")
    assert d.tabla.total == 1 and d.tabla.limpiar.isEnabled()
    monkeypatch.setattr(ui_seg, "_confirmar", lambda *a: True)
    qtbot.mouseClick(d.boton_vaciar, Qt.MouseButton.LeftButton)
    assert contexto.seguimiento.salidas(a.id) == [] and d.tabla.total == 0


def test_rejilla_semanal_del_recurrente(qtbot, contexto):
    from partes_salida.ui.seguimiento import DialogoRecurrente

    marc = next(a for a in contexto.alumnos if a.nombre == "MARC")
    d = DialogoRecurrente(contexto, marc)
    qtbot.addWidget(d)
    assert not d.guardar.isEnabled(), "sin días no se guarda"
    for dia in (0, 2):
        qtbot.mouseClick(d.dias[dia], Qt.MouseButton.LeftButton)
    assert d.horas[0].isEnabled() and not d.horas[1].isEnabled()
    d.hora_comun.setTime(QTime(13, 15))
    d._aplicar_comun()
    d.horas[2].setTime(QTime(14, 0))
    d.motivo.setText("Conservatorio")
    qtbot.mouseClick(d.correo, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(d.guardar, Qt.MouseButton.LeftButton)
    r = contexto.seguimiento.recurrentes[marc.id]
    assert r.horas == {0: "13:15", 2: "14:00"} and r.entrega == CORREO and r.motivo == "Conservatorio"
    assert r.resumen == "L 13:15 · X 14:00"


def test_recurrentes_del_dia_de_golpe_solo_etapas_visibles(qtbot, ventana, correo, contexto):
    from partes_salida.ui.seguimiento import DialogoRecurrentes

    por = {a.nombre: a for a in contexto.alumnos}
    seg = contexto.seguimiento
    seg.poner_recurrencia(por["MARC"].id, Recurrencia({0: "12:30"}, entrega=CORREO))  # 1CFS, por correo
    seg.poner_recurrencia(por["HUGO"].id, Recurrencia({0: "11:00"}))  # 2CFS, papel
    seg.poner_recurrencia(por["IVÁN"].id, Recurrencia({0: "13:00"}, avisar_familia=True))  # 1CFS, papel + padre
    seg.poner_recurrencia(por["PAU"].id, Recurrencia({0: "10:00"}))  # ESO: etapa oculta
    contexto.gestor.poner(etapas_ocultas=["ESO"])
    d = DialogoRecurrentes(contexto, ventana, hoy=LUNES)
    qtbot.addWidget(d)
    assert [p.alumno.nombre for p in d.marcados()] == ["HUGO", "MARC", "IVÁN"]
    assert d.boton_emitir.text() == "Imprimir 2 (uno por hoja) y enviar 1 por correo"
    qtbot.mouseClick(d.boton_emitir, Qt.MouseButton.LeftButton)
    assert correo["trabajos"] == 1, "todos los de papel en un solo trabajo de impresión"
    assert [(p.alumno.nombre, f"{p.salida:%H:%M}") for p in correo["impresos"]] == [("HUGO", "11:00"), ("IVÁN", "13:00")]
    qtbot.waitUntil(lambda: len(correo["enviados"]) == 2, timeout=3000)
    destinos = sorted(m["To"] for m in correo["enviados"])
    assert destinos == ["marc.albert@ejemplo.es", "rafa.navarro@ejemplo.es"]
    assert all(seg.salidas(por[n].id)[0].recurrente for n in ("MARC", "HUGO", "IVÁN"))
    assert seg.salidas(por["PAU"].id) == []
    assert d.marcados() == [] and "0 pendientes" in d.pestanas.tabText(0)
    assert d.tabla_todos.total == 3, "la lista de todos, también sin la etapa oculta"


def test_boton_de_la_barra_con_los_pendientes_de_hoy(qtbot, ventana, contexto):
    assert not ventana.boton_recurrentes.isVisible()
    marc = contexto.alumnos[0]
    contexto.seguimiento.poner_recurrencia(marc.id, Recurrencia({d: "12:30" for d in range(5)}))
    contexto.seguimiento_cambiado.emit()
    assert ventana.boton_recurrentes.isVisible()
    if date.today().weekday() < 5:
        assert ventana.boton_recurrentes.text() == "Partes recurrentes · 1 hoy"
        assert ventana.boton_recurrentes.property("primario")


def test_varios_partes_van_en_un_pdf_de_una_hoja_cada_uno(qtbot, contexto, monkeypatch, tmp_path):
    from PyQt6.QtPrintSupport import QPrintDialog, QPrinter

    from partes_salida import impresion
    from partes_salida.parte import DatosParte

    salida_pdf = tmp_path / "partes.pdf"

    class ImpresoraPdf(QPrinter):
        def __init__(self, modo):
            super().__init__(modo)
            self.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
            self.setOutputFileName(str(salida_pdf))

    class Dialogo:
        DialogCode = QPrintDialog.DialogCode

        def __init__(self, *a):
            pass

        def setWindowTitle(self, _t):  # noqa: N802
            pass

        def exec(self):
            return QPrintDialog.DialogCode.Accepted

    monkeypatch.setattr(impresion, "QPrinter", ImpresoraPdf)
    monkeypatch.setattr(impresion, "QPrintDialog", Dialogo)
    ahora = datetime(2026, 10, 12, 12, 0)
    partes = [DatosParte(a, None, ahora, ahora, contexto.firmante.contenido_qr(a.id, ahora, ahora))
              for a in contexto.alumnos[:3]]
    assert impresion.imprimir_varios(partes, contexto)
    crudo = salida_pdf.read_bytes()
    assert crudo.count(b"/Type /Page\n") + crudo.count(b"/Type /Page ") + crudo.count(b"/Type /Page>") == 3


def test_el_parte_para_el_correo_lleva_png_y_pdf(qtbot, contexto):
    from partes_salida.impresion import parte_adjunto
    from partes_salida.parte import DatosParte

    a = contexto.alumnos[0]
    ahora = datetime(2026, 10, 12, 12, 0)
    adj = parte_adjunto(DatosParte(a, contexto.foto(a.id), ahora, ahora,
                                   contexto.firmante.contenido_qr(a.id, ahora, ahora)), contexto)
    assert adj.png.startswith(b"\x89PNG") and adj.pdf.startswith(b"%PDF")
    assert a.nombre_listado in adj.nombre and "2026-10-12 12.00" in adj.nombre
