"""Minecraft-персонаж со сгибами (как риги в Mine-imator): локти, колени и сгиб корпуса.

Руки и ноги делятся на две половины по 6 пикселей; нижняя половина продлена на 1 пиксель
вверх внутрь верхней, поэтому на сгибе нет дыры. Корпус делится на низ и верх (грудь),
к груди крепятся голова и руки.

Поза (все углы в градусах, отсутствующий ключ = 0):
    loc=(x, y, z)  yaw — разворот (+ лицом к +X)
    hips=(вперёд, вбок, поворот)   chest=(...)   head=(кивок, наклон, поворот)
    arm_r / arm_l = (вперёд−/назад+, в сторону, скрутка)   elbow_r / elbow_l = сгиб (+)
    leg_r / leg_l = (вперёд−/назад+, в сторону)              knee_r / knee_l = сгиб (+)
Для правой руки/ноги «в сторону наружу» = +, для левой = −.
"""
import math

import bpy

PX = 1 / 16
LIMB = 12

# (u, v, w, h, d) развёртки 64x64: базовый слой и верхний слой
TEX = {
    "head":  ((0, 0, 8, 8, 8),    (32, 0, 8, 8, 8)),
    "body":  ((16, 16, 8, 12, 4), (16, 32, 8, 12, 4)),
    "arm_r": ((40, 16, 4, 12, 4), (40, 32, 4, 12, 4)),
    "arm_l": ((32, 48, 4, 12, 4), (48, 48, 4, 12, 4)),
    "leg_r": ((0, 16, 4, 12, 4),  (0, 32, 4, 12, 4)),
    "leg_l": ((16, 48, 4, 12, 4), (0, 48, 4, 12, 4)),
}


def _uv(px, py):
    return (px / 64, 1 - py / 64)


def seg_mesh(name, tex, w, d, rows, x0, y0, z_top, inflate=0.0, shrink=0.0):
    """Кусок бокса: строки rows=(r0, r1) боковых граней текстуры (сверху вниз).
    Верхняя грань — только если r0 == 0, нижняя — только если r1 == полной высоте."""
    u, v, _, H, _ = tex
    r0, r1 = rows
    e = inflate - shrink
    X0, X1 = x0 - e, x0 + w * PX + e
    Y0, Y1 = y0 - e, y0 + d * PX + e
    Z1 = z_top + (inflate if r0 == 0 else 0)
    Z0 = z_top - (r1 - r0) * PX - (inflate if r1 == H else 0)
    sv = v + d + r0     # первая строка боковых граней
    sh = r1 - r0
    faces = [
        ([(X0, Y0, Z1), (X0, Y0, Z0), (X1, Y0, Z0), (X1, Y0, Z1)], (u + d, sv, w, sh)),           # перед
        ([(X1, Y1, Z1), (X1, Y1, Z0), (X0, Y1, Z0), (X0, Y1, Z1)], (u + 2 * d + w, sv, w, sh)),   # зад
        ([(X0, Y1, Z1), (X0, Y1, Z0), (X0, Y0, Z0), (X0, Y0, Z1)], (u, sv, d, sh)),               # правый бок
        ([(X1, Y0, Z1), (X1, Y0, Z0), (X1, Y1, Z0), (X1, Y1, Z1)], (u + d + w, sv, d, sh)),       # левый бок
    ]
    if r0 == 0:
        faces.append(([(X0, Y1, Z1), (X0, Y0, Z1), (X1, Y0, Z1), (X1, Y1, Z1)], (u + d, v, w, d)))
    if r1 == H:
        faces.append(([(X0, Y0, Z0), (X0, Y1, Z0), (X1, Y1, Z0), (X1, Y0, Z0)], (u + d + w, v, w, d)))
    verts, polys, uvs = [], [], []
    for corners, (tx, ty, tw, th) in faces:
        i = len(verts)
        verts += corners
        polys.append((i, i + 1, i + 2, i + 3))
        uvs += [_uv(tx, ty), _uv(tx, ty + th), _uv(tx + tw, ty + th), _uv(tx + tw, ty)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], polys)
    layer = me.uv_layers.new()
    for li, loop in enumerate(me.loops):
        layer.data[li].uv = uvs[loop.vertex_index]
    me.update()
    return me


def _empty(name, loc, parent):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.parent = parent
    e.empty_display_size = 0.05
    bpy.context.scene.collection.objects.link(e)
    return e


def _obj(name, me, mat, parent):
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    ob.parent = parent
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build(tag, slim, mat, mat_ov):
    """Собрать персонажа. Возвращает корневой empty «{tag}_root»."""
    aw = 3 if slim else 4
    root = _empty(f"{tag}_root", (0, 0, 0), None)
    hips = _empty(f"{tag}_hips", (0, 0, 12 * PX), root)
    chest = _empty(f"{tag}_chest", (0, 0, 6 * PX), hips)

    def piece(name, key, piv, w, d, rows, x0, y0, z_top, inflate, shrink=0.0):
        base, ov = TEX[key]
        if key.startswith("arm"):
            base = (base[0], base[1], aw, base[3], base[4])
            ov = (ov[0], ov[1], aw, ov[3], ov[4])
        _obj(f"{tag}_{name}", seg_mesh(name, base, w, d, rows, x0, y0, z_top, 0, shrink), mat, piv)
        _obj(f"{tag}_{name}_ov", seg_mesh(name + "_ov", ov, w, d, rows, x0, y0, z_top, inflate, shrink),
             mat_ov, piv)

    # корпус: низ на hips, верх на chest (сгиб на середине)
    piece("body_lo", "body", hips, 8, 4, (6, 12), -4 * PX, -2 * PX, 6 * PX, 0.25 * PX)
    piece("body_hi", "body", chest, 8, 4, (0, 6), -4 * PX, -2 * PX, 6 * PX, 0.25 * PX)
    head = _empty(f"{tag}_head_pivot", (0, 0, 6 * PX), chest)
    piece("head", "head", head, 8, 8, (0, 8), -4 * PX, -4 * PX, 8 * PX, 0.5 * PX)

    for side, sx in (("r", -1), ("l", 1)):
        sh = _empty(f"{tag}_arm_{side}", (sx * (4 + aw / 2) * PX, 0, 4 * PX), chest)
        piece(f"arm_{side}_up", f"arm_{side}", sh, aw, 4, (0, 6), -aw / 2 * PX, -2 * PX, 2 * PX, 0.25 * PX)
        el = _empty(f"{tag}_elbow_{side}", (0, 0, -4 * PX), sh)
        piece(f"arm_{side}_lo", f"arm_{side}", el, aw, 4, (5, 12), -aw / 2 * PX, -2 * PX, 1 * PX,
              0.25 * PX, shrink=0.02 * PX)
        hp = _empty(f"{tag}_leg_{side}", (sx * 2 * PX, 0, 12 * PX), root)
        piece(f"leg_{side}_up", f"leg_{side}", hp, 4, 4, (0, 6), -2 * PX, -2 * PX, 0, 0.25 * PX)
        kn = _empty(f"{tag}_knee_{side}", (0, 0, -6 * PX), hp)
        piece(f"leg_{side}_lo", f"leg_{side}", kn, 4, 4, (5, 12), -2 * PX, -2 * PX, 1 * PX,
              0.25 * PX, shrink=0.02 * PX)
    return root


JOINTS = ["root", "hips", "chest", "head_pivot", "arm_r", "arm_l", "elbow_r", "elbow_l",
          "leg_r", "leg_l", "knee_r", "knee_l"]


def foot_height(p):
    """Насколько поднять/опустить корень, чтобы ниже стоящая стопа стояла на полу (по z)."""
    r = math.radians
    best = None
    for s in ("r", "l"):
        lp, lr = (list(p.get(f"leg_{s}", (0, 0))) + [0, 0])[:2]
        k = p.get(f"knee_{s}", 0)
        hp = p.get("hips", (0, 0, 0))[0] * 0  # наклон таза ног не двигает (ноги на корне)
        # бедро 6 px от сустава, голень 6 px; угол от вертикали
        a1 = r(lp)
        a2 = r(lp + k)
        drop = 6 * PX * math.cos(a1) * math.cos(r(lr)) + 6 * PX * math.cos(a2) * math.cos(r(lr))
        best = drop if best is None else max(best, drop)
    return 12 * PX - best


def set_pose(tag, p, ground=True):
    """Применить позу. При ground=True корень опускается, чтобы опорная нога стояла на полу."""
    o = bpy.data.objects
    r = math.radians

    def tri(key):
        v = list(p.get(key, (0, 0, 0)))
        return (v + [0, 0, 0])[:3]

    x, y, z = (list(p.get("loc", (0, 0, 0))) + [0, 0, 0])[:3]
    if ground:
        z -= foot_height(p)
    o[f"{tag}_root"].location = (x, y, z)
    o[f"{tag}_root"].rotation_euler = (0, 0, r(p.get("yaw", 0)))
    o[f"{tag}_hips"].rotation_euler = tuple(r(a) for a in tri("hips"))
    o[f"{tag}_chest"].rotation_euler = tuple(r(a) for a in tri("chest"))
    hp, hr, hy = tri("head")
    o[f"{tag}_head_pivot"].rotation_euler = (r(hp), r(hr), r(hy))
    for s in ("r", "l"):
        a = tri(f"arm_{s}")
        o[f"{tag}_arm_{s}"].rotation_euler = (r(a[0]), r(a[1]), r(a[2]))
        o[f"{tag}_elbow_{s}"].rotation_euler = (r(-p.get(f"elbow_{s}", 0)), 0, 0)
        lg = tri(f"leg_{s}")
        o[f"{tag}_leg_{s}"].rotation_euler = (r(lg[0]), r(lg[1]), 0)
        o[f"{tag}_knee_{s}"].rotation_euler = (r(p.get(f"knee_{s}", 0)), 0, 0)


def key_pose(tag, frame):
    o = bpy.data.objects
    for j in JOINTS:
        ob = o[f"{tag}_{j}"]
        ob.keyframe_insert("location", frame=frame)
        ob.keyframe_insert("rotation_euler", frame=frame)
