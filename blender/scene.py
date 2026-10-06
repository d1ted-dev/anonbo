"""Минecraft-ремейк арта «четыре стадии настроения» в Blender.

Запуск (Blender как python-модуль `pip install bpy`, либо `blender -b -P`):
    python3 blender/scene.py --skin skins/4ered1t.png --model slim \
        --variant glow --out renders/glow.png
"""
import argparse
import math
import sys

import bpy
from bpy_extras.object_utils import world_to_camera_view
from mathutils import Vector

PX = 1 / 16  # один пиксель скина = 1/16 м, персонаж ~2 м

# (u, v, w, h, d) в пикселях развёртки 64x64
PARTS = {
    "head":     ((0, 0, 8, 8, 8),    (32, 0, 8, 8, 8)),
    "body":     ((16, 16, 8, 12, 4), (16, 32, 8, 12, 4)),
    "arm_r":    ((40, 16, 4, 12, 4), (40, 32, 4, 12, 4)),
    "arm_l":    ((32, 48, 4, 12, 4), (48, 48, 4, 12, 4)),
    "leg_r":    ((0, 16, 4, 12, 4),  (0, 32, 4, 12, 4)),
    "leg_l":    ((16, 48, 4, 12, 4), (0, 48, 4, 12, 4)),
}


def uv(px, py):
    return (px / 64, 1 - py / 64)


def box_mesh(name, size, offset, tex, inflate):
    """Куб с UV по раскладке скина. Персонаж смотрит в -Y, его правая сторона = -X."""
    w, h, d = size
    u, v = tex
    x0, x1 = offset[0] - inflate, offset[0] + w * PX + inflate
    y0, y1 = offset[1] - inflate, offset[1] + d * PX + inflate
    z0, z1 = offset[2] - inflate, offset[2] + h * PX + inflate
    # для каждой грани: углы TL, BL, BR, TR (вид снаружи) и прямоугольник текстуры
    faces = [
        ([(x0, y0, z1), (x0, y0, z0), (x1, y0, z0), (x1, y0, z1)], (u + d, v + d, w, h)),          # front
        ([(x1, y1, z1), (x1, y1, z0), (x0, y1, z0), (x0, y1, z1)], (u + 2 * d + w, v + d, w, h)),  # back
        ([(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)], (u, v + d, d, h)),              # right
        ([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], (u + d + w, v + d, d, h)),      # left
        ([(x0, y1, z1), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1)], (u + d, v, w, d)),              # top
        ([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], (u + d + w, v, w, d)),          # bottom
    ]
    verts, polys, uvs = [], [], []
    for corners, (tx, ty, tw, th) in faces:
        i = len(verts)
        verts += corners
        polys.append((i, i + 1, i + 2, i + 3))
        uvs += [uv(tx, ty), uv(tx, ty + th), uv(tx + tw, ty + th), uv(tx + tw, ty)]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], polys)
    layer = me.uv_layers.new()
    for li, loop in enumerate(me.loops):
        layer.data[li].uv = uvs[loop.vertex_index]
    me.update()
    return me


def make_material(name, img, tint, tint_amt, brightness, glow, lift_white=0.32):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    n, l = nt.nodes, nt.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    texn = n.new("ShaderNodeTexImage")
    texn.image = img
    texn.interpolation = "Closest"
    lum = n.new("ShaderNodeRGBToBW")
    tinted = n.new("ShaderNodeMix"); tinted.data_type = "RGBA"; tinted.blend_type = "MULTIPLY"
    tinted.inputs["Factor"].default_value = 1.0
    tinted.inputs["B"].default_value = (*tint, 1)
    mix = n.new("ShaderNodeMix"); mix.data_type = "RGBA"
    mix.inputs["Factor"].default_value = tint_amt
    bright = n.new("ShaderNodeMix"); bright.data_type = "RGBA"; bright.blend_type = "MULTIPLY"
    bright.inputs["Factor"].default_value = 1.0
    bright.inputs["B"].default_value = (brightness,) * 3 + (1,)

    l.new(texn.outputs["Color"], lum.inputs["Color"])
    # «выцветшая» версия: яркость * сине-лиловый тон, слегка приподнятая
    lift = n.new("ShaderNodeMath"); lift.operation = "MULTIPLY_ADD"
    lift.inputs[1].default_value = 0.6; lift.inputs[2].default_value = 0.25
    l.new(lum.outputs["Val"], lift.inputs[0])
    l.new(lift.outputs["Value"], tinted.inputs["A"])
    l.new(texn.outputs["Color"], mix.inputs["A"])
    l.new(tinted.outputs["Result"], mix.inputs["B"])
    l.new(mix.outputs["Result"], bright.inputs["A"])
    l.new(bright.outputs["Result"], bsdf.inputs["Base Color"])
    l.new(texn.outputs["Alpha"], bsdf.inputs["Alpha"])
    bsdf.inputs["Roughness"].default_value = 0.85

    if glow > 0:
        # пастельное свечение с градиентом розовый → жёлто-зелёный (как в оригинале)
        geo = n.new("ShaderNodeNewGeometry")
        sep = n.new("ShaderNodeSeparateXYZ")
        ramp = n.new("ShaderNodeValToRGB")
        ramp.color_ramp.elements[0].position = 0.1
        ramp.color_ramp.elements[0].color = (0.78, 1.0, 0.7, 1)
        ramp.color_ramp.elements[1].position = 0.95
        ramp.color_ramp.elements[1].color = (1.0, 0.7, 0.9, 1)
        mid = ramp.color_ramp.elements.new(0.55)
        mid.color = (1.0, 0.97, 0.9, 1)
        scale = n.new("ShaderNodeMath"); scale.operation = "MULTIPLY"
        scale.inputs[1].default_value = 1 / (32 * PX)
        l.new(geo.outputs["Position"], sep.inputs["Vector"])
        l.new(sep.outputs["Z"], scale.inputs[0])
        l.new(scale.outputs["Value"], ramp.inputs["Fac"])
        # высветлить текстуру к белому и окрасить пастельным градиентом
        lifted = n.new("ShaderNodeMix"); lifted.data_type = "RGBA"
        lifted.inputs["Factor"].default_value = lift_white
        lifted.inputs["B"].default_value = (1, 1, 1, 1)
        l.new(texn.outputs["Color"], lifted.inputs["A"])
        pastel = n.new("ShaderNodeMix"); pastel.data_type = "RGBA"; pastel.blend_type = "MULTIPLY"
        pastel.inputs["Factor"].default_value = 1.0
        l.new(lifted.outputs["Result"], pastel.inputs["A"])
        l.new(ramp.outputs["Color"], pastel.inputs["B"])
        l.new(pastel.outputs["Result"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = glow
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_rainbow_material(name, img):
    """Сияющая фигура: свои цвета, высветленные до пастели, + радужный ободок по краям."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    n, l = mat.node_tree.nodes, mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    bsdf = n.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.8
    texn = n.new("ShaderNodeTexImage"); texn.image = img; texn.interpolation = "Closest"
    l.new(texn.outputs["Alpha"], bsdf.inputs["Alpha"])

    def mixc(a, b, fac, blend="MIX"):
        m = n.new("ShaderNodeMix"); m.data_type = "RGBA"; m.blend_type = blend
        m.inputs["Factor"].default_value = fac
        for sock, val in (("A", a), ("B", b)):
            if isinstance(val, tuple):
                m.inputs[sock].default_value = val
            else:
                l.new(val, m.inputs[sock])
        return m.outputs["Result"]

    # пастель: чуть меньше насыщенности, подтянуть к светло-лиловому белому
    hsv = n.new("ShaderNodeHueSaturation")
    hsv.inputs["Saturation"].default_value = 1.05
    l.new(texn.outputs["Color"], hsv.inputs["Color"])
    pastel = mixc(hsv.outputs["Color"], (0.97, 0.94, 1.0, 1), 0.36)

    # мягкий перелив: розовый сверху → жёлто-зелёный снизу (по высоте в мире)
    geo = n.new("ShaderNodeNewGeometry")
    sep = n.new("ShaderNodeSeparateXYZ"); l.new(geo.outputs["Position"], sep.inputs["Vector"])
    hz = n.new("ShaderNodeMath"); hz.operation = "MULTIPLY"; hz.inputs[1].default_value = 1 / (32 * PX)
    l.new(sep.outputs["Z"], hz.inputs[0])
    ramp = n.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.15; ramp.color_ramp.elements[0].color = (0.85, 1.0, 0.7, 1)
    ramp.color_ramp.elements[1].position = 0.95; ramp.color_ramp.elements[1].color = (1.0, 0.75, 0.9, 1)
    ramp.color_ramp.elements.new(0.55).color = (1.0, 0.97, 0.85, 1)
    l.new(hz.outputs["Value"], ramp.inputs["Fac"])
    sheen = mixc(pastel, ramp.outputs["Color"], 0.5, "MULTIPLY")
    # светится в основном сама (свет сцены почти не влияет) — так цвета не выгорают
    l.new(mixc(sheen, (0, 0, 0, 1), 0.7), bsdf.inputs["Base Color"])

    # радужный ободок: оттенок зависит от положения, сила — от угла к камере
    hue = n.new("ShaderNodeMath"); hue.operation = "MULTIPLY_ADD"
    hue.inputs[1].default_value = 0.22; hue.inputs[2].default_value = 0.1
    l.new(sep.outputs["Z"], hue.inputs[0])
    hx = n.new("ShaderNodeMath"); hx.operation = "MULTIPLY_ADD"
    hx.inputs[1].default_value = -0.35
    l.new(sep.outputs["X"], hx.inputs[0]); l.new(hue.outputs["Value"], hx.inputs[2])
    fr = n.new("ShaderNodeMath"); fr.operation = "FRACT"; l.new(hx.outputs["Value"], fr.inputs[0])
    rgb = n.new("ShaderNodeCombineColor"); rgb.mode = "HSV"
    rgb.inputs[1].default_value = 0.6; rgb.inputs[2].default_value = 1.0
    l.new(fr.outputs["Value"], rgb.inputs[0])
    lw = n.new("ShaderNodeLayerWeight"); lw.inputs["Blend"].default_value = 0.45
    pw = n.new("ShaderNodeMath"); pw.operation = "POWER"; pw.inputs[1].default_value = 2.5
    l.new(lw.outputs["Facing"], pw.inputs[0])
    # чёрный → цвет радуги по мере того, как грань отворачивается от камеры
    rim_s = n.new("ShaderNodeMix"); rim_s.data_type = "RGBA"
    l.new(pw.outputs["Value"], rim_s.inputs["Factor"])
    rim_s.inputs["A"].default_value = (0, 0, 0, 1)
    l.new(rgb.outputs["Color"], rim_s.inputs["B"])
    base_em = sheen  # светится своим цветом
    em = mixc(base_em, rim_s.outputs["Result"], 1.0, "ADD")
    l.new(em, bsdf.inputs["Emission Color"])
    bsdf.inputs["Emission Strength"].default_value = 1.6
    l.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def make_mask_material(img):
    mat = bpy.data.materials.new("mask")
    mat.use_nodes = True
    n, l = mat.node_tree.nodes, mat.node_tree.links
    n.clear()
    out = n.new("ShaderNodeOutputMaterial")
    texn = n.new("ShaderNodeTexImage"); texn.image = img; texn.interpolation = "Closest"
    em = n.new("ShaderNodeEmission"); em.inputs["Strength"].default_value = 1.0
    tr = n.new("ShaderNodeBsdfTransparent")
    mx = n.new("ShaderNodeMixShader")
    l.new(texn.outputs["Alpha"], mx.inputs["Fac"])
    l.new(tr.outputs["BSDF"], mx.inputs[1]); l.new(em.outputs["Emission"], mx.inputs[2])
    l.new(mx.outputs["Shader"], out.inputs["Surface"])
    return mat


def add_obj(name, mesh, mat, parent):
    ob = bpy.data.objects.new(name, mesh)
    ob.data.materials.append(mat)
    ob.parent = parent
    bpy.context.collection.objects.link(ob)
    return ob


def empty(name, loc, parent=None):
    e = bpy.data.objects.new(name, None)
    e.location = loc
    e.parent = parent
    bpy.context.collection.objects.link(e)
    return e


def build_character(tag, img, slim, mat, mat_overlay, pose, loc, yaw):
    """pose: углы в градусах для частей: head (pitch, yaw, roll), body_pitch, arm_r, arm_l, leg_r, leg_l (pitch, roll)."""
    arm_w = 3 if slim else 4
    root = empty(f"{tag}_root", loc)
    root.rotation_euler = (0, 0, math.radians(yaw))
    hips = empty(f"{tag}_hips", (0, 0, 12 * PX), root)
    hips.rotation_euler = (math.radians(pose["body_pitch"]), 0, math.radians(pose.get("body_roll", 0)))

    def part(key, pivot, pivot_parent, box_off, size, rot):
        piv = empty(f"{tag}_{key}_pivot", pivot, pivot_parent)
        piv.rotation_euler = tuple(math.radians(a) for a in rot)
        (bu, bv, *_), (ou, ov, *_) = PARTS[key]
        infl = 0.5 * PX if key == "head" else 0.25 * PX
        add_obj(f"{tag}_{key}", box_mesh(key, size, box_off, (bu, bv), 0), mat, piv)
        add_obj(f"{tag}_{key}_ov", box_mesh(key + "_ov", size, box_off, (ou, ov), infl), mat_overlay, piv)
        return piv

    body = part("body", (0, 0, 0), hips, (-4 * PX, -2 * PX, 0), (8, 12, 4), (0, 0, 0))
    hp, hy, hr = pose["head"]
    part("head", (0, 0, 12 * PX), hips, (-4 * PX, -4 * PX, 0), (8, 8, 8), (hp, hr, hy))
    ap, ar = pose["arm_r"]
    part("arm_r", (-(4 + arm_w / 2) * PX, 0, 10 * PX), hips,
         (-arm_w / 2 * PX, -2 * PX, -10 * PX), (arm_w, 12, 4), (ap, ar, 0))
    ap, ar = pose["arm_l"]
    part("arm_l", ((4 + arm_w / 2) * PX, 0, 10 * PX), hips,
         (-arm_w / 2 * PX, -2 * PX, -10 * PX), (arm_w, 12, 4), (ap, ar, 0))
    for key, x in (("leg_r", -2), ("leg_l", 2)):
        lp, lr = pose[key]
        part(key, (x * PX, 0, 12 * PX), root, (-2 * PX, -2 * PX, -12 * PX), (4, 12, 4), (lp, lr, 0))
    # голова привязана к hips — тело наклоняется вместе с ней
    return root


# Позы: от поникшей к сияющей. Положительный pitch = наклон вперёд.
POSES = [
    dict(head=(38, 0, -6), body_pitch=14, arm_r=(8, 4), arm_l=(-6, -4), leg_r=(-14, 0), leg_l=(14, 0)),
    dict(head=(24, 12, 4), body_pitch=8, arm_r=(16, 3), arm_l=(-14, -3), leg_r=(18, 0), leg_l=(-18, 0)),
    dict(head=(12, -30, -6), body_pitch=3, arm_r=(-14, 4), arm_l=(16, -4), leg_r=(-20, 0), leg_l=(20, 0)),
    dict(head=(-10, -8, 8), body_pitch=-2, body_roll=-2, arm_r=(10, 6), arm_l=(-18, -24),
         leg_r=(12, 0), leg_l=(-12, 0)),
]
# тон (лиловый), сила «выцветания», яркость, свечение
LOOKS = [
    ((0.38, 0.36, 0.85), 0.92, 0.45, 0.0),
    ((0.45, 0.48, 0.95), 0.8, 0.65, 0.0),
    ((0.6, 0.68, 1.0), 0.5, 0.85, 0.0),
    ((1.0, 1.0, 1.0), 0.0, 0.5, 1.1),
]

VARIANTS = {
    # камера: позиция, цель, фокусное; расстановка фигур
    "glow":    dict(cam=(3.4, -8.6, 1.9), target=(-1.0, 0.7, 1.2), lens=62, outline=False, floor=False),
    "cartoon": dict(cam=(3.4, -8.6, 1.9), target=(-1.0, 0.7, 1.2), lens=62, outline=True, floor=False),
    "march":   dict(cam=(0.4, -10.5, 1.3), target=(-1.0, 0.6, 1.1), lens=55, outline=True, floor=True),
    "closeup": dict(cam=(2.6, -5.4, 2.0), target=(-0.35, 0.3, 1.7), lens=55, outline=False, floor=True),
}


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--skin", required=True)
    ap.add_argument("--model", default="slim", choices=["slim", "classic"])
    ap.add_argument("--variant", default="glow", choices=list(VARIANTS))
    ap.add_argument("--out", required=True)
    ap.add_argument("--samples", type=int, default=96)
    ap.add_argument("--res", type=int, default=1600)
    ap.add_argument("--style", default="soft", choices=["soft", "bright"],
                    help="bright — более яркое сияние и отражающий пол")
    ap.add_argument("--shell", action="store_true",
                    help="сияющая фигура со своими цветами и радужной оболочкой")
    ap.add_argument("--mask", help="куда отрендерить маску силуэта сияющей фигуры")
    ap.add_argument("--meta", help="куда записать экранные координаты сияющей головы")
    a = ap.parse_args(argv)
    cfg = dict(VARIANTS[a.variant])
    bright = a.style == "bright"
    if bright and a.variant == "closeup":
        cfg.update(cam=(2.6, -5.2, 1.9), target=(-0.2, 0.3, 1.55))

    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    img = bpy.data.images.load(a.skin)
    img.alpha_mode = "STRAIGHT"

    # фигуры по диагонали: дальняя слева, сияющая — ближе всех справа
    spots = [(-3.0, 1.9), (-1.75, 1.15), (-0.55, 0.45), (0.75, -0.2)]
    if a.variant == "march":
        spots = [(-3.3, 1.0), (-1.9, 0.7), (-0.5, 0.4), (0.95, 0.1)]
    yaw = 42 if a.variant != "march" else 70
    heads = []
    for i, (pose, (tint, amt, br, glow), (x, y)) in enumerate(zip(POSES, LOOKS, spots)):
        lw = 0.42 if bright else 0.32
        if a.shell and glow > 0:
            m = mo = make_rainbow_material(f"rb{i}", img)
        else:
            m = make_material(f"m{i}", img, tint, amt, br, glow, lw)
            mo = make_material(f"mo{i}", img, tint, amt, br, glow, lw)
        root = build_character(f"c{i}", img, a.model == "slim", m, mo, pose, (x, y, 0), yaw)
        heads.append(root)

    # мир: тёмно-синяя ночь
    world = bpy.data.worlds.new("w"); sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.012, 0.014, 0.035, 1)
    bg.inputs["Strength"].default_value = 1.0

    def light(kind, loc, energy, color, size=1.0, target=None):
        ld = bpy.data.lights.new(kind + str(len(bpy.data.lights)), kind)
        ld.energy = energy; ld.color = color
        if kind == "AREA":
            ld.size = size
        elif kind == "POINT":
            ld.shadow_soft_size = size
        ob = bpy.data.objects.new(ld.name, ld); ob.location = loc
        sc.collection.objects.link(ob)
        if target:
            look_at(ob, target)
        return ob

    gx, gy = spots[3]
    # свет исходит от сияющей фигуры и гаснет к дальним
    if bright:
        light("POINT", (gx - 0.9, gy - 0.6, 1.4), 260, (1.0, 0.85, 0.92), 0.6)
    else:
        light("POINT", (gx - 0.5, gy - 0.9, 1.5), 150, (1.0, 0.85, 0.92), 0.6)
    # холодный лунный заполняющий свет и контровой
    light("AREA", (2.5, -6, 5), 120, (0.55, 0.6, 1.0), 4, (-1, 1, 1))
    light("AREA", (-2, 5, 3.5), 200, (0.5, 0.45, 1.0), 3, (-1, 1, 1.2))

    if cfg["floor"]:
        bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -0.002))
        fl = bpy.context.active_object
        fm = bpy.data.materials.new("floor"); fm.use_nodes = True
        p = fm.node_tree.nodes["Principled BSDF"]
        p.inputs["Base Color"].default_value = (0.03, 0.03, 0.06, 1)
        p.inputs["Roughness"].default_value = 0.35
        fl.data.materials.append(fm)
        fl.is_shadow_catcher = not bright  # soft: без видимой линии горизонта

    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = cfg["lens"]
    cam = bpy.data.objects.new("cam", cam_d); cam.location = cfg["cam"]
    sc.collection.objects.link(cam); sc.camera = cam
    look_at(cam, cfg["target"])

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = a.samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = a.res
    sc.render.resolution_y = int(a.res * 9 / 16)
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    if cfg["outline"]:
        sc.render.use_freestyle = True
        sc.render.line_thickness = 1.6
        fs = sc.view_layers[0].freestyle_settings
        ls = fs.linesets[0] if len(fs.linesets) else fs.linesets.new("outline")
        if ls.linestyle is None:
            ls.linestyle = bpy.data.linestyles.new("outline")
        ls.linestyle.color = (0.04, 0.04, 0.09)
        ls.select_by_visibility = True
        ls.select_silhouette = True
        ls.select_border = True
        ls.select_crease = False

    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = a.out
    bpy.ops.render.render(write_still=True)

    if a.mask:
        # второй быстрый проход: только сияющая фигура, белым по чёрному
        mm = make_mask_material(img)
        for ob in sc.objects:
            if ob.type == "MESH":
                if ob.name.startswith("c3_"):
                    ob.data.materials[0] = mm
                else:
                    ob.hide_render = True
        bg.inputs["Color"].default_value = (0, 0, 0, 1)
        sc.render.use_freestyle = False
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.look = "None"
        sc.cycles.samples = 8
        sc.cycles.use_denoising = False
        sc.render.filepath = a.mask
        bpy.ops.render.render(write_still=True)

    if a.meta:
        import json
        bpy.context.view_layer.update()
        head = bpy.data.objects["c3_head"]
        center = head.matrix_world @ Vector((0, 0, 4 * PX))
        p = world_to_camera_view(sc, cam, center)
        top = world_to_camera_view(sc, cam, head.matrix_world @ Vector((0, 0, 9 * PX)))
        feet = world_to_camera_view(sc, cam, bpy.data.objects["c3_root"].matrix_world.translation)
        json.dump({"head": [p.x, 1 - p.y], "top": [top.x, 1 - top.y], "feet": [feet.x, 1 - feet.y]},
                  open(a.meta, "w"))


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    main(argv)
