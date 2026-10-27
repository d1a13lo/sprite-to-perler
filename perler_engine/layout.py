"""Pegboard layout: board counts, sprite placement and per-board bead counts.

Geometry measured from the Photoshop template and the approved reference patterns:
29 x 29 pegs per board, 25 output pixels per bead, 725 pixels per board.
"""
import math
from collections import Counter
from dataclasses import dataclass, replace

import numpy as np

from .sprite import pack_rgb, unpack_rgb

BOARD_PEGS = 29
PITCH = 25
BOARD_PX = BOARD_PEGS * PITCH


@dataclass(frozen=True)
class Layout:
    boards_x: int
    boards_y: int
    sprite_offset: tuple = (0, 0)  # (column, row) of the sprite's top-left bead
    guide_offset: tuple = (0, 0)   # (dx, dy) output pixels; whole guide layer
    ring_offset: tuple = (0, 0)    # (dx, dy) output pixels; whole ring overlay

    @property
    def columns(self):
        return self.boards_x * BOARD_PEGS

    @property
    def rows(self):
        return self.boards_y * BOARD_PEGS

    @property
    def total_boards(self):
        return self.boards_x * self.boards_y

    @property
    def canvas_size(self):
        return self.columns * PITCH, self.rows * PITCH

    def moved(self, **changes):
        return replace(self, **changes)


def boards_needed(width, height):
    return math.ceil(width / BOARD_PEGS), math.ceil(height / BOARD_PEGS)


def auto_layout(grid):
    """Smallest board layout with the sprite centred on whole beads.

    When a margin is odd, the extra empty column goes on the right and the
    extra empty row on the bottom (as in the approved centred reference pattern).
    """
    bx, by = boards_needed(grid.width, grid.height)
    ox = (bx * BOARD_PEGS - grid.width) // 2
    oy = (by * BOARD_PEGS - grid.height) // 2
    return Layout(bx, by, sprite_offset=(ox, oy))


def bead_positions(grid, layout):
    """Layout (row, column) of every occupied bead and its original colour."""
    ys, xs = np.nonzero(grid.occupied)
    return ys + layout.sprite_offset[1], xs + layout.sprite_offset[0], grid.rgb[ys, xs]


def board_counts(grid, layout):
    """{(board_row, board_col): Counter(rgb -> beads)}, numbered from 1 at top-left.

    Boards are located by the guide layer, which must sit on whole bead
    positions for the assignment to be meaningful.
    """
    gdx, gdy = layout.guide_offset
    if gdx % PITCH or gdy % PITCH:
        raise ValueError("Guide layer is not aligned to bead positions")
    rows, cols, colors = bead_positions(grid, layout)
    board_r = (rows - gdy // PITCH) // BOARD_PEGS + 1
    board_c = (cols - gdx // PITCH) // BOARD_PEGS + 1
    # One int64 key per bead (a single fast sort): board row (12 bits), board
    # column (12 bits) and colour (24 bits). Board indices are shifted by 1024
    # so beads just outside the layout (moved guides) stay distinct.
    shift = 1 << 10
    keys = (((board_r.astype(np.int64) + shift) << 36) | ((board_c.astype(np.int64) + shift) << 24)
            | pack_rgb(colors).astype(np.int64))
    groups, counts = np.unique(keys, return_counts=True)
    result = {}
    for key, n in zip(groups.tolist(), counts.tolist()):
        br, bc = (key >> 36) - shift, ((key >> 24) & 0xFFF) - shift
        result.setdefault((br, bc), Counter())[unpack_rgb(key & 0xFFFFFF)] = n
    return result
