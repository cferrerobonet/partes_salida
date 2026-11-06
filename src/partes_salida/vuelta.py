"""Lo que vuelve al buzón de envío: rebotes y mensajes de las familias.

Las familias responden aunque el aviso diga que no hace falta. El aviso lleva
«Responder a» la jefatura del alumno, pero quien copia la dirección a mano escribe
al buzón de envío, y los rebotes (direcciones que ya no existen o están mal
escritas) llegan siempre ahí. Nadie lee ese buzón, así que la app lo revisa por
IMAP con la misma cuenta:

- Rebote de un correo de este equipo → el parte queda «Rebotado» en el historial,
  con la dirección, y se avisa para llamar a la familia.
- Mensaje de una familia o de un alumno (responde a un aviso o escribe desde un
  correo del padrón) → se reenvía a su jefatura, con «Responder a» quien lo escribió.
- Respuestas automáticas, rebotes de otros equipos y correo desconocido → no se tocan.

Lo tratado se marca en el servidor para que otro equipo no lo repita; nunca se
borra nada. Los mensajes se leen en memoria: nada va a disco ni al registro.
"""

from __future__ import annotations

import imaplib
import logging
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from email import policy
from email.message import EmailMessage, Message
from email.parser import BytesHeaderParser, BytesParser
from email.utils import formataddr, parseaddr

from .ajustes import Ajustes
from .modelo import Alumno

logger = logging.getLogger(__name__)

#: Palabra clave IMAP con que se marca lo tratado (si el servidor no las admite, se marca como leído).
MARCA = "PartesTratado"
#: Solo se mira lo llegado en estos días: lo de antes ya se trató o no es de nadie.
DIAS = 14
PUERTO_IMAP = 993
#: Lo que pasa de aquí no se descarga entero: se reenvía sin el original.
MAX_BYTES = 10 * 1024 * 1024
#: Reenvíos fallidos de un mismo mensaje antes de dejarlo y avisar.
INTENTOS = 3
_ID = re.compile(rb"<[^<>\s@]+@[^<>\s]+>")
_ID_CABECERA = re.compile(rb"^Message-ID:[ \t]*(<[^<>\s@]+@[^<>\s]+>)", re.I | re.M)
_MESES = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_DEMONIOS = ("mailer-daemon", "postmaster", "mail-daemon", "mailerdaemon")
_ASUNTOS_AUTOMATICOS = ("respuesta automática", "automatic reply", "auto-reply", "autoreply", "fuera de la oficina",
                        "out of office", "resposta automàtica")


@dataclass
class Rebote:
    ids: set[str]  # Message-ID de los correos devueltos que cita el rebote
    direcciones: list[str] = field(default_factory=list)


@dataclass
class Mensaje:
    """Lo que alguien ha escrito al buzón de envío."""

    remitente: str
    original: EmailMessage
    responde_a: set[str] = field(default_factory=set)  # Message-ID que cita (In-Reply-To, References)
    recortado: bool = False  # demasiado grande: solo se descargaron las cabeceras


def imap_configurado(ajustes: Ajustes) -> bool:
    return bool(ajustes.imap_servidor.strip() and ajustes.smtp_usuario.strip())


def _ids(datos: bytes | str) -> set[str]:
    if isinstance(datos, str):
        datos = datos.encode("utf-8", "replace")
    return {m.decode("ascii", "replace") for m in _ID.findall(datos)}


def _direccion(valor: str) -> str:
    """`rfc822; ana@ejemplo.es` → `ana@ejemplo.es`."""
    return parseaddr(valor.rpartition(";")[2].strip())[1].lower()


def _bloques_dsn(parte: Message) -> list[Message]:
    """Los bloques de campos de un `message/delivery-status` (el primero es el del servidor)."""
    carga = parte.get_payload()
    if isinstance(carga, list):
        return [b for b in carga if isinstance(b, Message)]
    texto = carga if isinstance(carga, str) else ""
    return [BytesHeaderParser(policy=policy.compat32).parsebytes((b + "\n").encode("utf-8", "replace"))
            for b in re.split(r"\r?\n\s*\r?\n", texto) if b.strip()]


def _es_informe(msg: Message) -> bool:
    return msg.get_content_type() == "multipart/report" and \
        (msg.get_param("report-type") or "").lower() == "delivery-status"


def es_del_servidor(msg: Message) -> bool:
    """Avisos de los servidores de correo (no entrega, retraso), no de personas."""
    usuario = parseaddr(str(msg.get("From", "")))[1].lower().partition("@")[0]
    return _es_informe(msg) or usuario in _DEMONIOS


def rebote(msg: Message, crudo: bytes) -> Rebote | None:
    """Si el mensaje es un aviso de no entrega, qué correos y qué direcciones. Los avisos de retraso
    («delayed») y de entrega no cuentan."""
    if not es_del_servidor(msg):
        return None
    informe = _es_informe(msg)
    fallido = not informe  # sin informe normalizado, el aviso de un demonio se toma por rebote
    direcciones: list[str] = []
    ids: set[str] = set()
    for parte in msg.walk():
        tipo = parte.get_content_type()
        if tipo == "message/delivery-status":
            for bloque in _bloques_dsn(parte):
                if str(bloque.get("Action", "")).strip().lower() == "failed":
                    fallido = True
                    destino = str(bloque.get("Final-Recipient") or bloque.get("Original-Recipient") or "")
                    if _direccion(destino) and _direccion(destino) not in direcciones:
                        direcciones.append(_direccion(destino))
        elif tipo == "message/rfc822":
            for interno in parte.get_payload() if isinstance(parte.get_payload(), list) else []:
                ids |= _ids(str(interno.get("Message-ID", "")))
        elif tipo == "text/rfc822-headers":
            cabeceras = BytesHeaderParser(policy=policy.compat32).parsebytes(parte.get_payload(decode=True) or b"")
            ids |= _ids(str(cabeceras.get("Message-ID", "")))
    if not fallido:
        return None
    if not ids:
        # Aviso sin el original en su sitio: solo las líneas «Message-ID:» citadas en el texto, no las
        # referencias (un reenvío a jefatura que rebote lleva las del mensaje de la familia).
        propio = _ids(str(msg.get("Message-ID", "")))
        ids = {m.decode("ascii", "replace") for m in _ID_CABECERA.findall(crudo)} - propio
    return Rebote(ids, direcciones)


def es_automatico(msg: Message) -> bool:
    """Respuestas automáticas (vacaciones, fuera de la oficina) y correo masivo: no se reenvían."""
    if str(msg.get("Auto-Submitted", "no")).strip().lower() not in ("", "no"):
        return True
    if msg.get("X-Autoreply") or msg.get("X-Autorespond"):
        return True
    if str(msg.get("Precedence", "")).strip().lower() in ("bulk", "junk", "list", "auto_reply"):
        return True
    asunto = str(msg.get("Subject", "")).strip().lower()
    return asunto.startswith(_ASUNTOS_AUTOMATICOS)


def clasificar(crudo: bytes, recortado: bool = False) -> Rebote | Mensaje | None:
    msg = BytesParser(policy=policy.default).parsebytes(crudo)
    r = rebote(msg, crudo)
    if r is not None:
        return r
    if es_del_servidor(msg) or es_automatico(msg):
        return None
    remitente = parseaddr(str(msg.get("From", "")))[1].lower()
    if not remitente:
        return None
    citados = _ids(f"{msg.get('In-Reply-To', '')} {msg.get('References', '')}")
    return Mensaje(remitente, msg, citados, recortado)


# Reenvío a jefatura


def _texto(msg: EmailMessage) -> str:
    try:
        cuerpo = msg.get_body(("plain",))
        if cuerpo is not None:
            return cuerpo.get_content().strip()
        cuerpo = msg.get_body(("html",))
        if cuerpo is not None:
            sin_etiquetas = re.sub(r"<(style|script)\b.*?</\1>|<[^>]+>", " ", cuerpo.get_content(), flags=re.S | re.I)
            return re.sub(r"[ \t]+", " ", re.sub(r"\n\s*\n+", "\n\n", sin_etiquetas)).strip()
    except (LookupError, KeyError, ValueError):
        pass
    return "(Véase el mensaje adjunto.)"


def mensaje_de_reenvio(a: Ajustes, alumnos: list[Alumno], mensaje: Mensaje, destino: str,
                       nuevo_id: Callable[[str], str]) -> EmailMessage:
    """El mensaje de la familia, a su jefatura: «Responder» le contesta a ella, y el original va adjunto."""
    quien = mensaje.remitente
    es_alumno = any(quien == al.email.strip().lower() for al in alumnos)
    nombres = ", ".join(f"{al.nombre_completo} ({al.curso})" for al in alumnos)
    de = "del alumno" if es_alumno and not alumnos[0].es_mujer else "de la alumna" if es_alumno else "de la familia"
    breves = ", ".join(f"{al.nombre} {al.apellido1}" for al in alumnos)
    msg = EmailMessage()
    msg["Subject"] = f"Mensaje {de}: {breves}"
    msg["From"] = formataddr((a.remitente_nombre, a.smtp_usuario))
    msg["To"] = destino
    msg["Reply-To"] = quien
    msg["Auto-Submitted"] = "auto-forwarded"
    msg["Message-ID"] = nuevo_id(a.smtp_usuario)
    asunto = str(mensaje.original.get("Subject", "")).strip() or "(sin asunto)"
    msg.set_content("\n".join([
        "Este mensaje ha llegado al buzón de envío de los partes de salida, que no se lee: se reenvía a "
        "Jefatura de Estudios.",
        "",
        f"Lo escribe: {quien}",
        f"Sobre: {nombres}",
        f"Asunto: {asunto}",
        "",
        f"Para contestar, pulse Responder: la respuesta irá a {quien}.",
        "",
        *(["El mensaje es demasiado grande para reenviarlo: está en el buzón de envío."] if mensaje.recortado
          else ["--- Mensaje original ---", "", _texto(mensaje.original)]),
    ]))
    if not mensaje.recortado:
        msg.add_attachment(mensaje.original)
    return msg


# Pasada por el buzón


@dataclass
class Estado:
    """Lo que se recuerda entre pasadas mientras la app está abierta."""

    vistos: set[str] = field(default_factory=set)  # ya mirado y no era de este equipo (o ya tratado)
    intentos: dict[str, int] = field(default_factory=dict)  # reenvíos fallidos de cada mensaje
    enviados: dict[str, set[str]] = field(default_factory=dict)  # mensaje → jefaturas a las que ya salió


@dataclass
class Resultado:
    rebotes: list[tuple[str, str, list[str]]] = field(default_factory=list)  # (alumno, salida, direcciones)
    reenviados: int = 0
    sin_reenviar: int = 0  # mensajes que no se han podido reenviar tras `INTENTOS`: quedan en el buzón
    revisados: int = 0
    error: str = ""  # tipo del error que cortó la pasada; lo de antes vale


def _fecha_imap(dia: date) -> str:
    return f"{dia.day:02d}-{_MESES[dia.month - 1]}-{dia.year}"


def _marca_del_buzon(imap) -> str:
    """La palabra clave si el servidor la guarda; si no, «leído»."""
    _, datos = imap.response("PERMANENTFLAGS")
    banderas = b" ".join(d for d in datos or [] if isinstance(d, bytes))
    return MARCA if (b"\\*" in banderas or MARCA.encode() in banderas) else "\\Seen"


def _ok(respuesta, que: str):
    tipo, datos = respuesta
    if tipo != "OK":
        raise imaplib.IMAP4.error(f"El servidor no ha aceptado {que}")
    return datos


def _descargar(imap, uid: bytes) -> tuple[bytes | None, bool]:
    """El mensaje entero o, si pasa de `MAX_BYTES`, solo sus cabeceras (y `True`)."""
    datos = _ok(imap.uid("FETCH", uid, "(RFC822.SIZE)"), "la consulta del tamaño")
    texto = b" ".join(d if isinstance(d, bytes) else d[0] for d in datos or [] if d)
    tamano = re.search(rb"RFC822\.SIZE (\d+)", texto)
    grande = bool(tamano) and int(tamano.group(1)) > MAX_BYTES
    datos = _ok(imap.uid("FETCH", uid, "(BODY.PEEK[HEADER])" if grande else "(BODY.PEEK[])"), "la descarga")
    return next((d[1] for d in datos or [] if isinstance(d, tuple) and len(d) > 1), None), grande


def revisar(
    imap,
    conocidos: dict[str, tuple[str, str]],
    alumnos_de: Callable[[Mensaje, str | None], list[Alumno]],
    jefatura_de: Callable[[Alumno], str],
    enviar_a: Callable[[str, list[Alumno], Mensaje], None],
    estado: Estado,
    dominio: str = "",
    hoy: date | None = None,
) -> Resultado:
    """Una pasada por la bandeja de entrada.

    `conocidos`: Message-ID de los correos de este equipo → (alumno, salida). `alumnos_de(mensaje,
    id_alumno)`: de quién habla un mensaje (el alumno del parte que cita o, si no cita ninguno, los del
    padrón con ese correo). `jefatura_de(alumno)`: adónde se reenvía ("" si a ninguna). `enviar_a(destino,
    alumnos, mensaje)` lo manda. `dominio`, el del buzón: un mensaje que responde a un correo de ese
    dominio que no es de este equipo responde al aviso de otro equipo (comparten buzón), y lo trata ese.

    Si algo falla a mitad, se devuelve lo hecho hasta ahí (con `error`): los rebotes ya marcados en el
    servidor tienen que llegar al historial.
    """
    resultado = Resultado()
    _ok(imap.select("INBOX"), "la bandeja de entrada")
    marca = _marca_del_buzon(imap)
    _, validez = imap.response("UIDVALIDITY")
    validez = (validez or [b""])[0] or b""
    desde = _fecha_imap((hoy or date.today()) - timedelta(days=DIAS))
    pendiente = ("UNKEYWORD", MARCA) if marca == MARCA else ("UNSEEN",)
    datos = _ok(imap.uid("SEARCH", None, "SINCE", desde, *pendiente), "la búsqueda")
    for uid in (datos[0] or b"").split() if datos else []:
        clave = f"{validez!r}:{uid!r}"
        if clave in estado.vistos:
            continue
        try:
            _tratar(imap, uid, clave, marca, conocidos, alumnos_de, jefatura_de, enviar_a, estado, dominio,
                    resultado)
        except Exception as e:  # noqa: BLE001 - se corta la pasada, no lo ya hecho
            resultado.error = type(e).__name__
            break
    return resultado


def _tratar(imap, uid, clave, marca, conocidos, alumnos_de, jefatura_de, enviar_a, estado: Estado, dominio,
            resultado: Resultado) -> None:
    estado.vistos.add(clave)
    crudo, recortado = _descargar(imap, uid)
    if not crudo:
        return
    resultado.revisados += 1
    cosa = clasificar(crudo, recortado)
    if isinstance(cosa, Rebote):
        propios = [conocidos[m] for m in sorted(cosa.ids & conocidos.keys())]
        if propios:
            _ok(imap.uid("STORE", uid, "+FLAGS", f"({marca})"), "la marca")
            resultado.rebotes += [(id_alumno, id_salida, list(cosa.direcciones)) for id_alumno, id_salida in propios]
        return
    if not isinstance(cosa, Mensaje):
        return
    citado = next((conocidos[m] for m in sorted(cosa.responde_a & conocidos.keys())), None)
    if citado is None and dominio and any(m.lower().endswith(f"@{dominio.lower()}>") for m in cosa.responde_a):
        return  # responde al aviso de otro equipo: que lo trate ese
    destinos: dict[str, list[Alumno]] = {}
    for al in alumnos_de(cosa, citado[0] if citado else None):
        if jefatura_de(al):
            destinos.setdefault(jefatura_de(al), []).append(al)
    if not destinos:
        return
    # Se reserva antes de reenviar: otro equipo que revise a la vez ya no lo ve.
    _ok(imap.uid("STORE", uid, "+FLAGS", f"({marca})"), "la marca")
    hechos = estado.enviados.setdefault(clave, set())
    try:
        for destino, suyos in destinos.items():
            if destino not in hechos:  # hermanos de etapas distintas: no repetir la jefatura que ya lo tiene
                enviar_a(destino, suyos, cosa)
                hechos.add(destino)
    except Exception as e:  # noqa: BLE001
        intentos = estado.intentos[clave] = estado.intentos.get(clave, 0) + 1
        logger.warning("Reenvío a jefatura fallido (%s), intento %d de %d", type(e).__name__, intentos, INTENTOS)
        if intentos >= INTENTOS:
            resultado.sin_reenviar += 1  # se queda marcado: no se insiste más y se avisa
        else:
            estado.vistos.discard(clave)
            _ok(imap.uid("STORE", uid, "-FLAGS", f"({marca})"), "la marca")
        return
    resultado.reenviados += 1


def abrir(ajustes: Ajustes, clave: str) -> imaplib.IMAP4_SSL:
    try:
        import certifi

        contexto = ssl.create_default_context(cafile=certifi.where())
    except ImportError:
        contexto = ssl.create_default_context()
    imap = imaplib.IMAP4_SSL(ajustes.imap_servidor.strip(), PUERTO_IMAP, ssl_context=contexto, timeout=25)
    imap.login(ajustes.smtp_usuario.strip(), clave)
    return imap
