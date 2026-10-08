from datetime import datetime

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
    nerea = next(a for a in alumnos if a.nombre == "NEREA")
    salida = datetime(2026, 10, 8, 12, 30)
    msg = construir_mensaje(g, nerea, salida, ["amparo.roig@ejemplo.es"])
    assert msg["To"] == "amparo.roig@ejemplo.es"
    assert "no_contestar@aplicaciones.epla.es" in msg["From"]
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


def test_contacto_vacio_no_sale(datos, alumnos):
    g = GestorAjustes(datos)
    g.poner(contacto_tarde_email="", contacto_tarde_tel="")
    texto = texto_plano(g.valores, alumnos[0], datetime(2026, 10, 8, 9, 0))
    assert "Turno de tarde" not in texto and "Turno de mañana" in texto
