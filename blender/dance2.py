"""Танец в стиле Minecraft-анимаций (Mine-imator): риг со сгибами, замахи/проскоки/паузы,
несколько камер со склейками. Пока — вступление (первые 7 секунд).

    python3 blender/dance2.py --left skins/friend.png --right skins/4ered1t.png \
        --stage blocks --audio original.mp4 --out renders/dance2_intro.mp4
"""
import argparse
import math
import os
import subprocess
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rig  # noqa: E402
from scene import look_at, make_material  # noqa: E402

FPS = 30

# --- позы ------------------------------------------------------------------------------
# L — белая (стоит слева), R — твой скин (подходит справа). Кадры — с 1.

def L_pose(f):
    """Вступление белой: стоит → замечает → вздрагивает → тянет руку → хватает → смеётся."""
    base = {"loc": (-0.95, 0, 0), "yaw": 30, "head": (14, 0, -18),
            "arm_r": (-20, -12, 0), "elbow_r": 105, "arm_l": (4, -4, 0), "elbow_l": 12,
            "leg_r": (0, 3), "leg_l": (0, -3), "knee_l": 6}
    keys = {
        1: base,
        14: {**base, "head": (18, 0, -20)},                                   # чуть опустила голову
        20: {**base, "head": (2, 0, 26), "chest": (0, 0, 4)},                 # бросила взгляд на R
        24: {**base, "head": (0, 0, 30), "chest": (0, 0, 5)},
        52: {**base, "head": (2, 3, 28), "chest": (0, 0, 5)},
        64: {**base, "yaw": 55, "head": (4, 6, 12), "chest": (0, 0, 6)},       # повернулась к нему
        94: {**base, "yaw": 58, "head": (2, 6, 10), "chest": (0, 0, 6)},
        # R рванул — вздрогнула: отшатнулась, рука выше к груди, шаг назад
        100: {**base, "loc": (-1.02, 0, 0), "yaw": 60, "hips": (-6, 0, 0), "chest": (-12, 0, 0),
              "head": (-12, 0, 0), "arm_r": (-30, -18, 0), "elbow_r": 135, "arm_l": (14, -12, 0),
              "elbow_l": 25, "leg_r": (16, 3), "knee_r": 12},
        104: {**base, "loc": (-1.04, 0, 0), "yaw": 60, "hips": (-8, 0, 0), "chest": (-15, 0, 0),
              "head": (-14, 0, 0), "arm_r": (-32, -18, 0), "elbow_r": 138, "arm_l": (18, -14, 0),
              "elbow_l": 30, "leg_r": (18, 3), "knee_r": 14},
        114: {**base, "loc": (-1.04, 0, 0), "yaw": 62, "hips": (-4, 0, 0), "chest": (-8, 0, 0),
              "head": (-6, 10, 0), "arm_r": (-28, -16, 0), "elbow_r": 128, "leg_r": (12, 3), "knee_r": 8},
        # колеблется, потом смягчается
        128: {**base, "loc": (-1.03, 0, 0), "yaw": 64, "chest": (2, 0, 0), "head": (6, -8, 0),
              "arm_r": (-22, -10, 0), "elbow_r": 80, "leg_r": (6, 3)},
        140: {**base, "loc": (-0.98, 0, 0), "yaw": 70, "hips": (4, 0, 0), "chest": (6, 0, 0),
              "head": (8, -4, 0), "arm_r": (-45, -4, 0), "elbow_r": 45, "leg_l": (-14, -3), "knee_l": 10},
        # тянет руку и шлёпает по его руке (быстро)
        148: {**base, "loc": (-0.86, 0, 0), "yaw": 74, "hips": (6, 0, 0), "chest": (8, 0, 0),
              "head": (2, 0, 0), "arm_r": (-74, 0, 0), "elbow_r": 18, "leg_l": (-18, -3), "knee_l": 14},
        152: {**base, "loc": (-0.8, 0, 0), "yaw": 76, "hips": (6, 0, 0), "chest": (10, 0, 0),
              "head": (0, 0, 0), "arm_r": (-86, 2, 0), "elbow_r": 6, "leg_l": (-20, -3), "knee_l": 14},
        # схватила — рука чуть отскочила и встала (проскок)
        156: {**base, "loc": (-0.8, 0, 0), "yaw": 76, "hips": (2, 0, 0), "chest": (-4, 0, 0),
              "head": (8, 0, 0), "arm_r": (-68, 2, 0), "elbow_r": 26, "leg_l": (-14, -3), "knee_l": 10},
        164: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "chest": (0, 0, 0), "head": (10, 0, 0),
              "arm_r": (-62, 2, 0), "elbow_r": 22, "leg_r": (-8, 3), "knee_r": 6},
        # смеётся: голова назад, пружинит на коленях
        176: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "chest": (-4, 0, 0), "head": (-6, 0, 0),
              "arm_r": (-60, 2, 0), "elbow_r": 24, "arm_l": (-30, -10, 0), "elbow_l": 70},
        182: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "chest": (-10, 0, 0), "head": (-24, 0, 0),
              "arm_r": (-60, 2, 0), "elbow_r": 24, "arm_l": (-35, -12, 0), "elbow_l": 85},
        190: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "hips": (8, 0, 0), "chest": (4, 0, 0), "head": (6, 0, 0),
              "arm_r": (-60, 2, 0), "elbow_r": 28, "arm_l": (-40, -10, 0), "elbow_l": 80,
              "leg_r": (-14, 3), "knee_r": 30, "leg_l": (-14, -3), "knee_l": 30},
        196: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "chest": (-6, 0, 0), "head": (-12, 0, 0),
              "arm_r": (-62, 2, 0), "elbow_r": 22, "arm_l": (-40, -10, 0), "elbow_l": 80},
        203: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "hips": (8, 0, 0), "chest": (4, 0, 0), "head": (4, 0, 0),
              "arm_r": (-60, 2, 0), "elbow_r": 28, "arm_l": (-40, -10, 0), "elbow_l": 80,
              "leg_r": (-12, 3), "knee_r": 26, "leg_l": (-12, -3), "knee_l": 26},
        210: {**base, "loc": (-0.86, 0, 0), "yaw": 78, "chest": (-3, 0, 0), "head": (-4, 0, 0),
              "arm_r": (-62, 2, 0), "elbow_r": 22, "arm_l": (-40, -10, 0), "elbow_l": 80},
    }
    return keys


def R_pose(f):
    """Вступление твоего персонажа: понуро стоит → присед-замах → рывок с рукой → выпрямляется."""
    slump = {"loc": (1.45, 0.05, 0), "yaw": -62, "hips": (6, 0, 0), "chest": (18, 0, 0), "head": (28, 0, 0),
             "arm_r": (8, 4, 0), "elbow_r": 12, "arm_l": (6, -4, 0), "elbow_l": 15,
             "leg_r": (0, 3), "leg_l": (0, -3), "knee_r": 6}
    keys = {
        1: slump,
        40: {**slump, "head": (32, 4, 0), "chest": (20, 0, 0)},
        58: {**slump, "head": (38, 6, 0), "chest": (22, 0, 0)},                 # совсем сник
        # подготовка: медленный присед, руки назад
        72: {**slump, "hips": (14, 0, 0), "chest": (22, 0, 0), "head": (10, 0, 0),
             "arm_r": (30, 8, 0), "elbow_r": 20, "arm_l": (28, -8, 0), "elbow_l": 20,
             "leg_r": (-26, 3), "knee_r": 45, "leg_l": (-20, -3), "knee_l": 40},
        88: {**slump, "hips": (22, 0, 0), "chest": (24, 0, 0), "head": (-6, 0, 0),
             "arm_r": (45, 10, 0), "elbow_r": 25, "arm_l": (42, -10, 0), "elbow_l": 22,
             "leg_r": (-42, 3), "knee_r": 75, "leg_l": (-36, -3), "knee_l": 70},
        # РЫВОК (6 кадров) с рукой вперёд
        94: {"loc": (0.82, 0.02, 0), "yaw": -70, "hips": (30, 0, 0), "chest": (14, 0, 0), "head": (-16, 0, 0),
             "arm_l": (-92, 0, 0), "elbow_l": 4, "arm_r": (40, 8, 0), "elbow_r": 30,
             "leg_r": (34, 3), "knee_r": 40, "leg_l": (-38, -3), "knee_l": 18},
        # проскок вперёд и возврат
        98: {"loc": (0.74, 0.02, 0), "yaw": -71, "hips": (34, 0, 0), "chest": (16, 0, 0), "head": (-20, 0, 0),
             "arm_l": (-98, 0, 0), "elbow_l": 2, "arm_r": (46, 8, 0), "elbow_r": 34,
             "leg_r": (38, 3), "knee_r": 44, "leg_l": (-42, -3), "knee_l": 20},
        108: {"loc": (0.78, 0.02, 0), "yaw": -72, "hips": (30, 0, 0), "chest": (14, 0, 0), "head": (-14, 0, 0),
              "arm_l": (-90, 0, 0), "elbow_l": 6, "arm_r": (38, 8, 0), "elbow_r": 30,
              "leg_r": (34, 3), "knee_r": 40, "leg_l": (-38, -3), "knee_l": 18},
        # держит руку, ждёт (рука чуть подрагивает)
        124: {"loc": (0.78, 0.02, 0), "yaw": -72, "hips": (28, 0, 0), "chest": (14, 0, 0), "head": (-18, 4, 0),
              "arm_l": (-86, 2, 0), "elbow_l": 10, "arm_r": (34, 8, 0), "elbow_r": 28,
              "leg_r": (32, 3), "knee_r": 38, "leg_l": (-36, -3), "knee_l": 18},
        146: {"loc": (0.62, 0.02, 0), "yaw": -73, "hips": (24, 0, 0), "chest": (12, 0, 0), "head": (-20, 2, 0),
              "arm_l": (-84, 0, 0), "elbow_l": 8, "arm_r": (30, 8, 0), "elbow_r": 26,
              "leg_r": (28, 3), "knee_r": 34, "leg_l": (-32, -3), "knee_l": 16},
        # она шлёпнула — дёрнулся и выпрямился, шаг к ней
        153: {"loc": (0.56, 0.02, 0), "yaw": -74, "hips": (16, 0, 0), "chest": (6, 0, 0), "head": (-8, 0, 0),
              "arm_l": (-80, 0, 0), "elbow_l": 12, "arm_r": (24, 8, 0), "elbow_r": 22,
              "leg_r": (20, 3), "knee_r": 26, "leg_l": (-20, -3), "knee_l": 12},
        160: {"loc": (0.52, 0.02, 0), "yaw": -76, "hips": (2, 0, 0), "chest": (-4, 0, 0), "head": (2, 0, 0),
              "arm_l": (-64, 0, 0), "elbow_l": 24, "arm_r": (8, 6, 0), "elbow_r": 16,
              "leg_r": (-10, 3), "knee_r": 10, "leg_l": (12, -3), "knee_l": 14},
        168: {"loc": (0.56, 0.02, 0), "yaw": -78, "chest": (0, 0, 0), "head": (6, 0, 0),
              "arm_l": (-62, 0, 0), "elbow_l": 22, "arm_r": (6, 6, 0), "elbow_r": 14},
        # смеётся вместе с ней (на 2 кадра позже — «нахлёст»)
        184: {"loc": (0.56, 0.02, 0), "yaw": -78, "chest": (-10, 0, 0), "head": (-22, 0, 0),
              "arm_l": (-60, 0, 0), "elbow_l": 24, "arm_r": (-25, 12, 0), "elbow_r": 80},
        192: {"loc": (0.56, 0.02, 0), "yaw": -78, "hips": (8, 0, 0), "chest": (4, 0, 0), "head": (6, 0, 0),
              "arm_l": (-60, 0, 0), "elbow_l": 28, "arm_r": (-30, 12, 0), "elbow_r": 85,
              "leg_r": (-14, 3), "knee_r": 30, "leg_l": (-14, -3), "knee_l": 30},
        198: {"loc": (0.56, 0.02, 0), "yaw": -78, "chest": (-6, 0, 0), "head": (-12, 0, 0),
              "arm_l": (-62, 0, 0), "elbow_l": 22, "arm_r": (-30, 12, 0), "elbow_r": 85},
        205: {"loc": (0.56, 0.02, 0), "yaw": -78, "hips": (8, 0, 0), "chest": (4, 0, 0), "head": (4, 0, 0),
              "arm_l": (-60, 0, 0), "elbow_l": 28, "arm_r": (-30, 12, 0), "elbow_r": 85,
              "leg_r": (-12, 3), "knee_r": 26, "leg_l": (-12, -3), "knee_l": 26},
        210: {"loc": (0.56, 0.02, 0), "yaw": -78, "chest": (-3, 0, 0), "head": (-4, 0, 0),
              "arm_l": (-62, 0, 0), "elbow_l": 22, "arm_r": (-30, 12, 0), "elbow_r": 85},
    }
    return keys


# --- камеры: (первый кадр, позиция, цель, фокусное) -----------------------------------
SHOTS = [
    (1,   (-0.35, -2.4, 0.95), (-0.95, 0.0, 1.62), 40),   # крупно снизу на белую
    (30,  (-2.9, -1.55, 2.15), (1.3, 0.1, 1.0), 42),     # из-за её плеча на тебя
    (90,  (0.25, -5.4, 1.35), (0.0, 0.0, 1.0), 38),       # средний сбоку: рывок и реакция
    (150, (-0.15, -2.0, 1.15), (-0.12, -0.35, 1.22), 45),  # крупно руки
    (172, (-0.1, -3.4, 1.7), (-0.15, 0.0, 1.5), 42),      # двое, смеются
]


def build(left, right, stage):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
    for tag, path in (("L", left), ("R", right)):
        img = bpy.data.images.load(os.path.abspath(path)); img.alpha_mode = "STRAIGHT"
        rig.build(tag, True, make_material(tag + "_m", img, (1, 1, 1), 0, 1, 0),
                  make_material(tag + "_mo", img, (1, 1, 1), 0, 1, 0))
    from stage import build_stage, animate_dust
    build_stage(os.path.abspath(stage))

    for tag, keys in (("L", L_pose(0)), ("R", R_pose(0))):
        for f in sorted(keys):
            rig.set_pose(tag, keys[f])
            rig.key_pose(tag, f)
    # «живое» дыхание поверх ключей: лёгкий шум на груди и голове
    for tag in ("L", "R"):
        for name, idx, strength, scale in (("chest", 0, 0.03, 28), ("head_pivot", 2, 0.04, 45),
                                          ("head_pivot", 0, 0.025, 35)):
            ob = bpy.data.objects[f"{tag}_{name}"]
            for fc in _fcurves(ob):
                if fc.data_path == "rotation_euler" and fc.array_index == idx:
                    m = fc.modifiers.new("NOISE"); m.strength = strength; m.scale = scale
                    m.phase = hash(tag + name) % 100

    for i, (f, loc, tgt, lens) in enumerate(SHOTS):
        cd = bpy.data.cameras.new(f"shot{i}"); cd.lens = lens
        cam = bpy.data.objects.new(f"shot{i}", cd); cam.location = loc
        sc.collection.objects.link(cam); look_at(cam, tgt)
        mk = sc.timeline_markers.new(f"shot{i}", frame=f); mk.camera = cam
    sc.camera = bpy.data.objects["shot0"]
    sc.frame_start, sc.frame_end = 1, 210
    sc.render.fps = FPS
    animate_dust(sc.frame_end)
    return sc


def _fcurves(ob):
    act = ob.animation_data.action if ob.animation_data else None
    if not act:
        return []
    if hasattr(act, "fcurves") and len(act.fcurves):
        return list(act.fcurves)
    return [fc for layer in act.layers for st in layer.strips for bag in st.channelbags for fc in bag.fcurves]


def save_blend(sc, path, audio, res, samples):
    """.blend для рендера на своей видеокарте: звук упакован, вывод сразу в mp4 со звуком."""
    from scene import set_bloom
    # мягкий bloom вокруг ламп и светокамня
    ng = bpy.data.node_groups.new("Finish", "CompositorNodeTree")
    ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
    rl = ng.nodes.new("CompositorNodeRLayers")
    glare = ng.nodes.new("CompositorNodeGlare")
    out = ng.nodes.new("NodeGroupOutput")
    set_bloom(glare)
    for sock, val in (("Threshold", 1.2), ("Strength", 0.45), ("Size", 0.6)):
        if sock in glare.inputs:
            glare.inputs[sock].default_value = val
    ng.links.new(rl.outputs["Image"], glare.inputs["Image"])
    ng.links.new(glare.outputs["Image"], out.inputs[0])
    sc.compositing_node_group = ng
    sc.render.use_compositing = True
    if audio:
        wav = os.path.splitext(os.path.abspath(path))[0] + "_audio.wav"
        total = (sc.frame_end - sc.frame_start + 1) / FPS
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", audio, "-vn", "-t", f"{total:.3f}", wav], check=True)
        se = sc.sequence_editor_create()
        st = se.strips.new_sound("music", wav, 1, 1)
        st.sound.pack()
    sc.cycles.device = "GPU"
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.render.image_settings.media_type = "VIDEO"
    sc.render.image_settings.file_format = "FFMPEG"
    sc.render.ffmpeg.format = "MPEG4"
    sc.render.ffmpeg.codec = "H264"
    sc.render.ffmpeg.constant_rate_factor = "HIGH"
    sc.render.ffmpeg.audio_codec = "AAC"
    sc.render.filepath = "//render/dance2_intro.mp4"
    sc.frame_set(1)
    bpy.ops.file.pack_all()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(path), compress=True)
    print("blend", path)


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True)
    ap.add_argument("--right", required=True)
    ap.add_argument("--stage", required=True)
    ap.add_argument("--audio")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="renders/dance2_frames")
    ap.add_argument("--res", type=int, default=720)
    ap.add_argument("--samples", type=int, default=16)
    ap.add_argument("--save-blend", dest="save_blend")
    a = ap.parse_args(argv)
    sc = build(a.left, a.right, a.stage)
    sc.render.engine = "CYCLES"; sc.cycles.samples = a.samples; sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = a.res
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast"
    if a.save_blend:
        save_blend(sc, a.save_blend, a.audio, a.res, a.samples)
        return
    os.makedirs(a.frames, exist_ok=True)
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = os.path.abspath(a.frames) + "/f_"
    bpy.ops.render.render(animation=True)
    total = (sc.frame_end - sc.frame_start + 1) / FPS
    cmd = ["ffmpeg", "-v", "error", "-y", "-framerate", str(FPS), "-i", os.path.abspath(a.frames) + "/f_%04d.png"]
    if a.audio:
        cmd += ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-t", f"{total:.3f}", a.out]
    subprocess.run(cmd, check=True)
    print("video", a.out)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
