# Padel Club Android app

A [Trusted Web Activity](https://developer.chrome.com/docs/android/trusted-web-activity):
a small Android app that opens https://padel-club-9u7j.onrender.com full-screen using
Chrome. Website changes reach the app automatically, so the APK rarely needs rebuilding.

## Building

Needs only Docker Desktop. From the project folder, in Git Bash:

```bash
bash android/build.sh
```

The output goes to `app/downloads/padel-club.apk`. The website serves it at `/app`, so commit it and push.

## The signing key: back it up

The first build creates `android/keystore/release.jks` and `android/keystore.properties`,
which holds the passwords. These files are **not in git**. Copy both somewhere safe, such as a USB stick or a password manager.
If they are lost, a new APK can't update the installed app. Every player would have to uninstall the app and reinstall it,
and you would have to update the fingerprint below.

The key's SHA-256 fingerprint is listed in `app/pwa.py` (`ANDROID_CERT_SHA256`) and published at
`/.well-known/assetlinks.json`. That proves the app belongs to the site, so Chrome hides its address bar.

## When to rebuild

Rebuild only when something in `android/` changes, such as the site address, the icon or the name. Before rebuilding, bump
`versionCode` and `versionName` in `android/app/build.gradle.kts`.
