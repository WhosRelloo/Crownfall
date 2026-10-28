"""Pixel-art ground for Crownfall maps (Mirefen first): grass, mud road, swamp water, with natural edges.

The ground is drawn as flat images at the characters' pixel scale (64 px = 5 studs across). In game each image lies
on the floor stretched along the camera's depth by 1 / sin(pitch), so its pixels come out square on screen.

A map's terrain comes from shapes (Map in Tools/world/mirefen.py): roads as polylines with a width, pools as blobs,
tall-grass patches. Every pixel takes the kind of the nearest shape edge, wobbled by noise so nothing looks drawn
with a ruler. Shading then works per kind: grass in patchy tones with tufts, the road with ruts and pebbles and grass
hanging over its edges, water deepening away from a dark bank with ripples (animated as separate overlay frames).
"""
import math

import numpy as np

# Mirefen palette: wet greens and peat browns, a little muted so the characters' dark rags still read on it.
GRASS = [(46, 66, 36), (60, 84, 42), (74, 100, 48), (92, 118, 56), (118, 142, 68)]
TALL = [(38, 56, 32), (50, 72, 38), (66, 92, 46), (86, 112, 54)]
MUD = [(52, 40, 30), (70, 54, 38), (88, 68, 46), (108, 86, 58), (128, 106, 76)]
WATER = [(18, 46, 48), (24, 60, 60), (30, 74, 70), (40, 92, 82)]
RIPPLE = [(66, 126, 108), (104, 164, 140), (168, 214, 186)]
BANK = [(30, 34, 24), (42, 46, 30), (56, 58, 36)]

GRASS_K, TALL_K, MUD_K, WATER_K = 0, 1, 2, 3


def value_noise(h, w, cell, seed):
    """Smooth noise in 0..1 on an (h, w) grid, features about `cell` px across."""
    rng = np.random.default_rng(seed)
    gh, gw = h // cell + 2, w // cell + 2
    g = rng.random((gh, gw))
    ys = np.arange(h) / cell
    xs = np.arange(w) / cell
    y0 = np.floor(ys).astype(int)
    x0 = np.floor(xs).astype(int)
    ty = ys - y0
    tx = xs - x0
    ty = ty * ty * (3 - 2 * ty)
    tx = tx * tx * (3 - 2 * tx)
    a = g[y0][:, x0]
    b = g[y0][:, x0 + 1]
    c = g[y0 + 1][:, x0]
    d = g[y0 + 1][:, x0 + 1]
    top = a + (b - a) * tx[None, :]
    bot = c + (d - c) * tx[None, :]
    return top + (bot - top) * ty[:, None]


def fbm(h, w, cell, seed, octaves=3):
    out = np.zeros((h, w))
    amp, total = 1.0, 0.0
    for o in range(octaves):
        out += value_noise(h, w, max(2, cell >> o), seed + o * 101) * amp
        total += amp
        amp *= 0.5
    return out / total


def dist_to_polyline(h, w, pts):
    """Distance (px) from every pixel to a polyline."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    best = np.full((h, w), 1e9)
    for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
        dx, dy = x2 - x1, y2 - y1
        L = dx * dx + dy * dy or 1
        t = np.clip(((xx - x1) * dx + (yy - y1) * dy) / L, 0, 1)
        px, py = x1 + t * dx, y1 + t * dy
        best = np.minimum(best, np.hypot(xx - px, yy - py))
    return best


def blob_field(h, w, cx, cy, rx, ry):
    """< 1 inside an ellipse, growing outward."""
    yy, xx = np.mgrid[0:h, 0:w].astype(float)
    return np.hypot((xx - cx) / rx, (yy - cy) / ry)


def terrain(h, w, shapes, seed):
    """Kind per pixel from the shapes, with edges wobbled by noise. Returns (kind, water_depth_px)."""
    wobble = (fbm(h, w, 24, seed) - 0.5) * 2  # -1..1
    fine = (fbm(h, w, 6, seed + 7) - 0.5) * 2
    kind = np.full((h, w), GRASS_K, dtype=np.int8)
    for s in shapes:
        if s["kind"] == "tall":
            f = blob_field(h, w, s["x"], s["y"], s["rx"], s["ry"]) + wobble * 0.35 + fine * 0.08
            kind[(f < 1) & (kind == GRASS_K)] = TALL_K
    for s in shapes:
        if s["kind"] == "road":
            d = dist_to_polyline(h, w, s["pts"]) + wobble * 3.5 + fine * 1.2
            kind[d < s["width"] / 2] = MUD_K
    water = np.zeros((h, w), dtype=bool)
    for s in shapes:
        if s["kind"] == "pool":
            f = blob_field(h, w, s["x"], s["y"], s["rx"], s["ry"]) + wobble * 0.22 + fine * 0.02
            water |= f < 1
        elif s["kind"] == "stream":
            d = dist_to_polyline(h, w, s["pts"]) + wobble * 4 + fine * 1.5
            water |= d < s["width"] / 2
    kind[water] = WATER_K
    # depth: distance into the water from the nearest non-water pixel (a cheap chamfer pass)
    depth = np.where(water, 999, 0).astype(np.int32)
    for _ in range(2):
        for y in range(1, h):
            depth[y] = np.minimum(depth[y], depth[y - 1] + 1)
        for y in range(h - 2, -1, -1):
            depth[y] = np.minimum(depth[y], depth[y + 1] + 1)
        for x in range(1, w):
            depth[:, x] = np.minimum(depth[:, x], depth[:, x - 1] + 1)
        for x in range(w - 2, -1, -1):
            depth[:, x] = np.minimum(depth[:, x], depth[:, x + 1] + 1)
    return kind, depth


def pick(pal, t):
    return pal[max(0, min(len(pal) - 1, int(t)))]


def paint(kind, depth, seed):
    """RGBA ground image (numpy uint8 h x w x 4)."""
    h, w = kind.shape
    rng = np.random.default_rng(seed)
    big = fbm(h, w, 40, seed + 11)
    mid = fbm(h, w, 10, seed + 12)
    grain = rng.random((h, w))
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., 3] = 255

    # grass: patchy tones (light from the top-left shows as slightly lighter patches) with a fine dither
    t = big * 2.4 + mid * 1.1 + (grain - 0.5) * 0.3
    for k, pal in ((GRASS_K, GRASS[:4]), (TALL_K, TALL)):
        m = kind == k
        idx = np.clip((t * (len(pal) - 1) / 3.4).astype(int), 0, len(pal) - 1)
        for i, c in enumerate(pal):
            img[m & (idx == i), :3] = c

    # mud: ruts along the road (darker bands) and pebbles
    m = kind == MUD_K
    rut = (fbm(h, w, 5, seed + 21) > 0.62)
    idx = np.clip((1.6 + mid * 1.6 + (grain - 0.5) * 0.8 - rut * 1.2).astype(int), 0, 3)
    for i, c in enumerate(MUD[:4]):
        img[m & (idx == i), :3] = c
    pebbles = m & (grain > 0.985)
    img[pebbles, :3] = MUD[4]

    # water: deeper away from the bank
    m = kind == WATER_K
    widx = np.clip(3 - (depth // 3) + ((mid - 0.5) * 2).astype(int), 0, 3)
    for i, c in enumerate(WATER):
        img[m & (widx == i), :3] = c
    # bank: the first water pixels below grass read as a dark earth edge (the ground stands above the water)
    bank1 = m & (depth == 1)
    img[bank1, :3] = BANK[0]
    below_land = np.zeros_like(m)
    below_land[1:] = (kind[:-1] != WATER_K) & m[1:]
    img[below_land, :3] = BANK[0]
    two_below = np.zeros_like(m)
    two_below[2:] = (kind[:-2] != WATER_K) & m[2:] & ~below_land[2:]
    img[two_below, :3] = BANK[1]

    # grass edge over mud and water: a darker rim and blades hanging over
    land = (kind == GRASS_K) | (kind == TALL_K)
    edge = np.zeros_like(land)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        sh = np.roll(np.roll(kind, dy, 0), dx, 1)
        edge |= land & ((sh == MUD_K) | (sh == WATER_K))
    img[edge, :3] = GRASS[0]
    _blades(img, kind, rng)
    return img


def _blades(img, kind, rng):
    """Grass tufts: small V blades, light tips, scattered on grass and hanging over road and water edges."""
    h, w = kind.shape
    land = (kind == GRASS_K) | (kind == TALL_K)
    clumps = fbm(h, w, 14, int(rng.integers(1 << 30))) > 0.58  # tufts grow in clumps, not evenly
    n = int(h * w * 0.006)
    ys = rng.integers(3, h - 1, n)
    xs = rng.integers(2, w - 2, n)
    for y, x in zip(ys, xs):
        if not land[y, x] or not clumps[y, x]:
            continue
        tall = kind[y, x] == TALL_K
        hi = GRASS[4] if not tall else TALL[3]
        mid = GRASS[3] if not tall else TALL[2]
        img[y, x, :3] = mid
        img[y - 1, x - 1, :3] = mid
        img[y - 1, x + 1, :3] = mid
        img[y - 2, x - 1, :3] = hi
        img[y - 2, x + 1, :3] = hi
        if tall:
            img[y - 3, x, :3] = hi


def ripple_frames(kind, depth, seed, frames=4):
    """Animated water: transparent overlays holding only ripple highlights - short horizontal streaks that drift
    sideways a pixel or two each frame, and a few glints."""
    h, w = kind.shape
    out = []
    water = (kind == WATER_K) & (depth > 2)
    # noise stretched 5x along x, so highlights come out as horizontal dashes
    narrow = fbm(h, w // 5 + 2, 3, seed + 31)
    for f in range(frames):
        o = np.zeros((h, w, 4), dtype=np.uint8)
        wide = np.repeat(narrow, 5, axis=1)[:, :w]
        wide = np.roll(wide, f * 2, axis=1)
        wide[1::2] = np.roll(wide[1::2], -f, axis=1)  # alternate rows drift the other way: water shimmer
        band = water & (wide > 0.74)
        o[band, :3] = RIPPLE[0]
        o[band, 3] = 255
        top = water & (wide > 0.83)
        o[top, :3] = RIPPLE[1]
        glint = water & (fbm(h, w, 3, seed + 40 + f) > 0.95) & top
        o[glint, :3] = RIPPLE[2]
        out.append(o)
    return out
