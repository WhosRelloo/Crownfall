"""Write an animation sheet as upload-ready files with readable names.

    python Tools/export.py <sheet.png> <Name> <fps> [out_root]

Makes <out_root>/<Name>/ (default out_root: ~/Downloads/Crownfall) holding:
  <Name> (South).png ... one 768 x 96 strip per direction, in the game's row order (upload these)
  <Name> (All Directions).png   the whole sheet
  <Name> Preview.gif            all 8 directions playing side by side, 3x
"""
import os
import sys

from PIL import Image

ROWS = ["S", "SW", "W", "NW", "N", "NE", "E", "SE"]
NAMES = {"S": "South", "SW": "South-West", "W": "West", "NW": "North-West",
         "N": "North", "NE": "North-East", "E": "East", "SE": "South-East"}
CELL, FRAMES, ZOOM = 96, 8, 3


def main():
    sheet_path, name, fps = sys.argv[1], sys.argv[2], float(sys.argv[3])
    root = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.expanduser("~"), "Downloads", "Crownfall")
    out = os.path.join(root, name)
    os.makedirs(out, exist_ok=True)
    sheet = Image.open(sheet_path).convert("RGBA")
    for r, d in enumerate(ROWS):
        sheet.crop((0, r * CELL, CELL * FRAMES, (r + 1) * CELL)).save(os.path.join(out, f"{name} ({NAMES[d]}).png"))
    sheet.save(os.path.join(out, f"{name} (All Directions).png"))
    frames = []
    for f in range(FRAMES):
        canvas = Image.new("RGBA", (CELL * len(ROWS), CELL), (58, 62, 58, 255))
        for r in range(len(ROWS)):
            canvas.alpha_composite(sheet.crop((f * CELL, r * CELL, (f + 1) * CELL, (r + 1) * CELL)), (r * CELL, 0))
        frames.append(canvas.resize((canvas.width * ZOOM, canvas.height * ZOOM), Image.NEAREST).convert("P"))
    frames[0].save(os.path.join(out, f"{name} Preview.gif"), save_all=True, append_images=frames[1:],
                   duration=round(1000 / fps), loop=0, disposal=2)
    print("wrote", out)


if __name__ == "__main__":
    main()
