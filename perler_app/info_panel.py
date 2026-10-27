"""Bead and Perler supply information shown under the preview.

Purely informational: it displays counts from the bead grid and the supply
report, and never changes the artwork, preview or exported pattern.
"""
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QHBoxLayout, QHeaderView, QLabel,
                               QSizePolicy, QTableWidget, QTableWidgetItem, QTabWidget,
                               QVBoxLayout, QWidget)

from perler_engine.charts import board_info_problem, color_numbers
from perler_engine.palette import match_quality

QUALITY_TEXT = {"close": "Close", "approximate": "Approx.", "weak": "Weak ⚠", "unmatched": "—"}
MAX_COLOR_ROWS = 300  # pixel art rarely has more; the CSV export always lists every colour
MAX_BOARD_ROWS = 400  # e.g. 20 x 20 boards; the board CSV always lists every board


def swatch(rgb):
    pixmap = QPixmap(14, 14)
    pixmap.fill(QColor(*rgb))
    return QIcon(pixmap)


def hex_of(rgb):
    return "#%02X%02X%02X" % rgb


def make_table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
    table.verticalHeader().setVisible(False)
    table.verticalHeader().setDefaultSectionSize(22)
    table.setWordWrap(False)
    table.setTextElideMode(Qt.TextElideMode.ElideRight)  # full text in each tooltip
    header = table.horizontalHeader()
    header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
    header.setStretchLastSection(True)
    return table


def fill(table, rows):
    """rows: list of cells; a cell is text or (text, tooltip, rgb-for-swatch)."""
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, cell in enumerate(row):
            text, tip, rgb = (cell, None, None) if isinstance(cell, str) else cell
            item = QTableWidgetItem(text)
            item.setToolTip(tip or text)
            if rgb is not None:
                item.setIcon(swatch(rgb))
            if text.replace(",", "").isdigit():
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(r, c, item)
    table.resizeColumnsToContents()


def titled(title_label, table):
    box = QVBoxLayout()
    box.setContentsMargins(0, 0, 0, 0)
    box.addWidget(title_label)
    box.addWidget(table, 1)
    return box


def title_label():
    label = QLabel("")
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    return label


class InfoPanel(QTabWidget):
    def __init__(self):
        super().__init__()
        self.colors_title = title_label()
        self.colors_table = make_table(["#", "Original color", "Beads", "Suggested Perler"])
        self.supply_title = title_label()
        self.supply_table = make_table(["Perler color", "Code", "Beads", "Match"])
        self.footnote = title_label()
        self.footnote.setObjectName("secondary")
        self.footnote.setText("Informational only — the pattern always keeps the original colors. "
                              "Perler colors are digital approximations; physical beads vary. "
                              "* photo-estimated color data · ⚠ weak match (ΔE over 10). "
                              "Hover over a row for details.")
        supplies = QWidget()
        outer = QVBoxLayout(supplies)
        outer.setContentsMargins(6, 6, 6, 6)
        row = QHBoxLayout()
        row.addLayout(titled(self.colors_title, self.colors_table), 4)
        row.addLayout(titled(self.supply_title, self.supply_table), 6)
        outer.addLayout(row, 1)
        outer.addWidget(self.footnote)
        self.addTab(supplies, "Colors && Perler Supplies")

        boards = QWidget()
        box = QVBoxLayout(boards)
        box.setContentsMargins(6, 6, 6, 6)
        self.boards_title = title_label()
        self.boards_table = make_table(["Board", "Position", "Beads", "Colors"])
        box.addLayout(titled(self.boards_title, self.boards_table), 1)
        self.addTab(boards, "Pegboards")
        self.clear()

    # --- states -------------------------------------------------------------------------

    def clear(self, message="No sprite loaded."):
        for table in (self.colors_table, self.supply_table, self.boards_table):
            table.setRowCount(0)
        self.colors_title.setText(f"<b>Original Sprite Colors</b> — {message}")
        self.supply_title.setText("<b>Suggested Perler Supplies</b>")
        self.boards_title.setText("<b>Pegboards</b>")

    def show_counts(self, grid, supply=None):
        """Original colour counts; suggestions are filled in once `supply` is ready."""
        numbers = color_numbers(grid)
        matches = {s.rgb: s for s in supply.sources} if supply else {}
        counts = grid.color_counts()
        rows = []
        for rgb, n in counts[:MAX_COLOR_ROWS]:
            m = matches.get(rgb)
            suggestion = ("…" if supply is None else
                          "Unmatched" if m.color is None else f"{m.color.name} ({m.color.code})")
            rows.append([str(numbers[rgb]), (hex_of(rgb), f"{hex_of(rgb)}  RGB {rgb}", rgb),
                         f"{n:,}", suggestion])
        if len(counts) > MAX_COLOR_ROWS:
            rest = counts[MAX_COLOR_ROWS:]
            note = "All colors are listed in the Original Colors CSV (Export Charts & CSV)."
            rows.append(["…", (f"{len(rest):,} more colors", note, None),
                         f"{sum(n for _, n in rest):,}", (note, note, None)])
        fill(self.colors_table, rows)
        colors = len(counts)
        self.colors_title.setText(f"<b>Original Sprite Colors</b> — {colors} "
                                  f"color{'s' if colors != 1 else ''} · {grid.total:,} beads")
        if supply is None:
            self.supply_table.setRowCount(0)
            self.supply_title.setText("<b>Suggested Perler Supplies</b> — calculating…")

    def show_supply(self, grid, supply):
        self.show_counts(grid, supply)
        rows = []
        for line in supply.supplies:
            originals = ", ".join(hex_of(rgb) for rgb in line.sources)
            if line.color is None:
                tip = (f"No Perler color could be suggested for {originals}. "
                       f"{supply.error or ''}").strip()
                rows.append([("Unmatched", tip, None), "—", f"{line.beads:,}", ("—", tip, None)])
                continue
            c = line.color
            quality = match_quality(line.max_delta_e)
            name = c.name + (" *" if c.photo_estimate else "")
            notes = [s.note for s in supply.sources if s.color == c and s.note]
            tip = "\n".join(filter(None, [
                f"{c.name} ({c.code}), digital color {c.hex}",
                f"Original colors: {originals}",
                f"Largest difference: ΔE {line.max_delta_e:.1f} ({quality} match)",
                f"Color data: {c.source} — {c.confidence}",
                c.notes, *notes]))
            rows.append([(name, tip, c.rgb), (c.code, tip, None), f"{line.beads:,}",
                         (f"{QUALITY_TEXT[quality]} (ΔE {line.max_delta_e:.1f})", tip, None)])
        fill(self.supply_table, rows)
        matched = sum(1 for l in supply.supplies if l.color is not None)
        unmatched = supply.unmatched_beads
        extra = f" · ⚠ {unmatched:,} beads unmatched" if unmatched else ""
        self.supply_title.setText(f"<b>Suggested Perler Supplies</b> — {matched} "
                                  f"color{'s' if matched != 1 else ''} · "
                                  f"{supply.total:,} beads{extra}")

    def show_boards(self, pattern):
        layout, alignment = pattern.layout, pattern.alignment
        problem = board_info_problem(alignment)
        if problem:
            self.boards_table.setRowCount(0)
            self.boards_title.setText(f"<b>Pegboards</b> — ⚠ board counts unavailable. {problem}")
            return
        counts = alignment.board_counts
        rows = []
        for r in range(1, layout.boards_y + 1):
            for c in range(1, layout.boards_x + 1):
                if len(rows) == MAX_BOARD_ROWS:
                    break
                board = counts.get((r, c), {})
                rows.append([f"R{r}C{c}", f"Row {r}, column {c}", f"{sum(board.values()):,}",
                             str(len(board))])
        if layout.total_boards > MAX_BOARD_ROWS:
            listed = {f"R{r}C{c}" for r in range(1, layout.boards_y + 1)
                      for c in range(1, layout.boards_x + 1)}
            shown = {row[0] for row in rows}
            rest = sum(sum(v.values()) for (r, c), v in counts.items() if f"R{r}C{c}" not in shown)
            note = "Every board is listed in the board counts CSV (Export Charts & CSV)."
            rows.append([("…", note, None), (f"{len(listed - shown):,} more boards", note, None),
                         f"{rest:,}", (note, note, None)])
        fill(self.boards_table, rows)
        occupied = sum(1 for b in counts.values() if b)
        self.boards_title.setText(
            f"<b>Pegboards</b> — {layout.boards_x} × {layout.boards_y} = {layout.total_boards} "
            f"boards, {occupied} occupied · {pattern.grid.total:,} beads · "
            "R1C1 = top-left board, as in the preview")
