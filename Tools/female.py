"""Draws the female starter's base poses from the male ones (Docs/Character-Customization.md section 5).

    python Tools/female.py <male_src_dir> <out_dir>

For each of the five drawn directions (S, SW, W, NW, N; the east side is mirrored by walk_cycle.py) this loads the
male walk frame 1, pivots it like walk_cycle.py does, and paints a hand-made overlay on it: long hair over the
shoulders and down the back, a softer face with lips, a shaped chest and a narrower waist. The results are written
as cf_human_f_full_rags_walk_<LABEL>_frame01.png so walk_cycle.py --prefix cf_human_f_full_rags_walk can animate them.

Overlay maps: one string per row, starting at column X. Each character paints one pixel:
  .  keep          x  erase (transparent)
  o  outline       1-6 hair, darkest to highlight
  <  copy the pixel to the right    >  copy the pixel to the left (widens a shape by one pixel)
  p  lip           q  lip shadow     z  skin shadow (a soft jaw)
  a b c e f  skin, light to deep (scalp, ears)        r  brow
  D  darken the pixel already there (fold, shadow)    B  brighten it (highlight)
  W  darken it a little (soft shading)                 H  brighten it a lot (strong highlight)
"""
import argparse
import os
import random

from PIL import Image


HAIR = {"o": (9, 5, 4), "1": (17, 11, 10), "2": (26, 18, 16), "3": (36, 26, 23), "4": (49, 36, 31), "5": (64, 47, 40),
        "6": (82, 61, 51)}
LIP, LIP_SHADOW = (190, 106, 98), (122, 56, 52)
SKIN_SHADOW = (176, 104, 76)
# skin ramp for painted scalp, ears and brows (Tools/hair.py): light from the top-left
SKIN = {"a": (240, 170, 124), "b": (222, 150, 108), "c": (196, 124, 88), "e": (160, 94, 66), "f": (122, 68, 48),
        "r": (92, 56, 42)}
JITTER = 2  # +- per channel on painted hair, so it blends with the painted art
SKIN_JITTER = 4  # painted skin gets a little more grain (a flat gradient reads as plastic next to the cloth)

# direction -> (X, Y, rows): the overlay's top-left in pivoted coordinates
OVERLAYS = {
    "S": (40, 36, [
        "....32.......23.....",
        "...o342.....243o....",
        "...o452......54o....",
        "...o361..pp.163o....",
        "...o242...z.242o....",
        "...o352.....253o....",
        ".xoo243.....342o.ox.",
        ".xoo352.....253o.ox.",
        "xo..o432...234o...ox",
        "....o34o...o43o.....",
        ".....o3o...o3o......",
        "......o.....o.......",
        "....................",
        "....................",
        "....................",
        "....xo.......ox.....",
        "....xo.......ox.....",
        "....xo.......ox.....",
        "....xo.......ox.....",
        "....xo.......ox.....",
        "....................",
        "..o<............>...",
        "..o<............>o..",
        "................>o..",
    ]),
    "W": (42, 38, [
        "............34o.",
        "...........245o.",
        "...p.......353o.",
        "..........2463o.",
        "...........2453o",
        "............353o",
        "............244o",
        ".oB.........353o",
        ".oB..........44o",
        ".............35o",
        ".............24o",
        ".............o3o",
        "..............o.",
        ".xo........ox...",
        ".xo........ox...",
        ".xo........ox...",
        "................",
        "................",
        "...........>o...",
        "............o...",
    ]),
    "SW": (40, 37, [
        ".o342...............",
        ".o352.......23o.....",
        ".o342.pp.....24o....",
        ".o242........35o....",
        "..o352.......243o...",
        "..o342........34o...",
        "..o243.........34o..",
        "...o32..............",
        "....oo..............",
        "....................",
        "....................",
        "....................",
        "....................",
        "....................",
        "....................",
        "....xo......ox......",
        "....xo......ox......",
        "....xo......ox......",
        "....................",
        "....................",
        "..............>o....",
        "..o...........>o....",
        "..o............o....",
    ]),
    "NW": (42, 39, [
        "...o2435342o..",
        "..o324534243o.",
        "..o243543524o.",
        "..o342534253o.",
        "..o234524352o.",
        "..o324353423o.",
        "...o3425342o..",
        "...o2435243o..",
        "...o3452534o..",
        "....o24353o...",
        "....o3425o....",
        ".....o34o.....",
        "......oo......",
    ]),
    "N": (42, 38, [
        "..o24353432o..",
        "..o34254243o..",
        ".o3425435242o.",
        ".o2435424532o.",
        ".o3425345243o.",
        ".o2434534242o.",
        ".o3425435342o.",
        "..o42534524o..",
        "..o32435432o..",
        "..o24354243o..",
        "...o352453o...",
        "...o243542o...",
        "....o3453o....",
        ".....o44o.....",
        "......oo......",
    ]),
}


HAIR_TONES = "123456"


def _split(direction):
    """(body rows, hair rows) of a direction's overlay: hair is the hair tones plus every outline pixel touching
    them; the rest (lips, shoulders, waist, hips, chest) is the body."""
    x0, y0, rows = OVERLAYS[direction]
    grid = [list(r) for r in rows]
    hair = [["." for _ in r] for r in rows]
    for y, row in enumerate(rows):
        for x, ch in enumerate(row):
            near = any(0 <= y + dy < len(rows) and 0 <= x + dx < len(row) and rows[y + dy][x + dx] in HAIR_TONES
                       for dx in (-1, 0, 1) for dy in (-1, 0, 1))
            if ch in HAIR_TONES or (ch == "o" and near):
                hair[y][x] = ch
                grid[y][x] = "."
    return (x0, y0, ["".join(r) for r in grid]), (x0, y0, ["".join(r) for r in hair])


def body_overlay(direction):
    """The female body changes without her hair."""
    return _split(direction)[0]


def hair_overlay(direction):
    """Only her long hair (the "long" hairstyle)."""
    return _split(direction)[1]


def hair_pixels(direction):
    """Every pixel an overlay paints with a hair tone (not its outline), in pivoted coordinates."""
    if direction not in OVERLAYS:
        return set()
    x0, y0, rows = OVERLAYS[direction]
    return {(x0 + dx, y0 + dy) for dy, row in enumerate(rows) for dx, ch in enumerate(row) if ch in "123456"}


def write_hair_mask(path, size, pixels):
    """A mask beside a base pose naming its hair pixels; Tools/walk_cycle.py reads it for the colour classes."""
    mask = Image.new("L", size, 0)
    mpx = mask.load()
    for x, y in pixels:
        mpx[x, y] = 255
    mask.save(path)


def paint(base, overlay, seed):
    rnd = random.Random(seed)
    x0, y0, rows = overlay
    px = base.load()
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            x, y = x0 + dx, y0 + dy
            if ch == ".":
                continue
            c = px[x, y]
            if ch in "<>":
                n = px[x + 1, y] if ch == "<" else px[x - 1, y]
                if n[3]:
                    px[x, y] = n
            elif ch == "x":
                px[x, y] = (0, 0, 0, 0)
            elif ch in HAIR:
                h = HAIR[ch]
                j = 0 if ch == "o" else rnd.randint(-JITTER, JITTER)
                px[x, y] = (max(0, h[0] + j), max(0, h[1] + j), max(0, h[2] + j), 255)
            elif ch == "p":
                px[x, y] = LIP + (255,)
            elif ch == "q":
                px[x, y] = LIP_SHADOW + (255,)
            elif ch == "z":
                px[x, y] = SKIN_SHADOW + (255,)
            elif ch in SKIN:
                k = SKIN[ch]
                j = rnd.randint(-SKIN_JITTER, SKIN_JITTER)
                px[x, y] = (max(0, min(255, k[0] + j)), max(0, min(255, k[1] + j)), max(0, min(255, k[2] + j)), 255)
            elif ch in "DWBH" and c[3]:
                k = {"D": 0.62, "W": 0.82, "B": 1.3, "H": 1.6}[ch]
                px[x, y] = (min(255, int(c[0] * k)), min(255, int(c[1] * k)), min(255, int(c[2] * k)), 255)
    return base


def main():
    import walk_cycle as W  # (walk_cycle imports this module for hair_pixels)

    ap = argparse.ArgumentParser()
    ap.add_argument("male_src")
    ap.add_argument("out_dir")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    for i, d in enumerate(["S", "SW", "W", "NW", "N"]):
        base = W.pivoted(f"{a.male_src}/cf_human_m_full_rags_walk_{W.LABEL_FOR[d]}_frame01.png")
        if d in OVERLAYS:
            base = paint(base, OVERLAYS[d], seed=i)
        out = os.path.join(a.out_dir, f"cf_human_f_full_rags_walk_{W.LABEL_FOR[d]}_frame01.png")
        base.save(out)
        write_hair_mask(out.replace("_frame01.png", "_hairmask.png"), base.size, hair_pixels(d))
        print("wrote", out)


if __name__ == "__main__":
    main()
