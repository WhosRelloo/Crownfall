"""Build an 8-frame walk cycle sheet from one neutral standing frame per direction.

python Tools/walk_cycle.py <src_dir> <out.png> [--prefix cf_human_m_full_rags_walk]

Reads <prefix>_<LABEL>_frame01.png for each direction, using LABEL_FOR to pick the file that really
shows each direction (the walk_v2 upload's labels were shifted). The figure is split into parts with
hand-placed regions (PARTS, measured on 8x gridded views of each base pose) and each part moves:
  legs   alternate: sides swing each leg front-to-back so they cross; front/back lift the stepping leg
  arms   swing opposite the legs, rotating about the shoulder (10 degrees on the sides, 5-7 elsewhere)
  sword  rides with the hand that holds it
  cloak  the tunic flap / cloak tail sways a step behind the hips; on the sides it trails behind
  hair   the top two rows trail 1 px behind on the sides as the body rises
  body   bobs 1 px on the passing frames
Every body part moves rigidly (translate/rotate only), so proportions never change; only cloth bends.
Torso pixels uncovered by a moving arm are filled from their neighbours, and a cleanup pass fills
1-2 px gaps and removes stray islands. Output follows
Docs/Art-Spec.md: rows S, SW, W, NW, N, NE, E, SE; 8 frames of 96 x 96; feet on the pivot (48, 88);
hard alpha.
"""
import argparse
import math
from PIL import Image

ROWS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
# Real direction -> label of the walk_v2 file that shows it (checked against the idle sheet in Studio).
LABEL_FOR = {"S": "N", "SE": "NE", "E": "E", "SW": "SE", "NE": "S", "N": "SW", "NW": "W", "W": "NW"}
BOB = [0, 0, -1, -1, 0, 0, -1, -1]  # contact frames 1 and 5 low, passing frames high
CELL, PIVOT = 96, (48, 88)
HIP = 66  # first leg row after pivoting

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
           "arms": [{"rects": [(36, 46, 43, 66)], "pivot": (40, 46), "phase": 1, "sword": [(29, 64, 39, 87)]},
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
        edge = {(x, y) for x, y in in_rect - blade if not brown(px[x, y])
                and any((x + dx, y + dy) in blade for dx in (-1, 0, 1) for dy in (-1, 0, 1))}
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
    return labels


def transform(points, pivot, angle, scale_y, shift):
    """Inverse-map a set of pixels through rotate(angle) * scale(1, scale_y) about pivot, then shift."""
    if not points:
        return {}
    c, s = math.cos(angle), math.sin(angle)
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    pad = 16  # room for a rotated sword tip
    out = {}
    for dy in range(min(ys) - pad, max(ys) + pad + 1):
        for dx in range(min(xs) - pad, max(xs) + pad + 1):
            vx, vy = dx - shift[0] - pivot[0], dy - shift[1] - pivot[1]
            # inverse rotation, then inverse scale
            rx, ry = vx * c - vy * s, vx * s + vy * c
            sx, sy = round(pivot[0] + rx), round(pivot[1] + ry / scale_y)
            if (sx, sy) in points:
                out[(dx, dy)] = points[(sx, sy)]
    return out


def frame(base, direction, i):
    kind, facing = VIEW[direction]
    parts = PARTS[direction]
    diagonal = facing != 0 and kind != "side"
    p = 2 * math.pi * i / 8
    px = base.load()
    labels = split(base, parts)
    colour = {pt: px[pt[0], pt[1]] for pt in labels}
    cx, bottom = feet_centre(base)
    layers = []  # list of dicts {(x, y): rgba}, drawn in order

    # Legs: each leg is a rigid piece. Side views swing the legs front-to-back in opposite phase, so they
    # pass each other on frames 3 and 7 (a real walk, not a scissor). Front/back views lift the stepping
    # leg straight up (its top tucks under the tunic). Diagonals blend both. Nothing is stretched.
    if kind == "side":
        lift, stride_deg = 1, 16.0
    elif diagonal:
        lift, stride_deg = 1, 9.0
    else:
        lift, stride_deg = 2, 0.0
    hip_pivot = (cx, HIP - 2)
    legs = []
    for side in (-1, 1):
        pts = {pt: colour[pt] for pt, lab in labels.items() if lab == "leg" and (pt[0] < cx) == (side < 0)}
        # Forward is the way the character faces on screen (+x when facing right).
        angle = math.radians(stride_deg) * math.cos(p) * side * (facing or 1)
        if stride_deg:
            swinging = max(0.0, -side * math.sin(p))  # this leg is moving forward through the air
        else:
            swinging = max(0.0, side * math.sin(p))
        # The standing leg stays planted; the swinging leg rises with the body and lifts its foot.
        dy = BOB[i] - round(lift * swinging) if swinging > 0 else 0
        legs.append((swinging, transform(pts, hip_pivot, angle, 1.0, (0, dy))))
    legs.sort(key=lambda l: l[0])  # standing leg first, swinging leg drawn over it as it passes
    layers.extend(layer for _, layer in legs)

    # Body (torso, head, hair): rigid, with the bob. In side views the top two rows of hair trail
    # 1 px behind on the rising frames; the head keeps its size.
    rising = BOB[i] < BOB[i - 1]
    top = min(y for (x, y), lab in labels.items() if lab == "body")
    body = {}
    for (x, y), lab in labels.items():
        if lab != "body":
            continue
        dx = -facing if (kind == "side" and rising and y <= top + 1) else 0
        body[(x + dx, y + BOB[i])] = colour[(x, y)]
    # Where an arm moved off the body, show the torso/sleeve behind it: the arm's own pixel, 35% darker.
    # Only inside the body's outline: between the leftmost and rightmost non-arm pixel of that row.
    span = {}
    for (x, y), lab in labels.items():
        if not isinstance(lab, tuple):
            lo, hi = span.get(y, (x, x))
            span[y] = (min(lo, x), max(hi, x))
    for (x, y), lab in labels.items():
        if not isinstance(lab, tuple) or y not in span:
            continue
        spot = (x, y + BOB[i])
        if spot not in body and span[y][0] <= x <= span[y][1]:
            r_, g_, b_, a_ = colour[(x, y)]
            body[spot] = (int(r_ * 0.65), int(g_ * 0.65), int(b_ * 0.65), a_)
    layers.append(body)

    # Cloak / tunic: sways behind the hips; on the sides it trails behind the walker.
    cl = parts["cloak"]
    cloak = {}
    for (x, y), lab in labels.items():
        if lab != "cloak":
            continue
        t = min(1.0, max(0.0, (y - cl["anchor"]) / max(1, cl["hem"] - cl["anchor"])))
        if kind == "side":
            dx = -facing * round((1 + 0.5 + 0.5 * math.sin(2 * p - 0.8)) * t)
        else:
            amp = 1.5 if kind == "back" else 1.0
            dx = round(amp * math.sin(p - 0.8) * t)
        dy = BOB[i] - (1 if (kind == "side" and BOB[i] < 0 and t > 0.6) else 0)
        # Cloth stretches: cover every pixel between where it was and where it moved, so no gap opens.
        step = 1 if dx >= 0 else -1
        for k in range(0, dx + step, step) if dx else (0,):
            cloak.setdefault((x + k, y + dy), colour[(x, y)])
        cloak[(x + dx, y + dy)] = colour[(x, y)]
    layers.append(cloak)

    # Arms and swords.
    for a, arm in enumerate(parts["arms"]):
        # Rigid swing about the shoulder: no stretching, so the arm keeps its length.
        scale = 1.0
        if kind == "side":
            angle = -facing * math.radians(10) * math.cos(p)  # counter-swing: back while the leading leg is forward
        else:
            fwd = math.sin(p) * arm["phase"]
            outward = -1 if arm["pivot"][0] < cx else 1  # which side of the body this arm hangs on
            deg = 7 if diagonal else 5
            angle = math.radians(deg) * fwd * (facing if diagonal else outward)
        pts = {pt: colour[pt] for pt, lab in labels.items() if lab == ("arm", a)}
        blade = {pt: colour[pt] for pt, lab in labels.items() if lab == ("sword", a)}
        layers.append(transform(pts, arm["pivot"], angle, scale, (0, BOB[i])))
        layers.append(transform(blade, arm["pivot"], angle, scale, (0, BOB[i])))

    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dst = out.load()
    for layer in layers:
        for (x, y), c in layer.items():
            if 0 <= x < base.width and 0 <= y < base.height:
                dst[x, y] = c
    return cleanup(out)


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
            near = [px[x + dx, y + dy] for dx, dy in NEIGHBOURS if px[x + dx, y + dy][3]]
            if len(near) >= 5 and not any(steel(c) for c in near):
                out.append((x, y))
    return out


def fill_from_neighbours(im, spots):
    px = im.load()
    w, h = im.size
    for x, y in spots:
        near = [px[x + dx, y + dy] for dx, dy in NEIGHBOURS
                if 0 <= x + dx < w and 0 <= y + dy < h and px[x + dx, y + dy][3]]
        if not near:  # deep inside a big hole: grow inward on a later pass
            continue
        px[x, y] = max(set(near), key=near.count)


def cleanup(im):
    """Drop stray islands of 5 pixels or fewer, then close every gap a moving part opened."""
    px = im.load()
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
            if len(comp) <= 5:
                for q in comp:
                    px[q] = (0, 0, 0, 0)
    # Fill last, so nothing removed above can reopen a gap. Dents get two passes (enough to close them,
    # not enough to creep down a real slit); enclosed holes are filled completely.
    for _ in range(2):
        fill_from_neighbours(im, notches(im))
    for _ in range(2):  # the hip band, where the legs separate from the body, gets two more passes
        fill_from_neighbours(im, [(x, y) for x, y in notches(im) if HIP - 4 <= y < HIP + 8])
    for _ in range(20):
        spots = holes(im)
        if not spots:
            break
        fill_from_neighbours(im, spots)
    return im


def pivoted(path):
    base = hard(Image.open(path).convert("RGBA"))
    cx, bottom = feet_centre(base)
    shift = (round(PIVOT[0] - cx), PIVOT[1] - 1 - bottom)
    moved = Image.new("RGBA", base.size, (0, 0, 0, 0))
    moved.alpha_composite(base, (max(0, shift[0]), max(0, shift[1])), (max(0, -shift[0]), max(0, -shift[1])))
    return moved


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir")
    ap.add_argument("out")
    ap.add_argument("--prefix", default="cf_human_m_full_rags_walk")
    a = ap.parse_args()

    sheet = Image.new("RGBA", (CELL * 8, CELL * len(ROWS)), (0, 0, 0, 0))
    for r, direction in enumerate(ROWS):
        base = pivoted(f"{a.src_dir}/{a.prefix}_{LABEL_FOR[direction]}_frame01.png")
        for i in range(8):
            sheet.alpha_composite(frame(base, direction, i), (i * CELL, r * CELL))
    sheet.save(a.out)
    print(f"wrote {a.out}: {sheet.width} x {sheet.height}")


if __name__ == "__main__":
    main()
