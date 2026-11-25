"""Installable web app + Android app support.

- /manifest.webmanifest and /sw.js make the site installable (PWA).
- /.well-known/assetlinks.json proves the Android app (Trusted Web Activity) belongs
  to this site, so it opens full-screen without Chrome's address bar.
- /app and /download/padel-club.apk let players download the Android app.
"""
import json
import os

from flask import Blueprint, Response, abort, render_template, send_from_directory, url_for

bp = Blueprint("pwa", __name__)

APP_DIR = os.path.dirname(os.path.abspath(__file__))
DOWNLOADS = os.path.join(APP_DIR, "downloads")
APK_NAME = "padel-club.apk"
THEME = "#1f8a5b"

# Android app identity. The fingerprint is the SHA-256 of the APK signing certificate
# (public information; see android/README.md for how it was obtained).
ANDROID_PACKAGE = "com.padelclub.app"
ANDROID_CERT_SHA256 = [
    "8A:21:1D:66:EF:18:EA:B9:BD:B6:94:D9:CE:F2:09:3C:85:43:69:AE:24:F3:3E:78:D7:33:B6:20:C3:86:53:58",
]


@bp.route("/manifest.webmanifest")
def manifest():
    data = {
        "name": "Padel Club",
        "short_name": "Padel",
        "description": "Presences, scores and leaderboard for our padel group.",
        "id": "/",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait",
        "background_color": "#f4f6f3",
        "theme_color": THEME,
        "icons": [
            {"src": url_for("static", filename="icons/icon-192.png"), "sizes": "192x192", "type": "image/png"},
            {"src": url_for("static", filename="icons/icon-512.png"), "sizes": "512x512", "type": "image/png"},
            {"src": url_for("static", filename="icons/maskable-512.png"), "sizes": "512x512",
             "type": "image/png", "purpose": "maskable"},
        ],
    }
    return Response(json.dumps(data), mimetype="application/manifest+json")


@bp.route("/sw.js")
def service_worker():
    resp = send_from_directory(os.path.join(APP_DIR, "static"), "sw.js",
                               mimetype="application/javascript")
    resp.headers["Cache-Control"] = "no-cache"
    return resp


@bp.route("/offline")
def offline():
    return render_template("offline.html")


@bp.route("/.well-known/assetlinks.json")
def assetlinks():
    statements = [{
        "relation": ["delegate_permission/common.handle_all_urls"],
        "target": {
            "namespace": "android_app",
            "package_name": ANDROID_PACKAGE,
            "sha256_cert_fingerprints": ANDROID_CERT_SHA256,
        },
    }] if ANDROID_CERT_SHA256 else []
    return Response(json.dumps(statements), mimetype="application/json")


@bp.route("/app")
def get_app():
    has_apk = os.path.exists(os.path.join(DOWNLOADS, APK_NAME))
    return render_template("get_app.html", has_apk=has_apk)


@bp.route(f"/download/{APK_NAME}")
def download_apk():
    if not os.path.exists(os.path.join(DOWNLOADS, APK_NAME)):
        abort(404)
    return send_from_directory(DOWNLOADS, APK_NAME, as_attachment=True,
                               mimetype="application/vnd.android.package-archive")
