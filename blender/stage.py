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


def build_stage(tex_dir):
    sc = bpy.context.scene
    planks = _block_mat(tex_dir, "dark_oak_planks")
    wool = _block_mat(tex_dir, "red_wool")
    pillar = _block_mat(tex_dir, "polished_blackstone_bricks")
    beam = _block_mat(tex_dir, "dark_oak_log")
    glow = _block_mat(tex_dir, "glowstone", emit=2.5)
    shroom = _block_mat(tex_dir, "shroomlight", emit=1.2)

    # пол-сцена: верх на z=0, передний край сцены перед камерой
    tiled_box("floor", -9, 9, -4, 5, -1, 0, planks)
    # занавес: колонны шерсти, чётные чуть выдвинуты — получаются складки
    for i, x in enumerate(range(-9, 9)):
        y = 3.5 if i % 2 == 0 else 3.8
        tiled_box(f"curtain{i}", x, x + 1, y, y + 1, 0, 7, wool)
    tiled_box("beam", -9, 9, 3.2, 4.2, 7, 8, beam)
    # колонны по бокам со светокамнем наверху
    for x in (-5, 4):
        tiled_box(f"pillar{x}", x, x + 1, 2.0, 3.0, 0, 3, pillar)
        tiled_box(f"pillar_glow{x}", x, x + 1, 2.0, 3.0, 3, 4, glow)
        _light("POINT", (x + 0.5, 1.7, 3.5), 90, (1.0, 0.75, 0.45), shadow_soft_size=0.5)
    # рампа: грибосветы, утопленные в передний край пола
    for x in (-3.5, 3.5):
        tiled_box(f"foot{int(x)}", x - 0.5, x + 0.5, -3.4, -2.4, -0.9, 0.08, shroom)
        _light("POINT", (x, -2.9, 0.4), 18, (1.0, 0.6, 0.3), shadow_soft_size=0.4)

    # тёмный зал
    world = sc.world
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.01, 0.008, 0.016, 1)
    bg.inputs["Strength"].default_value = 1.0

    # сценический свет: тёплый прожектор сверху, мягкий фронтальный, контровой сзади
    _light("SPOT", (0.4, -3.5, 8.5), 6500, (1.0, 0.9, 0.78), (0, 0.2, 0.6),
           spot_size=math.radians(34), spot_blend=0.55, shadow_soft_size=0.5)
    _light("AREA", (0, -9, 2.6), 150, (0.85, 0.85, 1.0), (0, 0, 1.2), size=4)
    _light("AREA", (0, 2.8, 6), 260, (1.0, 0.55, 0.7), (0, -0.5, 1.2), size=2.5)
