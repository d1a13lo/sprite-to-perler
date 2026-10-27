"""Add numbered callouts to the raw screenshots and write the guide's images.

Callouts are placed from the control rectangles recorded by capture_screens.ps1
(UI Automation), so each number points at the real control. Only copies are
annotated; the raw captures are not changed.
    python docs/tools/annotate.py
"""
import json
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "build" / "docs_raw"
OUT = ROOT / "docs" / "images"
ACCENT = (255, 159, 28)
INK = (23, 25, 28)
FONT = ImageFont.truetype("C:/Windows/Fonts/segoeuib.ttf", 22)

# Window-relative regions that are not single named controls (from the capture metadata).
PREVIEW = [20, 48, 1177, 695]
ZOOM_BAR = [20, 751, 345, 37]
SIDE = [1205, 48, 375, 1032]
INFO_BOX = [1216, 182, 352, 182]
# Side panel below the information box: notes (e.g. "Empty outer margins ignored") and Adjust Layers.
SIDE_CROP = [1150, 370, 1590, 900]


def rect_of(controls, ref):
    if isinstance(ref, list):
        return ref
    kind, name = ref
    for c in controls:
        if c["type"] == kind and c["name"] == name:
            return [c["x"], c["y"], c["w"], c["h"]]
    for c in controls:
        if c["type"] == kind and c["name"].startswith(name):
            return [c["x"], c["y"], c["w"], c["h"]]
    raise KeyError(ref)


def badge(d, n, cx, cy):
    r = 17
    d.ellipse([cx - r - 2, cy - r - 2, cx + r + 2, cy + r + 2], fill=INK)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=ACCENT)
    d.text((cx, cy + 1), str(n), fill=INK, font=FONT, anchor="mm")


def annotate(src, out, marks=(), crop=None):
    img = Image.open(RAW / f"{src}.png").convert("RGB")
    controls = json.loads((RAW / f"{src}.json").read_text(encoding="utf-8-sig")) \
        if (RAW / f"{src}.json").exists() else []
    if isinstance(controls, dict):
        controls = [controls]
    d = ImageDraw.Draw(img)
    for n, ref, side in marks:
        x, y, w, h = rect_of(controls, ref)
        pad = 4
        d.rounded_rectangle([x - pad, y - pad, x + w + pad, y + h + pad], radius=10,
                            outline=INK, width=6)
        d.rounded_rectangle([x - pad, y - pad, x + w + pad, y + h + pad], radius=10,
                            outline=ACCENT, width=3)
        cx, cy = {"left": (x - pad - 22, y + h / 2), "right": (x + w + pad + 22, y + h / 2),
                  "top": (x + 26, y - pad - 20), "bottom": (x + 26, y + h + pad + 20),
                  "inside": (x + 30, y + 30), "topright": (x + w - 26, y - pad - 20),
                  "insideright": (x + w - 30, y + h * 0.72)}[side]
        badge(d, n, cx, cy)
    if crop:
        img = img.crop(crop)
    OUT.mkdir(parents=True, exist_ok=True)
    img.save(OUT / f"{out}.png", optimize=True)
    print(f"{out}.png {img.size}")


SPEC = [
    ("01_empty", "main-window-empty", [(1, PREVIEW, "inside"), (2, ("Button", "Upload Image"), "left"),
                                       (3, INFO_BOX, "left"), (4, ("Button", "Generate PNG"), "left")]),
    ("02_loaded", "main-window-loaded", [(1, PREVIEW, "inside"), (2, ZOOM_BAR, "right"),
                                         (3, INFO_BOX, "left"), (4, ("Button", "Adjust Layers"), "left"),
                                         (5, ("Tab", "Colors & Perler Supplies"), "right"),
                                         (6, ("Button", "Generate PNG"), "left"),
                                         (7, ("Button", "Export Charts & CSV"), "left")]),
    ("03_zoom_100", "zoom-100-percent", [(1, ("Button", "−"), "top"), (2, ("Button", "+"), "top"),
                                         (3, ("Button", "Fit"), "top"), (4, ("Button", "100%"), "top")],
     [0, 0, 1205, 800]),
    ("02_loaded", "pattern-information", [], [1205, 100, 1580, 422]),  # box and the notes below it
    ("02_loaded", "colors-and-supplies", [(1, ("Table", ""), "topright"), (2, [497, 866, 691, 158], "topright"),
                                          (3, ("Header", "Match"), "insideright"),
                                          (4, ("Text", "Informational only"), "insideright")],
     [0, 780, 1205, 1090]),
    ("06_pegboards", "pegboards-tab", [(1, ("TabItem", "Pegboards"), "top")], [0, 780, 1205, 1090]),
    ("07_adjust_open", "adjust-layers-panel", [(1, ("RadioButton", "Sprite Artwork"), "left"),
                                               (2, ("Button", "←"), "left"),
                                               (3, ("Text", "Sprite Artwork: H"), "left"),
                                               (4, ("Button", "Reset Selected Layer"), "left"),
                                               (5, ("Button", "Done"), "left")],
     SIDE_CROP),
    ("08_sprite_moved", "sprite-moved", [], [0, 0, 1590, 870]),
    ("09_rings_moved", "rings-moved", [], [0, 0, 1590, 870]),
    ("10_lines_off_grid", "lines-off-grid", [], None),
    ("11_sprite_edge", "sprite-edge-limit", [], SIDE_CROP),
    ("12_reset_all", "reset-all", [(1, ("Button", "Reset All Layers"), "left")], SIDE_CROP),
    ("13_png_saved", "png-saved", [(1, ("Button", "Generate PNG"), "left")], [1150, 880, 1590, 1090]),
    ("14_charts_saved", "charts-saved", [(1, ("Button", "Export Charts & CSV"), "left")],
     [1150, 880, 1590, 1090]),
    ("15_animated_gif", "animated-gif-notice", [], [1150, 100, 1590, 480]),
    ("16_solid_background", "solid-background-removed", [], None),
    ("17_background_question", "background-question", []),
    ("18_background_outside", "background-outside-result", [], None),
    ("19_error", "error-not-an-image", []),
    ("20_keep_every_pixel", "background-keep-every-pixel", []),
    ("21_large_loaded", "large-pattern-overview", [], None),
    ("22_large_detail", "large-pattern-detail", [], [0, 0, 1590, 800]),
]


def main():
    for entry in SPEC:
        src, out, marks = entry[:3]
        crop = entry[3] if len(entry) > 3 else None
        annotate(src, out, marks, crop)


if __name__ == "__main__":
    main()
