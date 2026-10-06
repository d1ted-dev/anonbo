"""Сцена из блоков Minecraft: пол из тёмного дуба, занавес из красной шерсти, колонны,
светящиеся блоки и сценический свет.

Текстуры блоков не хранятся в репозитории (это файлы Mojang) — их скачивает
`python3 blender/fetch_blocks.py` из официального клиента нужной версии.
"""
import math
import os

import bpy
from mathutils import Vector


def _block_mat(tex_dir, name, emit=0.0):
    key = f"blk_{name}_{emit}"
    if key in bpy.data.materials:
        return bpy.data.materials[key]
    mat = bpy.data.materials.new(key)
    mat.use_nodes = True
    n, l = mat.node_tree.nodes, mat.node_tree.links
    bsdf = n["Principled BSDF"]
    tex = n.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(os.path.abspath(os.path.join(tex_dir, name + ".png")), check_existing=True)
    tex.interpolation = "Closest"
    l.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    bsdf.inputs["Roughness"].default_value = 0.9
    if emit:
        l.new(tex.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = emit
    return mat


def tiled_box(name, x0, x1, y0, y1, z0, z1, mat):
    """Параллелепипед, на каждой грани текстура повторяется раз в 1 м — выглядит как блоки."""
    faces = [
        # (углы TL, BL, BR, TR) и оси (u, v) для UV в метрах
        ([(x0, y0, z1), (x0, y0, z0), (x1, y0, z0), (x1, y0, z1)], lambda p: (p[0], p[2])),   # -Y
        ([(x1, y1, z1), (x1, y1, z0), (x0, y1, z0), (x0, y1, z1)], lambda p: (-p[0], p[2])),  # +Y
        ([(x0, y1, z1), (x0, y1, z0), (x0, y0, z0), (x0, y0, z1)], lambda p: (-p[1], p[2])),  # -X
        ([(x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)], lambda p: (p[1], p[2])),   # +X
        ([(x0, y1, z1), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1)], lambda p: (p[0], p[1])),   # +Z
        ([(x0, y0, z0), (x0, y1, z0), (x1, y1, z0), (x1, y0, z0)], lambda p: (p[0], -p[1])),  # -Z
    ]
    verts, polys, uvs = [], [], []
    for corners, f in faces:
        i = len(verts)
        verts += corners
        polys.append((i, i + 1, i + 2, i + 3))
        uvs += [f(c) for c in corners]
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], polys)
    layer = me.uv_layers.new()
    for li, loop in enumerate(me.loops):
        layer.data[li].uv = uvs[loop.vertex_index]
    me.update()
    ob = bpy.data.objects.new(name, me)
    ob.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _light(kind, loc, energy, color, target=None, **kw):
    ld = bpy.data.lights.new(f"st_{kind}_{len(bpy.data.lights)}", kind)
    ld.energy, ld.color = energy, color
    for k, v in kw.items():
        setattr(ld, k, v)
    ob = bpy.data.objects.new(ld.name, ld)
    ob.location = loc
    bpy.context.scene.collection.objects.link(ob)
    if target is not None:
        d = Vector(target) - ob.location
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    return ob


SPOT_MAIN = ((0.4, -3.5, 8.5), (0, 0.2, 0.6))          # основной прожектор (вне кадра)
LAMPS = [(-2.5, 2.9, 4.55), (2.5, 2.9, 4.55)]           # лампы под балкой над занавесом
N_DUST = 34


def build_stage(tex_dir):
    sc = bpy.context.scene
    planks = _block_mat(tex_dir, "dark_oak_planks")
    hall = _block_mat(tex_dir, "spruce_planks")
    wool = _block_mat(tex_dir, "red_wool")
    pillar = _block_mat(tex_dir, "polished_blackstone_bricks")
    beam = _block_mat(tex_dir, "dark_oak_log")
    glow = _block_mat(tex_dir, "glowstone", emit=2.5)
    shroom = _block_mat(tex_dir, "shroomlight", emit=1.2)
    lamp = _block_mat(tex_dir, "redstone_lamp_on", emit=6.0)

    # сцена: верх на z=0, передний край y=-4, отделка кромки, ниже — пол зала
    tiled_box("floor", -9, 9, -4, 5, -1, 0, planks)
    tiled_box("edge_trim", -9, 9, -4.12, -3.88, -0.18, 0.05, pillar)
    tiled_box("hall", -12, 12, -14, -4.25, -2, -1, hall)
    # занавес: колонны шерсти, чётные чуть выдвинуты — получаются складки
    for i, x in enumerate(range(-9, 9)):
        y = 3.5 if i % 2 == 0 else 3.8
        tiled_box(f"curtain{i}", x, x + 1, y, y + 1, 0, 7, wool)
    # балка над сценой с лампами-прожекторами
    tiled_box("beam", -9, 9, 2.7, 3.5, 4.7, 5.5, beam)
    for i, (x, y, z) in enumerate(LAMPS):
        tiled_box(f"lamp{i}", x - 0.4, x + 0.4, y - 0.4, y + 0.4, z - 0.6, z + 0.15, lamp)
        _light("SPOT", (x, y - 0.45, z - 0.5), 2200, (1.0, 0.82, 0.62), (x * 0.25, -0.6, 0.0),
               spot_size=math.radians(26), spot_blend=0.35, shadow_soft_size=0.15)
    # колонны по бокам со светокамнем наверху — в кадре
    for x in (-3.9, 2.9):
        tiled_box(f"pillar{x}", x, x + 1, 1.6, 2.6, 0, 3, pillar)
        tiled_box(f"pillar_glow{x}", x, x + 1, 1.6, 2.6, 3, 4, glow)
        _light("POINT", (x + 0.5, 1.3, 3.5), 70, (1.0, 0.75, 0.45), shadow_soft_size=0.5)
    # рампа: грибосветы, утопленные в передний край
    for x in (-3.5, 3.5):
        tiled_box(f"foot{int(x)}", x - 0.5, x + 0.5, -3.9, -2.9, -0.9, 0.08, shroom)
        _light("POINT", (x, -3.4, 0.4), 18, (1.0, 0.6, 0.3), shadow_soft_size=0.4)

    # тёмный зал
    world = sc.world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.01, 0.008, 0.016, 1)
    bg.inputs["Strength"].default_value = 1.0

    # лёгкая дымка над сценой — в ней видны лучи прожекторов
    haze = bpy.data.materials.new("haze")
    haze.use_nodes = True
    hn = haze.node_tree.nodes
    hn.remove(hn["Principled BSDF"])
    vol = hn.new("ShaderNodeVolumePrincipled")
    vol.inputs["Density"].default_value = 0.045
    vol.inputs["Anisotropy"].default_value = 0.35
    haze.node_tree.links.new(vol.outputs[0], hn["Material Output"].inputs["Volume"])
    hb = tiled_box("haze", -6, 6, -4, 3.4, 0.0, 7.5, haze)
    hb.visible_shadow = False

    # основной тёплый прожектор спереди-сверху, слабая заливка, розовый контровой
    (pos, tgt) = SPOT_MAIN
    _light("SPOT", pos, 6000, (1.0, 0.9, 0.78), tgt,
           spot_size=math.radians(30), spot_blend=0.4, shadow_soft_size=0.12)
    _light("AREA", (0, -9, 2.6), 120, (0.85, 0.85, 1.0), (0, 0, 1.2), size=4)
    _light("AREA", (0, 2.8, 6), 160, (1.0, 0.55, 0.7), (0, -0.5, 1.2), size=2.5)

    # заготовка частиц: квадратные «пылинки» как в Minecraft, перемешиваются на каждом кадре
    dust = bpy.data.materials.new("dust")
    dust.use_nodes = True
    db = dust.node_tree.nodes["Principled BSDF"]
    db.inputs["Base Color"].default_value = (1, 0.9, 0.7, 1)
    db.inputs["Emission Color"].default_value = (1, 0.88, 0.65, 1)
    db.inputs["Emission Strength"].default_value = 1.4
    for i in range(N_DUST):
        ob = tiled_box(f"dust{i}", -0.018, 0.018, -0.018, 0.018, -0.018, 0.018, dust)
        ob.visible_shadow = False


def shuffle_particles(seed):
    """Разбросать пылинки внутри лучей (основной прожектор и лампы); seed — кадр."""
    import random
    rnd = random.Random(seed)
    sources = [SPOT_MAIN] + [((x, y - 0.45, z - 0.5), (x * 0.25, -0.6, 0.0)) for x, y, z in LAMPS]
    for i in range(N_DUST):
        pos, tgt = sources[0] if i < N_DUST // 2 else sources[1 + i % 2]
        p, t = Vector(pos), Vector(tgt)
        k = rnd.uniform(0.45, 0.92)               # где вдоль луча
        c = p.lerp(t, k)
        spread = (t - p).length * k * 0.14        # ширина конуса на этом расстоянии
        ob = bpy.data.objects[f"dust{i}"]
        ob.location = (c.x + rnd.uniform(-spread, spread), c.y + rnd.uniform(-spread, spread),
                       max(0.2, c.z + rnd.uniform(-spread, spread)))
        ob.rotation_euler = (rnd.uniform(0, 3), rnd.uniform(0, 3), rnd.uniform(0, 3))
        s = rnd.choice((0.7, 1.0, 1.4))
        ob.scale = (s, s, s)
