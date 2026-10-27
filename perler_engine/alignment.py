"""Limits and alignment checks for manually adjusted layers.

The automatic layout is always valid. After manual moves:
- the sprite moves in whole beads and is kept fully on the board layout, so
  no occupied bead is ever clipped or dropped;
- the ring overlay repeats every 25 px, so its offset is stored in -12..12;
- the guide layer may move up to one board (725 px) in each direction.
Per-board counts are only reported when the guide lines sit on bead-cell
boundaries, because only then do they mark real board divisions.
"""
from dataclasses import dataclass

from .layout import BOARD_PX, PITCH, board_counts

GUIDE_LIMIT = BOARD_PX


def _clamp(value, low, high):
    return max(low, min(high, value))


def clamp_sprite_offset(grid, layout, offset):
    """Nearest sprite position that keeps every bead on the boards."""
    return (_clamp(offset[0], 0, layout.columns - grid.width),
            _clamp(offset[1], 0, layout.rows - grid.height))


def normalize_ring_offset(offset):
    """Equivalent ring offset in -12..12 (the overlay repeats every 25 px)."""
    return tuple((v + PITCH // 2) % PITCH - PITCH // 2 for v in offset)


def clamp_guide_offset(offset):
    return tuple(_clamp(v, -GUIDE_LIMIT, GUIDE_LIMIT) for v in offset)


@dataclass(frozen=True, eq=False)
class Alignment:
    rings_aligned: bool
    guides_on_bead_grid: bool
    beads_outside_boards: int
    board_counts: object  # {(row, col): Counter} for marked boards, or None if unavailable
    warnings: tuple

    @property
    def valid(self):
        return not self.warnings


def check_alignment(grid, layout):
    warnings = []
    rings_aligned = layout.ring_offset == (0, 0)
    if not rings_aligned:
        warnings.append("Bead rings are off the bead positions. Reset Bead Rings to fix.")
    gdx, gdy = layout.guide_offset
    on_grid = gdx % PITCH == 0 and gdy % PITCH == 0
    counts, outside = None, 0
    if not on_grid:
        warnings.append("Pegboard lines are not between bead positions, so they are not real "
                        "board divisions. Board counts are unavailable. "
                        "Reset Pegboard Lines to fix.")
    else:
        everything = board_counts(grid, layout)
        counts = {k: v for k, v in everything.items()
                  if 1 <= k[0] <= layout.boards_y and 1 <= k[1] <= layout.boards_x}
        outside = sum(sum(v.values()) for k, v in everything.items() if k not in counts)
        if outside:
            warnings.append(f"{outside:,} beads fall outside the marked pegboards. "
                            "Move the sprite or reset Pegboard Lines.")
    return Alignment(rings_aligned, on_grid, outside, counts, tuple(warnings))
