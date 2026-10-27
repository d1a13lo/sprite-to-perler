"""Public regression tests: only the project's own example sprites (docs/examples),
its committed sample output (docs/sample-output) and synthetic images. They need no
private reference files.

Covers the universal auto-fit, bead counts, peg alignment, original colours and
transparency, pegboard lines, board counts, exports, layer adjustments, GIF input,
background handling, large patterns and the bundled assets.
"""
import csv
import hashlib
import importlib
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication

from conftest import ROOT, app_grid
from perler_app.pattern import build_pattern, export_charts, export_png, load_pattern
from perler_engine import (BackgroundDecisionNeeded, InputError, Layout, auto_layout, board_counts,
                           crop_to_beads, load_sprite, render)
from perler_engine.alignment import check_alignment, clamp_sprite_offset
from perler_engine.charts import board_cells
from perler_engine.palette import ciede2000, load_palette, supply_report_for
from perler_engine.render import RING_TILE_SHA256, ring_tile
from perler_engine.sprite import prepare_sprite

R = importlib.import_module("perler_engine.render")
EXAMPLES = ROOT / "docs" / "examples"
SAMPLE = ROOT / "docs" / "sample-output"
PIP = EXAMPLES / "pip_mushroom.png"
GLOB = EXAMPLES / "glob_slime_solid_background.png"
TWINKLE = EXAMPLES / "twinkle_star_animated.gif"
DUSK = EXAMPLES / "dusk_valley_large.png"
BACKGROUND = (0x2B, 0x2B, 0x2B)
RED, BLACK = (200, 40, 10, 255), (0, 0, 0, 255)


def placed(grid, layout):
    """Every bead as (layout row, layout column, rgb)."""
    ys, xs = np.nonzero(grid.occupied)
    return sorted(zip((ys + layout.sprite_offset[1]).tolist(), (xs + layout.sprite_offset[0]).tolist(),
                      map(tuple, grid.rgb[ys, xs].tolist())))


def visible_box(grid):
    ys, xs = np.nonzero(grid.occupied)
    return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def sprite(width, height, pixels):
    """Transparent image with the given {(x, y): rgba} pixels."""
    a = np.zeros((height, width, 4), np.uint8)
    for (x, y), colour in pixels.items():
        a[y, x] = colour
    return prepare_sprite(Image.fromarray(a, "RGBA"), background="keep")


def block(width, height, left, top, w, h):
    return sprite(width, height, {(x, y): (RED if (x + y) % 3 else BLACK)
                                  for x in range(left, left + w) for y in range(top, top + h)})


def assert_fitted(original, layout):
    """Smallest whole-board rectangle around the visible pixels, centred, nothing lost."""
    left, top, right, bottom = visible_box(original)
    w, h = right - left, bottom - top
    assert (layout.boards_x, layout.boards_y) == (-(-w // 29), -(-h // 29))
    assert layout.sprite_offset == ((layout.columns - w) // 2, (layout.rows - h) // 2)


def assert_same_beads_shifted(original, fitted, layout):
    """Every original bead, same colour, all moved by one common whole-bead offset."""
    left, top, _, _ = visible_box(original)
    shift = (layout.sprite_offset[1] - top, layout.sprite_offset[0] - left)
    assert placed(fitted, layout) == [(r + shift[0], c + shift[1], rgb)
                                      for r, c, rgb in placed(original, Layout(1, 1))]


def peg_samples(image, layout):
    """Colour of every peg at a point the bead-ring drawing leaves uncovered
    (ring tile row 4, column 12): the bead's own colour, or the background."""
    a = np.asarray(image)
    rows = np.arange(layout.rows) * 25 + 4
    cols = np.arange(layout.columns) * 25 + 12
    return a[rows][:, cols]


def sample_png(name):
    return np.asarray(Image.open(SAMPLE / name).convert("RGB"))


# --- the project's own examples -----------------------------------------------------------------

def test_pip_matches_the_committed_sample_pattern_exactly():
    pattern = load_pattern(PIP)
    assert (pattern.layout.boards_x, pattern.layout.boards_y) == (2, 2)
    assert (pattern.grid.width, pattern.grid.height, pattern.grid.total) == (38, 34, 886)
    assert np.array_equal(np.asarray(pattern.image), sample_png("pip_mushroom_bead_pattern.png"))
    assert any("40 × 40 pixels, the visible sprite 38 × 34" in w for w in pattern.grid.warnings)


def test_pip_charts_and_csv_match_the_committed_sample_output(tmp_path):
    pattern = load_pattern(PIP)
    folder, files, skipped = export_charts(pattern, supply_report_for(pattern.grid), tmp_path)
    expected = SAMPLE / "pip_mushroom_bead_charts"
    assert skipped == "" and sorted(os.listdir(folder)) == sorted(os.listdir(expected))
    for name in os.listdir(expected):
        if name.endswith(".csv"):
            assert (folder / name).read_text(encoding="utf-8-sig") == \
                (expected / name).read_text(encoding="utf-8-sig"), name
        else:
            assert np.array_equal(np.asarray(Image.open(folder / name).convert("RGB")),
                                  np.asarray(Image.open(expected / name).convert("RGB"))), name
    with open(folder / "pip_mushroom_board_counts.csv", encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    assert int(rows[-1]["Total beads"]) == 886


@pytest.mark.parametrize("name,background", [("glob_slime_solid_background.png", "auto"),
                                             ("glob_slime_white_background.png", "outside")])
def test_glob_needs_one_board_and_keeps_every_bead(name, background):
    path = EXAMPLES / name
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    original = load_sprite(path, background=background)
    assert (auto_layout(original).boards_x, auto_layout(original).boards_y) == (2, 1)
    pattern = load_pattern(path, background=background)
    grid, layout = pattern.grid, pattern.layout
    assert (layout.boards_x, layout.boards_y, grid.width, grid.height) == (1, 1, 28, 18)
    assert layout.sprite_offset == (0, 5)  # (29 - 28) // 2, (29 - 18) // 2
    assert_same_beads_shifted(original, grid, layout)
    assert grid.total == original.total == 422 and grid.color_counts() == original.color_counts()
    assert sum(sum(c.values()) for c in board_counts(grid, layout).values()) == 422
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before  # source never written


def test_glob_background_question_and_removal_modes():
    white = EXAMPLES / "glob_slime_white_background.png"
    with pytest.raises(BackgroundDecisionNeeded) as asked:
        load_pattern(white)
    assert asked.value.interior_pixels == 2  # the white eye highlights
    outside = load_pattern(white, background="outside").grid
    everywhere = load_pattern(white, background="all").grid
    assert (outside.total, everywhere.total) == (422, 420)
    solid = load_pattern(GLOB).grid
    assert solid.color_counts() == outside.color_counts()
    assert "Removed background colour #FF00FF." in solid.warnings


def test_twinkle_gif_uses_the_first_frame():
    pattern = load_pattern(TWINKLE)
    with Image.open(TWINKLE) as im:
        im.seek(0)
        first = int((np.asarray(im.convert("RGBA"))[..., 3] >= 128).sum())
    assert pattern.grid.total == first == 321
    assert (pattern.grid.width, pattern.grid.height, pattern.layout.boards_x, pattern.layout.boards_y) == (23, 23, 1, 1)
    assert any("animated (2 frames)" in w for w in pattern.grid.warnings)


def test_large_example_is_fitted():
    original = load_sprite(DUSK, background="keep")
    pattern = load_pattern(DUSK, background="keep")
    assert_fitted(original, pattern.layout)
    assert_same_beads_shifted(original, pattern.grid, pattern.layout)


def test_large_example_needs_a_decision_and_previews_exactly():
    with pytest.raises(BackgroundDecisionNeeded):
        load_pattern(DUSK)
    pattern = build_pattern(DUSK, background="keep")
    grid, layout, s = pattern.grid, pattern.layout, pattern.scale
    assert (layout.boards_x, layout.boards_y, grid.total) == (12, 9, 320 * 240)
    assert s > 1  # reduced preview
    full = R.render_region(grid, layout, (0, 0, 40 * s, 40 * s))
    assert np.array_equal(np.asarray(pattern.image)[:40, :40], np.asarray(full.reduce(s)))


def test_not_an_image_is_refused():
    with pytest.raises(InputError, match="not a readable image"):
        load_pattern(EXAMPLES / "not_an_image.png")


# --- peg alignment, colours, transparency, pegboard lines, counts --------------------------------

def test_every_peg_shows_its_original_colour_or_the_background():
    a = np.zeros((33, 45, 4), np.uint8)
    rng = np.random.default_rng(7)
    a[3:30, 2:43, :3] = rng.integers(0, 256, (27, 41, 3), dtype=np.uint8)
    a[3:30, 2:43, 3] = 255
    a[10:14, 20:25, 3] = 0  # internal transparent hole
    path_grid = prepare_sprite(Image.fromarray(a, "RGBA"))
    grid = crop_to_beads(path_grid)
    layout = auto_layout(grid)
    samples = peg_samples(render(grid, layout, guides=False), layout)
    expected = np.tile(np.array(BACKGROUND, np.uint8), (layout.rows, layout.columns, 1))
    ox, oy = layout.sprite_offset
    region = expected[oy:oy + grid.height, ox:ox + grid.width]
    region[grid.occupied] = grid.rgb[grid.occupied]
    assert np.array_equal(samples, expected)
    assert not grid.occupied[10 - 3, 20 - 2]  # the hole stays empty


def test_partial_transparency_rule():
    a = np.zeros((4, 4, 4), np.uint8)
    a[..., :3] = 90
    a[0, :, 3] = 255
    a[1, :, 3] = 200   # at least half visible: full bead
    a[2, :, 3] = 100   # fainter: empty
    grid = prepare_sprite(Image.fromarray(a, "RGBA"))
    assert grid.total == 8 and grid.occupied[:2].all() and not grid.occupied[2:].any()
    assert any("8 partially transparent pixels" in w for w in grid.warnings)


def test_pegboard_lines_are_white_3px_every_725px_and_on_top():
    grid = block(58, 29, 0, 0, 58, 29)  # dark beads everywhere
    layout = auto_layout(grid)
    assert layout.canvas_size == (1450, 725)
    image = np.asarray(render(grid, layout))
    white = np.all(image == 255, axis=2)
    assert np.nonzero(white.all(axis=0))[0].tolist() == [0, 1, 2, 725, 726, 727, 1447, 1448, 1449]
    assert np.nonzero(white.all(axis=1))[0].tolist() == [0, 1, 2, 722, 723, 724]
    plain = np.asarray(render(grid, layout, guides=False))
    assert np.array_equal(image[~white], plain[~white])


def test_board_counts_follow_bead_positions():
    grid = crop_to_beads(block(60, 20, 5, 4, 40, 10))
    layout = auto_layout(grid)
    assert (layout.boards_x, layout.boards_y, layout.sprite_offset) == (2, 1, (9, 9))
    counts = board_counts(grid, layout)
    assert {k: sum(v.values()) for k, v in counts.items()} == {(1, 1): 200, (1, 2): 200}
    cells = board_cells(grid, layout)
    assert sum(c is not None for cell in cells.values() for c in cell.ravel()) == 400


# --- universal auto-fit: synthetic boundary cases -------------------------------------------------

@pytest.mark.parametrize("size,box,boards", [
    ((40, 40), (5, 6, 29, 29), (1, 1)),     # exactly one board of visible pixels
    ((40, 40), (5, 6, 30, 29), (2, 1)),     # one column more -> two boards wide
    ((31, 33), (1, 2, 29, 29), (1, 1)),     # margin on every side, fits one board
    ((64, 20), (0, 0, 58, 20), (2, 1)),     # touches the left/top edge, margin right
    ((100, 100), (70, 80, 30, 20), (2, 1)),  # far corner: still the smallest rectangle
])
def test_smallest_board_rectangle_and_centring(size, box, boards):
    original = block(*size, *box)
    fitted = crop_to_beads(original)
    layout = auto_layout(fitted)
    assert (layout.boards_x, layout.boards_y) == boards
    assert_fitted(original, layout)
    assert_same_beads_shifted(original, fitted, layout)
    assert check_alignment(fitted, layout).valid


def test_single_pixel_is_centred_on_one_board():
    fitted = crop_to_beads(sprite(100, 100, {(73, 5): RED}))
    layout = auto_layout(fitted)
    assert (layout.boards_x, layout.boards_y, layout.sprite_offset) == (1, 1, (14, 14))


def test_internal_gaps_and_empty_boards_inside_the_rectangle_are_kept():
    # Beads 60 apart diagonally: 3 x 3 boards, most of them empty but kept.
    original = sprite(90, 90, {(10, 12): RED, (70, 72): BLACK, (40, 42): RED})
    fitted = crop_to_beads(original)
    layout = auto_layout(fitted)
    assert (fitted.width, fitted.height, layout.boards_x, layout.boards_y) == (61, 61, 3, 3)
    assert fitted.total == 3 and fitted.occupied[30, 30]  # middle bead kept in place
    assert_same_beads_shifted(original, fitted, layout)
    assert len(board_counts(fitted, layout)) == 3  # only diagonal boards hold beads; others stay


def test_no_margin_means_same_grid():
    original = block(30, 20, 0, 0, 30, 20)
    assert crop_to_beads(original) is original


def test_large_sprite_is_fitted_without_losing_beads():
    original = block(700, 650, 13, 40, 600, 590)
    fitted = crop_to_beads(original)
    layout = auto_layout(fitted)
    assert (layout.boards_x, layout.boards_y) == (21, 21)  # 700 x 650 needed 25 x 23
    assert_same_beads_shifted(original, fitted, layout)


def test_large_pattern_preview_and_export_still_agree(tmp_path):
    a = np.zeros((300, 280, 4), np.uint8)
    a[20:290, 15:260] = (30, 160, 90, 255)
    a[100:120, 100:120, 3] = 0  # internal hole
    path = tmp_path / "big.png"
    Image.fromarray(a, "RGBA").save(path)
    pattern = build_pattern(path)
    assert (pattern.layout.boards_x, pattern.layout.boards_y) == (9, 10)  # 280 x 300 needed 10 x 11
    assert pattern.grid.total == int((a[..., 3] == 255).sum())
    out = export_png(pattern, tmp_path / "big pattern.png")
    with Image.open(out) as im:
        assert im.size == pattern.layout.canvas_size


# --- exports ---------------------------------------------------------------------------------------

def test_png_export_equals_preview_and_never_overwrites_the_sprite(tmp_path):
    pattern = load_pattern(PIP)
    out = export_png(pattern, tmp_path / "pip.png")
    with Image.open(out) as saved:
        assert saved.info["dpi"] == pytest.approx((300, 300), abs=0.01)
        assert np.array_equal(np.asarray(saved.convert("RGB")), np.asarray(pattern.image))
    copy = tmp_path / "sprite.png"
    copy.write_bytes(PIP.read_bytes())
    own = load_pattern(copy)
    with pytest.raises(OSError, match="original sprite"):
        export_png(own, copy)
    assert copy.read_bytes() == PIP.read_bytes()
    assert sorted(p.name for p in tmp_path.iterdir()) == ["pip.png", "sprite.png"]  # no temp files


# --- the window: layer adjustments and exports ----------------------------------------------------

@pytest.fixture
def window():
    from perler_app.window import MainWindow
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.errors, w.notices = [], []
    w.show_error = lambda title, message: w.errors.append((title, message))
    w.show_notice = lambda title, message: w.notices.append((title, message))
    w.show()
    app.processEvents()
    yield w
    w.close()


def wait_for_export():
    QThreadPool.globalInstance().waitForDone()
    QApplication.instance().processEvents()


def shown(window):
    q = window.view.displayed_image().convertToFormat(window.view.displayed_image().Format.Format_RGB888)
    a = np.frombuffer(q.constBits(), np.uint8, q.sizeInBytes()).reshape(q.height(), q.bytesPerLine())
    return a[:, :q.width() * 3].reshape(q.height(), q.width(), 3).copy()


def test_window_shows_pip_and_its_information(window):
    assert window.open_file(PIP)
    window.wait_for_supply()
    info = {k: v.text() for k, v in window.info.items()}
    assert info == {"size": "38 × 34 beads", "beads": "886", "colors": "10",
                    "grid": "2 × 2", "boards": "4", "occupied": "4"}
    assert "Empty outer margins ignored" in window.notes_label.text()
    assert np.array_equal(shown(window), sample_png("pip_mushroom_bead_pattern.png"))
    assert sum(line.beads for line in window.supply.supplies) == 886


def test_layer_adjustments_warnings_export_and_reset(window, tmp_path):
    from perler_app.window import GUIDES, RINGS, SPRITE
    window.open_file(PIP)
    auto = window.pattern.auto
    assert auto.sprite_offset == (10, 12)
    window.enter_adjust_mode()
    window.select_layer(SPRITE)
    window.nudge(3, 2)
    window.wait_for_render()
    assert window.pattern.layout.sprite_offset == (13, 14)
    assert "still aligned" in window.alignment_label.text() and window.info["occupied"].text() == "4"
    assert window.pattern.grid.total == 886
    window.nudge(-30, 0)  # pushed past the left edge: stops at column 0, no bead lost
    window.wait_for_render()
    assert window.pattern.layout.sprite_offset == (0, 14) and window.pattern.grid.total == 886
    window.select_layer(RINGS)
    window.nudge(6, 0)
    window.select_layer(GUIDES)
    window.nudge(0, 4)
    window.wait_for_render()
    assert "Misaligned" in window.alignment_label.text()
    assert window.info["occupied"].text() == "unavailable"
    out = tmp_path / "adjusted.png"
    window.start_export(str(out))
    wait_for_export()
    assert window.errors == []
    saved = np.asarray(Image.open(out).convert("RGB"))
    assert np.array_equal(saved, shown(window))
    assert np.array_equal(saved, np.asarray(render(app_grid(PIP), window.pattern.layout)))
    window.reset_all_layers()
    window.wait_for_render()
    assert window.pattern.layout == auto
    assert np.array_equal(shown(window), sample_png("pip_mushroom_bead_pattern.png"))


def test_glob_export_charts_and_adjustment(window, tmp_path):
    from perler_app.window import SPRITE
    assert window.open_file(GLOB)
    window.wait_for_supply()
    assert window.info["grid"].text() == "1 × 1" and window.info["beads"].text() == "422"
    out = tmp_path / "glob.png"
    window.start_export(str(out))
    wait_for_export()
    saved = np.asarray(Image.open(out).convert("RGB"))
    assert saved.shape == (725, 725, 3) and np.array_equal(saved, shown(window))
    window.start_chart_export(str(tmp_path))
    wait_for_export()
    assert window.errors == []
    folder = tmp_path / "glob_slime_solid_background_bead_charts"
    assert len([f for f in os.listdir(folder) if "_board_R" in f]) == 1
    with open(folder / "glob_slime_solid_background_board_counts.csv", encoding="utf-8-sig", newline="") as f:
        assert int(list(csv.DictReader(f))[-1]["Total beads"]) == 422
    cells = board_cells(window.pattern.grid, window.pattern.layout)
    assert list(cells) == [(1, 1)] and sum(c is not None for c in cells[1, 1].ravel()) == 422
    # Manual adjustment still works and stays on the board.
    window.enter_adjust_mode()
    window.select_layer(SPRITE)
    window.nudge(5, 20)
    window.wait_for_render()
    assert window.pattern.layout.sprite_offset == (1, 11)
    assert clamp_sprite_offset(window.pattern.grid, window.pattern.layout, (5, 20)) == (1, 11)
    assert window.pattern.grid.total == 422 and window.info["occupied"].text() == "1"
    window.reset_all_layers()
    window.wait_for_render()
    assert window.pattern.layout == window.pattern.auto


# --- bundled assets and colour data ---------------------------------------------------------------

def test_bundled_ring_asset_and_palette():
    tile = ring_tile()
    assert tile.shape == (25, 25, 4)
    assert hashlib.sha256(tile.tobytes()).hexdigest() == RING_TILE_SHA256
    palette = load_palette()
    assert (len(palette.colors), len(palette.excluded)) == (118, 11)
    # Sharma, Wu and Dalal (2005), pair 1.
    assert ciede2000(np.array([50.0, 2.6772, -79.7751]), np.array([50.0, 0.0, -82.7485])) == \
        pytest.approx(2.0425, abs=1e-4)
    assert supply_report_for(load_pattern(PIP).grid).total == 886
