package es.epla.vigilante

import android.content.Context
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.google.mlkit.vision.barcode.common.Barcode
import com.google.mlkit.vision.codescanner.GmsBarcodeScannerOptions
import com.google.mlkit.vision.codescanner.GmsBarcodeScanning
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter

private val HORA = DateTimeFormatter.ofPattern("HH:mm")

/** Equipos de confianza en las preferencias del móvil: solo claves públicas. */
private class Equipos(context: Context) {
    private val prefs = context.getSharedPreferences("equipos", Context.MODE_PRIVATE)

    fun todos(): Map<String, ClaveEquipo> =
        (prefs.getStringSet("qr", emptySet()) ?: emptySet())
            .mapNotNull { Verificador.claveDeQr(it) }
            .associateBy { it.id }

    fun alta(qr: String): ClaveEquipo? {
        val clave = Verificador.claveDeQr(qr) ?: return null
        val actuales = prefs.getStringSet("qr", emptySet()).orEmpty().toMutableSet()
        actuales.add(qr.trim())
        prefs.edit().putStringSet("qr", actuales).apply()
        return clave
    }
}

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        val equipos = Equipos(this)
        val escaner = GmsBarcodeScanning.getClient(
            this,
            GmsBarcodeScannerOptions.Builder().setBarcodeFormats(Barcode.FORMAT_QR_CODE).build(),
        )
        setContent {
            MaterialTheme {
                var mensaje by remember { mutableStateOf("Escanea el QR del parte.") }
                var color by remember { mutableStateOf(Color(0xFF5D6B60)) }
                Pantalla(
                    mensaje = mensaje,
                    color = color,
                    equipos = equipos.todos().size,
                    escanearParte = {
                        escaner.startScan().addOnSuccessListener { codigo ->
                            val (texto, c) = describir(Verificador.verificar(codigo.rawValue.orEmpty(), equipos.todos()))
                            mensaje = texto
                            color = c
                        }
                    },
                    altaEquipo = {
                        escaner.startScan().addOnSuccessListener { codigo ->
                            val clave = equipos.alta(codigo.rawValue.orEmpty())
                            mensaje = clave?.let { "Equipo dado de alta: ${it.nombre}" }
                                ?: "Ese QR no es el de Ajustes → QR y verificación."
                            color = if (clave != null) Color(0xFF2C7A3A) else Color(0xFFA32D2D)
                        }
                    },
                )
            }
        }
    }
}

private fun describir(r: Resultado, ahora: LocalDateTime = LocalDateTime.now()): Pair<String, Color> = when (r) {
    is Resultado.Rechazado -> r.motivo to Color(0xFFA32D2D)
    is Resultado.Autentico -> when {
        r.salida.toLocalDate() != LocalDate.now() -> "Parte de otro día: no vale." to Color(0xFFA32D2D)
        ahora.isBefore(r.salida) -> "Auténtico, pero todavía no: sale a las ${r.salida.format(HORA)}." to Color(0xFF9A5B00)
        else -> "Auténtico. Puede salir (desde las ${r.salida.format(HORA)}).\nNIA ${r.idAlumno} · ${r.equipo}" to Color(0xFF2C7A3A)
    }
}

@Composable
private fun Pantalla(mensaje: String, color: Color, equipos: Int, escanearParte: () -> Unit, altaEquipo: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        verticalArrangement = Arrangement.Center,
    ) {
        Text("Vigilante EPLA", fontSize = 28.sp, fontWeight = FontWeight.Bold)
        Spacer(Modifier.height(24.dp))
        Text(
            mensaje,
            color = Color.White,
            fontSize = 20.sp,
            modifier = Modifier.fillMaxWidth().background(color).padding(20.dp),
        )
        Spacer(Modifier.height(24.dp))
        Button(onClick = escanearParte, modifier = Modifier.fillMaxWidth().height(64.dp)) {
            Text("Escanear parte", fontSize = 20.sp)
        }
        Spacer(Modifier.height(12.dp))
        OutlinedButton(onClick = altaEquipo, modifier = Modifier.fillMaxWidth()) {
            Text("Dar de alta un equipo ($equipos)")
        }
    }
}
