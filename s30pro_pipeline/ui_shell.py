"""Shell widgets for the v2 window: the stage rail, the session ribbon,
the pane header and the action bar.

These are plain PyQt6 widgets with no knowledge of the pipeline. The
window wires them up in ui_v2.UiV2Mixin. Nothing here draws its own
colours: everything comes from theme.py's object names, so restyling the
app means editing theme.py alone.
"""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QCheckBox, QFrame, QHBoxLayout, QLabel, QMenu, QProgressBar, QPushButton,
    QSizePolicy, QToolButton, QVBoxLayout, QWidget,
)

from s30pro_pipeline.constants import STAGES

__all__ = ["StageRail", "SessionRibbon", "PaneHeader", "ActionBar",
           "AdvancedSection", "hairline", "STAGE_GROUPS", "COMPACT_WIDTH"]

# The 13 stages read as four phases. Grouping them is most of the answer to
# "where am I" — a flat list of 13 does not scan.
STAGE_GROUPS = [
    ("STACK", (0, 1)),
    ("CLEAN", (2, 3, 4, 5, 6, 7)),
    ("STRETCH", (8, 9)),
    ("FINISH", (10, 11, 12)),
]

# Below this window width the rail drops its labels and the ribbon collapses
# its detail line. One threshold, used by both.
COMPACT_WIDTH = 1180

RAIL_WIDTH = 212
RAIL_WIDTH_COMPACT = 58

# Short rail labels — the full stage titles are too long for 212px.
RAIL_LABELS = {
    0: "Preprocess", 1: "Crop", 2: "Remove Green", 3: "Auto Gradient",
    4: "Remove Background", 5: "Remove Stars", 6: "Denoise",
    7: "Hubble Palette", 8: "Stretch", 9: "Histogram", 10: "Final Touch",
    11: "Annotate", 12: "Watermark",
}


def hairline(vertical=False):
    """A 1px rule. Use instead of QFrame.HLine, which draws a bevel."""
    f = QFrame()
    f.setObjectName("VRule" if vertical else "Hairline")
    if vertical:
        f.setFixedWidth(1)
    else:
        f.setFixedHeight(1)
    return f


def _repolish(w):
    """Re-evaluate QSS property selectors after setProperty()."""
    w.style().unpolish(w)
    w.style().polish(w)


class RailRow(QFrame):
    """One stage in the rail: number, name, state flag, progress hairline."""

    clicked = pyqtSignal(int)

    def __init__(self, idx, parent=None):
        super().__init__(parent)
        self.idx = idx
        self.setObjectName("RailRow")
        self.setProperty("active", "false")
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(13, 6, 14, 6)
        outer.setSpacing(5)

        row = QHBoxLayout()
        row.setSpacing(9)
        self.num = QLabel(f"{idx + 1:02d}")
        self.num.setObjectName("RailNum")
        self.num.setFixedWidth(15)
        self.name = QLabel(RAIL_LABELS.get(idx, STAGES[idx]))
        self.name.setObjectName("RailName")
        self.flag = QLabel("")
        self.flag.setObjectName("RailFlag")
        row.addWidget(self.num)
        row.addWidget(self.name, 1)
        row.addWidget(self.flag)
        outer.addLayout(row)

        self.bar = QProgressBar()
        self.bar.setTextVisible(False)
        self.bar.setRange(0, 100)
        self.bar.setValue(0)
        self.bar.setVisible(False)
        outer.addWidget(self.bar)

        # Qt delivers a mouse press to whichever child widget is under the
        # cursor and does not bubble it up to the parent on its own — since
        # these four children cover almost the whole row, without this the
        # row's own mousePressEvent below only fired on the thin sliver of
        # margin around them, making a click on the stage name/number/flag
        # (i.e. most of the row) silently do nothing. Marking them
        # transparent to mouse events lets clicks anywhere in the row reach
        # RailRow itself.
        for w in (self.num, self.name, self.flag, self.bar):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        self.setToolTip(STAGES[idx])

    def mousePressEvent(self, e):
        self.clicked.emit(self.idx)

    def set_active(self, on):
        self.setProperty("active", "true" if on else "false")
        self.name.setProperty("state", "active" if on else "")
        _repolish(self)
        _repolish(self.name)

    def set_state(self, state, text=None):
        """state: 'done' | 'queued' | 'off' | 'running' | 'skipped'."""
        flags = {"done": "\u2713", "queued": "QUEUED", "off": "OFF",
                 "skipped": "SKIPPED", "running": ""}
        self.flag.setText(text if text is not None else flags.get(state, ""))
        self.flag.setProperty(
            "state", "done" if state in ("done", "running") else "")
        self.name.setProperty("state", state if state == "off" else "")
        self.bar.setVisible(state == "running")
        _repolish(self.flag)
        _repolish(self.name)

    def set_progress(self, frac):
        self.bar.setValue(max(0, min(100, int(frac * 100))))

    def set_compact(self, on):
        self.name.setVisible(not on)
        self.flag.setVisible(not on)
        m = self.layout().contentsMargins()
        self.layout().setContentsMargins(13 if not on else 8, m.top(),
                                         14 if not on else 8, m.bottom())


class StageRail(QWidget):
    """Fixed-width list of all 13 stages, grouped, never scrolling.

    It is the primary navigation AND the progress display: no separate
    progress bar per stage is needed anywhere else.
    """

    stageSelected = pyqtSignal(int)
    importRequested = pyqtSignal()
    exportRequested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Rail")
        self.setFixedWidth(RAIL_WIDTH)
        self._compact = False
        self.rows = {}
        self._group_heads = []

        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        for title, idxs in STAGE_GROUPS:
            head = QLabel(title)
            head.setObjectName("GroupHead")
            head.setContentsMargins(16, 14, 16, 6)
            self._group_heads.append(head)
            v.addWidget(head)
            for i in idxs:
                row = RailRow(i)
                row.clicked.connect(self.stageSelected.emit)
                self.rows[i] = row
                v.addWidget(row)

        v.addStretch(1)
        v.addWidget(hairline())

        foot = QVBoxLayout()
        foot.setContentsMargins(16, 12, 16, 12)
        foot.setSpacing(8)
        self._foot_head = QLabel("SETTINGS")
        self._foot_head.setObjectName("GroupHead")
        foot.addWidget(self._foot_head)
        self.preset_label = QLabel("defaults")
        self.preset_label.setObjectName("SubHeader")
        foot.addWidget(self.preset_label)
        btns = QHBoxLayout()
        btns.setSpacing(8)
        self.import_btn = QPushButton("\u2912 IMPORT")
        self.import_btn.setObjectName("Ghost")
        self.import_btn.setToolTip("Load all pipeline settings from a JSON file")
        self.import_btn.clicked.connect(self.importRequested.emit)
        self.export_btn = QPushButton("\u2913 EXPORT")
        self.export_btn.setObjectName("Ghost")
        self.export_btn.setToolTip("Save all pipeline settings to a JSON file")
        self.export_btn.clicked.connect(self.exportRequested.emit)
        btns.addWidget(self.import_btn)
        btns.addWidget(self.export_btn)
        foot.addLayout(btns)
        v.addLayout(foot)
        self._foot = foot

    def add_footer_widget(self, widget):
        """Append a widget under Import/Export — for whole-pipeline
        actions (Run Full Pipeline, Close pipeline) that belong with the
        rail's other pipeline-wide controls rather than the pane."""
        self._foot.addWidget(widget)

    # -- state ------------------------------------------------------------
    def set_current(self, idx):
        for i, row in self.rows.items():
            row.set_active(i == idx)

    def set_state(self, idx, state, text=None):
        if idx in self.rows:
            self.rows[idx].set_state(state, text)

    def set_progress(self, idx, frac):
        if idx in self.rows:
            self.rows[idx].set_progress(frac)

    def set_preset_name(self, name):
        self.preset_label.setText(name or "defaults")

    def set_compact(self, on):
        if on == self._compact:
            return
        self._compact = on
        self.setFixedWidth(RAIL_WIDTH_COMPACT if on else RAIL_WIDTH)
        for row in self.rows.values():
            row.set_compact(on)
        for h in self._group_heads:
            h.setVisible(not on)
        self._foot_head.setVisible(not on)
        self.preset_label.setVisible(not on)
        self.import_btn.setText("\u2912" if on else "\u2912 IMPORT")
        self.export_btn.setText("\u2913" if on else "\u2913 EXPORT")


class SessionRibbon(QWidget):
    """Two lines across the top: what this image is, and how far the run got.

    Line 1: target, folder, run progress. Line 2: the image-info fields.
    The window's existing status_label / progress_bar / image_info_label are
    handed in so every 1.x call site that writes to them keeps working.
    """

    refreshRequested = pyqtSignal()

    def __init__(self, status_label, progress_bar, info_label, parent=None):
        super().__init__(parent)
        self.setObjectName("Ribbon")
        self._compact = False

        v = QVBoxLayout(self)
        v.setContentsMargins(18, 10, 18, 11)
        v.setSpacing(7)

        top = QHBoxLayout()
        top.setSpacing(14)
        self.kicker = QLabel("SESSION")
        self.kicker.setObjectName("Kicker")
        self.target = QLabel("No image loaded")
        self.target.setObjectName("Lead")
        self.folder = QLabel("")
        self.folder.setObjectName("Caption")
        self.status = status_label          # the window's own QLabel
        self.count = QLabel("")
        self.count.setObjectName("SubHeader")
        self.progress = progress_bar        # the window's own QProgressBar
        # Shortened to make room for the percentage/elapsed-time labels
        # beside it — the bar's own built-in percentage text is turned off
        # (progress_pct replaces it) so the number isn't shown twice.
        self.progress.setFixedWidth(120)
        self.progress.setTextVisible(False)
        self.progress_pct = QLabel("")
        self.progress_pct.setObjectName("SubHeader")
        self.progress_pct.setFixedWidth(34)
        self.progress_pct.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.progress_time = QLabel("")
        self.progress_time.setObjectName("SubHeader")
        self.progress_time.setFixedWidth(48)
        top.addWidget(self.kicker)
        top.addWidget(self.target)
        top.addWidget(self.folder)
        top.addStretch(1)
        top.addWidget(self.status)
        top.addWidget(self.count)
        top.addWidget(self.progress)
        top.addWidget(self.progress_pct)
        top.addWidget(self.progress_time)
        v.addLayout(top)

        bottom = QHBoxLayout()
        bottom.setSpacing(12)
        self.info = info_label              # the window's own QLabel
        self.info.setObjectName("SubHeader")
        self.details_btn = QPushButton("DETAILS \u2304")
        self.details_btn.setObjectName("Link")
        self.details_btn.setCheckable(True)
        self.details_btn.setVisible(False)
        self.details_btn.toggled.connect(self._on_details)
        self.refresh_btn = QPushButton("\u21bb REFRESH")
        self.refresh_btn.setObjectName("Link")
        self.refresh_btn.setToolTip(
            "Refresh image info from the current Siril image")
        self.refresh_btn.clicked.connect(self.refreshRequested.emit)
        bottom.addWidget(self.info, 1)
        bottom.addWidget(self.details_btn)
        bottom.addWidget(self.refresh_btn)
        v.addLayout(bottom)

    def set_target(self, name, folder=""):
        self.target.setText(name or "No image loaded")
        self.folder.setText(folder)

    def set_progress_text(self, done, total):
        self.count.setText(f"{done} of {total} done" if total else "")

    def set_running(self, running):
        self.kicker.setText("RUNNING" if running else "SESSION")

    def _on_details(self, shown):
        self.info.setVisible(shown or not self._compact)
        self.details_btn.setText("DETAILS \u2303" if shown else "DETAILS \u2304")

    def set_compact(self, on):
        if on == self._compact:
            return
        self._compact = on
        self.folder.setVisible(not on)
        self.details_btn.setVisible(on)
        self.info.setVisible(not on)
        self.refresh_btn.setText("\u21bb" if on else "\u21bb REFRESH")
        if not on:
            self.details_btn.setChecked(False)


class PaneHeader(QWidget):
    """Top of the settings pane: stage number, enable tick, title, one-line
    description, and the "starting from" row that owns "Use Siril's image".
    """

    enabledToggled = pyqtSignal(bool)
    useSirilRequested = pyqtSignal()

    def __init__(self, number, title, parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 18, 20, 14)
        v.setSpacing(6)

        top = QHBoxLayout()
        kicker = QLabel(f"STAGE {number:02d}")
        kicker.setObjectName("Kicker")
        self.enable = QCheckBox("Run this stage")
        self.enable.setToolTip(
            "Whether this stage runs as part of Run Full Pipeline.")
        self.enable.toggled.connect(self.enabledToggled.emit)
        top.addWidget(kicker)
        top.addStretch(1)
        top.addWidget(self.enable)
        v.addLayout(top)

        self.title = QLabel(title)
        self.title.setObjectName("Hero")
        self.title.setWordWrap(True)
        v.addWidget(self.title)

        self.desc = QLabel("")
        self.desc.setObjectName("SubHeader")
        self.desc.setWordWrap(True)
        self.desc.setVisible(False)
        v.addWidget(self.desc)

        # Source row — the input, stated before the controls.
        src = QFrame()
        src.setObjectName("ImageFrame")
        sl = QHBoxLayout(src)
        sl.setContentsMargins(11, 7, 8, 7)
        sl.setSpacing(8)
        self.source = QLabel("Starting from: previous stage")
        self.source.setObjectName("SubHeader")
        use_btn = QPushButton("\u21e9 USE SIRIL'S IMAGE")
        use_btn.setObjectName("Link")
        use_btn.setToolTip(
            "Preview whatever image is currently loaded in Siril as this "
            "stage's starting point.")
        use_btn.clicked.connect(self.useSirilRequested.emit)
        sl.addWidget(self.source, 1)
        sl.addWidget(use_btn)
        v.addWidget(src)

    def set_description(self, text):
        self.desc.setText(text)
        self.desc.setVisible(bool(text))

    def set_source(self, text):
        self.source.setText(text)


class ActionBar(QWidget):
    """Pinned pane footer: one secondary action, one overflow menu.

    Run Full Pipeline and Close pipeline live in the rail footer instead
    (see StageRail.add_footer_widget) — they're whole-pipeline actions,
    grouped there with Import/Export rather than here with the pane's own
    per-stage/save actions.

    The 1.x buttons (export settings, reset) stay as real QPushButtons —
    _set_running() disables them by attribute — but they live off-screen
    and the menu actions click them, so the enabled state stays in one
    place.
    """

    def __init__(self, save_btn, menu_buttons, parent=None):
        super().__init__(parent)
        self.setObjectName("PaneFooter")
        v = QVBoxLayout(self)
        v.setContentsMargins(20, 16, 20, 16)
        v.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(8)
        row.addWidget(save_btn, 1)

        self.overflow = QToolButton()
        self.overflow.setObjectName("Overflow")
        self.overflow.setText("\u22ef")
        self.overflow.setPopupMode(
            QToolButton.ToolButtonPopupMode.InstantPopup)
        self.overflow.setToolTip("More actions")
        menu = QMenu(self.overflow)
        self._pairs = []
        for label, btn in menu_buttons:
            act = menu.addAction(label)
            act.triggered.connect(btn.click)
            self._pairs.append((act, btn))
            btn.setVisible(False)          # kept alive, not shown
        menu.aboutToShow.connect(self._sync)
        self.overflow.setMenu(menu)
        self.menu = menu
        row.addWidget(self.overflow)
        v.addLayout(row)

    def add_action(self, label, slot):
        """For future functionality: one line, no layout change."""
        act = self.menu.addAction(label)
        act.triggered.connect(slot)
        return act

    def add_separator(self):
        self.menu.addSeparator()

    def _sync(self):
        for act, btn in self._pairs:
            act.setEnabled(btn.isEnabled())


class AdvancedSection(QWidget):
    """The disclosure every stage puts its non-essential controls behind.

    Two or three controls stay visible in a stage; everything else goes in
    here. Collapsed by default, and it says how many settings it holds so
    nothing feels hidden.
    """

    def __init__(self, title="ADVANCED", note="", parent=None):
        super().__init__(parent)
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(10)
        v.addWidget(hairline())

        head = QHBoxLayout()
        head.setSpacing(8)
        self.toggle = QPushButton("\u25b8  " + title)
        self.toggle.setObjectName("CollapseHeader")
        self.toggle.setCheckable(True)
        self.note = QLabel(note)
        self.note.setObjectName("Caption")
        head.addWidget(self.toggle)
        head.addWidget(self.note, 1)
        v.addLayout(head)

        self.body = QWidget()
        self.body.setVisible(False)
        self.content = QVBoxLayout(self.body)
        self.content.setContentsMargins(0, 2, 0, 0)
        self.content.setSpacing(10)
        v.addWidget(self.body)

        self._title = title
        self.toggle.toggled.connect(self._on_toggle)
        self.setSizePolicy(QSizePolicy.Policy.Preferred,
                           QSizePolicy.Policy.Maximum)

    def _on_toggle(self, shown):
        self.body.setVisible(shown)
        self.toggle.setText(("\u25be  " if shown else "\u25b8  ") + self._title)

    def set_note(self, text):
        self.note.setText(text)
