from PIL import Image, ImageDraw
import os

CELL = 70
MARGIN = 15
GRID = 11
BOARD_PX = CELL * GRID
CANVAS = BOARD_PX + 2 * MARGIN

RED = (198, 40, 40)
BLUE = (21, 101, 192)
YELLOW = (245, 178, 15)
GREEN = (46, 125, 50)
WOOD = (230, 200, 160)
WOOD_LINE = (178, 140, 100)
BORDER = (101, 67, 33)

RED_PASTEL = (247, 205, 205)
BLUE_PASTEL = (203, 222, 247)
YELLOW_PASTEL = (250, 232, 190)
GREEN_PASTEL = (205, 232, 207)

STACK_OFFSETS = {
    1: [(0.0, 0.0)],
    2: [(-0.22, 0.0), (0.22, 0.0)],
    3: [(0.0, -0.20), (-0.22, 0.16), (0.22, 0.16)],
    4: [(-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22)],
}
STACK_RADIUS_FACTOR = {1: 0.36, 2: 0.26, 3: 0.22, 4: 0.19}


def cell_box(row, col):
    x0 = MARGIN + col * CELL
    y0 = MARGIN + row * CELL
    return (x0, y0, x0 + CELL, y0 + CELL)


def cell_center(row, col):
    x0, y0, x1, y1 = cell_box(row, col)
    return ((x0 + x1) // 2, (y0 + y1) // 2)


def tint(color, amt=0.55):
    return tuple(int(c * (1 - amt) + 255 * amt) for c in color)


def draw_home_yard(draw, row0, col0, pastel, vivid):
    x0, y0, _, _ = cell_box(row0, col0)
    _, _, x1, y1 = cell_box(row0 + 3, col0 + 3)
    draw.rectangle([x0, y0, x1, y1], fill=pastel, outline=BORDER, width=3)
    pad = 12
    draw.rounded_rectangle([x0 + pad, y0 + pad, x1 - pad, y1 - pad], radius=14,
                            fill=(255, 255, 255), outline=vivid, width=2)
    near, far = 1.5 - 0.35 * 1.5, 1.5 + 0.35 * 1.5
    for r, c in [(row0 + near, col0 + near), (row0 + near, col0 + far),
                 (row0 + far, col0 + near), (row0 + far, col0 + far)]:
        cx, cy = cell_center(r, c)
        cx, cy = int(cx), int(cy)
        rad = 16
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=vivid, width=2)


def draw_ring_cell(draw, row, col, fill=WOOD):
    x0, y0, x1, y1 = cell_box(row, col)
    draw.rectangle([x0, y0, x1, y1], fill=fill, outline=WOOD_LINE, width=1)


def build_board():
    img = Image.new("RGB", (CANVAS, CANVAS), WOOD)
    draw = ImageDraw.Draw(img)

    draw_home_yard(draw, 0, 0, RED_PASTEL, RED)
    draw_home_yard(draw, 0, 7, BLUE_PASTEL, BLUE)
    draw_home_yard(draw, 7, 0, YELLOW_PASTEL, YELLOW)
    draw_home_yard(draw, 7, 7, GREEN_PASTEL, GREEN)

    # top arm (rows0-3, cols4-6), Blue's private stretch at col5, rows1-3
    for row in range(0, 4):
        for col in range(4, 7):
            fill = tint(BLUE) if (col == 5 and row >= 1) else WOOD
            draw_ring_cell(draw, row, col, fill)
    # bottom arm (rows7-10, cols4-6), Yellow's private stretch at col5, rows7-9
    for row in range(7, 11):
        for col in range(4, 7):
            fill = tint(YELLOW) if (col == 5 and row <= 9) else WOOD
            draw_ring_cell(draw, row, col, fill)
    # left arm (rows4-6, cols0-3), Red's private stretch at row5, cols1-3
    for row in range(4, 7):
        for col in range(0, 4):
            fill = tint(RED) if (row == 5 and col >= 1) else WOOD
            draw_ring_cell(draw, row, col, fill)
    # right arm (rows4-6, cols7-10), Green's private stretch at row5, cols7-9
    for row in range(4, 7):
        for col in range(7, 11):
            fill = tint(GREEN) if (row == 5 and col <= 9) else WOOD
            draw_ring_cell(draw, row, col, fill)

    # center 3x3 pinwheel (rows4-6, cols4-6)
    cx0, cy0, _, _ = cell_box(4, 4)
    _, _, cx1, cy1 = cell_box(6, 6)
    center_pt = ((cx0 + cx1) // 2, (cy0 + cy1) // 2)
    draw.polygon([(cx0, cy0), (cx1, cy0), center_pt], fill=BLUE)
    draw.polygon([(cx1, cy0), (cx1, cy1), center_pt], fill=GREEN)
    draw.polygon([(cx1, cy1), (cx0, cy1), center_pt], fill=YELLOW)
    draw.polygon([(cx0, cy1), (cx0, cy0), center_pt], fill=RED)
    draw.rectangle([cx0, cy0, cx1, cy1], outline=BORDER, width=3)

    return img, draw


def draw_stack(draw, row, col, colors):
    n = min(len(colors), 4)
    cx, cy = cell_center(row, col)
    cx, cy = int(cx), int(cy)
    r = int(CELL * STACK_RADIUS_FACTOR[n])
    for (dx, dy), color in zip(STACK_OFFSETS[n], colors[:4]):
        px, py = cx + int(dx * CELL), cy + int(dy * CELL)
        draw.ellipse([px - r, py - r, px + r, py + r], fill=color, outline=(25, 25, 25), width=2)
        hl = tuple(min(255, c + 70) for c in color)
        draw.ellipse([int(px - r * 0.5), int(py - r * 0.6), int(px - r * 0.05), int(py - r * 0.15)], fill=hl)


if __name__ == "__main__":
    img, draw = build_board()
    os.makedirs("/home/claude", exist_ok=True)
    tc_path = "/home/claude/board_truecolor.png"
    img.save(tc_path, optimize=True)
    pal = img.convert("P", palette=Image.ADAPTIVE, colors=32)
    pal_path = "/home/claude/board_palette.png"
    pal.save(pal_path, optimize=True)
    print("canvas:", CANVAS, "x", CANVAS)
    print("truecolor bytes:", os.path.getsize(tc_path))
    print("palette bytes:", os.path.getsize(pal_path))
