"""Generate the app icons (website + Android launcher) from code.

    python scripts/make_icons.py

Requires Pillow (in requirements-dev.txt).
"""
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
GREEN = (31, 138, 91, 255)       # matches --accent in style.css
BALL = (216, 240, 74, 255)
SEAM = (255, 255, 255, 255)
SS = 4  # supersampling factor for smooth edges


def ball_layer(size, ball_frac):
    """Transparent square with a padel ball of diameter size*ball_frac in the middle."""
    big = size * SS
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    r = big * ball_frac / 2
    cx = cy = big / 2
    box = (cx - r, cy - r, cx + r, cy + r)

    ball = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(ball)
    d.ellipse(box, fill=BALL)
    # Two curved seams: arcs of circles centred outside the ball, clipped to it.
    w = max(1, int(r * 0.11))
    for side in (-1, 1):
        ox = cx + side * r * 1.45
        R = r * 1.05
        d.ellipse((ox - R, cy - R, ox + R, cy + R), outline=SEAM, width=w)
    mask = Image.new("L", (big, big), 0)
    ImageDraw.Draw(mask).ellipse(box, fill=255)
    ball.putalpha(ImageChops.multiply(ball.getchannel("A"), mask))
    layer.alpha_composite(ball)
    return layer.resize((size, size), Image.LANCZOS)


def full_icon(size, ball_frac=0.58, rounded=False):
    big = size * SS
    bg = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(bg)
    if rounded:
        d.rounded_rectangle((0, 0, big - 1, big - 1), radius=big * 0.22, fill=GREEN)
    else:
        d.rectangle((0, 0, big, big), fill=GREEN)
    bg = bg.resize((size, size), Image.LANCZOS)
    bg.alpha_composite(ball_layer(size, ball_frac))
    return bg


def save(img, path):
    path = ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, optimize=True)
    print("wrote", path.relative_to(ROOT))


def main():
    # Website / installable web app
    save(full_icon(192), "app/static/icons/icon-192.png")
    save(full_icon(512), "app/static/icons/icon-512.png")
    save(full_icon(512, ball_frac=0.5), "app/static/icons/maskable-512.png")
    save(full_icon(180), "app/static/icons/apple-touch-icon.png")
    save(full_icon(32, ball_frac=0.75, rounded=True), "app/static/icons/favicon-32.png")

    # Android launcher: legacy square icons + adaptive-icon foreground (108dp canvas)
    res = "android/app/src/main/res"
    for name, scale in {"mdpi": 1, "hdpi": 1.5, "xhdpi": 2, "xxhdpi": 3, "xxxhdpi": 4}.items():
        save(full_icon(int(48 * scale), rounded=True), f"{res}/mipmap-{name}/ic_launcher.png")
        save(ball_layer(int(108 * scale), 0.42), f"{res}/mipmap-{name}/ic_launcher_foreground.png")
    # Splash-screen image shown while the site loads (centred on the green background)
    save(ball_layer(384, 0.9), f"{res}/drawable-nodpi/splash.png")


if __name__ == "__main__":
    main()
