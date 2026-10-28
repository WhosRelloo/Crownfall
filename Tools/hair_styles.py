"""Hairstyles drawn as silhouettes and shaded by Tools/hair_gen.py (the hand-painted ones live in Tools/hair.py).

Each style is a function (direction, bald image) -> overlay (X, Y, rows) for Tools/female.py's painter.
Silhouettes are pivoted coordinates over the bald head; hair_gen.CAP is the scalp a short cut covers.

Which way each view faces: S front; SW front three-quarter facing screen-left; W profile facing screen-left (the
character's left side toward the camera); NW back three-quarter; N back. The east side is mirrored from the west.
Hair is kept out of the arm regions of Tools/walk_cycle.py PARTS (it would swing with the arm) and off the face.
"""
from hair_gen import CAP, cap, grid, merge, shade

DIRS = ("S", "SW", "W", "NW", "N")

# Face pixels hair must never cover (eyes, nose, mouth, cheeks), per view; back views have none.
FACE = {
    "S": {(x, y) for x in range(46, 54) for y in range(36, 41)} | {(x, 35) for x in range(47, 53)},
    "SW": {(x, y) for x in range(44, 52) for y in range(35, 41)},
    "W": {(x, y) for x in range(43, 50) for y in range(36, 42)},
    "NW": set(),
    "N": set(),
}


def spans(rows, kind="#"):
    """[(y, x0, x1), ...] -> silhouette (x0..x1 inclusive)."""
    return {(x, y): kind for y, x0, x1 in rows for x in range(x0, x1 + 1)}


def top_rows(direction, n, kind="#"):
    """The first n rows of the short-cut scalp."""
    x0, y0, rows = CAP[direction]
    return {p: kind for p in grid(x0, y0, rows[:n])}


def fluff(sil, direction, seed, reach=1):
    """Bumpy volume: pixels just outside the silhouette's top and sides join it here and there."""
    out = dict(sil)
    face = FACE[direction]
    for _ in range(reach):
        add = {}
        for (x, y), k in out.items():
            if k != "#":
                continue
            for dx, dy in ((-1, 0), (1, 0), (0, -1), (-1, -1), (1, -1)):
                p = (x + dx, y + dy)
                if p not in out and p not in face and ((p[0] * 31 + p[1] * 17 + seed) % 3) != 0:
                    add[p] = "#"
        out.update(add)
    return out


def clear_face(sil, direction):
    return {p: k for p, k in sil.items() if p not in FACE[direction]}


def style(texture, light=0.0, **parts):
    def draw(direction, bald):
        return shade(clear_face(parts[direction](), direction), bald, texture, light)
    return draw


def each(fn):
    return {d: (lambda d=d: fn(d)) for d in DIRS}


# ===================================================================================================== male =======

BUZZ = style("smooth", light=-0.9, **each(lambda d: {p: ("#" if (p[0] * 7 + p[1] * 3) % 3 == 0 else "s")
                                                      for p in cap(d)}))

SHAVED = style("smooth", **each(lambda d: cap(d, "s")))

MOHAWK = style("straight", light=0.3,
    S=lambda: merge(cap("S", "s"), spans([(25, 48, 49), (26, 47, 50), (27, 47, 50), (28, 47, 50), (29, 47, 50),
                                         (30, 47, 50), (31, 47, 50), (32, 47, 50), (33, 48, 49)])),
    SW=lambda: merge(cap("SW", "s"), spans([(24, 48, 49), (25, 47, 49), (26, 46, 49), (27, 46, 49), (28, 46, 49),
                                           (29, 46, 49), (30, 46, 49), (31, 46, 49), (32, 47, 49)])),
    W=lambda: merge(cap("W", "s"), spans([(25, 48, 48), (25, 51, 51), (25, 54, 54), (26, 47, 48), (26, 50, 52),
                                          (26, 54, 55), (27, 46, 55), (28, 46, 55), (29, 45, 56), (30, 46, 55),
                                          (31, 47, 54)])),
    NW=lambda: merge(cap("NW", "s"), spans([(26, 48, 50), (27, 47, 50), (28, 46, 50), (29, 46, 50), (30, 46, 50),
                                           (31, 47, 50), (32, 47, 50), (33, 47, 50), (34, 47, 50), (35, 48, 50),
                                           (36, 48, 50)])),
    N=lambda: merge(cap("N", "s"), spans([(24, 47, 48), (25, 46, 49), (26, 46, 49), (27, 46, 49), (28, 46, 49),
                                          (29, 46, 49), (30, 46, 49), (31, 46, 49), (32, 46, 49), (33, 46, 49),
                                          (34, 46, 49), (35, 46, 49), (36, 47, 48)])),
)

# Undercut: long top swept over, the sides and back shaved.
UNDERCUT = style("straight", light=0.2,
    S=lambda: merge(cap("S", "s"), top_rows("S", 4), spans([(27, 48, 52), (28, 46, 53), (33, 44, 47), (34, 45, 47),
                                                            (35, 46, 46)])),
    SW=lambda: merge(cap("SW", "s"), top_rows("SW", 4), spans([(26, 48, 51), (27, 46, 52), (32, 44, 47),
                                                              (33, 44, 46), (34, 45, 45)])),
    W=lambda: merge(cap("W", "s"), top_rows("W", 4), spans([(29, 47, 54), (30, 45, 55), (33, 43, 45), (34, 43, 44),
                                                           (35, 43, 43)])),
    NW=lambda: merge(cap("NW", "s"), top_rows("NW", 4), spans([(28, 47, 52), (29, 46, 54)])),
    N=lambda: merge(cap("N", "s"), top_rows("N", 4), spans([(26, 46, 50), (27, 45, 52)])),
)

# Swept back: no fringe, a high forehead, length to the nape.
SWEPT_S = [(28, 46, 53), (29, 45, 54), (30, 44, 55), (31, 44, 55), (32, 44, 55), (33, 44, 45), (33, 54, 55),
           (34, 44, 45), (34, 54, 55), (35, 44, 44), (35, 55, 55)]
SWEPT_SW = [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 43, 55), (32, 43, 44), (32, 51, 55),
            (33, 43, 43), (33, 52, 56), (34, 52, 55), (35, 52, 54)]
SWEPT_W = [(30, 46, 51), (31, 44, 53), (32, 43, 54), (33, 43, 55), (34, 44, 56), (35, 46, 56), (36, 49, 56),
           (37, 51, 56), (38, 53, 56), (39, 54, 55)]
SWEPT_NW = [(29, 47, 52), (30, 45, 54), (31, 44, 55), (32, 43, 56), (33, 43, 56), (34, 43, 56), (35, 44, 56),
            (36, 44, 55), (37, 45, 54), (38, 46, 53), (39, 47, 52)]
SWEPT_N = [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 43, 54), (32, 43, 54), (33, 43, 54),
           (34, 44, 53), (35, 44, 53), (36, 45, 52), (37, 45, 52), (38, 46, 51)]
SWEPT = {"S": SWEPT_S, "SW": SWEPT_SW, "W": SWEPT_W, "NW": SWEPT_NW, "N": SWEPT_N}

SWEPT_BACK = style("straight", light=0.2, **each(lambda d: spans(SWEPT[d])))

# Long loose: to the shoulders, parted in the middle.
LONG_S = [(28, 46, 53), (29, 45, 54), (30, 44, 55), (31, 43, 56), (32, 43, 56), (33, 43, 56), (34, 43, 46),
          (34, 53, 56), (35, 43, 45), (35, 54, 56), (36, 43, 45), (36, 54, 56), (37, 43, 45), (37, 54, 56),
          (38, 43, 45), (38, 54, 56), (39, 43, 45), (39, 54, 56), (40, 44, 45), (40, 54, 55), (41, 44, 45),
          (41, 54, 55), (42, 44, 44), (42, 55, 55)]
LONG_SW = [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 42, 55), (32, 42, 56), (33, 42, 44),
           (33, 50, 56), (34, 42, 43), (34, 51, 56), (35, 42, 43), (35, 52, 56), (36, 42, 43), (36, 52, 56),
           (37, 42, 43), (37, 52, 56), (38, 43, 43), (38, 51, 56), (39, 51, 56), (40, 51, 55), (41, 52, 55),
           (42, 53, 54)]
LONG_W = [(30, 46, 51), (31, 44, 53), (32, 43, 54), (33, 43, 55), (34, 43, 56), (35, 44, 56), (36, 45, 56),
          (37, 48, 56), (38, 48, 56), (39, 49, 56), (40, 49, 56), (41, 50, 56), (42, 51, 56), (43, 52, 55)]
LONG_NW = [(29, 47, 52), (30, 45, 54), (31, 44, 55), (32, 43, 56), (33, 42, 56), (34, 42, 56), (35, 42, 56),
           (36, 43, 56), (37, 43, 56), (38, 44, 56), (39, 44, 55), (40, 45, 54), (41, 45, 54), (42, 46, 53),
           (43, 47, 52)]
LONG_N = [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 42, 55), (32, 42, 55), (33, 41, 56),
          (34, 41, 56), (35, 41, 56), (36, 42, 55), (37, 42, 55), (38, 42, 55), (39, 43, 54), (40, 43, 54),
          (41, 44, 53), (42, 45, 52)]
LONG = {"S": LONG_S, "SW": LONG_SW, "W": LONG_W, "NW": LONG_NW, "N": LONG_N}

LONG_LOOSE = style("straight", **each(lambda d: spans(LONG[d])))

# Tied back: swept back with a short tail at the nape.
TAIL = {
    "S": [],
    "SW": [(33, 55, 55, "t"), (34, 55, 56), (35, 55, 56), (36, 55, 56), (37, 56, 56)],
    "W": [(35, 55, 56, "t"), (36, 55, 57), (37, 55, 57), (38, 56, 57), (39, 56, 57), (40, 57, 57)],
    "NW": [(38, 48, 51, "t"), (39, 48, 51), (40, 48, 51), (41, 49, 51), (42, 49, 50), (43, 50, 50)],
    "N": [(37, 47, 50, "t"), (38, 47, 50), (39, 47, 50), (40, 48, 49), (41, 48, 49), (42, 48, 48)],
}


def tail_spans(rows):
    out = {}
    for r in rows:
        kind = r[3] if len(r) > 3 else "#"
        out.update(spans([r[:3]], kind))
    return out


TIED_BACK = style("straight", light=0.2, **each(lambda d: merge(spans(SWEPT[d]), tail_spans(TAIL[d]))))

# Topknot: shaved sides, a knot on the crown.
KNOT = {"S": (47, 24), "SW": (46, 23), "W": (49, 26), "NW": (48, 25), "N": (46, 23)}


def knot(d):
    x, y = KNOT[d]
    return merge(spans([(y, x + 1, x + 2), (y + 1, x, x + 3), (y + 2, x, x + 3)]), spans([(y + 3, x + 1, x + 2)], "t"))


TOPKNOT = style("straight", light=0.1, **each(lambda d: merge(cap(d, "s"), top_rows(d, 2), knot(d))))

# Braids: cornrows over the scalp and two short plaits at the back.
PLAITS = {
    "S": [],
    "SW": [(34, 54, 55), (35, 54, 55), (36, 54, 55), (37, 55, 55, "t")],
    "W": [(36, 53, 54), (37, 53, 54), (38, 53, 54), (39, 53, 54), (40, 54, 54), (41, 53, 54), (42, 54, 54, "t")],
    "NW": [(37, 46, 47), (37, 51, 52), (38, 46, 47), (38, 51, 52), (39, 46, 47), (39, 51, 52), (40, 47, 47),
           (40, 52, 52), (41, 46, 47), (41, 51, 52), (42, 47, 47, "t"), (42, 52, 52, "t")],
    "N": [(36, 45, 46), (36, 50, 51), (37, 45, 46), (37, 50, 51), (38, 45, 46), (38, 50, 51), (39, 46, 46),
          (39, 51, 51), (40, 45, 46), (40, 50, 51), (41, 46, 46, "t"), (41, 51, 51, "t")],
}
BRAIDS = style("braid", light=0.1, **each(lambda d: merge(cap(d), tail_spans(PLAITS[d]))))

# Curly: a bumpy crown of curls.
CURLY_M = style("curly", light=0.3, **each(lambda d: fluff(cap(d), d, seed=3, reach=2)))

MALE = [
    ("swept_back", "Swept Back", SWEPT_BACK),
    ("long_loose", "Long Loose", LONG_LOOSE),
    ("tied_back", "Tied Back", TIED_BACK),
    ("mohawk", "Mohawk", MOHAWK),
    ("shaved", "Shaved", SHAVED),
]
# Drawn but held back until they read better in every view (owner: "5 more styles for now, then expand later").
PARKED_MALE = [("undercut", "Undercut", UNDERCUT), ("topknot", "Topknot", TOPKNOT), ("braids", "Braids", BRAIDS),
               ("buzz", "Buzz", BUZZ), ("curly", "Curly", CURLY_M)]

# =================================================================================================== female =======

# A fuller, smoother scalp for the female cuts: the long-hair silhouettes' crowns.
def crown(d, rows=7):
    return spans([r for r in LONG[d] if r[0] < LONG[d][0][0] + rows])


HIGH_TAIL = {
    "S": [(25, 48, 49), (26, 48, 49), (27, 47, 50, "t"), (28, 47, 50)],
    "SW": [(24, 48, 49), (25, 48, 50), (26, 47, 50, "t"), (27, 48, 51), (28, 54, 55), (29, 55, 56), (30, 55, 56),
           (31, 55, 56), (32, 55, 56), (33, 55, 56), (34, 55, 56), (35, 56, 56)],
    "W": [(27, 51, 53, "t"), (28, 51, 54), (29, 52, 55), (30, 53, 56), (31, 54, 57), (32, 55, 57), (33, 55, 57),
          (34, 55, 57), (35, 55, 57), (36, 55, 57), (37, 55, 56), (38, 55, 56), (39, 56, 56)],
    "NW": [(26, 48, 51, "t"), (27, 48, 51), (28, 48, 51), (29, 48, 51), (30, 48, 51), (31, 48, 51), (32, 48, 51),
           (33, 48, 51), (34, 48, 51), (35, 48, 51), (36, 48, 51), (37, 48, 51), (38, 49, 51), (39, 49, 50),
           (40, 49, 50), (41, 50, 50)],
    "N": [(25, 46, 49, "t"), (26, 46, 49), (27, 46, 49), (28, 46, 49), (29, 46, 49), (30, 46, 49), (31, 46, 49),
          (32, 46, 49), (33, 46, 49), (34, 46, 49), (35, 46, 49), (36, 46, 49), (37, 46, 49), (38, 47, 48),
          (39, 47, 48), (40, 47, 48), (41, 47, 47)],
}
HIGH_PONYTAIL = style("smooth", light=0.4, **each(lambda d: merge(crown(d), tail_spans(HIGH_TAIL[d]))))

BRAID_DOWN = {
    "S": [],
    "SW": [(34, 55, 56), (35, 55, 56), (36, 55, 56), (37, 55, 56), (38, 55, 56), (39, 56, 56)],
    "W": [(35, 54, 56), (36, 54, 56), (37, 54, 56), (38, 54, 56), (39, 54, 56), (40, 54, 56), (41, 54, 56),
          (42, 54, 56), (43, 55, 56), (44, 55, 56), (45, 55, 56), (46, 55, 56, "t"), (47, 55, 56), (48, 56, 56)],
    "NW": [(36, 48, 51), (37, 48, 51), (38, 48, 51), (39, 48, 51), (40, 48, 51), (41, 48, 51), (42, 49, 51),
           (43, 49, 51), (44, 49, 51), (45, 49, 50, "t"), (46, 49, 50), (47, 49, 50), (48, 50, 50)],
    "N": [(36, 46, 49), (37, 46, 49), (38, 46, 49), (39, 46, 49), (40, 46, 49), (41, 46, 49), (42, 46, 49),
          (43, 47, 48), (44, 47, 48), (45, 47, 48, "t"), (46, 47, 48), (47, 47, 48), (48, 47, 47)],
}
# the cap is smooth; only the plait carries the braid texture, so it's drawn as its own shaded layer
def _braid_style(cap_fn, braid, light=0.3):
    def draw(direction, bald):
        cap_ov = shade(clear_face(cap_fn(direction), direction), bald, "smooth", light)
        if not braid[direction]:
            return cap_ov
        braid_ov = shade(tail_spans(braid[direction]), bald, "braid", light)
        return _stack(cap_ov, braid_ov)
    return draw


def _stack(a, b):
    """Two overlays (X, Y, rows) -> one; b's non-'.' characters win."""
    cells = {}
    for x0, y0, rows in (a, b):
        for dy, row in enumerate(rows):
            for dx, ch in enumerate(row):
                if ch != ".":
                    cells[(x0 + dx, y0 + dy)] = ch
    xs = [p[0] for p in cells]
    ys = [p[1] for p in cells]
    x0, y0 = min(xs), min(ys)
    return (x0, y0, ["".join(cells.get((x, y), ".") for x in range(x0, max(xs) + 1)) for y in range(y0, max(ys) + 1)])


SINGLE_BRAID = _braid_style(crown, BRAID_DOWN)

TWIN = {
    "S": [(36, 43, 44), (37, 43, 44), (38, 43, 44), (39, 43, 44), (40, 43, 44), (41, 43, 44), (42, 43, 44),
          (43, 43, 44), (44, 43, 44), (45, 43, 44, "t"), (46, 43, 44), (47, 44, 44),
          (36, 55, 56), (37, 55, 56), (38, 55, 56), (39, 55, 56), (40, 55, 56), (41, 55, 56), (42, 55, 56),
          (43, 55, 56), (44, 55, 56), (45, 55, 56, "t"), (46, 55, 56), (47, 55, 55)],
    "SW": [(35, 42, 43), (36, 42, 43), (37, 42, 43), (38, 42, 43), (39, 42, 43), (40, 42, 43), (41, 42, 43),
           (42, 42, 43), (43, 42, 43, "t"), (44, 42, 43), (45, 43, 43),
           (36, 55, 56), (37, 55, 56), (38, 55, 56), (39, 55, 56), (40, 55, 56), (41, 55, 56), (42, 55, 56, "t"),
           (43, 56, 56)],
    "W": [(37, 53, 54), (38, 53, 54), (39, 53, 54), (40, 53, 54), (41, 53, 54), (42, 53, 54), (43, 53, 54),
          (44, 53, 54, "t"), (45, 53, 54), (46, 54, 54)],
    "NW": [(36, 43, 44), (37, 43, 44), (38, 43, 44), (39, 43, 44), (40, 43, 44), (41, 43, 44), (42, 43, 44, "t"),
           (43, 43, 43), (36, 53, 54), (37, 53, 54), (38, 53, 54), (39, 53, 54), (40, 53, 54), (41, 53, 54),
           (42, 53, 54, "t"), (43, 54, 54)],
    "N": [(36, 43, 44), (37, 43, 44), (38, 43, 44), (39, 43, 44), (40, 43, 44), (41, 43, 44), (42, 43, 44),
          (43, 43, 44, "t"), (44, 43, 43), (36, 53, 54), (37, 53, 54), (38, 53, 54), (39, 53, 54), (40, 53, 54),
          (41, 53, 54), (42, 53, 54), (43, 53, 54, "t"), (44, 54, 54)],
}
TWIN_BRAIDS = _braid_style(crown, TWIN)

# Bob: chin length, with bangs.
BOB = {
    "S": [(28, 46, 53), (29, 45, 54), (30, 44, 55), (31, 43, 56), (32, 43, 56), (33, 43, 56), (34, 43, 56),
          (35, 43, 46), (35, 53, 56), (36, 43, 45), (36, 54, 56), (37, 43, 45), (37, 54, 56), (38, 43, 45),
          (38, 54, 56), (39, 43, 45), (39, 54, 56), (40, 44, 45), (40, 54, 55)],
    "SW": [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 42, 55), (32, 42, 56), (33, 42, 56),
           (34, 42, 43), (34, 51, 56), (35, 42, 43), (35, 52, 56), (36, 42, 43), (36, 52, 56), (37, 42, 43),
           (37, 52, 56), (38, 43, 43), (38, 52, 56), (39, 52, 56), (40, 53, 55)],
    "W": [(30, 46, 51), (31, 44, 53), (32, 43, 54), (33, 42, 55), (34, 42, 56), (35, 42, 56), (36, 48, 56),
          (37, 50, 56), (38, 50, 56), (39, 50, 56), (40, 51, 55)],
    "NW": [(29, 47, 52), (30, 45, 54), (31, 44, 55), (32, 43, 56), (33, 42, 56), (34, 42, 56), (35, 42, 56),
           (36, 43, 56), (37, 43, 56), (38, 44, 55), (39, 44, 55), (40, 45, 54)],
    "N": [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 42, 55), (32, 42, 55), (33, 41, 56),
          (34, 41, 56), (35, 41, 56), (36, 42, 55), (37, 42, 55), (38, 42, 55), (39, 43, 54), (40, 44, 53)],
}
BOB_CUT = style("smooth", light=0.4, **each(lambda d: spans(BOB[d])))

# Bun: smooth hair gathered into a bun high at the back.
BUN = {
    "S": [(26, 47, 52), (27, 46, 53), (28, 47, 52, "t")],
    "SW": [(27, 53, 56), (28, 53, 57), (29, 53, 57), (30, 54, 56), (31, 54, 55, "t")],
    "W": [(31, 55, 58), (32, 55, 59), (33, 55, 59), (34, 55, 59), (35, 56, 58), (33, 55, 55, "t"), (34, 55, 55, "t")],
    "NW": [(31, 47, 52), (32, 46, 53), (33, 46, 53), (34, 46, 53), (35, 47, 52), (36, 48, 51, "t")],
    "N": [(30, 46, 50), (31, 45, 51), (32, 45, 51), (33, 45, 51), (34, 46, 50), (35, 46, 50, "t")],
}
BUN_STYLE = style("smooth", light=0.4, **each(lambda d: merge(crown(d), tail_spans(BUN[d]))))

# Pixie: short and textured, a long fringe swept to one side.
PIXIE_FRINGE = {
    "S": [(33, 48, 54), (34, 50, 54), (35, 52, 53)],
    "SW": [(32, 47, 53), (33, 48, 53), (34, 50, 52)],
    "W": [(33, 43, 46), (34, 43, 45), (35, 43, 44)],
    "NW": [],
    "N": [],
}
PIXIE = style("wavy", light=0.4, **each(lambda d: merge(fluff(cap(d), d, seed=5), spans(PIXIE_FRINGE[d]))))

# Side-swept: long hair brushed over to the character's left side.
SIDE = {
    "S": [(28, 46, 53), (29, 45, 54), (30, 44, 55), (31, 44, 56), (32, 44, 56), (33, 44, 56), (34, 47, 57),
          (35, 50, 57), (36, 44, 45), (36, 54, 57), (37, 44, 44), (37, 54, 57), (38, 54, 57), (39, 54, 57),
          (40, 54, 57), (41, 54, 57), (42, 54, 57), (43, 55, 57), (44, 55, 57), (45, 55, 56), (46, 56, 56)],
    "SW": [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 43, 55), (32, 44, 56), (33, 46, 56),
           (34, 51, 57), (35, 52, 57), (36, 52, 57), (37, 52, 57), (38, 52, 57), (39, 52, 57), (40, 53, 57),
           (41, 53, 57), (42, 54, 56), (43, 54, 56), (44, 55, 55)],
    "W": [(30, 46, 51), (31, 44, 53), (32, 43, 54), (33, 43, 55), (34, 43, 56), (35, 44, 56), (36, 45, 56),
          (37, 49, 56), (38, 49, 56), (39, 50, 56), (40, 50, 56), (41, 50, 56), (42, 51, 56), (43, 52, 56),
          (44, 53, 55)],
    "NW": [(29, 47, 52), (30, 45, 54), (31, 44, 55), (32, 43, 55), (33, 42, 55), (34, 42, 54), (35, 42, 53),
           (36, 42, 52), (37, 42, 50), (38, 42, 48), (39, 42, 47), (40, 42, 47), (41, 42, 46), (42, 43, 46),
           (43, 43, 45), (44, 44, 44)],
    "N": [(27, 46, 51), (28, 45, 52), (29, 44, 53), (30, 43, 54), (31, 42, 54), (32, 41, 54), (33, 41, 54),
          (34, 41, 53), (35, 41, 52), (36, 41, 51), (37, 41, 49), (38, 41, 47), (39, 41, 46), (40, 42, 46),
          (41, 42, 45), (42, 43, 45), (43, 43, 44)],
}
SIDE_SWEPT = style("straight", light=0.3, **each(lambda d: spans(SIDE[d])))

# Wavy: long hair past the shoulders, in waves.
def _longer(rows, extra):
    """Lengthen a long-hair silhouette by `extra` rows, narrowing toward the ends."""
    last_y = rows[-1][0]
    ends = [r for r in rows if r[0] == last_y]
    out = list(rows)
    for k in range(1, extra + 1):
        for _, x0, x1 in ends:
            shrink = k // 2
            if x1 - shrink >= x0 + shrink:
                out.append((last_y + k, x0 + shrink, x1 - shrink))
    return out


WAVY = style("wavy", light=0.3, **each(lambda d: fluff(spans(_longer(LONG[d], 4)), d, seed=9)))

# Shaved side: one side shaved, the other long and brushed over.
SHAVED_SIDE_STUBBLE = {
    "S": [(31, 44, 46), (32, 44, 46), (33, 44, 46), (34, 44, 45), (35, 44, 45)],
    "SW": [(31, 43, 45), (32, 43, 45), (33, 43, 44), (34, 43, 44)],
    "W": [],
    "NW": [(32, 52, 55), (33, 52, 55), (34, 52, 55), (35, 52, 54), (36, 52, 54)],
    "N": [(31, 51, 54), (32, 51, 54), (33, 51, 54), (34, 51, 53), (35, 51, 53)],
}


def _shaved_side(d):
    sil = spans(SIDE[d])
    for p in spans(SHAVED_SIDE_STUBBLE[d], "s"):
        sil[p] = "s"
    return sil


SHAVED_SIDE = style("straight", light=0.3, **each(_shaved_side))

# Curly: big curly volume to the shoulders.
CURLY_F = style("curly", light=0.4, **each(lambda d: fluff(spans(LONG[d]), d, seed=11, reach=2)))

FEMALE = [
    ("bob", "Bob", BOB_CUT),
    ("side_swept", "Side-swept", SIDE_SWEPT),
    ("wavy", "Wavy", WAVY),
    ("pixie", "Pixie", PIXIE),
    ("high_ponytail", "High Ponytail", HIGH_PONYTAIL),
]
PARKED_FEMALE = [("single_braid", "Single Braid", SINGLE_BRAID), ("twin_braids", "Twin Braids", TWIN_BRAIDS),
                 ("bun", "Bun", BUN_STYLE), ("shaved_side", "Shaved Side", SHAVED_SIDE), ("curly", "Curly", CURLY_F)]
