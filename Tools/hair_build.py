"""Build the bald bodies and every hairstyle layer (Docs/Plans/2026-10-28-class-origin-traits-hair.md, section 5).

    python Tools/hair_build.py <out_dir> [--styles id,id] [--bodies m,f] [--jobs 4]

For each body: animates the bald base (idle, walk, run, dodge) and each hairstyle's styled base with
Tools/walk_cycle.py --classes, then for each hairstyle:
  - the layer = every pixel where the styled frame differs from the bald one, so bald + layer = styled except
    where the styled art trimmed a bald outline pixel (a one-pixel nub at the hair's edge; counted, allowed);
  - checks every composite frame (bald + layer) is one piece with no holes or gaps;
  - audits the styled sheets (Tools/walk_audit.py rules, one connected piece per frame);
  - packs the 256 layer frames (4 anims x 8 directions x 8 frames) into one atlas, with a class atlas.
Writes to <out_dir>:
  <rig>_bald_<anim>.png (+ _classes), <rig>_<style>_<anim>.png (+ _classes), hair_<rig>_<style>.png (atlas),
  hair_<rig>_<style>_classes.png, hair_<rig>_<style>.json (frame rects), preview_<rig>_<style>.gif.
"""
import argparse
import json
import os
import subprocess
import sys
import tempfile
import zipfile
from concurrent.futures import ThreadPoolExecutor

from PIL import Image

import female
import hair

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, ".."))
ZIP = os.path.join(ROOT, "Art", "Source", "cf_human_m_full_rags_walk_v2.zip")
ANIMS = ["idle", "walk", "run", "dodge"]
ROWS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
CELL, FRAMES = 96, 8
RIG = {"m": "humanm", "f": "humanf"}
PREFIX = {"m": "cf_human_m_full_rags_walk", "f": "cf_human_f_full_rags_walk"}
ATLAS_WIDTH = 512
PAD = 1  # px between atlas cells


def male_sources(scratch):
    src = os.path.join(scratch, "male")
    with zipfile.ZipFile(ZIP) as z:
        z.extractall(src)
    for root, _, files in os.walk(src):
        if any(f.endswith("_frame01.png") for f in files):
            return root
    raise FileNotFoundError("no frame01 images in " + ZIP)


def write_bases(folder, body, make):
    """make(male_base, direction) -> (image, hair pixels or None). Writes the poses walk_cycle.py reads."""
    import walk_cycle as W

    os.makedirs(folder, exist_ok=True)
    for d in hair.DRAWN:
        male = W.pivoted(f"{SRC_MALE}/cf_human_m_full_rags_walk_{W.LABEL_FOR[d]}_frame01.png")
        image, hair_px = make(male, d)
        path = os.path.join(folder, f"{PREFIX[body]}_{W.LABEL_FOR[d]}_frame01.png")
        image.save(path)
        if hair_px is not None:
            female.write_hair_mask(path.replace("_frame01.png", "_hairmask.png"), image.size, hair_px)


def measure(folder, body, out_dir, name, spin=None):
    """First pass: roll this pose set through the dodge, recording its whole-figure moves. spin: a motion file whose
    spin centres and flips to use (the bald body's), so only the landings are measured."""
    path = os.path.join(out_dir, f"{name}_dodge_motion_free.json")
    extra = ["--motion-in", spin] if spin else []
    subprocess.run([sys.executable, os.path.join(HERE, "walk_cycle.py"), folder, os.path.join(out_dir, f"{name}_free.png"),
                    "--style", "dodge", "--prefix", PREFIX[body], "--motion-out", path] + extra, check=True,
                   stdout=subprocess.DEVNULL)
    with open(path) as fh:
        return json.load(fh)


def shared_motion(bald, styles):
    """One set of whole-figure moves for a body and all its hairstyles: the bald body's spin centres and flips,
    and for each landing the highest any of them needs (so no hair ever dips through the floor mid-roll)."""
    out = dict(bald)
    for key in bald:
        if key.endswith("/land"):
            frame = key[: -len("/land")]
            total = [rec[key] + rec.get(frame + "/reland", 0) for rec in [bald] + styles if key in rec]
            out[key] = min(total)  # the whole drop to the floor, after the cleanup's correction
            out[frame + "/reland"] = 0
    return out


def animate(folder, body, out_dir, name):
    """All four anims of the poses in folder -> <name>_<anim>.png and <name>_<anim>_classes.png, replaying the
    body's shared motion so every hairstyle's body lines up with the bald one."""
    def one(anim):
        sheet = os.path.join(out_dir, f"{name}_{anim}.png")
        classes = os.path.join(out_dir, f"{name}_{anim}_classes.png")
        motion = os.path.join(out_dir, f"{RIG[body]}_{anim}_motion.json")
        subprocess.run([sys.executable, os.path.join(HERE, "walk_cycle.py"), folder, sheet, "--style", anim,
                        "--prefix", PREFIX[body], "--classes", classes, "--motion-in", motion], check=True,
                       stdout=subprocess.DEVNULL)
        audit = subprocess.run([sys.executable, os.path.join(HERE, "walk_audit.py"), folder, sheet, anim, PREFIX[body], motion],
                               capture_output=True, text=True)
        return anim, audit.stdout.strip().splitlines()[-1] if audit.stdout.strip() else audit.stderr.strip()
    return one


def layer(styled, bald, styled_classes):
    """(layer RGBA, layer classes L, lost pixel count) for one sheet."""
    sp, bp, cp = styled.load(), bald.load(), styled_classes.load()
    out = Image.new("RGBA", styled.size, (0, 0, 0, 0))
    cls = Image.new("L", styled.size, 0)
    op, clp = out.load(), cls.load()
    lost = 0
    for y in range(styled.height):
        for x in range(styled.width):
            s, b = sp[x, y], bp[x, y]
            if s[3] and s != b:
                op[x, y] = s
                clp[x, y] = cp[x, y]
            elif b[3] and not s[3]:
                lost += 1
    return out, cls, lost


def pack(frames):
    """frames: list of (image, classes, (dx, dy)) crops -> (atlas, class atlas, rects [x, y, w, h, dx, dy])."""
    order = sorted(range(len(frames)), key=lambda i: -frames[i][0].height)
    rects = [None] * len(frames)
    x = y = shelf = 0
    for i in order:
        img = frames[i][0]
        w, h = img.size
        if w == 0 or h == 0:
            rects[i] = [0, 0, 0, 0, 0, 0]
            continue
        if x + w > ATLAS_WIDTH:
            x, y, shelf = 0, y + shelf + PAD, 0
        rects[i] = [x, y, w, h, frames[i][2][0], frames[i][2][1]]
        x += w + PAD
        shelf = max(shelf, h)
    height = y + shelf
    assert height <= 1024, f"atlas too tall: {height}"
    atlas = Image.new("RGBA", (ATLAS_WIDTH, max(1, height)), (0, 0, 0, 0))
    catlas = Image.new("L", atlas.size, 0)
    for (img, cls, _), r in zip(frames, rects):
        if r[2]:
            atlas.paste(img, (r[0], r[1]))
            catlas.paste(cls, (r[0], r[1]))
    return atlas, catlas, rects


def preview(out_dir, body, style_id, path):
    """Bald + layer, all 8 directions, each anim in turn (proves the layer lines up)."""
    frames = []
    for anim in ["idle", "walk", "run", "dodge"]:
        bald = Image.open(os.path.join(out_dir, f"{RIG[body]}_bald_{anim}.png")).convert("RGBA")
        lay = Image.open(os.path.join(out_dir, f"{RIG[body]}_{style_id}_{anim}_layer.png")).convert("RGBA")
        for f in range(FRAMES):
            canvas = Image.new("RGBA", (CELL * 8, CELL), (58, 62, 58, 255))
            for r in range(8):
                box = (f * CELL, r * CELL, (f + 1) * CELL, (r + 1) * CELL)
                canvas.alpha_composite(bald.crop(box), (r * CELL, 0))
                canvas.alpha_composite(lay.crop(box), (r * CELL, 0))
            frames.append(canvas.resize((canvas.width * 2, canvas.height * 2), Image.NEAREST).convert("P"))
    frames[0].save(path, save_all=True, append_images=frames[1:], duration=110, loop=0, disposal=2)


def main():
    global SRC_MALE
    ap = argparse.ArgumentParser()
    ap.add_argument("out_dir")
    ap.add_argument("--styles", default="")
    ap.add_argument("--bodies", default="m,f")
    ap.add_argument("--jobs", type=int, default=4)
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    wanted = set(filter(None, a.styles.split(",")))
    report = {}
    with tempfile.TemporaryDirectory() as scratch:
        SRC_MALE = male_sources(scratch)
        jobs = []
        for body in a.bodies.split(","):
            folder = os.path.join(scratch, f"{body}_bald")
            write_bases(folder, body, lambda m, d, body=body: (hair.bald_base(m, d, body), set()))
            jobs.append((folder, body, f"{RIG[body]}_bald"))
            for style_id, _, _ in hair.STYLES[body]:
                if wanted and style_id not in wanted:
                    continue
                folder = os.path.join(scratch, f"{body}_{style_id}")
                write_bases(folder, body, lambda m, d, body=body, sid=style_id: hair.styled_base(m, d, body, sid))
                jobs.append((folder, body, f"{RIG[body]}_{style_id}"))
        with ThreadPoolExecutor(a.jobs) as pool:
            # pass 1: every pose set rolls through the dodge freely; one shared motion per body comes out of it
            # the bald bodies spin freely; the hairstyles spin about the same centres so their landings are comparable
            free = {name: pool.submit(measure, folder, body, a.out_dir, name) for folder, body, name in jobs
                    if name.endswith("_bald")}
            for body in a.bodies.split(","):
                spin = {k: v for k, v in free[f"{RIG[body]}_bald"].result().items()
                        if not (k.endswith("/land") or k.endswith("/reland"))}
                with open(os.path.join(a.out_dir, f"{RIG[body]}_dodge_spin.json"), "w") as fh:
                    json.dump(spin, fh)
            free.update({name: pool.submit(measure, folder, body, a.out_dir, name,
                                           os.path.join(a.out_dir, f"{RIG[body]}_dodge_spin.json"))
                         for folder, body, name in jobs if not name.endswith("_bald")})
            for body in a.bodies.split(","):
                bald = free[f"{RIG[body]}_bald"].result()
                styles = [f.result() for n, f in free.items() if n.startswith(RIG[body] + "_") and not n.endswith("_bald")]
                with open(os.path.join(a.out_dir, f"{RIG[body]}_dodge_motion.json"), "w") as fh:
                    json.dump(shared_motion(bald, styles), fh)
                for anim in ANIMS[:-1]:  # idle, walk and run have no whole-figure moves
                    with open(os.path.join(a.out_dir, f"{RIG[body]}_{anim}_motion.json"), "w") as fh:
                        json.dump({}, fh)
            # pass 2: everything, replaying the shared motion
            futures = {(name, anim): pool.submit(animate(folder, body, a.out_dir, name), anim)
                       for folder, body, name in jobs for anim in ANIMS}
            for (name, anim), fut in futures.items():
                report[f"{name} {anim}"] = fut.result()[1]
    failures = [k for k, v in report.items() if v != "all 64 frames pass"]
    for k, v in report.items():
        print(f"audit {k}: {v}")

    import walk_cycle as W
    for body in a.bodies.split(","):
        rig = RIG[body]
        for style_id, _, _ in hair.STYLES[body]:
            if wanted and style_id not in wanted:
                continue
            frames, lost_total, split = [], 0, 0
            for anim in ANIMS:
                styled = Image.open(os.path.join(a.out_dir, f"{rig}_{style_id}_{anim}.png")).convert("RGBA")
                bald = Image.open(os.path.join(a.out_dir, f"{rig}_bald_{anim}.png")).convert("RGBA")
                classes = Image.open(os.path.join(a.out_dir, f"{rig}_{style_id}_{anim}_classes.png"))
                lay, cls, lost = layer(styled, bald, classes)
                lost_total += lost
                lay.save(os.path.join(a.out_dir, f"{rig}_{style_id}_{anim}_layer.png"))
                for r in range(8):
                    for f in range(FRAMES):
                        box = (f * CELL, r * CELL, (f + 1) * CELL, (r + 1) * CELL)
                        cell, ccell = lay.crop(box), cls.crop(box)
                        # what the game draws: the bald body with the hair layer on top; it may not have more
                        # pieces, holes or gaps than the styled frame it stands in for
                        shown = bald.crop(box)
                        shown.alpha_composite(cell)
                        whole = styled.crop(box)
                        # a bald-only nub can close one more notch than the styled art had; allow one per nub
                        nubs = sum(1 for yy in range(CELL) for xx in range(CELL)
                                   if bald.getpixel((box[0] + xx, box[1] + yy))[3] and not whole.getpixel((xx, yy))[3])
                        if (len(W.pieces(shown)) != 1 or len(W.holes(shown)) > len(W.holes(whole))
                                or len(W.interior_gaps(shown)) > len(W.interior_gaps(whole)) + nubs):
                            split += 1
                        bb = cell.getbbox()
                        if bb:
                            frames.append((cell.crop(bb), ccell.crop(bb), (bb[0], bb[1])))
                        else:
                            frames.append((Image.new("RGBA", (0, 0)), Image.new("L", (0, 0)), (0, 0)))
            atlas, catlas, rects = pack(frames)
            atlas.save(os.path.join(a.out_dir, f"hair_{rig}_{style_id}.png"))
            catlas.save(os.path.join(a.out_dir, f"hair_{rig}_{style_id}_classes.png"))
            with open(os.path.join(a.out_dir, f"hair_{rig}_{style_id}.json"), "w") as fh:
                json.dump({"size": atlas.size, "rects": rects}, fh)
            preview(a.out_dir, body, style_id, os.path.join(a.out_dir, f"preview_{rig}_{style_id}.gif"))
            # lost: pixels the bald body shows that the styled art had trimmed (single outline nubs at the hair edge)
            print(f"{rig} {style_id}: atlas {atlas.size}, bald-only pixels {lost_total}, composite frames failing {split}")
            if split:
                failures.append(f"{rig} {style_id}")
    if failures:
        print("FAILED:", ", ".join(failures))
        sys.exit(1)
    print("all hairstyles pass")


SRC_MALE = None

if __name__ == "__main__":
    main()
