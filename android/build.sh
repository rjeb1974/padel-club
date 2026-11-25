#!/bin/bash
# Build the signed Android APK inside Docker (no Android tools needed on the PC).
#
#   bash android/build.sh        (from the project folder, in Git Bash)
#
# First run: creates the signing key (android/keystore/) -- BACK IT UP. Every future
# version of the app must be signed with the same key, or phones will refuse the update.
# Output: app/downloads/padel-club.apk (served by the website at /app).
set -euo pipefail
export MSYS_NO_PATHCONV=1

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(dirname "$HERE")"
IMAGE=padel-android-build
WIN_HERE="$(cd "$HERE" && pwd -W 2>/dev/null || pwd)"

run() { docker run --rm -v "$WIN_HERE:/project" -v padel-gradle-cache:/root/.gradle "$IMAGE" "$@"; }

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
    echo "==> Building the Android build environment (one-time, several minutes)"
    docker build -q -t "$IMAGE" "$HERE"
fi

if [ ! -f "$HERE/keystore.properties" ]; then
    echo "==> Creating the app signing key"
    # (pipefail off here: `head` closing the pipe early is expected, not an error)
    PASS="$(set +o pipefail; LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32)"
    [ ${#PASS} -eq 32 ] || { echo "Could not generate a password"; exit 1; }
    mkdir -p "$HERE/keystore"
    run keytool -genkeypair -keystore /project/keystore/release.jks -alias padel \
        -keyalg RSA -keysize 4096 -validity 10000 \
        -storepass "$PASS" -keypass "$PASS" \
        -dname "CN=Padel Club, O=Padel Club" >/dev/null 2>&1
    cat > "$HERE/keystore.properties" <<EOF
storeFile=keystore/release.jks
storePassword=$PASS
keyAlias=padel
keyPassword=$PASS
EOF
fi

echo "==> Building the APK"
run gradle --no-daemon -q assembleRelease

APK="$HERE/app/build/outputs/apk/release/app-release.apk"
mkdir -p "$ROOT/app/downloads"
cp "$APK" "$ROOT/app/downloads/padel-club.apk"

PASS="$(grep storePassword "$HERE/keystore.properties" | cut -d= -f2)"
FP="$(run keytool -list -v -keystore /project/keystore/release.jks -storepass "$PASS" -alias padel \
      | grep -E '^\s*SHA256:' | awk '{print $2}')"
echo
echo "APK:    app/downloads/padel-club.apk ($(du -k "$ROOT/app/downloads/padel-club.apk" | cut -f1) KB)"
echo "SHA256: $FP"
echo "(this fingerprint must be listed in ANDROID_CERT_SHA256 in app/pwa.py)"
