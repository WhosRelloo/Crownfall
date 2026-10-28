"""Hairstyle drawing helper (Tools/hair.py): a hairstyle is drawn as a silhouette per direction, and this shades it.

Silhouette characters (pivoted coordinates, one string per row from (X, Y)):
  #  hair          t  tie / band (darkest)        s  stubble (the scalp shaded darker, with flecks)
  .  nothing

The shader turns a silhouette into an overlay for Tools/female.py's painter:
  - outline (o) where hair meets open air or cloth; a soft dark edge where it meets skin (forehead, neck);
  - light from the top-left like the rest of the art: tones 6 (highlight) to 2 across the shape;
  - a texture per style: straight strands, waves, curls, braid crossings, or smooth.
"""

TEXTURES = ("straight", "wavy", "curly", "braid", "smooth")


def grid(x0, y0, rows):
    """{(x, y): char} for every non-'.' character."""
    out = {}
    for dy, row in enumerate(rows):
        for dx, ch in enumerate(row):
            if ch != ".":
                out[(x0 + dx, y0 + dy)] = ch
    return out


def merge(*grids):
    """Later grids win."""
    out = {}
    for g in grids:
        out.update(g)
    return out


def _skin(c):
    return c[3] and c[0] > 110 and c[0] - c[2] > 40


def _hash(x, y):
    return ((x * 73856093) ^ (y * 19349663) ^ (x * y * 83492791)) & 0xFFFF


def shade(sil, bald, texture="straight", light=0.0):
    """sil: {(x, y): '#'|'t'|'s'}; bald: the bald base image under it. Returns (X, Y, rows) for female.paint.
    light: -1..1 shifts the whole shape darker or lighter."""
    assert texture in TEXTURES, texture
    hair = {p for p, k in sil.items() if k in "#t"}
    if not sil:
        return (0, 0, [])
    xs = [p[0] for p in sil]
    ys = [p[1] for p in sil]
    left, right, top, bottom = min(xs), max(xs), min(ys), max(ys)
    bpx = bald.load()
    w, h = max(1, right - left), max(1, bottom - top)
    out = {}
    for (x, y), kind in sil.items():
        if kind == "s":  # stubble: the scalp a little darker, with sparse darker flecks
            out[(x, y)] = "D" if _hash(x, y) % 4 == 0 else "W"
            continue
        if kind == "t":
            out[(x, y)] = "1"
            continue
        edge = None
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            n = (x + dx, y + dy)
            if n in hair:
                continue
            c = bpx[n] if 0 <= n[0] < bald.width and 0 <= n[1] < bald.height else (0, 0, 0, 0)
            edge = "soft" if (_skin(c) and edge is None) else "hard"
            if edge == "hard":
                break
        if edge == "hard":
            out[(x, y)] = "o"
            continue
        v = (y - top) / h
        u = (x - left) / w
        tone = 5.6 - (0.62 * v + 0.38 * u) * 3.4 + light
        r = _hash(x, y)
        if texture == "straight":  # vertical strands: a few light and dark streaks
            s = _hash(x, y // 3) % 5
            tone += {0: 1, 1: 0, 2: 0, 3: -1, 4: 0}[s]
        elif texture == "wavy":  # strands that shift sideways every few rows
            s = _hash(x + ((y // 3) % 2), 0) % 4
            tone += {0: 1, 1: 0, 2: -1, 3: 0}[s]
        elif texture == "curly":  # clumps: light tops, dark undersides
            cx, cy = x // 2, y // 2
            tone += 1 if (cx + cy) % 2 == 0 and y % 2 == 0 else (-1 if (cx + cy) % 2 else 0)
        elif texture == "braid":  # crossing plaits
            tone += -1.5 if (x + y) % 3 == 0 else (0.8 if (x - y) % 3 == 0 else 0)
        elif texture == "smooth":
            tone += 0.6 if r % 7 == 0 else 0
        if edge == "soft":
            tone = min(tone, 2)
        out[(x, y)] = str(max(1, min(6, round(tone))))
    rows = []
    for y in range(top, bottom + 1):
        rows.append("".join(out.get((x, y), ".") for x in range(left, right + 1)))
    return (left, top, rows)


# The scalp a short haircut covers, per drawn direction: the bald skull above a natural hairline (Tools/hair.py BALD).
CAP = {
    "S": (43, 29, [
        "....######....",
        "..##########..",
        ".############.",
        ".############.",
        ".############.",
        ".###......###.",
        ".##........##.",
    ]),
    "SW": (42, 28, [
        ".....#####......",
        "...#########....",
        "..###########...",
        "..###########...",
        ".#############..",
        ".###.....#####..",
        ".##.......###...",
        "..#........##...",
    ]),
    "W": (42, 31, [
        ".....#####......",
        "...#########....",
        "..###########...",
        "..###########...",
        "...###########..",
        ".....#########..",
        ".......#######..",
        "...........##...",
    ]),
    "NW": (42, 30, [
        ".....######.....",
        "...##########...",
        "..############..",
        ".#############..",
        ".#############..",
        "..############..",
        "..###########...",
        "...#########....",
    ]),
    "N": (42, 28, [
        "....######......",
        "...########.....",
        "..##########....",
        ".############...",
        ".############...",
        ".############...",
        "..##########....",
        "..##########....",
        "...########.....",
    ]),
}


def cap(direction, kind="#"):
    x0, y0, rows = CAP[direction]
    return {p: kind for p in grid(x0, y0, rows)}
