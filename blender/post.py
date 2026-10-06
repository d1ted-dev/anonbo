"""Постобработка рендера: свечение (bloom), звёздочки и месяц вокруг сияющей фигуры.

    python3 blender/post.py renders/raw/glow.png renders/raw/glow.json renders/glow.png
"""
import json
import math
import sys

import numpy as np
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


def hsv_to_rgb(h, s, v):
    i = np.floor(h * 6).astype(int) % 6
    f = h * 6 - np.floor(h * 6)
    p, q, t = v * (1 - s), v * (1 - s * f), v * (1 - s * (1 - f))
    r = np.choose(i, [v, q, p, p, t, v]); g = np.choose(i, [t, v, v, q, p, p])
    b = np.choose(i, [p, p, t, v, v, q])
    return np.stack([r, g, b], -1)


def rainbow_shell(im, mask_path):
    """Радужная оболочка по силуэту: розовый слева сверху → лиловый → голубой → зелёный → жёлтый снизу."""
    W, H = im.size
    u = W / 1920
    mask = Image.open(mask_path).convert("RGBA").resize(im.size)
    mask = Image.fromarray((np.asarray(mask, np.float32)[..., :3].mean(-1) * np.asarray(mask, np.float32)[..., 3] / 255).astype(np.uint8))
    m = np.asarray(mask, np.float32) / 255
    ys, xs = np.nonzero(m > 0.5)
    cx, cy = xs.mean(), ys.mean()

    def grow(r, blur):
        k = max(3, int(r * u) | 1)
        g = mask.filter(ImageFilter.MaxFilter(k)) if k > 1 else mask
        return np.asarray(g.filter(ImageFilter.GaussianBlur(blur * u)), np.float32) / 255

    yy, xx = np.mgrid[0:H, 0:W]
    ang = np.degrees(np.arctan2(-(yy - cy), (xx - cx) * 1.6))
    hue = np.interp(ang, [-180, -100, -45, 0, 50, 115, 180],
                         [0.97, 0.14, 0.32, 0.5, 0.76, 0.9, 0.97]) % 1
    rainbow = hsv_to_rgb(hue, np.full_like(hue, 0.72), np.ones_like(hue))

    a = np.asarray(im, np.float32) / 255
    # мягкий белый свет снаружи
    outside = (1 - m)[..., None]
    outer = grow(9, 26)[..., None] * 0.6 * outside
    a = 1 - (1 - a) * (1 - outer)
    # цветная полоса снаружи по контуру
    ring = np.clip(grow(22, 5) - m, 0, 1)[..., None]
    a = a * (1 - ring * 0.95) + rainbow * ring * 0.95
    # тонкая белая кромка у самого силуэта
    edge = np.clip(grow(6, 1.5) - m, 0, 1)[..., None]
    a = 1 - (1 - a) * (1 - edge * 0.85)
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def holo_shell(im, mask_path, strength=0.2, lift=0.14, white=0.9, toward_right=False):
    """Голографический перелив по всей фигуре + толстое белое свечение с лёгким цветным отливом."""
    W, H = im.size
    u = W / 1920
    mask = Image.open(mask_path).convert("RGBA").resize(im.size)
    mask = Image.fromarray((np.asarray(mask, np.float32)[..., :3].mean(-1) * np.asarray(mask, np.float32)[..., 3] / 255).astype(np.uint8))
    m = np.asarray(mask, np.float32) / 255
    ys, xs = np.nonzero(m > 0.5)
    x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()

    def grow(r, blur):
        k = max(3, int(r * u) | 1)
        g = mask.filter(ImageFilter.MaxFilter(k))
        return np.asarray(g.filter(ImageFilter.GaussianBlur(blur * u)), np.float32) / 255

    def shrink(r):
        k = max(3, int(r * u) | 1)
        return np.asarray(mask.filter(ImageFilter.MinFilter(k)), np.float32) / 255

    yy, xx = np.mgrid[0:H, 0:W]
    # диагональ: розовый слева сверху → персиково-жёлтый → бирюзовый справа снизу
    t = np.clip(((xx - x0) / (x1 - x0 + 1) * 0.55 + (yy - y0) / (y1 - y0 + 1) * 0.45), 0, 1)
    hue = np.interp(t, [0, 0.3, 0.55, 0.8, 1], [-0.07, 0.03, 0.14, 0.3, 0.48]) % 1
    holo = hsv_to_rgb(hue, np.full_like(hue, 0.42), np.ones_like(hue))
    holo_weak = hsv_to_rgb(hue, np.full_like(hue, 0.22), np.ones_like(hue))

    a = np.asarray(im, np.float32) / 255
    mi = m[..., None]
    # внутри фигуры: окрасить переливом умножением (детали скина остаются) и чуть осветлить
    tint = hsv_to_rgb(hue, np.full_like(hue, strength), np.ones_like(hue))
    inner = a * tint
    inner = inner + (1 - inner) * lift
    a = a * (1 - mi) + inner * mi
    # кромка внутри силуэта светлеет (как свечение изнутри)
    rim_in = np.clip(m - shrink(9), 0, 1)
    rim_in = np.asarray(Image.fromarray((rim_in * 255).astype(np.uint8))
                        .filter(ImageFilter.GaussianBlur(3 * u)), np.float32)[..., None] / 255 * mi
    a = 1 - (1 - a) * (1 - holo_weak * rim_in * 0.75 * white)
    # толстое белое свечение снаружи + широкий мягкий ореол
    out = 1 - mi
    band = grow(6 + 10 * white, 2 + 3 * white)[..., None] * out
    a = a * (1 - band * white) + holo_weak * band * white
    halo = grow(20, 34)[..., None] * out * 0.55 * white
    a = 1 - (1 - a) * (1 - halo * holo_weak)
    if toward_right:
        # отсвет сильнее с той стороны, где стоит счастливая (справа в кадре)
        orig = np.asarray(im, np.float32) / 255
        w = np.clip((xx - x0) / (x1 - x0 + 1) * 1.1 - 0.1, 0, 1)[..., None]
        a = orig * (1 - w) + a * w
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))


def main(src, meta, dst, style="soft", mask=None, shell="holo", mask_prev=None):
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
    if mask:  # с оболочкой bloom не нужен: он выбеливает фигуры, свет даёт сама сцена
        lum = Image.new("L", im.size, 0)
    hot = Image.composite(im, Image.new("RGB", im.size), lum)
    glow = Image.new("RGB", im.size)
    for rad, k in ((W / 160, 0.9), (W / 60, 0.7), (W / 25, 0.55)):
        b = hot.filter(ImageFilter.GaussianBlur(rad))
        glow = ImageChops.add(glow, b.point(lambda v, k=k: int(v * k)))
    im = ImageChops.screen(im, glow)

    if mask:
        if shell == "neon":
            im = rainbow_shell(im, mask)
        elif shell == "holo-skin":  # свечение слабее — скин хорошо видно
            im = holo_shell(im, mask, strength=0.14, lift=0.0, white=0.45)
            if mask_prev:  # отсвет тех же цветов на прошлой версии, но слабее
                im = holo_shell(im, mask_prev, strength=0.16, lift=0.05, white=0.32, toward_right=True)
        elif shell == "holo-mid":
            im = holo_shell(im, mask, strength=0.18, lift=0.05, white=0.65)
        elif shell == "holo-strong":
            im = holo_shell(im, mask, strength=0.32, lift=0.2)
        else:
            im = holo_shell(im, mask)
    # мягкий розово-белый ореол вокруг сияющей фигуры
    halo = Image.new("RGB", im.size)
    d = ImageDraw.Draw(halo)
    cx, cy = hx, hy + body_h * 0.35
    if not mask:
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
    main(*sys.argv[1:8])
