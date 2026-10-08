package es.epla.vigilante

import org.bouncycastle.crypto.params.Ed25519PublicKeyParameters
import org.bouncycastle.crypto.signers.Ed25519Signer
import java.security.MessageDigest
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.Base64

/** Equipo de jefatura dado de alta escaneando su QR `PSK1`. */
data class ClaveEquipo(val id: String, val publica: ByteArray, val nombre: String) {
    override fun equals(other: Any?) = other is ClaveEquipo && other.id == id
    override fun hashCode() = id.hashCode()
}

sealed class Resultado {
    data class Autentico(
        val idAlumno: String,
        val salida: LocalDateTime,
        val expedido: LocalDateTime,
        val equipo: String,
    ) : Resultado()

    data class Rechazado(val motivo: String) : Resultado()
}

/** Verificación del QR del parte (especificación en android/ESPECIFICACION_QR.md). */
object Verificador {
    private val FORMATO: DateTimeFormatter = DateTimeFormatter.ofPattern("yyyyMMddHHmm")

    fun deB64url(texto: String): ByteArray = Base64.getUrlDecoder().decode(texto)

    fun idDeClave(publica: ByteArray): String =
        MessageDigest.getInstance("SHA-256").digest(publica).take(4)
            .joinToString("") { "%02X".format(it) }

    /** `PSK1|id|clave|nombre` → equipo, o null si no es un QR de alta válido. */
    fun claveDeQr(texto: String): ClaveEquipo? {
        val partes = texto.trim().split("|")
        if (partes.size != 4 || partes[0] != "PSK1") return null
        val publica = runCatching { deB64url(partes[2]) }.getOrNull() ?: return null
        if (publica.size != 32 || idDeClave(publica) != partes[1]) return null
        return ClaveEquipo(partes[1], publica, partes[3])
    }

    fun verificar(texto: String, claves: Map<String, ClaveEquipo>): Resultado {
        val partes = texto.trim().split("|")
        if (partes.size != 6 || partes[0] != "PS1") return Resultado.Rechazado("No es un parte de salida")
        val equipo = claves[partes[1]] ?: return Resultado.Rechazado("Firmado por un equipo desconocido")
        val firma = runCatching { deB64url(partes[5]) }.getOrNull()
        val mensaje = partes.subList(0, 5).joinToString("|").toByteArray(Charsets.UTF_8)
        val valida = firma != null && firma.size == 64 && runCatching {
            Ed25519Signer().run {
                init(false, Ed25519PublicKeyParameters(equipo.publica, 0))
                update(mensaje, 0, mensaje.size)
                verifySignature(firma)
            }
        }.getOrDefault(false)
        if (!valida) return Resultado.Rechazado("Firma no válida: el parte está alterado o es falso")
        return runCatching {
            Resultado.Autentico(
                idAlumno = partes[2],
                salida = LocalDateTime.parse(partes[3], FORMATO),
                expedido = LocalDateTime.parse(partes[4], FORMATO),
                equipo = equipo.nombre,
            )
        }.getOrElse { Resultado.Rechazado("Firma no válida: el parte está alterado o es falso") }
    }
}
