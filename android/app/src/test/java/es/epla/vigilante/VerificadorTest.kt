package es.epla.vigilante

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File

/** Los mismos casos que pasa la app de escritorio (tests/test_seguridad.py). */
class VerificadorTest {
    private val vectores = JSONObject(File("../vectores_qr.json").readText())
    private val equipo = Verificador.claveDeQr(vectores.getString("qr_de_clave"))!!

    @Test
    fun claveDeAltaCoincideConElId() {
        assertEquals(vectores.getString("id_clave"), equipo.id)
    }

    @Test
    fun casosDeLosVectores() {
        val casos = vectores.getJSONArray("casos")
        for (i in 0 until casos.length()) {
            val caso = casos.getJSONObject(i)
            val r = Verificador.verificar(caso.getString("qr"), mapOf(equipo.id to equipo))
            assertEquals(caso.getString("descripcion"), caso.getBoolean("valido"), r is Resultado.Autentico)
            if (r is Resultado.Autentico) {
                assertEquals(caso.getString("id_alumno"), r.idAlumno)
                assertTrue(r.salida.toString().startsWith(caso.getString("salida")))
            }
        }
    }

    @Test
    fun qrDeAltaManipuladoSeRechaza() {
        val qr = vectores.getString("qr_de_clave").replaceFirst("|", "|0")
        assertEquals(null, Verificador.claveDeQr(qr))
        assertNotNull(Verificador.claveDeQr(vectores.getString("qr_de_clave")))
    }
}
