"""Application icon (cosmetic): approved files kept exactly, applied at startup."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import hashlib

from PIL import Image
from PySide6.QtWidgets import QApplication

import perler_app.__main__ as entry

APPROVED_ICO_SHA256 = "128ed4108df2c05bd5124400045364e6aa302c709befdcb9aa010872e14927cb"
APPROVED_PNG_SHA256 = "bf18c71374914fad51a900ccfdfb6265fcb7915e235dc475381d94b5351fa64d"


def test_approved_icon_files_are_unchanged():
    assets = entry.ICON_PATH.parent
    assert hashlib.sha256(entry.ICON_PATH.read_bytes()).hexdigest() == APPROVED_ICO_SHA256
    png = assets / "Sprite_to_Perler_pegboard_icon.png"
    assert hashlib.sha256(png.read_bytes()).hexdigest() == APPROVED_PNG_SHA256
    sizes = sorted(Image.open(entry.ICON_PATH).info["sizes"])
    assert sizes == [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]


def test_window_icon_is_set():
    app = QApplication.instance() or QApplication([])
    previous = app.windowIcon()
    try:
        entry.set_app_icon(app)
        icon = app.windowIcon()
        assert not icon.isNull()
        assert {s.width() for s in icon.availableSizes()} >= {16, 32, 48, 256}
    finally:
        app.setWindowIcon(previous)
