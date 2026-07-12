"""
render_board_custom.py - adapter that uses the user's own artwork as the
board background instead of the procedurally-drawn one, auto-calibrated
to the image's actual pixel size (measured: 1088x1080, 11x11 grid, no margin).
"""
from PIL import Image, ImageDraw
import os

import os
_HERE = os.path.dirname(os.path.abspath(__file__))
BOARD_IMAGE_SAFE = os.path.join(_HERE, "board_safe.jpg")
BOARD_IMAGE_NORMAL = os.path.join(_HERE, "board_normal.jpg")

GRID = 11
MARGIN_X = 0
MARGIN_Y = 0


def _make_builder(image_path):
    def build_board():
        img = Image.open(image_path).convert("RGB")
        w, h = img.size
        cell_x = (w - 2 * MARGIN_X) / GRID
        cell_y = (h - 2 * MARGIN_Y) / GRID
        draw = ImageDraw.Draw(img)
        return img, draw, cell_x, cell_y
    return build_board

build_board_safe = _make_builder(BOARD_IMAGE_SAFE)
build_board_normal = _make_builder(BOARD_IMAGE_NORMAL)


def make_cell_functions(cell_x, cell_y):
    def cell_box(row, col):
        x0 = MARGIN_X + col * cell_x
        y0 = MARGIN_Y + row * cell_y
        return (x0, y0, x0 + cell_x, y0 + cell_y)

    def cell_center(row, col):
        """Center of the unit CELL at integer index (row,col) -- adds +0.5 cell."""
        x0, y0, x1, y1 = cell_box(row, col)
        return ((x0 + x1) / 2, (y0 + y1) / 2)

    def position_to_pixel(row_pos, col_pos):
        """Direct continuous-position -> pixel conversion, NO +0.5 cell offset.
        Use this for yard_slot()'s fractional positions (e.g. yard center = 2.0),
        NOT cell_center (which is for referencing a specific named grid cell)."""
        x = MARGIN_X + col_pos * cell_x
        y = MARGIN_Y + row_pos * cell_y
        return (x, y)

    return cell_box, cell_center, position_to_pixel


STACK_OFFSETS = {
    1: [(0.0, 0.0)],
    2: [(-0.22, 0.0), (0.22, 0.0)],
    3: [(0.0, -0.20), (-0.22, 0.16), (0.22, 0.16)],
    4: [(-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22)],
}
STACK_RADIUS_FACTOR = {1: 0.34, 2: 0.25, 3: 0.21, 4: 0.18}


def draw_stack(draw, cell_center_fn, cell_size, row, col, colors):
    n = min(len(colors), 4)
    cx, cy = cell_center_fn(row, col)
    r = int(cell_size * STACK_RADIUS_FACTOR[n])
    for (dx, dy), color in zip(STACK_OFFSETS[n], colors[:4]):
        px, py = int(cx + dx * cell_size), int(cy + dy * cell_size)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color, outline=(20, 20, 20), width=2)
        hl = tuple(min(255, c + 70) for c in color)
        draw.ellipse([int(px - r*0.5), int(py - r*0.6), int(px - r*0.05), int(py - r*0.15)], fill=hl)


if __name__ == "__main__":
    RED, BLUE, GREEN, YELLOW = (198,40,40), (21,101,192), (46,125,50), (245,178,15)
    img, draw, cell_x, cell_y = build_board_safe()
    cell_box, cell_center = make_cell_functions(cell_x, cell_y)

    # draw a thin grid overlay so we can visually check alignment
    for r in range(GRID + 1):
        y = MARGIN_Y + r * cell_y
        draw.line([(MARGIN_X, y), (MARGIN_X + GRID*cell_x, y)], fill=(0, 255, 0), width=2)
    for c in range(GRID + 1):
        x = MARGIN_X + c * cell_x
        draw.line([(x, MARGIN_Y), (x, MARGIN_Y + GRID*cell_y)], fill=(0, 255, 0), width=2)

    # place one sample piece of each color at their yard's first slot, using board_geometry
    import sys; sys.path.insert(0, ".")
    from board_geometry import yard_slot
    for color, rgb in [("Red", RED), ("Blue", BLUE), ("Green", GREEN), ("Yellow", YELLOW)]:
        row, col = yard_slot(color, 0)
        draw_stack(draw, cell_center, min(cell_x, cell_y), row, col, [rgb])

    out = "/home/claude/custom_calibration_test.png"
    img.save(out, quality=90)
    print("cell_x:", cell_x, "cell_y:", cell_y)
    print("saved:", out)


COLOR_TO_CAT = {"Green": "black", "Blue": "white", "Red": "orange", "Yellow": "calico"}
_CAT_CACHE = {}


def _get_cat(color, tag):
    key = (color, tag)
    if key not in _CAT_CACHE:
        path = os.path.join(_HERE, "pieces", "sized", f"{COLOR_TO_CAT[color]}_{tag}.png")
        _CAT_CACHE[key] = Image.open(path).convert("RGBA")
    return _CAT_CACHE[key]


def draw_cats(img, cell_center_fn, cell_size, row, col, colors):
    n = min(len(colors), 4)
    tag = {1: "full", 2: "pair", 3: "trio", 4: "quad"}[n]
    cx, cy = cell_center_fn(row, col)
    for (dx, dy), color in zip(STACK_OFFSETS[n], colors[:4]):
        cat = _get_cat(color, tag)
        px, py = int(cx + dx*cell_size), int(cy + dy*cell_size)
        img.paste(cat, (px - cat.width//2, py - cat.height//2), cat)
