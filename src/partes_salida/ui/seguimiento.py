"""Historial de salidas de un alumno, su parte recurrente y los recurrentes del día."""

from __future__ import annotations

from datetime import date

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from ..fechas import fecha_larga
from ..impresion import imprimir_documento
from ..modelo import Alumno
from ..seguimiento import CORREO, DIAS, PAPEL, ParteDelDia, Recurrencia, Salida, informe_html
from . import estilo
from .componentes import boton, etiqueta
from .listado import Columna, TablaPaginada


def _titulo(texto: str, tam: int = 22) -> QLabel:
    t = QLabel(texto)
    t.setFont(estilo.fuente(tam, QFont.Weight.Bold, estilo.TITULAR))
    t.setWordWrap(True)
    return t


def _confirmar(padre, titulo: str, texto: str) -> bool:
    r = QMessageBox.warning(
        padre, titulo, texto,
        QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard,
        QMessageBox.StandardButton.Cancel,
    )
    return r == QMessageBox.StandardButton.Discard


def entrega_texto(entrega: str, alumno: Alumno) -> str:
    return "Por correo al alumno" if entrega == CORREO and alumno.email else "En papel"


class DialogoHistorial(QDialog):
    """Todas las salidas de un alumno: consultar, imprimir (A4) y vaciar."""

    def __init__(self, contexto, alumno: Alumno, padre=None):
        super().__init__(padre)
        self.ctx = contexto
        self.alumno = alumno
        self.setWindowTitle(f"Historial de salidas · {alumno.nombre_listado}")
        self.resize(900, 580)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 16)
        v.setSpacing(10)
        v.addWidget(_titulo(alumno.nombre_listado))
        self.subtitulo = etiqueta("", "muted")
        v.addWidget(self.subtitulo)
        self.tabla = TablaPaginada(
            [
                Columna("Fecha", lambda s: f"{s.momento_salida:%d/%m/%Y}", lambda s: s.salida, 100),
                Columna("Salida", lambda s: f"{s.momento_salida:%H:%M}", lambda s: s.salida[11:], 70),
                Columna("Expedido", lambda s: f"{s.momento_expedido:%d/%m %H:%M}", lambda s: s.expedido, 100),
                Columna("Entrega", lambda s: s.como),
                Columna("Avisados", lambda s: s.avisados_texto),
                Columna("Correo", lambda s: s.correo_texto, ancho=110),
            ],
            "salidas", lambda s: s.id, orden_inicial=(0, True), marcador="Buscar por fecha, entrega o avisados",
        )
        v.addWidget(self.tabla, 1)
        botones = QHBoxLayout()
        self.boton_vaciar = boton("Vaciar historial…", pequeno=True, peligro=True)
        self.boton_vaciar.clicked.connect(self._vaciar)
        botones.addWidget(self.boton_vaciar)
        botones.addStretch(1)
        self.boton_imprimir = boton("Imprimir…")
        self.boton_imprimir.setToolTip("Historial en A4: a una impresora o a PDF")
        self.boton_imprimir.clicked.connect(self._imprimir)
        botones.addWidget(self.boton_imprimir)
        cerrar = boton("Cerrar", primario=True)
        cerrar.clicked.connect(self.accept)
        botones.addWidget(cerrar)
        v.addLayout(botones)
        self.ctx.seguimiento_cambiado.connect(self._cargar)
        self._cargar()

    def _cargar(self) -> None:
        salidas = self.ctx.seguimiento.salidas(self.alumno.id)
        n = len(salidas)
        a = self.alumno
        self.subtitulo.setText(
            f"{a.curso} · {a.etapa} · " + (f"{n} salida{'s' if n != 1 else ''} registrada{'s' if n != 1 else ''}"
                                           if n else "Sin salidas registradas")
        )
        self.tabla.poner(salidas, resaltar=salidas[0].id if salidas else None)
        self.boton_vaciar.setEnabled(bool(n))

    def _imprimir(self) -> None:
        salidas = self.ctx.seguimiento.salidas(self.alumno.id)
        html = informe_html(self.alumno, salidas, self.ctx.gestor.valores.centro)
        imprimir_documento(html, f"Historial de salidas {self.alumno.nombre_listado}", self)

    def _vaciar(self) -> None:
        n = len(self.ctx.seguimiento.salidas(self.alumno.id))
        if _confirmar(self, "Vaciar el historial",
                      f"Se borran las {n} salidas registradas de {self.alumno.nombre_completo}. "
                      "Su parte recurrente, si lo tiene, se conserva."):
            self.ctx.seguimiento.vaciar_historial(self.alumno.id)
            self.ctx.seguimiento_cambiado.emit()


class DialogoRecurrente(QDialog):
    """Días y horas fijos de un alumno: rejilla de la semana con su hora por día."""

    def __init__(self, contexto, alumno: Alumno, padre=None):
        super().__init__(padre)
        self.ctx = contexto
        self.alumno = alumno
        actual = contexto.seguimiento.recurrentes.get(alumno.id)
        self.setWindowTitle(f"Parte recurrente · {alumno.nombre_listado}")
        self.setMinimumWidth(640)
        v = QVBoxLayout(self)
        v.setContentsMargins(22, 18, 22, 16)
        v.setSpacing(12)
        v.addWidget(_titulo("Parte recurrente"))
        v.addWidget(etiqueta(
            f"{alumno.nombre_completo} · {alumno.curso}. Marca los días en que sale y a qué hora. Se repite todas "
            "las semanas del curso hasta que lo quites; cada día sale en «Partes recurrentes» para imprimirlo o "
            "enviarlo de golpe.", "muted", envolver=True))

        semana = QFrame()
        semana.setProperty("rol", "caja")
        rejilla = QGridLayout(semana)
        rejilla.setContentsMargins(14, 12, 14, 12)
        rejilla.setHorizontalSpacing(10)
        rejilla.setVerticalSpacing(8)
        self.dias: list[QCheckBox] = []
        self.horas: list[QTimeEdit] = []
        for d, nombre in enumerate(DIAS):
            dia = boton(nombre, chip=True)
            dia.setCheckable(True)
            dia.setMinimumHeight(34)
            hora = QTimeEdit()
            hora.setDisplayFormat("HH:mm")
            hora.setAlignment(Qt.AlignmentFlag.AlignCenter)
            hora.setButtonSymbols(QTimeEdit.ButtonSymbols.NoButtons)
            hora.setFont(estilo.fuente(22, QFont.Weight.Bold, estilo.TITULAR))
            hora.setMinimumHeight(40)
            previa = actual.horas.get(d) if actual else None
            dia.setChecked(previa is not None)
            hora.setTime(QTime.fromString(previa, "HH:mm") if previa else QTime(12, 0))
            hora.setEnabled(previa is not None)
            dia.toggled.connect(lambda marcado, d=d: self._dia(d, marcado))
            rejilla.addWidget(dia, 0, d)
            rejilla.addWidget(hora, 1, d)
            self.dias.append(dia)
            self.horas.append(hora)
        v.addWidget(semana)

        comun = QHBoxLayout()
        comun.addWidget(etiqueta("Misma hora para todos los días marcados", "muted"))
        self.hora_comun = QTimeEdit()
        self.hora_comun.setDisplayFormat("HH:mm")
        self.hora_comun.setTime(QTime(12, 0))
        comun.addWidget(self.hora_comun)
        aplicar = boton("Aplicar", pequeno=True)
        aplicar.clicked.connect(self._aplicar_comun)
        comun.addWidget(aplicar)
        comun.addStretch(1)
        v.addLayout(comun)

        formulario = QGridLayout()
        formulario.setHorizontalSpacing(12)
        formulario.setVerticalSpacing(8)
        formulario.addWidget(etiqueta("Motivo"), 0, 0)
        self.motivo = QLineEdit(actual.motivo if actual else "")
        self.motivo.setPlaceholderText("Deportista de élite, conservatorio… (opcional, solo para jefatura)")
        formulario.addWidget(self.motivo, 0, 1)
        formulario.addWidget(etiqueta("Entrega del parte"), 1, 0)
        entrega = QHBoxLayout()
        self.grupo_entrega = QButtonGroup(self)
        self.papel = boton("En papel", chip=True)
        self.correo = boton("Por correo al alumno", chip=True)
        for b in (self.papel, self.correo):
            b.setCheckable(True)
            self.grupo_entrega.addButton(b)
            entrega.addWidget(b)
        self.correo.setEnabled(bool(alumno.email))
        self.correo.setToolTip(alumno.email or "Sin correo del alumno en Educamos")
        (self.correo if actual and actual.entrega == CORREO and alumno.email else self.papel).setChecked(True)
        entrega.addSpacing(6)
        entrega.addWidget(etiqueta(alumno.email or "Sin correo del alumno en Educamos", "correo"))
        entrega.addStretch(1)
        formulario.addLayout(entrega, 1, 1)
        familia = [t for t in alumno.tutores if t.puede_recibir_correo]
        self.avisar = QCheckBox(
            "Avisar a la familia por correo cada día (" + " y ".join(t.parentesco_texto.lower() for t in familia) + ")"
            if familia else "Avisar a la familia por correo (nadie de la familia recibe correos)"
        )
        self.avisar.setEnabled(bool(familia))
        self.avisar.setChecked(bool(familia) and bool(actual and actual.avisar_familia))
        formulario.addWidget(self.avisar, 2, 1)
        formulario.setColumnStretch(1, 1)
        v.addLayout(formulario)

        botones = QHBoxLayout()
        self.quitar = boton("Quitar parte recurrente", pequeno=True, peligro=True)
        self.quitar.setVisible(actual is not None)
        self.quitar.clicked.connect(self._quitar)
        botones.addWidget(self.quitar)
        botones.addStretch(1)
        cancelar = boton("Cancelar")
        cancelar.clicked.connect(self.reject)
        botones.addWidget(cancelar)
        self.guardar = boton("Guardar", primario=True)
        self.guardar.clicked.connect(self._guardar)
        botones.addWidget(self.guardar)
        v.addLayout(botones)
        self._comprobar()

    def _dia(self, d: int, marcado: bool) -> None:
        self.horas[d].setEnabled(marcado)
        self._comprobar()

    def _aplicar_comun(self) -> None:
        for dia, hora in zip(self.dias, self.horas, strict=True):
            if dia.isChecked():
                hora.setTime(self.hora_comun.time())

    def _comprobar(self) -> None:
        self.guardar.setEnabled(any(d.isChecked() for d in self.dias))

    def recurrencia(self) -> Recurrencia:
        actual = self.ctx.seguimiento.recurrentes.get(self.alumno.id)
        return Recurrencia(
            horas={d: self.horas[d].time().toString("HH:mm") for d in range(5) if self.dias[d].isChecked()},
            motivo=self.motivo.text().strip(),
            entrega=CORREO if self.correo.isChecked() else PAPEL,
            avisar_familia=self.avisar.isChecked(),
            **({"alta": actual.alta} if actual else {}),
        )

    def _guardar(self) -> None:
        self.ctx.seguimiento.poner_recurrencia(self.alumno.id, self.recurrencia())
        self.ctx.seguimiento_cambiado.emit()
        self.accept()

    def _quitar(self) -> None:
        if _confirmar(self, "Quitar el parte recurrente",
                      f"{self.alumno.nombre_completo} deja de salir en «Partes recurrentes». "
                      "Su historial de salidas se conserva."):
            self.ctx.seguimiento.poner_recurrencia(self.alumno.id, None)
            self.ctx.seguimiento_cambiado.emit()
            self.accept()


class DialogoRecurrentes(QDialog):
    """Los recurrentes de hoy para emitirlos de golpe, y la lista de todos."""

    def __init__(self, contexto, ventana, hoy: date | None = None):
        super().__init__(ventana)
        self.ctx = contexto
        self.ventana = ventana
        self.hoy = hoy or date.today()
        self.setWindowTitle("Partes recurrentes")
        self.resize(940, 600)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 16)
        v.setSpacing(10)
        v.addWidget(_titulo("Partes recurrentes"))
        v.addWidget(etiqueta(
            "Alumnos que salen los mismos días a la misma hora. Solo los de las etapas visibles en este equipo "
            "(Ajustes → Datos del alumnado). Para dar de alta uno, búscalo y pulsa «Parte recurrente» en su ficha.",
            "muted", envolver=True))
        self.pestanas = QTabWidget()
        self.pestanas.addTab(self._pestana_hoy(), "")
        self.pestanas.addTab(self._pestana_todos(), "")
        v.addWidget(self.pestanas, 1)
        cerrar = boton("Cerrar")
        cerrar.clicked.connect(self.accept)
        fila = QHBoxLayout()
        fila.addStretch(1)
        fila.addWidget(cerrar)
        v.addLayout(fila)
        self.ctx.seguimiento_cambiado.connect(self._cargar)
        self._cargar()

    # Hoy
    def _pestana_hoy(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 0)
        self.hoy_titulo = etiqueta("", "etiqueta")
        v.addWidget(self.hoy_titulo)
        self.tabla_hoy = QTableWidget(0, 7)
        self.tabla_hoy.setHorizontalHeaderLabels(["", "Hora", "Alumno", "Curso", "Entrega", "Familia", "Estado"])
        self.tabla_hoy.verticalHeader().hide()
        self.tabla_hoy.setShowGrid(False)
        self.tabla_hoy.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tabla_hoy.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        cab = self.tabla_hoy.horizontalHeader()
        for i, ancho in enumerate((34, 64, 0, 0, 150, 90, 150)):
            if ancho:
                cab.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed)
                self.tabla_hoy.setColumnWidth(i, ancho)
            else:
                cab.setSectionResizeMode(i, QHeaderView.ResizeMode.Stretch)
        self.tabla_hoy.itemChanged.connect(lambda _i: self._resumen())
        v.addWidget(self.tabla_hoy, 1)
        self.vacio_hoy = etiqueta("", "muted")
        self.vacio_hoy.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(self.vacio_hoy)
        fila = QHBoxLayout()
        pendientes = boton("Marcar los pendientes", pequeno=True)
        pendientes.clicked.connect(lambda: self._marcar(solo_pendientes=True))
        ninguno = boton("Ninguno", pequeno=True)
        ninguno.clicked.connect(lambda: self._marcar(ninguno=True))
        fila.addWidget(pendientes)
        fila.addWidget(ninguno)
        fila.addStretch(1)
        self.resumen = etiqueta("", "muted")
        fila.addWidget(self.resumen)
        v.addLayout(fila)
        self.boton_emitir = boton("", primario=True, grande=True)
        self.boton_emitir.clicked.connect(self._emitir)
        v.addWidget(self.boton_emitir)
        return w

    def partes_de_hoy(self) -> list[ParteDelDia]:
        return self.ctx.seguimiento.partes_del_dia(self.hoy, self.ctx.por_id, self.ctx.etapas_visibles())

    def _cargar(self) -> None:
        self._partes = self.partes_de_hoy()
        pendientes = sum(1 for p in self._partes if p.emitido is None)
        self.pestanas.setTabText(0, f"Hoy · {pendientes} pendiente{'s' if pendientes != 1 else ''}")
        self.hoy_titulo.setText(fecha_larga(self.hoy).capitalize())
        t = self.tabla_hoy
        t.blockSignals(True)
        t.setRowCount(len(self._partes))
        for r, p in enumerate(self._partes):
            casilla = QTableWidgetItem()
            casilla.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            casilla.setCheckState(Qt.CheckState.Unchecked if p.emitido else Qt.CheckState.Checked)
            t.setItem(r, 0, casilla)
            estado = (f"Emitido a las {p.emitido.momento_expedido:%H:%M}" if p.emitido else "Pendiente")
            familia = "Sí" if p.recurrencia.avisar_familia and any(x.puede_recibir_correo for x in p.alumno.tutores) \
                else "No"
            for c, texto in enumerate((f"{p.salida:%H:%M}", p.alumno.nombre_listado, p.alumno.curso,
                                       entrega_texto(p.recurrencia.entrega, p.alumno), familia, estado), start=1):
                item = QTableWidgetItem(texto)
                if c == 1:
                    item.setFont(estilo.fuente(14, QFont.Weight.Bold))
                t.setItem(r, c, item)
        t.blockSignals(False)
        t.setVisible(bool(self._partes))
        fin_de_semana = self.hoy.weekday() > 4
        self.vacio_hoy.setText(
            "" if self._partes else
            ("Hoy es fin de semana: no hay partes recurrentes." if fin_de_semana
             else "Hoy no sale ningún alumno con parte recurrente.")
        )
        self.vacio_hoy.setVisible(not self._partes)
        self._resumen()
        self._cargar_todos()

    def marcados(self) -> list[ParteDelDia]:
        return [p for r, p in enumerate(self._partes)
                if self.tabla_hoy.item(r, 0) and self.tabla_hoy.item(r, 0).checkState() == Qt.CheckState.Checked]

    def _marcar(self, solo_pendientes: bool = False, ninguno: bool = False) -> None:
        for r, p in enumerate(self._partes):
            marcar = not ninguno and (p.emitido is None or not solo_pendientes)
            self.tabla_hoy.item(r, 0).setCheckState(Qt.CheckState.Checked if marcar else Qt.CheckState.Unchecked)

    def _resumen(self) -> None:
        marcados = self.marcados()
        papel = sum(1 for p in marcados if not (p.recurrencia.entrega == CORREO and p.alumno.email))
        correo = len(marcados) - papel
        partes = []
        if papel:
            partes.append(f"imprimir {papel} (uno por hoja)")
        if correo:
            partes.append(f"enviar {correo} por correo")
        self.boton_emitir.setText(
            ("Emitir: " + " y ".join(partes)).replace("Emitir: imprimir", "Imprimir").replace("Emitir: enviar", "Enviar")
            if partes else "Marca los partes que quieras emitir"
        )
        self.boton_emitir.setEnabled(bool(marcados))
        ya = sum(1 for p in marcados if p.emitido)
        self.resumen.setText(f"{ya} ya emitido{'s' if ya != 1 else ''} hoy: saldría otra vez" if ya else "")

    def _emitir(self) -> None:
        marcados = self.marcados()
        if not marcados:
            return
        emisiones = [
            self.ventana.emision(
                p.alumno, p.salida,
                CORREO if p.recurrencia.entrega == CORREO and p.alumno.email else PAPEL,
                [t for t in p.alumno.tutores if t.puede_recibir_correo] if p.recurrencia.avisar_familia else [],
                recurrente=True,
            )
            for p in marcados
        ]
        self.ventana.emitir_partes(emisiones, padre=self)

    # Todos
    def _pestana_todos(self) -> QWidget:
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(0, 12, 0, 0)
        self.tabla_todos = TablaPaginada(
            [
                Columna("Alumno", lambda f: f[0].nombre_listado),
                Columna("Curso", lambda f: f[0].curso, ancho=150),
                Columna("Días y horas", lambda f: f[1].resumen, ancho=190),
                Columna("Entrega", lambda f: entrega_texto(f[1].entrega, f[0]), ancho=150),
                Columna("Familia", lambda f: "Sí" if f[1].avisar_familia else "No", ancho=70),
                Columna("Motivo", lambda f: f[1].motivo or "—"),
            ],
            "alumnos", lambda f: f[0].id, orden_inicial=(0, False), marcador="Buscar por nombre, curso o motivo",
        )
        self.tabla_todos.elegida.connect(lambda f: self._botones_todos(f is not None))
        self.tabla_todos.activada.connect(lambda f: f and self._editar(f))
        v.addWidget(self.tabla_todos, 1)
        fila = QHBoxLayout()
        self.boton_quitar = boton("Quitar", pequeno=True, peligro=True)
        self.boton_quitar.clicked.connect(lambda: self._quitar(self.tabla_todos.seleccionada()))
        fila.addWidget(self.boton_quitar)
        fila.addStretch(1)
        self.boton_editar = boton("Editar…", pequeno=True)
        self.boton_editar.clicked.connect(lambda: self._editar(self.tabla_todos.seleccionada()))
        fila.addWidget(self.boton_editar)
        v.addLayout(fila)
        self._botones_todos(False)
        return w

    def filas_todos(self) -> list[tuple[Alumno, Recurrencia]]:
        visibles = self.ctx.etapas_visibles()
        return [
            (self.ctx.por_id[i], r) for i, r in self.ctx.seguimiento.recurrentes.items()
            if i in self.ctx.por_id and (visibles is None or self.ctx.por_id[i].etapa_codigo in visibles)
        ]

    def _cargar_todos(self) -> None:
        filas = self.filas_todos()
        self.pestanas.setTabText(1, f"Todos · {len(filas)}")
        self.tabla_todos.poner(filas)

    def _botones_todos(self, hay: bool) -> None:
        self.boton_editar.setEnabled(hay)
        self.boton_quitar.setEnabled(hay)

    def _editar(self, fila) -> None:
        if fila:
            d = DialogoRecurrente(self.ctx, fila[0], self)
            d.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            d.exec()

    def _quitar(self, fila) -> None:
        if fila and _confirmar(self, "Quitar el parte recurrente",
                               f"{fila[0].nombre_completo} deja de salir en «Partes recurrentes». "
                               "Su historial de salidas se conserva."):
            self.ctx.seguimiento.poner_recurrencia(fila[0].id, None)
            self.ctx.seguimiento_cambiado.emit()


def resumen_historial(salidas: list[Salida]) -> str:
    if not salidas:
        return "Sin salidas registradas"
    n, ultima = len(salidas), salidas[0].momento_salida
    return f"{n} salida{'s' if n != 1 else ''} · última {ultima:%d/%m/%Y} {ultima:%H:%M}"

