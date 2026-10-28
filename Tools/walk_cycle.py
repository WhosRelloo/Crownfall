"""Build an 8-frame walk or run cycle sheet from one neutral standing frame per direction.

python Tools/walk_cycle.py <src_dir> <out.png> [--style walk|run] [--prefix cf_human_m_full_rags_walk]

Reads <prefix>_<LABEL>_frame01.png for each direction, using LABEL_FOR to pick the file that really
shows each direction (the walk_v2 upload's labels were shifted). The figure is split into parts with
hand-placed regions (PARTS, measured on 8x gridded views of each base pose) and each part moves:
  legs   alternate: the boot slides as one upright block and the leg above slants to meet it;
         sides swing two whole legs (far one shaded) front-to-back so they cross;
         front/back lift the stepping leg
  arms   swing opposite the legs, rotating about the shoulder (10 degrees on the sides, 5-7 elsewhere)
  sword  rides with the hand that holds it
  cloak  the tunic flap / cloak tail sways a step behind the hips; on the sides it trails behind;
         a darker copy of its resting shape sits underneath so a sway never opens an empty space
  hair   the top two rows trail 1 px behind on the sides as the body rises
  body   bobs 1 px on the passing frames
Every body part moves rigidly (translate/rotate only), so proportions never change; only cloth bends.
Torso pixels uncovered by a moving arm are filled from their neighbours, and a cleanup pass fills
1-2 px gaps and removes stray islands; finally every empty space inside the outline is filled
(except right beside the sword blade). Output follows
Docs/Art-Spec.md: rows S, SW, W, NW, N, NE, E, SE; 8 frames of 96 x 96; feet on the pivot (48, 88);
hard alpha.
"""
import argparse
import json
import math
import os

import numpy as np
import colour_classes
from PIL import Image

ROWS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
# Real direction -> label of the walk_v2 file that shows it (checked against the idle sheet in Studio).
LABEL_FOR = {"S": "N", "SE": "NE", "E": "E", "SW": "SE", "NE": "S", "N": "SW", "NW": "W", "W": "NW"}
# Motion settings per animation. Pixel numbers are at the 64 px character scale.
STYLES = {
    "walk": {
        "bob": [0, 0, -1, -1, 0, 0, -1, -1],  # contact frames 1 and 5 low, passing frames high
        "airborne": [],                         # frames with both feet off the ground
        "stride": {"side": 8, "diagonal": 3, "front": 0},  # boot reach in px
        "lift": {"side": 2, "diagonal": 1, "front": 2},    # swinging foot lift in px
        "arm_deg": {"side": 10, "diagonal": 7, "front": 5},
        "cloak_trail": 1.0,                     # side views: how far the cloak tail trails (px at the hem)
        "cloak_sway": 1.0,                      # front/back views: flap sway (px at the hem)
        "lean_deg": 0,                          # forward lean of the upper body about the hip
    },
    "run": {  # a sprint: two-segment legs with real knee bends, hard lean, high knees, heel kick
        "bob": [0, 0, -1, -2, 0, 0, -1, -2],  # front/back views (side and diagonal height comes from the legs)
        "airborne": [3, 7],
        "stride": {"side": 0, "diagonal": 0, "front": 0},
        "lift": {"side": 0, "diagonal": 0, "front": 5},
        # Per-leg sprint cycle, (thigh, knee) in degrees: thigh + = forward, knee - = shin folds back.
        # One leg plays phase i, the other phase i + 4. Phases 0-2 carry the body; 3 and 7 are airborne.
        # The planted phases stay nearly straight so the body never sinks (the sword tip hangs just above the floor).
        "poses": [(18, -6), (6, -14), (-10, -6), (-30, -20), (-38, -75), (-10, -110), (40, -95), (45, -35)],
        "stance": [0, 1, 2],
        "flight_lift": 2,
        "diagonal_scale": 0.4,  # on a diagonal most of the swing points toward/away from the camera
        "arm_deg": {"side": 22, "diagonal": 14, "front": 10},
        # Front/back views: the forearm (with hand and sword) pumps as a rigid piece. Toward the camera it
        # rises "up" px and tucks over the upper arm (a bent arm driving forward, fist at chest height);
        # away from the camera it rises "back_up" px, slides inward and goes behind the body.
        "pump": {"up": 5, "back_up": 3, "tuck": 2},
        "cloak_trail": 4.0,
        "cloak_sway": 2.5,
        "lean_deg": 14,
    },
}
STYLES["idle"] = {  # standing at rest: slow breathing (the chest rises a pixel), arms and cloth settle
    "fps": 6,
    "bob": [0, 0, -1, -1, -1, -1, 0, 0],
    "airborne": [],
    "stride": {"side": 0, "diagonal": 0, "front": 0},
    "lift": {"side": 0, "diagonal": 0, "front": 0},
    "arm_deg": {"side": 2, "diagonal": 2, "front": 1},
    "cloak_trail": 0.3,
    "cloak_sway": 0.5,
    "lean_deg": 0,
}
STYLES["dodge"] = {  # a forward roll: crouch, dive, tuck and spin through a full turn, land, rise
    "fps": 20,
    # Side and diagonal views: per-frame leg poses (near leg, far leg) as (thigh, knee) degrees, upper-body
    # lean, arm swing (+ = forward), whole-body roll, and height off the ground after landing it on the floor.
    # Tuck frames (3-5): knees pulled to the chest and the head pushed down past them -> a tight ball.
    "frame_poses": [((35, -70), (20, -60)), ((-35, -5), (50, -70)), ((110, -155), (100, -150)),
                    ((110, -155), (100, -150)), ((110, -155), (100, -150)), ((70, -125), (80, -135)),
                    ((30, -70), (15, -55)), ((10, -20), (0, -10))],
    "lean_seq": [25, 50, 100, 100, 100, 70, 25, 8],
    "arm_seq": [-25, 70, 110, 110, 110, 60, 10, -5],
    "roll_seq": [0, 0, 80, 170, 260, 330, 360, 360],
    "lift_seq": [0, 3, 0, 0, 0, 0, 0, 0],
    # Front/back views: the body sinks into a ball over legs drawn up beneath it, forearms pulled in and
    # the head tucked down behind the shoulders. Mid-roll (frames 3-5) shows the other side of him as a
    # round hunched back (right side up), the way a roll toward or away from the camera looks.
    # 1 wind-up (arms back), 2 dive (low, arms thrust forward, legs kicked up out of sight), 3-5 the tucked
    # roll (deepest in the middle), 6 landing crouch (hands forward to catch), 7 push up, 8 stand.
    "bob": [6, 12, 17, 20, 18, 12, 5, 0],
    "legs_up": [2, 8, 10, 14, 12, 6, 2, 0],
    "head_tuck": [1, 3, 2, 4, 3, 2, 1, 0],  # enough to drop the face away, not so much the top goes flat
    "cloth_gather": [0, 3, 6, 12, 9, 3, 0, 0],  # px the tunic/cloak rides up behind the ball
    # + pulls the forearms up toward the camera, - swings them back behind the body. In the ball the
    # arms wrap low around the knees (pulled high, they made square corners).
    "arm_tuck": [-0.6, 1.0, 0.4, 0.4, 0.4, 0.8, 0.3, 0.0],
    "front_swap": [False, False, True, True, True, False, False, False],
    "airborne": [],
    "stance": [],
    "stride": {"side": 0, "diagonal": 0, "front": 0},
    "lift": {"side": 0, "diagonal": 0, "front": 0},
    "diagonal_scale": 1.0,
    "arm_deg": {"side": 0, "diagonal": 0, "front": 0},
    "pump": {"up": 7, "back_up": 4, "tuck": 2},
    "cloak_trail": 4.0,
    "cloak_sway": 2.0,
    "lean_deg": 0,
    "travel_studs": 2.5,  # how far the game moves the character over the dodge (previews show it)
}
SRC = {"dir": None, "prefix": "cf_human_m_full_rags_walk"}  # where base poses load from (front/back roll swaps views)
STYLE = STYLES["walk"]
CELL, PIVOT = 96, (48, 88)
HIP = 66  # first leg row after pivoting
BOOT_ROWS = 9  # bottom rows of each leg that make up the boot; moved as one block, never rotated
LAST_BLADE = set()  # where the sword pixels landed in the last frame built (cleanup leaves gaps by it)
LAST_BOOTS = []  # where each boot pixel landed in the last frame built (read by Tools/walk_audit.py)
# Where the whole-figure moves (the dodge roll's spin centre, its upside-down flip and its landing) are measured from
# the figure's outline, a hairstyle would shift the body. Tools/hair_build.py records them on the bald body
# (--motion-out) and replays them for every hairstyle (--motion-in), so hair layers line up with the bald body.
MOTION = {"record": None, "fixed": None, "key": None}
FAR_LEG_SHADE = 0.78  # side views: the far leg is this much darker than the near one

# View kind per direction: front, back or side, and which way the character faces on screen (+1 right).
VIEW = {"S": ("front", 0), "N": ("back", 0), "E": ("side", 1), "W": ("side", -1),
        "SE": ("front", 1), "SW": ("front", -1), "NE": ("back", 1), "NW": ("back", -1)}

# Hand-placed regions in pivoted coordinates (x0, y0, x1, y1 inclusive).
# arm phase: +1 swings with sin(p), -1 against it (opposite the same-side leg).
PARTS = {
    "S": {"hair": 36,
          "arms": [{"rects": [(33, 44, 40, 62), (36, 62, 41, 67)], "pivot": (39, 45), "phase": 1, "sword": [(28, 66, 39, 88)]},
                   {"rects": [(56, 44, 62, 67)], "pivot": (59, 45), "phase": -1}],
          "cloak": {"rects": [(44, 60, 53, 75)], "light": True, "anchor": 58, "hem": 75}},
    "N": {"hair": 34,
          "arms": [{"rects": [(36, 44, 42, 67)], "pivot": (40, 45), "phase": 1},
                   {"rects": [(55, 44, 62, 63), (57, 62, 61, 67)], "pivot": (58, 45), "phase": -1, "sword": [(57, 65, 68, 87)]}],
          "cloak": {"rects": [(43, 58, 55, 76)], "light": True, "anchor": 56, "hem": 76}},
    "E": {"hair": 33,
          "arms": [{"rects": [(45, 45, 52, 62), (48, 62, 53, 68)], "pivot": (48, 45), "phase": 1, "sword": [(52, 66, 68, 87)]}],
          "cloak": {"rects": [(39, 55, 44, 70)], "light": False, "anchor": 55, "hem": 70}},
    "W": {"hair": 34,
          "arms": [{"rects": [(44, 45, 52, 62), (39, 61, 46, 68)], "pivot": (48, 45), "phase": 1, "sword": [(27, 66, 42, 87)]}],
          "cloak": {"rects": [(53, 55, 58, 72)], "light": False, "anchor": 55, "hem": 72}},
    "SE": {"hair": 35,
           "arms": [{"rects": [(34, 46, 41, 66)], "pivot": (39, 46), "phase": 1},
                    {"rects": [(54, 46, 59, 61), (55, 61, 59, 66)], "pivot": (56, 46), "phase": -1, "sword": [(57, 64, 70, 87)]}],
           "cloak": {"rects": [(43, 58, 52, 72)], "light": True, "anchor": 58, "hem": 72}},
    "SW": {"hair": 35,
           "arms": [{"rects": [(36, 46, 43, 66)], "pivot": (40, 46), "phase": 1, "sword": [(26, 64, 39, 88)]},
                    {"rects": [(55, 46, 61, 66)], "pivot": (58, 46), "phase": -1}],
           "cloak": {"rects": [(44, 58, 53, 74)], "light": True, "anchor": 58, "hem": 74}},
    "NE": {"hair": 36,
           "arms": [{"rects": [(34, 46, 41, 66)], "pivot": (39, 46), "phase": 1},
                    {"rects": [(52, 46, 58, 62), (54, 62, 58, 67)], "pivot": (56, 46), "phase": -1, "sword": [(56, 64, 68, 87)]}],
           "cloak": {"rects": [(42, 56, 54, 76)], "light": True, "anchor": 56, "hem": 76}},
    "NW": {"hair": 36,
           "arms": [{"rects": [(36, 46, 42, 66)], "pivot": (40, 46), "phase": 1, "sword": [(29, 64, 40, 88)]},
                    {"rects": [(55, 46, 61, 64)], "pivot": (58, 46), "phase": -1}],
           "cloak": {"rects": [(43, 56, 55, 76)], "light": True, "anchor": 56, "hem": 76}},
}


def hard(im):
    a = im.split()[3].point(lambda v: 255 if v >= 128 else 0)
    im = im.copy()
    im.putalpha(a)
    return im


def feet_centre(im):
    px = im.load()
    bottom = im.getbbox()[3] - 1
    xs = [x for y in range(bottom - 3, bottom + 1) for x in range(im.width) if px[x, y][3] > 0]
    return sum(xs) / len(xs), bottom


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def steel(c):
    return abs(c[0] - c[1]) < 22 and abs(c[1] - c[2]) < 22 and lum(c) > 30


def outline_dark(c):
    return lum(c) < 45


def skin(c):
    return c[0] > 150 and c[0] - c[2] > 60


def cloth_tone(colours):
    """The middle cloth tone of some colours: skips near-black outline and skin, then takes the median by
    brightness. Fills made from it read as fabric, not black spots or bright skin strips."""
    pool = [c for c in colours if not outline_dark(c) and not skin(c)]
    if not pool:
        pool = [c for c in colours if not outline_dark(c)] or list(colours)
    pool.sort(key=lum)
    return pool[len(pool) // 2]


def brown(c):
    return c[0] - c[2] > 25  # leather, cloth and skin all run warm; the blade and its outline don't


def inside(rects, x, y):
    return any(x0 <= x <= x1 and y0 <= y <= y1 for x0, y0, x1, y1 in rects)


def split(base, parts):
    """Label every opaque pixel: ('sword', i), ('arm', i), 'cloak', 'leg' or 'body'."""
    px = base.load()
    w, h = base.size
    labels = {}
    opaque = [(x, y) for y in range(h) for x in range(w) if px[x, y][3]]
    for i, arm in enumerate(parts["arms"]):
        rects = arm.get("sword")
        if not rects:
            continue
        in_rect = {(x, y) for x, y in opaque if inside(rects, x, y)}
        blade = {p for p in in_rect if steel(px[p[0], p[1]])}
        # Non-brown pixels touching the blade are its outline.
        # At leg height a dark pixel that also touches brown leather is the boot's outline, not the blade's.
        def touches_leather(x, y):
            return any(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3] and brown(px[x + dx, y + dy])
                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
        edge = {(x, y) for x, y in in_rect - blade if not brown(px[x, y])
                and any((x + dx, y + dy) in blade for dx in (-1, 0, 1) for dy in (-1, 0, 1))
                and not (y >= HIP and touches_leather(x, y))}
        blade |= edge
        # Anything else left in the sword area with no 4-neighbour outside the blade is a stray blade pixel.
        for x, y in in_rect - blade:
            if not any((x + dx, y + dy) in in_rect - blade for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                blade.add((x, y))
        for p in blade:
            labels[p] = ("sword", i)
    for x, y in opaque:
        if (x, y) in labels:
            continue
        for i, arm in enumerate(parts["arms"]):
            if inside(arm["rects"], x, y):
                labels[(x, y)] = ("arm", i)
                break
        else:
            cloak = parts["cloak"]
            # Above the hips the flap takes every pixel (no speckle left behind); over the legs only its lighter cloth.
            if inside(cloak["rects"], x, y) and (y < HIP or not cloak["light"] or lum(px[x, y]) > 50):
                labels[(x, y)] = "cloak"
            elif y >= HIP:
                labels[(x, y)] = "leg"
            else:
                labels[(x, y)] = "body"
    # Safeguard: a tiny cluster of "leg" pixels touching the sword is a blade tip that poked outside its
    # region, not part of a boot.
    legs = {p for p, lab in labels.items() if lab == "leg"}
    seen = set()
    for start in legs:
        if start in seen:
            continue
        comp, stack = [], [start]
        seen.add(start)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    n = (x + dx, y + dy)
                    if n in legs and n not in seen:
                        seen.add(n)
                        stack.append(n)
        if len(comp) <= 5:
            owner = next((labels[(x + dx, y + dy)] for x, y in comp for dx in (-1, 0, 1) for dy in (-1, 0, 1)
                          if isinstance(labels.get((x + dx, y + dy)), tuple) and labels[(x + dx, y + dy)][0] == "sword"), None)
            if owner:
                for q in comp:
                    labels[q] = owner
    return labels


def scale2x(img):
    """EPX / Scale2x on an (h, w) array of packed RGBA ints: doubles size, keeps pixel-art edges crisp."""
    p = img
    # Edges are found by comparing colours only: the alpha byte can carry a colour class (--classes), which
    # must not change the result. Opaque/transparent still differ (bit 24).
    k = (p >> 8) | ((p & 0xFF) > 0).astype(p.dtype) << 24
    def around(v):  # above, below, left, right
        return (np.pad(v, ((1, 0), (0, 0)), mode="edge")[:-1], np.pad(v, ((0, 1), (0, 0)), mode="edge")[1:],
                np.pad(v, ((0, 0), (1, 0)), mode="edge")[:, :-1], np.pad(v, ((0, 0), (0, 1)), mode="edge")[:, 1:])
    a, d, c, b = around(k)
    pa, pd, pc, pb = around(p)
    e0 = np.where((c == a) & (c != d) & (a != b), pc, p)
    e1 = np.where((a == b) & (a != c) & (b != d), pa, p)
    e2 = np.where((d == c) & (d != b) & (c != a), pd, p)
    e3 = np.where((b == d) & (b != a) & (d != c), pb, p)
    out = np.empty((p.shape[0] * 2, p.shape[1] * 2), dtype=p.dtype)
    out[0::2, 0::2], out[0::2, 1::2], out[1::2, 0::2], out[1::2, 1::2] = e0, e1, e2, e3
    return out


def transform(points, pivot, angle, scale_y, shift):
    """Move a set of pixels: rotate(angle) * scale(1, scale_y) about pivot, then shift.
    Pure moves copy pixels exactly. Rotations use RotSprite (Scale2x three times to 8x, rotate, sample
    each target pixel's centre), so rotated pixel art keeps clean edges with no dropped or doubled pixels."""
    if not points:
        return {}
    if abs(angle) < 1e-6 and scale_y == 1.0:
        sx_, sy_ = round(shift[0]), round(shift[1])
        return {(x + sx_, y + sy_): c for (x, y), c in points.items()}
    xs = [q[0] for q in points]
    ys = [q[1] for q in points]
    x0, y0 = min(xs) - 1, min(ys) - 1
    w, h = max(xs) - x0 + 2, max(ys) - y0 + 2
    packed = np.zeros((h, w), dtype=np.uint32)
    for (x, y), c in points.items():
        packed[y - y0, x - x0] = (c[0] << 24) | (c[1] << 16) | (c[2] << 8) | c[3]
    big = scale2x(scale2x(scale2x(packed)))  # 8x
    pad = 24  # room for a rotated sword tip or a kicked-up shin
    gx, gy = np.meshgrid(np.arange(min(xs) - pad, max(xs) + pad + 1), np.arange(min(ys) - pad, max(ys) + pad + 1))
    c_, s_ = math.cos(angle), math.sin(angle)
    vx = gx - shift[0] - pivot[0]
    vy = gy - shift[1] - pivot[1]
    rx, ry = vx * c_ - vy * s_, vx * s_ + vy * c_  # inverse rotation
    sx = pivot[0] + rx
    sy = pivot[1] + ry / scale_y
    bx = np.floor((sx - x0 + 0.5) * 8).astype(int)
    by = np.floor((sy - y0 + 0.5) * 8).astype(int)
    inside = (bx >= 0) & (by >= 0) & (bx < w * 8) & (by < h * 8)
    out = {}
    vals = np.zeros(gx.shape, dtype=np.uint32)
    vals[inside] = big[by[inside], bx[inside]]
    hit = inside & ((vals & 0xFF) > 0)
    for X, Y, v in zip(gx[hit].tolist(), gy[hit].tolist(), vals[hit].tolist()):
        out[(X, Y)] = ((v >> 24) & 0xFF, (v >> 16) & 0xFF, (v >> 8) & 0xFF, v & 0xFF)
    return out


def leg_geometry(bottom):
    hip_y = HIP - 1
    ankle_y = bottom - BOOT_ROWS + 1
    knee_y = (HIP + ankle_y) // 2
    return hip_y, knee_y, ankle_y


def leg_pose(phase, diagonal):
    a1, a2 = STYLE["poses"][phase % 8]
    k = STYLE["diagonal_scale"] if diagonal else 1.0
    return math.radians(a1 * k), math.radians(a2 * k)


def body_drop(i, bottom, diagonal):
    """How far the body sits below standing height (px, + = lower) so the planted foot is on the ground.
    Airborne frames rise flight_lift above their neighbours."""
    hip_y, knee_y, ankle_y = leg_geometry(bottom)
    if i in STYLE["airborne"]:
        before = body_drop((i - 1) % 8, bottom, diagonal)
        after = body_drop((i + 1) % 8, bottom, diagonal)
        return round((before + after) / 2) - STYLE["flight_lift"]
    phase = i if i % 8 in STYLE["stance"] else i + 4
    a1, a2 = leg_pose(phase, diagonal)
    reach = (knee_y - hip_y) * math.cos(a1) + (ankle_y - knee_y) * math.cos(a1 + a2)
    return round((ankle_y - hip_y) - reach)


def posed_legs(labels, colour, i, cx, bottom, split_x, kind, facing, diagonal, bob):
    """Two-segment legs: the thigh rotates at the hip, the shin at the knee, and the boot hangs from the
    ankle (flat while planted, tipped with the shin when it kicks up). Every piece is rigid."""
    hip_y, knee_y, ankle_y = leg_geometry(bottom)
    f = facing or 1
    out = []
    for side in (-1, 1):
        phase = i if side > 0 else i + 4
        if kind == "side":
            shade = FAR_LEG_SHADE if side < 0 else 1.0
            pts = {pt: (int(c[0] * shade), int(c[1] * shade), int(c[2] * shade), c[3])
                   for pt, c in ((pt, colour[pt]) for pt, lab in labels.items() if lab == "leg")}
        else:
            pts = {pt: colour[pt] for pt, lab in labels.items()
                   if lab == "leg" and (pt[0] < split_x[pt[1]]) == (side < 0)}
        if not pts:
            continue
        hx = sum(x for x, y in pts) / len(pts)
        if STYLE.get("frame_poses"):
            pose = STYLE["frame_poses"][i][0 if side > 0 else 1]
            k = STYLE["diagonal_scale"] if diagonal else 1.0
            a1, a2 = math.radians(pose[0] * k), math.radians(pose[1] * k)
        else:
            a1, a2 = leg_pose(phase, diagonal)
        # Segments overlap by 2 rows at each joint, so the knee and ankle never open a seam.
        thigh = {q: c for q, c in pts.items() if q[1] < knee_y + 2}
        shin = {q: c for q, c in pts.items() if knee_y - 1 <= q[1] < ankle_y + 1}
        boot = {q: c for q, c in pts.items() if q[1] >= ankle_y}
        planted = (phase % 8) in STYLE["stance"] or (STYLE.get("frame_poses") and i in (0, 7))
        knee = (hx + (knee_y - hip_y) * math.sin(f * a1), hip_y + bob + (knee_y - hip_y) * math.cos(a1))
        ankle = (knee[0] + (ankle_y - knee_y) * math.sin(f * (a1 + a2)),
                 knee[1] + (ankle_y - knee_y) * math.cos(a1 + a2))
        layer = {}
        layer.update(transform(thigh, (hx, hip_y), f * a1, 1.0, (0, bob)))
        layer.update(transform(shin, (hx, knee_y), f * (a1 + a2), 1.0, (knee[0] - hx, knee[1] - knee_y)))
        boot_angle = 0.0 if planted else f * (a1 + a2) * 0.7
        placed_boot = transform(boot, (hx, ankle_y), boot_angle, 1.0, (ankle[0] - hx, ankle[1] - ankle_y))
        layer.update(placed_boot)
        # Nothing on a leg may go below the ground line: lift the whole leg (rigidly) by any overflow.
        overflow = max(y for x, y in layer) - bottom
        if overflow > 0:
            layer = {(x, y - overflow): c for (x, y), c in layer.items()}
            placed_boot = {(x, y - overflow): c for (x, y), c in placed_boot.items()}
        LAST_BOOTS.append(set(placed_boot))
        out.append((side, layer))
    out.sort(key=lambda l: l[0])  # side views: far (shaded) leg first, near leg on top
    return [layer for _, layer in out]


def frame(base, direction, i):
    MOTION["key"] = f"{STYLE.get('name', '')}/{direction}/{i}"
    kind, facing = VIEW[direction]
    parts = PARTS[direction]
    diagonal = facing != 0 and kind != "side"
    flip = bool(STYLE.get("front_swap")) and kind in ("front", "back") and not diagonal and STYLE["front_swap"][i]
    if flip:  # mid-roll toward/away from the camera shows the other side of him (right side up)
        other = "N" if direction == "S" else "S"
        base = base_for(other)
        parts = PARTS[other]
    p = 2 * math.pi * i / 8
    px = base.load()
    labels = split(base, parts)
    colour = {pt: px[pt[0], pt[1]] for pt in labels}
    cx, bottom = feet_centre(base)
    posed = bool(STYLE.get("poses") or STYLE.get("frame_poses")) and (kind == "side" or diagonal)
    rolling = bool(STYLE.get("roll_seq"))
    if rolling and posed:
        bob = prev_bob = 0  # the finished frame is set on the floor afterwards
    else:
        bob = body_drop(i, bottom, diagonal) if posed else STYLE["bob"][i]
        prev_bob = body_drop((i - 1) % 8, bottom, diagonal) if posed else STYLE["bob"][i - 1]
    layers = []  # list of dicts {(x, y): rgba}, drawn in order

    # Underlayer: the cloth's resting shape, 15% darker, drawn first. When the tunic flap or cloak tail
    # sways away, this shows as the shaded fabric/pants behind it instead of an empty space.
    layers.append({(x, y + bob): (int(c[0] * 0.85), int(c[1] * 0.85), int(c[2] * 0.85), c[3])
                   for (x, y), c in ((pt, colour[pt]) for pt, lab in labels.items() if lab == "cloak")})

    # Legs. The boot is never rotated or cropped: it slides as one upright block (sole flat on the ground
    # line), and the leg above it slants row by row from the hip down to the boot. Every row keeps its
    # pixels, so the leg keeps its full height.
    #   side views: both legs are the whole drawn leg (the far one shaded 22%), swinging front-to-back in
    #               opposite phase so they pass each other on frames 3 and 7
    #   diagonals:  the two drawn legs (split at the centre line) do the same with a shorter stride
    #   front/back: the stepping leg lifts straight up (its top tucks under the tunic)
    view = "side" if kind == "side" else "diagonal" if diagonal else "front"
    stride, lift = STYLE["stride"][view], STYLE["lift"][view]  # walk side stride 8: boots never touch
    boot_top = bottom - BOOT_ROWS + 1
    # Where to split the two drawn legs on each row: the middle of the widest see-through gap near the
    # centre line (so a boot is never sliced); rows where the legs touch use the centre line.
    split_x = {}
    leg_rows = {}
    for (x, y), lab in labels.items():
        if lab == "leg":
            leg_rows.setdefault(y, set()).add(x)
    for y in range(base.height):
        xs = leg_rows.get(y, set())
        best, here = None, round(cx)
        run = []
        for x in range(round(cx) - 6, round(cx) + 7):
            if x not in xs:
                run.append(x)
            elif run:
                if best is None or len(run) > len(best):
                    best = run
                run = []
        if run and (best is None or len(run) > len(best)):
            best = run
        split_x[y] = (best[0] + best[-1] + 1) / 2 if best and min(xs, default=here) < best[0] and max(xs, default=here) > best[-1] else cx
    LAST_BOOTS.clear()
    if posed:
        layers.extend(posed_legs(labels, colour, i, cx, bottom, split_x, kind, facing, diagonal, bob))
        legs = None
    else:
        legs = []
    for side in ((-1, 1) if legs is not None else ()):
        if kind == "side":
            shade = FAR_LEG_SHADE if side < 0 else 1.0
            pts = {pt: (int(c[0] * shade), int(c[1] * shade), int(c[2] * shade), c[3])
                   for pt, c in ((pt, colour[pt]) for pt, lab in labels.items() if lab == "leg")}
        else:
            pts = {pt: colour[pt] for pt, lab in labels.items() if lab == "leg" and (pt[0] < split_x[pt[1]]) == (side < 0)}
        reach = round(stride * math.cos(p)) * side * (facing or 1)  # boot offset; forward is the facing way
        if stride:
            swinging = max(0.0, -side * math.sin(p))  # this leg is moving forward through the air
        else:
            swinging = max(0.0, side * math.sin(p))
        up = round(lift * swinging)
        layer = {}
        # The planted leg stays on the ground. A swinging leg lifts as one piece (its top tucks under the
        # body), together with the body bob, so no row is ever stretched or skipped.
        dy = min(0, bob) - up if swinging > 0 else 0  # a foot never goes below the ground line
        if STYLE.get("legs_up"):
            dy = -STYLE["legs_up"][i]  # both legs drawn up under the body
        if i in STYLE["airborne"] and swinging == 0:
            dy = -1  # flight: the trailing foot has left the ground too
        boot = set()
        for (x, y), c in pts.items():
            t = 1.0 if y >= boot_top else (y - HIP) / max(1, boot_top - HIP)
            layer[(x + round(reach * t), y + dy)] = c
            if y >= boot_top:
                boot.add((x + reach, y + dy))
        LAST_BOOTS.append(boot)
        legs.append((side, swinging, layer))
    if legs is not None:
        if kind == "side":
            legs.sort(key=lambda l: l[0])  # far (shaded) leg first, near leg on top
        else:
            legs.sort(key=lambda l: l[1])  # standing leg first, stepping leg over it
        layers.extend(layer for _, _, layer in legs)

    # Body (torso, head, hair): rigid, with the bob. In side views the top two rows of hair trail
    # 1 px behind on the rising frames; the head keeps its size.
    rising = bob < prev_bob
    top = min(y for (x, y), lab in labels.items() if lab == "body")
    body = {}
    head = {}  # a tucked head (dodge, front/back views) goes behind the shoulders
    tuck = STYLE["head_tuck"][i] if STYLE.get("head_tuck") and kind in ("front", "back") and not diagonal else 0
    neck = parts["hair"] + 6
    for (x, y), lab in labels.items():
        if lab != "body":
            continue
        dx = -facing if (kind == "side" and rising and y <= top + 1) else 0
        if tuck and y <= neck:
            head[(x + dx, y + bob + tuck)] = colour[(x, y)]
        else:
            body[(x + dx, y + bob)] = colour[(x, y)]
    if head:
        layers.append(head)
    # Where an arm moved off the body, show shadowed torso behind it: the torso's middle cloth tone,
    # 15% darker (the darkest tones read as black spots). A copy of the arm
    # itself would leave a ghost second arm behind the swinging one.
    # Only inside the body's outline: between the leftmost and rightmost non-arm pixel of that row.
    span = {}
    row_cloth = {}
    for (x, y), lab in labels.items():
        if not isinstance(lab, tuple):
            lo, hi = span.get(y, (x, x))
            span[y] = (min(lo, x), max(hi, x))
            if lab == "body" and y >= neck:
                row_cloth.setdefault(y, []).append(colour[(x, y)])
    # One tone for the whole torso (a tone per row painted horizontal stripes).
    every = [c for cols in row_cloth.values() for c in cols]
    tone = cloth_tone(every) if every else None
    # (with --classes the shadow is torso cloth, whichever pixel its tone was taken from)
    alpha = tone and (tone[3] if tone[3] == 255 else 255 - colour_classes.OUTFIT)
    shade = (int(tone[0] * 0.85), int(tone[1] * 0.85), int(tone[2] * 0.85), alpha) if tone else None
    shadow = {y: shade for y in row_cloth}
    for (x, y), lab in labels.items():
        if not isinstance(lab, tuple) or lab[0] != "arm" or y not in span:  # arms only, never the sword
            continue
        spot = (x, y + bob)
        if spot not in body and span[y][0] <= x <= span[y][1]:
            body[spot] = shadow.get(y) or shadow.get(y - 1) or colour[(x, y)]
    body_index = len(layers)
    layers.append(body)

    # Cloak / tunic: sways behind the hips; on the sides it trails behind the walker.
    cl = parts["cloak"]
    cloak = {}
    for (x, y), lab in labels.items():
        if lab != "cloak":
            continue
        t = min(1.0, max(0.0, (y - cl["anchor"]) / max(1, cl["hem"] - cl["anchor"])))
        if kind == "side":
            dx = -facing * round(STYLE["cloak_trail"] * (1 + 0.5 + 0.5 * math.sin(2 * p - 0.8)) * t)
        else:
            amp = (1.5 if kind == "back" else 1.0) * STYLE["cloak_sway"]
            dx = round(amp * math.sin(p - 0.8) * t)
        dy = bob - (1 if (kind == "side" and bob < 0 and t > 0.6) else 0)
        # Cloth stretches: cover every pixel between where it was and where it moved, so no gap opens.
        step = 1 if dx >= 0 else -1
        for k in range(0, dx + step, step) if dx else (0,):
            cloak.setdefault((x + k, y + dy), colour[(x, y)])
        cloak[(x + dx, y + dy)] = colour[(x, y)]
    gather = STYLE["cloth_gather"][i] if STYLE.get("cloth_gather") and kind in ("front", "back") and not diagonal else 0
    if gather:  # the cloth bunches up behind the tucked body instead of hanging below it like a skirt
        # It is behind him, so only what falls inside the body's outline on each row can show.
        rows = {}
        for (x, y) in list(body) + list(head):
            lo, hi = rows.get(y, (x, x))
            rows[y] = (min(lo, x), max(hi, x))
        gathered = {(x, y - gather): c for (x, y), c in cloak.items()}
        layers.insert(body_index, {(x, y): c for (x, y), c in gathered.items()
                                   if y in rows and rows[y][0] <= x <= rows[y][1]})
    else:
        layers.append(cloak)

    # Arms and swords.
    behind = []  # arm pieces drawn behind the body (a run arm swung away from the camera)
    blades = {}  # every sword pixel as placed this frame
    for a, arm in enumerate(parts["arms"]):
        pts = {pt: colour[pt] for pt, lab in labels.items() if lab == ("arm", a)}
        blade = {pt: colour[pt] for pt, lab in labels.items() if lab == ("sword", a)}
        if STYLE.get("pump") and kind in ("front", "back") and not diagonal and pts:
            # Two rigid pieces: the upper arm stays at the shoulder; the forearm, hand and sword move.
            low = max(y for x, y in pts)
            elbow = arm["pivot"][1] + (low - arm["pivot"][1]) * 0.45
            upper = {q: c for q, c in pts.items() if q[1] < elbow}
            fore = {q: c for q, c in pts.items() if q[1] >= elbow}
            pump = math.sin(p) * arm["phase"]
            toward = pump if kind == "front" else -pump  # > 0: this forearm comes toward the camera
            if STYLE.get("arm_tuck"):
                toward = STYLE["arm_tuck"][i]  # both forearms pulled in
            inward = 1 if arm["pivot"][0] < cx else -1
            P = STYLE["pump"]
            if toward >= 0:
                shift = (round(P["tuck"] * 0.75 * toward) * inward, bob - round(P["up"] * toward))
            else:
                shift = (round(P["tuck"] * -toward) * inward, bob - round(P["back_up"] * -toward))
            pieces = [transform(upper, arm["pivot"], 0.0, 1.0, (0, bob)),
                      transform(fore, arm["pivot"], 0.0, 1.0, shift),
                      transform(blade, arm["pivot"], 0.0, 1.0, shift)]
            blades.update(pieces[2])
            if toward >= 0:
                layers.extend(pieces)
            else:
                layers.append(pieces[0])
                behind.extend(pieces[1:])
            continue
        # Rigid swing about the shoulder: no stretching, so the arm keeps its length.
        scale = 1.0
        if STYLE.get("arm_seq") and (kind == "side" or diagonal):
            # + = reaching forward. Diagonal drawings hang the arms at the sides, so a big in-picture
            # swing would throw them off the body: they get 40% of the side-view swing.
            angle = facing * math.radians(STYLE["arm_seq"][i] * (0.4 if diagonal else 1.0))
        elif kind == "side":
            angle = -facing * math.radians(STYLE["arm_deg"]["side"]) * math.cos(p)  # counter-swing: back while the leading leg is forward
        else:
            fwd = math.sin(p) * arm["phase"]
            outward = -1 if arm["pivot"][0] < cx else 1  # which side of the body this arm hangs on
            deg = STYLE["arm_deg"]["diagonal" if diagonal else "front"]
            angle = math.radians(deg) * fwd * (facing if diagonal else outward)
        layers.append(transform(pts, arm["pivot"], angle, scale, (0, bob)))
        placed = transform(blade, arm["pivot"], angle, scale, (0, bob))
        blades.update(placed)
        layers.append(placed)
    layers[body_index:body_index] = behind  # swung-back forearms go behind the body

    # Forward lean: the whole upper body (cloth underlayer, torso, head, cloak, arms, sword) tilts as one
    # rigid piece about the hip, so nothing in it stretches. Full lean from the side, half on diagonals;
    # a lean toward or away from the camera doesn't show, so front/back views stay upright.
    lean = STYLE["lean_deg"] * (1.0 if kind == "side" else 0.5 if diagonal else 0.0)
    if STYLE.get("lean_seq"):
        lean = STYLE["lean_seq"][i] * (1.0 if kind == "side" else 0.7) if (kind == "side" or diagonal) else 0
    if lean:
        under, legs_layers, rest = layers[0], layers[1:3], layers[3:]
        upper = {}
        for layer in rest:
            upper.update(layer)
        hip = (round(cx), HIP + bob)
        # Lean as far as allowed, easing off a degree at a time if the tilt would swing the low-hanging
        # sword tip below the ground line (clipping it would be a cut-off).
        while True:
            angle = -(facing or 1) * math.radians(lean)  # negative tips the top toward +x when facing right
            leaned = transform(upper, hip, angle, 1.0, (0, 0))
            if lean <= 0 or rolling or max(y for x, y in leaned) <= bottom:
                break
            lean -= 1
        # the cloth underlayer leans too but stays beneath the legs
        layers = [transform(under, hip, angle, 1.0, (0, 0))] + legs_layers + [leaned]
        blades = transform(blades, hip, angle, 1.0, (0, 0))

    # The darker cloth underlayer only fills gaps: drop any of it that sticks out past the outline of
    # everything else on that row, where it would read as a ghost duplicate of the cloak.
    span = {}
    for layer in layers[1:]:
        for (x, y) in layer:
            lo, hi = span.get(y, (x, x))
            span[y] = (min(lo, x), max(hi, x))
    layers[0] = {(x, y): c for (x, y), c in layers[0].items() if y in span and span[y][0] <= x <= span[y][1]}

    if rolling:
        layers, blades = roll_and_land(layers, blades, kind, facing, diagonal, i, False)

    LAST_BLADE.clear()
    LAST_BLADE.update(blades)

    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dst = out.load()
    for layer in layers:
        for (x, y), c in layer.items():
            if 0 <= x < base.width and 0 <= y < base.height:
                dst[x, y] = c
    out = cleanup(out)
    if rolling:  # the cleanup may have trimmed the lowest stray pixel: set the frame on the floor again
        ground = PIVOT[1] - 1 - (STYLE["lift_seq"][i] if STYLE.get("lift_seq") else 0)
        dy = _motion("reland", lambda: ground - (out.getbbox()[3] - 1))
        if dy:
            moved = Image.new("RGBA", out.size, (0, 0, 0, 0))
            moved.paste(out.crop((0, max(0, -dy), out.width, out.height)), (0, max(0, dy)))
            out = moved
            shifted = {(x, y + dy) for x, y in LAST_BLADE}
            LAST_BLADE.clear()
            LAST_BLADE.update(shifted)
    return out


def _motion(name, compute):
    """A whole-figure measurement for this frame: replayed when fixed, else computed (and recorded)."""
    key = f"{MOTION['key']}/{name}"
    if MOTION["fixed"] is not None and key in MOTION["fixed"]:
        value = MOTION["fixed"][key]
        return tuple(value) if isinstance(value, list) else value
    value = compute()
    if MOTION["record"] is not None:
        MOTION["record"][key] = value
    return value


def roll_and_land(layers, blades, kind, facing, diagonal, i, flip):
    """Dodge: spin the whole figure (one rigid piece, RotSprite) through this frame's roll angle, flip it
    upside down on the front/back mid-roll frames, then set its lowest pixel on the floor (plus lift)."""
    whole = {}
    for layer in layers:
        whole.update(layer)
    if not whole:
        return layers, blades
    xs = [q[0] for q in whole]
    ys = [q[1] for q in whole]
    centre = _motion("centre", lambda: ((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2))
    moves = []
    roll = STYLE["roll_seq"][i] % 360 if (kind == "side" or diagonal) else 0
    if roll:
        angle = -(facing or 1) * math.radians(roll)  # forward roll: the head goes over toward the facing way
        whole = transform(whole, centre, angle, 1.0, (0, 0))
        blades = set(transform({q: (0, 0, 0, 255) for q in blades}, centre, angle, 1.0, (0, 0)))
        moves.append(("rot", centre, angle))
    if flip:
        top, low = _motion("flip", lambda: (min(y for x, y in whole), max(y for x, y in whole)))
        whole = {(x, top + low - y): c for (x, y), c in whole.items()}
        blades = {(x, top + low - y) for x, y in blades}
        moves.append(("flip", top, low))
    ground = PIVOT[1] - 1 - STYLE["lift_seq"][i] if STYLE.get("lift_seq") else PIVOT[1] - 1
    dy = _motion("land", lambda: ground - max(y for x, y in whole))
    whole = {(x, y + dy): c for (x, y), c in whole.items()}
    blades = {(x, y + dy) for x, y in blades}
    # boots follow the same moves, so the cleanup still protects their toe and heel tips
    for k, boot in enumerate(LAST_BOOTS):
        pts = {q: (0, 0, 0, 255) for q in boot}
        for m in moves:
            if m[0] == "rot":
                pts = transform(pts, m[1], m[2], 1.0, (0, 0))
            else:
                pts = {(x, m[1] + m[2] - y): c for (x, y), c in pts.items()}
        LAST_BOOTS[k] = {(x, y + dy) for x, y in pts}
    return [whole], blades


STRAY_ISLAND = 8  # px; detached bits this small are removed
MAX_HOLE = 8  # px; enclosed transparent areas up to this size are specks to fill
NEIGHBOURS = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]


def holes(im):
    """Small transparent specks (up to MAX_HOLE px) that can't reach the frame edge."""
    px = im.load()
    w, h = im.size
    outside = set()
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in outside or not (0 <= x < w and 0 <= y < h) or px[x, y][3]:
            continue
        outside.add((x, y))
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    inner = {(x, y) for y in range(h) for x in range(w) if not px[x, y][3] and (x, y) not in outside}
    # Only small specks are holes. A larger enclosed opening (the space between a swinging arm and the
    # torso) is real space and stays see-through.
    small, seen = [], set()
    for start in inner:
        if start in seen:
            continue
        comp, stack = [], [start]
        seen.add(start)
        while stack:
            x, y = stack.pop()
            comp.append((x, y))
            for n in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                if n in inner and n not in seen:
                    seen.add(n)
                    stack.append(n)
        if len(comp) <= MAX_HOLE:
            small += comp
    return small


def notches(im):
    """Transparent pixels with 5 or more opaque neighbours: dents cut into the silhouette.
    Spots next to the sword are skipped, so the real gap between blade and body is never webbed over."""
    px = im.load()
    w, h = im.size
    out = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            if px[x, y][3]:
                continue
            near = [(x + dx, y + dy) for dx, dy in NEIGHBOURS if px[x + dx, y + dy][3]]
            if len(near) >= 5 and not any(q in LAST_BLADE for q in near):
                out.append((x, y))
    return out


def fill_from_neighbours(im, spots):
    px = im.load()
    w, h = im.size
    for x, y in spots:
        near = [(x + dx, y + dy) for dx, dy in NEIGHBOURS
                if 0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]]
        if not near:  # no direct neighbour yet: it fills on a later pass as the gap closes inward
            continue
        # A closed gap takes the middle cloth tone of its non-blade neighbours: the darkest neighbour left
        # black spots (it was usually the outline), the most common one painted skin strips along arms.
        c = cloth_tone([px[q] for q in near if q not in LAST_BLADE] or [px[q] for q in near])
        px[x, y] = (int(c[0] * 0.85), int(c[1] * 0.85), int(c[2] * 0.85), c[3])  # a soft fold, not black


KNEE = HIP + 6  # rows from here down are left open between the legs
INTERIOR_REACH = 4  # px: a gap with character pixels this close on all four sides counts as inside


def interior_gaps(im):
    """Transparent pixels with character pixels within INTERIOR_REACH on the left, right, above and below:
    any empty space inside the character's outline. Pixels touching the sword blade are skipped so the
    blade never gets glued to the body."""
    px = im.load()
    w, h = im.size
    out = []
    for y in range(min(h, KNEE)):  # below the knees the space between the feet is real, not a gap
        for x in range(w):
            if px[x, y][3]:
                continue
            touching = [(x + dx, y + dy) for dx, dy in NEIGHBOURS
                        if 0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]]
            # A cut touches the character; a pixel with nothing around it is open space, not a cut.
            # Pixels touching the sword blade are skipped so the blade never gets glued to the body.
            if not touching or any(q in LAST_BLADE for q in touching):
                continue
            def first(dx, dy):  # the first character pixel within reach in one direction, or None
                for k in range(1, INTERIOR_REACH + 1):
                    q = (x + dx * k, y + dy * k)
                    if not (0 <= q[0] < w and 0 <= q[1] < h):
                        return None
                    if px[q][3]:
                        return q
                return None
            left, right, above, below = first(-1, 0), first(1, 0), first(0, -1), first(0, 1)
            # The open space between the hanging sword and the body is real: leave a gap see-through when
            # the first thing across it is the blade (known by position, not guessed from colour).
            if any(q is not None and q in LAST_BLADE for q in (left, right, above, below)):
                continue
            # Closed in on both sides, or above and below: a slit cut into the character, however long.
            if ((left and right and (above or below)) or (above and below and (left or right))):
                out.append((x, y))
    return out


def pieces(im):
    """8-connected opaque pieces, largest first."""
    px = im.load()
    w, h = im.size
    seen, out = set(), []
    for y in range(h):
        for x in range(w):
            if px[x, y][3] and (x, y) not in seen:
                comp, stack = [], [(x, y)]
                seen.add((x, y))
                while stack:
                    a, b = stack.pop()
                    comp.append((a, b))
                    for dx, dy in NEIGHBOURS:
                        n = (a + dx, b + dy)
                        if 0 <= n[0] < w and 0 <= n[1] < h and n not in seen and px[n][3]:
                            seen.add(n)
                            stack.append(n)
                out.append(comp)
    out.sort(key=len, reverse=True)
    return out


REATTACH_REACH = 6  # px: how far a detached arm/sword/cloth piece may slide to touch the body again


def reattach(im):
    """A part that ended up detached (an arm or blade swung clear of the shoulder) slides, unchanged, the
    shortest distance that makes it touch the body again. Tiny specks are left to the stray-island sweep."""
    px = im.load()
    w, h = im.size
    for _ in range(4):
        found = pieces(im)
        if len(found) < 2:
            return
        main = set(found[0])
        moved = False
        for comp in found[1:]:
            if len(comp) <= STRAY_ISLAND:
                continue
            colours = {q: px[q] for q in comp}
            touch = {(x + dx, y + dy) for x, y in main for dx, dy in NEIGHBOURS}
            best = None
            for r in range(1, REATTACH_REACH + 1):
                for dx in range(-r, r + 1):
                    for dy in range(-r, r + 1):
                        if max(abs(dx), abs(dy)) != r:
                            continue
                        if any((x + dx, y + dy) in touch for x, y in comp):
                            d = dx * dx + dy * dy
                            if best is None or d < best[0]:
                                best = (d, dx, dy)
                if best:
                    break
            if not best:
                continue
            _, dx, dy = best
            for q in comp:
                px[q] = (0, 0, 0, 0)
            for (x, y), c in colours.items():
                if 0 <= x + dx < w and 0 <= y + dy < h and not px[x + dx, y + dy][3]:
                    px[x + dx, y + dy] = c
            if any(q in LAST_BLADE for q in comp):
                for q in comp:
                    LAST_BLADE.discard(q)
                LAST_BLADE.update((x + dx, y + dy) for x, y in comp)
            moved = True
        if not moved:
            return


def cleanup(im):
    """Trim hairline dashes, drop stray islands of STRAY_ISLAND pixels or fewer, then close every gap
    a moving part opened."""
    px = im.load()
    w, h = im.size
    # Hairlines: pixels with nothing directly above or below are 1-px-high dashes left by stretched
    # cloth; trim them (twice, so a 2-px dash goes too). The blade and anything touching it is kept:
    # its diagonal pixels are rightly one pixel thick.
    boots = set().union(*LAST_BOOTS) if LAST_BOOTS else set()  # a boot's toe or heel tip is kept too
    for _ in range(2):
        cut = []
        for y in range(1, h - 1):
            for x in range(1, w - 1):
                c = px[x, y]
                if not c[3] or px[x, y - 1][3] or px[x, y + 1][3] or (x, y) in LAST_BLADE or (x, y) in boots:
                    continue
                if any((x + dx, y + dy) in LAST_BLADE for dx, dy in NEIGHBOURS):
                    continue
                cut.append((x, y))
        for q in cut:
            px[q] = (0, 0, 0, 0)
    reattach(im)
    w, h = im.size
    seen = set()
    for y in range(h):
        for x in range(w):
            if not px[x, y][3] or (x, y) in seen:
                continue
            comp, stack = [], [(x, y)]
            seen.add((x, y))
            while stack:
                cx_, cy_ = stack.pop()
                comp.append((cx_, cy_))
                for dx, dy in NEIGHBOURS:
                    n = (cx_ + dx, cy_ + dy)
                    if 0 <= n[0] < w and 0 <= n[1] < h and n not in seen and px[n][3]:
                        seen.add(n)
                        stack.append(n)
            if len(comp) <= STRAY_ISLAND:
                for q in comp:
                    px[q] = (0, 0, 0, 0)
    # Fill last, so nothing removed above can reopen a gap. Dents get two passes (enough to close them,
    # not enough to creep down a real slit); enclosed holes are filled completely.
    for _ in range(2):
        fill_from_neighbours(im, notches(im))
    for _ in range(2):  # the hip band, where the legs separate from the body, gets two more passes
        fill_from_neighbours(im, [(x, y) for x, y in notches(im) if HIP - 4 <= y < HIP + 8])
    # Then close enclosed specks and every empty space inside the outline (so the character reads as
    # solid), repeating both until nothing changes: filling one can leave a small remnant of the other.
    for _ in range(30):
        spots = holes(im) + interior_gaps(im)
        if not spots:
            break
        fill_from_neighbours(im, spots)
    # A fill that reached across open space can leave a 1-2 px speck floating; sweep those.
    for y in range(h):
        for x in range(w):
            if px[x, y][3] and not any(0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]
                                       and (abs(dx) + abs(dy)) > 0
                                       and any(0 <= x + dx + ex < w and 0 <= y + dy + ey < h and px[x + dx + ex, y + dy + ey][3]
                                               and (x + dx + ex, y + dy + ey) != (x, y)
                                               for ex, ey in NEIGHBOURS)
                                       for dx, dy in NEIGHBOURS):
                px[x, y] = (0, 0, 0, 0)
    return im


# The east side is the west side mirrored, so both sides always match (Docs/Art-Spec.md section 3).
MIRROR = {"E": "W", "NE": "NW", "SE": "SW"}


def mirrored(im):
    """Flip a frame left-right about the feet pivot (x = 48), not the cell centre, so the feet stay put."""
    flipped = im.transpose(Image.FLIP_LEFT_RIGHT)  # x -> 95 - x
    out = Image.new("RGBA", im.size, (0, 0, 0, 0))
    out.paste(flipped, (2 * PIVOT[0] - (im.width - 1), 0))  # shift so x -> 96 - x
    return out


def pivoted(path):
    base = hard(Image.open(path).convert("RGBA"))
    cx, bottom = feet_centre(base)
    shift = (round(PIVOT[0] - cx), PIVOT[1] - 1 - bottom)
    moved = Image.new("RGBA", base.size, (0, 0, 0, 0))
    moved.alpha_composite(base, (max(0, shift[0]), max(0, shift[1])), (max(0, -shift[0]), max(0, -shift[1])))
    return moved


def base_for(direction):
    """The pivoted base drawing for a direction; with --classes, each pixel's colour class rides in its alpha."""
    base = pivoted(f"{SRC['dir']}/{SRC['prefix']}_{LABEL_FOR[direction]}_frame01.png")
    if SRC.get("classes"):
        labels = split(base, PARTS[direction])
        # hair that runs past the drawing's hair line (long hair, hairstyles) comes as a mask beside the pose:
        # <prefix>_<LABEL>_hairmask.png, white where the pixel is hair (Tools/female.py, Tools/hair_build.py)
        extra = set()
        mask_path = f"{SRC['dir']}/{SRC['prefix']}_{LABEL_FOR[direction]}_hairmask.png"
        if os.path.exists(mask_path):
            with Image.open(mask_path) as mask:
                mpx = mask.convert("L").load()
                extra = {(x, y) for y in range(mask.height) for x in range(mask.width) if mpx[x, y] > 127}
        base = colour_classes.tag(base, colour_classes.classify(base, labels, PARTS[direction]["hair"], HIP, extra))
    return base


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir")
    ap.add_argument("out")
    ap.add_argument("--prefix", default="cf_human_m_full_rags_walk")
    ap.add_argument("--style", default="walk", choices=sorted(STYLES))
    ap.add_argument("--classes", help="also write the colour-class map (see Tools/colour_classes.py) here")
    ap.add_argument("--motion-out", help="record the whole-figure moves (roll centres, landings) to this JSON")
    ap.add_argument("--motion-in", help="replay whole-figure moves recorded with --motion-out")
    a = ap.parse_args()
    global STYLE
    STYLE = STYLES[a.style]
    SRC["dir"], SRC["prefix"] = a.src_dir, a.prefix
    if a.motion_in:
        with open(a.motion_in) as fh:
            MOTION["fixed"] = json.load(fh)
    if a.motion_out:
        MOTION["record"] = {}
    sheet = build_sheet()
    if a.motion_out:
        with open(a.motion_out, "w") as fh:
            json.dump(MOTION["record"], fh)
    sheet.save(a.out)
    print(f"wrote {a.out}: {sheet.width} x {sheet.height}")
    if a.classes:
        SRC["classes"] = True
        tagged, classes = colour_classes.untag(build_sheet())
        # the class run must move every pixel exactly as the plain run did
        assert tagged.tobytes() == sheet.tobytes(), "class tagging changed the sheet"
        assert all(classes.values()), "a pixel lost its class"
        out = Image.new("L", sheet.size, 0)
        opx = out.load()
        for q, k in classes.items():
            opx[q] = k
        out.save(a.classes)
        print(f"wrote {a.classes}")


def build_sheet():

    LAST_BLADE.clear()
    sheet = Image.new("RGBA", (CELL * 8, CELL * len(ROWS)), (0, 0, 0, 0))
    built = {}
    for direction in ROWS:
        if direction in MIRROR:
            continue
        base = base_for(direction)
        built[direction] = [frame(base, direction, i) for i in range(8)]
    for r, direction in enumerate(ROWS):
        frames = built[direction] if direction not in MIRROR else [mirrored(f) for f in built[MIRROR[direction]]]
        for i, f in enumerate(frames):
            sheet.paste(f, (i * CELL, r * CELL))
    return sheet


if __name__ == "__main__":
    main()
