"""
render_helper.py -- final version. Renders a game_engine.Game onto the
user's own artwork (safe-mode or normal-mode board image), using cat-face
piece tokens, and returns PNG bytes ready for Telegram's sendPhoto.
"""
from io import BytesIO
from PIL import Image
from render_board_custom import (
    build_board_safe, build_board_normal, make_cell_functions,
    COLOR_TO_CAT, _get_cat,
)
from board_geometry import cell_for_piece


def render_game_png(game) -> bytes:
    builder = build_board_safe if game.safe_mode else build_board_normal
    img, draw, cell_x, cell_y = builder()
    _, _, position_to_pixel = make_cell_functions(cell_x, cell_y)

    # group pieces sharing a cell so we can size them down together (ring/stretch only;
    # yard slots are already 4 distinct fixed positions, never "shared")
    cell_groups = {}
    for player in game.players:
        for i, piece in enumerate(player.pieces):
            pos = cell_for_piece(player.color, i, piece.progress)
            if piece.progress == 0:
                # yard: draw immediately, own fixed slot, always "full" size
                cx, cy = position_to_pixel(*pos)
                cat = _get_cat(player.color, "full")
                img.paste(cat, (int(cx - cat.width/2), int(cy - cat.height/2)), cat)
            else:
                cell_groups.setdefault(pos, []).append(player.color)

    tag_for_n = {1: "full", 2: "pair", 3: "trio", 4: "quad"}
    offsets = {
        1: [(0.0, 0.0)],
        2: [(-0.22, 0.0), (0.22, 0.0)],
        3: [(0.0, -0.20), (-0.22, 0.16), (0.22, 0.16)],
        4: [(-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22)],
    }
    cell_size = min(cell_x, cell_y)
    for pos, colors in cell_groups.items():
        n = min(len(colors), 4)
        tag = tag_for_n[n]
        cx, cy = position_to_pixel(*pos)
        for (dx, dy), color in zip(offsets[n], colors[:4]):
            cat = _get_cat(color, tag)
            px, py = int(cx + dx*cell_size), int(cy + dy*cell_size)
            img.paste(cat, (px - cat.width//2, py - cat.height//2), cat)

    buf = BytesIO()
    out_w = 800
    out_h = int(out_w * img.height / img.width)
    img = img.resize((out_w, out_h), Image.LANCZOS)
    img.convert("RGB").save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()
