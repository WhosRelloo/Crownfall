"""Audit a walk sheet built by walk_cycle.py: every frame must have whole boots, feet on the ground line,
no holes or gaps inside the outline, nothing touching a cell edge, and parts the same size as the base pose.

python Tools/walk_audit.py <src_dir> <sheet.png> [walk|run|dodge|idle] [prefix] [motion.json]   (exit code 1 on failure)
prefix: the base-pose file prefix, cf_human_m_full_rags_walk (default) or cf_human_f_full_rags_walk
motion: optional; the recorded whole-figure moves the sheet was built with (Tools/hair_build.py)
"""
import sys
from PIL import Image
import walk_cycle as W


def main():
    src, path = sys.argv[1], sys.argv[2]
    W.STYLE = W.STYLES[sys.argv[3] if len(sys.argv) > 3 else "walk"]
    W.SRC["dir"] = src
    W.SRC["prefix"] = sys.argv[4] if len(sys.argv) > 4 else "cf_human_m_full_rags_walk"
    if len(sys.argv) > 5:  # the motion the sheet was built with (walk_cycle.py --motion-in / --motion-out)
        import json
        with open(sys.argv[5]) as fh:
            W.MOTION["fixed"] = json.load(fh)
    rolling = bool(W.STYLE.get("roll_seq"))  # a roll spins the body: boots and height can't be fixed checks
    lift_room = 3 if W.STYLE["airborne"] else 1  # flight frames lift both feet
    sheet = Image.open(path)
    fails = []
    for r, d in enumerate(W.ROWS):
        source = W.MIRROR.get(d, d)  # mirrored rows are checked against their flipped source
        base = W.pivoted(f"{src}/{W.SRC['prefix']}_{W.LABEL_FOR[source]}_frame01.png")
        base_h = base.getbbox()[3] - base.getbbox()[1]
        for f in range(8):
            W.frame(base, source, f)  # rebuild to learn where each boot pixel should be
            boots = [set(b) for b in W.LAST_BOOTS]
            if source != d:
                boots = [{(2 * W.PIVOT[0] - x, y) for x, y in b} for b in boots]
                flipped = {(2 * W.PIVOT[0] - x, y) for x, y in W.LAST_BLADE}
                W.LAST_BLADE.clear()
                W.LAST_BLADE.update(flipped)
            fr = sheet.crop((f * 96, r * 96, f * 96 + 96, r * 96 + 96)).copy()
            px = fr.load()
            tag = f"{d} frame {f + 1}"
            for k, boot in enumerate([] if rolling else boots):
                missing = [p for p in boot if not (0 <= p[0] < 96 and 0 <= p[1] < 96) or not px[p][3]]
                if missing:
                    fails.append(f"{tag}: boot {k + 1} missing {len(missing)} px")
            b = fr.getbbox()
            if b[0] <= 1 or b[1] <= 1 or b[2] >= 95 or b[3] >= 95:
                fails.append(f"{tag}: touches the cell edge {b}")
            # Three-quarter views stand the far foot 1 px higher (1 px allowed); runs also have flight frames.
            room = 6 if f in W.STYLE["airborne"] else lift_room  # airborne frames: both feet are up
            if rolling:
                # with a hairstyle-shared landing (motion file) a roll may sit up to 2 px higher, so no hair dips below
                room = W.STYLE["lift_seq"][f] + (2 if W.MOTION["fixed"] else 0)
            if not (W.PIVOT[1] - 1 - room <= b[3] - 1 <= W.PIVOT[1] - 1):
                fails.append(f"{tag}: lowest pixel on row {b[3] - 1}, ground line is {W.PIVOT[1] - 1}")
            h = b[3] - b[1]
            # A forward lean tips the head lower without changing any part's size.
            lean_room = 2 + (4 if W.STYLE["lean_deg"] else 0)
            if not rolling and not (base_h - lean_room <= h <= base_h + 4):
                fails.append(f"{tag}: height {h} vs base {base_h}")
            if W.holes(fr):
                fails.append(f"{tag}: {len(W.holes(fr))} enclosed specks")
            if W.interior_gaps(fr):
                fails.append(f"{tag}: {len(W.interior_gaps(fr))} gaps inside the outline")
    print("\n".join(fails) if fails else "all 64 frames pass")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
