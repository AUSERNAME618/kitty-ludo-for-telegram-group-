"""
board_geometry.py -- compact board where yards sit flush against the arms
(no empty gap): yard=4, arm_length=4, arm_width=3, center=3, total grid=11x11.
Ring length is still 40 cells (same core structure as before, just resized).
"""

GRID = 11
YARD = 4
ARM = 4
CENTER = 3

RING_LENGTH = 40
HOME_STRETCH = 4
TOTAL_STEPS = (RING_LENGTH - 1) + HOME_STRETCH  # 43

START_OFFSET = {"Blue": 0, "Red": 10, "Green": 20, "Yellow": 30}

RING_ORDER = [
    (4, 1), (4, 2), (4, 3), (4, 4), (3, 4), (2, 4), (1, 4), (0, 4),
    (0, 5), (0, 6), (1, 6), (2, 6), (3, 6), (4, 6), (4, 7), (4, 8),
    (4, 9), (4, 10), (5, 10), (6, 10), (6, 9), (6, 8), (6, 7), (6, 6),
    (7, 6), (8, 6), (9, 6), (10, 6), (10, 5), (10, 4), (9, 4), (8, 4),
    (7, 4), (6, 4), (6, 3), (6, 2), (6, 1), (6, 0), (5, 0), (4, 0),
]
assert len(RING_ORDER) == RING_LENGTH

STRETCH = {
    "Blue":   [(5, 1), (5, 2), (5, 3), (5, 4)],
    "Red":    [(1, 5), (2, 5), (3, 5), (4, 5)],
    "Green":  [(5, 9), (5, 8), (5, 7), (5, 6)],
    "Yellow": [(9, 5), (8, 5), (7, 5), (6, 5)],
}

YARD_ORIGIN = {"Blue": (0, 0), "Red": (0, 7), "Yellow": (7, 0), "Green": (7, 7)}


def yard_slot(color, piece_index):
    r0, c0 = YARD_ORIGIN[color]
    CENTER_Y = {"Blue": 2.0 - 0.40, "Red": 2.0 - 0.40, "Yellow": 2.0, "Green": 2.0}
    CENTER_X = {"Blue": 2.0 - 0.20, "Yellow": 2.0 - 0.20, "Red": 2.0 + 0.20, "Green": 2.0 + 0.20}
    center_x, center_y = CENTER_X[color], CENTER_Y[color]
    spread = 0.55
    slots = [(r0 + center_y - spread, c0 + center_x - spread),
             (r0 + center_y - spread, c0 + center_x + spread),
             (r0 + center_y + spread, c0 + center_x - spread),
             (r0 + center_y + spread, c0 + center_x + spread)]
    return slots[piece_index % 4]


def absolute_ring_index(color, progress):
    return (START_OFFSET[color] + progress - 1) % RING_LENGTH


def cell_for_piece(color, piece_index, progress):
    """Returns a continuous (row, col) position, always meant for position_to_pixel
    (NOT cell_center) -- ring/stretch cells get +0.5 to land at that cell's true
    center, matching yard_slot's already-continuous coordinates."""
    if progress == 0:
        return yard_slot(color, piece_index)
    if 1 <= progress <= RING_LENGTH - 1:
        r, c = RING_ORDER[absolute_ring_index(color, progress)]
        return (r + 0.5, c + 0.5)
    stretch_idx = progress - RING_LENGTH
    r, c = STRETCH[color][stretch_idx]
    return (r + 0.5, c + 0.5)


if __name__ == "__main__":
    for color in START_OFFSET:
        seen = set()
        for progress in range(0, TOTAL_STEPS + 1):
            seen.add(cell_for_piece(color, 0, progress))
        print(color, "unique cells:", len(seen), "/", TOTAL_STEPS + 1)
