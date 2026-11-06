from datetime import datetime

import pytest

from partes_salida.ajustes import GestorAjustes
from partes_salida.busqueda import Buscador
from partes_salida.correo import asunto, construir_mensaje, texto_plano


def nombres(lista):
    return [a.nombre for a in lista]


def test_busqueda_sin_tildes_en_cualquier_orden(alumnos):
    b = Buscador(alumnos)
    assert nombres(b.buscar("beltran")) == ["NEREA"]
    assert nombres(b.buscar("roig nerea")) == ["NEREA"]
    assert nombres(b.buscar("Nér Bel")) == ["NEREA"]
    assert len(b.buscar("")) == len(alumnos)


def test_busqueda_tolera_erratas(alumnos):
    assert "NEREA" in nombres(Buscador(alumnos).buscar("beltan"))


def test_filtros_de_etapa_curso_y_etapas_ocultas(alumnos):
    b = Buscador(alumnos)
    assert {a.etapa_codigo for a in b.buscar(etapa="CFS")} == {"CFS"}
    assert nombres(b.buscar(clase="2BACC")) == ["NEREA"]
    assert all(a.etapa_codigo == "ESO" for a in b.buscar(etapas_visibles={"ESO"}))


def test_correo_en_femenino_con_logos_y_contacto(datos, alumnos):
    g = GestorAjustes(datos)
    g.poner(smtp_usuario="remitente@ejemplo.es")
    nerea = next(a for a in alumnos if a.nombre == "NEREA")
    salida = datetime(2026, 10, 8, 12, 30)
    msg = construir_mensaje(g, nerea, salida, ["amparo.roig@ejemplo.es"])
    assert msg["To"] == "amparo.roig@ejemplo.es"
    assert "remitente@ejemplo.es" in msg["From"]
    assert msg["Subject"] == asunto(nerea, salida)
    html = msg.get_body(("html",)).get_content()
    assert "su hija" in html and "autorizada" in html and "12:30" in html
    assert "jefaturafpbach@epla.es" in html and "96 363 73 54" in html
    imagenes = [p for p in msg.walk() if p.get_content_maintype() == "image"]
    assert len(imagenes) == 2 and all(p["Content-ID"] for p in imagenes)


def test_correo_en_masculino(datos, alumnos):
    g = GestorAjustes(datos)
    marc = next(a for a in alumnos if a.nombre == "MARC")
    texto = texto_plano(g.valores, marc, datetime(2026, 10, 8, 9, 0))
    assert "su hijo MARC" in texto and "autorizado" in texto


@pytest.mark.parametrize("para_alumno, frase", [
    (False, "no es necesario responderlo. Si tienen cualquier duda, contacten con Jefatura de Estudios:"),
    (True, "no hace falta que lo respondas. Si tienes cualquier duda, pregunta en Jefatura de Estudios:"),
])
def test_correo_avisa_de_que_es_automatico_antes_de_las_jefaturas(datos, alumnos, para_alumno, frase):
    g = GestorAjustes(datos)
    marc = next(a for a in alumnos if a.nombre == "MARC")
    msg = construir_mensaje(g, marc, datetime(2026, 10, 8, 9, 0), ["familia@example.com"], para_alumno=para_alumno)
    for parte in ("plain", "html"):
        cuerpo = msg.get_body((parte,)).get_content()
        assert "Este correo se ha enviado de forma automática" in cuerpo
        assert frase in cuerpo and cuerpo.index(frase) < cuerpo.index("@epla.es")


def test_correo_de_un_parte_para_otro_dia_no_dice_hoy(datos, alumnos):
    from datetime import date, time, timedelta

    from partes_salida.fechas import fecha_larga

    g = GestorAjustes(datos)
    marc = next(a for a in alumnos if a.nombre == "MARC")
    hoy = datetime.combine(date.today(), time(12, 30))
    assert asunto(marc, hoy).endswith("· hoy a las 12:30")
    assert f"hoy, {fecha_larga(hoy.date())}, a las 12:30 h" in texto_plano(g.valores, marc, hoy)
    otro = hoy + timedelta(days=3)
    assert asunto(marc, otro, para_alumno=True) == f"Tu parte de salida · el {otro:%d/%m/%Y} a las 12:30"
    texto = texto_plano(g.valores, marc, otro)
    assert f"el {fecha_larga(otro.date())}, a las 12:30 h" in texto and "hoy" not in texto
    msg = construir_mensaje(g, marc, otro, ["familia@ejemplo.es"])
    assert "hoy" not in msg.get_body(("html",)).get_content()


def test_contactos_de_jefatura_segun_la_etapa(datos):
    """CarlosFB: ESO, su jefatura (2026-10-20); Bachillerato, la de FP de mañana; FP, la de su turno (2026-11-06);
    el resto, mañana y tarde."""
    from partes_salida.modelo import Alumno

    g = GestorAjustes(datos)
    salida = datetime(2026, 10, 8, 9, 0)

    def pie(clase):
        a = Alumno(id="1", nia="1", nombre="ANA", apellido1="FICTICIA", apellido2="PRUEBA", sexo="F", clase=clase)
        return texto_plano(g.valores, a, salida)

    eso = pie("3ESOA")
    assert "Jefatura de ESO: jefaturaestudios.eso@epla.es" in eso and "Turno de tarde" not in eso
    bac = pie("1BACC")
    assert "Jefatura de Bachillerato: jefaturafpbach@epla.es" in bac and "Turno de tarde" not in bac
    superior = pie("1CFS-SEA")
    assert "Turno de mañana" in superior and "Turno de tarde" not in superior and "jefaturaestudios.eso" not in superior
    medio = pie("1CFM-ITE")
    assert "Turno de tarde" in medio and "Turno de mañana" not in medio
    primaria = pie("6PRIB")
    assert "Turno de mañana" in primaria and "Turno de tarde" in primaria


def test_contacto_vacio_no_sale(datos, alumnos):
    g = GestorAjustes(datos)
    g.poner(contacto_tarde_email="", contacto_tarde_tel="")
    primaria = next(a for a in alumnos if a.etapa_codigo == "PRI")
    texto = texto_plano(g.valores, primaria, datetime(2026, 10, 8, 9, 0))
    assert "Turno de tarde" not in texto and "Turno de mañana" in texto


def test_sin_servidor_de_correo_configurado_no_se_intenta_enviar(datos):
    # El repositorio es público: servidor y remitente no vienen de serie (ADR-015).
    from email.message import EmailMessage

    from partes_salida.correo import correo_configurado, enviar

    g = GestorAjustes(datos)
    assert not correo_configurado(g.valores)
    with pytest.raises(ValueError, match="Ajustes → Correo"):
        enviar(EmailMessage(), g.valores, "clave")
    g.poner(smtp_servidor="smtp.ejemplo.es", smtp_usuario="remitente@ejemplo.es")
    assert correo_configurado(g.valores)
