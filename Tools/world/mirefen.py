"""Mirefen, the starting region (blueprint 8.1, Prologue): the first map slice.

    python Tools/world/mirefen.py <out_dir>

Writes the ground in 1024 px chunks (ground_<cx>_<cz>.png), each chunk's animated water overlays
(water_<cx>_<cz>_<f>.png), every prop drawing and its sway frames packed into prop atlases (props_<n>.png), a
preview of the whole map with its props, and map.json (chunks, prop kinds with atlas rects, and prop placements).

Ground pixels are character pixels: 64 px = 5 studs across. In game the ground is stretched along the camera's depth
so its pixels come out square on screen (Render/World). Map pixel (x, y) is world X = (x - W/2) * 5/64 studs and
Z = (y - H/2) * 5/64 / sin(pitch) studs; props stand at their foot pixel.
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

import ground as G
import props as P

W = H = 2048  # map pixels
CHUNK = 256  # map pixels per ground tile; each tile image is upscaled UPSCALE x (1024 px), see main()
UPSCALE = 4  # ground tiles are opaque decals, which the engine smooths: 4x4 blocks per map pixel keep them crisp
SEED = 1207

# ---------------------------------------------------------------------------------------------------------- layout
SHAPES = [
    # the Old Road: in from the west, past the shrine turn, on to Halden's Ford's square in the east
    {"kind": "road", "pts": [(0, 1180), (300, 1130), (560, 1210), (820, 1150), (1050, 1060), (1300, 1090),
                             (1560, 1020), (1800, 1040), (2048, 990)], "width": 54},
    {"kind": "road", "pts": [(560, 1210), (520, 980), (430, 760), (360, 560)], "width": 34},  # shrine path
    {"kind": "road", "pts": [(1560, 1020), (1620, 1240), (1700, 1460)], "width": 30},  # to the village edge
    # pools and the stream that links them
    {"kind": "pool", "x": 1000, "y": 520, "rx": 190, "ry": 120},
    {"kind": "pool", "x": 300, "y": 1600, "rx": 160, "ry": 110},
    {"kind": "pool", "x": 1200, "y": 1640, "rx": 120, "ry": 90},
    {"kind": "pool", "x": 1760, "y": 420, "rx": 110, "ry": 140},
    {"kind": "stream", "pts": [(1000, 600), (1080, 820), (1170, 1060), (1190, 1300), (1200, 1580)], "width": 30},
    {"kind": "stream", "pts": [(300, 1560), (520, 1500), (800, 1620), (1100, 1640)], "width": 24},
    # tall grass
    {"kind": "tall", "x": 650, "y": 380, "rx": 220, "ry": 160},
    {"kind": "tall", "x": 1500, "y": 700, "rx": 180, "ry": 140},
    {"kind": "tall", "x": 700, "y": 1820, "rx": 240, "ry": 150},
    {"kind": "tall", "x": 1850, "y": 1750, "rx": 200, "ry": 200},
]
SHRINE = (360, 520)  # Saint Ivel's roadside shrine clearing (props for it come with the market/shrine set)
SQUARE = (1820, 1000)  # Halden's Ford square, east end of the road


def place_props(kind, depth, rng):
    """Placements [(prop id, x, y)] by terrain rules, never overlapping (simple dart throwing)."""
    road = kind == G.MUD_K
    water = kind == G.WATER_K
    land = (kind == G.GRASS_K) | (kind == G.TALL_K)
    # distance from road / water, coarse (chamfer on a 4x grid is plenty for placement)
    def dist_from(mask, step=4):
        small = mask[::step, ::step]
        d = np.where(small, 0, 999).astype(np.int32)
        for _ in range(2):
            for y in range(1, d.shape[0]):
                d[y] = np.minimum(d[y], d[y - 1] + 1)
            for y in range(d.shape[0] - 2, -1, -1):
                d[y] = np.minimum(d[y], d[y + 1] + 1)
            for x in range(1, d.shape[1]):
                d[:, x] = np.minimum(d[:, x], d[:, x - 1] + 1)
            for x in range(d.shape[1] - 2, -1, -1):
                d[:, x] = np.minimum(d[:, x], d[:, x + 1] + 1)
        return np.repeat(np.repeat(d, step, 0), step, 1)[: mask.shape[0], : mask.shape[1]] * step

    d_road = dist_from(road)
    d_water = dist_from(water)
    d_shrine = np.hypot(*np.mgrid[0:H, 0:W][::-1] - np.array(SHRINE)[:, None, None])
    d_square = np.hypot(*np.mgrid[0:H, 0:W][::-1] - np.array(SQUARE)[:, None, None])
    groves = G.fbm(H, W, 160, SEED + 5) > 0.52  # trees gather in groves
    placed = []

    def free(x, y, r):
        return all((x - px) ** 2 + (y - py) ** 2 > (r + pr) ** 2 for _, px, py, pr in placed)

    def throw(pid, count, radius, ok, tries=40):
        n = 0
        for _ in range(count * tries):
            if n >= count:
                break
            x, y = int(rng.integers(40, W - 40)), int(rng.integers(60, H - 10))
            if ok(x, y) and free(x, y, radius):
                variants = VARIANTS[pid]
                placed.append((variants[int(rng.integers(len(variants)))], x, y, radius))
                n += 1

    clear = lambda x, y: d_shrine[y, x] > 130 and d_square[y, x] > 220
    throw("tree_big", 26, 46, lambda x, y: land[y, x] and groves[y, x] and d_road[y, x] > 60 and d_water[y, x] > 60 and clear(x, y))
    throw("tree_mid", 34, 38, lambda x, y: land[y, x] and d_road[y, x] > 50 and d_water[y, x] > 50 and clear(x, y))
    throw("tree_moss", 22, 42, lambda x, y: land[y, x] and d_water[y, x] < 140 and d_water[y, x] > 48 and d_road[y, x] > 50 and clear(x, y))
    throw("bush", 70, 18, lambda x, y: land[y, x] and d_road[y, x] > 22 and d_water[y, x] > 10 and clear(x, y))
    throw("bush_moss", 40, 14, lambda x, y: land[y, x] and d_road[y, x] > 20 and d_water[y, x] > 8)
    throw("rock", 26, 16, lambda x, y: land[y, x] and d_road[y, x] > 18)
    throw("rock_small", 40, 10, lambda x, y: (land[y, x] or road[y, x]) and d_water[y, x] > 6)
    throw("stump", 18, 14, lambda x, y: land[y, x] and d_road[y, x] > 24)
    throw("log", 8, 34, lambda x, y: land[y, x] and d_road[y, x] > 40 and d_water[y, x] > 20)
    throw("mushroom", 16, 18, lambda x, y: land[y, x] and d_water[y, x] < 90 and d_road[y, x] > 30)
    throw("mushroom_small", 30, 10, lambda x, y: land[y, x] and d_water[y, x] < 120)
    throw("reeds", 120, 7, lambda x, y: land[y, x] and d_water[y, x] < 10)
    throw("reeds_plain", 80, 6, lambda x, y: (land[y, x] and d_water[y, x] < 14) or (water[y, x] and depth[y, x] < 6))
    throw("lily", 60, 8, lambda x, y: water[y, x] and depth[y, x] > 8)
    throw("lily_flower", 16, 8, lambda x, y: water[y, x] and depth[y, x] > 10)
    return [(pid, x, y) for pid, x, y, _ in placed]


# ------------------------------------------------------------------------------------------------------ prop kinds
KINDS = {}
VARIANTS = {}  # placement id -> its drawn variants (a placement picks one at random)


def _kind(pid, draw, frames=1, amp=0.0, block=0, decal=False):
    KINDS[pid] = (draw, frames, amp, block, decal)
    VARIANTS.setdefault(pid.rsplit("_v", 1)[0], []).append(pid)


# id: drawing, sway frames, sway amplitude px, collision radius px (0 = walk through), lies flat on the ground
for v in range(4):
    _kind(f"tree_big_v{v}", lambda v=v: P.tree(110 + v, 1.1 + 0.05 * v), 4, 1.5, 9)
    _kind(f"tree_mid_v{v}", lambda v=v: P.tree(120 + v, 0.85 + 0.04 * v), 4, 1.2, 7)
    _kind(f"tree_moss_v{v}", lambda v=v: P.tree(130 + v, 0.95 + 0.05 * v, P.LEAF_MOSS, moss=True), 4, 1.4, 8)
    _kind(f"bush_v{v}", lambda v=v: P.bush(140 + v, 0.9 + 0.1 * v), 4, 1.0)
for v in range(3):
    _kind(f"bush_moss_v{v}", lambda v=v: P.bush(150 + v, 0.65 + 0.1 * v, P.LEAF_MOSS), 4, 0.8)
    _kind(f"rock_v{v}", lambda v=v: P.rock(160 + v, 0.9 + 0.15 * v), block=12)
    _kind(f"rock_small_v{v}", lambda v=v: P.rock(170 + v, 0.5 + 0.1 * v))
    _kind(f"mushroom_v{v}", lambda v=v: P.mushroom(180 + v, 0.85 + 0.15 * v), block=5)
    _kind(f"mushroom_small_v{v}", lambda v=v: P.mushroom(190 + v, 0.45 + 0.1 * v))
    _kind(f"reeds_v{v}", lambda v=v: P.reeds(200 + v), 4, 1.0)
    _kind(f"reeds_plain_v{v}", lambda v=v: P.reeds(210 + v, False), 4, 1.0)
for v in range(2):
    _kind(f"stump_v{v}", lambda v=v: P.stump(220 + v, 0.9 + 0.2 * v), block=9)
    _kind(f"log_v{v}", lambda v=v: P.log(230 + v, 60 + 16 * v))
    _kind(f"lily_v{v}", lambda v=v: P.lilypad(240 + v), decal=True)
_kind("lily_flower_v0", lambda: P.lilypad(250, True), decal=True)


def pack_props(out_dir):
    """Every prop's frames into atlases (512 wide shelves). Returns {id: {...frame rects...}}."""
    frames = []
    for pid, (draw, n, amp, block, decal) in KINDS.items():
        img = draw()
        seq = P.sway(img, n, amp) if n > 1 else [img]
        for f, fr in enumerate(seq):
            frames.append((pid, f, fr))
    frames.sort(key=lambda t: -t[2].shape[0])
    atlases, rects = [], {}
    AW, AH, pad = 1024, 1024, 1
    sheet = np.zeros((AH, AW, 4), dtype=np.uint8)
    x = y = shelf = 0
    for pid, f, fr in frames:
        h, w = fr.shape[:2]
        if x + w > AW:
            x, y, shelf = 0, y + shelf + pad, 0
        if y + h > AH:
            atlases.append(sheet)
            sheet = np.zeros((AH, AW, 4), dtype=np.uint8)
            x = y = shelf = 0
        sheet[y:y + h, x:x + w] = fr
        rects.setdefault(pid, {})[f] = [len(atlases), x, y, w, h]
        x += w + pad
        shelf = max(shelf, h)
    atlases.append(sheet)
    for i, a in enumerate(atlases):
        Image.fromarray(a).save(os.path.join(out_dir, f"props_{i}.png"))
    kinds = {}
    for pid, (draw, n, amp, block, decal) in KINDS.items():
        r = rects[pid]
        kinds[pid] = {"frames": [r[f] for f in range(n)], "fps": 3 if n > 1 else 0, "block": block, "decal": decal}
    return kinds, len(atlases)


def main():
    out = sys.argv[1]
    os.makedirs(out, exist_ok=True)
    rng = np.random.default_rng(SEED)
    kind, depth = G.terrain(H, W, SHAPES, SEED)
    img = G.paint(kind, depth, SEED)
    ripples = G.ripple_frames(kind, depth, SEED)
    placements = place_props(kind, depth, rng)
    # flat props (lily pads) are painted into the ground: the ground is opaque, nothing lies on it see-through
    base = Image.fromarray(img)
    for pid, x, y in placements:
        if KINDS[pid][4]:
            p = Image.fromarray(KINDS[pid][0]())
            base.alpha_composite(p, (int(x - p.width / 2), int(y - p.height)))
    img = np.array(base)
    placements = [t for t in placements if not KINDS[t[0]][4]]
    for f in [f for f in os.listdir(out) if f.startswith(("ground_", "water_"))]:
        os.remove(os.path.join(out, f))
    chunks = []
    for cz in range(H // CHUNK):
        for cx in range(W // CHUNK):
            sl = (slice(cz * CHUNK, (cz + 1) * CHUNK), slice(cx * CHUNK, (cx + 1) * CHUNK))
            tile = Image.fromarray(img[sl])
            big = (CHUNK * UPSCALE, CHUNK * UPSCALE)
            has_water = bool((kind[sl] == G.WATER_K).any())
            if has_water:  # each frame is the whole tile with that frame's ripples painted in
                for f, r in enumerate(ripples):
                    t = tile.copy()
                    t.alpha_composite(Image.fromarray(r[sl]))
                    t.resize(big, Image.NEAREST).save(os.path.join(out, f"ground_{cx}_{cz}_{f}.png"))
            else:
                tile.resize(big, Image.NEAREST).save(os.path.join(out, f"ground_{cx}_{cz}.png"))
            chunks.append({"cx": cx, "cz": cz, "water": has_water})
    kinds, n_atlas = pack_props(out)
    with open(os.path.join(out, "map.json"), "w") as f:
        json.dump({"size": [W, H], "chunk": CHUNK, "chunks": chunks, "atlases": n_atlas, "kinds": kinds,
                   "props": placements, "shrine": SHRINE, "square": SQUARE}, f)
    # preview: ground + props drawn back to front
    prev = Image.fromarray(img)
    prev.alpha_composite(Image.fromarray(ripples[0]))
    drawn = {pid: KINDS[pid][0]() for pid in KINDS}
    for pid, x, y in sorted(placements, key=lambda t: t[2]):
        p = Image.fromarray(drawn[pid])
        prev.alpha_composite(p, (int(x - p.width / 2), int(y - p.height)))
    prev.save(os.path.join(out, "preview.png"))
    prev.resize((1024, 1024), Image.LANCZOS).save(os.path.join(out, "preview_small.png"))
    print(f"wrote {out}: {len(chunks)} chunks, {n_atlas} prop atlases, {len(placements)} props")


if __name__ == "__main__":
    main()
