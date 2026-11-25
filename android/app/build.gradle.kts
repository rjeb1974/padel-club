import java.util.Properties

plugins {
    id("com.android.application")
}

// Signing key details live in android/keystore.properties (not in git; see android/README.md).
val keystoreProps = Properties().apply {
    val f = rootProject.file("keystore.properties")
    if (f.exists()) f.inputStream().use { load(it) }
}

android {
    namespace = "com.padelclub.app"
    compileSdk = 36
    buildToolsVersion = "36.1.0"  // the version installed in android/Dockerfile

    defaultConfig {
        applicationId = "com.padelclub.app"
        minSdk = 24
        targetSdk = 36
        // Bump both when publishing a new APK (only needed if this Android project changes;
        // website changes reach the app automatically).
        versionCode = 1
        versionName = "1.0"
    }

    signingConfigs {
        create("release") {
            if (keystoreProps.isNotEmpty()) {
                storeFile = rootProject.file(keystoreProps.getProperty("storeFile"))
                storePassword = keystoreProps.getProperty("storePassword")
                keyAlias = keystoreProps.getProperty("keyAlias")
                keyPassword = keystoreProps.getProperty("keyPassword")
            }
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            signingConfig = signingConfigs.getByName("release")
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

dependencies {
    implementation("com.google.androidbrowserhelper:androidbrowserhelper:2.8.0")
}
