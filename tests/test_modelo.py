from datetime import date

import pytest

from partes_salida.modelo import (
    Alumno,
    Tutor,
    analizar_clase,
    aplicar_correcciones,
    aplicar_patria_potestad,
    clave_nombre,
    etapas_presentes,
    nombre_propio,
)


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


def test_patria_potestad_exclusiva():
    madre = Tutor("MADRE", "Rosa Gil", "m@example.com")
    padre = Tutor("PADRE", "Joan Pla", "p@example.com")
    a = Alumno("1", tutores=[madre, padre])
    assert aplicar_patria_potestad(a, madre.clave)
    assert madre.puede_recibir_correo and not padre.puede_recibir_correo
    assert "sin_patria_potestad" not in a.a_dict()["tutores"][1]  # no se guarda en el padrón
    assert not aplicar_patria_potestad(a, "NADIE")  # ya no coincide: nadie recibe
    assert not madre.puede_recibir_correo and not padre.puede_recibir_correo
    assert aplicar_patria_potestad(a, None)
    assert madre.puede_recibir_correo and padre.puede_recibir_correo


def test_correos_corregidos_y_anadidos_en_este_equipo():
    madre = Tutor("MADRE", "Rosa Gil", "mal@example.com")
    padre = Tutor("PADRE", "Joan Pla", "")
    a = Alumno("1", tutores=[madre, padre])
    correcciones = {
        "familiar:ROSA GIL": {"de": "mal@example.com", "a": "rosa@example.com"},
        "familiar:JOAN PLA": {"de": "", "a": "joan@example.com"},  # sin correo en Educamos: se le pone
        "alumno": {"de": "", "a": "alumno@example.com"},
    }
    assert aplicar_correcciones(a, correcciones) == []
    assert (madre.email, padre.email, a.email) == ("rosa@example.com", "joan@example.com", "alumno@example.com")
    assert padre.puede_recibir_correo
    # El padrón guarda siempre lo de Educamos
    d = a.a_dict()
    assert (d["email"], d["tutores"][0]["email"], d["tutores"][1]["email"]) == ("", "mal@example.com", "")
    assert "correo_educamos" not in d and "correo_educamos" not in d["tutores"][0]
    # Aplicarlo otra vez (el mismo padrón reimportado) da lo mismo
    assert aplicar_correcciones(a, correcciones) == [] and madre.email == "rosa@example.com"
    # Educamos trae ya otra dirección: manda Educamos y la corrección se olvida
    nuevo = Alumno.de_dict(d)
    nuevo.tutores[0].email = "rosa.gil@example.com"
    nuevo.email = "alumno.educamos@example.com"
    assert sorted(aplicar_correcciones(nuevo, correcciones)) == ["alumno", "familiar:ROSA GIL"]
    assert nuevo.tutores[0].email == "rosa.gil@example.com" and nuevo.tutores[0].correo_educamos is None
    assert nuevo.email == "alumno.educamos@example.com"
    assert nuevo.tutores[1].email == "joan@example.com"
    # Sin correcciones, todo vuelve a lo de Educamos
    aplicar_correcciones(a, {})
    assert (madre.email, padre.email, a.email) == ("mal@example.com", "", "")
