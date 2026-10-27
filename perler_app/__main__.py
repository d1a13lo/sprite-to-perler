import ctypes
import sys
import traceback
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from perler_engine import AssetError
from perler_engine.render import ring_tile

from .theme import apply_theme
from .window import MainWindow


def show_unexpected_error(exc_type, exc, tb):
    """A windowed program has no console, so unexpected errors are shown, never lost."""
    details = "".join(traceback.format_exception(exc_type, exc, tb, limit=4))
    QMessageBox.critical(None, "Sprite-to-Bead Pattern — unexpected error",
                         "Something went wrong. Your files were not changed.\n\n" + details)


ICON_PATH = Path(__file__).resolve().parent / "assets" / "Sprite_to_Perler_pegboard_icon.ico"
APP_ID = "SpriteToPerler.App"


def set_app_icon(app):
    """Window, title bar, taskbar and Alt+Tab icon. Cosmetic: a missing icon is ignored."""
    if sys.platform == "win32":
        try:  # own taskbar identity, so a launch through pythonw.exe still shows our icon
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
        except (AttributeError, OSError):
            pass
    if ICON_PATH.is_file():
        app.setWindowIcon(QIcon(str(ICON_PATH)))


def main():
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app)  # interface only; the rendered pattern is never styled
    set_app_icon(app)
    sys.excepthook = show_unexpected_error
    try:
        ring_tile()  # the Photoshop-derived bead-ring asset must be present and unchanged
    except AssetError as exc:
        QMessageBox.critical(None, "Sprite-to-Bead Pattern cannot start",
                             f"{exc}\n\nThe program folder is incomplete or damaged. Copy the whole "
                             "'Sprite-to-Bead Pattern' folder again and keep all of its files together.")
        return 1
    window = MainWindow()
    window.show()
    if len(sys.argv) > 1:
        window.open_file(sys.argv[1])
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
