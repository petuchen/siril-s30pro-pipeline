"""v2 window shell: rail + one-stage pane + preview.

Drop-in over the 1.x layout. Mix this in FIRST so its `_build_ui` and
`_stage_box` win over the ones in S30Pro_Pipeline.py:

    class UnifiedPipelineWindow(UiV2Mixin, Stage1Mixin, AnnotateMixin, ...):

Every attribute the 1.x code touches is still created here with the same
name — run_all_btn, save_file_btn, export_settings_btn, reset_btn,
close_pipeline_btn, progress_bar, status_label, image_info_label,
preview_stage_combo, compare, chk_display_stretch, btn_before/split/after,
_stage_toggle_pairs — so no stage mixin needs editing to boot on v2.
Stages then migrate to `_advanced_section()` one at a time.
"""

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGroupBox, QHBoxLayout, QLabel,
    QProgressBar, QPushButton, QScrollArea, QSplitter, QStackedWidget,
    QVBoxLayout, QWidget,
)

from s30pro_pipeline.constants import STAGES
from s30pro_pipeline.ui_widgets import CompareView
from s30pro_pipeline.ui_shell import (
    ActionBar, AdvancedSection, COMPACT_WIDTH, PaneHeader, SessionRibbon,
    StageRail, hairline,
)

__all__ = ["UiV2Mixin"]

PANE_MIN = 300
PANE_MAX = 480

# One-line "why you need this" per stage, shown under the pane title. Taken
# from the README's stage table — beginners are the default audience.
STAGE_BLURBS = {
    0: "Aligns and averages hundreds of short exposures into one deep "
       "image, then calibrates the colours against star catalogues.",
    1: "Trims the ragged edges left by the telescope's drift, with an "
       "optional rotate first.",
    2: "Removes the green cast colour cameras tend to produce.",
    3: "A tunable gradient-flattening pass — useful on its own, or as a "
       "milder pre-pass before Remove Background.",
    4: "Flattens the sky glow from light pollution and moonlight so the "
       "object stands out.",
    5: "Separates stars from the nebulosity so later stages can work on "
       "one without the other.",
    6: "AI noise reduction — removes grain from faint areas while keeping "
       "stars and detail.",
    7: "Remaps emission-nebula colours into the gold-and-teal Hubble look.",
    8: "Brightens the image from almost black to visible without "
       "destroying the colours.",
    9: "Per-channel colour balance after the big stretch.",
    10: "The familiar last-mile polish: brightness, contrast, saturation, "
        "sharpening.",
    11: "Labels stars and deep-sky objects in the plate-solved field.",
    12: "Draws a semi-transparent info block onto the image for sharing.",
}


class UiV2Mixin:
    # ------------------------------------------------------------------ ui
    def _build_ui(self):
        self._stage_toggle_pairs = []
        self.stage_pages = {}
        self.stage_headers = {}
        self._syncing_stage = False
        self._compact = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # -- ribbon (owns the 1.x status/progress/info widgets) -----------
        self.status_label = QLabel("Ready.")
        self.status_label.setObjectName("StatusLabel")
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.image_info_label = QLabel("No image loaded.")
        self.image_info_label.setWordWrap(False)
        self.ribbon = SessionRibbon(self.status_label, self.progress_bar,
                                    self.image_info_label)
        self.ribbon.refreshRequested.connect(self._update_image_info)
        # Aliased so the window's 1.x-era progress-handling code
        # (_set_running / _on_progress) can drive these directly, same as
        # it already does for progress_bar/status_label/image_info_label.
        self.progress_pct_label = self.ribbon.progress_pct
        self.progress_time_label = self.ribbon.progress_time
        root.addWidget(self.ribbon)

        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        root.addLayout(body, 1)

        # -- rail --------------------------------------------------------
        self.rail = StageRail()
        self.rail.stageSelected.connect(self._select_stage)
        self.rail.importRequested.connect(self.on_import_settings)
        self.rail.exportRequested.connect(self.on_export_settings)
        body.addWidget(self.rail)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(1)
        body.addWidget(splitter, 1)

        # -- pane --------------------------------------------------------
        pane = QWidget()
        pane.setObjectName("Pane")
        pane.setMinimumWidth(PANE_MIN)
        pane.setMaximumWidth(PANE_MAX)
        pv = QVBoxLayout(pane)
        pv.setContentsMargins(0, 0, 0, 0)
        pv.setSpacing(0)

        self.stage_stack = QStackedWidget()
        pv.addWidget(self.stage_stack, 1)

        # Buttons the 1.x code disables by attribute.
        self.run_all_btn = QPushButton("\u25b6  RUN FULL PIPELINE", self)
        self.run_all_btn.setObjectName("RunAll")
        self.run_all_btn.setToolTip(
            "Run every enabled stage in order, top to bottom.")
        self.run_all_btn.clicked.connect(self.on_run_all)
        self.save_file_btn = QPushButton("SAVE IMAGE\u2026", self)
        self.save_file_btn.setToolTip(
            "Save the image currently loaded in Siril as FITS, JPEG, PNG or "
            "TIFF (uses Siril's own save commands).")
        self.save_file_btn.clicked.connect(self.on_save_file)
        self.export_settings_btn = QPushButton("Export settings\u2026", self)
        self.export_settings_btn.clicked.connect(self.on_export_settings)
        self.reset_btn = QPushButton("Reset pipeline\u2026", self)
        self.reset_btn.clicked.connect(self.on_reset_pipeline)
        self.close_pipeline_btn = QPushButton("\u2715  CLOSE PIPELINE", self)
        self.close_pipeline_btn.setObjectName("Ghost")
        self.close_pipeline_btn.setToolTip("Close this pipeline window.")
        self.close_pipeline_btn.clicked.connect(self.close)

        # Run Full Pipeline and Close pipeline go in the rail footer, right
        # under Import/Export — all four are whole-pipeline actions, not
        # per-stage ones, so they belong together rather than split
        # between the rail and the pane.
        self.rail.add_footer_widget(self.run_all_btn)
        self.rail.add_footer_widget(self.close_pipeline_btn)

        self.action_bar = ActionBar(
            self.save_file_btn,
            [("Export settings\u2026", self.export_settings_btn),
             ("Reset pipeline\u2026", self.reset_btn)])
        self.action_bar.add_separator()
        self.action_bar.add_action("Enable all stages",
                                   self.on_expand_all_stages)
        self.action_bar.add_action("Disable all stages",
                                   self.on_collapse_all_stages)
        pv.addWidget(self.action_bar)
        splitter.addWidget(pane)

        # -- preview -----------------------------------------------------
        splitter.addWidget(self._build_preview())
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([352, 1088])

        # -- stages ------------------------------------------------------
        # Called in index order; each one registers its page via _stage_box.
        for build in (self._build_stage1, self._build_stage_crop,
                      self._build_stage_scnr, self._build_stage_agr,
                      self._build_stage2, self._build_stage_stars,
                      self._build_stage3, self._build_stage_palette,
                      self._build_stage4, self._build_stage_hist,
                      self._build_stage_touch, self._build_stage_ann,
                      self._build_stage_watermark):
            build()

        self._select_stage(0)
        self._refresh_rail_states()
        # _select_stage(0) above is a no-op on preview_stage_combo (it's
        # already at index 0 by default, so its currentIndexChanged signal
        # never fires) — call this explicitly so the very first stage shown
        # already reflects whatever's loaded in Siril, same as every later
        # stage change does via _on_preview_stage_changed.
        #
        # Deferred via singleShot(0) rather than called directly: this
        # method fetches Siril's *full-resolution* current image
        # (self.siril.get_image_pixeldata()) and runs it through
        # to_hwc_float/display_autostretch/make_qimage — real work, and on
        # a typical smart-telescope stack (tens of megapixels) not
        # instant. _build_ui() runs inside __init__(), which runs before
        # the caller's win.show() — so calling this directly here meant
        # the whole plugin window stayed unshown/frozen for however long
        # that fetch+stretch took, on every single launch (whenever Siril
        # already had an image loaded, the normal case). Queuing it for
        # the next event-loop tick instead lets __init__ finish and the
        # window actually appear first; the preview then pops in a beat
        # later instead of blocking the launch itself.
        QTimer.singleShot(0, self._refresh_preview)

    def _build_preview(self):
        right = QWidget()
        right.setObjectName("Preview")
        rv = QVBoxLayout(right)
        rv.setContentsMargins(0, 0, 0, 0)
        rv.setSpacing(0)

        bar = QWidget()
        bar.setObjectName("PreviewToolbar")
        bl = QHBoxLayout(bar)
        bl.setContentsMargins(18, 10, 18, 10)
        bl.setSpacing(12)

        # Stage stepper — replaces the "Preview stage:" combo as the visible
        # control. The combo itself stays (hidden) because it is the value
        # every 1.x call site reads and writes.
        self.preview_stage_combo = QComboBox()
        self.preview_stage_combo.addItems(STAGES)
        self.preview_stage_combo.setVisible(False)
        self.preview_stage_combo.currentIndexChanged.connect(
            self._on_preview_stage_changed)

        stepper = QWidget()
        sl = QHBoxLayout(stepper)
        sl.setContentsMargins(0, 0, 0, 0)
        sl.setSpacing(0)
        self.prev_stage_btn = QPushButton("\u25c0")
        self.prev_stage_btn.setObjectName("ABBtn")
        self.prev_stage_btn.clicked.connect(lambda: self._step_stage(-1))
        self.stage_step_label = QLabel("01 PREPROCESS")
        self.stage_step_label.setObjectName("GroupHead")
        self.stage_step_label.setContentsMargins(12, 0, 12, 0)
        self.next_stage_btn = QPushButton("\u25b6")
        self.next_stage_btn.setObjectName("ABBtn")
        self.next_stage_btn.clicked.connect(lambda: self._step_stage(1))
        sl.addWidget(self.prev_stage_btn)
        sl.addWidget(self.stage_step_label)
        sl.addWidget(self.next_stage_btn)
        bl.addWidget(stepper)

        self.btn_before = QPushButton("Before")
        self.btn_split = QPushButton("Split")
        self.btn_after = QPushButton("After")
        for b, m in ((self.btn_before, "before"), (self.btn_split, "split"),
                     (self.btn_after, "after")):
            b.setObjectName("ABBtn")
            b.setCheckable(True)
            b.clicked.connect(lambda _, mode=m: self._set_compare_mode(mode))
            bl.addWidget(b)
        self.btn_split.setChecked(True)

        bl.addStretch(1)
        for text, tip, fn in (
                ("\u2212", "Zoom out", lambda: self.compare.zoom_by(0.8)),
                ("+", "Zoom in", lambda: self.compare.zoom_by(1.25)),
                ("Fit", "Reset zoom & position (or double-click the image)",
                 lambda: self.compare.reset_view())):
            b = QPushButton(text)
            b.setObjectName("ABBtn")
            b.setToolTip(tip)
            b.clicked.connect(fn)
            bl.addWidget(b)

        self.chk_display_stretch = QCheckBox("Auto-stretch")
        self.chk_display_stretch.setChecked(True)
        self.chk_display_stretch.setToolTip(
            "Applies a display-only screen stretch so linear images are "
            "visible.\nDoes not modify your data.")
        bl.addWidget(self.chk_display_stretch)
        rv.addWidget(bar)

        self.compare = CompareView()
        self.compare.selectionMade.connect(self._on_crop_selection)
        self.compare.pointPicked.connect(self._on_ann_point_picked)
        frame = QFrame()
        frame.setObjectName("ImageFrame")
        fl = QVBoxLayout(frame)
        fl.setContentsMargins(1, 1, 1, 1)
        fl.addWidget(self.compare)
        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(16, 16, 16, 10)
        wl.addWidget(frame)
        rv.addWidget(wrap, 1)

        self.preview_hint = QLabel(
            "Drag the divider to compare \u00b7 drag to move \u00b7 scroll to "
            "zoom \u00b7 double-click to fit \u00b7 preview is downscaled, "
            "full resolution stays in Siril")
        self.preview_hint.setObjectName("Caption")
        self.preview_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_hint.setContentsMargins(18, 0, 18, 14)
        rv.addWidget(self.preview_hint)
        return right

    # --------------------------------------------------------- stage pages
    def _stage_box(self, number, title, enabled_check=True,
                   start_expanded=None):
        """v2 replacement. Same signature and same return value —
        (checkable QGroupBox, content layout) — so every stage mixin works
        unchanged. The difference is where the box goes: one page of the
        pane's stack instead of one card in a long scrolling column, with
        the enable checkbox promoted to the pane header.

        `start_expanded` is accepted and ignored: only one stage is on
        screen at a time, so there is nothing to expand or collapse.
        """
        idx = number - 1

        page = QWidget()
        pl = QVBoxLayout(page)
        pl.setContentsMargins(0, 0, 0, 0)
        pl.setSpacing(0)

        header = PaneHeader(number, title)
        header.set_description(STAGE_BLURBS.get(idx, ""))
        header.useSirilRequested.connect(
            lambda _=False, i=idx, t=title:
            self._load_siril_current_into_stage(i, t))
        pl.addWidget(header)
        pl.addWidget(hairline())

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        hl = QVBoxLayout(holder)
        hl.setContentsMargins(20, 16, 20, 20)
        hl.setSpacing(16)

        box = QGroupBox()
        box.setObjectName("StagePanel")
        box.setCheckable(True)
        outer = QVBoxLayout(box)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        content = QWidget()
        content.setObjectName("StageContent")
        v = QVBoxLayout(content)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(14)
        outer.addWidget(content)

        hl.addWidget(box)
        hl.addStretch(1)
        scroll.setWidget(holder)
        pl.addWidget(scroll, 1)

        # Header tick <-> logical box, both ways, without a signal loop.
        def on_header(checked):
            if box.isChecked() != checked:
                box.setChecked(checked)

        def on_box(checked):
            content.setEnabled(checked)
            if header.enable.isChecked() != checked:
                header.enable.setChecked(checked)
            self._refresh_rail_states()

        header.enable.setChecked(enabled_check)
        box.setChecked(enabled_check)
        content.setEnabled(enabled_check)
        header.enabledToggled.connect(on_header)
        box.toggled.connect(on_box)

        # Kept so on_expand_all_stages / on_collapse_all_stages still work.
        dummy = QPushButton(page)
        dummy.setCheckable(True)
        dummy.setVisible(False)
        self._stage_toggle_pairs.append((box, dummy))

        self.stage_pages[idx] = page
        self.stage_headers[idx] = header
        self.stage_stack.insertWidget(idx, page)
        return box, v

    def _advanced_section(self, title="ADVANCED", note=""):
        """Where a stage's non-essential controls go. Two or three controls
        stay visible in the pane; everything else lives in here.

        Returns (widget, layout) — add the widget to the stage's own layout,
        put controls in the layout.
        """
        sec = AdvancedSection(title, note)
        return sec, sec.content

    # ------------------------------------------------------------ selection
    def _select_stage(self, idx):
        if not (0 <= idx < len(STAGES)):
            return
        self.stage_stack.setCurrentIndex(idx)
        self.rail.set_current(idx)
        self.stage_step_label.setText(
            f"{idx + 1:02d} {STAGES[idx].split('. ', 1)[-1].upper()}")
        self.prev_stage_btn.setEnabled(idx > 0)
        self.next_stage_btn.setEnabled(idx < len(STAGES) - 1)
        if self.preview_stage_combo.currentIndex() != idx:
            self._syncing_stage = True
            self.preview_stage_combo.setCurrentIndex(idx)
            self._syncing_stage = False
        self._refresh_rail_states()

    def _step_stage(self, delta):
        self._select_stage(self.stage_stack.currentIndex() + delta)

    def _on_preview_stage_changed(self, idx):
        # 1.x behaviour: changing the previewed stage refreshes the image.
        self._refresh_preview()
        if not self._syncing_stage:
            self._select_stage(idx)

    def _refresh_rail_states(self):
        """The rail is the progress display. 'done' = a snapshot exists."""
        snaps = getattr(self, "snapshots", {}) or {}
        current = self.stage_stack.currentIndex()
        done = 0
        for idx in range(len(STAGES)):
            box, _ = self._stage_toggle_pairs[idx] \
                if idx < len(self._stage_toggle_pairs) else (None, None)
            enabled = box.isChecked() if box is not None else False
            if idx in snaps:
                self.rail.set_state(idx, "done")
                done += 1
            elif not enabled:
                self.rail.set_state(idx, "off")
            elif idx == current:
                self.rail.set_state(idx, "queued", "")
            else:
                self.rail.set_state(idx, "queued")
        self.ribbon.set_progress_text(done, len(STAGES))

    def set_stage_running(self, idx, frac=0.0):
        """Call from the progress callback to light up the running row."""
        self.rail.set_state(idx, "running")
        self.rail.set_progress(idx, frac)
        self.ribbon.set_running(True)

    # ---------------------------------------------------------- responsive
    def resizeEvent(self, event):
        super().resizeEvent(event)
        compact = self.width() < COMPACT_WIDTH
        if compact != self._compact:
            self._compact = compact
            self.rail.set_compact(compact)
            self.ribbon.set_compact(compact)
            self.preview_hint.setVisible(not compact)
