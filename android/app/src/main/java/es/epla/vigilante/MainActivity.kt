package es.epla.vigilante

import android.content.Context
import android.os.Bundle
import android.view.HapticFeedbackConstants
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScanner
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

/** Colores de la app de escritorio (DESIGN.md): verde EPLA, aviso, peligro y secundario. */
private val VERDE = Color(0xFF2C7A3A)
private val AVISO = Color(0xFF9A5B00)
private val PELIGRO = Color(0xFFA32D2D)
private val SECUNDARIO = Color(0xFF5D6B60)
private val FONDO = Color(0xFFF3F5F1)
private val TINTA = Color(0xFF1D2A20)
private val HORA = DateTimeFormatter.ofPattern("HH:mm")
private val FECHA = DateTimeFormatter.ofPattern("dd/MM/yyyy")

/** Equipos de confianza en las preferencias del móvil: solo claves públicas y nombres, nada del alumnado. */
private class Equipos(context: Context) {
    private val prefs = context.getSharedPreferences("equipos", Context.MODE_PRIVATE)

    private fun qrs(): Set<String> = prefs.getStringSet("qr", emptySet()).orEmpty()

    fun todos(): Map<String, ClaveEquipo> = qrs().mapNotNull { Verificador.claveDeQr(it) }.associateBy { it.id }

    fun alta(qr: String): ClaveEquipo? {
        val clave = Verificador.claveDeQr(qr) ?: return null
        // un equipo que vuelve a darse de alta (otro nombre) sustituye al anterior
        val otros = qrs().filter { Verificador.claveDeQr(it)?.id != clave.id }
        prefs.edit().putStringSet("qr", (otros + qr.trim()).toSet()).apply()
        return clave
    }

    fun baja(id: String) {
        prefs.edit().putStringSet("qr", qrs().filter { Verificador.claveDeQr(it)?.id != id }.toSet()).apply()
    }
}

/** Lo que enseña la tarjeta de resultado. */
private data class Aviso(val simbolo: String, val titulo: String, val detalle: List<String>, val color: Color)

private val INICIO = Aviso("⌁", "Listo", listOf("Pulsa «Escanear parte» y apunta al QR del parte."), SECUNDARIO)

private fun aviso(r: Resultado, ahora: LocalDateTime = LocalDateTime.now()): Aviso =
    when (Verificador.veredicto(r, ahora)) {
        Veredicto.NO_VALE -> Aviso("✕", "NO VALE", listOf((r as Resultado.Rechazado).motivo), PELIGRO)
        Veredicto.OTRO_DIA -> (r as Resultado.Autentico).let {
            Aviso("✕", "OTRO DÍA", listOf("El parte es del ${it.salida.format(FECHA)}: no vale hoy.", "NIA ${it.idAlumno}"),
                PELIGRO)
        }
        Veredicto.TODAVIA_NO -> (r as Resultado.Autentico).let {
            Aviso("⏱", "TODAVÍA NO", listOf("Auténtico, pero sale a las ${it.salida.format(HORA)}.",
                "NIA ${it.idAlumno} · ${it.equipo}"), AVISO)
        }
        Veredicto.PUEDE_SALIR -> (r as Resultado.Autentico).let {
            Aviso("✓", "PUEDE SALIR", listOf("Salida desde las ${it.salida.format(HORA)}.",
                "NIA ${it.idAlumno} · comprueba la foto del parte.", "Firmado por ${it.equipo} a las ${it.expedido.format(HORA)}."),
                VERDE)
        }
    }

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // en la puerta, el móvil no debe apagarse entre alumno y alumno mientras la app está abierta
        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
        val equipos = Equipos(this)
        val escaner = GmsBarcodeScanning.getClient(
            this,
            GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build(),
        )
        setContent {
            MaterialTheme(colorScheme = lightColorScheme(primary = VERDE, background = FONDO)) {
                Pantalla(equipos, escaner)
            }
        }
    }
}

@Composable
private fun Pantalla(equipos: Equipos, escaner: GmsBarcodeScanner) {
    val vista = LocalView.current
    var actual by remember { mutableStateOf(INICIO) }
    var lista by remember { mutableStateOf(equipos.todos()) }
    var verEquipos by remember { mutableStateOf(false) }

    fun escanear(alLeer: (String) -> Unit) {
        escaner.startScan().addOnSuccessListener { alLeer(it.rawValue.orEmpty()) }
    }

    Column(
        modifier = Modifier.fillMaxSize().background(FONDO).padding(20.dp),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text("Vigilante EPLA", fontSize = 26.sp, fontWeight = FontWeight.Bold, color = TINTA,
                modifier = Modifier.weight(1f))
            Text(if (lista.isEmpty()) "sin equipos" else "${lista.size} equipo${if (lista.size == 1) "" else "s"}",
                color = SECUNDARIO, fontSize = 14.sp)
        }
        if (lista.isEmpty()) {
            Text("Antes de nada, da de alta el equipo de jefatura: en su ordenador, Ajustes → QR y verificación, y aquí "
                + "«Equipos de confianza» → «Dar de alta».", color = AVISO, fontSize = 15.sp)
        }
        Tarjeta(actual, Modifier.weight(1f))
        Button(
            onClick = {
                escanear { texto ->
                    actual = aviso(Verificador.verificar(texto, equipos.todos()))
                    vista.performHapticFeedback(
                        if (actual.color == VERDE) HapticFeedbackConstants.KEYBOARD_TAP else HapticFeedbackConstants.LONG_PRESS,
                    )
                }
            },
            modifier = Modifier.fillMaxWidth().height(72.dp),
            colors = ButtonDefaults.buttonColors(containerColor = VERDE),
        ) { Text("Escanear parte", fontSize = 22.sp, fontWeight = FontWeight.Bold) }
        OutlinedButton(onClick = { verEquipos = true }, modifier = Modifier.fillMaxWidth()) {
            Text("Equipos de confianza", color = TINTA)
        }
    }

    if (verEquipos) {
        AlertDialog(
            onDismissRequest = { verEquipos = false },
            title = { Text("Equipos de confianza") },
            text = {
                Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Solo se aceptan los partes firmados por estos equipos. Para dar de alta uno, escanea el QR de "
                        + "Ajustes → QR y verificación de su ordenador.", color = SECUNDARIO, fontSize = 14.sp)
                    if (lista.isEmpty()) Text("Ninguno todavía.", fontWeight = FontWeight.Bold)
                    lista.values.sortedBy { it.nombre }.forEach { e ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(e.nombre, fontWeight = FontWeight.Bold)
                                Text("Clave ${e.id}", color = SECUNDARIO, fontSize = 12.sp)
                            }
                            TextButton(onClick = { equipos.baja(e.id); lista = equipos.todos() }) {
                                Text("Quitar", color = PELIGRO)
                            }
                        }
                    }
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    escanear { texto ->
                        val clave = equipos.alta(texto)
                        lista = equipos.todos()
                        actual = if (clave != null) {
                            Aviso("✓", "EQUIPO DADO DE ALTA", listOf(clave.nombre, "Clave ${clave.id}"), VERDE)
                        } else {
                            Aviso("✕", "NO ES UN QR DE ALTA", listOf("Escanea el QR de Ajustes → QR y verificación."), PELIGRO)
                        }
                        verEquipos = false
                    }
                }) { Text("Dar de alta") }
            },
            dismissButton = { TextButton(onClick = { verEquipos = false }) { Text("Cerrar") } },
        )
    }
}

@Composable
private fun Tarjeta(a: Aviso, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier.fillMaxWidth().clip(RoundedCornerShape(16.dp)).background(a.color).padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Text(a.simbolo, color = Color.White, fontSize = 72.sp, fontWeight = FontWeight.Bold)
        Text(a.titulo, color = Color.White, fontSize = 30.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center)
        Spacer(Modifier.height(12.dp))
        a.detalle.forEach {
            Text(it, color = Color.White, fontSize = 18.sp, textAlign = TextAlign.Center)
        }
    }
}
