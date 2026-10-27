"""Convert a large painted sprite sheet into a Crownfall production sheet (Docs/Art-Spec.md).

python Tools/sprites.py <in.png> <out.png> [--x 165:720] [--rows 0,1,2,3,4] [--height 64] [--cell 96]

- Finds each figure by scanning for non-background pixels inside the --x column range
  (use it to skip labels and info panels baked into the image).
- Keeps the listed source rows, in that order (spec order: S, SW, W, NW, N).
- Removes the near-black background by flood fill from each figure's border.
- Scales every figure by ONE factor (from the first kept row) so proportions stay consistent,
  reduces the whole sheet to a shared 32-colour palette, makes alpha hard (0 or 255),
  adds a 1 px outline, and stands each figure's feet on the pivot (cell/2, cell - 8).

This is a stopgap for testing scale, pivot and directions in the game. Shipping art still needs a
pixel-artist cleanup pass: automatic downscaling leaves noise and frame-to-frame flicker.
"""
import argparse
from PIL import Image

BG_THRESHOLD = 45  # r+g+b at or below this counts as background
FG_THRESHOLD = 75  # r+g+b above this counts as figure when locating cells


def spans(flags, offset=0, min_len=8):
    out, start = [], None
    for i, on in enumerate(flags):
        if on and start is None:
            start = i
        if not on and start is not None:
            out.append((start + offset, i - 1 + offset))
            start = None
    if start is not None:
        out.append((start + offset, len(flags) - 1 + offset))
    return [s for s in out if s[1] - s[0] >= min_len]


def locate(im, x0, x1):
    px, w, h = im.load(), im.width, im.height

    def fg(x, y):
        r, g, b, a = px[x, y]
        return a > 0 and r + g + b > FG_THRESHOLD

    rows = spans([any(fg(x, y) for x in range(x0, x1, 2)) for y in range(h)])
    cols = spans([any(fg(x, y) for y in range(0, h, 2)) for x in range(x0, x1)], x0)
    return rows, cols


def cutout(im, box):
    c = im.crop(box).copy()
    w, h = c.size
    px = c.load()
    seen = set()
    stack = [(x, y) for x in range(w) for y in (0, h - 1)] + [(x, y) for y in range(h) for x in (0, w - 1)]
    while stack:
        x, y = stack.pop()
        if (x, y) in seen or not (0 <= x < w and 0 <= y < h):
            continue
        r, g, b, a = px[x, y]
        if r + g + b > BG_THRESHOLD:
            continue
        seen.add((x, y))
        px[x, y] = (0, 0, 0, 0)
        stack += [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
    return c.crop(c.getbbox())


def feet_centre(fig):
    px, w, h = fig.load(), fig.width, fig.height
    xs = [x for y in range(max(0, h - 6), h) for x in range(w) if px[x, y][3] > 0]
    return round(sum(xs) / len(xs)) if xs else w // 2


def outline(sheet, colour):
    src = sheet.load()
    out = sheet.copy()
    dst = out.load()
    w, h = sheet.size
    for y in range(h):
        for x in range(w):
            if src[x, y][3] == 0 and any(
                0 <= x + dx < w and 0 <= y + dy < h and src[x + dx, y + dy][3] > 0
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
            ):
                dst[x, y] = colour
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src")
    ap.add_argument("out")
    ap.add_argument("--x", default=None, help="column range to scan, e.g. 165:720")
    ap.add_argument("--rows", default="0,1,2,3,4")
    ap.add_argument("--height", type=int, default=64)
    ap.add_argument("--cell", type=int, default=96)
    a = ap.parse_args()

    im = Image.open(a.src).convert("RGBA")
    x0, x1 = (int(v) for v in a.x.split(":")) if a.x else (0, im.width)
    rows, cols = locate(im, x0, x1)
    keep = [int(r) for r in a.rows.split(",")]
    print(f"found {len(rows)} rows x {len(cols)} frames; keeping rows {keep}")

    figs = [[cutout(im, (cx0 - 6, rows[r][0] - 6, cx1 + 7, rows[r][1] + 7)) for cx0, cx1 in cols] for r in keep]
    scale = a.height / figs[0][0].height
    cell, pivot_y = a.cell, a.cell - 8
    sheet = Image.new("RGBA", (cell * len(cols), cell * len(keep)), (0, 0, 0, 0))
    for ri, row in enumerate(figs):
        for fi, fig in enumerate(row):
            small = fig.resize((max(1, round(fig.width * scale)), max(1, round(fig.height * scale))), Image.BOX)
            small.putalpha(small.split()[3].point(lambda v: 255 if v >= 128 else 0))
            fx = fi * cell + cell // 2 - feet_centre(small)
            fy = ri * cell + pivot_y - small.height
            sheet.alpha_composite(small, (fx, fy))

    alpha = sheet.split()[3]
    # Build the palette from figure pixels only; transparent pixels would otherwise take palette slots.
    # Fast octree keeps small distinct areas (the grey shirt); median cut merged it into the skin tones.
    opaque = [p[:3] for p in sheet.getdata() if p[3] == 255]
    sample = Image.new("RGB", (len(opaque), 1))
    sample.putdata(opaque)
    palette = sample.quantize(colors=32, method=Image.Quantize.FASTOCTREE)
    flat = sheet.convert("RGB").quantize(palette=palette, dither=Image.Dither.NONE)
    darkest = min(flat.getpalette()[: 32 * 3][i:i + 3] for i in range(0, 32 * 3, 3))
    sheet = flat.convert("RGBA")
    sheet.putalpha(alpha)
    sheet = outline(sheet, tuple(darkest) + (255,))
    sheet.save(a.out)
    print(f"wrote {a.out}: {sheet.width} x {sheet.height}, scale {scale:.3f}")


if __name__ == "__main__":
    main()
