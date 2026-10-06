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


# --- танец после вступления ---------------------------------------------------------------
BLACK = (409, 436)     # чёрная пауза (как в оригинальном звуке)
FADE = (718, 734)      # затемнение в конце
END = 734
STEP = 6               # одна «доля» = 6 кадров (как рисунки в оригинале)
SPIN_R = 0.62

# продуманные отличия полуоборотов (не случайные): голова, свободная рука, высота пинка, наклон
VARS = [
    dict(),
    dict(head=(-8, 0, 0), free_el=-15, kick=6),
    dict(head=(4, 7, 0), chest=(0, 0, 5)),
    dict(free_el=25, kick=-10),
    dict(head=(-5, -6, 0), kick=10, chest=(-4, 0, 0)),
    dict(head=(6, 0, 0), free_el=-10),
    dict(head=(0, 8, 0), kick=-5, free_el=15),
    dict(head=(-10, -4, 0), chest=(0, 0, -5)),
]


def _spin(phi, step, v):
    d = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
    yaw_l = math.degrees(math.atan2(d[0], -d[1]))
    yaw_r = math.degrees(math.atan2(-d[0], d[1]))
    hop = 0.08 if step % 2 else 0.0
    knee_a, knee_b = (38, 14) if step % 2 == 0 else (14, 38)
    var = VARS[v % len(VARS)]
    fe = var.get("free_el", 0)
    h = var.get("head", (0, 0, 0)); c = var.get("chest", (0, 0, 0))
    common = dict(hips=(-6, 0, 0))
    L = dict(common, loc=(-SPIN_R * d[0], -SPIN_R * d[1], hop), yaw=yaw_l,
             chest=(-10 + c[0], 6 + c[1], c[2]), head=(-12 + h[0], 6 + h[1], 8 + h[2]),
             arm_l=(-82, 4, 0), elbow_l=10, arm_r=(-20, 75, 0), elbow_r=35 + fe,
             leg_r=(-26, 3), knee_r=knee_a, leg_l=(20, -3), knee_l=knee_b)
    R = dict(common, loc=(SPIN_R * d[0], SPIN_R * d[1], hop), yaw=yaw_r,
             chest=(-10 + c[0], -6 - c[1], -c[2]), head=(-12 + h[0], -6 - h[1], -8 - h[2]),
             arm_r=(-82, -4, 0), elbow_r=10, arm_l=(-20, -75, 0), elbow_l=35 + fe,
             leg_l=(-26, -3), knee_l=knee_b, leg_r=(20, 3), knee_r=knee_a)
    return L, R, hop > 0


def _wide(kind, v):
    """В стороны лицом друг к другу, держатся внутренними руками.
    kind: a — колено внутренней ноги подтянуто (замах), kick — нога выстреливает, b — приземление."""
    var = VARS[v % len(VARS)]
    fe = var.get("free_el", 0); kick = var.get("kick", 0)
    h = var.get("head", (0, 0, 0)); c = var.get("chest", (0, 0, 0))
    turn, look = 35, 28
    if kind == "a":
        il, ik, ol, ok, lean, out, oel = (-35, -10), 80, (0, 8), 12, -4, 80, 45   # колено подтянуто
    elif kind == "kick":
        il, ik, ol, ok, lean, out, oel = (-25, -(58 + kick)), 0, (0, 10), 18, 10, 110, 20  # выстрел
    else:
        il, ik, ol, ok, lean, out, oel = (0, -14), 20, (0, 10), 22, 2, 70, 50     # приземление
    # левый в кадре: внутренние — левые рука/нога; правый в кадре — правые
    A = dict(loc=(-0.95, 0, 0.04 if kind == "kick" else 0), yaw=turn, hips=(4, 0, 0),
             chest=(c[0], lean + c[1], c[2]), head=(h[0], 6 + h[1], look + h[2]),
             arm_l=(0, -86, 0), elbow_l=10, arm_r=(-10, out, 0), elbow_r=oel + fe,
             leg_l=il, knee_l=ik, leg_r=ol, knee_r=ok)
    B = dict(loc=(0.95, 0, 0.04 if kind == "kick" else 0), yaw=-turn, hips=(4, 0, 0),
             chest=(c[0], -lean - c[1], -c[2]), head=(h[0], -6 - h[1], -look - h[2]),
             arm_r=(0, 86, 0), elbow_r=10, arm_l=(-10, -out, 0), elbow_l=oel + fe,
             leg_r=(il[0], -il[1]), knee_r=ik, leg_l=(ol[0], -ol[1]), knee_l=ok)
    return A, B


def dance_keys():
    """Ключи танца после вступления: {кадр: (поза L, поза R, флаги)}."""
    out = {}
    phases = [("spin", 45), ("spin", 90), ("spin", 135), ("wide", "a"), ("wide", "kick"), ("wide", "b")]
    base, step, half = 0, 0, 0
    f = 216
    kicks = []
    while f < FADE[0]:
        if BLACK[0] - STEP < f < BLACK[1] + 1:
            f = BLACK[1] + 1
            base, half = 0, half + 1
            continue
        for kind, arg in phases:
            if f >= FADE[0] or (BLACK[0] - STEP < f < BLACK[1] + 1):
                break
            if kind == "spin":
                step += 1
                L, R, _ = _spin(base + arg, step, half)
                out[f] = (L, R)
                if arg == 135:
                    base += 180
            else:
                A, B = _wide(arg, half)
                r_right = base % 360 == 0
                L, R = (A, B) if r_right else (B, A)
                out[f] = (L, R)
                if arg == "kick":
                    out[f + 2] = (L, R)       # короткая фиксация после выстрела
                    kicks.append(f)
            f += STEP
        half += 1
    # финальная поза: раскрылись к зрителю
    A, B = _wide("b", 0)
    out[FADE[0]] = (A, B) if base % 360 == 0 else (B, A)
    return out, kicks


DANCE_SHOTS = [
    # (кадр, позиция, цель, фокус, наезд: позиция в конце плана или None)
    (211, (0.0, -6.8, 1.6), (0, 0.1, 1.05), 40, (0.0, -5.6, 1.5)),       # общий, наезд
    (283, (0.9, -2.8, 0.55), (0, 0, 1.35), 30, None),                    # снизу
    (319, "orbit", (0, 0, 1.1), 35, (4.6, -125, -45, 1.7)),              # облёт спереди
    (355, (0.2, -3.6, 4.4), (0, 0.1, 0.8), 38, None),                    # сверху
    (437, (0.0, -7.2, 1.8), (0, 0.1, 1.05), 40, None),                   # свет загорелся
    (473, "orbit", (0, 0, 1.1), 35, (4.6, -50, -130, 1.5)),              # облёт в другую сторону
    (545, (0.0, -3.1, 1.75), (0, 0, 1.5), 45, None),                     # крупно лица
    (581, (3.6, -3.4, 0.75), (0, 0, 1.2), 32, None),                     # снизу сбоку
    (653, (0.0, -5.4, 1.5), (0, 0.1, 1.05), 40, (0.0, -8.0, 2.0)),       # финал, отъезд
]


def build(left, right, stage, full=False):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    world = bpy.data.worlds.new("w"); sc.world = world; world.use_nodes = True
    for tag, path in (("L", left), ("R", right)):
        img = bpy.data.images.load(os.path.abspath(path)); img.alpha_mode = "STRAIGHT"
        rig.build(tag, True, make_material(tag + "_m", img, (1, 1, 1), 0, 1, 0),
                  make_material(tag + "_mo", img, (1, 1, 1), 0, 1, 0))
    from stage import build_stage, animate_dust
    build_stage(os.path.abspath(stage))

    dk, kicks = dance_keys() if full else ({}, [])
    for tag, keys in (("L", L_pose(0)), ("R", R_pose(0))):
        for f in sorted(keys):
            rig.set_pose(tag, keys[f])
            rig.key_pose(tag, f)
        idx = 0 if tag == "L" else 1
        for f in sorted(dk):
            p = dict(dk[f][idx])
            hop = p["loc"][2]
            rig.set_pose(tag, p)
            if hop:
                bpy.data.objects[f"{tag}_root"].location.z += hop
            rig.key_pose(tag, f)
    # разворот без рывков: угол корня — ближайший к прошлому
    for tag in ("L", "R"):
        for fc in _fcurves(bpy.data.objects[f"{tag}_root"]):
            if fc.data_path == "rotation_euler" and fc.array_index == 2:
                prev = None
                for kp in fc.keyframe_points:
                    if prev is not None:
                        while kp.co[1] - prev > math.pi:
                            kp.co[1] -= 2 * math.pi
                        while kp.co[1] - prev < -math.pi:
                            kp.co[1] += 2 * math.pi
                    prev = kp.co[1]
                fc.update()
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
    if full:
        sc.frame_end = END
        add_dance_cameras(sc, kicks)
        add_blackout_and_lights(sc)
    sc.render.fps = FPS
    animate_dust(sc.frame_end)
    return sc


def add_dance_cameras(sc, kicks):
    cams = []
    for i, (f, loc, tgt, lens, move) in enumerate(DANCE_SHOTS):
        cd = bpy.data.cameras.new(f"dshot{i}"); cd.lens = lens
        cam = bpy.data.objects.new(f"dshot{i}", cd)
        sc.collection.objects.link(cam)
        end = DANCE_SHOTS[i + 1][0] - 1 if i + 1 < len(DANCE_SHOTS) else END
        if f <= BLACK[0] <= end:
            end = BLACK[0] - 1
        if loc == "orbit":
            r, a0, a1, z = move
            n = 6
            for k in range(n + 1):
                fr = f + (end - f) * k / n
                a = math.radians(a0 + (a1 - a0) * k / n)
                cam.location = (r * math.cos(a), r * math.sin(a), z)
                look_at(cam, tgt)
                cam.keyframe_insert("location", frame=fr); cam.keyframe_insert("rotation_euler", frame=fr)
        else:
            cam.location = loc; look_at(cam, tgt)
            cam.keyframe_insert("location", frame=f); cam.keyframe_insert("rotation_euler", frame=f)
            if move:
                cam.location = move; look_at(cam, tgt)
                cam.keyframe_insert("location", frame=end); cam.keyframe_insert("rotation_euler", frame=end)
        mk = sc.timeline_markers.new(f"dshot{i}", frame=f); mk.camera = cam
        cams.append((f, end, cam))
    # тряска на пинках: 3 кадра, затухает
    for kf in kicks:
        for f, end, cam in cams:
            if f <= kf <= end:
                sc.frame_set(kf)
                base = cam.matrix_world.translation.copy()
                for k, amp in enumerate((0.05, -0.035, 0.018, 0.0)):
                    cam.location = base + Vector((amp, 0, -amp * 0.6))
                    cam.keyframe_insert("location", frame=kf + k)
                break


def add_blackout_and_lights(sc):
    """Чёрная пауза: заслонка перед каждой камерой; после паузы свет загорается с миганием;
    в конце — затемнение."""
    mat = bpy.data.materials.new("blackout"); mat.use_nodes = True
    n = mat.node_tree.nodes; n.remove(n["Principled BSDF"])
    mix = n.new("ShaderNodeMixShader"); tr = n.new("ShaderNodeBsdfTransparent")
    em = n.new("ShaderNodeEmission"); em.inputs["Color"].default_value = (0, 0, 0, 1)
    mat.node_tree.links.new(tr.outputs[0], mix.inputs[1])
    mat.node_tree.links.new(em.outputs[0], mix.inputs[2])
    mat.node_tree.links.new(mix.outputs[0], n["Material Output"].inputs["Surface"])
    for cam in [o for o in sc.objects if o.type == "CAMERA"]:
        me = bpy.data.meshes.new("plate")
        me.from_pydata([(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)], [], [(0, 1, 2, 3)])
        pl = bpy.data.objects.new(f"blackout_{cam.name}", me)
        pl.data.materials.append(mat); pl.parent = cam
        pl.location = (0, 0, -cam.data.clip_start - 0.02); pl.scale = (1, 1, 1)
        pl.visible_shadow = False
        sc.collection.objects.link(pl)
    marks = sorted(((m.frame, m.camera.name) for m in sc.timeline_markers), key=lambda t: t[0])
    for i, (f0, cname) in enumerate(marks):
        f1 = marks[i + 1][0] if i + 1 < len(marks) else END + 1
        pl = bpy.data.objects[f"blackout_{cname}"]
        for fr, hidden in ((1, True), (f0, False), (f1, True)):
            pl.hide_render = hidden; pl.hide_viewport = hidden
            pl.keyframe_insert("hide_render", frame=fr); pl.keyframe_insert("hide_viewport", frame=fr)
    fac = mix.inputs["Fac"]
    for fr, v in ((1, 0), (BLACK[0], 1), (BLACK[1] + 1, 0), (FADE[0], 0), (FADE[1], 1)):
        fac.default_value = v; fac.keyframe_insert("default_value", frame=fr)
    for fc in _fcurves_nt(mat.node_tree):
        for kp in fc.keyframe_points:
            kp.interpolation = "CONSTANT"
        fc.keyframe_points[-2].interpolation = "LINEAR"
    # свет загорается после паузы: мигнул — погас — загорелся
    for ob in sc.objects:
        if ob.type == "LIGHT":
            e = ob.data.energy
            for fr, k in ((1, 1.0), (BLACK[0], 0.0), (BLACK[1] + 1, 0.0), (BLACK[1] + 3, 1.0),
                          (BLACK[1] + 5, 0.15), (BLACK[1] + 8, 1.0)):
                ob.data.energy = e * k; ob.data.keyframe_insert("energy", frame=fr)
            ob.data.energy = e
            for fc in _fcurves_nt(ob.data):
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


def _fcurves_nt(owner):
    ad = owner.animation_data
    if not ad or not ad.action:
        return []
    act = ad.action
    if hasattr(act, "fcurves") and len(act.fcurves):
        return list(act.fcurves)
    return [fc for layer in act.layers for st in layer.strips for bag in st.channelbags for fc in bag.fcurves]


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
    sc.render.filepath = "//render/dance2_full.mp4" if sc.frame_end > 210 else "//render/dance2_intro.mp4"
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
    ap.add_argument("--full", action="store_true", help="весь танец (24.5 с), а не только вступление")
    a = ap.parse_args(argv)
    sc = build(a.left, a.right, a.stage, a.full)
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
