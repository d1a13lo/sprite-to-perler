"""Pegboard charts and CSV reports, built from the authoritative bead grid.

Board convention: boards are numbered from the top-left of the arrangement as
seen in the preview, "R<row>C<column>" (R1C1 = top-left). Inside a board,
peg rows run 1-29 from top to bottom and peg columns 1-29 from left to right.
Colour numbers (#1, #2, ...) rank the original colours by bead count and are
the same in every chart and CSV.

Board information is only produced when the pegboard lines sit on bead
boundaries and every bead lies on a marked board; otherwise it would be
misleading.
"""
import csv
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from .layout import BOARD_PEGS, PITCH

CELL = 30          # chart pixels per peg
EMPTY = (255, 255, 255)
EMPTY_DOT = (175, 175, 175)  # marks a peg with no bead
OVERVIEW_EMPTY = (150, 150, 150)  # mid grey: black and white beads both stand out
GRID = (200, 200, 200)
GRID_5 = (120, 120, 120)
INK = (30, 30, 30)


def board_info_problem(alignment):
    """Why board charts/counts cannot be produced, or "" when they can."""
    if alignment.board_counts is None:
        return ("Pegboard lines are not between bead positions, so board divisions are not real. "
                "Reset Pegboard Lines to get board charts and counts.")
    if alignment.beads_outside_boards:
        return (f"{alignment.beads_outside_boards:,} beads fall outside the marked pegboards. "
                "Move the sprite or reset Pegboard Lines to get board charts and counts.")
    return ""


def color_numbers(grid):
    """{rgb: number} ranking original colours by bead count (1 = most used)."""
    return {rgb: i for i, (rgb, _) in enumerate(grid.color_counts(), start=1)}


def board_cells(grid, layout):
    """{(board_row, board_col): 29x29 object array of rgb tuples or None}.

    Every board of the layout is included (empty boards have no beads).
    """
    return dict(iter_board_cells(grid, layout))


def iter_board_cells(grid, layout):
    """Yield ((board_row, board_col), 29x29 cells) one board at a time.

    Each board is cut straight out of the authoritative grid, so large
    patterns never need every board in memory at once."""
    gx, gy = layout.guide_offset[0] // PITCH, layout.guide_offset[1] // PITCH
    ox, oy = layout.sprite_offset
    seen = 0
    for r in range(1, layout.boards_y + 1):
        for c in range(1, layout.boards_x + 1):
            cells = np.full((BOARD_PEGS, BOARD_PEGS), None, dtype=object)
            # Sprite rows/columns covered by this board.
            top, left = (r - 1) * BOARD_PEGS + gy - oy, (c - 1) * BOARD_PEGS + gx - ox
            y0, y1 = max(0, top), min(grid.height, top + BOARD_PEGS)
            x0, x1 = max(0, left), min(grid.width, left + BOARD_PEGS)
            if y0 < y1 and x0 < x1:
                occupied = grid.occupied[y0:y1, x0:x1]
                rgb = grid.rgb[y0:y1, x0:x1]
                for py, px in zip(*np.nonzero(occupied)):
                    cells[py + y0 - top, px + x0 - left] = tuple(rgb[py, px].tolist())
                seen += int(occupied.sum())
            yield (r, c), cells
    if seen != grid.total:
        raise ValueError("A bead lies outside the marked pegboards")


def _font(size):
    try:
        return ImageFont.load_default(size=size)
    except TypeError:  # very old Pillow without scalable default font
        return ImageFont.load_default()


def _text_color(rgb):
    luminance = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
    return (0, 0, 0) if luminance > 140 else (255, 255, 255)


def render_board_chart(cells, key, layout, numbers, supply_names=None):
    """Assembly chart for one board: original colours, colour numbers, peg numbering."""
    supply_names = supply_names or {}
    r, c = key
    counts = {}
    for rgb in cells.ravel():
        if rgb is not None:
            counts[rgb] = counts.get(rgb, 0) + 1
    legend = sorted(counts, key=lambda rgb: numbers[rgb])
    title_font, label_font, cell_font = _font(22), _font(14), _font(12)
    margin, top = 34, 96
    grid_px = BOARD_PEGS * CELL
    legend_rows = max(1, math.ceil(len(legend) / 2))
    width = margin + grid_px + 20
    height = top + grid_px + 30 + legend_rows * 24 + 20
    img = Image.new("RGB", (width, height), (255, 255, 255))
    d = ImageDraw.Draw(img)
    total = sum(counts.values())
    d.text((margin, 12), f"Board R{r}C{c}  ·  {total:,} beads", fill=INK, font=title_font)
    d.text((margin, 42), f"Row {r} of {layout.boards_y}, column {c} of {layout.boards_x} "
                         "(R1C1 = top-left, as in the preview)", fill=INK, font=label_font)
    # Mini map of the whole arrangement with this board highlighted.
    s = 12
    mx = width - 20 - layout.boards_x * s
    for br in range(layout.boards_y):
        for bc in range(layout.boards_x):
            box = [mx + bc * s, 10 + br * s, mx + bc * s + s - 2, 10 + br * s + s - 2]
            d.rectangle(box, fill=INK if (br + 1, bc + 1) == key else (225, 225, 225))
    gx0, gy0 = margin, top
    for i in range(BOARD_PEGS):  # peg numbers
        label = str(i + 1)
        d.text((gx0 + i * CELL + CELL / 2, gy0 - 14), label, fill=INK, font=cell_font, anchor="mm")
        d.text((gx0 - 16, gy0 + i * CELL + CELL / 2), label, fill=INK, font=cell_font, anchor="mm")
    for py in range(BOARD_PEGS):
        for px in range(BOARD_PEGS):
            rgb = cells[py, px]
            box = [gx0 + px * CELL, gy0 + py * CELL, gx0 + (px + 1) * CELL, gy0 + (py + 1) * CELL]
            d.rectangle(box, fill=EMPTY if rgb is None else rgb)
            if rgb is None:
                cx, cy = box[0] + CELL / 2, box[1] + CELL / 2
                d.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=EMPTY_DOT)
            else:
                d.text((box[0] + CELL / 2, box[1] + CELL / 2), str(numbers[rgb]),
                       fill=_text_color(rgb), font=cell_font, anchor="mm")
    for i in range(BOARD_PEGS + 1):
        color = GRID_5 if i % 5 == 0 or i == BOARD_PEGS else GRID
        d.line([gx0 + i * CELL, gy0, gx0 + i * CELL, gy0 + grid_px], fill=color)
        d.line([gx0, gy0 + i * CELL, gx0 + grid_px, gy0 + i * CELL], fill=color)
    ly = gy0 + grid_px + 24
    col_w = grid_px // 2
    for i, rgb in enumerate(legend):
        x, y = gx0 + (i % 2) * col_w, ly + (i // 2) * 24
        d.rectangle([x, y, x + 18, y + 18], fill=rgb, outline=GRID_5)
        name = supply_names.get(rgb, "")
        text = f"#{numbers[rgb]}  {'#%02X%02X%02X' % rgb}  {counts[rgb]} bead{'s' if counts[rgb] != 1 else ''}" + (f"  ({name})" if name else "")
        d.text((x + 26, y + 2), text, fill=INK, font=label_font)
    return img


def render_board_layout(grid, layout, board_totals):
    """Map of the whole arrangement with board ids and bead totals.

    Each bead is a small square (at most 8 px; smaller for large patterns so
    the map stays about 4,000 px across or less)."""
    s = max(1, min(8, 4000 // max(layout.columns, layout.rows)))
    beads = np.empty((layout.rows, layout.columns, 3), np.uint8)
    beads[...] = OVERVIEW_EMPTY
    ox, oy = layout.sprite_offset
    area = beads[oy:oy + grid.height, ox:ox + grid.width]
    area[grid.occupied[:area.shape[0], :area.shape[1]]] = \
        grid.rgb[:area.shape[0], :area.shape[1]][grid.occupied[:area.shape[0], :area.shape[1]]]
    w, h = layout.columns * s, layout.rows * s
    img = Image.new("RGB", (w + 40, h + 70), (255, 255, 255))
    img.paste(Image.fromarray(np.repeat(np.repeat(beads, s, axis=0), s, axis=1)), (20, 50))
    d = ImageDraw.Draw(img)
    d.text((20, 10), "Board layout (R1C1 = top-left)", fill=INK, font=_font(18))
    gx, gy = layout.guide_offset[0] // PITCH, layout.guide_offset[1] // PITCH
    board_px = BOARD_PEGS * s
    font = _font(max(8, min(16, board_px // 8)))
    for r in range(1, layout.boards_y + 1):
        for c in range(1, layout.boards_x + 1):
            x0 = 20 + ((c - 1) * BOARD_PEGS + gx) * s
            y0 = 50 + ((r - 1) * BOARD_PEGS + gy) * s
            d.rectangle([x0, y0, x0 + board_px, y0 + board_px], outline=(255, 0, 160),
                        width=2 if s > 2 else 1)
            if board_px >= 40:  # labels only where they fit
                d.text((x0 + 4, y0 + 4), f"R{r}C{c}: {board_totals.get((r, c), 0):,}",
                       fill=(255, 255, 255), font=font, stroke_width=2, stroke_fill=(0, 0, 0))
    return img


# --- CSV reports -----------------------------------------------------------------------

def _hex(rgb):
    return "#%02X%02X%02X" % rgb


def write_original_colors_csv(path, grid, supply):
    numbers = color_numbers(grid)
    by_rgb = {s.rgb: s for s in supply.sources}
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Color #", "Hex", "Red", "Green", "Blue", "Beads",
                    "Suggested Perler color", "Product code", "Match Delta E (CIEDE2000)"])
        for rgb, n in grid.color_counts():
            s = by_rgb[rgb]
            w.writerow([numbers[rgb], _hex(rgb), *rgb, n,
                        s.color.name if s.color else "UNMATCHED", s.color.code if s.color else "",
                        "" if s.color is None else f"{s.delta_e:.1f}"])
        w.writerow(["TOTAL", "", "", "", "", grid.total, "", "", ""])


def write_supplies_csv(path, supply):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Perler color", "Product code", "Digital hex", "Beads", "Original colors",
                    "Largest match Delta E (CIEDE2000)", "Color data source", "Data confidence", "Notes"])
        for line in supply.supplies:
            originals = " ".join(_hex(rgb) for rgb in line.sources)
            if line.color is None:
                w.writerow(["UNMATCHED", "", "", line.beads, originals, "", "", "",
                            supply.error or "no palette color could be suggested"])
                continue
            c = line.color
            w.writerow([c.name, c.code, c.hex, line.beads, originals, f"{line.max_delta_e:.1f}",
                        c.source, c.confidence, c.notes])
        w.writerow(["TOTAL", "", "", supply.total, "", "", "", "",
                    "Digital approximations only; physical bead colors vary."])


def write_board_counts_csv(path, grid, layout, board_counts):
    """One row per board (all boards, R1C1 first) with per-colour bead counts."""
    colors = [rgb for rgb, _ in grid.color_counts()]
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Board", "Board row", "Board column", "Total beads"] + [_hex(c) for c in colors])
        totals = {c: 0 for c in colors}
        for r in range(1, layout.boards_y + 1):
            for c in range(1, layout.boards_x + 1):
                counts = board_counts.get((r, c), {})
                for rgb, n in counts.items():
                    totals[rgb] += n
                w.writerow([f"R{r}C{c}", r, c, sum(counts.values())] +
                           [counts.get(x, 0) for x in colors])
        w.writerow(["ALL BOARDS", "", "", sum(totals.values())] + [totals[x] for x in colors])


def export_charts_and_reports(folder, grid, layout, alignment, supply, stem, progress=None):
    """Write CSV reports and (when valid) board charts into an existing folder.

    Returns (list of written file names, reason board files were skipped or "").
    Charts are drawn one board at a time, so memory stays small for large patterns.
    """
    folder = Path(folder)
    written = []
    write_original_colors_csv(folder / f"{stem}_original_colors.csv", grid, supply)
    write_supplies_csv(folder / f"{stem}_perler_supplies.csv", supply)
    written += [f"{stem}_original_colors.csv", f"{stem}_perler_supplies.csv"]
    problem = board_info_problem(alignment)
    if problem:
        return written, problem
    write_board_counts_csv(folder / f"{stem}_board_counts.csv", grid, layout, alignment.board_counts)
    written.append(f"{stem}_board_counts.csv")
    numbers = color_numbers(grid)
    names = {s.rgb: s.color.name for s in supply.sources if s.color}
    totals = {k: sum(v.values()) for k, v in alignment.board_counts.items()}
    render_board_layout(grid, layout, totals).save(folder / f"{stem}_board_layout.png")
    written.append(f"{stem}_board_layout.png")
    for i, (key, cells) in enumerate(iter_board_cells(grid, layout), start=1):
        if totals.get(key):  # empty boards need no chart; they are listed in the CSV
            name = f"{stem}_board_R{key[0]}C{key[1]}.png"
            render_board_chart(cells, key, layout, numbers, names).save(folder / name)
            written.append(name)
        if progress:
            progress(i / layout.total_boards)
    return written, ""
