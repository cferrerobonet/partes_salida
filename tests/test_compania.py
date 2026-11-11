"""ESO y Grado Básico: si el alumno sale solo o acompañado (QR firmado, parte, correo e historial)."""

from datetime import date, datetime

import pytest

from partes_salida.ajustes import GestorAjustes
from partes_salida.correo import texto_html, texto_plano
from partes_salida.firma import Firmante, verificar
from partes_salida.modelo import Alumno, codigo_compania, sale_solo
from partes_salida.seguimiento import Salida, autorizacion_vigente, fin_de_curso

SALIDA, EXPEDIDO = datetime(2026, 10, 8, 12, 30), datetime(2026, 10, 8, 9, 14)


def alumno(clase: str, sexo: str = "M") -> Alumno:
    return Alumno(id="1", nia="10633407", nombre="PAU", apellido1="CASTELLÓ", sexo=sexo, clase=clase)


@pytest.mark.parametrize(
    ("clase", "sexo", "solo", "codigo"),
    [
        ("4ESOB", "M", True, "SO"),
        ("4ESOB", "F", True, "SA"),
        ("4ESOB", "M", False, "AO"),
        ("2CFB-EE", "F", False, "AA"),
        ("2CFB-EE", "M", True, "SO"),
        ("2BACC", "F", True, "-"),  # Bachillerato no lo lleva
        ("1CFM-IEA-A", "M", True, "-"),
        ("4ESOB", "M", None, "-"),
    ],
)
def test_codigo_de_compania_por_etapa_y_sexo(clase, sexo, solo, codigo):
    assert codigo_compania(alumno(clase, sexo), solo) == codigo


@pytest.mark.parametrize("compania", ["SO", "SA", "AO", "AA", "-"])
def test_la_compania_va_firmada_en_el_qr(compania):
    f = Firmante.del_llavero()
    qr = f.contenido_qr("10633407", SALIDA, EXPEDIDO, compania)
    assert qr.startswith(f"PS2|{f.id_clave}|10633407|202610081230|202610080914|{compania}|")
    v = verificar(qr, {f.id_clave: f.publica})
    assert v.valido and v.compania == compania


def test_cambiar_la_compania_a_mano_invalida_el_parte():
    f = Firmante.del_llavero()
    qr = f.contenido_qr("10633407", SALIDA, EXPEDIDO, "AO")
    assert not verificar(qr.replace("|AO|", "|SO|"), {f.id_clave: f.publica}).valido


def test_compania_desconocida_no_se_firma():
    with pytest.raises(ValueError):
        Firmante.del_llavero().contenido_qr("1", SALIDA, EXPEDIDO, "XX")


def test_el_qr_con_compania_cabe_en_la_version_8():
    """El QR va a 20 mm: más módulos lo harían ilegible para el móvil del vigilante."""
    import segno

    qr = Firmante.del_llavero().contenido_qr("10633407", SALIDA, EXPEDIDO, "SA")
    assert segno.make(qr, error="m", micro=False, boost_error=False).version <= 8


def test_fin_de_curso_y_caducidad_de_la_autorizacion():
    assert fin_de_curso(date(2026, 11, 11)) == date(2027, 8, 31)
    assert fin_de_curso(date(2027, 3, 1)) == date(2027, 8, 31)
    assert fin_de_curso(date(2027, 9, 1)) == date(2028, 8, 31)
    assert autorizacion_vigente("2026-11-11", date(2027, 8, 31))
    assert not autorizacion_vigente("2026-11-11", date(2027, 9, 1))
    assert not autorizacion_vigente("no es fecha", date(2026, 11, 11))


def test_autorizacion_se_guarda_cifrada_y_caduca(datos):
    from partes_salida.almacen import Almacen
    from partes_salida.cifrado import Cifrador
    from partes_salida.seguimiento import Seguimiento

    almacen = Almacen(datos, Cifrador.del_llavero())
    seg = Seguimiento(almacen)
    seg.poner_autorizacion("a", True, hoy=date(2026, 11, 11))
    seg.poner_autorizacion("viejo", True, hoy=date(2024, 10, 1))
    assert seg.autorizado("a", date(2027, 6, 1)) and not seg.autorizado("a", date(2027, 9, 2))
    otra = Seguimiento(almacen)
    assert otra.autorizado("a") and "viejo" not in otra.autorizados, "la de un curso pasado se descarta al cargar"
    otra.poner_autorizacion("a", False)
    assert not Seguimiento(almacen).autorizado("a")


def test_la_autorizacion_se_va_con_el_alumno(datos):
    from partes_salida.almacen import Almacen
    from partes_salida.cifrado import Cifrador
    from partes_salida.seguimiento import Seguimiento

    seg = Seguimiento(Almacen(datos, Cifrador.del_llavero()))
    seg.poner_autorizacion("a", True)
    seg.poner_autorizacion("b", True)
    seg.conservar_solo(["b"])
    assert set(seg.autorizados) == {"b"}
    seg.olvidar_todo()
    assert seg.autorizados == {}


def test_historial_dice_si_salio_solo():
    assert Salida.nueva(SALIDA, "papel", [], compania="SA").como == "Impreso · sale sola"
    assert Salida.nueva(SALIDA, "papel", [], compania="AO").como == "Impreso"
    assert Salida(**{k: v for k, v in Salida.nueva(SALIDA, "papel", []).__dict__.items() if k != "compania"}).compania == "-"
    assert sale_solo("SO") and not sale_solo("AA") and not sale_solo("-")


@pytest.mark.parametrize(("compania", "linea"), [("SA", "Sale: Sola"), ("AO", "Sale: Acompañado"), ("-", None)])
def test_el_correo_dice_si_sale_solo(datos, compania, linea):
    g = GestorAjustes(datos)
    a = alumno("4ESOB", "F" if compania == "SA" else "M")
    texto = texto_plano(g.valores, a, SALIDA, compania=compania)
    html = texto_html(g.valores, a, SALIDA, None, None, compania=compania)
    if linea:
        assert linea in texto and linea.split(": ")[1] in html
    else:
        assert "Sale:" not in texto and ">Sale<" not in html


@pytest.mark.parametrize("orientacion", ["horizontal", "vertical"])
def test_el_parte_lleva_la_etiqueta_sale_solo(qapp, datos, orientacion):
    from partes_salida.parte import DatosParte, ImagenesParte, imagen_parte, maqueta
    from partes_salida.ui import estilo

    estilo.cargar_fuentes()
    g = GestorAjustes(datos)
    g.poner(orientacion=orientacion)
    m = maqueta(orientacion)
    a = alumno("4ESOB", "F")

    def oscuros(compania: str) -> float:
        img = imagen_parte(DatosParte(a, None, SALIDA, EXPEDIDO, "PS2|X", compania), g, ImagenesParte(g), 1480)
        escala = img.width() / m.ancho
        x, y, w, h = (v * escala for v in m.solo)
        puntos = [(int(x + i * w / 20), int(y + j * h / 6)) for i in range(1, 20) for j in range(1, 6)]
        return sum(img.pixelColor(px, py).lightness() < 100 for px, py in puntos) / len(puntos)

    assert oscuros("SA") > 0.5, "sale sola: etiqueta en negativo"
    assert oscuros("AA") < 0.05 and oscuros("-") < 0.05, "acompañada o sin compañía: nada en ese hueco"


# Interfaz ------------------------------------------------------------------------------------------


@pytest.fixture
def ventana(qtbot, contexto, monkeypatch):
    from partes_salida.ui.ventana import VentanaPrincipal

    impresos: list = []
    monkeypatch.setattr("partes_salida.ui.ventana.imprimir_varios",
                        lambda partes, ctx, padre: impresos.extend(partes) or True)
    monkeypatch.setattr("partes_salida.ui.envios.contrasena_smtp", lambda a: "clave")
    monkeypatch.setattr("partes_salida.ui.envios.enviar", lambda msg, a, c: None)
    v = VentanaPrincipal(contexto)
    v.impresos = impresos
    qtbot.addWidget(v)
    v.show()
    return v


def elegir(qtbot, v, texto):
    v.buscador.setText(texto)
    v.actualizar_lista()
    qtbot.wait(10)
    return v.ficha.alumno


@pytest.mark.ui
def test_selector_solo_en_eso_y_grado_basico(qtbot, ventana):
    from PyQt6.QtCore import Qt

    elegir(qtbot, ventana, "beltran")  # Bachillerato
    assert ventana.caja_compania.isHidden() and ventana.ficha.boton_solo.isHidden()
    assert ventana.solo() is None
    elegir(qtbot, ventana, "castello")  # ESO
    assert not ventana.caja_compania.isHidden() and not ventana.ficha.boton_solo.isHidden()
    marta = elegir(qtbot, ventana, "ibanez")  # 3º ESO, alumna
    assert ventana.compania_acompanado.isChecked(), "de serie, acompañada"
    assert (ventana.compania_acompanado.text(), ventana.compania_solo.text()) == ("Acompañada", "Sola")
    assert ventana.aviso_compania.isHidden()
    qtbot.mouseClick(ventana.compania_solo, Qt.MouseButton.LeftButton)
    assert not ventana.aviso_compania.isHidden(), "sola sin autorización: avisa"
    assert ventana.resumen.text().startswith("Sale sola del centro.")
    ventana.imprimir()
    assert ventana.impresos[-1].compania == "SA" and "|SA|" in ventana.impresos[-1].qr
    assert ventana.ctx.seguimiento.salidas(marta.id)[0].compania == "SA"


@pytest.mark.ui
def test_grado_basico_sale_solo_de_serie_sin_autorizacion(qtbot, ventana, contexto):
    """CarlosFB, 2026-11-11: en Grado Básico lo normal es salir solo; acompañado es la excepción."""
    from PyQt6.QtCore import Qt

    jordi = elegir(qtbot, ventana, "esteve")  # 2º Grado Básico
    assert not ventana.caja_compania.isHidden()
    assert ventana.compania_solo.isChecked(), "de serie, solo"
    assert ventana.aviso_compania.isHidden(), "sin aviso de autorización"
    assert ventana.ficha.boton_solo.isHidden() and ventana.ficha.seg_titulos[2].isHidden(), "sin fila «Salir solo»"
    ventana.cambiar_autorizacion()
    assert not contexto.seguimiento.autorizado(jordi.id), "en Grado Básico no se marca autorización"
    ventana.imprimir()
    assert ventana.impresos[-1].compania == "SO"
    qtbot.mouseClick(ventana.compania_acompanado, Qt.MouseButton.LeftButton)  # hoy vienen a por él
    assert ventana.aviso_compania.isHidden()
    ventana.imprimir()
    assert ventana.impresos[-1].compania == "AO"


@pytest.mark.ui
def test_la_autorizacion_se_recuerda_y_se_puede_cambiar_ese_dia(qtbot, ventana, contexto):
    from PyQt6.QtCore import Qt

    pau = elegir(qtbot, ventana, "castello")  # 4º ESO
    assert ventana.ficha.seg_solo.text() == "Sin autorización de la familia"
    qtbot.mouseClick(ventana.ficha.boton_solo, Qt.MouseButton.LeftButton)
    assert contexto.seguimiento.autorizado(pau.id)
    assert ventana.ficha.seg_solo.text().startswith("Autorizado por la familia hasta el 31/08/")
    assert ventana.compania_solo.isChecked() and ventana.aviso_compania.isHidden()
    elegir(qtbot, ventana, "peris")
    assert ventana.compania_acompanado.isChecked(), "otro alumno sin autorización: acompañada"
    elegir(qtbot, ventana, "castello")
    assert ventana.compania_solo.isChecked(), "vuelve a salir solo sin marcarlo"
    qtbot.mouseClick(ventana.compania_acompanado, Qt.MouseButton.LeftButton)  # hoy vienen a por él
    ventana.imprimir()
    assert ventana.impresos[-1].compania == "AO"
    assert contexto.seguimiento.autorizado(pau.id), "cambiar un parte no quita la autorización"


@pytest.mark.ui
def test_autorizar_desde_el_aviso_del_selector(qtbot, ventana, contexto):
    from PyQt6.QtCore import Qt

    laia = elegir(qtbot, ventana, "peris")
    qtbot.mouseClick(ventana.compania_solo, Qt.MouseButton.LeftButton)
    qtbot.mouseClick(ventana.boton_autorizar, Qt.MouseButton.LeftButton)
    assert contexto.seguimiento.autorizado(laia.id) and ventana.aviso_compania.isHidden()
    assert ventana.compania_solo.isChecked()


@pytest.mark.ui
def test_los_recurrentes_siguen_la_autorizacion(qtbot, ventana, contexto):
    from partes_salida.seguimiento import Recurrencia
    from partes_salida.ui.seguimiento import DialogoRecurrentes

    por = {a.nombre: a for a in contexto.alumnos}
    seg = contexto.seguimiento
    for nombre in ("PAU", "LAIA", "NEREA", "JORDI"):
        seg.poner_recurrencia(por[nombre].id, Recurrencia({0: "12:30"}))
    seg.poner_autorizacion(por["PAU"].id, True)
    seg.poner_autorizacion(por["NEREA"].id, True)  # Bachillerato: no aplica
    d = DialogoRecurrentes(contexto, ventana, hoy=date(2026, 10, 12))
    qtbot.addWidget(d)
    d._emitir()
    assert {p.alumno.nombre: p.compania for p in ventana.impresos} == {
        "PAU": "SO", "LAIA": "AA", "NEREA": "-", "JORDI": "SO"}  # Jordi: Grado Básico, solo de serie
