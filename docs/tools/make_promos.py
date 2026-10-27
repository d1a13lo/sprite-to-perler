"""Build the before-and-after promotional images and copy sample exports.

"After" images are real outputs: the app's own exported PNG for Pip (from
capture_screens.ps1) and the same verified engine for Glob and Dusk Valley.
"Before" images are the original sprites enlarged by whole pixels (labelled).
    python docs/tools/make_promos.py
"""
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from perler_engine import auto_layout, crop_to_beads, load_sprite, prepare_sprite, render  # noqa: E402

EXPORTS = Path("C:/SpriteToPerlerDocs")
EXAMPLES = ROOT / "docs" / "examples"
PROMO = ROOT / "docs" / "promo"
IMAGES = ROOT / "docs" / "images"
SAMPLE = ROOT / "docs" / "sample-output"
BG, PANEL, TEXT, SECONDARY, ACCENT = (23, 25, 28), (36, 39, 43), (240, 242, 245), (170, 177, 187), (80, 106, 134)
BOLD = "C:/Windows/Fonts/segoeuib.ttf"
REGULAR = "C:/Windows/Fonts/segoeui.ttf"


def font(path, size):
    return ImageFont.truetype(path, size)


def enlarge(sprite, box):
    """Whole-pixel enlargement on a checkerboard (shows transparency)."""
    scale = max(1, min(box[0] // sprite.width, box[1] // sprite.height))
    big = sprite.resize((sprite.width * scale, sprite.height * scale), Image.Resampling.NEAREST)
    checker = Image.new("RGBA", big.size, (58, 62, 68, 255))
    d = ImageDraw.Draw(checker)
    step = max(8, scale)
    for y in range(0, big.height, step):
        for x in range((y // step) % 2 * step, big.width, step * 2):
            d.rectangle([x, y, x + step - 1, y + step - 1], fill=(48, 51, 56, 255))
    checker.alpha_composite(big)
    return checker, scale


def fit(image, box):
    scale = min(box[0] / image.width, box[1] / image.height, 1.0)
    return image.resize((round(image.width * scale), round(image.height * scale)),
                        Image.Resampling.LANCZOS)


def panel(canvas, xy, size, title, subtitle, image):
    d = ImageDraw.Draw(canvas)
    x, y = xy
    d.rounded_rectangle([x, y, x + size[0], y + size[1]], radius=18, fill=PANEL)
    d.text((x + 28, y + 22), title, fill=TEXT, font=font(BOLD, 30))
    d.text((x + 28, y + 62), subtitle, fill=SECONDARY, font=font(REGULAR, 20))
    area = (size[0] - 56, size[1] - 130)
    ix = x + 28 + (area[0] - image.width) // 2
    iy = y + 105 + (area[1] - image.height) // 2
    canvas.paste(image.convert("RGB"), (ix, iy))


def promo(name, sprite_path, pattern, caption, detail=None):
    sprite = Image.open(sprite_path).convert("RGBA")
    grid = crop_to_beads(load_sprite(sprite_path)) if sprite_path.suffix else None  # as the app lays it out
    W, H = 1920, 1080
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    icon = Image.open(ROOT / "perler_app" / "assets" / "Sprite_to_Perler_pegboard_icon.png").convert("RGBA")
    canvas.paste(icon.resize((72, 72), Image.Resampling.LANCZOS), (60, 40), icon.resize((72, 72), Image.Resampling.LANCZOS))
    d.text((150, 44), "Sprite to Perler", fill=TEXT, font=font(BOLD, 44))
    d.text((152, 98), caption, fill=SECONDARY, font=font(REGULAR, 24))
    box = (800, 760)
    before, scale = enlarge(sprite, (box[0] - 56, box[1] - 130))
    panel(canvas, (60, 170), box, "Before", f"Original sprite · {sprite.width} × {sprite.height} pixels "
          f"(shown {scale}× larger)", before)
    after = fit(pattern, (box[0] - 56, box[1] - 130))
    layout = auto_layout(grid)
    panel(canvas, (1060, 170), box, "After",
          f"Bead pattern · {grid.total:,} beads · {layout.boards_x} × {layout.boards_y} pegboards", after)
    # Arrow between the panels.
    d.polygon([(905, 520), (1015, 550), (905, 580)], fill=ACCENT)
    d.rectangle([870, 538, 910, 562], fill=ACCENT)
    if detail is not None:  # a 1:1 crop proving the ring detail
        crop = pattern.crop(detail).resize(((detail[2] - detail[0]) * 2, (detail[3] - detail[1]) * 2),
                                           Image.Resampling.NEAREST)
        d.rounded_rectangle([1060 + 800 - crop.width - 40, 170 + 760 - crop.height - 40,
                             1060 + 800 - 20, 170 + 760 - 20], radius=12, fill=(15, 17, 19))
        canvas.paste(crop.convert("RGB"), (1060 + 800 - crop.width - 30, 170 + 760 - crop.height - 30))
        d.text((1060 + 800 - crop.width - 30, 170 + 760 - crop.height - 66), "Detail (2× zoom)",
               fill=SECONDARY, font=font(REGULAR, 18))
    d.text((60, 960), "One sprite pixel = one bead · original colors kept · dark #2B2B2B pattern "
           "background · white lines mark each 29 × 29 pegboard", fill=SECONDARY, font=font(REGULAR, 22))
    PROMO.mkdir(parents=True, exist_ok=True)
    canvas.save(PROMO / f"{name}.png", optimize=True)
    print(f"promo/{name}.png")


def main():
    # Sample exports written by the real app during capture_screens.ps1.
    if SAMPLE.exists():
        shutil.rmtree(SAMPLE)
    SAMPLE.mkdir(parents=True)
    shutil.copy(EXPORTS / "pip_mushroom_bead_pattern.png", SAMPLE)
    shutil.copytree(EXPORTS / "pip_mushroom_bead_charts", SAMPLE / "pip_mushroom_bead_charts")
    print("sample-output:", sorted(p.name for p in SAMPLE.rglob("*") if p.is_file()))
    charts = SAMPLE / "pip_mushroom_bead_charts"
    shutil.copy(charts / "pip_mushroom_board_R1C1.png", IMAGES / "chart-board-R1C1.png")
    shutil.copy(charts / "pip_mushroom_board_layout.png", IMAGES / "chart-board-layout.png")

    pip_pattern = Image.open(SAMPLE / "pip_mushroom_bead_pattern.png").convert("RGB")
    grid = crop_to_beads(load_sprite(EXAMPLES / "pip_mushroom.png"))
    assert np.array_equal(np.asarray(pip_pattern), np.asarray(render(grid, auto_layout(grid)))), \
        "exported PNG differs from the engine render"
    promo("before-after-pip-mushroom", EXAMPLES / "pip_mushroom.png", pip_pattern,
          "Turn pixel-art sprites into ready-to-build Perler bead patterns")
    glob = crop_to_beads(load_sprite(EXAMPLES / "glob_slime_solid_background.png"))
    promo("before-after-glob-slime", EXAMPLES / "glob_slime_solid_background.png",
          render(glob, auto_layout(glob)), "Solid backgrounds are removed automatically")
    dusk = crop_to_beads(prepare_sprite(Image.open(EXAMPLES / "dusk_valley_large.png"), background="keep"))
    dusk_pattern = render(dusk, auto_layout(dusk))
    promo_large(dusk, dusk_pattern)
    # The guide also shows a 1:1 detail of the bead rings.
    pip_pattern.crop((450, 420, 900, 700)).save(IMAGES / "bead-detail-actual-size.png")


def promo_large(grid, pattern):
    """Large example: whole pattern reduced to fit, labelled as reduced."""
    sprite = Image.open(EXAMPLES / "dusk_valley_large.png").convert("RGBA")
    W, H = 1920, 1080
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    icon = Image.open(ROOT / "perler_app" / "assets" / "Sprite_to_Perler_pegboard_icon.png").convert("RGBA")
    small = icon.resize((72, 72), Image.Resampling.LANCZOS)
    canvas.paste(small, (60, 40), small)
    d.text((150, 44), "Sprite to Perler", fill=TEXT, font=font(BOLD, 44))
    d.text((152, 98), "Large sprites, split across many pegboards", fill=SECONDARY, font=font(REGULAR, 24))
    layout = auto_layout(grid)
    before, scale = enlarge(sprite, (744, 630))
    panel(canvas, (60, 170), (800, 760), "Before",
          f"Original sprite · {sprite.width} × {sprite.height} pixels (shown {scale}× larger)", before)
    panel(canvas, (1060, 170), (800, 760), "After",
          f"{grid.total:,} beads · {layout.boards_x} × {layout.boards_y} pegboards (shown reduced)",
          fit(pattern, (744, 630)))
    d.polygon([(905, 520), (1015, 550), (905, 580)], fill=ACCENT)
    d.rectangle([870, 538, 910, 562], fill=ACCENT)
    d.text((60, 960), "Every pegboard can be exported as its own numbered chart", fill=SECONDARY,
           font=font(REGULAR, 22))
    canvas.save(PROMO / "before-after-dusk-valley-large.png", optimize=True)
    print("promo/before-after-dusk-valley-large.png")


if __name__ == "__main__":
    main()
