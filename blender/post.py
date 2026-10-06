"""Постобработка рендера: свечение (bloom), звёздочки и месяц вокруг сияющей фигуры.

    python3 blender/post.py renders/raw/glow.png renders/raw/glow.json renders/glow.png
"""
import json
import math
import sys

from PIL import Image, ImageChops, ImageDraw, ImageFilter


def star(draw, cx, cy, r, color, thin=0.16):
    """Четырёхлучевая звёздочка как в мультяшном арте."""
    t = r * thin
    pts = []
    for i in range(8):
        a = math.pi / 2 * (i // 2) + (math.pi / 4 if i % 2 else 0)
        rad = r if i % 2 == 0 else t
        pts.append((cx + rad * math.cos(a), cy - rad * math.sin(a)))
    draw.polygon(pts, fill=color)


def main(src, meta, dst, style="soft"):
    bright = style == "bright"
    im = Image.open(src).convert("RGB")
    W, H = im.size
    m = json.load(open(meta))
    hx, hy = m["head"][0] * W, m["head"][1] * H
    head_r = abs(m["head"][1] - m["top"][1]) * H  # примерно полголовы
    body_h = abs(m["feet"][1] - m["top"][1]) * H

    # bloom: яркие участки размываем в нескольких масштабах и складываем
    th, gain = (150, 2.4) if bright else (160, 2.6)
    lum = im.convert("L").point(lambda v: 0 if v < th else int((v - th) * gain))
    bright = Image.composite(im, Image.new("RGB", im.size), lum)
    glow = Image.new("RGB", im.size)
    for rad, k in ((W / 160, 0.9), (W / 60, 0.7), (W / 25, 0.55)):
        b = bright.filter(ImageFilter.GaussianBlur(rad))
        glow = ImageChops.add(glow, b.point(lambda v, k=k: int(v * k)))
    im = ImageChops.screen(im, glow)

    # мягкий розово-белый ореол вокруг сияющей фигуры
    halo = Image.new("RGB", im.size)
    d = ImageDraw.Draw(halo)
    cx, cy = hx, hy + body_h * 0.35
    d.ellipse([cx - body_h * 0.42, cy - body_h * 0.62, cx + body_h * 0.42, cy + body_h * 0.62],
              fill=(70, 45, 75))
    im = ImageChops.screen(im, halo.filter(ImageFilter.GaussianBlur(body_h * 0.22)))

    # звёздочки и месяц
    fx = Image.new("RGB", im.size)
    d = ImageDraw.Draw(fx)
    s = head_r
    if bright:
        sparkles = [(-1.9, -1.1, 0.42), (1.7, -1.9, 0.62), (2.3, 1.3, 0.3), (-1.4, 3.6, 0.34),
                    (2.6, 4.4, 0.24), (-2.6, 0.9, 0.2)]
    else:
        sparkles = [(-0.9, -2.2, 0.4), (1.7, -1.9, 0.62), (2.4, 1.4, 0.3), (2.0, 5.6, 0.3),
                    (2.8, 3.6, 0.22), (0.4, -3.1, 0.18)]
    for dx, dy, r in sparkles:
        star(d, hx + dx * s, hy + dy * s, r * s, (255, 255, 255))
    mx, my, mr = hx + 2.5 * s, hy - 0.6 * s, 0.38 * s
    d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(255, 250, 245))
    d.ellipse([mx - mr * 0.55, my - mr * 1.15, mx + mr * 1.25, my + mr * 0.6], fill=(0, 0, 0))
    fx_glow = fx.filter(ImageFilter.GaussianBlur(s * 0.18))
    im = ImageChops.screen(im, ImageChops.add(fx, fx_glow))

    # виньетка
    vig = Image.new("L", (W, H), 0)
    ImageDraw.Draw(vig).ellipse([-W * 0.15, -H * 0.25, W * 1.15, H * 1.25], fill=255)
    vig = vig.filter(ImageFilter.GaussianBlur(W / 10))
    im = Image.composite(im, ImageChops.multiply(im, Image.new("RGB", im.size, (90, 90, 110))), vig)
    im.save(dst)


if __name__ == "__main__":
    main(*sys.argv[1:5])
