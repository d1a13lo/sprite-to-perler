"""Load a prepared sprite and turn it into the authoritative bead grid.

One sprite pixel is one bead. Colours are never changed; the only decision
made per pixel is whether it holds a bead.

Partial transparency rule (none of the approved sources contain any):
alpha >= 128 is a bead drawn with its original RGB, alpha < 128 is empty.
Whenever this rule is applied a warning reports how many pixels it affected.
"""
from dataclasses import dataclass, field, replace
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from .errors import BackgroundDecisionNeeded, InputError

# Largest accepted sprite (one pixel = one bead): about 71 x 71 pegboards. Large
# patterns are rendered in strips, so this is set by processing time, not memory
# (measured times are in the user guide, "Large sprites").
MAX_SIDE = 2048
SUPPORTED_FORMATS = ("PNG", "GIF")  # GIF frame 0 keeps its exact palette colours
PARTIAL_ALPHA_THRESHOLD = 128


def pack_rgb(rgb):
    """(..., 3) uint8 colours as single integers 0xRRGGBB (same order as RGB tuples)."""
    rgb = np.asarray(rgb, dtype=np.uint32)
    return (rgb[..., 0] << 16) | (rgb[..., 1] << 8) | rgb[..., 2]


def unpack_rgb(value):
    return ((value >> 16) & 255, (value >> 8) & 255, value & 255)


@dataclass(frozen=True, eq=False)
class BeadGrid:
    rgb: np.ndarray        # (height, width, 3) uint8, original colours
    occupied: np.ndarray   # (height, width) bool, True where a bead goes
    warnings: tuple = field(default=())

    @property
    def width(self):
        return self.rgb.shape[1]

    @property
    def height(self):
        return self.rgb.shape[0]

    @property
    def total(self):
        return int(self.occupied.sum())

    def color_counts(self):
        """[(rgb tuple, count)] for occupied cells, most used first (ties by RGB)."""
        values, counts = np.unique(pack_rgb(self.rgb[self.occupied]), return_counts=True)
        order = np.lexsort((values, -counts))
        return [(unpack_rgb(v), int(n)) for v, n in zip(values[order].tolist(),
                                                        counts[order].tolist())]

    def rgba(self):
        alpha = np.where(self.occupied, 255, 0).astype(np.uint8)
        return np.dstack([self.rgb, alpha])


def crop_to_beads(grid):
    """The grid cut to the bounding box of its beads, so empty outer margins
    never cost pegboards. Beads keep their colours and relative positions, and
    internal gaps stay. Returns the same grid when there is no empty margin.
    """
    rows, cols = np.nonzero(grid.occupied.any(axis=1))[0], np.nonzero(grid.occupied.any(axis=0))[0]
    top, bottom, left, right = int(rows[0]), int(rows[-1]) + 1, int(cols[0]), int(cols[-1]) + 1
    if (top, left, bottom, right) == (0, 0, grid.height, grid.width):
        return grid
    note = (f"Empty outer margins ignored: the image is {grid.width} × {grid.height} pixels, "
            f"the visible sprite {right - left} × {bottom - top}.")
    return replace(grid, rgb=np.ascontiguousarray(grid.rgb[top:bottom, left:right]),
                   occupied=np.ascontiguousarray(grid.occupied[top:bottom, left:right]),
                   warnings=grid.warnings + (note,))


def load_sprite(path, background="auto", background_color=None):
    """Open and validate a sprite file, then build its bead grid."""
    path = Path(path)
    if not path.is_file():
        raise InputError(f"File not found: {path}")
    if path.stat().st_size == 0:
        raise InputError("The file is empty.")
    try:
        image = Image.open(path)
    except UnidentifiedImageError:
        raise InputError("This file is not a readable image.") from None
    with image:
        if image.format not in SUPPORTED_FORMATS:
            raise InputError(f"Unsupported image type ({image.format}). "
                             "Please use a PNG or GIF sprite.")
        check_size(image.size)
        notices = []
        try:
            frames = getattr(image, "n_frames", 1)
            if frames > 1 and image.format == "PNG":
                raise InputError("Animated PNG files are not supported. "
                                 "Please use a single-frame sprite.")
            if frames > 1:
                # Only the first frame of an animated GIF is used.
                image.seek(0)
                notices.append(f"This GIF is animated ({frames} frames). "
                               "Only the first frame is used.")
            image.load()
        except (OSError, ValueError, EOFError) as exc:
            raise InputError(f"The image file is damaged or incomplete ({exc}).") from None
        grid = prepare_sprite(image, background, background_color)
    return replace(grid, warnings=tuple(notices) + grid.warnings)


def check_size(size):
    w, h = size
    if w < 1 or h < 1:
        raise InputError("The image has no pixels.")
    if w > MAX_SIDE or h > MAX_SIDE:
        raise InputError(
            f"The sprite is {w} x {h} pixels. The limit is {MAX_SIDE} x {MAX_SIDE} "
            f"(one pixel = one bead, about {-(-MAX_SIDE // 29)} x {-(-MAX_SIDE // 29)} "
            "pegboards). Please use a prepared, unscaled sprite.")


def prepare_sprite(image, background="auto", background_color=None):
    """Build a BeadGrid from a PIL image.

    background:
      "auto"    use existing transparency; if there is none, remove a uniform
                corner colour only when it never appears inside the sprite.
      "keep"    every opaque pixel is a bead (no colour removal).
      "outside" remove the background colour only where it touches the border.
      "all"     remove every pixel of the background colour.
    background_color: explicit (r, g, b) for "outside"/"all"; defaults to the
    uniform corner colour.
    """
    check_size(image.size)
    rgba = np.asarray(image.convert("RGBA"))
    rgb = np.ascontiguousarray(rgba[..., :3])
    alpha = rgba[..., 3]
    warnings = []

    partial = (alpha > 0) & (alpha < 255)
    occupied = alpha >= PARTIAL_ALPHA_THRESHOLD
    if partial.any():
        kept = int((partial & occupied).sum())
        warnings.append(
            f"{int(partial.sum())} partially transparent pixels found: {kept} kept as "
            f"full beads (alpha >= {PARTIAL_ALPHA_THRESHOLD}), "
            f"{int(partial.sum()) - kept} treated as empty.")

    has_transparency = bool((alpha < 255).any())
    if background not in ("auto", "keep", "outside", "all"):
        raise ValueError(f"Unknown background mode: {background}")

    if background == "auto" and not has_transparency:
        color = background_color or corner_color(rgb)
        if color is None:
            raise BackgroundDecisionNeeded(
                "The image has no transparency and its corners are different colours, "
                "so no background colour could be identified. Keep every pixel as a bead?")
        same = np.all(rgb == color, axis=2)
        outside = border_connected(same)
        interior = int((same & ~outside).sum())
        if interior:
            raise BackgroundDecisionNeeded(
                f"The background colour #{color[0]:02X}{color[1]:02X}{color[2]:02X} also "
                f"appears in {interior} pixels inside the sprite. Remove it only around "
                "the outside, or everywhere?", color, interior)
        if same.all():
            raise BackgroundDecisionNeeded(
                "The whole image is one colour, so removing it as background would leave "
                "nothing. Keep every pixel as a bead?", color)
        occupied = occupied & ~same
        warnings.append(f"Removed background colour #{color[0]:02X}{color[1]:02X}{color[2]:02X}.")
    elif background in ("outside", "all"):
        color = background_color or corner_color(rgb)
        if color is None:
            raise InputError("No background colour was given and the corners are not uniform.")
        same = np.all(rgb == color, axis=2)
        remove = border_connected(same) if background == "outside" else same
        occupied = occupied & ~remove
        warnings.append(f"Removed background colour #{color[0]:02X}{color[1]:02X}{color[2]:02X} "
                        f"({'outside only' if background == 'outside' else 'everywhere'}).")

    if not occupied.any():
        raise InputError("The sprite has no visible pixels (it is fully transparent).")
    return BeadGrid(rgb=rgb, occupied=occupied, warnings=tuple(warnings))


def corner_color(rgb):
    corners = {tuple(rgb[y, x].tolist()) for y in (0, -1) for x in (0, -1)}
    return corners.pop() if len(corners) == 1 else None


def _fill_runs(reached, mask):
    """Spread `reached` along each row through unbroken runs of `mask`."""
    h, w = mask.shape
    m = mask.ravel()
    starts = m.copy()
    starts[1:] &= ~m[:-1]
    starts[::w] = m[::w]  # every row starts a new run
    ids = np.cumsum(starts) * m
    hit = np.bincount(ids, weights=(reached.ravel() & m), minlength=int(ids.max()) + 1) > 0
    hit[0] = False
    return hit[ids].reshape(h, w)


def border_connected(mask):
    """Cells of `mask` reachable from the image border (4-connected).

    Alternates whole-run filling along rows and columns, which needs only a
    few passes even for large images."""
    mask = np.ascontiguousarray(mask, dtype=bool)
    reached = np.zeros_like(mask)
    reached[0, :] = mask[0, :]
    reached[-1, :] = mask[-1, :]
    reached[:, 0] |= mask[:, 0]
    reached[:, -1] |= mask[:, -1]
    mask_t = np.ascontiguousarray(mask.T)
    while True:
        grown = _fill_runs(reached, mask)
        grown = np.ascontiguousarray(_fill_runs(np.ascontiguousarray(grown.T), mask_t).T)
        if np.array_equal(grown, reached):
            return reached
        reached = grown
