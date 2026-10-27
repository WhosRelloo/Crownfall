"""Build an 8-frame walk cycle sheet from one neutral standing frame per direction.

python Tools/walk_cycle.py <src_dir> <out.png> [--prefix cf_human_m_full_rags_walk] [--hip 58]

Reads <prefix>_<LABEL>_frame01.png for each direction, using LABEL_FOR below to pick the file that
really shows each direction (the walk_v2 upload's labels were shifted). Each leg moves on its own:
front/back views lift the stepping foot, side views open and close the stride, diagonals blend both.
The body bobs 1 px on the passing frames. Output follows Docs/Art-Spec.md: rows S, SW, W, NW, N, NE,
E, SE; 8 frames of 96 x 96; feet centred on the pivot (48, 88); hard alpha.

This is procedural in-betweening of a still pose, not hand animation: arms and cloth don't move.
"""
import argparse
import math
from PIL import Image

ROWS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
# Real direction -> label of the walk_v2 file that shows it (checked against the idle sheet in Studio).
LABEL_FOR = {"S": "N", "SE": "NE", "E": "E", "SW": "SE", "NE": "S", "N": "SW", "NW": "W", "W": "NW"}
# How much of each motion a view gets: (foot lift px, stride half-width px at the feet).
MOTION = {
    "S": (2, 0), "N": (2, 0),
    "E": (0, 4), "W": (0, 4),
    "SE": (1, 2), "SW": (1, 2), "NE": (1, 2), "NW": (1, 2),
}
BOB = [0, 0, -1, -1, 0, 0, -1, -1]  # contact frames 1 and 5 low, passing frames high
CELL, PIVOT = 96, (48, 88)


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


def frame(base, direction, i, hip):
    lift, stride = MOTION[direction]
    p = 2 * math.pi * i / 8
    cx, bottom = feet_centre(base)
    span = max(1, bottom - hip)
    src = base.load()
    out = Image.new("RGBA", base.size, (0, 0, 0, 0))
    dst = out.load()
    # Upper body: copied with the bob.
    for y in range(0, hip):
        for x in range(base.width):
            if src[x, y][3]:
                ny = y + BOB[i]
                if 0 <= ny < base.height:
                    dst[x, ny] = src[x, y]
    # Legs: left half and right half move in opposite phase. Back leg drawn first.
    halves = [(-1, lambda x: x < cx), (1, lambda x: x >= cx)]
    for side, inside in halves:
        swing = math.sin(p) * side  # +1: this leg is stepping forward

        def target(y):
            t = min(1.0, max(0.0, (y - hip) / span))
            dy = BOB[i] * (1 - t) - lift * max(0.0, swing) * t
            return round(y + dy), round(stride * abs(math.cos(p)) * t) * side

        for y in range(hip, base.height):
            ty, dx = target(y)
            # When neighbouring rows land two apart, also draw this row one lower so the leg has no gap.
            rows_to_draw = [ty] if target(y + 1)[0] - ty < 2 else [ty, ty + 1]
            for x in range(base.width):
                if inside(x) and src[x, y][3]:
                    for ny in rows_to_draw:
                        nx = x + dx
                        if 0 <= nx < base.width and 0 <= ny < base.height:
                            dst[nx, ny] = src[x, y]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src_dir")
    ap.add_argument("out")
    ap.add_argument("--prefix", default="cf_human_m_full_rags_walk")
    ap.add_argument("--hip", type=int, default=58)
    a = ap.parse_args()

    sheet = Image.new("RGBA", (CELL * 8, CELL * len(ROWS)), (0, 0, 0, 0))
    for r, direction in enumerate(ROWS):
        base = hard(Image.open(f"{a.src_dir}/{a.prefix}_{LABEL_FOR[direction]}_frame01.png").convert("RGBA"))
        cx, bottom = feet_centre(base)
        # Move the figure so its feet sit on the pivot: feet centre x = 48, feet bottom row = 87.
        shift = (round(PIVOT[0] - cx), PIVOT[1] - 1 - bottom)
        moved = Image.new("RGBA", base.size, (0, 0, 0, 0))
        moved.alpha_composite(base, (max(0, shift[0]), max(0, shift[1])), (max(0, -shift[0]), max(0, -shift[1])))
        for i in range(8):
            sheet.alpha_composite(frame(moved, direction, i, a.hip + shift[1]), (i * CELL, r * CELL))
    sheet.save(a.out)
    print(f"wrote {a.out}: {sheet.width} x {sheet.height}")


if __name__ == "__main__":
    main()
