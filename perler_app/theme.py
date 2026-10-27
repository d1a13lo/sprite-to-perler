"""Dark interface theme (cosmetic only).

Styles the application's widgets. It never touches the rendered pattern: the
template keeps its own #2B2B2B background, rings, guides and original colours,
and exported files are unaffected.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette

WINDOW = "#17191C"      # main window background
PANEL = "#24272B"       # panels and sections
BUTTON = "#393E45"      # normal buttons
PRIMARY = "#506A86"     # primary action buttons
TEXT = "#F0F2F5"        # main text
SECONDARY = "#AAB1BB"   # secondary text
# Derived shades for states and borders.
BORDER = "#33373D"
BUTTON_HOVER = "#454B53"
BUTTON_PRESSED = "#2F3338"
PRIMARY_HOVER = "#5E7B9B"
PRIMARY_PRESSED = "#445A72"
DISABLED_BG = "#2A2D31"
DISABLED_TEXT = "#6E7682"
FOCUS = "#8DB3DC"
WORKSPACE = "#0F1113"   # area around the pattern (the pattern canvas itself stays #2B2B2B)
WARNING = "#E8B04B"
ERROR = "#FF7B7B"
OK = "#7FD18B"
# Widgets opt in by objectName: "primaryButton" (Upload, Generate PNG, Export), "infoBox",
# "adjustPanel", "dropZone", "busyPage", "secondary" (hints and footnotes).

STYLESHEET = f"""
QWidget {{ background-color: {WINDOW}; color: {TEXT}; }}
QLabel, QRadioButton {{ background-color: transparent; }}
QToolTip {{ background-color: {PANEL}; color: {TEXT}; border: 1px solid {BORDER};
            padding: 4px 6px; }}

QFrame#infoBox, QFrame#adjustPanel {{ background-color: {PANEL}; border: 1px solid {BORDER};
            border-radius: 8px; }}
QFrame#infoBox QLabel, QFrame#adjustPanel QLabel, QFrame#adjustPanel QRadioButton {{
            background-color: transparent; }}
QLabel#secondary {{ color: {SECONDARY}; background: transparent; }}
QLabel#dropZone {{ border: 2px dashed #4A5058; border-radius: 12px; color: {SECONDARY};
            background-color: #1C1F23; font-size: 20px; }}
QLabel#busyPage {{ color: {SECONDARY}; font-size: 18px; }}

QPushButton {{ background-color: {BUTTON}; color: {TEXT}; border: 1px solid #454B53;
            border-radius: 8px; padding: 6px 12px; }}
QPushButton:hover {{ background-color: {BUTTON_HOVER}; }}
QPushButton:pressed {{ background-color: {BUTTON_PRESSED}; }}
QPushButton:focus {{ border: 2px solid {FOCUS}; }}
QPushButton:disabled {{ background-color: {DISABLED_BG}; color: {DISABLED_TEXT};
            border: 1px dashed #3E434A; }}
QPushButton#primaryButton {{ background-color: {PRIMARY}; border: 1px solid #5E7B9B;
            font-weight: 600; }}
QPushButton#primaryButton:hover {{ background-color: {PRIMARY_HOVER}; }}
QPushButton#primaryButton:pressed {{ background-color: {PRIMARY_PRESSED}; }}
QPushButton#primaryButton:focus {{ border: 2px solid {FOCUS}; }}
QPushButton#primaryButton:disabled {{ background-color: {DISABLED_BG}; color: {DISABLED_TEXT};
            border: 1px dashed #3E434A; font-weight: normal; }}

QRadioButton {{ spacing: 8px; padding: 2px 0; }}
QRadioButton::indicator {{ width: 12px; height: 12px; border-radius: 8px;
            border: 2px solid #7A828D; background-color: #1E2125; }}
QRadioButton::indicator:hover {{ border: 2px solid {SECONDARY}; }}
QRadioButton::indicator:checked {{ border: 2px solid {FOCUS};
            background-color: qradialgradient(cx:0.5, cy:0.5, radius:0.5, fx:0.5, fy:0.5,
            stop:0 {FOCUS}, stop:0.5 {FOCUS}, stop:0.56 #1E2125, stop:1 #1E2125); }}
QRadioButton::indicator:disabled {{ border: 2px solid #4A5058; }}
QRadioButton:focus {{ color: #FFFFFF; text-decoration: underline; }}
QRadioButton:disabled {{ color: {DISABLED_TEXT}; }}

QTabWidget::pane {{ background-color: {PANEL}; border: 1px solid {BORDER}; border-radius: 8px;
            top: -1px; }}
QTabWidget > QWidget > QWidget, QTabWidget QStackedWidget > QWidget {{ background-color: {PANEL}; }}
QTabBar::tab {{ background-color: #1E2125; color: {SECONDARY}; border: 1px solid {BORDER};
            border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px;
            padding: 6px 14px; margin-right: 2px; }}
QTabBar::tab:selected {{ background-color: {PANEL}; color: {TEXT}; border-top: 2px solid {PRIMARY}; }}
QTabBar::tab:hover:!selected {{ color: {TEXT}; background-color: #2A2E33; }}
QTabBar::tab:focus {{ color: #FFFFFF; }}

QTableWidget {{ background-color: #1E2125; alternate-background-color: #22252A; color: {TEXT};
            gridline-color: {BORDER}; border: 1px solid {BORDER}; border-radius: 6px;
            selection-background-color: {PRIMARY}; selection-color: {TEXT}; }}
QTableWidget:focus {{ border: 1px solid {FOCUS}; }}
QHeaderView {{ background-color: transparent; }}
QHeaderView::section {{ background-color: #2B2F34; color: {SECONDARY}; border: none;
            border-right: 1px solid {BORDER}; border-bottom: 1px solid {BORDER}; padding: 4px 6px; }}
QTableCornerButton::section {{ background-color: #2B2F34; border: none; }}

QScrollArea, QScrollArea > QWidget > QWidget {{ background-color: {WINDOW}; border: none; }}
QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle {{ background-color: #4A5058; border-radius: 4px; min-height: 24px; min-width: 24px; }}
QScrollBar::handle:hover {{ background-color: #5C636D; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QSplitter::handle {{ background-color: {WINDOW}; }}
QSplitter::handle:hover {{ background-color: {BORDER}; }}
QGraphicsView {{ border: 1px solid {BORDER}; border-radius: 6px; }}

QMessageBox {{ background-color: {PANEL}; }}
QMessageBox QLabel {{ background-color: transparent; color: {TEXT}; }}
"""


def apply_theme(app):
    """Dark palette + stylesheet for the whole application (widgets only)."""
    try:  # Windows 11: dark title bars and native dark hints (Qt 6.8+)
        app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    except AttributeError:
        pass
    app.setStyle("Fusion")  # draws consistently with a custom palette on every Windows version
    palette = QPalette()
    for role, color in [
        (QPalette.ColorRole.Window, WINDOW), (QPalette.ColorRole.WindowText, TEXT),
        (QPalette.ColorRole.Base, "#1E2125"), (QPalette.ColorRole.AlternateBase, "#22252A"),
        (QPalette.ColorRole.Text, TEXT), (QPalette.ColorRole.Button, BUTTON),
        (QPalette.ColorRole.ButtonText, TEXT), (QPalette.ColorRole.Highlight, PRIMARY),
        (QPalette.ColorRole.HighlightedText, TEXT), (QPalette.ColorRole.ToolTipBase, PANEL),
        (QPalette.ColorRole.ToolTipText, TEXT), (QPalette.ColorRole.PlaceholderText, SECONDARY),
        (QPalette.ColorRole.Link, FOCUS), (QPalette.ColorRole.Mid, BORDER),
    ]:
        palette.setColor(role, QColor(color))
    for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                 QPalette.ColorRole.ButtonText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor(DISABLED_TEXT))
    app.setPalette(palette)
    app.setStyleSheet(STYLESHEET)
