"""Pixel-art props for Crownfall maps: trees, bushes and the like, drawn in code at the characters' pixel scale.

Each prop is an RGBA image whose bottom-centre is where it stands (its foot), with a soft ground shadow drawn in.
Trees and bushes are built from overlapping rounded leaf clumps: each clump lit from the top-left with a leafy
texture, darker where a clump in front overlaps one behind, all outlined. sway() makes animation frames in which
the top moves most and the roots stay put.
"""
import math

import numpy as np

OUTLINE = (16, 22, 14)
LEAF_MIREFEN = [(26, 46, 30), (38, 64, 38), (54, 86, 44), (76, 110, 52), (104, 138, 64)]
LEAF_MOSS = [(46, 58, 26), (66, 80, 30), (90, 104, 36), (118, 130, 46), (150, 160, 62)]
BARK = [(40, 28, 22), (58, 40, 28), (80, 56, 36), (104, 76, 48)]
SHADOW = (12, 18, 12, 110)
MOSS_STRAND = [(92, 112, 40), (130, 150, 56), (170, 184, 82)]


def _rng(seed):
    return np.random.default_rng(seed)


def _outline(img):
    """Dark 1 px outline around every opaque area (outside the shape)."""
    a = img[..., 3] > 0
    ring = np.zeros_like(a)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ring |= np.roll(np.roll(a, dy, 0), dx, 1)
    ring &= ~a
    img[ring] = OUTLINE + (255,)
    return img


def _shadow(img, cx, cy, rx, ry):
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    m = (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2 < 1) & (img[..., 3] == 0)
    img[m] = SHADOW


def canopy(img, cx, cy, rw, rh, puffs, pal, seed, texture=0.5):
    """Draw a canopy of `puffs` leaf clumps inside the ellipse (cx, cy, rw, rh). Back clumps first."""
    rng = _rng(seed)
    h, w = img.shape[:2]
    yy, xx = np.mgrid[0:h, 0:w]
    blobs = []
    for i in range(puffs):
        ang = rng.random() * math.tau
        rad = math.sqrt(rng.random()) * 0.62
        bx = cx + math.cos(ang) * rw * rad
        by = cy + math.sin(ang) * rh * rad
        r = (0.38 + rng.random() * 0.2) * min(rw, rh)
        blobs.append((by, bx, r))
    blobs.sort()  # top (back) clumps first, front ones over them
    grain = rng.random((h, w))
    # leaf clusters: small 3-4 px round lights scattered over the canopy (instead of single-pixel noise)
    leaves = np.zeros((h, w))
    for _ in range(int(rw * rh * 0.06)):
        lx0 = cx + (rng.random() - 0.5) * 2 * rw
        ly0 = cy + (rng.random() - 0.5) * 2 * rh
        rr = 1.4 + rng.random() * 1.2
        dd = np.hypot(xx - lx0, yy - ly0)
        leaves = np.maximum(leaves, np.clip(1 - dd / rr, 0, 1) * ((xx - lx0) + (yy - ly0) < 0.5))
    for by, bx, r in blobs:
        ang = np.arctan2(yy - by, xx - bx)
        phase = rng.random() * math.tau
        lobes = 1 + 0.10 * np.sin(ang * (6 + int(rng.random() * 3)) + phase) + 0.05 * np.sin(ang * 13 + phase * 2)
        d = np.hypot(xx - bx, yy - by) / (r * lobes)
        inside = d < 1
        # light from the top-left of each clump; leafy break-up along the light falloff
        lx, ly = bx - r * 0.45, by - r * 0.5
        lit = 1 - np.clip(np.hypot(xx - lx, yy - ly) / (r * 1.7), 0, 1)
        t = lit * 3.6 + leaves * 1.3 + (grain - 0.5) * texture * 0.7
        rim = inside & (d > 0.86) & ((xx - bx) + (yy - by) > 0)  # dark lower-right rim where it meets clumps behind
        idx = np.clip(t.astype(int), 0, len(pal) - 1)
        idx[rim] = 0
        col = np.array(pal, dtype=np.uint8)[idx]
        img[inside, :3] = col[inside]
        img[inside, 3] = 255
    return img


def trunk(img, x, top, bottom, width, seed):
    """A trunk from `top` to `bottom` (the foot), flaring into roots at the base."""
    rng = _rng(seed)
    h, w = img.shape[:2]
    for y in range(top, bottom + 1):
        flare = max(0, (y - (bottom - 7))) * 1.1
        half = width / 2 * (0.75 + 0.25 * (y - top) / max(1, bottom - top)) + flare
        for xx in range(int(x - half), int(x + half) + 1):
            if 0 <= xx < w and 0 <= y < h and img[y, xx, 3] == 0:
                rel = (xx - (x - half)) / max(1, 2 * half)
                k = 3 if rel < 0.3 else 2 if rel < 0.6 else 1 if rel < 0.85 else 0
                if rng.random() < 0.15:
                    k = max(0, k - 1)
                img[y, xx] = BARK[k] + (255,)
    # roots: a few short claws at the base
    for dx in (-1, 1):
        for k in range(int(width * 0.6)):
            rx = int(x + dx * (width / 2 + 2 + k))
            ry = bottom - (k // 3)
            if 0 <= rx < w and img[ry, rx, 3] == 0:
                img[ry, rx] = BARK[1] + (255,)


def moss_strands(img, cx, bottom_y, rw, seed, count=9):
    """Moss hanging from under a canopy (swamp trees)."""
    rng = _rng(seed)
    h, w = img.shape[:2]
    for _ in range(count):
        x = int(cx + (rng.random() - 0.5) * rw * 1.6)
        col = img[:, x, 3] if 0 <= x < w else None
        if col is None or not col.any():
            continue
        y0 = int(np.nonzero(col)[0].max())
        length = int(4 + rng.random() * 10)
        for k in range(length):
            y = y0 + k
            if y >= h:
                break
            img[y, x] = MOSS_STRAND[0 if k > length - 3 else (2 if k == 0 else 1)] + (255,)


def tree(seed, size=1.0, pal=LEAF_MIREFEN, moss=False):
    """A broadleaf tree. size 1.0 ~ 140 px tall (about twice a character)."""
    W, H = int(140 * size), int(160 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    foot = H - 6
    cx = W // 2
    crown_h = int(H * 0.62)
    crown_h = int(H * 0.72)
    canopy(img, cx, int(crown_h * 0.52) + 4, W * 0.44, crown_h * 0.48, puffs=int(10 + 7 * size), pal=pal, seed=seed)
    if moss:
        moss_strands(img, cx, crown_h, W * 0.38, seed + 3, count=int(8 * size) + 4)
    trunk(img, cx + int((_rng(seed + 1).random() - 0.5) * 6), int(crown_h * 0.8), foot, max(6, int(11 * size)), seed + 2)
    _outline(img)
    _shadow(img, cx, foot + 1, W * 0.30, 5 * size + 2)
    return img


def bush(seed, size=1.0, pal=LEAF_MIREFEN):
    W, H = int(56 * size), int(44 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    canopy(img, W // 2, H // 2 + 1, W * 0.44, H * 0.40, puffs=int(5 + 3 * size), pal=pal, seed=seed, texture=0.7)
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


STONE = [(48, 50, 50), (70, 72, 70), (96, 96, 90), (124, 122, 112)]
MOSS = [(52, 74, 30), (76, 100, 40), (104, 128, 52)]
CAP = [(80, 70, 92), (110, 100, 122), (150, 140, 160), (196, 188, 204)]  # pale violet swamp caps
STEM = [(150, 140, 120), (186, 176, 154), (214, 206, 186)]
REED = [(54, 78, 34), (78, 106, 44), (108, 136, 58)]
CATTAIL = [(70, 44, 28), (98, 64, 38)]
LILY = [(36, 70, 40), (54, 98, 52), (80, 128, 64)]
BLOSSOM = [(206, 140, 170), (238, 190, 210)]


def _ellipse_mask(h, w, cx, cy, rx, ry):
    yy, xx = np.mgrid[0:h, 0:w]
    return (((xx - cx) / rx) ** 2 + ((yy - cy) / ry) ** 2) < 1


def rock(seed, size=1.0):
    """A mossy boulder: lit facets from the top-left, moss on top."""
    rng = _rng(seed)
    W, H = int(40 * size), int(32 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    h, w = H, W
    yy, xx = np.mgrid[0:h, 0:w]
    cx, cy, rx, ry = w / 2, h * 0.55, w * 0.44, h * 0.40
    ang = np.arctan2(yy - cy, xx - cx)
    lobes = 1 + 0.08 * np.sin(ang * 5 + rng.random() * 6)
    d = np.hypot((xx - cx) / rx, (yy - cy) / ry) / lobes
    inside = d < 1
    lit = np.clip(1 - np.hypot(xx - (cx - rx * 0.4), yy - (cy - ry * 0.6)) / (rx * 1.6), 0, 1)
    facet = ((xx + yy * 2 + int(rng.random() * 7)) // 7) % 2
    t = lit * 3.2 + facet * 0.4
    idx = np.clip(t.astype(int), 0, 3)
    img[inside, :3] = np.array(STONE, dtype=np.uint8)[idx][inside]
    img[inside, 3] = 255
    moss = inside & (yy < cy - ry * 0.15 + np.sin(xx * 0.7) * 2) & (rng.random((h, w)) > 0.25)
    midx = np.clip((lit * 2.6).astype(int), 0, 2)
    img[moss, :3] = np.array(MOSS, dtype=np.uint8)[midx][moss]
    _outline(img)
    _shadow(img, cx, h - 3, rx, 3)
    return img


def stump(seed, size=1.0):
    rng = _rng(seed)
    W, H = int(34 * size), int(28 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    cx = W // 2
    top = int(H * 0.3)
    trunk(img, cx, top, H - 5, int(W * 0.5), seed)
    ring = _ellipse_mask(H, W, cx, top + 1, W * 0.27, 3)
    img[ring] = (150, 118, 80, 255)
    inner = _ellipse_mask(H, W, cx, top + 1, W * 0.16, 1.6)
    img[inner] = (122, 92, 62, 255)
    _outline(img)
    _shadow(img, cx, H - 4, W * 0.42, 3)
    return img


def reeds(seed, cattails=True):
    """A clump of reeds with a couple of cattails; drawn blade by blade."""
    rng = _rng(seed)
    W, H = 22, 30
    img = np.zeros((H, W, 4), dtype=np.uint8)
    base = H - 2
    for k in range(7):
        x0 = W / 2 + (rng.random() - 0.5) * 8
        lean = (rng.random() - 0.5) * 0.8
        length = int(12 + rng.random() * 14)
        for t in range(length):
            x = int(round(x0 + lean * t * (t / length)))
            y = base - t
            if 0 <= x < W and 0 <= y < H:
                img[y, x] = REED[2 if t > length * 0.7 else 1 if t > length * 0.3 else 0] + (255,)
        if cattails and k < 2:
            for t in range(3):
                x = int(round(x0 + lean * length))
                y = base - length - t
                if 0 <= x < W and 0 <= y < H:
                    img[y, x] = CATTAIL[t % 2] + (255,)
                    if x + 1 < W:
                        img[y, x + 1] = CATTAIL[0] + (255,)
    _outline(img)
    return img


def mushroom(seed, size=1.0):
    """A pale swamp mushroom: wide cap lit from the top-left, spotted, on a thick stem."""
    rng = _rng(seed)
    W, H = int(46 * size), int(52 * size)
    img = np.zeros((H, W, 4), dtype=np.uint8)
    cx = W / 2
    stem_top, foot = int(H * 0.45), H - 5
    for y in range(stem_top, foot + 1):
        half = W * 0.11 + (y - stem_top) * 0.06
        for x in range(int(cx - half), int(cx + half) + 1):
            rel = (x - (cx - half)) / (2 * half)
            img[y, x] = STEM[2 if rel < 0.35 else 1 if rel < 0.75 else 0] + (255,)
    h, w = H, W
    yy, xx = np.mgrid[0:h, 0:w]
    capm = _ellipse_mask(h, w, cx, H * 0.36, W * 0.47, H * 0.22) & (yy < H * 0.47)
    lit = np.clip(1 - np.hypot(xx - (cx - W * 0.2), yy - H * 0.22) / (W * 0.6), 0, 1)
    idx = np.clip((lit * 3.4).astype(int), 0, 3)
    img[capm, :3] = np.array(CAP, dtype=np.uint8)[idx][capm]
    img[capm, 3] = 255
    under = capm & (yy > H * 0.43)
    img[under, :3] = CAP[0]
    for _ in range(6):  # spots
        sx, sy = int(cx + (rng.random() - 0.5) * W * 0.6), int(H * 0.22 + rng.random() * H * 0.16)
        if capm[sy, sx]:
            img[sy, sx, :3] = CAP[3]
    _outline(img)
    _shadow(img, cx, H - 4, W * 0.3, 3)
    return img


def lilypad(seed, flower=False):
    """A ground decal for water: a pad with its notch, sometimes a blossom."""
    rng = _rng(seed)
    W, H = 16, 10
    img = np.zeros((H, W, 4), dtype=np.uint8)
    yy, xx = np.mgrid[0:H, 0:W]
    pad = _ellipse_mask(H, W, 8, 5, 6.5, 3.6)
    notch = (xx > 8) & (abs(yy - 5) <= (xx - 8) * 0.4)
    m = pad & ~notch
    img[m] = LILY[1] + (255,)
    img[m & (yy < 4)] = LILY[2] + (255,)
    img[m & (yy > 6)] = LILY[0] + (255,)
    if flower:
        img[3:5, 6:9] = BLOSSOM[0] + (255,)
        img[3, 7] = BLOSSOM[1] + (255,)
    _outline(img)
    return img


def log(seed, length=70):
    """A fallen, mossy log lying across the view."""
    rng = _rng(seed)
    W, H = length, 22
    img = np.zeros((H, W, 4), dtype=np.uint8)
    for x in range(3, W - 6):
        for y in range(6, 16):
            rel = (y - 6) / 10
            k = 3 if rel < 0.25 else 2 if rel < 0.55 else 1 if rel < 0.85 else 0
            if rng.random() < 0.12:
                k = max(0, k - 1)
            img[y, x] = BARK[k] + (255,)
        if rng.random() < 0.55:
            img[6, x] = MOSS[1 + int(rng.random() * 2)] + (255,)
    end = _ellipse_mask(H, W, W - 6, 11, 3, 5)
    img[end] = (150, 118, 80, 255)
    img[_ellipse_mask(H, W, W - 6, 11, 1.5, 2.5)] = (110, 84, 56, 255)
    _outline(img)
    _shadow(img, W / 2, 18, W * 0.48, 3)
    return img
