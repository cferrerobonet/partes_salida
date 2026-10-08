from datetime import date

import pytest

from partes_salida.modelo import Alumno, Tutor, analizar_clase, clave_nombre, etapas_presentes, nombre_propio


@pytest.mark.parametrize(
    ("clase", "esperado"),
    [
        ("1CFS-SEA", ("CFS", "FP Grado Superior", "1º SEA")),
        ("2CFM-IEA-B", ("CFM", "FP Grado Medio", "2º IEA B")),
        ("1CFB-SA", ("CFB", "FP Grado Básico", "1º SA")),
        ("2BACC", ("BAC", "Bachillerato", "2º Bach. Ciencias C")),
        ("1BAHA", ("BAC", "Bachillerato", "1º Bach. Humanidades A")),
        ("4ESOB", ("ESO", "ESO", "4º ESO B")),
        ("6PRIC", ("PRI", "Primaria", "6º Primaria C")),
        ("3INFA", ("INF", "Infantil", "Infantil 3 años A")),
        ("RARO", ("OTR", "Otros", "RARO")),
        ("", ("OTR", "Otros", "—")),
    ],
)
def test_etapa_y_curso_salen_de_la_clase(clase, esperado):
    assert analizar_clase(clase) == esperado


def test_clave_de_nombre_ignora_tildes_mayusculas_y_espacios():
    assert clave_nombre("Peña  Mejía , Enmanuel") == clave_nombre("PENA MEJIA, ENMANUEL") == "PENA MEJIA, ENMANUEL"
    assert clave_nombre("D'Acosta-Pérez, Ñoño") == "D ACOSTA PEREZ, NONO"


def test_nombre_propio_respeta_particulas():
    assert nombre_propio("MARIA DE LA O GARCIA-PONS") == "Maria de la O Garcia-Pons"
    assert nombre_propio("DE LA FUENTE") == "De la Fuente"


def test_alumno_nombres_genero_y_edad():
    a = Alumno(id="1", nombre="LUCÍA", apellido1="GARCÍA", apellido2="SOLER", sexo="F", clase="2ESOA",
               nacimiento="2012-10-09")
    assert a.nombre_completo == "LUCÍA GARCÍA SOLER"
    assert a.nombre_listado == "GARCÍA SOLER, LUCÍA"
    assert a.es_mujer
    assert a.edad(date(2026, 10, 8)) == 13
    assert a.edad(date(2026, 10, 9)) == 14
    assert Alumno(id="2").edad() is None


def test_alumno_ida_y_vuelta_por_diccionario():
    a = Alumno(id="1", nombre="A", tutores=[Tutor("MADRE", "Ana", "ana@x.es", "600", True)], clase="1CFS-SEA")
    b = Alumno.de_dict(a.a_dict())
    assert b == a and b.curso == "1º SEA"


def test_tutor_parentesco_y_correo():
    assert Tutor("TUTOR LEGAL").parentesco_texto == "Tutor legal"
    assert Tutor("").parentesco_texto == "Familiar"
    assert not Tutor(email="x@y.es", recibe_informacion=False).puede_recibir_correo
    assert Tutor(email="x@y.es").puede_recibir_correo


def test_etapas_presentes_en_orden_de_botones():
    al = [Alumno(id=str(i), clase=c) for i, c in enumerate(["1CFS-SEA", "1BAHA", "3INFA", "2BACC"])]
    assert etapas_presentes(al) == ["INF", "BAC", "CFS"]
