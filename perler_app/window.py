"""Main window: upload/drop a sprite, see the finished pattern, zoom, save PNG."""
import math
import traceback
from pathlib import Path

from PySide6.QtCore import QEvent, QObject, QRunnable, QSize, Qt, QThreadPool, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPixmap
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QFormLayout, QFrame,
                               QGraphicsPixmapItem, QGraphicsScene, QGraphicsView,
                               QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton,
                               QRadioButton, QScrollArea, QSizePolicy, QSplitter,
                               QStackedWidget, QVBoxLayout, QWidget)

from perler_engine import PITCH, BackgroundDecisionNeeded, EngineError
from perler_engine.alignment import (clamp_guide_offset, clamp_sprite_offset,
                                     normalize_ring_offset)
from perler_engine.palette import supply_report_for
from perler_engine.render import render_region

from . import theme
from .info_panel import InfoPanel
from .pattern import (export_charts, export_png, load_pattern, png_too_large_message,
                      with_layout)

ZOOM_STEP = 1.25
ZOOM_MIN, ZOOM_MAX = 0.05, 8.0


def to_qimage(image):
    """Exact RGB copy of a PIL image as a QImage."""
    data = image.tobytes()
    return QImage(data, image.width, image.height, image.width * 3,
                  QImage.Format.Format_RGB888).copy()


class ElidedLabel(QLabel):
    """One-line label for file names and paths, which have no spaces to wrap at.

    Long text is shortened in the middle with "…" to fit the panel; the full
    text is always available as a tooltip and never widens the panel.
    """

    def __init__(self, text=""):
        super().__init__()
        self.full_text = ""
        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text):
        self.full_text = text
        self.setToolTip(text)
        self._elide()

    def text_shown(self):
        return super().text()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def _elide(self):
        width = max(self.width(), 1)
        super().setText(self.fontMetrics().elidedText(self.full_text,
                                                       Qt.TextElideMode.ElideMiddle, width))

    def minimumSizeHint(self):
        return QSize(0, super().minimumSizeHint().height())


def wrapping_label(text=""):
    """Multi-line label that wraps to the panel width and never widens it."""
    label = QLabel(text)
    label.setWordWrap(True)
    label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
    return label


class SidePanelScroll(QScrollArea):
    """Vertical-only scroll area: the content is always exactly as wide as the
    visible area, so nothing can be pushed sideways out of view."""

    def viewportEvent(self, event):
        # The viewport also narrows when the vertical scroll bar appears.
        if event.type() == QEvent.Type.Resize and self.widget():
            self.widget().setFixedWidth(self.viewport().width())
        return super().viewportEvent(event)


class PreviewView(QGraphicsView):
    """Zoomable view of the finished pattern. Zoom only changes the display.

    Normally a left-drag pans. In adjust mode a left-drag moves the selected
    layer instead (reported in output pixels, so zoom never changes the
    result) and the middle button pans.
    """

    zoom_changed = Signal(float)
    view_changed = Signal()  # zoom or scroll position changed
    layer_drag_started = Signal()
    layer_dragged = Signal(float, float)  # total output-pixel movement since the press

    def __init__(self):
        super().__init__()
        self.setScene(QGraphicsScene(self))
        self.item = QGraphicsPixmapItem()
        self.scene().addItem(self.item)
        # Large patterns: full-detail render of the visible area, drawn over the
        # reduced overview. Scene coordinates are always full-detail output pixels.
        self.detail = QGraphicsPixmapItem()
        self.detail.setZValue(1)
        self.scene().addItem(self.detail)
        self.horizontalScrollBar().valueChanged.connect(self.view_changed)
        self.verticalScrollBar().valueChanged.connect(self.view_changed)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setBackgroundBrush(QColor(theme.WORKSPACE))  # around the pattern only
        self.setAcceptDrops(False)  # drops are handled by the main window
        self.viewport().setAcceptDrops(False)
        self.fit_mode = True
        self.zoom = 1.0
        self.adjusting = False
        self._drag_start = None
        self._pan_start = None

    def set_image(self, qimage, refit=True, scale=1, canvas=None):
        """Show a preview; `scale` > 1 means it is the template reduced by that factor."""
        self.clear_detail()
        self.item.setPixmap(QPixmap.fromImage(qimage))
        self.item.setScale(scale)
        width, height = canvas or (qimage.width(), qimage.height())
        self.scene().setSceneRect(0, 0, width, height)
        if refit:
            self.fit()
        else:
            self._update_zoom(self.zoom)

    def set_detail(self, qimage, x, y):
        self.detail.setPixmap(QPixmap.fromImage(qimage))
        self.detail.setPos(x, y)

    def clear_detail(self):
        self.detail.setPixmap(QPixmap())

    def has_detail(self):
        return not self.detail.pixmap().isNull()

    def visible_scene_rect(self):
        return self.mapToScene(self.viewport().rect()).boundingRect()

    def set_adjust_mode(self, adjusting):
        self.adjusting = adjusting
        self._drag_start = self._pan_start = None
        self.setDragMode(QGraphicsView.DragMode.NoDrag if adjusting
                         else QGraphicsView.DragMode.ScrollHandDrag)
        if adjusting:
            self.viewport().setCursor(Qt.CursorShape.SizeAllCursor)
        else:
            self.viewport().unsetCursor()

    def mousePressEvent(self, event):
        if self.adjusting and not self.item.pixmap().isNull():
            if event.button() == Qt.MouseButton.LeftButton:
                self._drag_start = self.mapToScene(event.position().toPoint())
                self.layer_drag_started.emit()
                return
            if event.button() == Qt.MouseButton.MiddleButton:
                self._pan_start = event.position()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._drag_start is not None:
            delta = self.mapToScene(event.position().toPoint()) - self._drag_start
            self.layer_dragged.emit(delta.x(), delta.y())
            return
        if self._pan_start is not None:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(self.horizontalScrollBar().value() - round(delta.x()))
            self.verticalScrollBar().setValue(self.verticalScrollBar().value() - round(delta.y()))
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._drag_start is not None or self._pan_start is not None:
            self._drag_start = self._pan_start = None
            return
        super().mouseReleaseEvent(event)

    def displayed_image(self):
        return self.item.pixmap().toImage()

    def fit(self):
        self.fit_mode = True
        if not self.item.pixmap().isNull():
            self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
            self._update_zoom(self.transform().m11())

    def set_zoom(self, zoom):
        self.fit_mode = False
        zoom = max(ZOOM_MIN, min(ZOOM_MAX, zoom))
        self.resetTransform()
        self.scale(zoom, zoom)
        self._update_zoom(zoom)

    def _update_zoom(self, zoom):
        self.zoom = zoom
        # Smooth scaling only when shrinking, so beads stay crisp when enlarged.
        shrinking = zoom * self.item.scale() < 1
        self.item.setTransformationMode(Qt.TransformationMode.SmoothTransformation if shrinking
                                        else Qt.TransformationMode.FastTransformation)
        self.detail.setTransformationMode(Qt.TransformationMode.SmoothTransformation if zoom < 1
                                          else Qt.TransformationMode.FastTransformation)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, shrinking or zoom < 1)
        self.zoom_changed.emit(zoom)
        self.view_changed.emit()

    def wheelEvent(self, event):
        if self.item.pixmap().isNull():
            return
        step = ZOOM_STEP if event.angleDelta().y() > 0 else 1 / ZOOM_STEP
        self.set_zoom(self.zoom * step)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.fit_mode:
            self.fit()


class ExportSignals(QObject):
    finished = Signal(object)
    failed = Signal(str)
    progress = Signal(float)  # 0..1, for long work on large patterns


class ExportTask(QRunnable):
    def __init__(self, pattern, destination):
        super().__init__()
        self.pattern, self.destination = pattern, destination
        self.signals = ExportSignals()

    def run(self):
        try:
            self.signals.finished.emit(export_png(self.pattern, self.destination,
                                                  self.signals.progress.emit))
        except Exception as exc:  # reported to the user, never silent
            self.signals.failed.emit(str(exc))


class RenderTask(QRunnable):
    """Render a layout's preview off the interface thread."""

    def __init__(self, pattern, layout, generation):
        super().__init__()
        self.pattern, self.layout, self.generation = pattern, layout, generation
        self.signals = ExportSignals()

    def run(self):
        try:
            pattern = with_layout(self.pattern, self.layout, self.signals.progress.emit)
            # Convert here too, so the interface thread only has to display it.
            self.signals.finished.emit((pattern, to_qimage(pattern.image)))
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class DetailTask(QRunnable):
    """Full-detail render of the visible area of a large pattern."""

    def __init__(self, grid, layout, box, generation):
        super().__init__()
        self.grid, self.layout, self.box, self.generation = grid, layout, box, generation
        self.signals = ExportSignals()

    def run(self):
        try:
            self.signals.finished.emit(to_qimage(render_region(self.grid, self.layout, self.box)))
        except Exception as exc:
            self.signals.failed.emit(str(exc))


DETAIL_MAX_PIXELS = 16_000_000  # largest visible area rendered at full detail at once


class SupplyTask(QRunnable):
    """Perler matching off the interface thread, so the preview is never delayed."""

    def __init__(self, grid, generation):
        super().__init__()
        self.grid, self.generation = grid, generation
        self.signals = ExportSignals()

    def run(self):
        try:
            self.signals.finished.emit(supply_report_for(self.grid))
        except Exception as exc:
            self.signals.failed.emit(str(exc))


class ChartExportTask(QRunnable):
    def __init__(self, pattern, supply, parent_folder):
        super().__init__()
        self.pattern, self.supply, self.parent_folder = pattern, supply, parent_folder
        self.signals = ExportSignals()

    def run(self):
        try:
            self.signals.finished.emit(export_charts(self.pattern, self.supply, self.parent_folder,
                                                     self.signals.progress.emit))
        except Exception as exc:
            self.signals.failed.emit(str(exc))


SPRITE, RINGS, GUIDES = "sprite", "rings", "guides"
LAYER_NAMES = {SPRITE: "Sprite Artwork", RINGS: "Bead Rings", GUIDES: "Pegboard Lines"}
LIMIT_NOTES = {
    SPRITE: "The sprite is at the edge of the boards. It cannot move further without "
            "losing beads.",
    GUIDES: "Pegboard lines can move at most one board (725 px) in each direction.",
}


def signed(value, unit):
    return f"{value:+d} {unit}" if value else f"0 {unit}"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Sprite-to-Bead Pattern")
        screen = QApplication.primaryScreen().availableGeometry()
        self.resize(min(1150, screen.width()), min(880, screen.height() - 40))
        self.setAcceptDrops(True)
        self.pattern = None
        self.target_layout = None  # newest requested layout; may still be rendering
        self.saving = False
        self.rendering = False
        self.active_layer = SPRITE
        self._generation = 0
        self._drag_base = (0, 0)
        self._tasks = set()
        self.render_pool = QThreadPool(self)
        self.render_pool.setMaxThreadCount(1)
        self.supply = None  # informational supply report for the current sprite
        self.info_pool = QThreadPool(self)
        self.info_pool.setMaxThreadCount(1)
        self.detail_pool = QThreadPool(self)
        self.detail_pool.setMaxThreadCount(1)
        self._detail_busy = self._detail_pending = False
        self.detail_timer = QTimer(self)
        self.detail_timer.setSingleShot(True)
        self.detail_timer.setInterval(150)  # wait until zooming/scrolling pauses
        self.detail_timer.timeout.connect(self._request_detail)

        # Preview area: a large drop zone until a pattern exists.
        self.drop_zone = QLabel("Drag and drop a sprite PNG or GIF here\n\nor use Upload Image")
        self.drop_zone.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_zone.setWordWrap(True)  # never forces a wide minimum window
        self.drop_zone.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.drop_zone.setObjectName("dropZone")
        self.view = PreviewView()
        self.busy_page = QLabel("")  # shown while a large pattern's first preview renders
        self.busy_page.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.busy_page.setWordWrap(True)
        self.busy_page.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        self.busy_page.setObjectName("busyPage")
        self.stack = QStackedWidget()
        self.stack.addWidget(self.drop_zone)
        self.stack.addWidget(self.view)
        self.stack.addWidget(self.busy_page)
        self.view.view_changed.connect(self._schedule_detail)

        self.zoom_out_btn = QPushButton("−")
        self.zoom_in_btn = QPushButton("+")
        self.fit_btn = QPushButton("Fit")
        self.actual_btn = QPushButton("100%")
        self.zoom_label = QLabel("")
        self.zoom_out_btn.clicked.connect(lambda: self.view.set_zoom(self.view.zoom / ZOOM_STEP))
        self.zoom_in_btn.clicked.connect(lambda: self.view.set_zoom(self.view.zoom * ZOOM_STEP))
        self.fit_btn.clicked.connect(self.view.fit)
        self.actual_btn.clicked.connect(lambda: self.view.set_zoom(1.0))
        self.view.zoom_changed.connect(lambda z: self.zoom_label.setText(f"{z * 100:.0f}%"))
        zoom_bar = QHBoxLayout()
        for w in (self.zoom_out_btn, self.zoom_in_btn, self.fit_btn, self.actual_btn):
            w.setFixedWidth(56)
            zoom_bar.addWidget(w)
        zoom_bar.addWidget(self.zoom_label)
        zoom_bar.addStretch()

        preview_box = QVBoxLayout()
        preview_box.setContentsMargins(0, 0, 0, 0)
        preview_box.addWidget(self.stack, 1)
        preview_box.addLayout(zoom_bar)
        preview_area = QWidget()
        preview_area.setLayout(preview_box)
        self.info_panel = InfoPanel()
        self.splitter = QSplitter(Qt.Orientation.Vertical)  # drag the divider to resize
        self.splitter.addWidget(preview_area)
        self.splitter.addWidget(self.info_panel)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 0)
        self.splitter.setSizes([10_000, 230])
        self.splitter.setCollapsible(0, False)
        left = QVBoxLayout()
        left.addWidget(self.splitter, 1)

        # Side panel.
        self.upload_btn = QPushButton("Upload Image")
        self.upload_btn.setObjectName("primaryButton")
        self.upload_btn.setMinimumHeight(40)
        self.upload_btn.clicked.connect(self.choose_file)
        self.file_label = ElidedLabel("No sprite loaded")

        self.info = {}
        form = QFormLayout()
        for key, label in [("size", "Sprite size"), ("beads", "Total beads"),
                           ("colors", "Original colors"), ("grid", "Board columns × rows"),
                           ("boards", "Total boards"), ("occupied", "Occupied boards")]:
            self.info[key] = QLabel("–")
            form.addRow(label + ":", self.info[key])
        info_box = QFrame()
        info_box.setObjectName("infoBox")
        info_box.setFrameShape(QFrame.Shape.StyledPanel)
        info_box.setLayout(form)

        self.notes_label = wrapping_label()
        self.notes_label.setStyleSheet(f"color: {theme.WARNING};")
        self.alignment_label = wrapping_label()

        self.adjust_btn = QPushButton("Adjust Layers")
        self.adjust_btn.setMinimumHeight(34)
        self.adjust_btn.clicked.connect(self.enter_adjust_mode)
        self.adjust_panel = self._build_adjust_panel()

        self.generate_btn = QPushButton("Generate PNG")
        self.generate_btn.setObjectName("primaryButton")
        self.generate_btn.setMinimumHeight(40)
        self.generate_btn.clicked.connect(self.choose_export_path)
        self.charts_btn = QPushButton("Export Charts && CSV")
        self.charts_btn.setObjectName("primaryButton")
        self.charts_btn.setMinimumHeight(34)
        self.charts_btn.clicked.connect(self.choose_charts_folder)
        self.status_label = wrapping_label()
        self.saved_path_label = ElidedLabel()  # full path in the tooltip

        side = QVBoxLayout()
        side.addWidget(self.upload_btn)
        side.addWidget(self.file_label)
        side.addSpacing(8)
        side.addWidget(QLabel("<b>Pattern information</b>"))
        side.addWidget(info_box)
        side.addWidget(self.notes_label)
        side.addWidget(self.alignment_label)
        side.addWidget(self.adjust_btn)
        side.addWidget(self.adjust_panel)
        side.addStretch()
        side.addWidget(self.generate_btn)
        side.addWidget(self.charts_btn)
        side.addWidget(self.status_label)
        side.addWidget(self.saved_path_label)
        side_widget = QWidget()
        side_widget.setLayout(side)
        side_scroll = SidePanelScroll()  # scrolls vertically when content is tall
        self.side_scroll = side_scroll
        side_scroll.setWidget(side_widget)
        side_scroll.setWidgetResizable(True)
        side_scroll.setFrameShape(QFrame.Shape.NoFrame)
        side_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        side_scroll.setFixedWidth(300)

        root = QHBoxLayout()
        root.addLayout(left, 1)
        root.addWidget(side_scroll)
        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)
        self.view.layer_drag_started.connect(self._layer_drag_started)
        self.view.layer_dragged.connect(self._layer_dragged)
        self._show_pattern(None)

    def _build_adjust_panel(self):
        panel = QFrame()
        panel.setObjectName("adjustPanel")
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        box = QVBoxLayout(panel)
        box.addWidget(QLabel("<b>Adjust layers</b>"))
        self.layer_buttons = {}
        group = QButtonGroup(panel)
        for layer in (SPRITE, RINGS, GUIDES):
            button = QRadioButton(LAYER_NAMES[layer])
            group.addButton(button)
            box.addWidget(button)
            self.layer_buttons[layer] = button
        self.layer_buttons[SPRITE].setChecked(True)
        for layer, button in self.layer_buttons.items():
            button.toggled.connect(lambda on, l=layer: on and self.select_layer(l))

        pad = QHBoxLayout()
        self.arrow_buttons = {}
        for text, step in [("←", (-1, 0)), ("↑", (0, -1)), ("↓", (0, 1)), ("→", (1, 0))]:
            button = QPushButton(text)
            button.setFixedSize(44, 30)
            button.setAutoRepeat(True)  # hold to keep moving
            button.clicked.connect(lambda _=False, s=step: self.nudge(*s))
            pad.addWidget(button)
            self.arrow_buttons[text] = button
        pad.addStretch()
        box.addLayout(pad)

        self.offset_label = wrapping_label()
        self.offset_label.setTextFormat(Qt.TextFormat.RichText)
        box.addWidget(self.offset_label)
        self.adjust_note = wrapping_label()
        self.adjust_note.setStyleSheet(f"color: {theme.WARNING};")
        box.addWidget(self.adjust_note)
        hint = wrapping_label("Drag the preview to move the layer. Middle-drag pans; wheel zooms.")
        hint.setObjectName("secondary")
        box.addWidget(hint)

        self.reset_layer_btn = QPushButton("Reset Selected Layer")
        self.reset_all_btn = QPushButton("Reset All Layers")
        self.done_btn = QPushButton("Done")
        self.reset_layer_btn.clicked.connect(self.reset_selected_layer)
        self.reset_all_btn.clicked.connect(self.reset_all_layers)
        self.done_btn.clicked.connect(self.leave_adjust_mode)
        resets = QHBoxLayout()
        resets.addWidget(self.reset_layer_btn)
        resets.addWidget(self.reset_all_btn)
        box.addLayout(resets)
        box.addWidget(self.done_btn)
        panel.hide()
        return panel

    # --- layer adjustment ---------------------------------------------------------

    def enter_adjust_mode(self):
        if self.pattern is None:
            return
        self.adjust_btn.hide()
        self.adjust_panel.show()
        self.view.set_adjust_mode(True)
        self._update_offset_label()

    def leave_adjust_mode(self):
        """Back to the normal preview; adjustments are kept."""
        self.adjust_panel.hide()
        self.adjust_btn.setVisible(True)
        self.view.set_adjust_mode(False)
        self.adjust_note.setText("")

    def select_layer(self, layer):
        self.active_layer = layer
        self.layer_buttons[layer].setChecked(True)  # no-op when chosen by the radio button
        self.adjust_note.setText("")
        self._update_offset_label()

    def layer_offset(self, layer, layout=None):
        """Offset of one layer relative to the automatic alignment.

        Sprite: whole beads. Bead rings and pegboard lines: output pixels.
        """
        layout = layout or self.target_layout
        if layer == SPRITE:
            auto = self.pattern.auto.sprite_offset
            return (layout.sprite_offset[0] - auto[0], layout.sprite_offset[1] - auto[1])
        return layout.ring_offset if layer == RINGS else layout.guide_offset

    def set_layer_offset(self, layer, offset):
        """Place one layer (other layers never move). Returns False if limited."""
        base = self.target_layout
        offset = (int(offset[0]), int(offset[1]))
        if layer == SPRITE:
            auto = self.pattern.auto.sprite_offset
            wanted = (auto[0] + offset[0], auto[1] + offset[1])
            placed = clamp_sprite_offset(self.pattern.grid, base, wanted)
            layout, limited = base.moved(sprite_offset=placed), placed != wanted
        elif layer == RINGS:
            layout, limited = base.moved(ring_offset=normalize_ring_offset(offset)), False
        else:
            placed = clamp_guide_offset(offset)
            layout, limited = base.moved(guide_offset=placed), placed != offset
        self.adjust_note.setText(LIMIT_NOTES[layer] if limited else "")
        if layout != base:
            self.request_layout(layout)
        return not limited

    def nudge(self, dx, dy):
        x, y = self.layer_offset(self.active_layer)
        return self.set_layer_offset(self.active_layer, (x + dx, y + dy))

    def _layer_drag_started(self):
        self._drag_base = self.layer_offset(self.active_layer)

    def _layer_dragged(self, dx, dy):
        if self.active_layer == SPRITE:  # snap to whole bead positions
            step = (round(dx / PITCH), round(dy / PITCH))
        else:
            step = (round(dx), round(dy))
        self.set_layer_offset(self.active_layer,
                              (self._drag_base[0] + step[0], self._drag_base[1] + step[1]))

    def reset_selected_layer(self):
        self.set_layer_offset(self.active_layer, (0, 0))

    def reset_all_layers(self):
        self.adjust_note.setText("")
        if self.target_layout != self.pattern.auto:
            self.request_layout(self.pattern.auto)

    def request_layout(self, layout):
        """Show a new layout. Rendering runs in the background and only the
        newest request is drawn, so rapid moves never queue up."""
        self.target_layout = layout
        self.view.clear_detail()  # the full-detail patch shows the old layout
        self._update_offset_label()
        self._update_generate()
        if not self.rendering:
            self._start_render()

    def _start_render(self):
        self.rendering = True
        task = RenderTask(self.pattern, self.target_layout, self._generation)
        self._tasks.add(task)
        task.signals.finished.connect(lambda result: self._render_done(task, *result))
        task.signals.failed.connect(lambda msg: self._render_failed(task, msg))
        task.signals.progress.connect(lambda f: self._render_progress(task, f))
        self.render_pool.start(task)

    def _render_progress(self, task, fraction):
        if task.generation != self._generation:
            return
        text = f"Rendering preview… {fraction * 100:.0f}%"
        if self.stack.currentWidget() is self.busy_page:
            self.busy_page.setText(f"Large pattern\n\n{text}")
        else:
            self.status_label.setText(text)

    def _render_done(self, task, pattern, qimage=None):
        self._finish(task)
        self.rendering = False
        if task.generation != self._generation:
            return  # a different sprite was opened meanwhile
        first = self.pattern.image is None  # first preview of a large pattern
        if first:
            self.stack.setCurrentWidget(self.view)
            for w in (self.zoom_in_btn, self.zoom_out_btn, self.fit_btn, self.actual_btn,
                      self.adjust_btn):
                w.setEnabled(True)
        if self.status_label.text().startswith("Rendering preview"):
            self.status_label.setText("")
        self._display(pattern, refit=first, qimage=qimage)
        if self.target_layout != pattern.layout:
            self._start_render()
        self._update_generate()

    def _render_failed(self, task, message):
        self._finish(task)
        self.rendering = False
        if task.generation != self._generation:
            return
        if self.pattern.image is None:  # nothing was ever shown: report and clear
            name = self.pattern.source.name
            self._show_pattern(None)
            self.show_error("Cannot show this pattern", f"{name}\n\n{message}")
            return
        self.target_layout = self.pattern.layout  # keep the last good preview
        self._update_offset_label()
        self._update_generate()
        self.show_error("Adjustment not applied", message)

    # --- full-detail view of large patterns ---------------------------------------------

    def _schedule_detail(self):
        if self.pattern is not None and self.pattern.scale > 1:
            self.detail_timer.start()

    def _request_detail(self):
        """When a large pattern is zoomed in past its overview resolution, render
        the visible area at full detail (exactly as exported)."""
        p = self.pattern
        if p is None or p.image is None or p.scale == 1 or self.target_layout != p.layout:
            return
        if self.view.zoom * p.scale <= 1:  # the overview already has enough detail
            self.view.clear_detail()
            return
        width, height = p.layout.canvas_size
        rect = self.view.visible_scene_rect()
        box = (max(0, math.floor(rect.left())), max(0, math.floor(rect.top())),
               min(width, math.ceil(rect.right())), min(height, math.ceil(rect.bottom())))
        if box[2] <= box[0] or box[3] <= box[1]:
            return
        if (box[2] - box[0]) * (box[3] - box[1]) > DETAIL_MAX_PIXELS:
            self.view.clear_detail()
            return
        if self._detail_busy:
            self._detail_pending = True
            return
        self._detail_busy = True
        task = DetailTask(p.grid, p.layout, box, self._generation)
        self._tasks.add(task)
        task.signals.finished.connect(lambda image: self._detail_done(task, image))
        task.signals.failed.connect(lambda msg: self._detail_done(task, None))
        self.detail_pool.start(task)

    def _detail_done(self, task, image):
        self._finish(task)
        self._detail_busy = False
        current = (self.pattern is not None and task.generation == self._generation
                   and task.layout == self.pattern.layout == self.target_layout)
        if current and image is not None:
            self.view.set_detail(image, task.box[0], task.box[1])
        if self._detail_pending:
            self._detail_pending = False
            self._request_detail()

    def wait_for_detail(self):
        """Block until any pending full-detail render is shown (tests)."""
        self.detail_timer.stop()
        self._request_detail()
        while self._detail_busy:
            self.detail_pool.waitForDone()
            QApplication.processEvents()

    def wait_for_render(self):
        """Block until the preview shows the newest requested layout (tests)."""
        while self.rendering:
            self.render_pool.waitForDone()
            QApplication.processEvents()

    def _update_offset_label(self):
        if self.pattern is None or self.target_layout is None:
            self.offset_label.setText("")
            return
        rows = []
        for layer, unit in ((SPRITE, "beads"), (RINGS, "px"), (GUIDES, "px")):
            x, y = self.layer_offset(layer)
            text = f"{LAYER_NAMES[layer]}: H {signed(x, unit)}, V {signed(y, unit)}"
            rows.append(f"<b>{text}</b>" if layer == self.active_layer else text)
        self.offset_label.setText("<br>".join(rows))

    def _finish(self, task):
        """Forget a task that has reported back. Deleting its signal object also
        releases the callbacks connected to it; otherwise the task, and the
        pattern it holds, would be kept alive through Qt (a memory leak)."""
        self._tasks.discard(task)
        task.signals.deleteLater()

    def _update_generate(self):
        ready = (self.pattern is not None and not self.saving and not self.rendering
                 and self.target_layout == self.pattern.layout)
        self.generate_btn.setEnabled(ready)
        self.charts_btn.setEnabled(ready and self.supply is not None)

    # --- opening sprites -----------------------------------------------------

    def choose_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Upload sprite", "",
                                              "Sprite images (*.png *.gif)")
        if path:
            self.open_file(path)

    def dragEnterEvent(self, event):
        if not self.saving and event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls() if u.isLocalFile()]
        event.acceptProposedAction()
        if len(files) != 1:
            self.show_error("One sprite at a time", "Please drop a single PNG or GIF file.")
            return
        self.open_file(files[0])

    def open_file(self, path):
        """Validate, process and display one sprite. Returns True on success."""
        if self.saving:
            return False
        self._generation += 1  # any adjustment still rendering belongs to the old sprite
        self.leave_adjust_mode()
        self.setCursor(Qt.CursorShape.WaitCursor)
        try:
            pattern = self._build(path)
        except EngineError as exc:
            self._show_pattern(None)
            self.show_error("Cannot use this file", f"{Path(path).name}\n\n{exc}")
            return False
        except Exception:
            self._show_pattern(None)
            self.show_error("Unexpected error", "The sprite could not be processed.\n\n"
                            + traceback.format_exc(limit=3))
            return False
        finally:
            self.unsetCursor()
        if pattern is None:  # the user cancelled a background question
            return False
        self._show_pattern(pattern)
        return True

    def _build(self, path):
        try:
            return load_pattern(path)
        except BackgroundDecisionNeeded as exc:
            mode = self.ask_background(exc)
            return load_pattern(path, background=mode) if mode else None

    def ask_background(self, exc):
        """Ask the smallest necessary background question. Returns a mode or None."""
        box = QMessageBox(self)
        box.setWindowTitle("Background color")
        box.setIcon(QMessageBox.Icon.Question)
        box.setText(str(exc))
        if exc.color is not None and exc.interior_pixels:
            choices = {box.addButton("Remove outside only", QMessageBox.ButtonRole.AcceptRole): "outside",
                       box.addButton("Remove everywhere", QMessageBox.ButtonRole.AcceptRole): "all"}
        else:
            choices = {box.addButton("Keep every pixel", QMessageBox.ButtonRole.AcceptRole): "keep"}
        box.addButton(QMessageBox.StandardButton.Cancel)
        box.exec()
        return choices.get(box.clickedButton())

    def show_error(self, title, message):
        QMessageBox.warning(self, title, message)

    def _show_pattern(self, pattern):
        """Show a newly opened pattern (or nothing) at its automatic alignment."""
        has = pattern is not None
        shown = has and pattern.image is not None  # large patterns render in the background
        for w in (self.zoom_in_btn, self.zoom_out_btn, self.fit_btn, self.actual_btn,
                  self.adjust_btn):
            w.setEnabled(shown)
        self.view.clear_detail()
        self.status_label.setText("")
        self.saved_path_label.setText("")
        self.target_layout = pattern.layout if has else None
        self.supply = None  # never keep counts from a previous sprite
        if not has:
            self.pattern = None
            self.info_panel.clear()
            self.stack.setCurrentWidget(self.drop_zone)
            self.view.item.setPixmap(QPixmap())
            self.file_label.setText("No sprite loaded")
            self.notes_label.setText("")
            self.alignment_label.setText("")
            self.zoom_label.setText("")
            for label in self.info.values():
                label.setText("–")
            self._update_generate()
            return
        self.file_label.setText(pattern.source.name)
        if shown:
            self.stack.setCurrentWidget(self.view)
        else:
            self.view.item.setPixmap(QPixmap())
            self.busy_page.setText("Large pattern\n\nRendering preview… 0%")
            self.stack.setCurrentWidget(self.busy_page)
        self._display(pattern, refit=True)
        self.info_panel.show_counts(pattern.grid)
        self._start_supply(pattern.grid)
        if not shown:
            self._start_render()
        self._update_generate()

    def _start_supply(self, grid):
        task = SupplyTask(grid, self._generation)
        self._tasks.add(task)
        task.signals.finished.connect(lambda report: self._supply_done(task, report))
        task.signals.failed.connect(lambda msg: self._supply_failed(task, msg))
        self.info_pool.start(task)

    def _supply_done(self, task, report):
        self._finish(task)
        if task.generation != self._generation or self.pattern is None:
            return  # belongs to a sprite that is no longer shown
        self.supply = report
        self.info_panel.show_supply(self.pattern.grid, report)
        self._update_generate()

    def _supply_failed(self, task, message):
        self._finish(task)
        if task.generation == self._generation:
            self.info_panel.supply_title.setText(
                f"<b>Suggested Perler Supplies</b> — ⚠ could not be calculated: {message}")

    def wait_for_supply(self):
        """Block until the supply report is shown (tests)."""
        while self.info_pool.activeThreadCount() or self._pending_signals():
            self.info_pool.waitForDone()
            QApplication.processEvents()

    def _pending_signals(self):
        return any(isinstance(t, SupplyTask) for t in self._tasks)

    def _display(self, pattern, refit, qimage=None):
        """Draw a rendered pattern and its information; zoom and scroll are kept
        unless `refit` is set. `qimage` is the preview already converted."""
        self.pattern = pattern
        grid, layout, alignment = pattern.grid, pattern.layout, pattern.alignment
        if pattern.image is not None:
            self.view.set_image(qimage if qimage is not None else to_qimage(pattern.image),
                                refit=refit, scale=pattern.scale, canvas=layout.canvas_size)
            self._schedule_detail()
        self.info["size"].setText(f"{grid.width} × {grid.height} beads")
        self.info["beads"].setText(f"{grid.total:,}")
        self.info["colors"].setText(str(len(grid.color_counts())))
        self.info["grid"].setText(f"{layout.boards_x} × {layout.boards_y}")
        self.info["boards"].setText(str(layout.total_boards))
        occupied = pattern.occupied_boards
        self.info["occupied"].setText("unavailable" if occupied is None else str(occupied))
        notes = list(grid.warnings)
        if pattern.scale > 1:
            width, height = layout.canvas_size
            notes.append(f"Large pattern ({width:,} × {height:,} px): the preview is shown at "
                         f"1/{pattern.scale} size and switches to full detail when you zoom in. "
                         "Exports always use full detail.")
            if not pattern.png_possible:
                notes.append("Too large for a single PNG; Export Charts & CSV saves every board.")
        self.notes_label.setText("\n".join(notes))
        if alignment.warnings:
            self.alignment_label.setStyleSheet(f"color: {theme.ERROR};")
            self.alignment_label.setText("⚠ Misaligned layers\n" + "\n".join(alignment.warnings))
        elif pattern.adjusted:
            self.alignment_label.setStyleSheet(f"color: {theme.OK};")
            self.alignment_label.setText("Layers adjusted and still aligned with bead positions.")
        else:
            self.alignment_label.setText("")
        self.info_panel.show_boards(pattern)
        self._update_offset_label()

    # --- export ----------------------------------------------------------------

    def choose_export_path(self):
        if not self.pattern:
            return
        if not self.pattern.png_possible:
            self.show_notice("Single PNG not available", png_too_large_message(self.pattern))
            return
        default = self.pattern.source.with_name(self.pattern.source.stem + "_bead_pattern.png")
        path, _ = QFileDialog.getSaveFileName(self, "Save bead pattern PNG", str(default),
                                              "PNG images (*.png)")
        if path:
            if not path.lower().endswith(".png"):
                path += ".png"
            self.start_export(path)

    def start_export(self, path):
        """Save in the background so the window stays responsive."""
        self._set_saving(True)
        self.status_label.setText("Saving PNG…")
        self.saved_path_label.setText("")
        task = ExportTask(self.pattern, path)
        self._tasks.add(task)
        task.signals.finished.connect(lambda dest: self._export_done(task, dest, None))
        task.signals.failed.connect(lambda msg: self._export_done(task, None, msg))
        task.signals.progress.connect(
            lambda f: self.status_label.setText(f"Saving PNG… {f * 100:.0f}%"))
        QThreadPool.globalInstance().start(task)

    def _export_done(self, task, destination, error):
        self._finish(task)
        self._set_saving(False)
        if error:
            self.status_label.setText("PNG was not saved.")
            self.saved_path_label.setText("")
            self.show_error("PNG not saved", error)
        else:
            self.status_label.setText("Saved and verified:")
            self.saved_path_label.setText(str(destination))

    def choose_charts_folder(self):
        if not self.pattern or self.supply is None:
            return
        folder = QFileDialog.getExistingDirectory(
            self, "Choose where to save the charts and CSV files", str(self.pattern.source.parent))
        if folder:
            self.start_chart_export(folder)

    def start_chart_export(self, folder):
        """Write charts and CSV files for exactly what the preview shows."""
        self._set_saving(True)
        self.status_label.setText("Saving charts and CSV files…")
        self.saved_path_label.setText("")
        task = ChartExportTask(self.pattern, self.supply, folder)
        self._tasks.add(task)
        task.signals.finished.connect(lambda result: self._charts_done(task, result, None))
        task.signals.failed.connect(lambda msg: self._charts_done(task, None, msg))
        task.signals.progress.connect(
            lambda f: self.status_label.setText(f"Saving charts and CSV files… {f * 100:.0f}%"))
        QThreadPool.globalInstance().start(task)

    def _charts_done(self, task, result, error):
        self._finish(task)
        self._set_saving(False)
        if error:
            self.status_label.setText("Charts and CSV files were not saved.")
            self.show_error("Charts not saved", error)
            return
        folder, files, skipped = result
        self.status_label.setText(f"Saved {len(files)} chart and CSV files to:")
        self.saved_path_label.setText(str(folder))
        if skipped:
            self.show_notice("Board charts not included",
                             "The color and Perler supply CSV files were saved, but board charts "
                             f"and board counts were left out because they would be wrong:\n\n{skipped}")

    def show_notice(self, title, message):
        QMessageBox.information(self, title, message)

    def closeEvent(self, event):
        QThreadPool.globalInstance().waitForDone()  # never abandon a save half-way
        self.render_pool.waitForDone()
        self.info_pool.waitForDone()
        self.detail_pool.waitForDone()
        super().closeEvent(event)

    def _set_saving(self, saving):
        self.saving = saving
        self.upload_btn.setEnabled(not saving)
        self._update_generate()
