"""Historial de salidas y partes recurrentes de cada alumno, cifrados en el equipo.

Vive en `seguimiento.bin` (AES-GCM, como el padrón). Todo cuelga de un alumno del
padrón y desaparece con él: al reimportar el Excel se borra lo de quien ya no
está y se conserva lo de quien sigue; «Vaciar todos los datos del alumnado» lo
borra todo. Importar fotos o ajustes no lo toca.
"""

from __future__ import annotations

import html
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, time

from .fechas import fecha_larga
from .modelo import Alumno

DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")
DIAS_CORTOS = ("L", "M", "X", "J", "V")
PAPEL = "papel"
CORREO = "correo"


def _minuto(momento: datetime) -> str:
    return momento.replace(second=0, microsecond=0).isoformat(timespec="minutes")


@dataclass
class Salida:
    """Una entrada del historial: un parte emitido."""

    expedido: str
    salida: str
    entrega: str = PAPEL  # «papel» (impreso) o «correo» (enviado al alumno)
    recurrente: bool = False
    avisados: list[str] = field(default_factory=list)  # «madre», «padre», «alumna»…
    correo: str = ""  # "" sin correo · «enviando» · «enviado» · «no enviado»
    equipo: str = ""
    id: str = field(default_factory=lambda: uuid.uuid4().hex)

    @classmethod
    def nueva(cls, salida: datetime, entrega: str, avisados: list[str], recurrente: bool = False,
              equipo: str = "", expedido: datetime | None = None) -> Salida:
        return cls(
            expedido=_minuto(expedido or datetime.now()),
            salida=_minuto(salida),
            entrega=entrega,
            recurrente=recurrente,
            avisados=list(avisados),
            correo="enviando" if avisados else "",
            equipo=equipo,
        )

    @property
    def momento_salida(self) -> datetime:
        return datetime.fromisoformat(self.salida)

    @property
    def momento_expedido(self) -> datetime:
        return datetime.fromisoformat(self.expedido)

    @property
    def como(self) -> str:
        texto = "Impreso" if self.entrega == PAPEL else "Por correo al alumno"
        return texto + (" · recurrente" if self.recurrente else "")

    @property
    def avisados_texto(self) -> str:
        return ", ".join(self.avisados) if self.avisados else "—"

    @property
    def correo_texto(self) -> str:
        return {"": "—", "enviando": "Enviando…", "enviado": "Enviado", "no enviado": "No enviado",
                "sin confirmar": "Sin confirmar"}.get(
            self.correo, self.correo
        )


@dataclass
class Recurrencia:
    """Un alumno que sale los mismos días a la misma hora todo el curso."""

    horas: dict[int, str]  # día de la semana (0 = lunes … 4 = viernes) → «HH:MM»
    motivo: str = ""
    entrega: str = PAPEL
    avisar_familia: bool = False
    alta: str = field(default_factory=lambda: date.today().isoformat())

    def hora(self, dia: int) -> time | None:
        h = self.horas.get(dia)
        return time.fromisoformat(h) if h else None

    @property
    def resumen(self) -> str:
        """`L, X 12:30 · V 13:15`: días agrupados por hora, en orden de la semana."""
        por_hora: dict[str, list[int]] = {}
        for d in sorted(self.horas):
            por_hora.setdefault(self.horas[d], []).append(d)
        grupos = sorted(por_hora.items(), key=lambda g: g[1][0])
        return " · ".join(f"{', '.join(DIAS_CORTOS[d] for d in dias)} {h}" for h, dias in grupos)

    def a_dict(self) -> dict:
        d = asdict(self)
        d["horas"] = {str(k): v for k, v in self.horas.items()}
        return d

    @classmethod
    def de_dict(cls, d: dict) -> Recurrencia:
        d = dict(d)
        d["horas"] = {int(k): v for k, v in d.get("horas", {}).items() if 0 <= int(k) <= 4}
        return cls(**d)


@dataclass
class ParteDelDia:
    alumno: Alumno
    recurrencia: Recurrencia
    salida: datetime
    emitido: Salida | None  # el de hoy, si ya se emitió


class Seguimiento:
    """Lee y guarda el historial y los recurrentes; cada cambio se escribe al momento."""

    VERSION = 1

    def __init__(self, almacen):
        self._almacen = almacen
        datos = almacen.cargar_seguimiento() or {}
        self.historial: dict[str, list[Salida]] = {
            k: [Salida(**s) for s in v] for k, v in datos.get("historial", {}).items()
        }
        # Un correo que estaba saliendo cuando se cerró la app: no se sabe si llegó.
        for s in (s for v in self.historial.values() for s in v if s.correo == "enviando"):
            s.correo = "sin confirmar"
        self.recurrentes: dict[str, Recurrencia] = {
            k: Recurrencia.de_dict(v) for k, v in datos.get("recurrentes", {}).items()
        }

    def _guardar(self) -> None:
        self._almacen.guardar_seguimiento({
            "version": self.VERSION,
            "historial": {k: [asdict(s) for s in v] for k, v in self.historial.items() if v},
            "recurrentes": {k: r.a_dict() for k, r in self.recurrentes.items()},
        })

    # Historial
    def registrar(self, id_alumno: str, salida: Salida) -> Salida:
        self.historial.setdefault(id_alumno, []).append(salida)
        self._guardar()
        return salida

    def marcar_correo(self, id_alumno: str, id_salida: str, estado: str) -> None:
        for s in self.historial.get(id_alumno, []):
            if s.id == id_salida:
                s.correo = estado
                self._guardar()
                return

    def salidas(self, id_alumno: str) -> list[Salida]:
        """Del alumno, la más reciente primero."""
        return sorted(self.historial.get(id_alumno, []), key=lambda s: (s.expedido, s.salida), reverse=True)

    def vaciar_historial(self, id_alumno: str | None = None) -> int:
        """Vacía el de un alumno o, sin argumento, el de todos. Devuelve cuántas entradas."""
        if id_alumno is None:
            n = sum(len(v) for v in self.historial.values())
            self.historial.clear()
        else:
            n = len(self.historial.pop(id_alumno, []))
        self._guardar()
        return n

    @property
    def total_salidas(self) -> int:
        return sum(len(v) for v in self.historial.values())

    # Recurrentes
    def poner_recurrencia(self, id_alumno: str, recurrencia: Recurrencia | None) -> None:
        if recurrencia is None or not recurrencia.horas:
            self.recurrentes.pop(id_alumno, None)
        else:
            self.recurrentes[id_alumno] = recurrencia
        self._guardar()

    def emitido_hoy(self, id_alumno: str, dia: date) -> Salida | None:
        return next(
            (s for s in self.salidas(id_alumno) if s.recurrente and s.momento_salida.date() == dia), None
        )

    def partes_del_dia(self, dia: date, por_id: dict[str, Alumno], visibles: set[str] | None) -> list[ParteDelDia]:
        """Los recurrentes que salen ese día, solo de las etapas visibles, por hora y nombre."""
        semana = dia.weekday()
        partes = []
        for id_alumno, r in self.recurrentes.items():
            a = por_id.get(id_alumno)
            hora = r.hora(semana)
            if a is None or hora is None or (visibles is not None and a.etapa_codigo not in visibles):
                continue
            partes.append(ParteDelDia(a, r, datetime.combine(dia, hora), self.emitido_hoy(id_alumno, dia)))
        return sorted(partes, key=lambda p: (p.salida, p.alumno.nombre_listado))

    # Vida del alumno
    def conservar_solo(self, ids_vigentes) -> int:
        """Tras un Excel nuevo: fuera lo de quien ya no está. Devuelve de cuántos alumnos."""
        vigentes = set(ids_vigentes)
        fuera = (set(self.historial) | set(self.recurrentes)) - vigentes
        for i in fuera:
            self.historial.pop(i, None)
            self.recurrentes.pop(i, None)
        if fuera:
            self._guardar()
        return len(fuera)

    def olvidar_todo(self) -> None:
        self.historial.clear()
        self.recurrentes.clear()


def informe_html(alumno: Alumno, salidas: list[Salida], centro: str, ahora: datetime | None = None) -> str:
    """Historial imprimible (A4) de un alumno: cabecera, datos y una fila por salida."""
    e = html.escape
    ahora = ahora or datetime.now()
    filas = "".join(
        "<tr>"
        f"<td>{s.momento_salida:%d/%m/%Y}</td>"
        f"<td>{s.momento_salida:%H:%M}</td>"
        f"<td>{s.momento_expedido:%d/%m/%Y %H:%M}</td>"
        f"<td>{e(s.como)}</td>"
        f"<td>{e(s.avisados_texto)}</td>"
        f"<td>{e(s.correo_texto)}</td>"
        "</tr>"
        for s in salidas
    ) or '<tr><td colspan="6">Sin salidas registradas.</td></tr>'
    nia = f" · NIA {e(alumno.nia)}" if alumno.nia else ""
    return f"""<html><body style="font-family:Arial,Helvetica,sans-serif;color:#1b1f1c">
<p style="font-size:9pt;color:#5a625c;margin:0">{e(centro)} · Jefatura de Estudios</p>
<h2 style="margin:4pt 0 2pt">Historial de salidas</h2>
<p style="font-size:11pt;margin:0 0 2pt"><b>{e(alumno.nombre_listado)}</b></p>
<p style="font-size:9.5pt;margin:0 0 10pt">{e(alumno.curso)} ({e(alumno.etapa)}){nia} · {len(salidas)} salida{'s' if len(salidas) != 1 else ''}</p>
<table width="100%" cellspacing="0" cellpadding="4" border="1" style="border-collapse:collapse;font-size:9pt;border-color:#d9e0d5">
<tr style="background:#eef2ec"><th align="left">Fecha</th><th align="left">Hora de salida</th><th align="left">Expedido</th>
<th align="left">Entrega</th><th align="left">Avisados</th><th align="left">Correo</th></tr>
{filas}
</table>
<p style="font-size:8pt;color:#5a625c;margin-top:10pt">Impreso el {e(fecha_larga(ahora.date()))} a las {ahora:%H:%M}.
Documento interno de Jefatura de Estudios con datos personales: guárdese o destrúyase conforme al RGPD.</p>
</body></html>"""
