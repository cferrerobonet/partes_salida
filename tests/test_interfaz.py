"""La app de punta a punta con pytest-qt: buscar, elegir, avisar e imprimir."""

import pytest
from PyQt6.QtCore import Qt, QTime

pytestmark = pytest.mark.ui


@pytest.fixture
def ventana(qtbot, contexto):
    from partes_salida.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal(contexto)
    qtbot.addWidget(v)
    v.show()
    return v


def buscar(qtbot, v, texto):
    v.buscador.setText(texto)
    v.actualizar_lista()
    qtbot.wait(10)


def test_arranca_con_recuento_y_etapas(ventana, contexto):
    assert "13 alumnos" in ventana.recuento.text()
    textos = [b.text() for b in ventana.grupo_etapas.buttons()]
    assert textos[0] == "Todas" and "G. Superior" in textos and "Infantil" in textos


def test_buscar_elige_al_primero_y_muestra_ficha(qtbot, ventana):
    buscar(qtbot, ventana, "beltran")
    assert ventana.modelo.rowCount() == 1
    assert ventana.ficha.alumno.nombre == "NEREA"
    assert "NEREA" in ventana.ficha.nombre.text()
    assert ventana.boton_imprimir.isEnabled()
    assert "madre y padre" in ventana.resumen.text()


def test_mayor_de_edad_sale_sin_aviso(qtbot, ventana):
    buscar(qtbot, ventana, "gimeno")
    assert ventana.ficha.alumno.edad() >= 18
    assert ventana.ficha.destinatarios() == []
    assert ventana.resumen.text() == "Sin aviso por correo"


def test_familiar_que_no_recibe_informacion_no_se_puede_marcar(qtbot, ventana):
    buscar(qtbot, ventana, "castello")
    assert [t.parentesco_texto for t in ventana.ficha.destinatarios()] == ["Madre"]


def test_filtrar_por_etapa_y_limpiar(qtbot, ventana):
    boton = next(b for b in ventana.grupo_etapas.buttons() if b.text() == "G. Superior")
    qtbot.mouseClick(boton, Qt.MouseButton.LeftButton)
    assert {a.etapa_codigo for a in ventana.modelo.alumnos} == {"CFS"}
    ventana.limpiar_filtros()
    assert ventana.modelo.rowCount() == 13


def test_parte_preparado_para_otro_dia(qtbot, ventana, monkeypatch):
    from datetime import date, timedelta

    from PyQt6.QtCore import QDate

    impresos = []
    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios",
                        lambda partes, ctx, padre: impresos.extend(partes) or True)
    buscar(qtbot, ventana, "gimeno")
    hoy = date.today()
    assert ventana.fecha.date().toPyDate() == hoy and ventana.fecha.minimumDate().toPyDate() == hoy
    ventana.fecha.setDate(QDate(hoy - timedelta(days=1)))
    assert ventana.fecha.date().toPyDate() == hoy  # un día pasado no se puede elegir
    manana = hoy + timedelta(days=1)
    ventana.fecha.setDate(QDate(manana))
    ventana.hora.setTime(QTime(8, 15))
    assert "otro día" in ventana.aviso_hora.text()
    ventana.imprimir()
    assert impresos[0].salida.date() == manana and impresos[0].salida.strftime("%H:%M") == "08:15"
    ventana._ahora()
    assert ventana.fecha.date().toPyDate() == hoy and ventana.aviso_hora.text() == ""


def test_a_medianoche_la_fecha_de_hoy_pasa_al_dia_nuevo(ventana, monkeypatch):
    from datetime import date, timedelta

    from PyQt6.QtCore import QDate

    hoy = date.today()

    class Manana(date):
        @classmethod
        def today(cls):
            return hoy + timedelta(days=1)

    monkeypatch.setattr("partes_salida.ui.ventana.date", Manana)
    ventana._comprobar_dia()
    assert ventana.fecha.date().toPyDate() == hoy + timedelta(days=1)
    ventana.fecha.setDate(QDate(hoy + timedelta(days=5)))
    ventana._hoy = hoy
    ventana._comprobar_dia()
    assert ventana.fecha.date().toPyDate() == hoy + timedelta(days=5)  # la de un día futuro se queda


def test_imprimir_firma_el_qr_y_avisa(qtbot, ventana, monkeypatch, contexto):
    from partes_salida.firma import verificar

    impresos, enviados = [], []
    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios",
                        lambda partes, ctx, padre: impresos.extend(partes) or True)
    monkeypatch.setattr("partes_salida.ui.envios.contrasena_smtp", lambda a: "clave")
    monkeypatch.setattr("partes_salida.ui.envios.enviar", lambda msg, a, c: enviados.append(msg))
    buscar(qtbot, ventana, "nerea")
    ventana.hora.setTime(QTime(12, 30))
    ventana.imprimir()
    qtbot.waitUntil(lambda: bool(enviados), timeout=3000)
    datos = impresos[0]
    assert datos.salida.strftime("%H:%M") == "12:30"
    assert verificar(datos.qr, {contexto.firmante.id_clave: contexto.firmante.publica}).valido
    assert enviados[0]["To"] == "amparo.roig@ejemplo.es, vicent.beltran@ejemplo.es"


def test_el_envio_responde_a_jefatura_y_guarda_su_identificador(qtbot, ventana, monkeypatch, contexto):
    """Con el Message-ID guardado se reconocen después sus rebotes y las respuestas de la familia."""
    enviados = []
    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios", lambda *a: True)
    monkeypatch.setattr("partes_salida.ui.envios.contrasena_smtp", lambda a: "clave")
    monkeypatch.setattr("partes_salida.ui.envios.enviar", lambda msg, a, c: enviados.append(msg))
    buscar(qtbot, ventana, "nerea")
    ventana.imprimir()
    nerea = ventana.ficha.alumno
    qtbot.waitUntil(lambda: contexto.seguimiento.salidas(nerea.id)[0].correo == "enviado", timeout=3000)
    assert enviados[0]["Reply-To"] == "jefaturafpbach@epla.es"  # Bachillerato: la de mañana
    assert contexto.seguimiento.salidas(nerea.id)[0].mensajes == [enviados[0]["Message-ID"]]


def test_un_rebote_marca_el_historial_y_pide_llamar(qtbot, ventana, monkeypatch, contexto):
    from datetime import datetime

    from partes_salida.seguimiento import PAPEL, Salida
    from partes_salida.vuelta import Resultado

    avisos = []
    monkeypatch.setattr("partes_salida.ui.vuelta.QMessageBox.warning", lambda *a: avisos.append(a[2]))
    nerea = next(a for a in contexto.alumnos if a.nombre == "NEREA")
    madre = nerea.tutores[0]
    s = contexto.seguimiento.registrar(nerea.id, Salida.nueva(datetime(2026, 11, 6, 12, 30), PAPEL, ["madre"]))
    ventana.vuelta._terminado(Resultado(rebotes=[(nerea.id, s.id, [madre.email.lower()])]))
    assert contexto.seguimiento.salidas(nerea.id)[0].correo_texto == "Rebotado"
    assert "NEREA" in avisos[0] and madre.email.lower() in avisos[0] and f"Llamar: {madre.telefono}" in avisos[0]


def test_sin_servidor_imap_no_se_revisa_el_buzon(ventana, contexto):
    contexto.gestor.poner(smtp_servidor="smtp.ejemplo.es", smtp_usuario="partes@ejemplo.es", imap_servidor="")
    ventana.vuelta.revisar()
    assert ventana.vuelta._tarea is None


def test_sin_contrasena_avisa_y_no_envia(qtbot, ventana, monkeypatch):
    avisos = []
    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios", lambda *a: True)
    monkeypatch.setattr("partes_salida.ui.envios.contrasena_smtp", lambda a: None)
    monkeypatch.setattr("partes_salida.ui.envios.QMessageBox.warning", lambda *a: avisos.append(a[2]))
    buscar(qtbot, ventana, "nerea")
    ventana.imprimir()
    assert avisos and "contraseña" in avisos[0]


def test_vista_previa_se_pinta(qtbot, ventana):
    buscar(qtbot, ventana, "nerea")
    ventana.vista._pintar()
    assert not ventana.vista.pixmap().isNull()


def test_cerrar_oculta_en_vez_de_salir(qtbot, ventana):
    ventana.close()
    assert not ventana.isVisible()
    ventana.mostrar_al_frente()
    assert ventana.isVisible()


def test_ajustes_abre_todos_los_apartados(qtbot, contexto):
    from partes_salida.ui.ajustes import APARTADOS, DialogoAjustes

    d = DialogoAjustes(contexto, None, "Correo")
    qtbot.addWidget(d)
    assert d.pila.currentIndex() == APARTADOS.index("Correo")
    for i in range(len(APARTADOS)):
        d.nav.setCurrentRow(i)
        assert d.pila.currentIndex() == i


def test_ocultar_etapa_desde_ajustes(qtbot, contexto, ventana):
    contexto.gestor.poner(etapas_ocultas=["INF", "PRI"])
    contexto.ajustes_cambiados.emit()
    assert all(a.etapa_codigo not in ("INF", "PRI") for a in ventana.modelo.alumnos)
    assert "Infantil" not in [b.text() for b in ventana.grupo_etapas.buttons()]


def test_sin_datos_invita_a_importar(qtbot, datos, qapp):
    from partes_salida.contexto import Contexto
    from partes_salida.ui.ventana import VentanaPrincipal

    v = VentanaPrincipal(Contexto(datos))
    qtbot.addWidget(v)
    assert v.ficha.pila.currentIndex() == 0 and not v.boton_imprimir.isEnabled()
    assert "importando" in v.ficha.vacio_titulo.text()


def test_version_nueva_se_ve_y_se_ofrece_una_vez(qtbot, ventana, monkeypatch):
    ofrecidas = []
    monkeypatch.setattr("partes_salida.ui.dialogos.ofrecer", lambda padre, v, u, n: ofrecidas.append(v))
    assert ventana.boton_actualizar.isHidden()
    ventana.actualizacion_disponible("9.0.0", "https://github.com/x.dmg", "Novedades")
    assert not ventana.boton_actualizar.isHidden() and "9.0.0" in ventana.boton_actualizar.text()
    ventana.actualizacion_disponible("9.0.0", "https://github.com/x.dmg", "Novedades")
    assert ofrecidas == ["9.0.0"], "la comprobación periódica no repite el diálogo de la misma versión"
    qtbot.mouseClick(ventana.boton_actualizar, Qt.MouseButton.LeftButton)
    assert ofrecidas == ["9.0.0", "9.0.0"], "el botón dorado vuelve a abrirlo"


def test_dialogo_de_actualizacion_destaca_actualizar(qtbot):
    from PyQt6.QtWidgets import QPushButton

    from partes_salida.ui.dialogos import DialogoActualizacion

    d = DialogoActualizacion("9.0.0", "## Novedades\n- Algo nuevo", None)
    qtbot.addWidget(d)
    principal = [b for b in d.findChildren(QPushButton) if b.property("primario")]
    assert [b.text() for b in principal] == ["Actualizar ahora"]


def test_presentacion_cuenta_la_carga_y_acerca_de_se_cierra(qtbot, datos):
    from partes_salida.contexto import Contexto
    from partes_salida.ui.presentacion import Presentacion

    p = Presentacion()
    qtbot.addWidget(p)
    pasos = []
    Contexto(datos, avance=lambda t, v: (pasos.append(t), p.paso(t, v)))
    assert "Descifrando los datos del alumnado…" in pasos
    assert p._texto == pasos[-1]
    a = Presentacion(acerca_de=True)
    qtbot.addWidget(a)
    a.show()
    qtbot.mouseClick(a, Qt.MouseButton.LeftButton)
    assert not a.isVisible()


def test_ayudas_de_importacion_junto_a_cada_zona(qtbot, contexto, monkeypatch):
    from partes_salida.ui.ajustes import DialogoAjustes
    from partes_salida.ui.ayuda import AYUDA_EXCEL, AYUDA_FOTOS, DialogoAyuda

    abiertas = []
    monkeypatch.setattr(DialogoAyuda, "exec", lambda self: abiertas.append(self.windowTitle()) or 1)
    d = DialogoAjustes(contexto, None, "Datos del alumnado")
    qtbot.addWidget(d)
    assert not d.zona_excel.ayuda.isHidden() and not d.zona_fotos.ayuda.isHidden()
    qtbot.mouseClick(d.zona_excel.ayuda, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(d.zona_fotos.ayuda, Qt.MouseButton.LeftButton)
    assert len(abiertas) == 2
    assert any("Import/Export" in p for p in AYUDA_EXCEL.pasos)
    assert any("APELLIDOS, NOMBRE" in p for p in AYUDA_FOTOS.pasos)
    for ayuda in (AYUDA_EXCEL, AYUDA_FOTOS):
        qtbot.addWidget(DialogoAyuda(ayuda))


def test_enviar_a_la_papelera(tmp_path):
    from partes_salida.ui.ajustes import enviar_a_papelera

    archivo = tmp_path / "x.txt"
    archivo.write_text("x")
    if enviar_a_papelera(str(archivo)):
        assert not archivo.exists()


def test_reimportar_excel_sustituye_y_conserva_fotos_de_quien_sigue(contexto, alumnos):
    nerea = next(a for a in alumnos if a.nombre == "NEREA")
    marc = next(a for a in alumnos if a.nombre == "MARC")
    assert contexto.almacen.tiene_foto(nerea.id) and contexto.almacen.tiene_foto(marc.id)
    borradas = contexto.nuevo_padron([nerea], "nuevo.xlsx")
    assert [a.id for a in contexto.alumnos] == [nerea.id]
    assert borradas >= 1 and contexto.almacen.tiene_foto(nerea.id) and not contexto.almacen.tiene_foto(marc.id)


def test_reimportar_fotos_sustituye_y_anade(contexto, tmp_path):
    import zipfile

    from partes_salida.importar_fotos import importar_fotos
    from tests import ficticios

    nerea = next(a for a in contexto.alumnos if a.nombre == "NEREA")
    antes = contexto.almacen.leer_foto(nerea.id)
    ruta = tmp_path / "nuevas.zip"
    with zipfile.ZipFile(ruta, "w") as z:
        z.writestr("otra/carpeta/BELTRÁN ROIG, NEREA.jpg", ficticios.retrato(3))
        z.writestr("QUILES ROMERO, LUCÍA.png", ficticios.retrato(4))
    inf = importar_fotos([ruta], contexto.alumnos, contexto.almacen)
    assert inf.asignadas == 2
    assert contexto.almacen.leer_foto(nerea.id) != antes
    lucia = next(a for a in contexto.alumnos if a.nombre == "LUCÍA")
    assert contexto.almacen.tiene_foto(lucia.id)


def test_ayuda_del_excel_lleva_las_capturas_de_educamos():
    from partes_salida.rutas import recursos
    from partes_salida.ui.ayuda import AYUDA_EXCEL

    assert any("Exportación de datos de los alumnos" in p for p in AYUDA_EXCEL.pasos)
    for nombre, _ancho in AYUDA_EXCEL.imagenes.values():
        assert (recursos() / nombre).exists() and nombre.isascii()


def test_patria_potestad_exclusiva_bloquea_al_otro_familiar(qtbot, ventana, contexto, monkeypatch):
    from PyQt6.QtWidgets import QCheckBox, QMessageBox

    from partes_salida.contexto import Contexto

    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.StandardButton.Yes)
    buscar(qtbot, ventana, "beltran")
    a = ventana.ficha.alumno
    marcas = [c for c in ventana.ficha.findChildren(QCheckBox) if c.text() == "Patria potestad exclusiva"]
    assert len(marcas) == 2
    marcas[0].setChecked(True)  # la madre
    qtbot.wait(20)
    assert [t.parentesco_texto for t in ventana.ficha.destinatarios()] == ["Madre"]
    assert ventana.resumen.text() == "Se avisará por correo a: madre"
    rotulos = [c.text() for c in ventana.ficha.findChildren(QCheckBox) if c.isVisible()]
    assert "Sin patria potestad: no recibe avisos" in rotulos
    # Vale también para los recurrentes (usan `puede_recibir_correo`), tras reimportar y al reabrir
    contexto.nuevo_padron(list(contexto.alumnos), "alumnos.xlsx")
    assert [t.puede_recibir_correo for t in contexto.por_id[a.id].tutores] == [True, False]
    otro = Contexto(contexto.carpeta)
    assert [t.puede_recibir_correo for t in otro.por_id[a.id].tutores] == [True, False]
    # Se quita desmarcando: los dos vuelven a recibir avisos
    buscar(qtbot, ventana, "beltran")
    next(c for c in ventana.ficha.findChildren(QCheckBox) if c.text() == "Patria potestad exclusiva"
         and c.isChecked()).setChecked(False)
    qtbot.wait(20)
    assert "madre y padre" in ventana.resumen.text()


def test_patria_potestad_que_ya_no_coincide_no_avisa_a_nadie(qtbot, ventana, contexto):
    buscar(qtbot, ventana, "beltran")
    a = ventana.ficha.alumno
    contexto.poner_patria_potestad(a, "OTRA PERSONA")
    ventana.ficha.mostrar(a)
    assert ventana.ficha.destinatarios() == []
    assert "ya no coincide" in "".join(lbl.text() for lbl in ventana.ficha.findChildren(type(ventana.resumen)))


def test_laterales_mas_anchas_sin_quitar_sitio_a_la_ficha(ventana):
    """Como Programaciones (CarlosFB, 2026-11-11): con pantalla de sobra, las dos laterales crecen hasta 360 y
    400 px y la ficha conserva 1040; en una pantalla pequeña se quedan en 300 y 340."""
    assert ventana.anchos_laterales(1366) == (300, 340)
    assert ventana.anchos_laterales(1700) == (310, 350)
    assert ventana.anchos_laterales(1800) == (360, 400)
    assert ventana.anchos_laterales(2560) == (360, 400)
    ventana.resize(1800, 900)
    assert (ventana.col_buscar.width(), ventana.col_imprimir.width()) == ventana.anchos_laterales(ventana.width())


def test_se_abre_a_pantalla_completa_y_cerrar_la_oculta(qtbot, ventana):
    ventana.hide()
    ventana.mostrar_al_frente()
    assert ventana.isFullScreen()
    assert ventana.boton_cerrar.property("salir") is True
    qtbot.mouseClick(ventana.boton_cerrar, Qt.MouseButton.LeftButton)
    assert not ventana.isVisible(), "se oculta: la app sigue en la barra"
