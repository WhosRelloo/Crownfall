"""Reference recolour for character customization: the same maths as Render/Recolour.luau, for previews and audits.

    python Tools/recolour.py <sheet.png> <classes.png> <out.png> [--skin ID] [--hair ID] [--outfit ID] [--grid]

Each recolourable class (skin, hair, outfit) maps a pixel's brightness, measured against that class's range in
the drawing, onto the chosen ramp. Outfit dye fades out on saturated pixels (leather straps, belts, bracers keep
their colour); see DYE_FULL / DYE_NONE.
"""
import argparse
import colorsys
import json
import os

from PIL import Image

import colour_classes as C

HERE = os.path.dirname(os.path.abspath(__file__))
PALETTES = os.path.join(HERE, "..", "Art", "Sprites", "palettes.json")
SLOT = {C.SKIN: "skin", C.HAIR: "hair", C.OUTFIT: "outfit"}
DYE_FULL, DYE_NONE = 0.50, 0.66  # outfit saturation: fully dyed at or below DYE_FULL, untouched from DYE_NONE


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def load_palettes():
    with open(PALETTES, encoding="utf-8") as f:
        return json.load(f)


def stats(pairs):
    """Brightness range per class (2nd and 98th percentile) from [(sheet, classes)], used to place each pixel on a ramp."""
    vals = {k: [] for k in SLOT}
    for sheet, classes in pairs:
        px, cp = sheet.load(), classes.load()
        for y in range(sheet.height):
            for x in range(sheet.width):
                k = cp[x, y]
                if k in vals and px[x, y][3]:
                    vals[k].append(lum(px[x, y]))
    out = {}
    for k, v in vals.items():
        v.sort()
        out[k] = (round(v[int(0.02 * (len(v) - 1))], 1), round(v[int(0.98 * (len(v) - 1))], 1))
    return out


def ramp_at(ramp, t):
    f = max(0.0, min(1.0, t)) * (len(ramp) - 1)
    i = min(int(f), len(ramp) - 2)
    u = f - i
    a, b = ramp[i], ramp[i + 1]
    return tuple(round(a[j] + (b[j] - a[j]) * u) for j in range(3))


def recolour_pixel(c, k, ramps, ranges):
    """c: (r, g, b); k: class id; ramps: {class: ramp or None}; ranges: {class: (lo, hi)}. Returns (r, g, b)."""
    ramp = ramps.get(k)
    if ramp is None:
        return c
    lo, hi = ranges[k]
    new = ramp_at(ramp, (lum(c) - lo) / (hi - lo))
    if k == C.OUTFIT:
        s = colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)[1]
        w = max(0.0, min(1.0, (DYE_NONE - s) / (DYE_NONE - DYE_FULL)))
        new = tuple(round(c[j] + (new[j] - c[j]) * w) for j in range(3))
    return new


def choose(palettes, skin=None, hair=None, outfit=None):
    """Ramps per class for the chosen ids; an 'original' entry (or None) keeps the drawn colours."""
    out = {}
    for k, slot, pick in ((C.SKIN, "skin", skin), (C.HAIR, "hair", hair), (C.OUTFIT, "outfit", outfit)):
        entry = next((e for e in palettes[slot] if e["id"] == pick), None)
        out[k] = None if entry is None or entry.get("original") else entry["ramp"]
    return out


def recolour(sheet, classes, ramps, ranges):
    out = sheet.copy()
    px, cp = out.load(), classes.load()
    for y in range(out.height):
        for x in range(out.width):
            c = px[x, y]
            if c[3]:
                px[x, y] = recolour_pixel(c[:3], cp[x, y], ramps, ranges) + (c[3],)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sheet")
    ap.add_argument("classes")
    ap.add_argument("out")
    ap.add_argument("--skin")
    ap.add_argument("--hair")
    ap.add_argument("--outfit")
    a = ap.parse_args()
    sheet = Image.open(a.sheet).convert("RGBA")
    classes = Image.open(a.classes)
    ranges = stats([(sheet, classes)])
    recolour(sheet, classes, choose(load_palettes(), a.skin, a.hair, a.outfit), ranges).save(a.out)
    print(f"wrote {a.out}  ranges {ranges}")


if __name__ == "__main__":
    main()
