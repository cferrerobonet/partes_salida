"""Historial de salidas, partes recurrentes y correo del alumno (dominio, sin pantalla)."""

from datetime import date, datetime

import pytest

from partes_salida.almacen import Almacen, DatosIlegibles
from partes_salida.cifrado import Cifrador
from partes_salida.seguimiento import CORREO, PAPEL, Recurrencia, Salida, Seguimiento, informe_html

LUNES = date(2026, 10, 12)


def por_nombre(alumnos, nombre):
    return next(a for a in alumnos if a.nombre == nombre)


@pytest.fixture
def seguimiento(datos):
    return Seguimiento(Almacen(datos, Cifrador.del_llavero()))


def salida(hora="12:30", dia=LUNES, **kw):
    return Salida.nueva(datetime.combine(dia, datetime.strptime(hora, "%H:%M").time()), kw.pop("entrega", PAPEL),
                        kw.pop("avisados", []), **kw)


def test_importa_el_correo_del_alumno_y_si_falta_el_de_google(alumnos):
    assert por_nombre(alumnos, "MARC").email == "marc.albert@ejemplo.es"
    assert por_nombre(alumnos, "HUGO").email == "hugo.gimeno@ejemplo.es"
    assert por_nombre(alumnos, "IVÁN").email == ""


def test_historial_y_recurrentes_cifrados_y_persistentes(datos, seguimiento, alumnos):
    marc = por_nombre(alumnos, "MARC")
    seguimiento.registrar(marc.id, salida(avisados=["madre"]))
    seguimiento.poner_recurrencia(marc.id, Recurrencia({0: "12:30"}, motivo="Conservatorio"))
    crudo = (datos / "seguimiento.bin").read_bytes()
    assert b"Conservatorio" not in crudo and b"madre" not in crudo and marc.id.encode() not in crudo
    otra = Seguimiento(Almacen(datos, Cifrador.del_llavero()))
    assert otra.salidas(marc.id)[0].avisados == ["madre"]
    assert otra.recurrentes[marc.id].hora(0).strftime("%H:%M") == "12:30"
    with pytest.raises(DatosIlegibles):
        Seguimiento(Almacen(datos, Cifrador(b"\1" * 32)))


def test_reimportar_el_excel_conserva_lo_de_quien_sigue_y_borra_lo_de_las_bajas(contexto):
    sigue, baja = contexto.alumnos[0], contexto.alumnos[1]
    for a in (sigue, baja):
        contexto.seguimiento.registrar(a.id, salida())
        contexto.seguimiento.poner_recurrencia(a.id, Recurrencia({1: "10:00"}))
    contexto.nuevo_padron([a for a in contexto.alumnos if a.id != baja.id], "nuevo.xlsx")
    assert len(contexto.seguimiento.salidas(sigue.id)) == 1 and sigue.id in contexto.seguimiento.recurrentes
    assert contexto.seguimiento.salidas(baja.id) == [] and baja.id not in contexto.seguimiento.recurrentes


def test_importar_fotos_no_toca_el_historial(contexto, zip_fotos):
    from partes_salida.importar_fotos import importar_fotos

    a = contexto.alumnos[0]
    contexto.seguimiento.registrar(a.id, salida())
    importar_fotos([zip_fotos], contexto.alumnos, contexto.almacen)
    contexto.fotos_cambiadas()
    assert len(contexto.seguimiento.salidas(a.id)) == 1


def test_vaciar_todos_los_datos_borra_historial_y_recurrentes(contexto, datos):
    a = contexto.alumnos[0]
    contexto.seguimiento.registrar(a.id, salida())
    contexto.seguimiento.poner_recurrencia(a.id, Recurrencia({0: "12:30"}))
    contexto.borrar_datos()
    assert not (datos / "seguimiento.bin").exists()
    assert contexto.seguimiento.total_salidas == 0 and not contexto.seguimiento.recurrentes


def test_vaciar_historial_de_uno_y_de_todos_conserva_los_recurrentes(seguimiento):
    seguimiento.registrar("1", salida())
    seguimiento.registrar("1", salida("13:00"))
    seguimiento.registrar("2", salida())
    seguimiento.poner_recurrencia("1", Recurrencia({0: "12:30"}))
    assert seguimiento.vaciar_historial("1") == 2
    assert seguimiento.total_salidas == 1
    assert seguimiento.vaciar_historial() == 1
    assert seguimiento.total_salidas == 0 and "1" in seguimiento.recurrentes


def test_las_salidas_salen_de_la_mas_reciente_a_la_mas_antigua(seguimiento):
    seguimiento.registrar("1", salida("09:00", expedido=datetime(2026, 10, 12, 8, 50)))
    seguimiento.registrar("1", salida("13:00", expedido=datetime(2026, 10, 12, 12, 55)))
    assert [s.momento_salida.hour for s in seguimiento.salidas("1")] == [13, 9]


def test_un_correo_a_medias_al_cerrar_queda_sin_confirmar(datos, seguimiento):
    seguimiento.registrar("1", salida(avisados=["madre"]))
    assert seguimiento.salidas("1")[0].correo == "enviando"
    otra = Seguimiento(Almacen(datos, Cifrador.del_llavero()))
    assert otra.salidas("1")[0].correo_texto == "Sin confirmar"


def test_partes_del_dia_solo_de_las_etapas_visibles_y_por_hora(contexto):
    marc, nerea, pau = (por_nombre(contexto.alumnos, n) for n in ("MARC", "NEREA", "PAU"))  # CFS, BAC, ESO
    seg = contexto.seguimiento
    seg.poner_recurrencia(marc.id, Recurrencia({0: "12:30", 2: "12:30"}))
    seg.poner_recurrencia(pau.id, Recurrencia({0: "10:00"}))
    seg.poner_recurrencia(nerea.id, Recurrencia({1: "11:00"}))
    lunes = seg.partes_del_dia(LUNES, contexto.por_id, None)
    assert [(p.alumno.nombre, f"{p.salida:%H:%M}") for p in lunes] == [("PAU", "10:00"), ("MARC", "12:30")]
    assert [p.alumno.nombre for p in seg.partes_del_dia(LUNES, contexto.por_id, {"CFS"})] == ["MARC"]
    assert seg.partes_del_dia(date(2026, 10, 17), contexto.por_id, None) == []  # sábado
    seg.registrar(marc.id, Salida.nueva(datetime(2026, 10, 12, 12, 30), PAPEL, [], recurrente=True))
    marc_hoy = next(p for p in seg.partes_del_dia(LUNES, contexto.por_id, None) if p.alumno.id == marc.id)
    assert marc_hoy.emitido is not None
    assert seg.emitido_hoy(marc.id, date(2026, 10, 14)) is None  # el miércoles vuelve a estar pendiente


def test_resumen_de_la_rejilla_agrupa_dias_por_hora():
    assert Recurrencia({0: "12:30", 2: "12:30", 4: "13:15"}).resumen == "L, X 12:30 · V 13:15"
    r = Recurrencia.de_dict(Recurrencia({1: "09:00"}, entrega=CORREO).a_dict())
    assert r.horas == {1: "09:00"} and r.entrega == CORREO


def test_informe_imprimible_del_historial(alumnos):
    marc = por_nombre(alumnos, "MARC")
    html = informe_html(marc, [salida(avisados=["madre", "alumno"], entrega=CORREO)], "Centro <de prueba>")
    assert "ALBERT FERRANDO, MARC" in html and "Centro &lt;de prueba&gt;" in html
    assert "12/10/2026" in html and "Por correo al alumno" in html and "madre, alumno" in html
    assert "Sin salidas registradas" in informe_html(marc, [], "C")


def test_correo_del_alumno_con_el_parte_y_aviso_a_la_familia(alumnos, datos):
    from partes_salida.ajustes import GestorAjustes
    from partes_salida.correo import ParteAdjunto, mensajes_del_parte

    marc = por_nombre(alumnos, "MARC")
    parte = ParteAdjunto(b"\x89PNG-parte", b"%PDF-parte", "Parte de salida ALBERT FERRANDO, MARC")
    gestor = GestorAjustes(datos)
    cuando = datetime(2026, 10, 12, 12, 30)
    familia, alumno = mensajes_del_parte(gestor, marc, cuando, ["rosa@ejemplo.es"], True, parte)
    assert alumno["To"] == "marc.albert@ejemplo.es" and alumno["Subject"].startswith("Tu parte de salida")
    assert "Hola, Marc" in alumno.get_body(("plain",)).get_content()
    for m in (familia, alumno):
        adjuntos = [p for p in m.iter_attachments() if p.get_content_type() == "application/pdf"]
        assert adjuntos and adjuntos[0].get_payload(decode=True) == b"%PDF-parte"
        assert 'alt="Parte de salida"' in m.get_body(("html",)).get_content()
    assert familia["To"] == "rosa@ejemplo.es" and "Estimada familia" in familia.get_body(("plain",)).get_content()
    assert len(mensajes_del_parte(gestor, marc, cuando, [], False, parte)) == 0
    ivan = por_nombre(alumnos, "IVÁN")
    assert mensajes_del_parte(gestor, ivan, cuando, [], True, parte) == [], "sin correo no hay parte por correo"


def test_paginacion_como_en_web_pedidos():
    from partes_salida.ui.listado import texto_recuento, ventana_paginas

    assert ventana_paginas(1, 10) == [1, 2, 3, 4, 5]
    assert ventana_paginas(6, 10) == [4, 5, 6, 7, 8]
    assert ventana_paginas(10, 10) == [8, 9, 10]
    assert texto_recuento(2, 10, 42, "salidas") == "Mostrando 11–20 de 42 salidas"
    assert texto_recuento(1, 10, 0, "salidas") == "Sin resultados"
