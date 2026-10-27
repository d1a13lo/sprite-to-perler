"""Compose the finished bead template.

Layer order, bottom to top (as in the Photoshop template):
  1. solid #2B2B2B background
  2. original sprite colours, one 25 x 25 cell per bead
  3. PSD 'HAMA BEADS' ring overlay, repeated every 25 px
  4. white pegboard guide lines, 3 px wide, one every 725 px

Compositing uses Pillow's alpha_composite, which reproduces the approved
reference templates pixel for pixel.
"""
import hashlib
import struct
import zlib
from functools import lru_cache
from pathlib import Path

import numpy as np
from PIL import Image

from .errors import AssetError
from .layout import BOARD_PX, PITCH

BACKGROUND = (43, 43, 43)
GUIDE_COLOR = (255, 255, 255)
GUIDE_WIDTH = 3
EXPORT_DPI = (300, 300)  # metadata only, matching the approved PNGs

RING_TILE_PATH = Path(__file__).resolve().parent / "assets" / "bead_ring_tile.png"
RING_TILE_SHA256 = "6aff365c047a1e1ce6fbf1f8c558aedb4f7000e91f5c7b8ba0f4c98321a3e93e"


@lru_cache(maxsize=None)
def _cached_ring_tile(path):
    return load_ring_tile(Path(path))


def load_ring_tile(path=RING_TILE_PATH):
    """Load the ring tile and check it is the exact PSD-derived raster."""
    try:
        with Image.open(path) as image:
            tile = np.asarray(image.convert("RGBA"))
    except FileNotFoundError:
        raise AssetError(f"Template asset is missing: {path}") from None
    except Exception as exc:
        raise AssetError(f"Template asset cannot be read: {path} ({exc})") from None
    if tile.shape != (PITCH, PITCH, 4) or hashlib.sha256(tile.tobytes()).hexdigest() != RING_TILE_SHA256:
        raise AssetError(f"Template asset is corrupted or has been changed: {path}")
    return tile


def ring_tile():
    return _cached_ring_tile(str(RING_TILE_PATH))


def render(grid, layout, guides=True):
    """Return the finished template as an RGB PIL image."""
    width, height = layout.canvas_size
    return render_region(grid, layout, (0, 0, width, height), guides)


def render_region(grid, layout, box, guides=True):
    """Render one rectangle (x0, y0, x1, y1) of the template, in output pixels.

    Every pixel depends only on its own position, so any region is exactly
    the matching crop of the full render; large patterns are rendered in
    pieces with bounded memory.
    """
    width, height = layout.canvas_size
    x0, y0 = max(0, box[0]), max(0, box[1])
    x1, y1 = min(width, box[2]), min(height, box[3])
    w, h = x1 - x0, y1 - y0
    if w <= 0 or h <= 0:
        raise ValueError(f"Region {box} is outside the {width} x {height} template")
    canvas = Image.new("RGBA", (w, h), BACKGROUND + (255,))
    canvas.alpha_composite(Image.fromarray(_sprite_layer(grid, layout, x0, y0, w, h), "RGBA"))
    canvas.alpha_composite(Image.fromarray(_ring_layer(layout, x0, y0, w, h), "RGBA"))
    pixels = np.array(canvas.convert("RGB"))
    if guides:
        _draw_guides(pixels, layout, x0, y0)
    return Image.fromarray(pixels, "RGB")


def _sprite_layer(grid, layout, x0, y0, w, h):
    """Sprite cells covering the region, one 25 x 25 cell per bead."""
    c0, r0 = x0 // PITCH, y0 // PITCH
    c1, r1 = -(-(x0 + w) // PITCH), -(-(y0 + h) // PITCH)
    cells = np.zeros((r1 - r0, c1 - c0, 4), np.uint8)
    ox, oy = layout.sprite_offset
    # Sprite rows/columns that fall inside this block of cells (clipped to the canvas).
    sr0, sr1 = max(0, r0 - oy), min(grid.height, r1 - oy)
    sc0, sc1 = max(0, c0 - ox), min(grid.width, c1 - ox)
    if sr0 < sr1 and sc0 < sc1:
        cells[sr0 + oy - r0:sr1 + oy - r0, sc0 + ox - c0:sc1 + ox - c0] = \
            grid.rgba()[sr0:sr1, sc0:sc1]
    pixels = np.repeat(np.repeat(cells, PITCH, axis=0), PITCH, axis=1)
    return np.ascontiguousarray(pixels[y0 - r0 * PITCH:y0 - r0 * PITCH + h,
                                       x0 - c0 * PITCH:x0 - c0 * PITCH + w])


def _ring_layer(layout, x0, y0, w, h):
    dx, dy = layout.ring_offset
    tile = np.roll(ring_tile(), (dy % PITCH, dx % PITCH), axis=(0, 1))
    sy, sx = y0 % PITCH, x0 % PITCH
    reps = (-(-(h + sy) // PITCH), -(-(w + sx) // PITCH), 1)
    return np.ascontiguousarray(np.tile(tile, reps)[sy:sy + h, sx:sx + w])


def guide_lines(length, boards, offset):
    """Start pixels of the guide lines along one axis.

    Line k sits at k * 725; the closing line at the far edge is drawn inside
    the canvas (last 3 pixels), as in the approved templates.
    """
    starts = [k * BOARD_PX for k in range(boards)] + [boards * BOARD_PX - GUIDE_WIDTH]
    return [s + offset for s in starts if -GUIDE_WIDTH < s + offset < length]


def _draw_guides(pixels, layout, x0=0, y0=0):
    """Draw the guide lines that cross a region whose top-left is (x0, y0)."""
    h, w = pixels.shape[:2]
    width, height = layout.canvas_size
    for x in guide_lines(width, layout.boards_x, layout.guide_offset[0]):
        a, b = max(x, x0, 0), min(x + GUIDE_WIDTH, x0 + w)
        if a < b:
            pixels[:, a - x0:b - x0] = GUIDE_COLOR
    for y in guide_lines(height, layout.boards_y, layout.guide_offset[1]):
        a, b = max(y, y0, 0), min(y + GUIDE_WIDTH, y0 + h)
        if a < b:
            pixels[a - y0:b - y0, :] = GUIDE_COLOR


def save_png(image, path):
    image.save(path, format="PNG", dpi=EXPORT_DPI, optimize=True)


# --- large patterns -------------------------------------------------------------------
#
# Patterns up to FULL_IMAGE_MAX_PIXELS are rendered as one image, exactly as
# before. Larger ones are rendered in horizontal strips: the preview is an
# exact reduction of the full-detail strips, and the PNG is streamed to disk
# strip by strip, so memory stays bounded.

FULL_IMAGE_MAX_PIXELS = 25_000_000      # one in-memory image (about 7 x 7 boards)
OVERVIEW_MAX_PIXELS = 8_000_000         # size of a reduced preview (sharper than full screen)
STRIP_MAX_PIXELS = 8_000_000            # pixels rendered at once
STREAM_PNG_MAX_PIXELS = 1_000_000_000   # largest single PNG written (about 3 GB uncompressed)


def render_strips(grid, layout, multiple=PITCH, max_pixels=None):
    """Yield (y0, strip image) covering the template top to bottom.

    Strip heights are multiples of `multiple` (except possibly the last)."""
    max_pixels = max_pixels or STRIP_MAX_PIXELS
    width, height = layout.canvas_size
    rows = max(multiple, (max_pixels // width) // multiple * multiple)
    for y0 in range(0, height, rows):
        yield y0, render_region(grid, layout, (0, y0, width, min(height, y0 + rows)))


def overview_factor(layout, max_pixels=None):
    """Smallest whole reduction factor that keeps the preview within max_pixels."""
    max_pixels = max_pixels or OVERVIEW_MAX_PIXELS
    width, height = layout.canvas_size
    factor = 1
    while -(-width // factor) * -(-height // factor) > max_pixels:
        factor += 1
    return factor


def render_overview(grid, layout, factor, progress=None):
    """The full template reduced by `factor` (box average), built strip by strip.

    Identical to render(grid, layout).reduce(factor), without ever holding the
    full-size image in memory."""
    width, height = layout.canvas_size
    out = Image.new("RGB", (-(-width // factor), -(-height // factor)))
    multiple = factor * max(1, PITCH // factor)
    for y0, strip in render_strips(grid, layout, multiple=multiple):
        out.paste(strip.reduce(factor) if factor > 1 else strip, (0, y0 // factor))
        if progress:
            progress(min(1.0, (y0 + strip.height) / height))
    return out


def _png_chunk(f, kind, data):
    f.write(struct.pack(">I", len(data)) + kind + data)
    f.write(struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF))


def save_png_streaming(grid, layout, path, progress=None):
    """Write the full-detail template as an RGB PNG, strip by strip.

    Returns the SHA-256 of the raw scanline data, for verify_png_streaming."""
    width, height = layout.canvas_size
    if width * height > STREAM_PNG_MAX_PIXELS:
        raise ValueError("Pattern is too large for a single PNG")
    digest = hashlib.sha256()
    compressor = zlib.compressobj(6)
    dpm = round(EXPORT_DPI[0] / 0.0254)  # 300 DPI = 11811 pixels per metre
    with open(path, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        _png_chunk(f, b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        _png_chunk(f, b"pHYs", struct.pack(">IIB", dpm, dpm, 1))
        for y0, strip in render_strips(grid, layout):
            pixels = np.asarray(strip).reshape(strip.height, width * 3)
            raw = np.concatenate([np.zeros((strip.height, 1), np.uint8), pixels], axis=1).tobytes()
            digest.update(raw)
            data = compressor.compress(raw)
            if data:
                _png_chunk(f, b"IDAT", data)
            if progress:
                progress(min(1.0, (y0 + strip.height) / height))
        _png_chunk(f, b"IDAT", compressor.flush())
        _png_chunk(f, b"IEND", b"")
    return digest.hexdigest()


def verify_png_streaming(path, expected_sha256):
    """Decode a PNG written by save_png_streaming and confirm its exact pixel data."""
    digest = hashlib.sha256()
    decompressor = zlib.decompressobj()
    with open(path, "rb") as f:
        if f.read(8) != b"\x89PNG\r\n\x1a\n":
            return False
        while True:
            header = f.read(8)
            if len(header) < 8:
                return False
            length, kind = struct.unpack(">I", header[:4])[0], header[4:]
            data = f.read(length)
            if struct.unpack(">I", f.read(4))[0] != zlib.crc32(kind + data) & 0xFFFFFFFF:
                return False
            if kind == b"IDAT":
                digest.update(decompressor.decompress(data))
            elif kind == b"IEND":
                digest.update(decompressor.flush())
                return digest.hexdigest() == expected_sha256
