"""Покадровая (stop-motion) анимация двух Minecraft-персонажей по раскадровке из видео.

Каждый рисунок оригинала — одна поза; она держится столько же кадров (30 fps), сколько
в оригинале, поэтому движение рывками, без плавных переходов. Звук берётся из оригинала.

    python3 blender/anim.py --left skins/friend.png --right skins/4ered1t.png \
        --audio original.mp4 --out renders/dance.mp4
"""
import argparse
import math
import os
import subprocess
import sys

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scene import PX, build_character, look_at, make_material  # noqa: E402

LEG = 12 * PX

# (первый кадр, длительность) каждого рисунка в оригинале, 30 fps
SEGMENTS = [
    (0, 6), (6, 5), (11, 5), (16, 5), (21, 5), (26, 35), (61, 5), (66, 5), (71, 5), (76, 5),
    (81, 5), (86, 5), (91, 5), (96, 55), (151, 6), (157, 5), (162, 6), (168, 5), (173, 6),
    (179, 6), (185, 5), (190, 6), (196, 5), (201, 6), (207, 5), (212, 6), (218, 5), (223, 6),
    (229, 6), (235, 5), (240, 6), (246, 5), (251, 6), (257, 6), (263, 7), (270, 6), (276, 6),
    (282, 6), (288, 7), (295, 6), (301, 6), (307, 6), (313, 7), (320, 6), (326, 7), (333, 6),
    (339, 7), (346, 6), (352, 6), (358, 6), (364, 7), (371, 6), (377, 6), (383, 6), (389, 7),
    (396, 6), (402, 7), (409, 28), (437, 6), (443, 6), (449, 6), (455, 7), (462, 6), (468, 6),
    (474, 6), (480, 7), (487, 6), (493, 6), (499, 6), (505, 7), (512, 6), (518, 6), (524, 6),
    (530, 7), (537, 6), (543, 7), (550, 6), (556, 6), (562, 6), (568, 6), (574, 7), (581, 6),
    (587, 6), (593, 6), (599, 7), (606, 6), (612, 6), (618, 6), (624, 7), (631, 6), (637, 6),
    (643, 6), (649, 7), (656, 6), (662, 6), (668, 6), (674, 7), (681, 6), (687, 6), (693, 6),
    (699, 7), (706, 6), (712, 6), (718, 16),
]
BLACK_SEG = 57          # пауза-затемнение посередине
FADE_SEG = len(SEGMENTS) - 1  # последний рисунок гаснет


def P(x, y=0.0, yaw=0, z=None, body=(0, 0, 0), head=(0, 0, 0),
      ar=(0, 0), al=(0, 0), lr=(0, 0), ll=(0, 0)):
    """Поза одного персонажа. Углы в градусах.
    yaw > 0 — разворот лицом к +X (вправо в кадре). body/head = (наклон вперёд, вбок, поворот).
    руки/ноги = (вперёд(-)/назад(+), вбок). Для правой руки/ноги «наружу» = +, для левой = −.
    """
    return dict(x=x, y=y, yaw=yaw, z=z, body=body, head=head, ar=ar, al=al, lr=lr, ll=ll)


# --- вступление: L стоит, R подходит сгорбившись, тянет руку, берутся за руки -------------
# у L ближняя к камере рука — правая (ar), у R — левая (al)
INTRO = [
    # 1 — L стоит, рука у груди, смотрит вниз в сторону
    (P(-0.95, yaw=25, head=(12, 0, -15), ar=(-38, -18), al=(4, -3)),
     P(1.15, yaw=-60, al=(-38, 18), ar=(4, 3), head=(6, 0, 0))),
    # 2 — L замечает R, бросает взгляд
    (P(-0.95, yaw=32, head=(4, 0, 22), ar=(-38, -18), al=(4, -3)),
     P(1.15, yaw=-60, al=(-30, 14), ar=(6, 3), head=(22, 0, 0))),
    # 3 — R сникает, L поворачивается к нему
    (P(-0.95, yaw=52, head=(2, 5, 14), ar=(-36, -16), al=(4, -3), ll=(-6, 0)),
     P(1.1, yaw=-62, body=(20, 0, 0), head=(30, 0, 0), al=(-8, 4), ar=(-4, 4),
       lr=(-10, 0), ll=(12, 0))),
    # 4 — R рывком тянет руку, L вздрагивает: отшатнулась, рука выше к груди
    (P(-1.02, yaw=60, body=(-9, 0, 0), head=(-8, 0, 0), ar=(-72, -26), al=(10, -6), lr=(12, 0)),
     P(1.02, yaw=-68, body=(40, 0, 0), head=(-5, 0, 0), al=(-55, 0), ar=(20, 4),
       lr=(28, 0), ll=(-22, 0))),
    # 5 — L колеблется, склонила голову
    (P(-1.02, yaw=66, body=(-3, 0, 0), head=(-2, 10, 0), ar=(-58, -20), al=(6, -4), lr=(6, 0)),
     P(0.98, yaw=-70, body=(42, 0, 0), head=(-8, 0, 0), al=(-72, 0), ar=(24, 4),
       lr=(32, 0), ll=(-24, 0))),
    # 9 — L смягчается: опускает руку от груди, шаг навстречу
    (P(-0.95, yaw=70, body=(6, 0, 0), head=(8, -6, 0), ar=(-28, -6), al=(4, -3), ll=(-14, 0)),
     P(0.95, yaw=-72, body=(46, 0, 0), head=(-14, 0, 0), al=(-88, 0), ar=(28, 4),
       lr=(36, 0), ll=(-26, 0))),
    # 13 — L сама тянется рукой навстречу
    (P(-0.88, yaw=74, body=(10, 0, 0), head=(4, 0, 0), ar=(-72, 0), al=(8, -3), ll=(-18, 0), lr=(10, 0)),
     P(0.86, yaw=-74, body=(42, 0, 0), head=(-10, 0, 0), al=(-82, 0), ar=(24, 4),
       lr=(32, 0), ll=(-22, 0))),
    # 14 — касание: L мягко тянет к себе, R выпрямляется
    (P(-0.88, yaw=76, body=(-5, 0, 0), head=(-6, 4, 0), ar=(-60, 0), al=(6, -3), lr=(10, 0)),
     P(0.62, yaw=-76, body=(22, 0, 0), head=(16, 0, 0), al=(-62, 0), ar=(10, 4),
       lr=(14, 0), ll=(-10, 0))),
    # 15 — держатся за руку, L делает шаг ближе
    (P(-0.8, yaw=78, body=(2, 0, 0), head=(0, 9, 0), ar=(-45, 0), al=(4, -3), lr=(-12, 0), ll=(8, 0)),
     P(0.4, yaw=-78, body=(4, 0, 0), head=(4, 0, 0), al=(-45, 0), ar=(6, 3),
       lr=(8, 0), ll=(-6, 0))),
    # 16 — L подаёт вторую руку
    (P(-0.72, yaw=80, ar=(-40, 0), al=(-24, 6), head=(-2, 6, 0)),
     P(0.3, yaw=-80, al=(-40, 0), ar=(-10, -3))),
    # 17–21 — обе руки, покачиваются вперёд-назад навстречу друг другу
    (P(-0.65, yaw=82, body=(7, 0, 0), ar=(-38, -6), al=(-38, 6), head=(6, 6, 0), lr=(-8, 0)),
     P(0.45, yaw=-82, body=(-5, 0, 0), ar=(-46, -6), al=(-46, 6), head=(-4, -4, 0), ll=(8, 0))),
    (P(-0.67, yaw=82, body=(-5, 0, 0), ar=(-46, -6), al=(-46, 6), head=(-4, -6, 0), ll=(8, 0)),
     P(0.43, yaw=-82, body=(7, 0, 0), ar=(-38, -6), al=(-38, 6), head=(8, 6, 0), lr=(-8, 0))),
    (P(-0.64, yaw=82, body=(7, 0, 0), ar=(-38, -6), al=(-38, 6), head=(4, 8, 0), lr=(-8, 0)),
     P(0.45, yaw=-82, body=(-5, 0, 0), ar=(-46, -6), al=(-46, 6), head=(-2, -6, 0), ll=(8, 0))),
    # 20 — долгая пауза: стоят близко, склонили головы друг к другу
    (P(-0.62, yaw=82, body=(3, 0, 0), ar=(-42, -6), al=(-42, 6), head=(6, 10, 0)),
     P(0.45, yaw=-82, body=(3, 0, 0), ar=(-42, -6), al=(-42, 6), head=(6, -10, 0))),
    (P(-0.6, yaw=82, ar=(-46, -8), al=(-46, 8), body=(6, 0, 0), lr=(-14, 0), ll=(8, 0)),
     P(0.42, yaw=-82, ar=(-46, -8), al=(-46, 8), body=(8, 0, 0), head=(8, 0, 0))),
]


SPIN_R = 0.62  # радиус кружения: держатся за руку на вытянутых руках


def spin(phi, step=0):
    """Пара кружится вокруг общего центра, держась за руку.
    phi — угол линии L→R (0: R справа, 90: R позади, L спиной к камере, 180: поменялись)."""
    d = (math.cos(math.radians(phi)), math.sin(math.radians(phi)))
    yaw_l = math.degrees(math.atan2(d[0], -d[1]))
    yaw_r = math.degrees(math.atan2(-d[0], d[1]))
    s1, s2 = (-24, 18) if step % 2 == 0 else (18, -24)  # шаг: ноги в разные стороны по очереди
    hop = 0.07 if step % 2 else 0.0                      # лёгкие подпрыгивания
    out = 58 if step % 2 else 70                         # свободная рука в сторону
    # держатся одной рукой (у L — левая, у R — правая), вторая отведена в сторону
    return (P(-SPIN_R * d[0], -SPIN_R * d[1], yaw=yaw_l, z=hop, body=(-10, 0, 0), head=(-8, 0, 6),
              al=(-80, 4), ar=(-10, out), lr=(s1, 0), ll=(s2, 0)),
            P(SPIN_R * d[0], SPIN_R * d[1], yaw=yaw_r, z=hop, body=(-10, 0, 0), head=(-8, 0, -6),
              ar=(-80, -4), al=(-10, -out), lr=(s2, 0), ll=(s1, 0)))


def wide(kind):
    """В стороны, держатся внутренними руками; kind: 'a' — стоят, 'kick' — пинок внутрь, 'b'."""
    out = {"a": 68, "kick": 62, "b": 56}[kind]
    if kind == "kick":
        legs_l = dict(lr=(0, 8), ll=(-14, -48))
        legs_r = dict(lr=(-14, 48), ll=(0, -8))
        lean = 6
    else:
        legs_l = dict(lr=(0, 12), ll=(0, -12))
        legs_r = dict(lr=(0, 12), ll=(0, -12))
        lean = 0
    # корпус развёрнут к партнёру, голова ещё сильнее — смотрят друг на друга, а не в камеру
    turn, look = 35, 30
    return (P(-0.92, yaw=turn, al=(0, -86), ar=(0, out), body=(0, lean, 0), head=(0, 4, look), **legs_l),
            P(0.92, yaw=-turn, ar=(0, 86), al=(0, -out), body=(0, -lean, 0), head=(0, -4, -look), **legs_r))


CYCLE = ["close", "single", "close", "wide-a", "wide-kick", "wide-b"]
SPIN_STEP = {"close": 45, "single": 90, "close2": 135}


def timeline():
    """Список (ключ кадра, (поза L, поза R) | None, длительность) по сегментам.
    Между раскрытиями «в стороны» пара делает пол-оборота (45° → 90° → 135° → 180°),
    поэтому после каждого «слияния» они меняются местами."""
    out = []
    base = 0      # угол последнего раскрытия «в стороны» (0 — R справа, 180 — R слева)
    step = 0

    def wide_pair(kind):
        a, b = wide(kind)          # (левый в кадре, правый в кадре)
        r_right = base % 360 == 0
        return (a, b) if r_right else (b, a)

    for s, (_, dur) in enumerate(SEGMENTS):
        if s < len(INTRO):
            out.append((f"intro{s:02d}", INTRO[s], dur))
            continue
        if s == BLACK_SEG:
            out.append(("black", None, dur))
            base = 0
            continue
        if s == 15:            # 22: начинают кружиться
            kind, phase = "spin", 45
        elif s == 16:          # 23: один за другим — передний спиной к нам
            kind, phase = "spin", 90
        elif s == 17:          # 24
            kind, phase = "spin", 135
        else:
            if s in (18, 19, 20):
                kind = ["wide-a", "wide-kick", "wide-b"][s - 18]
            else:
                start = 21 if s < BLACK_SEG else BLACK_SEG + 1
                i = (s - start) % 6
                kind = CYCLE[i]
                if kind == "close" and i == 2:
                    kind = "close2"
            phase = SPIN_STEP.get(kind)
            if phase is not None:
                kind = "spin"
        if kind == "spin":
            phi = base + phase
            step += 1
            out.append((f"spin{phi % 360:03d}-{step % 2}", spin(phi, step), dur))
            if phase == 135:
                base += 180
            continue
        w = kind.split("-")[1]
        out.append((f"wide-{w}-{base % 360}", wide_pair(w), dur))
    return out


# ------------------------------------------------------------------------------------------

def set_pose(tag, p):
    o = bpy.data.objects
    r = math.radians
    lp = [abs(p[k][0]) for k in ("lr", "ll")]
    lr_ = [abs(p[k][1]) for k in ("lr", "ll")]
    # опорная нога — более вертикальная; опускаем корпус, чтобы стопы стояли на полу
    support = max(math.cos(r(a)) * math.cos(r(b)) for a, b in zip(lp, lr_))
    z = -LEG * (1 - support) + (p["z"] or 0.0)  # z позы — подскок над полом
    root = o[f"{tag}_root"]
    root.location = (p["x"], p["y"], z)
    root.rotation_euler = (0, 0, r(p["yaw"]))
    o[f"{tag}_hips"].rotation_euler = tuple(r(a) for a in p["body"])
    hp, hr, hy = p["head"]
    o[f"{tag}_head_pivot"].rotation_euler = (r(hp), r(hr), r(hy))
    for key, name in (("ar", "arm_r"), ("al", "arm_l"), ("lr", "leg_r"), ("ll", "leg_l")):
        a, b = p[key]
        o[f"{tag}_{name}_pivot"].rotation_euler = (r(a), r(b), 0)


def build_scene(left_skin, right_skin, res, samples):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    neutral = dict(head=(0, 0, 0), body_pitch=0, arm_r=(0, 0), arm_l=(0, 0), leg_r=(0, 0), leg_l=(0, 0))
    for tag, path in (("L", left_skin), ("R", right_skin)):
        img = bpy.data.images.load(os.path.abspath(path))
        img.alpha_mode = "STRAIGHT"
        m = make_material(f"{tag}_m", img, (1, 1, 1), 0.0, 1.0, 0.0)
        mo = make_material(f"{tag}_mo", img, (1, 1, 1), 0.0, 1.0, 0.0)
        build_character(tag, img, True, m, mo, neutral, (0, 0, 0), 0)

    # светлый «бумажный» фон, мягкие тени на полу
    world = bpy.data.worlds.new("w"); sc.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.96, 0.955, 0.95, 1)
    bg.inputs["Strength"].default_value = 1.0
    bpy.ops.mesh.primitive_plane_add(size=200)
    bpy.context.active_object.is_shadow_catcher = True

    def area(loc, energy, size, target, color=(1, 1, 1)):
        ld = bpy.data.lights.new("a" + str(len(bpy.data.lights)), "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(ld.name, ld); ob.location = loc
        sc.collection.objects.link(ob); look_at(ob, target)

    area((-3.5, -6, 6), 600, 4, (0, 0, 1))
    area((5, -4, 3), 150, 5, (0, 0, 1), (0.9, 0.93, 1.0))

    cam_d = bpy.data.cameras.new("cam"); cam_d.lens = 85
    cam = bpy.data.objects.new("cam", cam_d); cam.location = (0, -11.0, 1.45)
    sc.collection.objects.link(cam); sc.camera = cam
    look_at(cam, (0, 0, 1.0))

    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x = sc.render.resolution_y = res
    sc.view_settings.view_transform = "Standard"  # белый фон как бумага
    sc.render.image_settings.file_format = "PNG"
    return sc


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--left", required=True, help="скин того, кто стоит слева в начале")
    ap.add_argument("--right", required=True, help="скин того, кто подходит справа")
    ap.add_argument("--audio", help="видео/аудио, откуда взять звук")
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", default="renders/dance_frames")
    ap.add_argument("--res", type=int, default=1080)
    ap.add_argument("--samples", type=int, default=48)
    ap.add_argument("--only", help="отрендерить только эти ключи поз (через запятую)")
    ap.add_argument("--reuse", action="store_true", help="не перерендеривать уже готовые кадры")
    a = ap.parse_args(argv)

    os.makedirs(a.frames, exist_ok=True)
    tl = timeline()
    sc = build_scene(a.left, a.right, a.res, a.samples)
    only = set(a.only.split(",")) if a.only else None

    done = set()
    for key, poses, _ in tl:
        if poses is None or key in done or (only and key not in only):
            continue
        if a.reuse and os.path.exists(os.path.join(a.frames, key + ".png")):
            done.add(key)
            continue
        done.add(key)
        set_pose("L", poses[0]); set_pose("R", poses[1])
        sc.render.filepath = os.path.abspath(os.path.join(a.frames, key + ".png"))
        bpy.ops.render.render(write_still=True)
        print("rendered", key, flush=True)
    if only:
        return

    # черный кадр для паузы
    black = os.path.join(a.frames, "black.png")
    # тот же формат, что и у рендеров, иначе concat выкидывает кадр
    from PIL import Image
    ref = Image.open(os.path.join(a.frames, tl[0][0] + ".png"))
    Image.new(ref.mode, ref.size, (0, 0, 0, 255)[:len(ref.mode)]).save(black)

    # сборка: каждый рисунок держится свою длительность (30 fps)
    lst = os.path.join(a.frames, "list.txt")
    with open(lst, "w") as f:
        for key, _, dur in tl:
            f.write(f"file '{os.path.abspath(os.path.join(a.frames, key + '.png'))}'\n")
            f.write(f"duration {dur / 30:.6f}\n")
        f.write(f"file '{os.path.abspath(os.path.join(a.frames, tl[-1][0] + '.png'))}'\n")
    total = sum(d for _, _, d in tl) / 30
    fade_start = SEGMENTS[FADE_SEG][0] / 30
    vf = f"fps=30,format=yuv420p,fade=t=out:st={fade_start:.3f}:d={SEGMENTS[FADE_SEG][1] / 30:.3f}"
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst]
    if a.audio:
        cmd += ["-i", a.audio, "-map", "0:v", "-map", "1:a", "-c:a", "aac", "-b:a", "192k"]
    cmd += ["-vf", vf, "-c:v", "libx264", "-crf", "18", "-t", f"{total:.3f}", a.out]
    subprocess.run(cmd, check=True)
    print("video", a.out, flush=True)


if __name__ == "__main__":
    main(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:])
