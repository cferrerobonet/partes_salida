plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("org.jetbrains.kotlin.plugin.compose")
}

// La versión es la de la app de escritorio (pyproject.toml), que la CI pasa con -PversionName; versionCode sale de ella
// (1.2.3 → 10203) para que cada APK nuevo se instale encima del anterior.
val nombreVersion = (findProperty("versionName") as String?) ?: "0.0.0"
val codigoVersion = nombreVersion.split(".").map { it.toIntOrNull() ?: 0 }.let { (a, b, c) -> a * 10000 + b * 100 + c }
    .coerceAtLeast(1)

// Firma fija (secretos de GitHub VIGILANTE_ALMACEN_B64 y VIGILANTE_CONTRASENA; copia en el llavero del Mac de CarlosFB):
// sin ella, cada compilación firmaría con una clave distinta y el móvil no dejaría actualizar.
val almacen = System.getenv("VIGILANTE_ALMACEN")
val contrasena = System.getenv("VIGILANTE_CONTRASENA")

android {
    namespace = "es.epla.vigilante"
    compileSdk = 35

    defaultConfig {
        applicationId = "es.epla.vigilante"
        minSdk = 26
        targetSdk = 35
        versionCode = codigoVersion
        versionName = nombreVersion
    }
    signingConfigs {
        if (almacen != null && contrasena != null) {
            create("epla") {
                storeFile = file(almacen)
                storeType = "pkcs12"
                storePassword = contrasena
                keyAlias = "vigilante"
                keyPassword = contrasena
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.findByName("epla")
        }
    }
    buildFeatures { compose = true }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }
    lint {
        // El APK sale aunque lint vea avisos de estilo; los errores reales los cazan las pruebas y la compilación.
        abortOnError = false
        checkReleaseBuilds = false
    }
}

dependencies {
    val composeBom = platform("androidx.compose:compose-bom:2024.10.01")
    implementation(composeBom)
    implementation("androidx.activity:activity-compose:1.9.3")
    implementation("androidx.compose.material3:material3")
    implementation("androidx.compose.ui:ui")
    implementation("com.google.android.gms:play-services-code-scanner:16.1.0")
    implementation("org.bouncycastle:bcprov-jdk18on:1.79")

    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20240303")
}
