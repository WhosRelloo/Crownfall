"""Pixel-art props for Crownfall maps: trees, bushes and the like, drawn in code at the characters' pixel scale.

Each prop is an RGBA image whose bottom-centre is where it stands (its foot), with a soft ground shadow drawn in.
Everything is shaded as if lit from the upper left, in hue-shifted ramps (shadows cool, lights warm), with banded
tones rather than noise. Trees and bushes are built from lobed leaf clumps, each shaded like a ball of leaves, back
clumps first; a front clump casts a shadow on the ones behind it. sway() makes animation frames in which the top
moves most and the roots stay put.
"""
import math

import numpy as np

OUTLINE = (16, 22, 14)
LEAF_MIREFEN = [(14, 30, 30), (22, 46, 38), (34, 66, 44), (52, 90, 48), (78, 118, 54), (116, 150, 70)]
LEAF_MOSS = [(30, 36, 24), (46, 58, 28), (66, 82, 32), (92, 106, 38), (124, 134, 50), (164, 168, 78)]
BARK = [(30, 22, 24), (46, 32, 30), (66, 46, 36), (90, 64, 44), (116, 88, 60)]
SHADOW = (12, 18, 12, 110)
MOSS_STRAND = [(70, 92, 40), (110, 132, 52), (156, 172, 78)]


def _rng(seed):
    return np.random.default_rng(seed)


def _outline(img):
    """Coloured 1 px outline around every opaque area (a dark shade of the colour inside)."""
    out = fine_outline(img)
    img[...] = out
    return img


def _shadow(img, cx, cy, rx, ry):
    contact_shadow(img, cx, cy, rx, ry)


def _ball(xx, yy, bx, by, r, lobes=None):
    """(inside mask, distance 0..1, sphere shade 0..1) for a lobed ball lit from the upper left."""
    dx, dy = xx - bx, yy - by
    d = np.hypot(dx, dy) / (r * (lobes if lobes is not None else 1))
    inside = d < 1
    nz = np.sqrt(np.clip(1 - d ** 2, 0, 1))
    nx, ny = dx / r, dy / r
    shade = np.clip(-0.55 * nx - 0.6 * ny + 0.58 * nz, 0, 1)
    return inside, d, shade


def canopy(img, cx, cy, rw, rh, puffs, pal, seed, texture=0.5):
    """Draw a canopy of `puffs` leaf clumps inside the ellipse (cx, cy, rw, rh). Back clumps first; each clump is a
    lobed ball of leaves with leaf-cluster highlights on its lit side, and drops a shadow on the clumps behind."""
    rng = _rng(seed)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    blobs = []
    for i in range(puffs):
        ang = rng.random() * math.tau
        rad = math.sqrt(rng.random()) * 0.6
        bx = cx + math.cos(ang) * rw * rad
        by = cy + math.sin(ang) * rh * rad
        r = (0.40 + rng.random() * 0.18) * min(rw, rh)
        blobs.append((by, bx, r))
    blobs.sort()  # top (back) clumps first, front ones over them
    # leaf clusters: little 2-4 px leaves, each lit on its upper left and dark below
    leaf = np.zeros((h, w))
    for _ in range(int(rw * rh * 0.09)):
        lx0 = cx + (rng.random() - 0.5) * 2.1 * rw
        ly0 = cy + (rng.random() - 0.5) * 2.1 * rh
        rr = 1.3 + rng.random() * 1.3
        dd = np.hypot(xx - lx0, yy - ly0)
        cell = dd < rr
        up = (xx - lx0) + (yy - ly0) < 0
        leaf = np.where(cell & up, 1.0, np.where(cell & ~up & (leaf == 0), -1.0, leaf))
    tone = np.full((h, w), -1.0)
    n = len(blobs)
    for i, (by, bx, r) in enumerate(blobs):
        ang = np.arctan2(yy - by, xx - bx)
        phase = rng.random() * math.tau
        lobes = 1 + 0.11 * np.sin(ang * (6 + int(rng.random() * 3)) + phase) + 0.05 * np.sin(ang * 13 + phase * 2)
        inside, d, shade = _ball(xx, yy, bx, by, r, lobes)
        # this clump's shadow on what is already drawn behind it (down and right)
        sh = (np.hypot(xx - bx - 2, yy - by - 3) / (r * lobes) < 1) & ~inside & (tone >= 0)
        tone[sh] = np.maximum(0, tone[sh] - 1.4)
        depth = 0.6 * (i / max(1, n - 1)) - 0.3  # front clumps slightly brighter
        t = 0.6 + shade * 4.2 + depth + leaf * 0.8 * (0.3 + shade)
        t = np.where(d > 0.88, t - 1.0, t)  # the edge turns away from us
        tone[inside] = t[inside]
    m = tone >= 0
    idx = np.clip(np.round(tone).astype(int), 0, len(pal) - 1)
    col = np.array(pal, dtype=np.uint8)[idx]
    img[m, :3] = col[m]
    img[m, 3] = 255
    return img


def trunk(img, x, top, bottom, width, seed):
    """A round trunk from `top` to `bottom` (the foot): bark ridges, lit on the left, flaring into roots."""
    rng = _rng(seed)
    h, w = img.shape[:2]
    ridge = rng.random(64)
    for y in range(top, bottom + 1):
        flare = max(0, (y - (bottom - 8))) ** 1.3 * 0.8
        half = width / 2 * (0.78 + 0.22 * (y - top) / max(1, bottom - top)) + flare
        for xx in range(int(x - half), int(x + half) + 1):
            if 0 <= xx < w and 0 <= y < h and img[y, xx, 3] == 0:
                rel = (xx - (x - half)) / max(1, 2 * half)
                t = 4.2 - abs(rel - 0.3) * 6
                col = int((xx - x + 32)) % 64
                if (xx - int(x - half)) % 3 == 0 and ridge[col] > 0.3:
                    t -= 1.0  # bark furrow
                if (y + col * 3) % 11 == 0:
                    t -= 0.6
                if y < top + 5:
                    t -= 1.2  # the crown's shadow on the trunk
                img[y, xx] = pal_at(BARK, t) + (255,)
    for dx in (-1, 1):  # roots: claws reaching out along the ground, lit on top
        for root in range(2):
            reach = int(width * (0.55 + 0.3 * root))
            for k in range(reach):
                rx = int(x + dx * (width / 2 + 1 + k + root * 2))
                ry = bottom - max(0, (reach - k) // 4) + root
                if 0 <= rx < w and 0 <= ry < h and img[ry, rx, 3] == 0:
                    img[ry, rx] = BARK[3 if dx < 0 else 2] + (255,)
                    if ry + 1 < h and img[ry + 1, rx, 3] == 0:
                        img[ry + 1, rx] = BARK[1] + (255,)


def moss_strands(img, cx, bottom_y, rw, seed, count=9):
    """Moss hanging from under a canopy (swamp trees): strands that thin out, lit on top."""
    rng = _rng(seed)
    h, w = img.shape[:2]
    for _ in range(count):
        x = int(cx + (rng.random() - 0.5) * rw * 1.6)
        col = img[:, x, 3] if 0 <= x < w else None
        if col is None or not col.any():
            continue
        y0 = int(np.nonzero(col)[0].max())
        length = int(5 + rng.random() * 12)
        wobble = rng.random() * 6
        for k in range(length):
            y = y0 + k
            xk = x + int(round(math.sin(k / 3 + wobble) * 0.7))
            if y >= h or not 0 <= xk < w:
                break
            img[y, xk] = MOSS_STRAND[0 if k > length - 4 else (2 if k < 2 else 1)] + (255,)
            if k < length * 0.5 and xk + 1 < w and img[y, xk + 1, 3] == 0:
                img[y, xk + 1] = MOSS_STRAND[0] + (255,)


def tree(seed, size=1.0, pal=LEAF_MIREFEN, moss=False):
    """A broadleaf tree. size 1.0 ~ 140 px tall (about twice a character)."""
    W, H = int(140 * size), int(160 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    foot = H - 6
    cx = W // 2
    crown_h = int(H * 0.72)
    canopy(img, cx, int(crown_h * 0.52) + 4, W * 0.44, crown_h * 0.48, puffs=int(11 + 7 * size), pal=pal, seed=seed)
    if moss:
        moss_strands(img, cx, crown_h, W * 0.38, seed + 3, count=int(9 * size) + 5)
    trunk(img, cx + int((_rng(seed + 1).random() - 0.5) * 6), int(crown_h * 0.8), foot, max(7, int(12 * size)), seed + 2)
    _outline(img)
    _shadow(img, cx, foot + 1, W * 0.32, 5 * size + 2)
    return img


def bush(seed, size=1.0, pal=LEAF_MIREFEN):
    W, H = int(56 * size), int(44 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    canopy(img, W // 2, H // 2 + 1, W * 0.44, H * 0.40, puffs=int(5 + 3 * size), pal=pal, seed=seed, texture=0.7)
    rng = _rng(seed + 9)
    for _ in range(int(3 * size)):  # a few berries
        bx, by = int(W * (0.25 + rng.random() * 0.5)), int(H * (0.3 + rng.random() * 0.4))
        if img[by, bx, 3] and img[by + 1, bx + 1, 3]:
            img[by, bx] = (176, 52, 60, 255)
            img[by + 1, bx + 1] = (110, 30, 40, 255)
            img[by, bx + 1] = (120, 34, 44, 255)
    _outline(img)
    _shadow(img, W // 2, H - 3, W * 0.42, 3)
    return img


def sway(img, frames=4, amp=1.5, foot_rows=12):
    """Animation frames: each row shifts sideways by up to `amp` px, most at the top, none at the roots."""
    h = img.shape[0]
    out = []
    for f in range(frames):
        phase = math.sin(f / frames * math.tau)
        frame = np.zeros_like(img)
        for y in range(h):
            k = max(0.0, 1 - y / max(1, h - foot_rows))
            frame[y] = np.roll(img[y], int(round(amp * phase * k)), axis=0)
        out.append(frame)
    return out


STONE = [(38, 40, 48), (56, 58, 64), (78, 80, 82), (102, 102, 98), (128, 126, 116), (156, 152, 136)]
MOSS = [(40, 60, 30), (60, 86, 36), (88, 114, 44), (122, 146, 60)]
CAP = [(62, 50, 82), (88, 74, 110), (118, 102, 140), (154, 140, 172), (196, 186, 210)]  # pale violet swamp caps
GILL = [(110, 92, 104), (140, 124, 130)]
STEM = [(120, 114, 108), (150, 142, 126), (186, 176, 154), (220, 212, 192)]
REED = [(34, 56, 32), (52, 78, 36), (76, 104, 44), (108, 136, 58), (146, 166, 80)]
CATTAIL = [(52, 32, 24), (80, 52, 32), (110, 76, 46)]
LILY = [(26, 56, 38), (40, 82, 46), (60, 108, 56), (92, 140, 70)]
BLOSSOM = [(186, 110, 150), (226, 160, 190), (250, 218, 230)]
SPORE = (190, 236, 220)
RING = [(110, 80, 52), (142, 108, 72), (176, 140, 96), (200, 168, 120)]


def _ellipse_mask(h, w, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:h, 0:w]
    return (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) < 1


def rock(seed, size=1.0):
    """A mossy boulder of flat facets (each its own tone by which way it faces), lit edges, a crack, moss on top."""
    rng = _rng(seed)
    W, H = int(40 * size), int(32 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    h, w = H, W
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, rx, ry = w / 2, h * 0.56, w * 0.45, h * 0.40
    ang = np.arctan2(yy - cy, xx - cx)
    lobes = 1 + 0.07 * np.sin(ang * 5 + rng.random() * 6) + 0.04 * np.sin(ang * 9 + rng.random() * 6)
    inside, d, shade = _ball(xx, yy, cx, cy, max(rx, 1), None)
    d = np.hypot((xx - cx) / rx, (yy - cy) / ry) / lobes
    inside = d < 1
    # facets: nearest of a few seed points; each facet takes the ball shade at its seed
    seeds = []
    for _ in range(int(5 + 3 * size)):
        a, rr = rng.random() * math.tau, math.sqrt(rng.random()) * 0.85
        seeds.append((cx + math.cos(a) * rx * rr, cy + math.sin(a) * ry * rr))
    dist = np.stack([np.hypot(xx - sx, yy - sy) for sx, sy in seeds])
    owner = dist.argmin(0)
    sorted_d = np.sort(dist, 0)
    edge = (sorted_d[1] - sorted_d[0]) < 0.9
    t = np.zeros((h, w))
    for k, (sx, sy) in enumerate(seeds):
        nx, ny = (sx - cx) / rx, (sy - cy) / ry
        nz = math.sqrt(max(0.0, 1 - min(1.0, nx * nx + ny * ny)))
        f = max(0.0, -0.55 * nx - 0.65 * ny + 0.55 * nz)
        t[owner == k] = 0.8 + f * 4.4
    up_left = np.roll(owner, 1, 0) != owner
    t = np.where(edge & up_left, t + 0.9, np.where(edge, t - 0.9, t))
    t = np.where(d > 0.9, t - 0.8, t)
    idx = np.clip(np.round(t).astype(int), 0, len(STONE) - 1)
    img[inside, :3] = np.array(STONE, dtype=np.uint8)[idx][inside]
    img[inside, 3] = 255
    # a crack
    px, py = cx + rx * 0.1, cy - ry * 0.3
    for k in range(int(8 * size)):
        px += rng.random() * 1.2 - 0.2
        py += 0.8
        ix, iy = int(px), int(py)
        if 0 <= ix < w and 0 <= iy < h and inside[iy, ix]:
            img[iy, ix, :3] = STONE[0]
            if ix - 1 >= 0 and inside[iy, ix - 1]:
                img[iy, ix - 1, :3] = STONE[4]
    # moss: a cap on the upper surface, ragged edge, drips down the lit side
    top_line = cy - ry * 0.2 + np.sin(xx * 0.6 + rng.random() * 6) * 1.6
    moss = inside & (yy < top_line) & (rng.random((h, w)) > 0.12)
    mt = shade * 3.4 + ((xx + yy) % 3 == 0) * 0.6
    midx = np.clip(np.round(mt).astype(int), 0, len(MOSS) - 1)
    img[moss, :3] = np.array(MOSS, dtype=np.uint8)[midx][moss]
    for _ in range(int(3 * size)):
        x = int(cx - rx * 0.6 + rng.random() * rx)
        ys = np.nonzero(moss[:, x])[0] if 0 <= x < w else []
        if len(ys):
            for k in range(1, 2 + int(rng.random() * 3)):
                y = ys.max() + k
                if y < h and inside[y, x]:
                    img[y, x, :3] = MOSS[1]
    _outline(img)
    _shadow(img, cx, h - 3, rx * 1.05, 3)
    return img


def stump(seed, size=1.0):
    """A cut stump: growth rings on top, a split, furrowed bark, roots, a little shelf fungus."""
    rng = _rng(seed)
    W, H = int(34 * size), int(30 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    cx = W // 2
    top = int(H * 0.32)
    rw = W * 0.27
    trunk(img, cx, top, H - 5, int(W * 0.54), seed)
    yy, xx = np.mgrid[0:H, 0:W]
    face = _ellipse_mask(H, W, cx, top + 1, rw, 3.2)
    dd = np.hypot((xx - cx) / rw, (yy - top - 1) / 3.2)
    ring_t = 3 - (np.floor(dd * 4) % 2) - (xx > cx + 1) * 1
    img[face, :3] = np.array(RING, dtype=np.uint8)[np.clip(ring_t, 0, 3).astype(int)][face]
    img[face, 3] = 255
    img[_ellipse_mask(H, W, cx, top + 1, 1.5, 0.9)] = RING[0] + (255,)
    for k in range(int(rw)):  # a split from the heart to the rim
        x = cx + 1 + k
        if face[top + 1, x]:
            img[top + 1, x] = (60, 40, 28, 255)
    fx, fy = int(cx + rw * 0.6), int(top + (H - top) * 0.45)  # shelf fungus on the shaded side
    for k in range(4):
        if fx + k < W:
            img[fy, fx + k] = (214, 170, 100, 255)
            img[fy + 1, fx + k] = (150, 110, 60, 255)
    _outline(img)
    _shadow(img, cx, H - 4, W * 0.44, 3)
    return img


def reeds(seed, cattails=True):
    """A clump of reeds with a couple of cattails; drawn blade by blade, back blades darker."""
    rng = _rng(seed)
    W, H = 24, 32
    img = np.zeros((H, W, 4), dtype=np.uint8)
    base = H - 2
    blades = []
    for k in range(10):
        blades.append((rng.random(), W / 2 + (rng.random() - 0.5) * 10, (rng.random() - 0.5) * 0.9,
                       int(12 + rng.random() * 16)))
    blades.sort()
    for i, (depth, x0, lean, length) in enumerate(blades):
        back = depth < 0.4
        for t in range(length):
            x = int(round(x0 + lean * t * (t / length)))
            y = base - t
            if not (0 <= x < W and 0 <= y < H):
                continue
            tone = 1 + (3.2 * t / length) - (1.2 if back else 0)
            img[y, x] = pal_at(REED, tone) + (255,)
            if t < length * 0.45 and x + 1 < W:  # blades are 2 px wide low down; the right half in shade
                img[y, x + 1] = pal_at(REED, tone - 1.2) + (255,)
        if cattails and i >= len(blades) - 2:
            tx = int(round(x0 + lean * length))
            for t in range(5):
                y = base - length - t
                if 0 <= tx < W - 1 and 0 <= y < H:
                    img[y, tx] = CATTAIL[2 if t in (2, 3) else 1] + (255,)
                    img[y, tx + 1] = CATTAIL[0] + (255,)
            y = base - length - 6
            if 0 <= tx < W and y >= 0:
                img[y, tx] = REED[3] + (255,)
    _outline(img)
    return img


def mushroom(seed, size=1.0):
    """A pale swamp mushroom: a domed cap shaded like a ball, gills under the rim, glowing spores, a ringed stem,
    and a small one at its foot."""
    rng = _rng(seed)
    W, H = int(46 * size), int(52 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    cx = W / 2
    stem_top, foot = int(H * 0.42), H - 5
    def stem(scx, s_top, s_foot, half0):
        for y in range(s_top, s_foot + 1):
            half = half0 + (y - s_top) * 0.06
            for x in range(int(scx - half), int(scx + half) + 1):
                if 0 <= x < W:
                    rel = (x - (scx - half)) / max(1, 2 * half)
                    img[y, x] = pal_at(STEM, 3.4 - abs(rel - 0.3) * 4.5) + (255,)
    stem(cx, stem_top, foot, W * 0.11)
    ring_y = stem_top + int((foot - stem_top) * 0.25)
    img[ring_y, int(cx - W * 0.13):int(cx + W * 0.13) + 1] = STEM[3] + (255,)
    img[ring_y + 1, int(cx - W * 0.12):int(cx + W * 0.12) + 1] = STEM[0] + (255,)
    h, w = H, W
    yy, xx = np.mgrid[0:h, 0:w]
    ccx, ccy, crx, cry = cx, H * 0.36, W * 0.47, H * 0.24
    capm = _ellipse_mask(h, w, ccx, ccy, crx, cry) & (yy < H * 0.46)
    nx, ny = (xx - ccx) / crx, (yy - ccy) / cry
    nz = np.sqrt(np.clip(1 - nx ** 2 - ny ** 2, 0, 1))
    shade = np.clip(-0.5 * nx - 0.7 * ny + 0.5 * nz, 0, 1)
    idx = np.clip(np.round(0.4 + shade * 4.2).astype(int), 0, len(CAP) - 1)
    img[capm, :3] = np.array(CAP, dtype=np.uint8)[idx][capm]
    img[capm, 3] = 255
    under = capm & (yy > H * 0.415)
    img[under, :3] = np.where(((xx[under] % 2) == 0)[:, None], GILL[0], GILL[1])
    for _ in range(int(7 * size) + 2):  # glowing spores
        sx, sy = int(ccx + (rng.random() - 0.5) * crx * 1.3), int(H * 0.18 + rng.random() * H * 0.18)
        if 0 <= sx < w - 1 and capm[sy, sx] and capm[sy, sx + 1]:
            img[sy, sx, :3] = SPORE
            if rng.random() < 0.5:
                img[sy, sx + 1, :3] = CAP[3]
    if size > 0.7:  # a small mushroom at its foot
        sx = int(cx + W * 0.28)
        stem(sx, foot - 6, foot, 1.2)
        small = _ellipse_mask(h, w, sx, foot - 6, 3.6, 2.2) & (yy <= foot - 6)
        img[small] = CAP[3] + (255,)
        img[small & (xx > sx)] = CAP[2] + (255,)
    _outline(img)
    _shadow(img, cx, H - 4, W * 0.32, 3)
    return img


def lilypad(seed, flower=False):
    """A ground decal for water: a pad with its notch and veins, sometimes a blossom."""
    W, H = 16, 10
    img = np.zeros((H, W, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    pad = _ellipse_mask(H, W, 8, 5, 6.5, 3.6)
    notch = (xx > 8) & (abs(yy - 5) <= (xx - 8) * 0.4)
    m = pad & ~notch
    img[m] = LILY[2] + (255,)
    img[m & (yy < 4)] = LILY[3] + (255,)
    img[m & (yy > 6)] = LILY[1] + (255,)
    img[m & ((xx - 8) == (yy - 5) * -2)] = LILY[1] + (255,)  # veins from the centre
    img[m & ((xx - 8) == (yy - 5) * 2) & (xx < 8)] = LILY[1] + (255,)
    img[5, 3:8] = LILY[1] + (255,)
    if flower:
        img[3:5, 6:9] = BLOSSOM[0] + (255,)
        img[3, 6:8] = BLOSSOM[1] + (255,)
        img[2, 7] = BLOSSOM[2] + (255,)
        img[4, 7] = (240, 210, 110, 255)
    _outline(img)
    return img


def log(seed, length=70):
    """A fallen, mossy log lying across the view: round bark ridges along it, knots, a ringed cut end, moss and fungi."""
    rng = _rng(seed)
    W, H = length, 24
    img = np.zeros((H, W, 4), dtype=np.uint8)
    ridge = rng.random((H, W))
    for x in range(3, W - 6):
        for y in range(6, 17):
            rel = (y - 6) / 10
            t = 4.0 - abs(rel - 0.25) * 4.4
            if (y + (x // 9)) % 3 == 0 and ridge[y, x] > 0.25:
                t -= 1.0  # bark ridges run along the log
            img[y, x] = pal_at(BARK, t) + (255,)
    for _ in range(max(1, length // 30)):  # knots
        kx = int(8 + rng.random() * (W - 20))
        img[10:13, kx:kx + 3] = BARK[1] + (255,)
        img[11, kx + 1] = BARK[0] + (255,)
        img[10, kx] = BARK[4] + (255,)
    for x in range(3, W - 6):  # moss along the top, in clumps
        if (math.sin(x * 0.35 + seed) + rng.random() * 0.6) > 0.2:
            img[6, x] = MOSS[2 + int(rng.random() * 2)] + (255,)
            img[5, x] = MOSS[1] + (255,) if rng.random() < 0.6 else img[5, x]
            if rng.random() < 0.3:
                img[7, x] = MOSS[1] + (255,)
    yy, xx = np.mgrid[0:H, 0:W]
    end = _ellipse_mask(H, W, W - 6, 11.5, 3.2, 5.6)
    dd = np.hypot((xx - (W - 6)) / 3.2, (yy - 11.5) / 5.6)
    img[end, :3] = np.array(RING, dtype=np.uint8)[np.clip(3 - (np.floor(dd * 3) % 2) - (yy > 13), 0, 3).astype(int)][end]
    img[end, 3] = 255
    fx = int(W * 0.3)  # shelf fungi on the side
    for k in range(5):
        img[15, fx + k] = (214, 170, 100, 255)
        img[16, fx + k] = (150, 110, 60, 255)
    _outline(img)
    _shadow(img, W / 2, 19, W * 0.5, 3)
    return img


# ------------------------------------------------------------------------------------------- shrine & market set
# Drawn with more care than the nature props: 5-6 tones per material, texture (grain, weave, mortar), contact shadow,
# and a coloured outline (a dark shade of the colour inside it) instead of flat black.

WOOD = [(42, 28, 20), (62, 42, 28), (86, 60, 38), (112, 82, 52), (140, 106, 70), (168, 134, 92)]
STONEW = [(44, 44, 50), (64, 64, 70), (88, 86, 88), (114, 110, 106), (140, 136, 126), (168, 162, 148)]
CANDLE = [(226, 214, 180), (255, 206, 110), (255, 244, 190)]
CLOTH_RED = [(84, 22, 26), (118, 34, 36), (156, 52, 46), (192, 76, 62), (220, 108, 84)]
CLOTH_WHITE = [(132, 124, 112), (170, 162, 148), (204, 196, 180), (228, 222, 208), (246, 242, 232)]
CLOTH_BLUE = [(26, 36, 72), (38, 54, 102), (54, 78, 136), (80, 108, 168), (118, 146, 196)]
CLOTH_PURPLE = [(48, 24, 62), (72, 36, 92), (100, 54, 124), (132, 80, 158), (168, 116, 188)]
IRON = [(34, 36, 42), (58, 62, 70), (92, 96, 104), (140, 146, 152)]
BURLAP = [(98, 80, 54), (128, 106, 74), (160, 136, 98), (190, 166, 124), (214, 194, 152)]
GLOW = (255, 214, 130)
PRODUCE = [(170, 50, 40), (220, 150, 40), (90, 140, 50), (200, 190, 80), (120, 70, 140)]


def pal_at(pal, t):
    return pal[max(0, min(len(pal) - 1, int(round(t))))]


def fine_outline(img):
    """Selective outline: each empty pixel touching the shape takes a dark shade of the colour beside it."""
    a = img[..., 3] > 0
    h, w = a.shape
    out = img.copy()
    for y in range(h):
        for x in range(w):
            if a[y, x]:
                continue
            for dx, dy, k in ((0, 1, 0.3), (1, 0, 0.3), (0, -1, 0.42), (-1, 0, 0.42)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and a[ny, nx]:
                    c = img[ny, nx]
                    out[y, x] = (int(c[0] * k), int(c[1] * k), min(255, int(c[2] * k) + 6), 255)
                    break
    return out


def contact_shadow(img, cx, cy, rx, ry, alpha=120):
    """A soft two-step shadow on the ground under a prop."""
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    d = ((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2
    for lim, a in ((1.0, alpha // 2), (0.55, alpha)):
        m = (d < lim) & ((img[..., 3] == 0) | (img[..., 3] < 255))
        img[m] = (10, 16, 10, a)
    return img


def wood_block(img, x0, y0, x1, y1, seed, vertical=False):
    """Planked wood: light top-left, grain streaks along the planks, dark gaps between them."""
    rng = _rng(seed)
    grain = rng.random((y1 - y0 + 1, x1 - x0 + 1))
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            u = (x - x0) / max(1, x1 - x0)
            v = (y - y0) / max(1, y1 - y0)
            t = 4.2 - u * 1.4 - v * 1.4
            across = (x - x0) if vertical else (y - y0)
            if across % 5 == 4:
                t -= 1.8  # gap between planks
            elif across % 5 == 0:
                t += 0.5  # lit plank edge
            g = grain[y - y0, x - x0]
            if g > 0.88:
                t += 0.8
            elif g < 0.1:
                t -= 0.8
            img[y, x] = pal_at(WOOD, t) + (255,)


def _flames(img, spots, frame):
    r2 = _rng(300 + frame)
    for cx, base in spots:
        tall = 3 + (cx % 3)
        img[base - tall:base, cx] = CANDLE[0] + (255,)
        img[base - tall:base, cx + 1] = (196, 184, 150, 255)
        fy = base - tall - 2 - int(r2.random() * 2)
        img[fy, cx] = CANDLE[1] + (255,)
        img[fy + 1, cx] = CANDLE[2] + (255,)
        img[fy + 1, cx + 1] = CANDLE[1] + (255,)


def _warm(img, cx, cy, r, k=1.0):
    """Warm the lit pixels around a light source."""
    h, w = img.shape[:2]
    for y in range(max(0, cy - r), min(h, cy + r + 1)):
        for x in range(max(0, cx - r), min(w, cx + r + 1)):
            d = math.hypot(x - cx, y - cy) / r
            if d < 1 and img[y, x, 3] == 255:
                f = (1 - d) * k
                c = img[y, x]
                img[y, x, :3] = (min(255, int(c[0] * (1 + 0.35 * f) + 18 * f)), min(255, int(c[1] * (1 + 0.18 * f) + 8 * f)), c[2])


def shrine(frame=0):
    """Saint Ivel's roadside shrine: a mossy stone niche on a stepped plinth, a pale saint, candles that flicker."""
    W, H = 56, 74
    img = np.zeros((H, W, 4), dtype=np.uint8)
    rng = _rng(90)

    def stone(x0, y0, x1, y1, course=5):
        for y in range(y0, y1 + 1):
            row = (y - y0) // course
            for x in range(x0, x1 + 1):
                off = (row % 2) * 5
                t = 4.4 - (x - x0) / max(1, x1 - x0) * 2.0 - (y - y0) / max(1, y1 - y0) * 0.8
                if (y - y0) % course == course - 1 or (x - x0 + off) % 10 == 0:
                    t = 1.0  # mortar
                elif (y - y0) % course == 0:
                    t += 0.6  # each block's lit top
                elif rng.random() < 0.12:
                    t -= 0.8
                img[y, x] = pal_at(STONEW, t) + (255,)

    stone(8, 62, 47, 69, 4)    # bottom step
    stone(12, 55, 43, 62, 4)   # plinth
    stone(15, 22, 40, 55)      # niche body
    for y in range(11, 23):    # arched cap
        half = int(13.5 * math.sqrt(max(0.0, 1 - ((y - 22) / 11.5) ** 2)))
        for x in range(28 - half, 28 + half):
            t = 4.8 - (x - (28 - half)) / max(1, 2 * half) * 2.6
            img[y, x] = pal_at(STONEW, t) + (255,)
    img[8:12, 27:29] = STONEW[4] + (255,)  # finial
    img[8, 27] = STONEW[5] + (255,)
    for y in range(26, 54):     # the niche: deep shadow, lighter at the top lip
        for x in range(20, 36):
            img[y, x] = (22, 20, 26, 255) if y > 28 else (40, 36, 42, 255)
    for y in range(31, 53):     # the saint: a robed figure, lit from the left
        half = 2 + (y - 31) // 5
        for x in range(28 - half, 28 + half):
            u = (x - (28 - half)) / max(1, 2 * half - 1)
            img[y, x] = pal_at(CLOTH_WHITE, 4.3 - u * 3.2) + (255,)
        if y % 4 == 0:  # robe folds
            img[y, 28] = CLOTH_WHITE[1] + (255,)
    for y in range(27, 31):  # head and hood
        for x in range(26, 30):
            img[y, x] = pal_at(CLOTH_WHITE, 4 - (x - 26) * 0.9) + (255,)
    img[37:39, 26:30] = CLOTH_WHITE[1] + (255,)  # folded hands
    img[37, 26:28] = CLOTH_WHITE[3] + (255,)
    for x in range(14, 42):     # moss on the cap, the ledge and the step
        if img[22, x, 3] and rng.random() < 0.6:
            img[22, x] = MOSS[int(rng.random() * 3)] + (255,)
            if rng.random() < 0.4:
                img[23, x] = MOSS[0] + (255,)
        if img[55, x, 3] and rng.random() < 0.4:
            img[55, x] = MOSS[int(rng.random() * 2)] + (255,)
    for x in range(8, 48):
        if rng.random() < 0.25:
            img[62, x] = MOSS[int(rng.random() * 3)] + (255,)
    spots = ((10, 62), (14, 62), (40, 62), (44, 62), (17, 55), (37, 55))
    for cx, base in spots:
        _warm(img, cx, base - 6, 6, 0.9)
    _flames(img, spots, frame)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 71, 25, 3.0)


def shrine_frames():
    return [shrine(f) for f in range(3)]


def barrel(seed):
    """An oak barrel: curved staves lit from the left, two iron hoops with a glint, a lid of boards."""
    W, H = 24, 30
    img = np.zeros((H, W, 4), dtype=np.uint8)
    rng = _rng(seed)
    for y in range(6, 27):
        bulge = 1 if 10 < y < 22 else 0
        x0, x1 = 3 - bulge, 20 + bulge
        for x in range(x0, x1 + 1):
            u = (x - x0) / (x1 - x0)
            t = 5.0 - abs(u - 0.3) * 5.5  # round: brightest a third of the way in
            if (x - x0) % 4 == 3:
                t -= 1.2  # stave joints
            if rng.random() < 0.12:
                t -= 0.6
            img[y, x] = pal_at(WOOD, t) + (255,)
        if y in (9, 10, 21, 22):
            for x in range(x0, x1 + 1):
                u = (x - x0) / (x1 - x0)
                img[y, x] = pal_at(IRON, 3.2 - abs(u - 0.3) * 4.5 - (0 if y in (9, 21) else 1)) + (255,)
    yy, xx = np.mgrid[0:H, 0:W]
    lid = _ellipse_mask(H, W, 11.5, 6, 8.5, 2.8)
    rim = _ellipse_mask(H, W, 11.5, 6, 9.5, 3.4) & ~lid
    img[rim] = WOOD[2] + (255,)
    img[lid] = WOOD[4] + (255,)
    img[lid & ((xx - 3) % 4 == 0)] = WOOD[3] + (255,)
    img[lid & (yy > 7)] = WOOD[3] + (255,)
    img[lid & (yy < 5) & (xx < 10)] = WOOD[5] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, 11.5, 28, 11, 2.0)


def crates(seed):
    """Stacked crates: planked faces, cross braces, corner frames, nail heads, a shadow under the top one."""
    W, H = 38, 34
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for (x0, y0, x1, y1), sd in (((2, 14, 18, 30), seed), ((18, 16, 35, 30), seed + 1), ((9, 3, 25, 15), seed + 2)):
        wood_block(img, x0, y0, x1, y1, sd)
        n = max(x1 - x0, y1 - y0)
        for i in range(n + 1):  # a diagonal brace
            x = x0 + 1 + int(i * (x1 - x0 - 2) / n)
            y = y1 - 1 - int(i * (y1 - y0 - 2) / n)
            img[y, x] = WOOD[4] + (255,)
            if y + 1 <= y1:
                img[y + 1, x] = WOOD[1] + (255,)
        for x in range(x0, x1 + 1):
            img[y0, x] = WOOD[5] + (255,)
            img[y0 + 1, x] = WOOD[4] + (255,)
            img[y1, x] = WOOD[1] + (255,)
        for y in range(y0, y1 + 1):
            img[y, x0] = WOOD[4] + (255,)
            img[y, x1] = WOOD[1] + (255,)
            img[y, x1 - 1] = WOOD[2] + (255,)
        for nx, ny in ((x0 + 1, y0 + 2), (x1 - 2, y0 + 2), (x0 + 1, y1 - 1), (x1 - 2, y1 - 1)):
            img[ny, nx] = IRON[3] + (255,)
    img[16, 10:25] = WOOD[0] + (255,)  # shadow under the top crate
    out = fine_outline(img)
    return contact_shadow(out, 18, 31, 18, 2.5)


def sacks(seed):
    """Grain sacks: round, lit top-left, tied necks, coarse weave, one spilling grain."""
    W, H = 34, 26
    img = np.zeros((H, W, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    for cx, cy, r in ((10, 17, 7.5), (23, 17, 7.5), (17, 11, 6.5)):
        m = _ellipse_mask(H, W, cx, cy, r, r * 0.85)
        lit = 1 - np.clip(np.hypot(xx - (cx - r * 0.4), yy - (cy - r * 0.5)) / (r * 1.6), 0, 1)
        t = lit * 4.4 + ((xx + yy) % 2) * 0.35 - ((xx * 3 + yy) % 7 == 0) * 0.8
        img[m] = np.array([pal_at(BURLAP, v) + (255,) for v in t[m]], dtype=np.uint8)
        ny = int(cy - r * 0.85)
        img[ny - 2:ny + 1, cx - 1:cx + 2] = BURLAP[2] + (255,)
        img[ny - 2, cx - 1] = BURLAP[3] + (255,)
        img[ny, cx - 2:cx + 3] = (70, 52, 34, 255)  # tie
    for i, (x, y) in enumerate(((30, 22), (31, 23), (29, 23), (32, 22), (28, 24))):  # spilled grain
        img[y, x] = (222, 196, 120, 255) if i % 2 else (190, 160, 90, 255)
    out = fine_outline(img)
    return contact_shadow(out, 17, 23, 16, 2.5)


def stall(seed, cloth=CLOTH_RED):
    """A market stall: a striped awning with folds and a scalloped hem over a planked counter heaped with goods."""
    rng = _rng(seed)
    W, H = 78, 70
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for x in (7, 69):  # poles, round: light left edge
        for y in range(16, 66):
            img[y, x] = WOOD[4] + (255,)
            img[y, x + 1] = WOOD[2] + (255,)
    wood_block(img, 7, 46, 70, 64, seed, vertical=True)  # counter front
    for x in range(7, 71):
        img[44, x] = WOOD[5] + (255,)  # counter top
        img[45, x] = WOOD[4] + (255,)
        img[46, x] = WOOD[1] + (255,)
    for bx0 in (10, 30, 50):  # three baskets on the counter
        for y in range(39, 44):
            for x in range(bx0, bx0 + 17):
                u = (x - bx0) / 16
                t = 3.6 - u * 1.6 - (y - 39) * 0.15 + (0.5 if (x + y) % 3 == 0 else 0)
                img[y, x] = pal_at(BURLAP, t) + (255,)
    for i in range(46):  # goods heaped in the baskets, each piece round and lit
        b = i % 3
        cx = 12 + b * 20 + int(rng.random() * 13)
        cy = 36 + int(rng.random() * 4)
        base = PRODUCE[(b * 2 + int(rng.random() * 2)) % len(PRODUCE)]
        for dy in range(-1, 2):
            for dx in range(-1, 2):
                if abs(dx) + abs(dy) < 2 or rng.random() < 0.5:
                    k = 1.25 if dx + dy < 0 else 0.75 if dx + dy > 0 else 1.0
                    img[cy + dy, cx + dx] = tuple(min(255, int(v * k)) for v in base) + (255,)
        img[cy - 1, cx - 1] = tuple(min(255, v + 80) for v in base) + (255,)
    # awning: stripes, cloth folds (shading across each stripe), a hem of scallops
    for y in range(5, 27):
        for x in range(2, 76):
            stripe = (x - 2) // 8
            pal = cloth if stripe % 2 else CLOTH_WHITE
            fold = math.cos(((x - 2) % 8) / 8 * math.tau) * 0.7
            scallop_y = 22 + int(round(3 * math.sin(((x - 2) % 8 + 0.5) / 8 * math.pi)))
            if y > scallop_y:
                continue
            t = 3.8 - (y - 5) * 0.08 + fold
            if y <= 6:
                t += 1.0  # lit ridge
            elif y == 7:
                t -= 1.2  # seam under the ridge
            elif y >= scallop_y - 1:
                t -= 0.8  # the hem turns away from the light
            img[y, x] = pal_at(pal, t) + (255,)
    for x in range(2, 76):  # the awning's shadow on the poles and goods
        sy = 22 + int(round(3 * math.sin(((x - 2) % 8 + 0.5) / 8 * math.pi))) + 1
        for y in (sy, sy + 1):
            if y < H and img[y, x, 3]:
                c = img[y, x]
                img[y, x, :3] = (int(c[0] * 0.6), int(c[1] * 0.6), int(c[2] * 0.62))
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 66, 36, 3.5)


def tent(seed):
    """A peaked merchant's tent: lit and shaded canvas faces with seams and sag, an open door glowing inside."""
    W, H = 76, 76
    img = np.zeros((H, W, 4), dtype=np.uint8)
    rng = _rng(seed)
    apex, base = 8, 66
    for y in range(apex, base + 1):
        half = int((y - apex) * 0.62) + 2
        for x in range(38 - half, 38 + half):
            left = x < 38
            u = abs(x - 38) / max(1, half)
            t = (4.0 if left else 2.2) - u * 0.9 + math.sin(u * 9) * 0.35
            if abs(x - 38) % 9 == 0 and x != 38:
                t -= 1.0  # seams
            if y > base - 3:
                t -= 0.6  # hem
            if rng.random() < 0.05:
                t -= 0.5
            img[y, x] = pal_at(CLOTH_PURPLE, t) + (255,)
        if left:
            pass
    for x in range(38 - 39, 38 + 39):  # gold trim along the hem
        if 0 <= x < W and img[base - 1, x, 3]:
            img[base - 1, x] = (214, 182, 90, 255) if x % 4 else (160, 128, 60, 255)
    for y in range(38, base + 1):  # open doorway, warm inside
        half = int((y - 38) * 0.38) + 3
        for x in range(38 - half, 38 + half):
            img[y, x] = (40, 24, 34, 255) if x < 38 else (30, 18, 28, 255)
        img[y, 38 - half] = CLOTH_PURPLE[4] + (255,)  # the tied-back flap's lit edge
    for y in range(52, base):
        for x in range(32, 45):
            d = math.hypot(x - 38, y - 58) / 8
            if d < 1 and img[y, x, 3]:
                c = img[y, x]
                img[y, x, :3] = (min(255, int(c[0] + 120 * (1 - d))), min(255, int(c[1] + 70 * (1 - d))), c[2])
    img[56:60, 36:40] = GLOW + (255,)
    img[57:59, 37:39] = (255, 240, 190, 255)
    for y in range(apex - 6, apex + 1):  # pole tip and pennant
        img[y, 37] = WOOD[4] + (255,)
        img[y, 38] = WOOD[2] + (255,)
    for i in range(6):
        img[apex - 6 + i // 2, 39 + i] = CLOTH_RED[3] + (255,)
        img[apex - 5 + i // 2, 39 + i] = CLOTH_RED[2] + (255,)
    for k in range(18):  # guy rope to a peg
        x, y = 56 + k // 2, 34 + int(k * 1.7)
        if x < W and y < H:
            img[y, x] = (150, 130, 96, 255)
    img[64:67, 64:66] = WOOD[3] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, 38, 67, 34, 3.5)


def banner(frame=0):
    """A pole with a long pennant rippling in the wind (4 frames)."""
    W, H = 26, 62
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(6, 60):
        img[y, 4] = WOOD[4] + (255,)
        img[y, 5] = WOOD[2] + (255,)
    img[2:6, 3:7] = (214, 182, 90, 255)
    img[2:4, 3] = (250, 226, 140, 255)
    img[5, 3:7] = (150, 120, 56, 255)
    for x in range(6, 24):
        ph = (x / 4.0) - frame * math.pi / 2
        wave = 1.6 * math.sin(ph)
        top = 9 + int(round(wave))
        bottom = 30 + int(round(wave)) - (x - 6) // 2
        for y in range(top, bottom):
            shade = 3.2 + math.cos(ph) * 1.1 - (y - top) * 0.06
            if y == top:
                shade += 0.6
            img[y, x] = pal_at(CLOTH_BLUE, shade) + (255,)
        if bottom - top > 4:  # a gold emblem stripe
            g = 1.0 + math.cos(ph) * 0.2
            img[top + (bottom - top) // 2, x] = (min(255, int(196 * g)), min(255, int(160 * g)), 70, 255)
    out = fine_outline(img)
    return contact_shadow(out, 5, 60, 4, 1.5)


def banner_frames():
    return [banner(f) for f in range(4)]


def lantern_post(frame=0):
    """A post with a hanging iron lantern; the flame flickers and warms the post."""
    W, H = 20, 58
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(10, 56):
        img[y, 9] = WOOD[4] + (255,)
        img[y, 10] = WOOD[2] + (255,)
    img[10:12, 4:16] = WOOD[3] + (255,)
    img[10, 4:16] = WOOD[5] + (255,)
    img[12, 5:15] = IRON[2] + (255,)  # cap
    img[13, 6:14] = IRON[1] + (255,)
    flick = [0, 1, 0, 2][frame % 4]
    for y in range(14, 22):
        for x in range(6, 14):
            if x in (6, 13) or y == 21:
                img[y, x] = IRON[1] + (255,)  # frame
                continue
            d = abs(x - 9.5) + abs(y - 17.5)
            c = (255, 244, 200) if d < 2 else GLOW if d < 4 else (220, 160, 80)
            img[y, x] = tuple(min(255, v + flick * 6) for v in c) + (255,)
    img[22, 8:12] = IRON[2] + (255,)
    _warm(img, 10, 18, 9, 0.6 + flick * 0.1)
    out = fine_outline(img)
    return contact_shadow(out, 10, 56, 6, 2)


def lantern_frames():
    return [lantern_post(f) for f in range(4)]


# ------------------------------------------------------------------------------------------- Halden's Ford bazaar
# The market square's own pieces (after the user's market reference sheets, drawn fresh): draped canopies on
# ribboned poles, forked-branch produce stalls, crates of produce, a weapon rack, armour stand, forked banners,
# a covered wagon, a bakery table, pottery and a fortune-teller's tent.

STEEL = [(36, 44, 66), (58, 72, 100), (92, 110, 142), (138, 156, 186), (200, 214, 232)]
GOLD = [(104, 64, 28), (164, 110, 38), (216, 164, 56), (250, 216, 116)]
CLOTH_GREEN = [(30, 42, 22), (46, 62, 30), (68, 86, 38), (94, 112, 50), (126, 142, 68)]
CLOTH_GREY = [(86, 88, 104), (118, 120, 136), (152, 154, 170), (190, 192, 204), (226, 228, 236)]
LINEN = [(150, 140, 124), (190, 182, 164), (222, 216, 200), (242, 238, 226)]
CLAY = [(70, 40, 34), (104, 62, 46), (140, 90, 62), (176, 124, 86)]
CREAM = [(150, 136, 112), (196, 184, 158), (228, 220, 198), (248, 244, 230)]
FRUIT = {  # palette dark -> light, radius px, extra look
    "watermelon": ([(22, 50, 26), (38, 82, 36), (62, 120, 48), (110, 160, 74)], 5.5, "stripes"),
    "melon": ([(150, 104, 24), (204, 150, 34), (238, 198, 64), (252, 236, 140)], 4.5, None),
    "pumpkin": ([(130, 52, 18), (186, 86, 26), (226, 126, 40), (250, 176, 84)], 4.5, "ribs"),
    "tomato": ([(110, 20, 22), (170, 36, 32), (214, 64, 48), (250, 140, 110)], 2.4, None),
    "apple": ([(100, 22, 26), (156, 38, 40), (200, 70, 56), (240, 150, 120)], 2.0, None),
    "grape": ([(44, 22, 56), (72, 38, 96), (104, 62, 136), (156, 116, 186)], 1.4, None),
    "cabbage": ([(36, 70, 30), (62, 110, 44), (100, 150, 62), (160, 196, 104)], 3.0, "leafy"),
    "orange": ([(150, 70, 20), (210, 112, 30), (240, 156, 50), (252, 210, 120)], 2.0, None),
    "grain": ([(120, 92, 48), (170, 136, 74), (210, 180, 108), (236, 216, 150)], 0.9, None),
}


def _put(img, x, y, c):
    h, w = img.shape[:2]
    x, y = int(x), int(y)
    if 0 <= x < w and 0 <= y < h:
        img[y, x] = tuple(c[:3]) + (255,)


def _ballpix(img, cx, cy, r, pal, look=None):
    """A small round thing shaded like a ball lit from the upper left."""
    for y in range(int(cy - r - 1), int(cy + r + 2)):
        for x in range(int(cx - r - 1), int(cx + r + 2)):
            dx, dy = (x + 0.5 - cx) / r, (y + 0.5 - cy) / (r * 0.9)
            d2 = dx * dx + dy * dy
            if d2 >= 1:
                continue
            nz = math.sqrt(1 - d2)
            t = 0.4 + max(0.0, -0.55 * dx - 0.6 * dy + 0.6 * nz) * 3.2
            if look == "stripes" and math.sin(dx * 7.5) > 0.35:
                t -= 1.3
            if look == "ribs" and abs(math.sin(dx * 4.7)) < 0.25:
                t -= 1.0
            if look == "leafy" and (x + 2 * y) % 4 == 0:
                t += 0.8
            _put(img, x, y, pal_at(pal, t))
    if look == "ribs":
        _put(img, cx, cy - r * 0.9, (70, 90, 36))
        _put(img, cx + 1, cy - r * 0.9 - 1, (70, 90, 36))


def heap(img, x0, x1, top, kind, rng, rows=2):
    """Fill a bin from x0 to x1 with produce heaped above `top` (back row first)."""
    pal, r, look = FRUIT[kind]
    step = max(1.6, r * 1.5)
    for row in range(rows):
        y = top - (rows - 1 - row) * r * 0.9
        x = x0 + r * (0.8 if row % 2 else 1.3)
        while x <= x1 - r * 0.6:
            _ballpix(img, x + rng.random() * 0.8, y + rng.random() * 0.8, r * (0.9 + rng.random() * 0.2), pal, look)
            x += step


def box(img, x0, y0, x1, y1, seed, inner=True):
    """A wooden bin seen from the front and a little above: a dark inside lip, planked front, lit top edge."""
    wood_block(img, x0, y0, x1, y1, seed)
    for x in range(x0, x1 + 1):
        _put(img, x, y0, WOOD[5])
        _put(img, x, y1, WOOD[0])
        if inner:
            _put(img, x, y0 - 1, WOOD[1])
    for y in range(y0, y1 + 1):
        _put(img, x0, y, WOOD[4])
        _put(img, x1, y, WOOD[1])


def branch_pole(img, x, top, bottom, side=1, fork=True):
    """A rough branch used as a pole: knobbly, lit on the left, with a forked twig near the top."""
    for y in range(top, bottom + 1):
        wob = 1 if (y // 7) % 2 else 0
        _put(img, x + wob, y, WOOD[4])
        _put(img, x + 1 + wob, y, WOOD[2])
        _put(img, x + 2 + wob, y, WOOD[1])
    if fork:
        for k in range(8):
            _put(img, x + 1 + side * (2 + k // 2 + k // 3), top + 8 - k, WOOD[3])
            _put(img, x + 1 + side * (2 + k // 2 + k // 3), top + 9 - k, WOOD[1])
        _put(img, x + 1, top - 1, WOOD[3])


def jar(img, cx, foot, h, pal=CLAY, tied=True):
    """A clay jar: round belly, narrow neck, a cloth tied over the mouth."""
    belly = h * 0.36
    for y in range(int(foot - h), foot + 1):
        v = (y - (foot - h)) / h
        if v < 0.25:
            half = belly * 0.45
        else:
            half = belly * math.sqrt(max(0.0, 1 - ((v - 0.62) / 0.4) ** 2)) + 0.5
        for x in range(int(cx - half), int(cx + half) + 1):
            u = (x - (cx - half)) / max(1, 2 * half)
            _put(img, x, y, pal_at(pal, 3.4 - abs(u - 0.3) * 4.5))
    if tied:
        for x in range(int(cx - belly * 0.6), int(cx + belly * 0.6) + 1):
            _put(img, x, foot - h, CREAM[3] if x < cx else CREAM[1])
            _put(img, x, foot - h - 1, CREAM[2])
        _put(img, cx, foot - h + 2, (120, 70, 40))


def produce_stall(seed):
    """A greengrocer's stall: forked-branch poles, a long counter of five bins heaped with produce, a jar and a small
    cask on the back shelf, garlic hanging from the pole."""
    rng = _rng(seed)
    W, H = 100, 70
    img = np.zeros((H, W, 4), dtype=np.uint8)
    branch_pole(img, 4, 4, 64, -1)
    branch_pole(img, 92, 4, 64, 1)
    # back shelf: a jar and a little cask
    jar(img, 26, 34, 12, CREAM)
    for y in range(24, 35):
        for x in range(68, 79):
            u = (x - 68) / 10
            t = 4.6 - abs(u - 0.3) * 5.5 - (1.2 if (x - 68) % 3 == 2 else 0)
            img[y, x] = pal_at(WOOD, t) + (255,)
    for x in range(68, 79):
        img[27, x] = IRON[2] + (255,)
        img[31, x] = IRON[1] + (255,)
    # the counter: five bins, then a skirt of planks to the ground
    kinds = ["apple", "cabbage", "tomato", "grain", "orange"]
    rng.shuffle(kinds)
    for i, kind in enumerate(kinds):
        x0 = 9 + i * 17
        box(img, x0, 40, x0 + 16, 48, seed + i)
        heap(img, x0 + 1, x0 + 15, 40, kind, rng, rows=3 if FRUIT[kind][1] < 2.5 else 2)
    wood_block(img, 8, 49, 93, 62, seed + 9, vertical=True)
    for x in range(8, 94):
        img[49, x] = WOOD[1] + (255,)
        img[62, x] = WOOD[0] + (255,)
    for y, x in ((14, 1), (18, 0), (22, 1)):  # garlic hanging from the left pole
        img[y - 3:y, x + 2] = (150, 120, 70, 255)
        for dx in range(3):
            img[y:y + 3, x + dx] = (CREAM[3] if dx == 0 else CREAM[2] if dx == 1 else CREAM[1]) + (255,)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 64, 46, 4)


def produce_crates(seed):
    """A row of crates in front of a stall: watermelons, melons, pumpkins, tomatoes and grapes, a jar beside them."""
    rng = _rng(seed)
    W, H = 112, 46
    img = np.zeros((H, W, 4), dtype=np.uint8)
    spec = [("watermelon", 6, 28, 22), ("melon", 30, 52, 24), ("pumpkin", 54, 76, 22), ("tomato", 78, 96, 24)]
    for k, (kind, x0, x1, top) in enumerate(spec):
        heap(img, x0 + 1, x1 - 1, top, kind, rng, rows=2)
        box(img, x0, top + 2, x1, 40, seed + k)
        for x in range(x0 + 2, x1 - 1, 5):  # slats
            img[top + 3:40, x] = WOOD[2] + (255,)
    heap(img, 97, 108, 22, "grape", rng, rows=4)
    box(img, 96, 24, 109, 40, seed + 7)
    jar(img, 3, 40, 12, CREAM)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 41, 54, 3.5)


def canopy_tent(seed, cloth=CLOTH_BLUE, frame=0):
    """A market canopy: striped cloth slung between four ribboned poles, sagging between them, its loose corners
    lifting in the wind (4 frames); a counter with a red cloth and a display sword underneath."""
    rng = _rng(seed)
    W, H = 116, 104
    img = np.zeros((H, W, 4), dtype=np.uint8)
    # a counter under the canopy, standing on the ground, hung with a red cloth; a display sword on top
    for y in range(64, 70):
        for x in range(30, 88):
            img[y, x] = pal_at(WOOD, 4.2 - (y - 64) * 0.3 - (1.2 if (x - 30) % 9 == 8 else 0)) + (255,)
    wood_block(img, 30, 70, 87, 96, seed, vertical=True)
    for y in range(70, 92):
        for x in range(38, 80):
            u = (x - 38) / 41
            img[y, x] = pal_at(CLOTH_RED, 3.4 - u * 1.4 - (0.8 if y > 88 and x % 3 == 0 else 0)) + (255,)
        img[y, 38] = GOLD[2] + (255,)
        img[y, 79] = GOLD[1] + (255,)
    for x in range(40, 78):
        img[66, x] = (STEEL[4] if x < 66 else GOLD[2]) + (255,)
        img[67, x] = (STEEL[2] if x < 66 else GOLD[1]) + (255,)
    img[64:69, 66] = GOLD[2] + (255,)
    img[65:68, 76] = GOLD[3] + (255,)
    for x in (44, 62):  # goods on the cloth: a shield emblem and a helm
        img[76:84, x:x + 8] = STEEL[2] + (255,)
        img[76:84, x:x + 3] = STEEL[3] + (255,)
        img[79, x:x + 8] = CLOTH_WHITE[3] + (255,)
    poles = [(12, 8, 80), (102, 8, 80), (20, 44, 100), (94, 44, 100)]  # x, top, foot (back pair then front pair)
    for x, top, foot in poles[:2]:
        for y in range(top, foot):
            img[y, x] = WOOD[3] + (255,)
            img[y, x + 1] = WOOD[1] + (255,)
    # the cloth: back edge from the back pole tops, front edge from the front pole tops, both sagging
    lift = [0, 1, 2, 1][frame % 4]
    for x in range(6, 110):
        u = (x - 6) / 103
        y_top = 10 + 7 * math.sin(math.pi * u) - (lift if u < 0.06 or u > 0.94 else 0)
        y_bot = 40 + 10 * math.sin(math.pi * u) + 2 * math.sin(u * 6 * math.pi) * (1 - abs(u - 0.5) * 2)
        for y in range(int(y_top), int(y_bot) + 1):
            v = (y - y_top) / max(1, y_bot - y_top)
            band = int(v * 5 + 0.6 * math.sin(u * 9 + 1))
            pal = cloth if band % 2 == 0 else CLOTH_WHITE
            sag = math.sin(math.pi * u)
            t = 3.6 - v * 1.2 + (0.5 - abs(u - 0.5)) * 0.8 - (0.9 if 0.4 < u < 0.6 and v > 0.5 else 0)
            t += 0.6 * math.cos(u * 6 * math.pi) * sag  # folds between the poles
            img[y, x] = pal_at(pal, t) + (255,)
        for k in range(1, 4):  # the front edge hangs over: a darker valance with a torn hem
            y = int(y_bot) + k
            if k < 3 or (x // 3) % 2:
                pal = cloth if (x // 6) % 2 else CLOTH_WHITE
                img[y, x] = pal_at(pal, 1.6 - k * 0.4) + (255,)
    for x, top, foot in poles[2:]:  # front poles drawn over the cloth
        for y in range(top, foot):
            img[y, x] = WOOD[4] + (255,)
            img[y, x + 1] = WOOD[2] + (255,)
    for x, top, foot in poles:  # gold finials and red ribbons
        tip = top - 2
        img[tip - 3:tip, x] = GOLD[3] + (255,)
        img[tip - 3:tip, x + 1] = GOLD[1] + (255,)
        img[tip - 5, x] = GOLD[2] + (255,)
        for k in range(6):
            sway = [0, 1, 1, 0][(frame + k // 2) % 4]
            img[tip + 1 + k, x + 2 + sway] = CLOTH_RED[3 if k < 3 else 2] + (255,)
            img[tip + 1 + k, x + 3 + sway] = CLOTH_RED[1] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 100, 52, 4)


def canopy_frames(seed, cloth=CLOTH_BLUE):
    return [canopy_tent(seed, cloth, f) for f in range(4)]


def weapon_rack(seed):
    """A smith's rack: two posts and rails, a sword, spear, axe and halberd leaning on it, a shield at the end and a
    helm on a post."""
    W, H = 76, 52
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for x in (6, 64):
        for y in range(18, 48):
            img[y, x:x + 4] = [WOOD[4] + (255,), WOOD[3] + (255,), WOOD[2] + (255,), WOOD[1] + (255,)]
        img[16:18, x:x + 4] = WOOD[5] + (255,)
    for y, t in ((24, 4), (25, 2), (40, 4), (41, 2)):
        img[y, 6:68] = WOOD[t] + (255,)

    def shaft(x, top, foot, tip):
        for y in range(top, foot):
            img[y, x] = WOOD[4] + (255,)
            img[y, x + 1] = WOOD[2] + (255,)
        tip(x, top)

    def blade(x, top):  # sword
        for y in range(top, top + 22):
            img[y, x] = STEEL[4] + (255,)
            img[y, x + 1] = STEEL[2] + (255,)
        img[top + 22, x - 2:x + 4] = GOLD[2] + (255,)
        img[top + 23:top + 28, x:x + 2] = (90, 50, 30, 255)
        img[top + 28, x:x + 2] = GOLD[3] + (255,)

    def spear(x, top):
        for k in range(6):
            w = 2 - abs(k - 3) // 2
            img[top - 6 + k, x - w + 1:x + w + 1] = (STEEL[4] if k < 3 else STEEL[2]) + (255,)
        img[top, x - 1:x + 3] = (180, 40, 40, 255)

    def axe(x, top):
        for k in range(8):
            img[top + k, x + 2:x + 2 + 6 - abs(k - 4)] = (STEEL[3] if k < 4 else STEEL[1]) + (255,)
        img[top + 1:top + 7, x + 7 - 2] = STEEL[4] + (255,)

    def halberd(x, top):
        spear(x, top)
        for k in range(6):
            img[top + 2 + k, x - 5 + k // 2:x] = (STEEL[2] if k > 2 else STEEL[3]) + (255,)

    blade(14, 14)
    shaft(24, 10, 46, spear)
    shaft(34, 18, 46, axe)
    blade(46, 16)
    shaft(54, 8, 46, halberd)
    yy, xx = np.mgrid[0:H, 0:W]  # shield
    sh = ((xx - 70) ** 2 / 36 + (yy - 36) ** 2 / 64 < 1) & (yy < 44 - abs(xx - 70) * 0.8)
    img[sh] = STEEL[2] + (255,)
    img[sh & (xx < 70)] = STEEL[3] + (255,)
    img[sh & (abs(xx - 70) < 1.5)] = CLOTH_RED[3] + (255,)
    img[sh & (abs(yy - 34) < 1.5)] = CLOTH_RED[3] + (255,)
    for y in range(9, 16):  # helm on the left post
        for x in range(4, 12):
            if (x - 8) ** 2 / 16 + (y - 14) ** 2 / 25 < 1:
                img[y, x] = pal_at(STEEL, 4 - (x - 4) * 0.45) + (255,)
    img[13, 6:11] = STEEL[0] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 48, 36, 3)


def armour_stand(seed):
    """A breastplate and horned helm on a wooden stand."""
    W, H = 26, 52
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(18, 48):
        img[y, 12] = WOOD[4] + (255,)
        img[y, 13] = WOOD[2] + (255,)
    img[46:48, 7:19] = WOOD[3] + (255,)
    for y in range(18, 36):  # breastplate
        half = 8 - max(0, y - 28) // 2
        for x in range(13 - half, 13 + half):
            u = (x - (13 - half)) / max(1, 2 * half)
            t = 4.4 - abs(u - 0.32) * 6
            if y == 26:
                t -= 1.4
            img[y, x] = pal_at(STEEL, t) + (255,)
    for x in (4, 20):  # pauldrons
        for y in range(17, 22):
            for dx in range(4):
                img[y, x + dx - (1 if x > 10 else 0)] = pal_at(STEEL, 3.6 - dx * 0.6 - (y - 17) * 0.3) + (255,)
    for y in range(6, 17):  # helm
        for x in range(8, 18):
            if (x - 13) ** 2 / 25 + (y - 13) ** 2 / 49 < 1:
                img[y, x] = pal_at(STEEL, 4.2 - (x - 8) * 0.4) + (255,)
    img[12, 10:16] = STEEL[0] + (255,)
    img[13:16, 12:14] = STEEL[0] + (255,)
    for k in range(5):  # horns
        img[9 - k, 7 - k // 2] = CREAM[2] + (255,)
        img[9 - k, 18 + k // 2] = CREAM[1] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, 13, 48, 9, 2)


def banner_red(frame=0):
    """A standard: a crossbar with gold finials, a long red banner with a forked tail, gold border and a sword."""
    W, H = 30, 74
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for y in range(6, 72):
        img[y, 14] = WOOD[4] + (255,)
        img[y, 15] = WOOD[2] + (255,)
    img[2:6, 14:16] = GOLD[3] + (255,)
    img[8, 3:27] = WOOD[4] + (255,)
    img[9, 3:27] = WOOD[2] + (255,)
    for x in (1, 27):
        img[7:11, x:x + 2] = GOLD[2] + (255,)
    for y in range(10, 46):
        sw = int(round(math.sin(y / 6 - frame * math.pi / 2) * (y - 10) / 36 * 1.5))
        cut = max(0, y - 38)  # forked tail
        for x in range(5, 25):
            if abs(x - 15) < cut:
                continue
            u = (x - 5) / 19
            t = 3.4 - u * 1.4 + math.sin(u * 6 + frame) * 0.4
            c = pal_at(CLOTH_RED, t)
            if x in (6, 23) or y in (11,):
                c = GOLD[2] if x != 23 else GOLD[1]
            img[y, x + sw] = c + (255,)
        if 16 <= y <= 34:  # sword emblem
            img[y, 14 + sw] = GOLD[3] + (255,)
            img[y, 15 + sw] = GOLD[1] + (255,)
        if y == 30:
            img[y, 11 + sw:19 + sw] = GOLD[2] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, 15, 72, 6, 1.5)


def banner_red_frames():
    return [banner_red(f) for f in range(4)]


def wagon(seed):
    """A pedlar's wagon: planked bed on spoked wheels, a green canvas hood on hoops, potions on the tailboard."""
    W, H = 104, 76
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for x in range(0, 22):  # shafts reaching forward
        y = 52 + x // 6
        img[y, x] = WOOD[3] + (255,)
        img[y + 1, x] = WOOD[1] + (255,)
    for y in range(18, 46):  # canvas hood: arched hoops, lit on the left, sagging between hoops
        for x in range(20, 96):
            u = (x - 20) / 75
            top = 18 + int(4 * abs(math.sin(u * math.pi * 3)))
            if y < top:
                continue
            t = 3.6 - u * 1.2 - (y - top) * 0.04 - (1.1 if abs(math.sin(u * math.pi * 3)) < 0.12 else 0)
            img[y, x] = pal_at(CLOTH_GREEN, t) + (255,)
    for x in range(20, 96):
        img[45, x] = CLOTH_GREEN[0] + (255,)
    wood_block(img, 16, 46, 98, 60, seed)  # bed
    for x in range(16, 99):
        img[46, x] = WOOD[5] + (255,)
        img[60, x] = WOOD[0] + (255,)
    for i, pal in enumerate(([(40, 110, 50), (90, 190, 90)], [(150, 80, 20), (240, 160, 60)],
                             [(70, 30, 70), (150, 80, 150)], [(30, 60, 140), (110, 160, 230)])):
        bx = 40 + i * 12
        for y in range(38, 46):
            half = 1 if y < 41 else 3
            for x in range(bx - half, bx + half + 1):
                img[y, x] = (pal[1] if x < bx else pal[0]) + (255,)
        img[37, bx] = CREAM[2] + (255,)
        img[42, bx - 2] = (255, 255, 255, 255)

    def wheel(cx, cy, r):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = math.hypot(x - cx, y - cy)
                if d <= r and d > r - 2:
                    img[y, x] = (WOOD[4] if (x - cx) + (y - cy) < 0 else WOOD[1]) + (255,)
                elif d <= r - 2 and (abs(x - cx) < 1 or abs(y - cy) < 1 or abs(abs(x - cx) - abs(y - cy)) < 1):
                    img[y, x] = WOOD[2] + (255,)
        img[cy - 1:cy + 2, cx - 1:cx + 2] = IRON[2] + (255,)

    wheel(30, 62, 10)
    wheel(84, 62, 10)
    out = fine_outline(img)
    return contact_shadow(out, 56, 72, 46, 3.5)


def bakery(seed):
    """A baker's table under a linen cloth between two poles: loaves, a long loaf, a basket of buns, flour sacks."""
    rng = _rng(seed)
    W, H = 88, 58
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for x in (6, 80):
        for y in range(4, 52):
            img[y, x] = WOOD[4] + (255,)
            img[y, x + 1] = WOOD[2] + (255,)
    for y in range(28, 48):  # tablecloth, hanging to a frilled hem
        for x in range(10, 79):
            u = (x - 10) / 68
            t = 3.2 - u * 1.2 - (y - 28) * 0.03 - (1 if y > 44 and x % 3 == 0 else 0)
            img[y, x] = pal_at(LINEN, t) + (255,)
    BREAD = [(110, 56, 22), (170, 96, 40), (214, 140, 64), (242, 196, 120)]
    for cx, cy, rx in ((20, 27, 5), (34, 26, 4), (64, 27, 5)):
        for y in range(cy - 3, cy + 2):
            for x in range(cx - rx, cx + rx + 1):
                if ((x - cx) / rx) ** 2 + ((y - cy) / 3.4) ** 2 < 1:
                    img[y, x] = pal_at(BREAD, 3 - (x - cx + rx) / (2 * rx) * 1.6 - (y - cy + 3) * 0.3) + (255,)
        img[cy - 2, cx - 1] = BREAD[3] + (255,)
        img[cy - 1, cx + 1] = BREAD[1] + (255,)
    for k in range(12):  # a long loaf lying diagonally
        x, y = 42 + k, 27 - k // 3
        img[y, x] = BREAD[2] + (255,)
        img[y + 1, x] = BREAD[1] + (255,)
    for y in range(20, 28):  # basket of buns
        for x in range(70, 80):
            if y > 23:
                img[y, x] = pal_at(BURLAP, 3 - (x - 70) * 0.2 + ((x + y) % 2) * 0.5) + (255,)
    for cx in (72, 75, 78):
        _ballpix(img, cx, 22, 1.8, BREAD)
    for cx in (5, 82):  # flour sacks at the ends
        for y in range(44, 56):
            half = 4 if y > 47 else 2
            for x in range(cx - half, cx + half + 1):
                img[y, x] = pal_at(BURLAP, 3.6 - (x - cx + half) * 0.4) + (255,)
        img[43, cx - 1:cx + 2] = (120, 90, 50, 255)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 54, 42, 3)


def pottery(seed):
    """Jars and pots of the potter's trade."""
    W, H = 48, 26
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for cx, h, pal in ((7, 16, CLAY), (19, 20, CREAM), (31, 15, CLAY), (41, 13, CREAM)):
        jar(img, cx, 23, h, pal)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 24, 23, 2)


def fence(seed):
    """A low market rail: posts with round tops and a scalloped board."""
    W, H = 66, 26
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for y, t in ((8, 5), (9, 4), (10, 3), (11, 2), (18, 4), (19, 2)):
        img[y, 3:63] = WOOD[t] + (255,)
    for x in range(6, 60):
        if math.sin((x - 6) / 54 * math.pi * 5) > 0:
            d = int(3 * math.sin((x - 6) / 54 * math.pi * 5))
            img[12:12 + d, x] = WOOD[2] + (255,)
    for x in (2, 31, 60):
        for y in range(5, 23):
            img[y, x:x + 4] = [WOOD[4] + (255,), WOOD[3] + (255,), WOOD[2] + (255,), WOOD[1] + (255,)]
        img[4, x + 1:x + 3] = WOOD[5] + (255,)
    out = fine_outline(img)
    return contact_shadow(out, W / 2, 23, 31, 2)


def mystic_tent(frame=0):
    """The fortune-teller's tent: a peaked purple roof with a jagged lilac trim, grey drapes swept out like wings
    over a dark doorway, a crescent moon crest, and a crystal ball on a stand whose glow pulses (4 frames)."""
    W, H = 104, 104
    img = np.zeros((H, W, 4), dtype=np.uint8)
    apex, eave = 8, 60
    for y in range(apex, 96):  # grey drapes first (they hang wider than the roof)
        if y < 30:
            continue
        spread = 18 + (y - 30) * 0.55
        for side in (-1, 1):
            for k in range(int(spread * 0.55)):
                x = int(52 + side * (spread - k))
                if 0 <= x < W:
                    t = 3.8 - k * 0.08 + math.sin(k * 0.9) * 0.6 - (0.8 if side > 0 else 0)
                    img[y, x] = pal_at(CLOTH_GREY, t) + (255,)
    for y in range(apex, eave + 1):  # roof
        half = (y - apex) * 0.75 + 1
        for x in range(int(52 - half), int(52 + half) + 1):
            u = (x - (52 - half)) / max(1, 2 * half)
            t = 3.8 - u * 2 + math.sin(u * 14) * 0.35
            img[y, x] = pal_at(CLOTH_PURPLE, t) + (255,)
        for side in (-1, 1):  # lilac zigzag trim along each slope
            x = int(52 + side * half)
            zig = 1 if (y // 2) % 2 else 0
            for dx in range(2):
                xx = x - side * (dx + zig)
                if 0 <= xx < W:
                    img[y, xx] = ((212, 150, 236) if dx == 0 else (176, 108, 210)) + (255,)
    for y in range(eave, 96):  # purple tails hanging at the front corners
        for side in (-1, 1):
            x0 = 52 + side * (40 - (y - eave) // 6)
            for k in range(5 - (y - eave) // 8):
                img[y, int(x0 + side * k)] = pal_at(CLOTH_PURPLE, 2.6 - k * 0.3) + (255,)
    for y in range(44, 96):  # doorway
        half = 6 + (y - 44) * 0.32
        for x in range(int(52 - half), int(52 + half) + 1):
            img[y, x] = (28, 18, 34, 255)
    for y in range(18, 30):  # crescent moon crest
        for x in range(44, 60):
            a = (x - 52) ** 2 + (y - 24) ** 2 < 36
            b = (x - 55) ** 2 + (y - 22) ** 2 < 25
            if a and not b:
                img[y, x] = (GOLD[3] if x < 50 else GOLD[2]) + (255,)
    pulse = [0, 1, 2, 1][frame % 4]  # crystal ball on a stand in the doorway
    for y in range(86, 96):
        img[y, 50:54] = WOOD[2] + (255,)
    img[95, 46:58] = WOOD[3] + (255,)
    BALL = [(120, 30, 50), (180, 50, 70), (230, 90, 100), (255, 170, 170)]
    _ballpix(img, 52, 80, 7, BALL)
    img[76, 49] = (255, 230, 230, 255)
    _warm(img, 52, 80, 14, 0.4 + pulse * 0.15)
    out = fine_outline(img)
    return contact_shadow(out, 52, 97, 46, 4)


def mystic_frames():
    return [mystic_tent(f) for f in range(4)]
