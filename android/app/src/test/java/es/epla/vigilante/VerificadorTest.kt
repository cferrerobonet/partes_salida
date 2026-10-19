package es.epla.vigilante

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.io.File
import java.time.LocalDateTime

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

    @Test
    fun veredictoSegunElDiaYLaHora() {
        val salida = LocalDateTime.of(2030, 1, 15, 12, 30)
        val r = Resultado.Autentico("1", salida, salida.minusHours(3), "Jefatura")
        assertEquals(Veredicto.PUEDE_SALIR, Verificador.veredicto(r, salida))
        assertEquals(Veredicto.PUEDE_SALIR, Verificador.veredicto(r, salida.plusMinutes(40)))
        assertEquals(Veredicto.TODAVIA_NO, Verificador.veredicto(r, salida.minusMinutes(1)))
        assertEquals(Veredicto.OTRO_DIA, Verificador.veredicto(r, salida.plusDays(1)))
        assertEquals(Veredicto.NO_VALE, Verificador.veredicto(Resultado.Rechazado("x"), salida))
    }
}
