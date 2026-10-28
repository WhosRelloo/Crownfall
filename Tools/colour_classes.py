"""Colour classes for character customization.

Every opaque pixel of a base drawing gets a class: what the game may recolour it as. The animation tool
(Tools/walk_cycle.py --classes) carries the class through every move in the alpha byte, so each finished
sheet gets a class map that lines up with it pixel for pixel. Tools/class_maps.py packs the maps for the game.
"""
import colorsys

# Class ids, as stored in the game data (0 = transparent). Keep in sync with Shared/Appearance.luau.
OUTLINE, STEEL, SKIN, HAIR, OUTFIT, BOOTS = 1, 2, 3, 4, 5, 6
NAMES = {OUTLINE: "outline", STEEL: "steel", SKIN: "skin", HAIR: "hair", OUTFIT: "outfit", BOOTS: "boots"}

OUTLINE_LUM = 12  # near-black line work stays as drawn
HAIR_DEPTH = 5  # rows below the drawing's hair line still counted as head (hair falls past the crown)
SKIN_DEPTH = 12  # skin shows on the face and neck down to here, and on the arms; orange below is rag highlight
BOOT_HEIGHT = 14  # rows above the soles that count as boot


def lum(c):
    return 0.3 * c[0] + 0.59 * c[1] + 0.11 * c[2]


def hsv(c):
    return colorsys.rgb_to_hsv(c[0] / 255, c[1] / 255, c[2] / 255)


def is_skin(c):
    h, s, v = hsv(c)
    return 0.02 <= h <= 0.11 and s > 0.35 and lum(c) > 70


def classify(base, labels, hair_row, hip, extra_hair=frozenset()):
    """base: pivoted RGBA drawing; labels: walk_cycle.split() output; extra_hair: pixels known to be hair below
    the hair line (long hair); returns {(x, y): class id}."""
    px = base.load()
    bottom = max(y for (x, y) in labels)
    out = {}
    for (x, y), lab in labels.items():
        c = px[x, y]
        if isinstance(lab, tuple) and lab[0] == "sword":
            out[(x, y)] = STEEL
        elif lum(c) < OUTLINE_LUM:
            out[(x, y)] = OUTLINE
        elif is_skin(c) and (y < hair_row + SKIN_DEPTH or (isinstance(lab, tuple) and lab[0] == "arm")):
            out[(x, y)] = SKIN
        elif y < hair_row + HAIR_DEPTH or (x, y) in extra_hair:
            out[(x, y)] = HAIR
        elif y >= hip and y > bottom - BOOT_HEIGHT and hsv(c)[1] > 0.45:
            out[(x, y)] = BOOTS
        else:
            out[(x, y)] = OUTFIT
    return out


def tag(base, classes):
    """Store each pixel's class in its alpha byte (255 - id). Every check in the tool reads alpha only as
    opaque/transparent, and its colour tests ignore alpha, so the moves are unchanged."""
    px = base.load()
    for (x, y), k in classes.items():
        c = px[x, y]
        px[x, y] = (c[0], c[1], c[2], 255 - k)
    return base


def untag(im):
    """Split a tagged frame or sheet into (normal RGBA image, {(x, y): class id})."""
    im = im.copy()
    px = im.load()
    classes = {}
    for y in range(im.height):
        for x in range(im.width):
            c = px[x, y]
            if c[3]:
                classes[(x, y)] = 255 - c[3]
                px[x, y] = (c[0], c[1], c[2], 255)
    return im, classes
