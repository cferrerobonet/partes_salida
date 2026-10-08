"""Ventana de Ajustes: cada cambio se guarda al momento."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import QSize, Qt, QTimer
from PyQt6.QtGui import QColor, QFont, QGuiApplication, QImage, QPainter, QPixmap
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QProgressDialog,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from .. import __version__
from ..ajustes import TEXTO_ALUMNA, TEXTO_ALUMNO
from ..cifrado import guardar_secreto
from ..correo import construir_mensaje, contrasena_smtp, enviar, nombre_secreto_smtp
from ..importar_excel import importar_excel
from ..importar_fotos import importar_fotos
from ..impresion import impresoras, imprimir, parte_de_prueba
from ..modelo import ETAPA_CORTA, Alumno
from ..rutas import carpeta_datos
from ..sistema import arranque_con_sistema
from . import estilo
from .ayuda import AYUDA_EXCEL, AYUDA_FOTOS, DialogoAyuda
from .componentes import FlujoLayout, Miniatura, Tarea, ZonaSoltar, boton, etiqueta

logger = logging.getLogger(__name__)

def enviar_a_papelera(ruta: str) -> bool:
    from PyQt6.QtCore import QFile

    resultado = QFile.moveToTrash(ruta)
    return bool(resultado[0] if isinstance(resultado, tuple) else resultado)


APARTADOS = [
    "Logos e identidad",
    "Sello y firma",
    "Textos del parte",
    "Datos del alumnado",
    "Correo",
    "Impresión",
    "QR y verificación",
    "General",
]
IMAGENES = "Imágenes (*.png *.jpg *.jpeg *.svg *.webp)"


class Apartado(QScrollArea):
    """Página de Ajustes: título y, debajo, filas «etiqueta | control» o bloques sueltos."""

    def __init__(self, titulo: str):
        super().__init__()
        self.setWidgetResizable(True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        contenido = QWidget()
        contenido.setObjectName("pagina")
        self.setWidget(contenido)
        self.capa = QVBoxLayout(contenido)
        self.capa.setContentsMargins(22, 18, 22, 18)
        self.capa.setSpacing(16)
        t = QLabel(titulo)
        t.setFont(estilo.fuente(23, QFont.Weight.Bold, estilo.TITULAR))
        self.capa.addWidget(t)
        self.rejilla: QGridLayout | None = None
        self._fila = 0

    def poner(self, elemento) -> None:
        """Bloque a todo el ancho (zona de importación, botones…)."""
        self.rejilla = None
        if isinstance(elemento, QWidget):
            self.capa.addWidget(elemento)
        else:
            self.capa.addLayout(elemento)

    def _rejilla(self) -> QGridLayout:
        if self.rejilla is None:
            self.rejilla = QGridLayout()
            self.rejilla.setHorizontalSpacing(18)
            self.rejilla.setVerticalSpacing(12)
            self.rejilla.setColumnMinimumWidth(0, 190)
            self.rejilla.setColumnStretch(1, 1)
            self.capa.addLayout(self.rejilla)
            self._fila = 0
        return self.rejilla

    def campo(self, texto: str, control, ayuda: str = "") -> None:
        rejilla = self._rejilla()
        e = QLabel(texto)
        e.setStyleSheet("font-weight:600;")
        arriba = isinstance(control, (QPlainTextEdit, QWidget)) and not isinstance(control, (QLineEdit, QCheckBox, QComboBox))
        rejilla.addWidget(e, self._fila, 0, Qt.AlignmentFlag.AlignTop if arriba else Qt.AlignmentFlag.AlignVCenter)
        if isinstance(control, QWidget):
            rejilla.addWidget(control, self._fila, 1)
        else:
            rejilla.addLayout(control, self._fila, 1)
        self._fila += 1
        if ayuda:
            rejilla.addWidget(etiqueta(ayuda, "pequeno", envolver=True), self._fila, 1)
            self._fila += 1

    def separador(self) -> None:
        linea = QFrame()
        linea.setObjectName("separador")
        linea.setFixedHeight(1)
        self._rejilla().addWidget(linea, self._fila, 0, 1, 2)
        self._fila += 1

    def fin(self) -> None:
        self.capa.addStretch(1)


def _fila(*widgets, estirar: bool = True) -> QHBoxLayout:
    f = QHBoxLayout()
    f.setSpacing(10)
    for w in widgets:
        f.addWidget(w)
    if estirar:
        f.addStretch(1)
    return f


class DialogoAjustes(QDialog):
    def __init__(self, contexto, padre=None, apartado: str | None = None):
        super().__init__(padre)
        self.ctx = contexto
        self.g = contexto.gestor
        self._tareas: list[Tarea] = []
        self.ultimo_informe = None
        self.setWindowTitle("Ajustes")
        self.resize(980, 640)
        capa = QHBoxLayout(self)
        capa.setContentsMargins(0, 0, 0, 0)
        capa.setSpacing(0)
        self.nav = QListWidget()
        self.nav.setObjectName("navegacion")
        self.nav.setFixedWidth(220)
        self.nav.setFont(estilo.fuente(14, QFont.Weight.DemiBold))
        for nombre in APARTADOS:
            item = QListWidgetItem(nombre)
            item.setSizeHint(QSize(0, 38))
            self.nav.addItem(item)
        capa.addWidget(self.nav)
        self.pila = QStackedWidget()
        self.pila.setStyleSheet(f"QStackedWidget, QWidget#pagina {{ background: {estilo.T['surface']}; }}")
        capa.addWidget(self.pila, 1)
        for crear in (
            self._logos, self._sello, self._textos, self._datos, self._correo, self._impresion, self._qr, self._general,
        ):
            self.pila.addWidget(crear())
        self.nav.currentRowChanged.connect(self.pila.setCurrentIndex)
        self.nav.setCurrentRow(APARTADOS.index(apartado) if apartado in APARTADOS else 0)

    # Utilidades de enlace
    def _texto(self, clave: str, ancho: int | None = None, marcador: str = "") -> QLineEdit:
        campo = QLineEdit(str(getattr(self.g.valores, clave)))
        campo.setPlaceholderText(marcador)
        if ancho:
            campo.setMaximumWidth(ancho)
        campo.editingFinished.connect(lambda: self.g.poner(**{clave: campo.text().strip()}))
        return campo

    def _parrafo(self, clave: str) -> QPlainTextEdit:
        campo = QPlainTextEdit(getattr(self.g.valores, clave))
        campo.setFixedHeight(68)
        temporizador = QTimer(campo, singleShot=True, interval=400)
        temporizador.timeout.connect(lambda: self.g.poner(**{clave: campo.toPlainText().strip()}))
        campo.textChanged.connect(temporizador.start)
        return campo

    def _casilla(self, texto: str, clave: str, tras=None) -> QCheckBox:
        c = QCheckBox(texto)
        c.setChecked(bool(getattr(self.g.valores, clave)))

        def cambio(v):
            self.g.poner(**{clave: v})
            if tras:
                tras(v)

        c.toggled.connect(cambio)
        return c

    def _hueco_imagen(self, nombre: str, texto_cambiar: str, quitar: str, pendiente: str = "Pendiente") -> QHBoxLayout:
        mini = Miniatura()
        mini.poner(self.g.ruta_imagen(nombre), pendiente)
        cambiar = boton(texto_cambiar, pequeno=True)
        quitar_b = boton(quitar, pequeno=True)

        def elegir():
            ruta, _ = QFileDialog.getOpenFileName(self, texto_cambiar.rstrip("…"), str(Path.home()), IMAGENES)
            if ruta:
                try:
                    self.g.poner_imagen(nombre, ruta)
                except Exception as e:  # noqa: BLE001
                    QMessageBox.warning(self, "Imagen no válida", f"No se puede usar esa imagen:\n{e}")
                    return
                mini.poner(self.g.ruta_imagen(nombre), pendiente)

        def borrar():
            self.g.quitar_imagen(nombre)
            mini.poner(self.g.ruta_imagen(nombre), pendiente)

        cambiar.clicked.connect(elegir)
        quitar_b.clicked.connect(borrar)
        return _fila(mini, cambiar, quitar_b)

    # Apartados
    def _logos(self) -> QWidget:
        ap = Apartado("Logos e identidad")
        ap.campo("Logo esquina izquierda", self._hueco_imagen("logo_izquierdo", "Cambiar…", "Restaurar"))
        ap.campo(
            "Logo esquina derecha",
            self._hueco_imagen("logo_derecho", "Cambiar…", "Restaurar"),
            "Por defecto, el escudo de EPLA y Colegios Amigó. Se puede poner cualquier imagen (PNG, JPG o SVG; "
            "mejor con fondo transparente) y sale en el parte y en la cabecera del correo.",
        )
        ap.campo("Nombre del centro", self._texto("centro"))
        ap.campo("Localidad del pie", self._texto("localidad", 320))
        ap.fin()
        return ap

    def _sello(self) -> QWidget:
        ap = Apartado("Sello y firma")
        ap.campo(
            "Sello de la etapa",
            self._hueco_imagen("sello", "Cambiar…", "Quitar", "Pendiente:\nfalta el sello"),
            "Cada etapa pone el suyo. Al subirlo se le quita el fondo blanco para que la firma se vea encima.",
        )
        ap.campo(
            "Firma del Jefe de Estudios",
            self._hueco_imagen("firma", "Subir firma…", "Quitar", "Pendiente:\nfalta la firma"),
            "Una foto o escaneo de la firma sobre papel blanco.",
        )
        ap.campo("Texto bajo la firma", self._texto("cargo_firma"))
        ap.fin()
        return ap

    def _textos(self) -> QWidget:
        ap = Apartado("Textos del parte")
        titulo = self._texto("titulo")
        ap.campo("Título", titulo)
        alumna = self._parrafo("texto_alumna")
        alumno = self._parrafo("texto_alumno")
        ap.campo("Texto (alumna)", alumna)
        ap.campo(
            "Texto (alumno)",
            alumno,
            "Dos líneas. Variables: {hora}, {nombre}, {curso}, {etapa} y {fecha}. El género sale de la columna SEXO.",
        )
        restaurar = boton("Restaurar los textos", pequeno=True)

        def volver():
            alumna.setPlainText(TEXTO_ALUMNA)
            alumno.setPlainText(TEXTO_ALUMNO)
            titulo.setText("AUTORIZACIÓN DE SALIDA")
            self.g.poner(texto_alumna=TEXTO_ALUMNA, texto_alumno=TEXTO_ALUMNO, titulo="AUTORIZACIÓN DE SALIDA")

        restaurar.clicked.connect(volver)
        ap.campo("", _fila(restaurar))
        ap.fin()
        return ap

    def _datos(self) -> QWidget:
        ap = Apartado("Datos del alumnado")
        self.zona_excel = ZonaSoltar(
            "Excel del alumnado (exportación de Educamos)", "", "Importar Excel…", (".xls", ".xlsx"), "▤"
        )
        self.zona_excel.con_ayuda(lambda: self._ayuda(AYUDA_EXCEL))
        self.zona_excel.boton.clicked.connect(self._elegir_excel)
        self.zona_excel.archivos.connect(lambda r: self._importar_excel(r[0]))
        ap.poner(self.zona_excel)
        self.zona_fotos = ZonaSoltar(
            "Fotos (uno o varios ZIP, con subcarpetas)",
            "Archivos «APELLIDOS, NOMBRE.png» o .jpg, en las carpetas que sea. Sustituyen a las que había y se "
            "añaden las nuevas; las que no son de ningún alumno se ignoran.",
            "Importar ZIP…", (".zip",), "◩",
        )
        self.zona_fotos.con_ayuda(lambda: self._ayuda(AYUDA_FOTOS))
        self.zona_fotos.boton.clicked.connect(self._elegir_zips)
        self.zona_fotos.archivos.connect(self._importar_fotos)
        ap.poner(self.zona_fotos)
        cifras = QHBoxLayout()
        cifras.setSpacing(8)
        self.cifras: dict[str, QLabel] = {}
        for clave, texto, color in (
            ("alumnos", "alumnos", None), ("con_foto", "con foto", "accent"),
            ("dudosas", "por confirmar", "warn"), ("sobrantes", "fotos sobrantes (se ignoran)", None),
        ):
            caja = QFrame()
            caja.setProperty("rol", "dato")
            c = QVBoxLayout(caja)
            c.setContentsMargins(12, 9, 12, 9)
            c.setSpacing(0)
            n = QLabel("—")
            n.setFont(estilo.fuente(26, QFont.Weight.Bold, estilo.TITULAR))
            if color:
                n.setStyleSheet(f"color:{estilo.T[color]};")
            c.addWidget(n)
            c.addWidget(etiqueta(texto, "pequeno"))
            self.cifras[clave] = n
            cifras.addWidget(caja, 1)
        ap.poner(cifras)
        self.boton_revisar = boton("Revisar las parecidas…", pequeno=True)
        self.boton_revisar.clicked.connect(self._revisar)
        ap.poner(_fila(self.boton_revisar))
        self.etapas_widget = QWidget()
        self.caja_etapas = FlujoLayout(self.etapas_widget, 14)
        ap.campo(
            "Etapas detectadas",
            self.etapas_widget,
            "Se crean solas a partir de la columna CLASE del Excel. Desmarca las que no deban salir en el buscador "
            "de este equipo.",
        )
        candado = QLabel()
        candado.setPixmap(estilo.icono_candado(estilo.T["accent"]))
        ap.campo(
            "Cifrado",
            _fila(candado, etiqueta("Activo", "cifrado"), etiqueta("· AES-256-GCM, clave en el llavero del sistema")),
            "Del Excel solo se guardan nombre, sexo, clase, NIA, fecha de nacimiento, teléfonos y, de cada familiar, "
            "nombre, parentesco, correo y teléfono. DNI, IBAN, tarjeta sanitaria y direcciones se descartan.",
        )
        borrar = boton("Vaciar todos los datos del alumnado…", pequeno=True, peligro=True)
        borrar.clicked.connect(self._borrar_datos)
        ap.campo("Fin de curso", _fila(borrar),
                 "Borra el padrón y todas las fotos de este equipo para empezar de cero (por ejemplo, en septiembre). "
                 "Los ajustes, el sello y la firma se conservan.")
        ap.fin()
        self._refrescar_datos()
        return ap

    def _correo(self) -> QWidget:
        ap = Apartado("Correo")
        ap.campo("Servidor", self._texto("smtp_servidor"))
        puerto = QSpinBox()
        puerto.setRange(1, 65535)
        puerto.setValue(int(self.g.valores.smtp_puerto))
        puerto.setMaximumWidth(110)
        puerto.valueChanged.connect(lambda v: self.g.poner(smtp_puerto=v))
        ap.campo("Puerto", puerto, "587 con STARTTLS (o 465 con SSL).")
        usuario = self._texto("smtp_usuario")
        ap.campo("Remitente", usuario)
        clave = QLineEdit()
        clave.setEchoMode(QLineEdit.EchoMode.Password)

        def marcador():
            clave.setPlaceholderText("Guardada en el llavero" if contrasena_smtp(self.g.valores) else "Pendiente")

        marcador()

        def guardar_clave():
            if clave.text():
                guardar_secreto(nombre_secreto_smtp(self.g.valores.smtp_usuario), clave.text())
                clave.clear()
                marcador()

        clave.editingFinished.connect(guardar_clave)
        usuario.editingFinished.connect(marcador)
        ap.campo("Contraseña", clave, "Se guarda en el llavero del sistema, nunca en archivos ni en el repositorio.")
        ap.campo("Nombre que ve la familia", self._texto("remitente_nombre"))
        ap.separador()
        ap.campo("Jefatura · mañana", _fila(self._texto("contacto_manana_email", marcador="Correo"),
                                           self._texto("contacto_manana_tel", 170, "Teléfono"), estirar=False))
        ap.campo("Jefatura · tarde", _fila(self._texto("contacto_tarde_email", marcador="Correo"),
                                          self._texto("contacto_tarde_tel", 170, "Teléfono"), estirar=False),
                 "Salen al pie del correo para que la familia sepa a quién llamar. Si uno queda vacío, no se muestra.")
        ap.separador()
        self.destino_prueba = QLineEdit()
        self.destino_prueba.setPlaceholderText("tu.correo@epla.es")
        prueba = boton("Enviar prueba", pequeno=True)
        prueba.clicked.connect(self._correo_prueba)
        self.destino_prueba.returnPressed.connect(self._correo_prueba)
        ap.campo("Correo de prueba", _fila(self.destino_prueba, prueba, estirar=False),
                 "Envía un aviso de ejemplo (alumna ficticia) a la dirección que escribas, no a las familias ni a "
                 "jefatura, para comprobar que el correo sale bien.")
        ap.fin()
        return ap

    def _impresion(self) -> QWidget:
        ap = Apartado("Impresión")
        combo = QComboBox()
        combo.addItem("Preguntar cada vez", "")
        for nombre in impresoras():
            combo.addItem(nombre, nombre)
        actual = combo.findData(self.g.valores.impresora)
        combo.setCurrentIndex(max(actual, 0))
        combo.currentIndexChanged.connect(lambda: self.g.poner(impresora=combo.currentData() or ""))
        ap.campo("Impresora", combo, "La de la bandeja A6.")
        orientacion = QComboBox()
        orientacion.addItem("Horizontal (148 × 105 mm)", "horizontal")
        orientacion.addItem("Vertical (105 × 148 mm)", "vertical")
        orientacion.setCurrentIndex(max(orientacion.findData(self.g.valores.orientacion), 0))
        orientacion.currentIndexChanged.connect(lambda: self.g.poner(orientacion=orientacion.currentData()))
        orientacion.setMaximumWidth(280)
        ap.campo("Orientación del parte", orientacion,
                 "El mismo contenido en las dos: en vertical, la hora pasa a una franja a todo el ancho. "
                 "La vista previa y el parte de prueba la siguen.")
        ap.campo("Al pulsar «Imprimir»", self._casilla("Imprimir directamente, sin el diálogo del sistema", "imprimir_directo"))
        x, y = QDoubleSpinBox(), QDoubleSpinBox()
        for spin, clave in ((x, "ajuste_x_mm"), (y, "ajuste_y_mm")):
            spin.setRange(-10, 10)
            spin.setSingleStep(0.5)
            spin.setSuffix(" mm")
            spin.setValue(float(getattr(self.g.valores, clave)))
            spin.setMaximumWidth(110)
            spin.valueChanged.connect(lambda v, clave=clave: self.g.poner(**{clave: v}))
        prueba = boton("Imprimir parte de prueba", pequeno=True)
        prueba.clicked.connect(self._imprimir_prueba)
        ap.campo("Ajuste fino", _fila(etiqueta("Horizontal"), x, etiqueta("Vertical"), y, prueba),
                 "Si el parte sale desplazado, corrige aquí y vuelve a probar. Positivo: a la derecha y abajo.")
        ap.fin()
        return ap

    def _qr(self) -> QWidget:
        ap = Apartado("QR y verificación")
        ap.campo("Contenido del QR", etiqueta("NIA · fecha y hora de salida · hora de expedición · firma digital", envolver=True))
        ap.campo("Firma digital", etiqueta(
            f"Ed25519. La clave privada no sale de este equipo (llavero). Identificador: {self.ctx.firmante.id_clave}",
            envolver=True))
        nombre = self._texto("nombre_equipo", 360, "Jefatura de Estudios de FP")
        imagen = QLabel()
        imagen.setFixedSize(176, 176)
        imagen.setStyleSheet("background:#ffffff;border-radius:8px;")

        def pintar():
            imagen.setPixmap(self._qr_pixmap(self.ctx.firmante.qr_de_clave(self.g.valores.nombre_equipo), 176))

        nombre.editingFinished.connect(pintar)
        pintar()
        ap.campo("Nombre de este equipo", nombre, "Es el nombre que verá el vigilante al comprobar un parte.")
        copiar = boton("Copiar la clave pública", pequeno=True)
        copiar.clicked.connect(lambda: QGuiApplication.clipboard().setText(
            self.ctx.firmante.qr_de_clave(self.g.valores.nombre_equipo)))
        explica = etiqueta(
            "La app del vigilante escaneará este código una vez para fiarse de los partes de este equipo. "
            "Un QR alterado o hecho fuera de aquí sale como falso.", "muted", envolver=True)
        columna = QVBoxLayout()
        columna.addWidget(explica)
        columna.addWidget(copiar, 0, Qt.AlignmentFlag.AlignLeft)
        columna.addStretch(1)
        caja = QHBoxLayout()
        caja.setSpacing(16)
        caja.addWidget(imagen)
        caja.addLayout(columna, 1)
        ap.campo("Clave para el vigilante", caja)
        ap.fin()
        return ap

    def _general(self) -> QWidget:
        ap = Apartado("General")
        ap.campo("Al iniciar sesión", self._casilla(
            "Abrir la app en segundo plano", "arrancar_con_sistema", tras=lambda v: arranque_con_sistema(v)),
            "Queda en la barra de menús (Mac) o en la bandeja (Windows), lista para usar.")
        ap.campo("Ventana", self._casilla("Siempre encima de las demás", "siempre_encima"))
        exportar = boton("Exportar ajustes…", pequeno=True)
        importar = boton("Importar ajustes…", pequeno=True)
        exportar.clicked.connect(self._exportar)
        importar.clicked.connect(self._importar_ajustes)
        ap.campo("Copia de ajustes", _fila(exportar, importar),
                 "Logos, sello, firma, textos, correo e impresora. Sin datos del alumnado ni contraseñas.")
        buscar = boton("Buscar actualizaciones", pequeno=True)
        buscar.clicked.connect(self._buscar_actualizaciones)
        acerca = boton("Acerca de…", pequeno=True)
        acerca.clicked.connect(self._acerca_de)
        ap.campo("Versión", _fila(etiqueta(__version__), buscar, acerca))
        ruta = etiqueta(str(carpeta_datos()), "pequeno", envolver=True)
        ruta.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        ap.campo("Carpeta de datos", ruta)
        ap.fin()
        return ap

    # Datos del alumnado
    def _refrescar_datos(self) -> None:
        ctx = self.ctx
        if ctx.hay_datos:
            fecha = ctx.importado.replace("T", " ")[:16]
            self.zona_excel.explicacion.setText(
                f"Último: {ctx.origen} · {fecha} · {len(ctx.alumnos):,} alumnos en "
                f"{len({a.clase for a in ctx.alumnos})} clases. Sustituye por completo al anterior.".replace(",", ".")
            )
        else:
            self.zona_excel.explicacion.setText("Todavía no hay datos. Arrastra aquí el Excel o pulsa el botón.")
        self.cifras["alumnos"].setText(f"{len(ctx.alumnos):,}".replace(",", ".") if ctx.hay_datos else "—")
        self.cifras["con_foto"].setText(f"{ctx.con_foto:,}".replace(",", ".") if ctx.hay_datos else "—")
        inf = self.ultimo_informe
        self.cifras["dudosas"].setText(str(len(inf.dudosas)) if inf else "—")
        self.cifras["sobrantes"].setText(str(inf.sobrantes) if inf else "—")
        self.boton_revisar.setVisible(bool(inf and inf.dudosas))
        if inf and inf.dudosas:
            n = len(inf.dudosas)
            self.boton_revisar.setText("Revisar la foto parecida…" if n == 1 else f"Revisar las {n} parecidas…")
        while self.caja_etapas.count():
            w = self.caja_etapas.takeAt(0).widget()
            if w:
                w.setParent(None)
                w.deleteLater()
        ocultas = set(self.g.valores.etapas_ocultas)
        for cod in ctx.etapas:
            c = QCheckBox(ETAPA_CORTA.get(cod, cod))
            c.setChecked(cod not in ocultas)
            c.toggled.connect(lambda v, cod=cod: self._etapa(cod, v))
            self.caja_etapas.addWidget(c)
        if not ctx.etapas:
            self.caja_etapas.addWidget(etiqueta("Aparecerán al importar el Excel.", "muted"))
        self.etapas_widget.updateGeometry()

    def _etapa(self, cod: str, visible: bool) -> None:
        ocultas = set(self.g.valores.etapas_ocultas)
        (ocultas.discard if visible else ocultas.add)(cod)
        self.g.poner(etapas_ocultas=sorted(ocultas))

    def _progreso(self, titulo: str) -> QProgressDialog:
        p = QProgressDialog(titulo, None, 0, 0, self)
        p.setWindowTitle("Importando")
        p.setWindowModality(Qt.WindowModality.WindowModal)
        p.setMinimumDuration(0)
        p.setMinimumWidth(420)
        p.show()
        return p

    def _lanzar(self, tarea: Tarea, progreso: QProgressDialog) -> None:
        tarea.finished.connect(progreso.close)
        tarea.finished.connect(lambda: self._tareas.remove(tarea))
        tarea.fallo.connect(lambda e: QMessageBox.warning(self, "No se ha podido importar", e))
        self._tareas.append(tarea)
        tarea.start()

    def _elegir_excel(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Excel del alumnado", str(Path.home()), "Excel (*.xls *.xlsx)")
        if ruta:
            self._importar_excel(ruta)

    def _importar_excel(self, ruta: str) -> None:
        progreso = self._progreso("Leyendo el Excel…")
        tarea = Tarea(lambda _p: importar_excel(ruta))

        def listo(resultado):
            borradas = self.ctx.nuevo_padron(resultado.alumnos, Path(ruta).name)
            self.ultimo_informe = None
            self._refrescar_datos()
            texto = (f"{len(resultado.alumnos):,} alumnos de {resultado.clases} clases importados y cifrados.\n"
                     f"Columnas usadas: {resultado.columnas_leidas} de {resultado.columnas_total}.").replace(",", ".")
            if borradas:
                texto += f"\nSe han borrado {borradas} fotos de alumnos que ya no están."
            if resultado.avisos:
                texto += "\n\n" + "\n".join(resultado.avisos)
            if not self.ctx.con_foto:
                texto += "\n\nAhora importa los ZIP con las fotos."
            QMessageBox.information(self, "Excel importado", texto)
            self._ofrecer_papelera([ruta], "el Excel")

        tarea.terminado.connect(listo)
        self._lanzar(tarea, progreso)

    def _elegir_zips(self) -> None:
        rutas, _ = QFileDialog.getOpenFileNames(self, "ZIP con las fotos", str(Path.home()), "ZIP (*.zip)")
        if rutas:
            self._importar_fotos(rutas)

    def _importar_fotos(self, rutas: list[str]) -> None:
        if not self.ctx.hay_datos:
            QMessageBox.information(self, "Primero el Excel", "Importa antes el Excel del alumnado: las fotos se casan con él.")
            return
        progreso = self._progreso("Leyendo las fotos…")
        tarea = Tarea(lambda avance: importar_fotos(rutas, self.ctx.alumnos, self.ctx.almacen, avance))
        tarea.progreso.connect(lambda h, t, n: (progreso.setMaximum(t), progreso.setValue(h)))

        def listo(informe):
            self.ultimo_informe = informe
            self.ctx.fotos_cambiadas()
            self._refrescar_datos()
            texto = (f"{informe.leidas} fotos leídas: {informe.asignadas} asignadas, "
                     f"{len(informe.dudosas)} por confirmar y {informe.sobrantes} sobrantes (se ignoran).")
            if informe.errores:
                texto += f"\n\nNo se han podido leer: {', '.join(informe.errores[:8])}"
            QMessageBox.information(self, "Fotos importadas", texto)
            if informe.dudosas:
                self._revisar()
            self._ofrecer_papelera(rutas, "el ZIP" if len(rutas) == 1 else "los ZIP")

        tarea.terminado.connect(listo)
        self._lanzar(tarea, progreso)

    def _revisar(self) -> None:
        from .dialogos import RevisarFotos

        inf = self.ultimo_informe
        if not inf or not inf.dudosas:
            return
        dialogo = RevisarFotos(inf.dudosas, self)
        if dialogo.exec() == QDialog.DialogCode.Accepted:
            elegidas = dialogo.elegidas()
            for d in elegidas:
                self.ctx.almacen.guardar_foto(d.id_alumno, d.jpeg)
            inf.dudosas = [d for d in inf.dudosas if d not in elegidas]
            inf.asignadas += len(elegidas)
            self.ctx.fotos_cambiadas()
            self._refrescar_datos()

    def _ayuda(self, ayuda) -> None:
        DialogoAyuda(ayuda, self).exec()

    def _ofrecer_papelera(self, rutas: list[str], que: str) -> None:
        """Tras cifrar, el original sobra y tiene datos sensibles (RGPD): a la papelera."""
        existentes = [r for r in rutas if Path(r).exists()]
        if not existentes:
            return
        caja = QMessageBox(self)
        caja.setIcon(QMessageBox.Icon.Warning)
        caja.setWindowTitle("Proteger los datos")
        caja.setText(f"Los datos ya están cifrados en la app. ¿Envío {que} a la papelera?")
        caja.setInformativeText(
            "Contiene datos personales del alumnado y no hace falta conservarlo (RGPD). "
            "Después, vacía la papelera.\n\n" + "\n".join(Path(r).name for r in existentes)
        )
        enviar = caja.addButton("Enviar a la papelera", QMessageBox.ButtonRole.AcceptRole)
        caja.addButton("Lo borraré yo", QMessageBox.ButtonRole.RejectRole)
        caja.setDefaultButton(enviar)
        caja.exec()
        if caja.clickedButton() is not enviar:
            return
        fallidos = [Path(r).name for r in existentes if not enviar_a_papelera(r)]
        if fallidos:
            QMessageBox.warning(self, "No se ha podido", "Bórralo a mano: " + ", ".join(fallidos))

    def _borrar_datos(self) -> None:
        r = QMessageBox.warning(
            self, "Borrar los datos del alumnado",
            "Se borran el padrón y todas las fotos de este equipo. Los ajustes, el sello y la firma se conservan.\n\n"
            "Para volver a tener datos habrá que importar el Excel y los ZIP del curso nuevo.",
            QMessageBox.StandardButton.Cancel | QMessageBox.StandardButton.Discard,
            QMessageBox.StandardButton.Cancel,
        )
        if r == QMessageBox.StandardButton.Discard:
            self.ctx.borrar_datos()
            self.ultimo_informe = None
            self._refrescar_datos()

    # Correo, impresión y general
    def _correo_prueba(self) -> None:
        clave = contrasena_smtp(self.g.valores)
        if not clave:
            QMessageBox.information(self, "Falta la contraseña", "Escribe antes la contraseña del correo.")
            return
        destino = self.destino_prueba.text().strip()
        if "@" not in destino or "." not in destino.split("@")[-1]:
            QMessageBox.information(self, "Correo de prueba", "Escribe la dirección a la que enviar la prueba.")
            self.destino_prueba.setFocus()
            return
        ahora = datetime.now().replace(second=0, microsecond=0)
        prueba = Alumno(id="0", nombre="ALUMNA", apellido1="DE", apellido2="PRUEBA", sexo="F", clase="1CFS-SEA")
        mensaje = construir_mensaje(self.g, prueba, ahora, [destino.strip()])
        progreso = self._progreso("Enviando el correo de prueba…")
        tarea = Tarea(lambda _p: enviar(mensaje, self.g.valores, clave))
        tarea.terminado.connect(lambda _: QMessageBox.information(self, "Correo enviado", f"Enviado a {destino}."))
        tarea.finished.connect(progreso.close)
        tarea.finished.connect(lambda: self._tareas.remove(tarea))
        tarea.fallo.connect(lambda e: QMessageBox.warning(self, "El correo no ha salido", e))
        self._tareas.append(tarea)
        tarea.start()

    def _imprimir_prueba(self) -> None:
        try:
            imprimir(parte_de_prueba(self.ctx), self.ctx, self)
        except Exception as e:  # noqa: BLE001
            QMessageBox.critical(self, "No se ha podido imprimir", str(e))

    @staticmethod
    def _qr_pixmap(texto: str, lado: int) -> QPixmap:
        import segno

        filas = list(segno.make(texto, error="m").matrix_iter(border=3))
        n = len(filas)
        img = QImage(n, n, QImage.Format.Format_RGB32)
        img.fill(QColor("#ffffff"))
        p = QPainter(img)
        for y, fila in enumerate(filas):
            for x, v in enumerate(fila):
                if v:
                    p.fillRect(x, y, 1, 1, QColor("#1b1f1c"))
        p.end()
        return QPixmap.fromImage(img.scaled(lado * 2, lado * 2)).scaled(
            lado, lado, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.FastTransformation)

    def _exportar(self) -> None:
        ruta, _ = QFileDialog.getSaveFileName(self, "Exportar ajustes", str(Path.home() / "Ajustes partes de salida.zip"),
                                              "ZIP (*.zip)")
        if ruta:
            self.g.exportar(ruta)
            QMessageBox.information(self, "Ajustes exportados", f"Guardados en {ruta}.")

    def _importar_ajustes(self) -> None:
        ruta, _ = QFileDialog.getOpenFileName(self, "Importar ajustes", str(Path.home()), "ZIP (*.zip)")
        if not ruta:
            return
        try:
            self.g.importar(ruta)
        except Exception as e:  # noqa: BLE001
            QMessageBox.warning(self, "No se han podido importar", str(e))
            return
        QMessageBox.information(self, "Ajustes importados", "Cierra y vuelve a abrir Ajustes para verlos.")

    def _acerca_de(self) -> None:
        from .presentacion import acerca_de

        self._acerca = acerca_de(self)

    def _buscar_actualizaciones(self) -> None:
        from .dialogos import buscar_actualizaciones

        buscar_actualizaciones(self, avisar_si_al_dia=True)
