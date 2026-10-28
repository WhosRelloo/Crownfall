"""Hairstyles (Docs/Plans/2026-10-28-class-origin-traits-hair.md, section 5).

Every body is drawn bald, and each hairstyle is a separate layer drawn over it:
  bald base  = the body's base pose with the hair painted out (BALD overlays: scalp, ears, brows)
  styled     = the bald base with a hairstyle's overlay painted on (or, for the original styles, the original art)
Both are animated by Tools/walk_cycle.py; a hairstyle's layer is every pixel where the styled frames differ from the
bald ones, so bald + layer reproduces the styled frame exactly. Tools/hair_build.py packs the layers into atlases.

Overlay maps use Tools/female.py's characters (1-6 hair, o outline, a-f skin, r brow, x erase, ...).
"""
import os

from PIL import Image

import female

DRAWN = ["S", "SW", "W", "NW", "N"]  # the east side is mirrored by walk_cycle.py

# The bald head, shared by both bodies (the female head is the male one). Pivoted coordinates.
BALD = {
    "S": (43, 28, [
        "xxxxxxxxxxxxxx",  # 28
        "xxxxooooooxxxx",  # 29
        "xxobaabbcceoxx",  # 30
        "xobaabbbcceeox",  # 31
        "xobbbbbccceeox",  # 32
        "xocbbbccccefox",  # 33
        "xoccccccceefox",  # 34
        "xoecrrccrrefox",  # 35
        "oeecc.bc.ceeeo",  # 36
        "oeee.....ceeeo",  # 37
        "xoee.......eox",  # 38
        "xx.f......oxxx",  # 39
        "xxof......foxx",  # 40
    ]),
    "SW": (41, 27, [
        "xxxxxxxxxxxxxxxxx",  # 27
        "xxxxxxoooooxxxxxx",  # 28
        "xxxxobaabbccoxxxx",  # 29
        "xxxobaabbbcceoxxx",  # 30
        "xxxobbabbcceeoxxx",  # 31
        "xxobbbbbccceefoxx",  # 32
        "xxocbbbcccceffoxx",  # 33
        "xxoccccccceeffoxx",  # 34
        "xxoecrrcccreefoxx",  # 35
        "xxoecc.cbc.eefoxx",  # 36
        "xxxo.e.e...eeoxxx",  # 37
        ".........efo.....",  # 38
        "..........efox...",  # 39
        ".........efoxxx..",  # 40
    ]),
    "W": (42, 30, [
        "xxxxxxxxxxxxxxxx",  # 30
        "xxxxxoooooxxxxxx",  # 31
        "xxxobaabbccoxxxx",  # 32
        "xxobaabbbcceoxxx",  # 33
        "xxobbbbbcceeoxxx",  # 34
        "xxobbbcccceefoxx",  # 35
        "xxocbcccceeffoxx",  # 36
        "xxocrcccefeefoxx",  # 37
        "xxocccce.fefoxxx",  # 38
        "xxoc....efefoxxx",  # 39
        "...c.....efo....",  # 40
    ]),
    "NW": (42, 29, [
        "xxxxxxxxxxxxxxxx",  # 29
        "xxxxxooooooxxxxx",  # 30
        "xxxobaabbcceoxxx",  # 31
        "xxobabbbccceeoxx",  # 32
        "xobbbbcccceefoxx",  # 33
        "xocbbbcccceffoxx",  # 34
        "ofccccccceeffoxx",  # 35
        "ofeccccccefffoxx",  # 36
        "xoeecccceeffoxxx",  # 37
        "xxoeeccceffoxxxx",  # 38
        "..xxofeeefox....",  # 39
    ]),
    "N": (42, 27, [
        "xxxxxxxxxxxxxxxx",  # 27
        "xxxxooooooxxxxxx",  # 28
        "xxxobaabbcoxxxxx",  # 29
        "xxobaabbbccoxxxx",  # 30
        "xobbabbbccceoxxx",  # 31
        "xobbbbbcccceoxxx",  # 32
        "xocbbbccccefoxxx",  # 33
        "ofccccccceeffoxx",  # 34
        "ofeccccccefffoxx",  # 35
        "xoeecccceeffoxxx",  # 36
        "xxoeeccceffoxxxx",  # 37
        "xxxofeeeefoxxxxx",  # 38
    ]),
}


def check_overlays():
    for d, (x0, y0, rows) in BALD.items():
        widths = {len(r) for r in rows}
        assert len(widths) == 1, f"BALD {d}: rows of different widths {widths}"


def bald_base(male_base, direction, body):
    """A pivoted base pose with the hair painted out. body 'f' also gets the female body changes (not her hair)."""
    base = male_base.copy()
    if body == "f" and direction in female.OVERLAYS:
        base = female.paint(base, female.body_overlay(direction), seed=0)
    return female.paint(base, BALD[direction], seed=1)


def main():
    import sys
    import walk_cycle as W

    check_overlays()
    src, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    sheet = Image.new("RGBA", (96 * 5, 96 * 2), (70, 74, 70, 255))
    for i, d in enumerate(DRAWN):
        male = W.pivoted(f"{src}/cf_human_m_full_rags_walk_{W.LABEL_FOR[d]}_frame01.png")
        for k, body in enumerate("mf"):
            b = bald_base(male, d, body)
            b.save(os.path.join(out, f"bald_{body}_{d}.png"))
            sheet.alpha_composite(b, (i * 96, k * 96))
    sheet.save(os.path.join(out, "bald_preview.png"))
    print("wrote", out)


if __name__ == "__main__":
    main()


# Hairstyles: body -> ordered list of (id, name, overlays). overlays is "original" for the hair the body was first
# drawn with (male Messy, female Long), or a direction -> (X, Y, rows) map painted on the bald base. Hair overlays
# never erase: the styled frame must cover the bald one, so the hair layer alone adds the hair.
STYLES = {
    "m": [
        ("messy", "Messy", "original"),
        ("cropped", "Cropped", {
            "S": (43, 28, [
                "....o.o.o.....",
                "...o343432o...",
                "..o23454332o..",
                ".o2344543322o.",
                ".o1233433221o.",
                ".o12.2..2.21o.",
                ".o1........1o.",
            ]),
            "SW": (42, 27, [
                ".....o.o.o......",
                "....o34343o.....",
                "...o2345443o....",
                "..o234454332o...",
                "..o123443322o...",
                ".o12.2..22321o..",
                ".o1......1221o..",
                "..........121o..",
            ]),
            "W": (42, 30, [
                "......o.o.o.....",
                "....o343432o....",
                "...o23454432o...",
                "..o2344543322o..",
                "..o2123343322o..",
                "....212333222o..",
                ".......123322o..",
                "...........21o..",
            ]),
            "NW": (42, 29, [
                ".....o.o.o......",
                "....o343432o....",
                "...o23454432o...",
                "..o2344543322o..",
                ".o22344433222o..",
                ".o12233333221o..",
                "..11222222211o..",
                "...111111111....",
                "....1.1.1.1.....",
            ]),
            "N": (42, 27, [
                "....o.o.o.......",
                "...o343432o.....",
                "..o23454432o....",
                "..o23344332o....",
                ".o2334433322o...",
                ".o2233333221o...",
                ".o1223332211o...",
                "..1122222211....",
                "...11111111.....",
                "...1.1.1.1......",
            ]),
        }),
    ],
    "f": [
        ("long", "Long", "original"),
        ("ponytail", "Ponytail", {
            "S": (43, 29, [
                "....oooooo....",
                "..o34566543o..",
                ".o2455654432o.",
                ".o2345543322o.",
                ".o2234432221o.",
                ".o2321..1232o.",
                ".o21......12o.",
                ".o1........1o.",
                "..o........o..",
            ]),
            "SW": (42, 28, [
                ".....ooooo......",
                "...o4556543o....",
                "..o245665432o...",
                "..o234554332o...",
                ".o22344432221o..",
                ".o21.....1232oo.",
                ".o1.......1213o.",
                "..o........1o4o.",
                "............o43o",
                ".............43o",
                ".............43o",
                ".............3o.",
                ".............o..",
            ]),
            "W": (42, 31, [
                ".....ooooo.......",
                "...o4556543o.....",
                "..o245665432o....",
                "..o234554332ooo..",
                "..o123443322213o.",
                "....o12333222143o",
                "......o123322243o",
                "...........21253o",
                "............o243o",
                ".............o43o",
                ".............o42o",
                ".............o53o",
                ".............o43o",
                ".............o32o",
                "..............o3o",
                "...............o.",
            ]),
            "NW": (42, 30, [
                ".....oooooo.....",
                "...o45566543o...",
                "..o2456654322o..",
                ".o23455443222o..",
                ".o22344432222o..",
                "..o1223443221o..",
                "...o1234321o....",
                "......o1111o....",
                "......o3443o....",
                "......o3453o....",
                "......o2443o....",
                "......o3453o....",
                ".......o43o.....",
                ".......o42o.....",
                ".......o33o.....",
                "........oo......",
            ]),
            "N": (42, 28, [
                "....oooooo......",
                "...o455654o.....",
                "..o24566543o....",
                ".o2345543322o...",
                ".o2334433222o...",
                ".o2233432221o...",
                "..1223443221....",
                "..o12344321o....",
                "...o123321o.....",
                "....o1111o......",
                "....o3443o......",
                "....o3453o......",
                "....o2443o......",
                "....o3453o......",
                "....o2442o......",
                ".....o43o.......",
                ".....o42o.......",
                ".....o33o.......",
                "......oo........",
            ]),
        }),
    ],
}


def style(body, style_id):
    for entry in STYLES[body]:
        if entry[0] == style_id:
            return entry
    raise KeyError(f"no hairstyle {style_id!r} for body {body!r}")


def styled_base(male_base, direction, body, style_id):
    """A pivoted base pose wearing a hairstyle, and the set of its hair pixels (for the colour classes; None means
    the drawing's own hair line decides, as for the original male art)."""
    _, _, overlays = style(body, style_id)
    if overlays == "original":
        # the art as first drawn, laid over the bald head so the styled pose always covers the bald one
        # (an ear or the crown can peek out where the original outline was tighter)
        if body == "m":
            art, hair_px = male_base.copy(), None
        else:
            art = female.paint(male_base.copy(), female.OVERLAYS[direction], seed=0) if direction in female.OVERLAYS else male_base.copy()
            hair_px = female.hair_pixels(direction)
        under = bald_base(male_base, direction, body)
        under.alpha_composite(art)
        return under, hair_px
    x0, y0, rows = overlays[direction]
    assert not any("x" in r for r in rows), f"{style_id} {direction}: hair overlays never erase"
    assert len({len(r) for r in rows}) == 1, f"{style_id} {direction}: rows of different widths"
    hair = {(x0 + dx, y0 + dy) for dy, r in enumerate(rows) for dx, ch in enumerate(r) if ch in female.HAIR_TONES}
    return female.paint(bald_base(male_base, direction, body), overlays[direction], seed=7), hair
