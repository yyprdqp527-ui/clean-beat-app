#!/usr/bin/env python3
"""
generate_icon.py
Génère les icônes PWA de QuiFaitQuoi avec la police Bubblegum Sans.
Dépendances : pip install pillow
"""

import base64
import json
import os
import sys

# ── 1. Lire la police TTF ────────────────────────────────────────────────────
FONT_TTF  = os.path.join("static", "fonts", "BubblegumSans.ttf")
FONT_WOF2 = os.path.join("static", "fonts", "BubblegumSans.woff2")

if not os.path.exists(FONT_TTF):
    # Fallback : convertir le woff2 en TTF à la volée
    if not os.path.exists(FONT_WOF2):
        print(f"❌ Police introuvable : {FONT_TTF} ni {FONT_WOF2}")
        sys.exit(1)
    try:
        from fontTools.ttLib import TTFont as _TTFont
    except ImportError:
        print("❌ fonttools non installé. Lancez : pip install fonttools brotli")
        sys.exit(1)
    tt = _TTFont(FONT_WOF2)
    tt.flavor = None
    tt.save(FONT_TTF)
    print(f"✅ woff2 → TTF converti automatiquement ({os.path.getsize(FONT_TTF):,} octets)")

font_path = FONT_TTF
print(f"✅ Police TTF prête : {font_path} ({os.path.getsize(font_path):,} octets)")

# Pour le SVG embarqué : encoder le woff2 si disponible, sinon le TTF
_embed_path = FONT_WOF2 if os.path.exists(FONT_WOF2) else FONT_TTF
with open(_embed_path, "rb") as _f:
    font_b64 = base64.b64encode(_f.read()).decode("ascii")

# ── 3. Générer le SVG (pour archivage) ──────────────────────────────────────
SVG_CONTENT = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <style>
      @font-face {{
        font-family: 'Bubblegum Sans';
        src: url('data:font/woff2;base64,{font_b64}') format('woff2');
      }}
    </style>
    <linearGradient id="bg" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%"   stop-color="#FFD454"/>
      <stop offset="50%"  stop-color="#FF8C35"/>
      <stop offset="100%" stop-color="#FF5733"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="115" fill="url(#bg)"/>
  <text x="256" y="185"  font-family="Bubblegum Sans" font-size="148"
        text-anchor="middle" fill="#1a1008">QUI</text>
  <text x="256" y="325"  font-family="Bubblegum Sans" font-size="148"
        text-anchor="middle" fill="#CC1111">FAIT</text>
  <text x="256" y="465"  font-family="Bubblegum Sans" font-size="148"
        text-anchor="middle" fill="#1a1008">QUOI</text>
</svg>"""

SVG_PATH = os.path.join("static", "qfq-icon.svg")
with open(SVG_PATH, "w", encoding="utf-8") as f:
    f.write(SVG_CONTENT)
print(f"✅ SVG généré : {SVG_PATH}")

# ── 4. Dessiner les PNG avec Pillow ─────────────────────────────────────────
try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    print("❌ Pillow non installé. Lancez : pip install pillow")
    sys.exit(1)


def hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))


def best_font_size(font_path: str, text: str, max_width: int, max_height: int) -> int:
    """Trouve la taille de police maximale pour que le texte tienne dans max_width × max_height."""
    from PIL import ImageFont
    lo, hi = 10, max_height
    while lo < hi - 1:
        mid = (lo + hi) // 2
        f = ImageFont.truetype(font_path, mid)
        bb = f.getbbox(text)          # (left, top, right, bottom)
        w = bb[2] - bb[0]
        h = bb[3] - bb[1]
        if w <= max_width and h <= max_height:
            lo = mid
        else:
            hi = mid
    return lo


def draw_text_stroked(draw, xy, text, font, fill, stroke_width=1):
    """Dessine un texte avec contour 1px même couleur (léger épaississement)."""
    x, y = xy
    for dx, dy in [(-1,0),(1,0),(0,-1),(0,1)]:
        draw.text((x + dx, y + dy), text, font=font, fill=fill, anchor="mm")
    draw.text((x, y), text, font=font, fill=fill, anchor="mm")


def make_icon(size: int) -> Image.Image:
    W = H = size
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))

    # ── Gradient diagonal #FFD454 → #FF8C35 → #FF5733 ───────────────────────
    c0 = hex_to_rgb("#FFD454")
    c1 = hex_to_rgb("#FF8C35")
    c2 = hex_to_rgb("#FF5733")

    def lerp(a, b, t):
        return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

    for y in range(H):
        for x in range(W):
            t = (x / W + y / H) / 2
            color = lerp(c0, c1, min(t * 2, 1)) if t < 0.5 else lerp(c1, c2, (t - 0.5) * 2)
            img.putpixel((x, y), (*color, 255))

    # ── Coins arrondis iOS (23%) ─────────────────────────────────────────────
    radius = int(0.23 * size)          # 512→118, 192→44
    mask = Image.new("L", (W, H), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, W - 1, H - 1], radius=radius, fill=255)
    img.putalpha(mask)

    draw = ImageDraw.Draw(img)

    # ── Texte : 90% de la largeur, positions fixes à 25/50/75% ─────────────
    max_w = int(W * 0.90)
    stroke_w = max(2, size // 170)

    words = [
        ("QUI",  int(H * 0.25), hex_to_rgb("#1a1008")),
        ("FAIT", int(H * 0.50), hex_to_rgb("#CC1111")),
        ("QUOI", int(H * 0.75), hex_to_rgb("#1a1008")),
    ]

    for word, cy, color in words:
        # Taille max pour tenir dans 90% de la largeur, 1/3 de la hauteur
        fs = best_font_size(font_path, word, max_w, int(H * 0.30))
        font = ImageFont.truetype(font_path, fs)
        draw_text_stroked(draw, (W // 2, cy), word, font, (*color, 255), stroke_w)

    return img


ICONS = [
    ("static/qfq-icon-192.png", 192),
    ("static/qfq-icon-512.png", 512),
]

for out_path, size in ICONS:
    icon = make_icon(size)
    icon.save(out_path, "PNG", optimize=True)
    file_size = os.path.getsize(out_path)
    print(f"✅ {out_path} ({size}×{size}) — {file_size:,} octets")

# ── 5. Mettre à jour manifest.json ──────────────────────────────────────────
MANIFEST_PATH = os.path.join("static", "manifest.json")

with open(MANIFEST_PATH, "r", encoding="utf-8") as f:
    manifest = json.load(f)

manifest["icons"] = [
    {"src": "/static/qfq-icon-192.png", "sizes": "192x192",
     "type": "image/png", "purpose": "any"},
    {"src": "/static/qfq-icon-192.png", "sizes": "192x192",
     "type": "image/png", "purpose": "maskable"},
    {"src": "/static/qfq-icon-512.png", "sizes": "512x512",
     "type": "image/png", "purpose": "any"},
    {"src": "/static/qfq-icon-512.png", "sizes": "512x512",
     "type": "image/png", "purpose": "maskable"},
]

with open(MANIFEST_PATH, "w", encoding="utf-8") as f:
    json.dump(manifest, f, ensure_ascii=False, indent=2)

print(f"✅ manifest.json mis à jour → qfq-icon-192.png / qfq-icon-512.png")
print("\n🎉 Terminé ! Les icônes PWA sont prêtes.")
