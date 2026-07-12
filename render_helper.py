"""
render_helper.py -- renders a game_engine.Game onto the user's own artwork
(safe-mode or normal-mode board image), using cat-face piece tokens.
Returns PNG/JPEG bytes ready for Telegram's sendPhoto / edit_message_media.
"""
from io import BytesIO
from PIL import Image, ImageDraw, ImageFont
from render_board_custom import (
    build_board_safe, build_board_normal, make_cell_functions,
    COLOR_TO_CAT, _get_cat,
)
from board_geometry import cell_for_piece

TAG_FOR_N = {1: "full", 2: "pair", 3: "trio", 4: "quad"}
OFFSETS = {
    1: [(0.0, 0.0)],
    2: [(-0.22, 0.0), (0.22, 0.0)],
    3: [(0.0, -0.20), (-0.22, 0.16), (0.22, 0.16)],
    4: [(-0.22, -0.22), (0.22, -0.22), (-0.22, 0.22), (0.22, 0.22)],
}


def render_game_png(game, choice_color=None, choice_indices=None) -> bytes:
    """Renders the board. If choice_color/choice_indices are given, a small
    faint number (1-4, matching that piece's index) is drawn on top of ONLY
    that color's movable pieces -- used when the player must pick which
    piece to move after rolling a 1 or 6 with multiple options."""
    builder = build_board_safe if game.safe_mode else build_board_normal
    img, draw, cell_x, cell_y = builder()
    _, _, position_to_pixel = make_cell_functions(cell_x, cell_y)
    cell_size = min(cell_x, cell_y)

    cell_groups = {}
    piece_pixel_pos = {}  # (color, piece_index) -> (px, py) actually used, for number overlay
    for player in game.players:
        for i, piece in enumerate(player.pieces):
            pos = cell_for_piece(player.color, i, piece.progress)
            if piece.progress == 0:
                cx, cy = position_to_pixel(*pos)
                cat = _get_cat(player.color, "full")
                img.paste(cat, (int(cx - cat.width/2), int(cy - cat.height/2)), cat)
                piece_pixel_pos[(player.color, i)] = (cx, cy, cat.width)
            else:
                cell_groups.setdefault(pos, []).append((player.color, i))

    for pos, entries in cell_groups.items():
        n = min(len(entries), 4)
        tag = TAG_FOR_N[n]
        cx, cy = position_to_pixel(*pos)
        for (dx, dy), (color, piece_i) in zip(OFFSETS[n], entries[:4]):
            cat = _get_cat(color, tag)
            px, py = int(cx + dx*cell_size), int(cy + dy*cell_size)
            img.paste(cat, (px - cat.width//2, py - cat.height//2), cat)
            piece_pixel_pos[(color, piece_i)] = (px, py, cat.width)

    if choice_color and choice_indices:
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        odraw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
                                       int(cell_size * 0.28))
        except Exception:
            font = ImageFont.load_default()
        for idx in choice_indices:
            if (choice_color, idx) not in piece_pixel_pos:
                continue
            px, py, w = piece_pixel_pos[(choice_color, idx)]
            r = int(w * 0.24)
            cx2, cy2 = px + int(w*0.30), py - int(w*0.30)  # small badge, upper-right of the cat
            odraw.ellipse([cx2-r, cy2-r, cx2+r, cy2+r], fill=(20, 20, 20, 165))
            label = str(idx + 1)
            bbox = odraw.textbbox((0, 0), label, font=font)
            tw, th = bbox[2]-bbox[0], bbox[3]-bbox[1]
            odraw.text((cx2 - tw/2 - bbox[0], cy2 - th/2 - bbox[1]), label, font=font, fill=(255, 255, 255, 230))
        img = Image.alpha_composite(img.convert("RGBA"), overlay)

    buf = BytesIO()
    out_w = 800
    out_h = int(out_w * img.height / img.width)
    img = img.convert("RGB").resize((out_w, out_h), Image.LANCZOS)
    img.save(buf, format="JPEG", quality=85, optimize=True)
    return buf.getvalue()
