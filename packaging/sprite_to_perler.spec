# PyInstaller build for the portable Windows program.
#   .venv\Scripts\pyinstaller.exe --noconfirm --distpath dist --workpath build packaging\sprite_to_perler.spec
# Output: dist\Sprite to Perler\Sprite to Perler.exe (keep the whole folder together).
from pathlib import Path

ROOT = Path(SPECPATH).parent
ICON = ROOT / "perler_app" / "assets" / "Sprite_to_Perler_pegboard_icon.ico"  # approved app icon

# Not used by the app; leaving them out keeps the folder smaller.
EXCLUDES = ["tkinter", "unittest", "pytest", "_pytest", "pydoc", "PySide6.QtNetwork",
            "PySide6.QtQml", "PySide6.QtQuick", "PySide6.QtOpenGL", "PySide6.QtSql",
            "PySide6.QtTest", "PySide6.QtDBus", "PySide6.QtXml", "PySide6.QtSvg"]

a = Analysis(
    [str(ROOT / "packaging" / "sprite_to_perler.py")],
    pathex=[str(ROOT)],
    # The bead-ring tile and Perler palette, at the same place the code looks for them.
    # The window icon (ICO) at the same place the code looks for it.
    datas=[(str(ROOT / "perler_engine" / "assets"), "perler_engine/assets"),
           (str(ICON), "perler_app/assets")],
    excludes=EXCLUDES,
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="Sprite to Perler",
          console=False,  # a normal windowed program, no command prompt
          icon=str(ICON),  # shown by File Explorer, shortcuts and the taskbar
          upx=False)
coll = COLLECT(exe, a.binaries, a.datas, name="Sprite to Perler", upx=False)
