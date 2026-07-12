import random

RING_LENGTH = 36  # matches board_geometry.py (4 pinwheel-corner cells removed per user feedback)
HOME_STRETCH = 4
TOTAL_STEPS = RING_LENGTH - 1 + HOME_STRETCH  # 39
EXIT_ROLLS = {1, 6}

START_OFFSET = {"Blue": 0, "Red": 9, "Green": 18, "Yellow": 27}


def safe_cells_for(safe_mode):
    if not safe_mode:
        return set()
    # exact ring indices the user marked (orange circles) on the real board image:
    # the fishbone tip, bowl, and spawn-paw cells of every arm -- 12 cells total
    return {0, 5, 7, 9, 14, 16, 18, 23, 25, 27, 32, 34}


class Piece:
    def __init__(self, color):
        self.color = color
        self.progress = 0  # 0 = yard, 1..51 = shared ring, 52..57 = home stretch/finished

    @property
    def in_yard(self):
        return self.progress == 0

    @property
    def finished(self):
        return self.progress == TOTAL_STEPS

    def absolute_ring_index(self):
        if 1 <= self.progress <= 51:
            return (START_OFFSET[self.color] + self.progress - 1) % RING_LENGTH
        return None


class Player:
    def __init__(self, color):
        self.color = color
        self.pieces = [Piece(color) for _ in range(4)]

    @property
    def any_finished(self):
        return any(p.finished for p in self.pieces)

    @property
    def all_finished(self):
        return all(p.finished for p in self.pieces)


class Game:
    def __init__(self, colors, quick_mode=True, safe_mode=True):
        self.players = [Player(c) for c in colors]
        self.turn_pos = 0
        self.consecutive_sixes = 0
        self.game_over = False
        self.winner = None
        self.quick_mode = quick_mode
        self.safe_mode = safe_mode
        self.safe_cells = safe_cells_for(safe_mode)

    @property
    def current(self):
        return self.players[self.turn_pos]

    def has_won(self, player):
        return player.any_finished if self.quick_mode else player.all_finished

    def movable_pieces(self, dice):
        moves = []
        for i, piece in enumerate(self.current.pieces):
            if piece.finished:
                continue
            if piece.in_yard:
                if dice in EXIT_ROLLS:
                    moves.append(i)
            elif piece.progress + dice <= TOTAL_STEPS:
                moves.append(i)
        return moves

    def apply_move(self, piece_index, dice):
        piece = self.current.pieces[piece_index]
        log = []
        if piece.in_yard:
            piece.progress = 1
            log.append(f"  {piece.color} #{piece_index} exits yard (rolled {dice}) -> start cell")
        else:
            piece.progress += dice
            log.append(f"  {piece.color} #{piece_index} moves {dice} -> progress {piece.progress}")

        if 1 <= piece.progress <= 51:
            landing = piece.absolute_ring_index()
            if landing not in self.safe_cells:
                for other in self.players:
                    if other is self.current:
                        continue
                    for op in other.pieces:
                        if 1 <= op.progress <= 51 and op.absolute_ring_index() == landing:
                            op.progress = 0
                            log.append(f"    -> captures {other.color} piece, sent back to yard")
            else:
                log.append("    (safe cell, no capture)")
        if piece.finished:
            log.append(f"    -> {piece.color} #{piece_index} reaches home!")
        return log

    def take_turn(self, dice):
        if self.game_over:
            return ["game already over"]
        log = [f"[{self.current.color}] rolled {dice}"]
        self.consecutive_sixes = self.consecutive_sixes + 1 if dice == 6 else 0

        if self.consecutive_sixes == 3:
            log.append("  three 6s in a row -> turn forfeited")
            self.consecutive_sixes = 0
            self.end_turn(extra=False)
            return log

        moves = self.movable_pieces(dice)
        if not moves:
            log.append("  no legal move -> turn passes")
            self.end_turn(extra=(dice == 6))
            return log

        chosen = moves[0]  # in the real bot: whichever piece the player taps
        log.extend(self.apply_move(chosen, dice))

        if self.has_won(self.current):
            self.game_over = True
            self.winner = self.current.color
            mode = "quick" if self.quick_mode else "full"
            log.append(f"  *** {self.current.color} WINS ({mode} mode) ***")
            return log

        self.end_turn(extra=(dice == 6))
        return log

    def end_turn(self, extra):
        if not extra:
            self.turn_pos = (self.turn_pos + 1) % len(self.players)
            self.consecutive_sixes = 0


if __name__ == "__main__":
    for quick in (True, False):
        for safe in (True, False):
            random.seed(3)
            game = Game(["Red", "Green", "Yellow", "Blue"], quick_mode=quick, safe_mode=safe)
            rounds = 0
            while not game.game_over and rounds < 3000:
                d = random.randint(1, 6)
                game.take_turn(d)
                rounds += 1
            label = ("Safe " if safe else "Normal ") + ("Quick" if quick else "Full")
            print(f"{label:14s}-> winner: {game.winner}, dice rolls: {rounds}")
