"""Processing used by the interface: one sprite file -> one finished pattern.

All bead data comes from the engine. Patterns up to the engine's
FULL_IMAGE_MAX_PIXELS keep one full-detail image that is both the preview and
the exported PNG. Larger patterns keep an exact reduced overview for the
preview (scale > 1); their PNG is streamed from the same renderer at full
detail, and counts and charts always come from the bead grid.
"""
import importlib
import os
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image

from perler_engine import auto_layout, crop_to_beads, load_sprite, render, save_png
from perler_engine.alignment import check_alignment

# The render module itself (the package exposes a function with the same name);
# its size limits are read at call time.
engine_render = importlib.import_module("perler_engine.render")
from perler_engine.charts import export_charts_and_reports


@dataclass(frozen=True, eq=False)
class Pattern:
    source: Path
    grid: object
    auto: object        # automatic layout, the reliable default
    layout: object      # current layout (equal to `auto` unless adjusted)
    image: object       # preview image for `layout`, or None while it is being rendered
    alignment: object
    scale: int = 1      # preview = full template reduced by this factor (1 = full detail)

    @property
    def adjusted(self):
        return self.layout != self.auto

    @property
    def occupied_boards(self):
        counts = self.alignment.board_counts
        return None if counts is None else len(counts)

    @property
    def canvas_pixels(self):
        width, height = self.layout.canvas_size
        return width * height

    @property
    def png_possible(self):
        return self.canvas_pixels <= engine_render.STREAM_PNG_MAX_PIXELS


def is_large(layout):
    width, height = layout.canvas_size
    return width * height > engine_render.FULL_IMAGE_MAX_PIXELS


def preview_scale(layout):
    return engine_render.overview_factor(layout) if is_large(layout) else 1


def render_preview(grid, layout, progress=None):
    """(preview image, scale) for a layout."""
    scale = preview_scale(layout)
    if scale == 1:
        return render(grid, layout), 1
    return engine_render.render_overview(grid, layout, scale, progress), scale


def load_pattern(path, background="auto"):
    """Load and lay out a sprite on the fewest pegboards that hold its visible
    pixels, centred. Small patterns are rendered straight away; for large ones
    `image` is None until with_layout renders the preview."""
    path = Path(path)
    grid = crop_to_beads(load_sprite(path, background=background))
    layout = auto_layout(grid)
    image, scale = (render(grid, layout), 1) if not is_large(layout) else (None, preview_scale(layout))
    return Pattern(source=path, grid=grid, auto=layout, layout=layout, image=image,
                   alignment=check_alignment(grid, layout), scale=scale)


def build_pattern(path, background="auto"):
    """Load a sprite and render its preview, whatever its size."""
    pattern = load_pattern(path, background)
    return pattern if pattern.image is not None else with_layout(pattern, pattern.layout)


def with_layout(pattern, layout, progress=None):
    """Same sprite and bead grid, rendered with the given layer positions."""
    image, scale = render_preview(pattern.grid, layout, progress)
    return Pattern(source=pattern.source, grid=pattern.grid, auto=pattern.auto, layout=layout,
                   image=image, alignment=check_alignment(pattern.grid, layout), scale=scale)


def png_too_large_message(pattern):
    width, height = pattern.layout.canvas_size
    return (f"This pattern would be one {width:,} × {height:,} pixel PNG "
            f"({pattern.canvas_pixels / 1e6:,.0f} megapixels), larger than the "
            f"{engine_render.STREAM_PNG_MAX_PIXELS / 1e6:,.0f}-megapixel limit for a single file. "
            "Use Export Charts & CSV instead: it saves every pegboard as its own chart, plus the "
            "board layout and all bead counts.")


def _not_allowed(folder):
    return OSError(f"Windows did not allow saving in “{folder}”. Choose another folder, "
                   "such as Documents or Desktop.")


def export_png(pattern, destination, progress=None):
    """Write the full-detail pattern PNG and confirm its pixels before keeping it.

    The file is written to a temporary name first so a failure never leaves a
    half-written PNG, and the original sprite can never be overwritten.
    """
    destination = Path(destination).resolve()
    if destination == pattern.source.resolve():
        raise OSError("The pattern cannot be saved over the original sprite file.")
    if not pattern.png_possible:
        raise OSError(png_too_large_message(pattern))
    try:
        fd, temp = tempfile.mkstemp(suffix=".png", prefix=".saving_", dir=destination.parent)
    except PermissionError:
        raise _not_allowed(destination.parent) from None
    os.close(fd)
    try:
        if pattern.scale == 1:
            save_png(pattern.image, temp)
            with Image.open(temp) as saved:
                if not np.array_equal(np.asarray(saved.convert("RGB")), np.asarray(pattern.image)):
                    raise OSError("The saved PNG did not match the preview; nothing was saved.")
        else:  # large: stream strips to disk, then verify the decoded pixel data
            digest = engine_render.save_png_streaming(pattern.grid, pattern.layout, temp, progress)
            if not engine_render.verify_png_streaming(temp, digest):
                raise OSError("The saved PNG did not match the rendered pattern; nothing was saved.")
        try:
            os.replace(temp, destination)
        except PermissionError:
            raise OSError(f"“{destination.name}” could not be replaced. It may be open in another "
                          "program or read-only. Close it or choose another name.") from None
    finally:
        if os.path.exists(temp):
            os.remove(temp)
    return destination


def export_charts(pattern, supply, parent, progress=None):
    """Write CSV reports and board charts into a new folder inside `parent`.

    Nothing existing is overwritten: the folder gets a fresh name, and it only
    appears once every file has been written. Returns (folder, files, skipped).
    """
    parent = Path(parent)
    stem = pattern.source.stem
    target, n = parent / f"{stem}_bead_charts", 2
    while target.exists():
        target, n = parent / f"{stem}_bead_charts ({n})", n + 1
    try:
        temp = Path(tempfile.mkdtemp(prefix=".saving_", dir=parent))
    except PermissionError:
        raise _not_allowed(parent) from None
    try:
        files, skipped = export_charts_and_reports(temp, pattern.grid, pattern.layout,
                                                   pattern.alignment, supply, stem, progress)
        os.replace(temp, target)
    except BaseException:
        shutil.rmtree(temp, ignore_errors=True)
        raise
    return target, files, skipped
