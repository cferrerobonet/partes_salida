"""Lo que vuelve al buzón de envío: jefatura de cada alumno, rebotes y mensajes de las familias (sin red)."""

from datetime import date, datetime

import pytest

from partes_salida.ajustes import Ajustes, GestorAjustes
from partes_salida.almacen import Almacen
from partes_salida.cifrado import Cifrador
from partes_salida.correo import construir_mensaje, correo_jefatura, nuevo_id
from partes_salida.modelo import Alumno, Tutor
from partes_salida.seguimiento import PAPEL, Salida, Seguimiento
from partes_salida.vuelta import MARCA, Estado, Mensaje, Rebote, clasificar, mensaje_de_reenvio, revisar

ESO = "jefaturaestudios.eso@epla.es"
MANANA = "jefaturafpbach@epla.es"
TARDE = "jefaturafptarde@epla.es"
NUESTRO = "<1.aviso@ejemplo.es>"


def alumno(clase="1CFS-SEA", **kw):
    return Alumno(id=kw.pop("id", "1"), nombre="ANA", apellido1="FICTICIA", apellido2="PRUEBA", sexo="F",
                  clase=clase, **kw)


@pytest.mark.parametrize("clase, jefatura", [
    ("3ESOA", ESO),
    ("1BACC", MANANA),
    ("1BAHA", MANANA),
    ("1CFS-SEA", MANANA),
    ("2CFS-AYF", MANANA),
    ("2CFM-CARR", MANANA),  # 2º de Carrocería, la única de Grado Medio en la de mañana
    ("1CFM-CARR", TARDE),
    ("2CFM-IEA-A", TARDE),
    ("1CFB-EE", TARDE),
    ("6PRIB", ""),
])
def test_jefatura_de_cada_alumno(datos, clase, jefatura):
    """CarlosFB (2026-11-06): mañana, Bachillerato, Grado Superior y 2º de Carrocería; tarde, Básico y Medio."""
    assert correo_jefatura(GestorAjustes(datos).valores, alumno(clase)) == jefatura


def test_el_aviso_responde_a_su_jefatura_y_lleva_identificador_propio(datos):
    g = GestorAjustes(datos)
    g.poner(smtp_usuario="partes@ejemplo.es")
    salida = datetime(2026, 11, 6, 12, 30)
    msg = construir_mensaje(g, alumno("2CFM-IEA-A"), salida, ["familia@example.com"])
    assert msg["Reply-To"] == TARDE
    assert msg["Message-ID"].endswith("@ejemplo.es>")
    assert "las respuestas llegan a Jefatura de Estudios" in msg.get_body(("plain",)).get_content()
    sin_jefatura = construir_mensaje(g, alumno("6PRIB"), salida, ["familia@example.com"])
    assert sin_jefatura["Reply-To"] is None
    assert "este buzón no recibe respuestas" in sin_jefatura.get_body(("plain",)).get_content()


# Correos que llegan al buzón (inventados)


def dsn(accion="failed", destino="perdido@example.com", cita=NUESTRO) -> bytes:
    return f"""From: Mail Delivery System <MAILER-DAEMON@mx.example.net>
To: partes@ejemplo.es
Subject: Undelivered Mail Returned to Sender
MIME-Version: 1.0
Content-Type: multipart/report; report-type=delivery-status; boundary="B"

--B
Content-Type: text/plain

No se ha podido entregar.
--B
Content-Type: message/delivery-status

Reporting-MTA: dns; mx.example.net

Final-Recipient: rfc822; {destino}
Action: {accion}
Status: 5.1.1

--B
Content-Type: text/rfc822-headers

Message-ID: {cita}
Subject: Salida del centro

--B--
""".encode()


def correo(remitente="familia@example.com", asunto="Re: Salida del centro", cita="", extra="") -> bytes:
    hilo = f"In-Reply-To: {cita}\nReferences: {cita}\n" if cita else ""
    return (f"From: Familia <{remitente}>\nTo: partes@ejemplo.es\nSubject: {asunto}\n{hilo}{extra}"
            "Content-Type: text/plain; charset=utf-8\n\nGracias, ¿puede salir antes?\n").encode()


def test_rebote_dice_que_correo_y_que_direccion():
    r = clasificar(dsn())
    assert isinstance(r, Rebote) and r.ids == {NUESTRO} and r.direcciones == ["perdido@example.com"]


def test_un_aviso_de_retraso_no_es_rebote_ni_mensaje():
    assert clasificar(dsn(accion="delayed")) is None


def test_respuestas_automaticas_no_se_reenvian():
    assert clasificar(correo(asunto="Respuesta automática: fuera de la oficina")) is None
    assert clasificar(correo(extra="Auto-Submitted: auto-replied\n")) is None


def test_mensaje_de_una_familia_con_lo_que_cita():
    m = clasificar(correo(cita=NUESTRO))
    assert isinstance(m, Mensaje) and m.remitente == "familia@example.com" and m.responde_a == {NUESTRO}


def test_reenvio_a_jefatura_con_responder_a_la_familia(datos):
    g = GestorAjustes(datos)
    g.poner(smtp_usuario="partes@ejemplo.es")
    m = clasificar(correo())
    r = mensaje_de_reenvio(g.valores, [alumno("2CFB-EE")], m, TARDE, nuevo_id)
    assert r["To"] == TARDE and r["Reply-To"] == "familia@example.com"
    assert r["Subject"] == "Mensaje de la familia: ANA FICTICIA"
    texto = r.get_body(("plain",)).get_content()
    assert "¿puede salir antes?" in texto and "Sobre: ANA FICTICIA PRUEBA (2º EE)" in texto
    assert [p.get_content_type() for p in r.iter_attachments()] == ["message/rfc822"]


# Pasada por el buzón con un servidor simulado


class Imap:
    """Servidor IMAP simulado: guarda las marcas y lo que se pide."""

    def __init__(self, mensajes, banderas=b"(\\Seen \\Flagged \\*)", tamanos=None, rompe=None):
        self.mensajes = {str(i + 1).encode(): m for i, m in enumerate(mensajes)}
        self.banderas = banderas
        self.tamanos = tamanos or {}
        self.rompe = rompe  # uid cuya descarga corta la conexión
        self.marcados, self.buscados, self.pedidos, self.ordenes = set(), [], [], []

    def select(self, _buzon):
        return "OK", [b"1"]

    def response(self, codigo):
        return codigo, [self.banderas if codigo == "PERMANENTFLAGS" else b"7"]

    def uid(self, orden, *args):
        if orden == "SEARCH":
            self.buscados.append(args)
            return "OK", [b" ".join(u for u in self.mensajes if u not in self.marcados)]
        if orden == "FETCH":
            uid, que = args
            if que == "(RFC822.SIZE)":
                return "OK", [b"%s (UID %s RFC822.SIZE %d)" % (uid, uid, self.tamanos.get(uid, 2000))]
            if uid == self.rompe:
                raise OSError("conexión cerrada")
            self.pedidos.append((uid, que))
            crudo = self.mensajes[uid]
            if que == "(BODY.PEEK[HEADER])":
                crudo = crudo.split(b"\n\n", 1)[0] + b"\n\n"
            return "OK", [(b"1 (BODY[] {1}", crudo), b")"]
        if orden == "STORE":
            uid, signo, marca = args
            self.ordenes.append((uid, signo, marca))
            (self.marcados.add if signo == "+FLAGS" else self.marcados.discard)(uid)
            return "OK", []
        raise AssertionError(orden)


def pasada(imap, conocidos, alumnos_de, enviar_a, estado=None, jefatura_de=None):
    return revisar(imap, conocidos, alumnos_de, jefatura_de or (lambda a: correo_jefatura(AJUSTES, a)), enviar_a,
                   estado if estado is not None else Estado(), "ejemplo.es", date(2026, 11, 6))


AJUSTES = Ajustes()  # contactos de jefatura de serie


def test_una_pasada_trata_lo_suyo_y_deja_lo_ajeno():
    ana = alumno("2CFB-EE", id="A", tutores=[Tutor(email="familia@example.com")])
    imap = Imap([
        dsn(),                                                    # 1 rebote de un aviso nuestro
        dsn(cita="<9.otro@ejemplo.es>"),                          # 2 rebote de otro equipo
        correo(cita=NUESTRO),                                     # 3 responde a un aviso nuestro
        correo(remitente="familia@example.com"),                  # 4 escribe desde cero, está en el padrón
        correo(remitente="otra@example.com", cita="<9.otro@ejemplo.es>"),  # 5 responde al aviso de otro equipo
        correo(remitente="desconocido@example.com"),              # 6 no está en el padrón
        correo(extra="Auto-Submitted: auto-replied\n"),           # 7 automática
    ])
    reenviados = []
    conocidos = {NUESTRO: ("A", "S1")}

    def alumnos_de(m, id_alumno):
        if id_alumno:
            return [ana]
        return [ana] if m.remitente == "familia@example.com" else []

    estado = Estado()
    r = pasada(imap, conocidos, alumnos_de, lambda d, al, m: reenviados.append((d, m.remitente)), estado)
    assert r.rebotes == [("A", "S1", ["perdido@example.com"])] and not r.error
    assert r.reenviados == 2 and reenviados == [(TARDE, "familia@example.com")] * 2
    assert imap.marcados == {b"1", b"3", b"4"}
    assert imap.buscados[0] == (None, "SINCE", "23-Oct-2026", "UNKEYWORD", MARCA)

    # Lo ajeno no se vuelve a descargar mientras la app sigue abierta.
    pasada(imap, conocidos, alumnos_de, lambda d, al, m: None, estado)
    assert len(imap.pedidos) == 7


def test_si_el_reenvio_falla_se_reintenta_y_al_tercero_se_avisa():
    imap = Imap([correo(cita=NUESTRO)])
    estado = Estado()

    def falla(*_):
        raise OSError("sin conexión")

    for _ in range(2):
        r = pasada(imap, {NUESTRO: ("A", "S1")}, lambda m, i: [alumno()], falla, estado)
        assert r.reenviados == 0 and r.sin_reenviar == 0 and imap.marcados == set()
    r = pasada(imap, {NUESTRO: ("A", "S1")}, lambda m, i: [alumno()], falla, estado)
    assert r.sin_reenviar == 1 and imap.marcados == {b"1"}  # no se insiste más
    assert imap.ordenes[0] == (b"1", "+FLAGS", f"({MARCA})")  # se reserva antes de reenviar


def test_hermanos_de_dos_etapas_no_repiten_la_jefatura_que_ya_lo_tiene():
    hermanos = [alumno("3ESOA", id="E"), alumno("1CFS-SEA", id="S")]
    imap = Imap([correo(remitente="familia@example.com")])
    estado, enviados = Estado(), []

    def a_veces(destino, _al, _m):
        if destino == MANANA and "fallo" not in enviados:  # la primera vez falla la segunda jefatura
            enviados.append("fallo")
            raise OSError("sin conexión")
        enviados.append(destino)

    pasada(imap, {}, lambda m, i: hermanos, a_veces, estado)
    r = pasada(imap, {}, lambda m, i: hermanos, a_veces, estado)
    assert r.reenviados == 1 and enviados == [ESO, "fallo", MANANA]


def test_un_fallo_a_mitad_conserva_los_rebotes_ya_marcados():
    imap = Imap([dsn(), correo(cita=NUESTRO)], rompe=b"2")
    r = pasada(imap, {NUESTRO: ("A", "S1")}, lambda m, i: [alumno()], lambda *a: None)
    assert r.rebotes == [("A", "S1", ["perdido@example.com"])] and r.error == "OSError"


def test_un_mensaje_enorme_se_reenvia_sin_el_original(datos):
    imap = Imap([correo(cita=NUESTRO)], tamanos={b"1": 50 * 1024 * 1024})
    hechos = []
    pasada(imap, {NUESTRO: ("A", "S1")}, lambda m, i: [alumno()], lambda d, al, m: hechos.append(m))
    assert imap.pedidos == [(b"1", "(BODY.PEEK[HEADER])")]
    g = GestorAjustes(datos)
    r = mensaje_de_reenvio(g.valores, [alumno()], hechos[0], MANANA, nuevo_id)
    assert "demasiado grande" in r.get_body(("plain",)).get_content() and not list(r.iter_attachments())


def test_sin_palabras_clave_en_el_servidor_se_marca_como_leido():
    imap = Imap([dsn()], banderas=b"(\\Seen \\Flagged)")
    pasada(imap, {NUESTRO: ("A", "S1")}, lambda m, i: [], lambda *a: None)
    assert imap.buscados[0][-1] == "UNSEEN" and imap.ordenes == [(b"1", "+FLAGS", "(\\Seen)")]


def test_rebote_sin_original_solo_mira_las_lineas_message_id():
    """El rebote de un reenvío a jefatura cita en References el aviso al que respondía la familia: no cuenta."""
    sin_original = f"""From: MAILER-DAEMON@mx.example.net
Subject: Mail delivery failed
Message-ID: <propio.dsn@mx.example.net>
Content-Type: text/plain

No se ha podido entregar a jefatura.
References: {NUESTRO}
Message-ID: <reenvio.1@ejemplo.es>
""".encode()
    r = clasificar(sin_original)
    assert isinstance(r, Rebote) and r.ids == {"<reenvio.1@ejemplo.es>"}


def test_el_aviso_pide_que_no_contesten_las_respuestas_automaticas(datos):
    g = GestorAjustes(datos)
    msg = construir_mensaje(g, alumno(), datetime(2026, 11, 6, 12, 30), ["familia@example.com"])
    assert msg["Auto-Submitted"] == "auto-generated"


def test_indice_de_correos_del_padron_con_hermanos():
    from partes_salida.ui.vuelta import por_correo

    a = alumno(id="1", email="Ana@Example.com", tutores=[Tutor(email="FAMILIA@example.com")])
    b = alumno(id="2", tutores=[Tutor(email="familia@example.com")])
    indice = por_correo([a, b])
    assert [x.id for x in indice["familia@example.com"]] == ["1", "2"] and [x.id for x in indice["ana@example.com"]] == ["1"]


def test_el_historial_guarda_identificadores_y_rebotes(datos):
    seg = Seguimiento(Almacen(datos, Cifrador.del_llavero()))
    s = seg.registrar("A", Salida.nueva(datetime(2026, 11, 6, 12, 30), PAPEL, ["madre"]))
    seg.marcar_correo("A", s.id, "enviado", [NUESTRO])
    assert seg.mensajes_conocidos() == {NUESTRO: ("A", s.id)}
    seg.marcar_rebote("A", s.id, ["Perdido@Example.com"])
    otro = Seguimiento(Almacen(datos, Cifrador.del_llavero()))
    guardada = otro.salidas("A")[0]
    assert guardada.correo_texto == "Rebotado" and guardada.rebotes == ["perdido@example.com"]
    assert otro.mensajes_conocidos() == {NUESTRO: ("A", s.id)}
