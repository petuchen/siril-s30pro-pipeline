"""
Unified AstroPipeline — Smart Telescope One-Click Processing Suite
==================================================================
A single Siril python script that chains four processing stages with a
modern UI and per-stage before/after preview:

    1. Preprocess   — Smart telescope stacking (based on Naztronomy
                      Smart Telescope Preprocessing by Nazmus Nasir)
    2. Remove BG    — GraXpert AI background extraction (based on the
                      GraXpert AI script by Adrian Knagg-Baugh,
                      models (c) GraXpert Development Team)
    3. Denoise      — GraXpert AI denoising (same origin as above)
    4. Stretch      — VeraLux HyperMetric Stretch (based on VeraLux by
                      Riccardo Paterniti)

CHANGELOG (recent — see CHANGELOG.md / S30Pro_Pipeline_README.html for
full history)
------------------------------------------------------------------------
* 2.0.0 — Rebuilt window: the 13 stages become a permanent left rail
  (grouped Stack / Clean / Stretch / Finish) that doubles as the progress
  display, and the settings panel shows one stage at a time instead of
  thirteen stacked cards. Each stage keeps two or three controls visible
  with the rest behind an ADVANCED disclosure. Image info and run progress
  move to a session ribbon across the top; the four bottom buttons collapse
  to one primary (Run Full Pipeline), one secondary (Save image) and an
  overflow menu; settings JSON import/export gets a permanent home in the
  rail footer. "Use Siril's image" moves to the top of each stage as a
  "Starting from" row. Expand All / Collapse All are gone — with one stage
  on screen there is nothing to expand; their enable/disable job is in the
  overflow menu. New dark theme: square corners, hairline borders, one
  steel accent. Window adapts below 1180px (rail collapses to numbers,
  ribbon detail behind a disclosure); minimum 960x640.
* 1.29.5 — Two "Combine with existing master" improvements:
  1) Total integration time is now the *sum* of this run's own subs and
  the existing master's, not just whatever Siril's `stack` naturally
  wrote for a 2-frame combine (STACKCNT=2, one inherited EXPTIME). New
  `_read_integration_seconds` helper reads each side's true LIVETIME
  (else STACKCNT x EXPTIME), and the sum is patched into the combined
  result's header before it's loaded, so the image-info panel and the
  saved filename both reflect real totals.
  2) The auto-saved output filename now gets a "_combined" suffix
  instead of "_stacked" when combine ran, so a merged result is
  identifiable from the filename alone — same pre-built-name convention
  the other stages' save actions already use (e.g. Annotate/Watermark's
  export dialogs pre-fill a descriptive default name).
* 1.29.4 — 1.29.3's `set32bits` + Siril `load`/`save` round trip didn't
  actually fix the "input images have different precision" crash — the
  same error persisted (`Command 'stack' failed: Generic error`, log
  showing both files read back as "32 bits" even though one was still
  a different underlying pixel format). Replaced that approach with a
  direct, reliable fix: both copies are now rewritten in Python (new
  `_ensure_float32_fits` helper, using astropy) to genuine normalized
  32-bit float — matching Siril's own on-disk float convention and
  reusing the same integer-ADU-to-[0,1] scaling (`VeraLuxCore.
  normalize_input`) already used elsewhere in this script for reading
  raw/master FITS files — before Siril's `convert`/`stack` ever see
  them, instead of hoping a Siril command round trip would do it.
* 1.29.3 — Fixed another follow-on crash in "Combine with existing
  master": `Stacking error: input images have different precision` /
  "Opening image 1 failed". Siril's `convert` command only symlinks or
  copies FITS files as-is — it does not re-encode them, so it never
  unified precision (bit depth) between this run's own 32-bit float
  stack and an existing master saved at a different bit depth (e.g.
  16-bit integer), which `stack` then refuses to combine. Now forces
  `set32bits` and re-saves both frames (via `load`/`save`) before
  converting/registering/stacking, so both inputs are guaranteed to be
  32-bit float going in.
* 1.29.2 — Fixed the follow-on crash after 1.29.1's registration
  fallback: `stack failed: Argument error` / "Unexpected argument to
  stacking `-weight_from_nbstack', aborting." The combine-master stack
  call used `-weight_from_nbstack`, a flag syntax this Siril build
  doesn't accept — every other weighted stack call in this script
  (Preprocess's own weighting option) uses `-weight=<mode>` instead, and
  that's the syntax this Siril install actually recognizes. Switched the
  combine step to match: `-weight=nbstack`.
* 1.29.1 — Fixed "Combine with existing master" crashing with
  `seqapplyreg failed: Generic error` ("Existing registration data is a
  set of identity matrices... aborting") when Siril's star-pattern
  registration couldn't find enough common stars between two
  independently-processed full masters. Now prefers plate-solve
  registration (WCS-based, robust to processing differences) when local
  Gaia astrometry is available, falls back to plain star registration,
  and if both fail, stacks without re-aligning instead of crashing —
  with a clear log warning either way so you know to check the result
  for misalignment.
* 1.29.0 — Preprocess: added "Combine with an existing master" — for
  when you have an already-stacked FITS from an earlier session but the
  raw subs weren't kept. Pick that file, and after this run's own
  lights are stacked, the pipeline registers it against the file you
  chose and combines the two with Siril's -weight_from_nbstack (each
  session weighted by its STACKCNT header, not averaged 50/50), with an
  optional sub-count override for masters missing that header. Your
  original file is never modified. Also added a reusable
  `_collapsible_section` helper (same collapsed-by-default pattern as
  1.28.1's GIMP polish block) for this new section.
* 1.28.2 — Fixed a Qt startup warning ("Populating font family aliases
  took ... ms. Replace uses of missing font family 'Segoe UI' with one
  that exists") on platforms without those named fonts installed (e.g.
  Linux). The global stylesheet named 'Segoe UI'/'SF Pro Text'/
  'Helvetica Neue' explicitly, which are Windows/macOS-only fonts —
  Qt would try to resolve each one via a one-time alias-population pass
  before falling back. Switched to the generic `sans-serif` CSS family,
  which Qt resolves directly to the platform's default UI font with no
  alias lookup. Purely cosmetic/startup-time — no behavior change.
* 1.28.1 — Hubble Palette's "GIMP replacement polish" block is now
  collapsed by default (click to expand) and dropped the "Ports the
  manual GIMP finishing pass..." lead-in sentence from its description.
  Also a small UI consistency pass: every "Reset" button across Stretch/
  Histogram/Final Touch/Hubble Palette now uses the same "↺  Reset"
  label, and every slider's numeric readout (Final Touch, Stretch,
  NebulaChrome, GIMP polish, ...) now shares one consistent minimum
  width instead of each stage picking its own.
* 1.28.0 — Hubble Palette: added an optional "GIMP replacement polish"
  block (saturation, shadows, highlights, contrast, sharpen, denoise —
  all independently tunable, off by default) that ports the manual GIMP
  finishing pass from the Rosette Nebula tutorial workflow into one
  repeatable step, based on the standalone gimp_replacement.py
  prototype (HSV saturation, shadow/highlight tone-curve nudges,
  midpoint contrast, unsharp-mask sharpen, bilateral noise reduction).
  Runs after the recolor (channel-mix or NebulaChrome), whichever mode
  is selected.
* 1.27.0 — Annotate: markers for Messier/NGC/IC/Sharpless/LdN objects are
  now sized to their real apparent diameter (OpenNGC's MajAx / VizieR's
  Diam / Area, converted via the plate-solve's pixel scale) instead of a
  fixed generic circle. Also replaced the fixed offset-from-marker label
  placement with a greedy layout pass that tries a ring of candidate
  positions per label, avoids overlapping already-placed labels, and
  guarantees every label stays fully inside the image (no more text
  overlap in crowded fields or labels clipped at the frame edge).
* 1.26.0 — Brought the Annotate stage back, rebuilt on structured data
  instead of catsearch's log-scraping: Messier/NGC/IC from OpenNGC
  (downloaded once, cached on disk), Sharpless/LdN from live VizieR cone
  searches, stars unchanged (Siril's own conesearch). Each catalogue has
  its own on/off checkbox and preview color. Added "Select objects to
  show..." (live preview updates as you check/uncheck), Undo, and
  "Save annotated image...". Stage renumbered back to 11 (Watermark is
  12 again).
* 1.25.0 — Removed the Annotate stage entirely (UI card, catsearch/
  conesearch helpers, DSO_NAMES/BRIGHT_STARS lists, the "Open Siril's
  Annotate tool" button, and its settings JSON keys). Despite several
  rounds of fixes, resolving Siril's bundled Messier/NGC/IC/Sharpless/LdN
  catalogues from a script never became reliable enough — Siril's own
  Annotate tool (Tools -> Astrometry -> Annotate... in Siril itself)
  remains the recommended way to label deep-sky objects. Remaining
  stages renumbered (Watermark is now stage 11).
* 1.24.1 — Annotate: fixed a bug where the catsearch-based DSO lookup
  (added in 1.23.1) reported zero results for every object, always. The
  RA/Dec parser only accepted whitespace between the RA and Dec halves,
  but Siril's real wording uses a comma ("17h01m12.87s, -30°06'44.70\""),
  so it silently failed to match every single line.
* 1.24.0 — Watermark: added a free-text "Author" credit field. Moved the
  detailed version history out of this docstring into CHANGELOG.md and
  the HTML docs, to keep this file more skimmable.
* 1.23.2 — Annotate: added an "Open Siril's Annotate tool..." button
  (opens Siril's own native catalogue browser as a manual companion).
* 1.23.1 — Annotate: redesigned deep-sky-object lookup to use Siril's own
  `catsearch` command (Messier/NGC/IC) instead of PGC/SIMBAD cone-search
  or a hardcoded coordinate table.
* 1.22.x — Annotate: SIMBAD named-DSO fix; preview orientation now
  matches Siril's own display. Watermark: "Remove all" button, two-column
  layout option.
* 1.21.x — New Watermark stage (info block with position/opacity
  controls). Crop-box preview scale fix.
* 1.20.0 and earlier — see CHANGELOG.md for the complete history back to
  1.14.0 (Final Touch Shadows/Highlights, Richardson-Lucy deconvolution,
  and the original 4-stage pipeline).

SPDX-License-Identifier: GPL-3.0-or-later
This combined work retains the GPL-3.0-or-later license of all three
source scripts. Full credit goes to the original authors:
  * Nazmus Nasir            https://www.naztronomy.com
  * Adrian Knagg-Baugh      (GraXpert AI Siril interface)
  * GraXpert Team           https://graxpert.com  (AI models, CC-BY-NC-SA-4.0)
  * Riccardo Paterniti      info@veralux.space

Requirements
------------
* Siril 1.4+ with sirilpy >= 0.8.6
* A 'lights' folder inside the Siril working directory (darks/flats/
  biases folders optional)
* GraXpert AI models already downloaded (bge-ai-models /
  denoise-ai-models in the GraXpert user data directory). Run GraXpert
  once, or use the original GraXpert-AI script's Model Manager, to
  download them.

VERSION 1.0.0
"""

import os
import sys
import csv
import math
import time
import copy
import json
import random
import shutil
import hashlib
import tempfile
import threading
import concurrent.futures
import urllib.request
import urllib.parse
from datetime import datetime

import sirilpy as s
from sirilpy import LogColor

if not s.check_module_version(">=0.8.6"):
    print("Error: requires sirilpy module >= 0.8.6")
    sys.exit(1)

# ONNX runtime (GraXpert AI stages)
onnx_helper = s.ONNXHelper()
onnx_helper.install_onnxruntime()

import onnxruntime
if hasattr(onnxruntime, "preload_dlls"):
    with s.SuppressedStderr(), s.SuppressedStdout():
        onnxruntime.preload_dlls()
onnxruntime.set_default_logger_severity(4)

s.ensure_installed("PyQt6", "numpy", "astropy", "opencv-python", "appdirs",
                    "scikit-image")

import numpy as np
import cv2
from astropy.io import fits
from appdirs import user_data_dir
from skimage.restoration import richardson_lucy as _skimage_richardson_lucy

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QCheckBox, QDoubleSpinBox, QSpinBox, QComboBox,
    QGroupBox, QMessageBox, QFileDialog, QSlider, QProgressBar, QFrame,
    QScrollArea, QSplitter, QSizePolicy, QStackedWidget, QLineEdit,
    QDialog, QListWidget, QListWidgetItem, QDialogButtonBox, QColorDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize, QRectF, QTimer
from PyQt6.QtGui import (QFont, QImage, QPixmap, QPainter, QColor, QPen,
                         QPainterPath, QPolygonF, QShortcut, QKeySequence)
from PyQt6.QtCore import QPointF

APP_NAME = "S30 Pro Pipeline"
VERSION = "2.1.2"

# Shared UI sizing constant: the small numeric/percent readout next to every
# slider in the app (Final Touch, Stretch, Hubble Palette/NebulaChrome, GIMP
# replacement polish, ...) uses this same minimum width so the value column
# lines up consistently across stages instead of each stage picking its own
# width (34px vs 38px, etc.) — a font-size/spacing consistency fix.
SLIDER_VALUE_LABEL_WIDTH = 40


# ---- local package (Phase 1 module split, see s30pro_pipeline/) -----------
# Explicit imports (not `import *`) so static tools like pyflakes can still
# catch real typos/undefined names in the code below, the same as before
# the split.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s30pro_pipeline.theme import STYLESHEET
from s30pro_pipeline.constants import (
    TELESCOPES, FILTER_OPTIONS_MAP, FILTER_COMMANDS_MAP,
    SPCC_SENSOR_MAP, TELESCOPE_HEADER_MAP, SENSOR_PROFILES,
    luminance, TELESCOPE_TO_PROFILE, STAGES, REC709_WEIGHTS,
    IDX_CROP, IDX_SCNR, IDX_AGR, IDX_BGE, IDX_STARS, IDX_DEN, IDX_PAL,
    IDX_STR, IDX_HIST, IDX_TOUCH, IDX_ANN, IDX_WM, WATERMARK_POSITIONS,
    PALETTE_PRESETS, PALETTE_TO_PROFILE,
)
from s30pro_pipeline.bortle import sqm_to_bortle, ZP_REF_50MM, BORTLE_NAMES
from s30pro_pipeline import graxpert_helpers
from s30pro_pipeline.graxpert_helpers import (
    get_available_local_models, richardson_lucy_sharpen, _make_gaussian_psf,
    graxpert_extract_background, graxpert_apply_correction, graxpert_denoise,
)
from s30pro_pipeline.agr_math import agr_correct_image
from s30pro_pipeline.veralux_stretch import VeraLuxCore, veralux_stretch
from s30pro_pipeline.image_utils import (
    to_hwc_float, display_autostretch, make_qimage,
)
from s30pro_pipeline.ui_widgets import (
    CompareView, HistogramEditor, Worker, PreviewFetchWorker,
)
from s30pro_pipeline.catalog_data import (
    BRIGHT_STARS, OPENNGC_URL, ANNOTATE_MAX_PER_CATALOG,
    CATALOG_COLORS, CATALOG_LABELS, _ang_sep, _sexa_to_deg, _http_get,
    _vizier_cone, _clean_ngc_ic_name, _parse_vizier_tsv,
)
from s30pro_pipeline.constellation_data import (
    CONSTELLATION_NAMES, CONSTELLATION_COLOR_PRESETS,
    _load_constellation_lines, _filter_constellation_lines, _inset_segment,
)
from s30pro_pipeline.stages.stage_scnr import ScnrMixin
from s30pro_pipeline.stages.stage_crop import CropMixin
from s30pro_pipeline.stages.stage_agr import AgrMixin
from s30pro_pipeline.stages.stage_watermark import WatermarkMixin
from s30pro_pipeline.stages.stage_touch import TouchMixin
from s30pro_pipeline.stages.stage_hist import HistMixin
from s30pro_pipeline.stages.stage_bge import BgeMixin
from s30pro_pipeline.stages.stage_denoise import DenoiseMixin
from s30pro_pipeline.stages.stage_stars import StarsMixin
from s30pro_pipeline.stages.stage_palette import PaletteMixin
from s30pro_pipeline.stages.stage_stretch import StretchMixin
from s30pro_pipeline.stages.stage_annotate import AnnotateMixin
from s30pro_pipeline.stages.stage1_preprocess import Stage1Mixin
from s30pro_pipeline.ui_v2 import UiV2Mixin

class UnifiedPipelineWindow(UiV2Mixin, Stage1Mixin, AnnotateMixin, StretchMixin, PaletteMixin, StarsMixin, BgeMixin, DenoiseMixin, HistMixin, TouchMixin, WatermarkMixin, AgrMixin, CropMixin, ScnrMixin, QMainWindow):

    snapshot_ready = pyqtSignal(int)
    log_d_solved = pyqtSignal(float)
    palette_cache_updated = pyqtSignal(str)
    # Comet Stack mode's two GUI-only steps (comet registration, Star
    # Recomposition — see stage1_preprocess.py) have to pause execution
    # mid-stage and show instructions in a modal dialog, but _exec_stage1
    # runs on the worker QThread where QDialog can't be shown directly.
    # Same cross-thread pattern as snapshot_ready/_on_snapshot_ready:
    # emitting this from the worker thread queues _on_guided_pause_requested
    # to run on the GUI thread; _guided_pause() (called from the worker)
    # blocks on a threading.Event until that slot sets it.
    guided_pause_requested = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} v{VERSION}")
        self.setStyleSheet(STYLESHEET)
        self.resize(1440, 900)

        self.siril = s.SirilInterface()
        self.initialization_successful = False
        try:
            self.siril.connect()
            self.siril.log(f"{APP_NAME} v{VERSION} connected to Siril", LogColor.GREEN)
        except s.SirilConnectionError:
            print("Failed to connect to Siril")
            return
        try:
            self.siril.cmd("requires", "1.3.6")
        except s.CommandError:
            return

        self.fits_extension = self.siril.get_siril_config("core", "extension")
        self.cwd = self.siril.get_siril_wd()

        # Gaia catalog availability (astrometry: plate solving / photometry: SPCC)
        self.gaia_available = False
        try:
            g = self.siril.get_siril_config("core", "catalogue_gaia_astro")
            if g and g != "(not set)" and os.path.isfile(g):
                self.gaia_available = True
        except s.CommandError:
            pass
        self.gaia_photo_available = False
        try:
            g = self.siril.get_siril_config("core", "catalogue_gaia_photo")
            if g and g != "(not set)" and os.path.isdir(g):
                self.gaia_photo_available = True
        except s.CommandError:
            pass

        # snapshots: stage index -> dict(before_qimg, after_qimg)
        self.snapshots = {}
        # full-resolution backups for the Undo buttons (stage idx -> ndarray)
        self.stage_backups = {}
        self.snapshots_raw_after = {}
        self.undo_buttons = {}
        self.worker = None
        # Background fetch for _refresh_preview()'s "no snapshot yet, show
        # Siril's current image" path — see _refresh_preview for why this
        # needs to be threaded rather than a plain synchronous call.
        self._preview_worker = None
        self._preview_pending = False
        # A "Run this stage"/"Run all" click that arrived while the above
        # preview fetch was in flight — see _launch()'s guard.
        self._pending_launch = None
        # Elapsed-time readout next to the progress bar: a real-time ticking
        # clock rather than something only updated when a progress() call
        # happens to fire, since some stages go a long stretch between
        # progress updates.
        self._run_start_time = None
        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)
        self._elapsed_timer.timeout.connect(self._update_elapsed_label)

        # Scratch folder for expensive intermediate results (currently the
        # StarNet star/starless split used by the Hubble Palette stage) so
        # switching palette presets or weights doesn't re-run StarNet every
        # time. Wiped when the window closes, never left behind.
        self._temp_dir = tempfile.mkdtemp(prefix="s30pro_pipeline_")
        self.palette_star_cache = {"fingerprint": None, "starless_path": None,
                                   "stars_path": None}
        self.held_stars = None  # star layer held back by the palette stage
                                 # (Hold-stars-until-stretch option) for the
                                 # Stretch stage to recombine after its own pass
        self._last_run_stage_idx = None  # for the Ctrl+Z "undo last stage" shortcut
        self._subsky_boxes = None  # user-edited background sample boxes
                                    # [(x, y, size), ...] in image pixel
                                    # coords, set via "Preview & edit
                                    # sample boxes..." — None means use
                                    # Siril's own automatic placement
        self.chosen_telescope = "ZWO Seestar S50"
        # Bortle scale estimate (Option C: derived from the raw lights
        # themselves) — populated once stage 1 runs, persists in the info
        # panel afterwards regardless of which stage's image is displayed.
        self.estimated_bortle = None
        # (min_date, max_date) strings scanned from the lights' DATE-OBS
        # headers during stage 1 — lets the info bar show a date *range*
        # when the subs span several nights.
        self.date_range = None
        self.snapshot_ready.connect(self._on_snapshot_ready)
        self.log_d_solved.connect(self._on_log_d_solved)
        self.guided_pause_requested.connect(self._on_guided_pause_requested)

        self._resolve_working_dir()
        self._build_ui()
        self.palette_cache_updated.connect(self.stars_cache_label.setText)
        self._detect_telescope()

        # debounce timers for the live previews
        self.hist_proxy = None
        self._hist_timer = QTimer(self)
        self._hist_timer.setSingleShot(True)
        self._hist_timer.timeout.connect(self._update_hist_live)
        self.touch_proxy = None
        self._touch_timer = QTimer(self)
        self._touch_timer.setSingleShot(True)
        self._touch_timer.timeout.connect(self._update_touch_live)

        self._update_image_info()
        self._setup_shortcuts()
        self.setAcceptDrops(True)
        self.initialization_successful = True

    def _setup_shortcuts(self):
        """Keyboard shortcuts: Ctrl+S save, Ctrl+Z undo last-run stage,
        Ctrl+Return run the whole pipeline."""
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self.on_save_file)
        QShortcut(QKeySequence("Ctrl+Return"), self, activated=self.on_run_all)
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.on_run_all)
        QShortcut(QKeySequence("Ctrl+Z"), self, activated=self._undo_last_run_stage)

    def _undo_last_run_stage(self):
        idx = getattr(self, "_last_run_stage_idx", None)
        if idx is None:
            return
        self._undo_stage(idx)

    # ------------------------------------------------------------------ setup

    def _resolve_working_dir(self):
        """Ensure cwd contains a lights/ dir (same logic as Naztronomy, simplified)."""
        if os.path.isdir(os.path.join(self.cwd, "lights")):
            self.siril.cmd("cd", f'"{self.cwd}"')
            os.chdir(self.cwd)
            return
        selected = QFileDialog.getExistingDirectory(
            self, "Select the folder that contains the 'lights' directory", self.cwd,
            QFileDialog.Option.ShowDirsOnly)
        if selected:
            self._set_working_dir(selected)

    def _set_working_dir(self, path):
        """Point Siril + this window's cwd at `path`, if it looks usable.
        Shared by the folder-picker dialog (_resolve_working_dir) and drag
        and drop (dropEvent) so both go through the same validation."""
        if not os.path.isdir(path):
            return
        if os.path.isdir(os.path.join(path, "lights")):
            self.siril.cmd("cd", f'"{path}"')
            os.chdir(path)
            self.cwd = path
            self._detect_telescope()
        else:
            QMessageBox.warning(self, "No lights folder",
                                "The selected folder has no 'lights' subfolder. "
                                "Stage 1 (Preprocess) will not run, but stages 2-4 "
                                "can still be applied to the currently loaded image.")

    def dragEnterEvent(self, event):
        urls = event.mimeData().urls()
        if urls and os.path.isdir(urls[0].toLocalFile()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if not urls:
            event.ignore()
            return
        path = urls[0].toLocalFile()
        if os.path.isdir(path):
            self._set_working_dir(path)
            event.acceptProposedAction()
        else:
            event.ignore()

    def _detect_telescope(self):
        try:
            lights = os.path.join(self.cwd, "lights")
            if not os.path.isdir(lights):
                return
            files = [f for f in os.listdir(lights) if f.lower().endswith(
                (".fits", ".fit", ".fits.fz", ".fit.fz"))]
            self.lights_count = len(files)
            self.files_label.setText(f"{self.lights_count} light frames found")
            if not files:
                return
            with fits.open(os.path.join(lights, files[0])) as hdul:
                hdr = hdul[0].header
                vals = [v for v in [hdr.get("TELESCOP", ""), hdr.get("CREATOR", ""),
                                    hdr.get("CAMERA", "")] if v]
                for key, ui in TELESCOPE_HEADER_MAP.items():
                    if any(v.startswith(key) for v in vals):
                        self.telescope_combo.setCurrentText(ui)
                        break
        except Exception as e:
            self.siril.log(f"Telescope autodetect failed: {e}", LogColor.SALMON)

    # --------------------------------------------------------------------- UI

    def _collapsible_section(self, title, start_expanded=False):
        """A titled, collapsible sub-section (arrow header + hideable
        content pane) for optional/advanced controls inside a stage card
        — same pattern as the Hubble Palette stage's "GIMP replacement
        polish" block. Returns (box, content_layout, toggle_btn); the
        caller adds widgets to content_layout and wires up anything else
        (e.g. an enable/disable checkbox) itself."""
        box = QGroupBox()
        bv = QVBoxLayout(box)
        bv.setContentsMargins(10, 6, 10, 10)
        bv.setSpacing(8)

        toggle_btn = QPushButton(("▾  " if start_expanded else "▸  ") + title)
        toggle_btn.setObjectName("CollapseHeader")
        toggle_btn.setCheckable(True)
        toggle_btn.setChecked(start_expanded)
        bv.addWidget(toggle_btn)

        content = QWidget()
        content.setVisible(start_expanded)
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 2, 0, 0)
        cv.setSpacing(8)
        bv.addWidget(content)

        def _on_toggle(checked):
            content.setVisible(checked)
            toggle_btn.setText(("▾  " if checked else "▸  ") + title)
        toggle_btn.toggled.connect(_on_toggle)

        return box, cv, toggle_btn

    def _run_row(self, slot, undo_stage=None):
        """Bottom row of a stage card: optional Undo + Run buttons."""
        row = QHBoxLayout()
        row.addStretch()
        if undo_stage is not None:
            undo_btn = QPushButton("↩  Undo")
            undo_btn.setToolTip("Restore the image as it was before this stage ran")
            undo_btn.setEnabled(False)
            undo_btn.clicked.connect(lambda: self._undo_stage(undo_stage))
            self.undo_buttons[undo_stage] = undo_btn
            row.addWidget(undo_btn)
        btn = QPushButton("Run this stage")
        btn.setObjectName("StageRun")
        btn.clicked.connect(slot)
        row.addWidget(btn)
        return row, btn

    def _slider_spin_row(self, label, minv, maxv, step, value, decimals, tooltip=""):
        """A labelled row with a slider and an editable QDoubleSpinBox kept
        in sync — the slider is a convenient drag handle, the box holds
        the exact value and can also be typed into directly. Returns
        (row layout, spin box)."""
        row = QHBoxLayout()
        row.addWidget(QLabel(label))

        box = QDoubleSpinBox()
        box.setRange(minv, maxv)
        box.setSingleStep(step)
        box.setDecimals(decimals)
        box.setValue(value)
        box.setMinimumWidth(80)
        if tooltip:
            box.setToolTip(tooltip)

        slider = QSlider(Qt.Orientation.Horizontal)
        steps = max(1, int(round((maxv - minv) / step)))
        slider.setRange(0, steps)
        slider.setValue(int(round((value - minv) / step)))
        if tooltip:
            slider.setToolTip(tooltip)

        def from_slider(pos):
            box.blockSignals(True)
            box.setValue(minv + pos * step)
            box.blockSignals(False)

        def from_box(val):
            slider.blockSignals(True)
            slider.setValue(int(round((val - minv) / step)))
            slider.blockSignals(False)

        slider.valueChanged.connect(from_slider)
        box.valueChanged.connect(from_box)
        row.addWidget(slider, 1)
        row.addWidget(box)
        return row, box

    # ------------------------------------------------------------- ui helpers

    def _on_telescope_changed(self, scope):
        self.chosen_telescope = scope
        self.filter_combo.clear()
        self.filter_combo.addItems(FILTER_OPTIONS_MAP.get(scope, []))
        if scope == "Celestron Origin":
            self.spcc_checkbox.setChecked(False)
            self.spcc_checkbox.setEnabled(False)
        else:
            self.spcc_checkbox.setEnabled(True)
        prof = TELESCOPE_TO_PROFILE.get(scope)
        if prof and prof in SENSOR_PROFILES:
            self.profile_combo.setCurrentText(prof)

    def _set_compare_mode(self, mode):
        for b, m in ((self.btn_before, "before"), (self.btn_split, "split"),
                     (self.btn_after, "after")):
            b.setChecked(m == mode)
        self.compare.set_mode(mode)

    def _refresh_preview(self):
        idx = self.preview_stage_combo.currentIndex()
        snap = self.snapshots.get(idx)
        if snap:
            self.compare.set_images(snap.get("before"), snap.get("after"))
            return
        # No snapshot yet for this stage (it hasn't been run this
        # session) — rather than leaving the preview blank, show
        # whatever's currently loaded in Siril, which is what this
        # stage will actually start from once run. This is the same
        # image _load_siril_current_into_stage() fetches on demand for
        # the "Use Siril's image" button; doing it automatically here
        # means moving to the next stage always shows the image it
        # would process, without an extra click.
        #
        # Fetching + stretching that image is real work (a second or
        # more on a typical smart-telescope stack), and this method
        # fires on every stage-navigation click for any stage that
        # hasn't run yet — so it's threaded via PreviewFetchWorker
        # rather than done inline, to avoid freezing the whole window on
        # every such click. Only one fetch runs at a time: if a click
        # arrives while one is already in flight, it's recorded as
        # `_preview_pending` and re-evaluated (from scratch, via this
        # same method — a snapshot may exist by then, or the user may
        # have moved on to yet another stage) once the in-flight one
        # finishes, instead of starting a second overlapping Siril call.
        if self._preview_worker is not None and self._preview_worker.isRunning():
            self._preview_pending = True
            return
        # Also hold off while a stage is actually executing (self.worker):
        # both that thread and this one would call Siril's API concurrently
        # otherwise. Stage navigation itself isn't blocked during a run
        # (_set_running() only disables the per-stage Run buttons, not the
        # rail), so this can genuinely happen. Re-checked from _on_succeeded/
        # _on_failed once the run finishes, same as the in-flight case above.
        if self.worker is not None and self.worker.isRunning():
            self._preview_pending = True
            return
        self._preview_pending = False

        stretch_on = self.chk_display_stretch.isChecked()

        def fetch():
            arr = self._get_current_image()  # may raise RuntimeError
            hwc = to_hwc_float(arr)
            if stretch_on:
                hwc = display_autostretch(hwc)
            return make_qimage(hwc)

        worker = PreviewFetchWorker(fetch)
        worker.succeeded.connect(self._on_preview_fetch_succeeded)
        worker.empty.connect(self._on_preview_fetch_empty)
        worker.failed.connect(self._on_preview_fetch_failed)
        self._preview_worker = worker
        worker.start()

    def _on_preview_fetch_done(self):
        """Shared tail of all three PreviewFetchWorker outcomes: clear the
        in-flight marker, then either fire a queued "Run this stage"/"Run
        all" click (see _launch()'s guard — takes priority, since it's an
        explicit user action) or re-run _refresh_preview() if a newer
        navigation request arrived while this fetch was running (see the
        _preview_pending comment in _refresh_preview)."""
        self._preview_worker = None
        if self._pending_launch is not None:
            stage_fns, self._pending_launch = self._pending_launch, None
            self._preview_pending = False
            self._launch(stage_fns)
            return
        if self._preview_pending:
            self._refresh_preview()

    def _on_preview_fetch_succeeded(self, qimg):
        # Same image on both sides rather than (qimg, None): a stage that
        # hasn't run yet has no real "after" to show, but passing None
        # leaves the right half of the split view blank/black, which reads
        # as broken rather than "nothing to compare yet". Filling both
        # sides keeps the split divider meaningful (drag it and both
        # halves show the same picture) without implying a stage result
        # that doesn't exist.
        self.compare.set_images(qimg, qimg)
        self._on_preview_fetch_done()

    def _on_preview_fetch_empty(self):
        self.compare.set_images(None, None)
        self._on_preview_fetch_done()

    def _on_preview_fetch_failed(self, msg):
        self.compare.set_images(None, None)
        self.siril.log(f"Preview refresh failed: {msg}", LogColor.SALMON)
        self._on_preview_fetch_done()

    def _on_snapshot_ready(self, stage_idx):
        self.preview_stage_combo.setCurrentIndex(stage_idx)
        self._refresh_preview()
        # enable this stage's Undo button once a backup exists
        btn = self.undo_buttons.get(stage_idx)
        if btn is not None and stage_idx in self.stage_backups:
            btn.setEnabled(True)
        if stage_idx == IDX_CROP and not getattr(self, "_pending_crop_box", None):
            self._clear_pending_crop_box()

    def _undo_stage(self, stage_idx):
        """Restore the full-resolution image saved before this stage ran."""
        backup = self.stage_backups.get(stage_idx)
        if backup is None:
            return
        # Undoing Histogram or Final Touch restores the pre-stage image, but
        # that stage's sliders would otherwise stay wherever the user left
        # them — reset them here (main thread — these are widget calls) so
        # the panel matches the restored image.
        if stage_idx == IDX_HIST:
            self._reset_hist_controls()
        elif stage_idx == IDX_TOUCH:
            self._reset_touch_controls()
        def job(progress):
            progress(f"Undoing {STAGES[stage_idx]}...", 0.3)
            self._set_current_image(
                backup, f"AstroPipeline: undo {STAGES[stage_idx]}")
            # swap the preview so 'after' shows the restored (before) state
            self._store_snapshot(stage_idx,
                                 self.snapshots_raw_after.get(stage_idx), backup,
                                 before_linear=stage_idx < IDX_STR,
                                 after_linear=stage_idx < IDX_HIST)
            progress(f"{STAGES[stage_idx]} undone.", 1.0)
            self.siril.log(f"Undid stage: {STAGES[stage_idx]}", LogColor.BLUE)
        self._launch([job])

    def _store_snapshot(self, stage_idx, before_arr, after_arr,
                        before_linear=True, after_linear=True):
        """Convert numpy arrays to display QImages and store them (thread-safe)."""
        do_stretch = self.chk_display_stretch.isChecked()

        def prep(arr, linear):
            if arr is None:
                return None
            hwc = to_hwc_float(arr)
            if linear and do_stretch:
                hwc = display_autostretch(hwc)
            return make_qimage(hwc)

        self.snapshots[stage_idx] = {
            "before": prep(before_arr, before_linear),
            "after": prep(after_arr, after_linear),
        }
        self.snapshot_ready.emit(stage_idx)

    def _load_siril_current_into_stage(self, stage_idx, stage_label):
        """'⇩ Use Siril's image' — small button on every stage's header
        (added in _stage_box). Refreshes just that stage's "before"
        preview with whatever is currently loaded in Siril right now, so
        work done manually in Siril's own GUI (or another script)
        outside this pipeline is visible here before continuing.

        Every _exec_stage* function already reads Siril's live image at
        run time via _get_current_image() — this button doesn't change
        that behavior, it only lets you confirm/preview it first. Only
        the "before" thumbnail is touched; any existing "after" result
        from a previous run of this stage is left as-is rather than
        being blanked out."""
        try:
            arr = self._get_current_image()
        except RuntimeError as e:
            QMessageBox.warning(self, "No image", str(e))
            return
        do_stretch = self.chk_display_stretch.isChecked()
        hwc = to_hwc_float(arr)
        if do_stretch:
            hwc = display_autostretch(hwc)
        snap = dict(self.snapshots.get(stage_idx, {}))
        snap["before"] = make_qimage(hwc)
        self.snapshots[stage_idx] = snap
        self.snapshot_ready.emit(stage_idx)
        self.status_label.setText(
            f"{stage_label}: synced with Siril's current image.")
        self.siril.log(
            f"{stage_label}: loaded Siril's current image as this "
            "stage's preview.", LogColor.BLUE)

    def _guided_pause(self, title, instructions, verify_fn=None,
                      verify_error=None):
        """Pause the calling stage (called from the worker thread, e.g.
        from within an `_exec_stage*` function) and show a modal dialog
        with `instructions` + Continue/Cancel on the GUI thread, blocking
        the worker until the user responds — used by Comet Stack mode's
        two GUI-only manual steps (comet registration, Star
        Recomposition), which have no Siril console command equivalent.

        If `verify_fn` is given, it's called (also on the GUI thread,
        right after Continue is clicked) to confirm the manual step
        actually happened (e.g. checking that an expected .seq file now
        exists on disk); if it returns falsy, `verify_error` is shown and
        the same dialog reappears rather than silently proceeding.
        Raises RuntimeError (aborting the stage, same as any other
        _exec_stage* failure) if the user clicks Cancel.

        Uses the same cross-thread signal pattern already established by
        snapshot_ready/_on_snapshot_ready — see the guided_pause_requested
        signal above — plus a threading.Event so the worker thread
        actually blocks until the GUI-thread dialog is dismissed."""
        event = threading.Event()
        state = {"cancelled": False}
        self.guided_pause_requested.emit({
            "title": title, "instructions": instructions,
            "verify_fn": verify_fn, "verify_error": verify_error,
            "event": event, "state": state,
        })
        event.wait()
        if state["cancelled"]:
            raise RuntimeError(f"{title}: cancelled by user.")

    def _on_guided_pause_requested(self, payload):
        """GUI-thread slot for guided_pause_requested — see _guided_pause
        above for why this two-part (emit + slot) split exists."""
        title = payload["title"]
        verify_fn = payload["verify_fn"]
        verify_error = payload["verify_error"]
        try:
            while True:
                dlg = QDialog(self)
                dlg.setWindowTitle(title)
                dlg.setMinimumWidth(480)
                dv = QVBoxLayout(dlg)
                lbl = QLabel(payload["instructions"])
                lbl.setWordWrap(True)
                dv.addWidget(lbl)
                buttons = QDialogButtonBox(
                    QDialogButtonBox.StandardButton.Ok |
                    QDialogButtonBox.StandardButton.Cancel)
                ok_btn = buttons.button(QDialogButtonBox.StandardButton.Ok)
                ok_btn.setText("Continue")
                buttons.accepted.connect(dlg.accept)
                buttons.rejected.connect(dlg.reject)
                dv.addWidget(buttons)
                if dlg.exec() != QDialog.DialogCode.Accepted:
                    payload["state"]["cancelled"] = True
                    break
                if verify_fn is None or verify_fn():
                    break
                QMessageBox.warning(
                    self, "Not ready yet",
                    verify_error or
                    "That manual step doesn't look like it finished yet — "
                    "please complete it, then click Continue again.")
        finally:
            payload["event"].set()

    def _finish_stage(self, idx, before, after, done_msg, log_msg,
                      before_linear=True, after_linear=True,
                      autosave_name=None, progress=None):
        """Common tail shared by most `_exec_stage*` functions: records the
        undo backup + preview snapshot, optionally auto-saves a copy under
        Siril, reports completion, and logs it. Called once a stage has
        already pushed `after` into Siril itself (via `_set_current_image`
        or a `siril.cmd` call) — this only handles the bookkeeping that
        follows, which used to be duplicated near-identically at the end of
        every stage's exec function.
        """
        if autosave_name:
            now = datetime.now().strftime("%Y-%m-%d_%H%M")
            try:
                self.siril.cmd("save", f"{autosave_name}_{now}")
            except Exception as e:
                self.siril.log(
                    f"Auto-save of '{autosave_name}_{now}' failed: {e}",
                    LogColor.SALMON)
        self.stage_backups[idx] = before
        self.snapshots_raw_after[idx] = after
        self._store_snapshot(idx, before, after, before_linear, after_linear)
        self._last_run_stage_idx = idx
        if progress:
            progress(done_msg, 1.0)
        self.siril.log(log_msg, LogColor.GREEN)

    # ------------------------------------------------------------ run control

    def _launch(self, stage_fns):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Busy", "A stage is already running.")
            return
        # A background PreviewFetchWorker may still be fetching Siril's
        # current image (e.g. right after opening the window, for whichever
        # stage has no snapshot yet — see _refresh_preview). Starting the
        # stage-execution Worker while that's in flight means two threads
        # hit the same Siril connection at once, which can hang rather than
        # error. Queue the launch instead and fire it from
        # _on_preview_fetch_done() once the fetch clears.
        if self._preview_worker is not None and self._preview_worker.isRunning():
            self._pending_launch = stage_fns
            self.status_label.setText("Waiting for preview to finish loading…")
            return
        self._pending_launch = None

        def job(progress):
            for fn in stage_fns:
                fn(progress)

        self._set_running(True)
        self.worker = Worker(job)
        self.worker.progressed.connect(self._on_progress)
        self.worker.failed.connect(self._on_failed)
        self.worker.succeeded.connect(self._on_succeeded)
        self.worker.start()

    def on_run_all(self):
        fns = []
        if self.stage1_box.isChecked():
            fns.append(self._exec_stage1)
        if self.stage_crop_box.isChecked():
            fns.append(self._exec_stage_crop)
        if self.stage_scnr_box.isChecked():
            fns.append(self._exec_stage_scnr)
        if self.stage_agr_box.isChecked():
            fns.append(self._exec_stage_agr)
        if self.stage2_box.isChecked():
            fns.append(self._exec_stage2)
        if self.stage_stars_box.isChecked():
            fns.append(self._exec_stage_stars)
        if self.stage3_box.isChecked():
            fns.append(self._exec_stage3)
        if self.stage_pal_box.isChecked():
            fns.append(self._exec_stage_palette)
        if self.stage4_box.isChecked():
            fns.append(self._exec_stage4)
        if self.stage_hist_box.isChecked():
            fns.append(self._exec_stage_hist)
        if self.stage_touch_box.isChecked():
            fns.append(self._exec_stage_touch)
        if self.stage_ann_box.isChecked():
            fns.append(self._exec_stage_ann)
        if self.stage_wm_box.isChecked():
            fns.append(self._exec_stage_watermark)
        if not fns:
            QMessageBox.information(self, "Nothing to run",
                                    "Enable at least one stage (checkbox in its title).")
            return
        self._launch(fns)

    def _set_running(self, running):
        for w in (self.run_all_btn, self.save_file_btn, self.stage1_run,
                  self.stage_crop_run,
                  self.stage_scnr_run, self.stage_agr_run,
                  self.stage2_run, self.stage_stars_run,
                  self.stage3_run, self.stage_pal_run,
                  self.stage4_run, self.stage_hist_run, self.stage_touch_run,
                  self.stage_ann_run, self.stage_wm_run, self.calc_d_btn,
                  self.hist_load_btn,
                  self.touch_load_btn, self.manual_readd_stars_btn,
                  self.crop_draw_btn, self.reset_btn):
            w.setEnabled(not running)
        self.progress_bar.setVisible(running)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_pct_label.setVisible(running)
        self.progress_time_label.setVisible(running)
        if running:
            self.status_label.setText("Working...")
            self.progress_pct_label.setText("0%")
            self.progress_time_label.setText("0:00")
            self._run_start_time = time.monotonic()
            self._elapsed_timer.start()
        else:
            self._elapsed_timer.stop()
            self._run_start_time = None

    def _update_elapsed_label(self):
        """Ticks once a second while a stage/run-all is in progress, so the
        elapsed-time readout is a live clock rather than only updating
        whenever a progress() call happens to fire (some stages go a long
        stretch between those)."""
        if self._run_start_time is None:
            return
        secs = int(time.monotonic() - self._run_start_time)
        m, s = divmod(secs, 60)
        h, m = divmod(m, 60)
        text = f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"
        self.progress_time_label.setText(text)

    def _on_progress(self, msg, p):
        self.status_label.setText(msg)
        if p > 0:
            self.progress_bar.setValue(int(p * 100))
            self.progress_pct_label.setText(f"{int(p * 100)}%")
        try:
            self.siril.update_progress(msg, p)
        except Exception:
            pass

    def _on_failed(self, err):
        self._set_running(False)
        self.status_label.setText(f"Error: {err}")
        self.siril.log(f"Pipeline error: {err}", LogColor.RED)
        QMessageBox.critical(self, "Pipeline error", err)
        # A preview fetch may have been deferred while this stage ran
        # (see _refresh_preview's self.worker.isRunning() guard) — retry it
        # now that the Siril connection is free again.
        if self._preview_pending:
            self._refresh_preview()

    def _on_succeeded(self):
        self._set_running(False)
        self.status_label.setText("Done. Compare results in the preview panel →")
        self._update_image_info()
        try:
            self.siril.reset_progress()
        except Exception:
            pass
        if self._preview_pending:
            self._refresh_preview()

    def _update_image_info(self):
        """Show target / date / integration / FOV / size of the current image."""
        try:
            if not self.siril.is_image_loaded():
                self.image_info_label.setText("No image loaded.")
                return
            hdr = self.siril.get_image_fits_header(return_as="dict")
        except Exception:
            self.image_info_label.setText("No image loaded.")
            return
        parts = []

        obj = str(hdr.get("OBJECT", "")).strip()
        if obj and obj.lower() != "unknown":
            parts.append(f"🎯 {obj}")

        # capture date(s): range scanned from all subs (stage 1), single
        # header date otherwise
        if self.date_range:
            d0, d1 = self.date_range
            parts.append(f"📅 {d0}" if d0 == d1 else f"📅 {d0} → {d1}")
        else:
            date_obs = str(hdr.get("DATE-OBS", ""))
            if date_obs:
                parts.append(f"📅 {date_obs.split('T')[0]}")

        # integration time: LIVETIME (total), else STACKCNT × EXPTIME
        try:
            live = float(hdr.get("LIVETIME", 0) or 0)
            cnt = int(hdr.get("STACKCNT", 0) or 0)
            exp = float(hdr.get("EXPTIME", 0) or 0)
            if live <= 0 and cnt and exp:
                live = cnt * exp
            if live > 0:
                txt = f"⏱ {live / 60.0:.0f} min"
                if cnt and exp:
                    txt += f" ({cnt}×{exp:.0f}s)"
                parts.append(txt)
        except Exception:
            pass

        # FOV and dimensions from the *current* (stacked/cropped/drizzled)
        # image. Pixel scale comes from the plate-solve WCS when available —
        # this is exact even after drizzle or crop, unlike the focal-length /
        # pixel-size formula which describes the raw sensor.
        try:
            w_px = int(hdr.get("NAXIS1", 0) or 0)
            h_px = int(hdr.get("NAXIS2", 0) or 0)
            scale = 0.0
            src = ""
            # 1) WCS CD matrix / CDELT written by the plate solve
            try:
                cd11 = float(hdr.get("CD1_1", 0) or 0)
                cd12 = float(hdr.get("CD1_2", 0) or 0)
                cd21 = float(hdr.get("CD2_1", 0) or 0)
                cd22 = float(hdr.get("CD2_2", 0) or 0)
                det = abs(cd11 * cd22 - cd12 * cd21)
                if det > 0:
                    scale = math.sqrt(det) * 3600.0  # deg/px → arcsec/px
                    src = "plate solve"
                else:
                    cdelt = abs(float(hdr.get("CDELT1", 0) or 0))
                    if cdelt > 1e-9:
                        scale = cdelt * 3600.0
                        src = "plate solve"
            except Exception:
                pass
            # 2) fallback: focal length + pixel size from the sensor
            if scale <= 0:
                focal = float(hdr.get("FOCALLEN", 0) or 0)
                pxsz = float(hdr.get("XPIXSZ", 0) or 0)
                if focal > 0 and pxsz > 0:
                    scale = 206.265 * pxsz / focal
                    src = "focal/pixel"
            if w_px and h_px and scale > 0:
                fov_w = scale * w_px / 3600.0
                fov_h = scale * h_px / 3600.0
                parts.append(f"🔭 FOV {fov_w:.2f}°×{fov_h:.2f}° "
                             f"({scale:.2f}\"/px, {src})")
            if w_px and h_px:
                parts.append(f"🖼 {w_px}×{h_px} px")
        except Exception:
            pass

        tele = str(hdr.get("TELESCOP", "") or hdr.get("INSTRUME", "")).strip()
        if tele:
            parts.append(f"📡 {tele}")

        if self.estimated_bortle:
            b = self.estimated_bortle
            parts.append(f"🌌 Bortle {b['bortle']} ({b['name']}) [est.]")
            self.image_info_label.setToolTip(
                f"Bortle estimate is derived from the sky background level of "
                f"{b['n_samples']} randomly sampled raw light frame(s), not a "
                f"calibrated SQM reading.\n"
                f"Estimated sky brightness: ~{b['sqm']:.2f} mag/arcsec² (SQM-equivalent).\n"
                f"Assumes 1 e-/ADU unless the header specifies a gain, and an "
                f"uncalibrated instrumental zero point scaled by aperture — "
                f"treat this as a rough comparison, not a certified measurement.")
        else:
            self.image_info_label.setToolTip("")

        self.image_info_label.setText(
            "   •   ".join(parts) if parts else "Image loaded (no metadata).")

    # -------------------------------------------------------- image utilities

    def _get_current_image(self):
        """Current Siril image as float32 planar, 0..1."""
        try:
            data = self.siril.get_image_pixeldata()
        except Exception as e:
            # sirilpy raises its own SirilError (not a None return) when
            # nothing's loaded yet — e.g. "no FITS image" right after the
            # pipeline window opens, before the user has loaded anything.
            # Every caller here already expects/catches RuntimeError for
            # "nothing to preview yet", so normalize to that instead of
            # letting sirilpy's exception type crash the caller.
            raise RuntimeError(f"No image loaded in Siril ({e}).") from e
        if data is None:
            raise RuntimeError("No image loaded in Siril.")
        if data.ndim == 2:
            data = data[np.newaxis, ...]
        return VeraLuxCore.normalize_input(data)

    def _set_current_image(self, arr, undo_label):
        arr = np.clip(arr, 0.0, 1.0).astype(np.float32)
        with self.siril.image_lock():
            self.siril.undo_save_state(undo_label)
            self.siril.set_image_pixeldata(arr)

    # ------------------------------------------------------ settings JSON I/O

    def _collect_settings(self):
        sd = {
            "app": APP_NAME, "version": VERSION,
            "stages_enabled": {
                "preprocess": self.stage1_box.isChecked(),
                "crop": self.stage_crop_box.isChecked(),
                "scnr": self.stage_scnr_box.isChecked(),
                "auto_gradient": self.stage_agr_box.isChecked(),
                "remove_bg": self.stage2_box.isChecked(),
                "stars": self.stage_stars_box.isChecked(),
                "denoise": self.stage3_box.isChecked(),
                "palette": self.stage_pal_box.isChecked(),
                "stretch": self.stage4_box.isChecked(),
                "histogram": self.stage_hist_box.isChecked(),
                "final_touch": self.stage_touch_box.isChecked(),
                "annotate": self.stage_ann_box.isChecked(),
                "watermark": self.stage_wm_box.isChecked(),
            },
            "final_touch": {
                **{k: sl.value() for k, sl in self.touch_sliders.items()},
                "sharpen_mode": self.touch_sharpen_mode_combo.currentIndex(),
            },
            "annotate": {
                "stars": self.ann_stars_checkbox.isChecked(),
                "online": self.ann_online_checkbox.isChecked(),
                "mag_limit": self.ann_mag_spin.value(),
                "label_size": self.ann_size_spin.value(),
                "marker_style": self.ann_marker_style_combo.currentText(),
                "circle_auto_th": self.ann_circle_auto_th_checkbox.isChecked(),
                "circle_th": self.ann_circle_th_spin.value(),
                "circle_custom_color":
                    self.ann_circle_custom_color_checkbox.isChecked(),
                "circle_color": list(self.ann_circle_color),
                "cross_auto_th": self.ann_cross_auto_th_checkbox.isChecked(),
                "cross_th": self.ann_cross_th_spin.value(),
                "cross_custom_color":
                    self.ann_cross_custom_color_checkbox.isChecked(),
                "cross_color": list(self.ann_cross_color),
                "cross_gap_mult": self.ann_cross_gap_spin.value(),
                "cross_arm_mult": self.ann_cross_arm_spin.value(),
                "cross_label_pos": self.ann_cross_label_pos_combo.currentText(),
                "cross_label_dist_mult": self.ann_cross_label_dist_spin.value(),
                "detail_type": self.ann_detail_type_checkbox.isChecked(),
                "detail_mag": self.ann_detail_mag_checkbox.isChecked(),
                "detail_const": self.ann_detail_const_checkbox.isChecked(),
                "detail_size": self.ann_detail_size_checkbox.isChecked(),
                "custom_lines": [
                    row for row in
                    self.ann_custom_lines_edit.toPlainText().splitlines()
                    if row.strip()],
                "show_overlay": self.ann_show_overlay_checkbox.isChecked(),
                "cat_messier": self.ann_cat_messier_checkbox.isChecked(),
                "cat_ngc": self.ann_cat_ngc_checkbox.isChecked(),
                "cat_ic": self.ann_cat_ic_checkbox.isChecked(),
                "cat_sh2": self.ann_cat_sh2_checkbox.isChecked(),
                "cat_ldn": self.ann_cat_ldn_checkbox.isChecked(),
                "constellations_enabled": self.ann_const_checkbox.isChecked(),
                "constellations_selected": sorted(self.ann_const_selected),
                "constellations_names": self.ann_const_names_checkbox.isChecked(),
                "constellations_width": self.ann_const_width_spin.value(),
                "constellations_gap": self.ann_const_gap_spin.value(),
                "constellations_color": list(self.ann_const_color),
                "constellations_name_color": list(self.ann_const_name_color),
                "constellations_preset": self.ann_const_preset_combo.currentText(),
            },
            "watermark": {
                "fields": {k: cb.isChecked()
                          for k, cb in self.wm_field_checkboxes.items()},
                "position": self.wm_position_combo.currentText(),
                "alpha_pct": self.wm_alpha_spin.value(),
                "two_column": self.wm_two_col_checkbox.isChecked(),
                "integration_unit": self.wm_integration_unit_combo.currentText(),
                "author_enabled": self.wm_author_checkbox.isChecked(),
                "author_name": self.wm_author_edit.text(),
            },
            "palette": {
                "mode": self.palette_mode_combo.currentIndex(),
                "preset": self.palette_preset_combo.currentText(),
                "linear_fit": self.palette_linfit_checkbox.isChecked(),
                "auto_profile": self.palette_set_profile_checkbox.isChecked(),
                "weights": {ch: [p[0].value(), p[1].value()]
                            for ch, p in self.palette_weights.items()},
                "nebulachrome_strength": self.palette_nebulachrome_strength.value(),
                "nebulachrome_peak": self.palette_nebulachrome_peak.value(),
                "gimp_polish_enabled": self.palette_gimp_checkbox.isChecked(),
                "gimp_polish": {k: sl.value()
                               for k, sl in self.palette_gimp_sliders.items()},
            },
            "stars": {
                "strength": self.star_strength_spin.value(),
                "asinh": self.star_asinh_spin.value(),
            },
            "preprocess": {
                "telescope": self.telescope_combo.currentText(),
                "filter": self.filter_combo.currentText(),
                "darks": self.darks_checkbox.isChecked(),
                "flats": self.flats_checkbox.isChecked(),
                "biases": self.biases_checkbox.isChecked(),
                "drizzle": self.drizzle_checkbox.isChecked(),
                "drizzle_amount": self.drizzle_amount.value(),
                "pixel_fraction": self.pixel_fraction.value(),
                "feather": self.feather_checkbox.isChecked(),
                "feather_amount": self.feather_amount.value(),
                "stack_method": self.stack_method_combo.currentText(),
                "weighting": self.weighting_checkbox.isChecked(),
                "weighting_method": self.weighting_method_combo.currentText(),
                "spcc": self.spcc_checkbox.isChecked(),
                "compression": self.compression_checkbox.isChecked(),
                "cleanup": self.cleanup_checkbox.isChecked(),
                "disto_order": self.disto_order_spin.value(),
                "seqsubsky": self.seqsubsky_checkbox.isChecked(),
                "seqsubsky_degree": self.seqsubsky_degree_spin.value(),
                "overlap_norm": self.overlap_norm_checkbox.isChecked(),
                "combine_master_enabled": self.combine_master_checkbox.isChecked(),
                "combine_master_path": self.combine_master_path_edit.text(),
                "combine_master_subcount":
                    self.combine_master_subcount_spin.value(),
                "comet_sigma_low": self.comet_sigma_low_spin.value(),
                "comet_sigma_high": self.comet_sigma_high_spin.value(),
                "comet_subsky_degree": self.comet_subsky_degree_spin.value(),
                "comet_subsky_samples": self.comet_subsky_samples_spin.value(),
            },
            "crop": {
                "auto": self.crop_auto_checkbox.isChecked(),
                "margins": {k: v.value() for k, v in self.crop_margins.items()},
                "rotate_deg": self.crop_rotate_spin.value(),
            },
            "scnr": {
                "type": self.scnr_type_combo.currentIndex(),
                "amount": self.scnr_amount.value(),
                "preserve": self.scnr_preserve_checkbox.isChecked(),
            },
            "auto_gradient": {
                "scale": self.agr_scale_spin.value(),
                "smoothness": self.agr_smoothness_spin.value(),
                "protect": self.agr_protect_checkbox.isChecked(),
                "protect_threshold": self.agr_pthr_spin.value(),
                "protect_amount": self.agr_pamt_spin.value(),
                "simplified": self.agr_simplified_checkbox.isChecked(),
                "degree": self.agr_degree_spin.value(),
                "downsample": self.agr_downsample_combo.currentText(),
                "mode": self.agr_mode_combo.currentText(),
            },
            "remove_bg": {
                "method": self.bge_method_combo.currentIndex(),
                "model": self.bge_model_combo.currentText(),
                "correction": self.bge_correction_combo.currentText(),
                "smoothing": self.bge_smoothing_slider.value(),
                "subsky_samples": self.subsky_samples.value(),
                "subsky_tolerance": self.subsky_tolerance.value(),
                "subsky_smooth": self.subsky_smooth.value(),
                "subsky_degree": self.subsky_degree.value(),
            },
            "denoise": {
                "model": self.denoise_model_combo.currentText(),
                "strength": self.denoise_strength_slider.value(),
                "batch_size": self.denoise_batch.value(),
                "gpu": self.denoise_gpu.isChecked(),
            },
            "stretch": {
                "profile": self.profile_combo.currentText(),
                "mode": self.stretch_mode_combo.currentText(),
                "log_d": self.log_d_spin.value(),
                "auto_log_d": self.auto_d_checkbox.isChecked(),
                "protect_b": self.protect_b_spin.value(),
                "target_bg": self.target_bg_spin.value(),
                "convergence": self.convergence_spin.value(),
                "color_grip": self.color_grip_spin.value(),
                "linear_expansion": self.linear_exp_spin.value(),
                "adaptive_anchor": self.adaptive_anchor_checkbox.isChecked(),
            },
            "histogram": {
                ch: {k: spin.value() for k, spin in controls.items()}
                for ch, controls in self.hist_controls.items()
            },
            "preview": {
                "autostretch": self.chk_display_stretch.isChecked(),
            },
        }
        return sd

    def _apply_settings(self, sd):
        en = sd.get("stages_enabled", {})
        self.stage1_box.setChecked(en.get("preprocess", True))
        self.stage_crop_box.setChecked(en.get("crop", True))
        self.stage_scnr_box.setChecked(en.get("scnr", False))
        self.stage_agr_box.setChecked(en.get("auto_gradient", False))
        self.stage2_box.setChecked(en.get("remove_bg", True))
        self.stage_stars_box.setChecked(en.get("stars", False))
        self.stage3_box.setChecked(en.get("denoise", True))
        self.stage_pal_box.setChecked(en.get("palette", False))
        self.stage4_box.setChecked(en.get("stretch", True))
        self.stage_hist_box.setChecked(en.get("histogram", False))
        self.stage_touch_box.setChecked(en.get("final_touch", False))
        self.stage_ann_box.setChecked(en.get("annotate", False))
        self.stage_wm_box.setChecked(en.get("watermark", False))

        ft = sd.get("final_touch", {})
        for k, sl in self.touch_sliders.items():
            if k in ft:
                sl.setValue(int(ft[k]))
        if "sharpen_mode" in ft:
            self.touch_sharpen_mode_combo.setCurrentIndex(int(ft["sharpen_mode"]))

        an = sd.get("annotate", {})
        self.ann_stars_checkbox.setChecked(an.get("stars", True))
        self.ann_online_checkbox.setChecked(an.get("online", False))
        self.ann_mag_spin.setValue(float(an.get("mag_limit", 6.0)))
        self.ann_size_spin.setValue(float(an.get("label_size", 1.0)))
        marker_style = an.get("marker_style", "Circle")
        if marker_style not in ("Circle", "Open Cross", "Circle + Open Cross"):
            marker_style = "Circle"
        self.ann_marker_style_combo.setCurrentText(marker_style)
        self.ann_circle_auto_th_checkbox.setChecked(
            an.get("circle_auto_th", True))
        self.ann_circle_th_spin.setValue(int(an.get("circle_th", 2)))
        self.ann_circle_custom_color_checkbox.setChecked(
            an.get("circle_custom_color", False))
        circle_color = an.get("circle_color")
        self.ann_circle_color = (
            tuple(int(c) for c in circle_color)
            if circle_color and len(circle_color) == 3 else (255, 255, 255))
        self.ann_cross_auto_th_checkbox.setChecked(
            an.get("cross_auto_th", True))
        self.ann_cross_th_spin.setValue(int(an.get("cross_th", 2)))
        self.ann_cross_custom_color_checkbox.setChecked(
            an.get("cross_custom_color", False))
        cross_color = an.get("cross_color")
        self.ann_cross_color = (
            tuple(int(c) for c in cross_color)
            if cross_color and len(cross_color) == 3 else (255, 255, 255))
        for color, swatch in ((self.ann_circle_color, self.ann_circle_swatch),
                              (self.ann_cross_color, self.ann_cross_swatch)):
            b, g_, r = color
            swatch.setStyleSheet(
                f"background-color: rgb({r},{g_},{b}); border-radius: 3px; "
                "border: 1px solid rgba(255,255,255,60);")
        self.ann_cross_gap_spin.setValue(float(an.get("cross_gap_mult", 0.5)))
        self.ann_cross_arm_spin.setValue(float(an.get("cross_arm_mult", 0.7)))
        cross_label_pos = an.get("cross_label_pos", "Auto (avoid overlap)")
        if cross_label_pos not in ("Auto (avoid overlap)", "NE", "NW", "SE", "SW"):
            cross_label_pos = "Auto (avoid overlap)"
        self.ann_cross_label_pos_combo.setCurrentText(cross_label_pos)
        self.ann_cross_label_dist_spin.setValue(
            float(an.get("cross_label_dist_mult", 0.1)))
        self.ann_detail_type_checkbox.setChecked(an.get("detail_type", False))
        self.ann_detail_mag_checkbox.setChecked(an.get("detail_mag", False))
        self.ann_detail_const_checkbox.setChecked(an.get("detail_const", False))
        self.ann_detail_size_checkbox.setChecked(an.get("detail_size", False))
        self.ann_custom_lines_edit.setPlainText(
            "\n".join(str(t) for t in an.get("custom_lines", [])))
        self.ann_show_overlay_checkbox.setChecked(an.get("show_overlay", True))
        self.ann_cat_messier_checkbox.setChecked(an.get("cat_messier", True))
        self.ann_cat_ngc_checkbox.setChecked(an.get("cat_ngc", True))
        self.ann_cat_ic_checkbox.setChecked(an.get("cat_ic", True))
        self.ann_cat_sh2_checkbox.setChecked(an.get("cat_sh2", False))
        self.ann_cat_ldn_checkbox.setChecked(an.get("cat_ldn", False))
        self.ann_const_checkbox.setChecked(
            an.get("constellations_enabled", False))
        const_sel = an.get("constellations_selected", None)
        if const_sel is None:
            # Key absent — either a fresh/empty settings dict (e.g. the
            # Reset button's self._apply_settings({})) or an older
            # settings JSON saved before this feature existed. Both cases
            # should land on "everything selected", not "leave whatever
            # was already checked alone".
            self.ann_const_selected = set(CONSTELLATION_NAMES.keys())
        else:
            self.ann_const_selected = {
                a for a in const_sel if a in CONSTELLATION_NAMES}
        self.ann_const_names_checkbox.setChecked(
            an.get("constellations_names", True))
        self.ann_const_width_spin.setValue(
            int(an.get("constellations_width", 1)))
        self.ann_const_gap_spin.setValue(
            int(an.get("constellations_gap", 8)))
        const_color = an.get("constellations_color")
        self.ann_const_color = (
            tuple(int(c) for c in const_color)
            if const_color and len(const_color) == 3
            else (220, 190, 255))
        const_name_color = an.get("constellations_name_color")
        self.ann_const_name_color = (
            tuple(int(c) for c in const_name_color)
            if const_name_color and len(const_name_color) == 3
            else self.ann_const_color)
        for color, swatch in ((self.ann_const_color, self.ann_const_swatch),
                              (self.ann_const_name_color,
                               self.ann_const_name_swatch)):
            b, g_, r = color
            swatch.setStyleSheet(
                f"background-color: rgb({r},{g_},{b}); border-radius: 3px; "
                "border: 1px solid rgba(255,255,255,60);")
        # Restore the preset dropdown's text without re-triggering
        # _apply_constellation_preset — the colors above are already the
        # authoritative values (whatever was actually saved), so applying
        # a preset here would either be redundant (matching preset) or
        # wrongly clobber genuinely custom colors.
        self.ann_const_preset_combo.blockSignals(True)
        preset_name = an.get("constellations_preset", "Custom")
        if preset_name not in CONSTELLATION_COLOR_PRESETS:
            preset_name = "Custom"
        self.ann_const_preset_combo.setCurrentText(preset_name)
        self.ann_const_preset_combo.blockSignals(False)

        wm = sd.get("watermark", {})
        wm_fields = wm.get("fields", {})
        for k, cb in self.wm_field_checkboxes.items():
            if k in wm_fields:
                cb.setChecked(bool(wm_fields[k]))
        if wm.get("position") in WATERMARK_POSITIONS:
            self.wm_position_combo.setCurrentText(wm["position"])
        if "alpha_pct" in wm:
            self.wm_alpha_spin.setValue(int(wm["alpha_pct"]))
        self.wm_two_col_checkbox.setChecked(bool(wm.get("two_column", False)))
        self.wm_integration_unit_combo.setCurrentText(
            wm.get("integration_unit", "Minutes"))
        self.wm_author_checkbox.setChecked(bool(wm.get("author_enabled", False)))
        self.wm_author_edit.setText(str(wm.get("author_name", "")))

        pal = sd.get("palette", {})
        if pal.get("preset") in PALETTE_PRESETS:
            self.palette_preset_combo.setCurrentText(pal["preset"])
        self.palette_linfit_checkbox.setChecked(pal.get("linear_fit", True))
        self.palette_set_profile_checkbox.setChecked(
            pal.get("auto_profile", True))
        self.palette_mode_combo.setCurrentIndex(int(pal.get("mode", 0)))
        self.palette_nebulachrome_strength.setValue(
            int(pal.get("nebulachrome_strength", 70)))
        self.palette_nebulachrome_peak.setValue(
            int(pal.get("nebulachrome_peak", 300)))
        self.palette_gimp_checkbox.setChecked(
            bool(pal.get("gimp_polish_enabled", False)))
        gp = pal.get("gimp_polish", {})
        gimp_defaults = {"saturation": 100, "shadows": 0, "highlights": 0,
                         "contrast": 0, "sharpen": 0, "denoise": 0}
        for key, sl in self.palette_gimp_sliders.items():
            sl.setValue(int(gp.get(key, gimp_defaults[key])))
        # stars section (with fallback to keys from pre-split settings files)
        stx = sd.get("stars", {})
        self.star_strength_spin.setValue(
            float(stx.get("strength", pal.get("star_strength", 1.0))))
        self.star_asinh_spin.setValue(
            float(stx.get("asinh", pal.get("star_asinh", 8.0))))
        if PALETTE_PRESETS.get(self.palette_preset_combo.currentText()) is None:
            for ch, vals in pal.get("weights", {}).items():
                if ch in self.palette_weights and len(vals) == 2:
                    self.palette_weights[ch][0].setValue(float(vals[0]))
                    self.palette_weights[ch][1].setValue(float(vals[1]))

        p = sd.get("preprocess", {})
        if p.get("telescope"):
            self.telescope_combo.setCurrentText(p["telescope"])
        if p.get("filter"):
            self.filter_combo.setCurrentText(p["filter"])
        self.darks_checkbox.setChecked(p.get("darks", False))
        self.flats_checkbox.setChecked(p.get("flats", False))
        self.biases_checkbox.setChecked(p.get("biases", False))
        self.drizzle_checkbox.setChecked(p.get("drizzle", False))
        self.drizzle_amount.setValue(p.get("drizzle_amount", 1.0))
        self.pixel_fraction.setValue(p.get("pixel_fraction", 1.0))
        self.feather_checkbox.setChecked(p.get("feather", False))
        self.feather_amount.setValue(int(p.get("feather_amount", 20)))
        # "Median" is the pre-1.36.0 saved value, before the item was
        # relabeled "Median (Milky Way Mode)" — alias it so older
        # settings JSON files still restore the right selection.
        saved_stack_method = p.get("stack_method", "Average (rejection)")
        if saved_stack_method == "Median":
            saved_stack_method = "Median (Milky Way Mode)"
        self.stack_method_combo.setCurrentText(saved_stack_method)
        self.weighting_checkbox.setChecked(p.get("weighting", False))
        if p.get("weighting_method"):
            self.weighting_method_combo.setCurrentText(p["weighting_method"])
        self.spcc_checkbox.setChecked(p.get("spcc", True))
        self.compression_checkbox.setChecked(p.get("compression", False))
        self.cleanup_checkbox.setChecked(p.get("cleanup", True))
        self.disto_order_spin.setValue(int(p.get("disto_order", 4)))
        self.seqsubsky_checkbox.setChecked(p.get("seqsubsky", False))
        self.seqsubsky_degree_spin.setValue(int(p.get("seqsubsky_degree", 1)))
        self.overlap_norm_checkbox.setChecked(p.get("overlap_norm", False))
        self.combine_master_checkbox.setChecked(
            p.get("combine_master_enabled", False))
        self.combine_master_path_edit.setText(
            p.get("combine_master_path", ""))
        self.combine_master_subcount_spin.setValue(
            int(p.get("combine_master_subcount", 0)))
        self.comet_sigma_low_spin.setValue(
            float(p.get("comet_sigma_low", 5.0)))
        self.comet_sigma_high_spin.setValue(
            float(p.get("comet_sigma_high", 5.0)))
        self.comet_subsky_degree_spin.setValue(
            int(p.get("comet_subsky_degree", 1)))
        self.comet_subsky_samples_spin.setValue(
            int(p.get("comet_subsky_samples", 20)))

        c = sd.get("crop", {})
        self.crop_auto_checkbox.setChecked(c.get("auto", True))
        for k, v in c.get("margins", {}).items():
            if k in self.crop_margins:
                self.crop_margins[k].setValue(float(v))
        self.crop_rotate_spin.setValue(float(c.get("rotate_deg", 0.0)))
        # scnr section (with fallback to keys from pre-split settings files)
        sc = sd.get("scnr", {})
        self.scnr_type_combo.setCurrentIndex(
            int(sc.get("type", c.get("scnr_type", 0))))
        self.scnr_amount.setValue(
            float(sc.get("amount", c.get("scnr_amount", 1.0))))
        self.scnr_preserve_checkbox.setChecked(
            sc.get("preserve", c.get("scnr_preserve", True)))
        if "scnr" in c and "scnr" not in sd.get("stages_enabled", {}):
            self.stage_scnr_box.setChecked(bool(c.get("scnr")))

        agr = sd.get("auto_gradient", {})
        self.agr_scale_spin.setValue(float(agr.get("scale", 5.0)))
        self.agr_smoothness_spin.setValue(float(agr.get("smoothness", 1.0)))
        self.agr_protect_checkbox.setChecked(bool(agr.get("protect", True)))
        self.agr_pthr_spin.setValue(float(agr.get("protect_threshold", 0.05)))
        self.agr_pamt_spin.setValue(float(agr.get("protect_amount", 0.5)))
        self.agr_simplified_checkbox.setChecked(bool(agr.get("simplified", False)))
        self.agr_degree_spin.setValue(int(agr.get("degree", 2)))
        if agr.get("downsample"):
            self.agr_downsample_combo.setCurrentText(str(agr["downsample"]))
        if agr.get("mode"):
            self.agr_mode_combo.setCurrentText(agr["mode"])

        b = sd.get("remove_bg", {})
        self.bge_method_combo.setCurrentIndex(int(b.get("method", 0)))
        if b.get("model"):
            self.bge_model_combo.setCurrentText(b["model"])
        if b.get("correction"):
            self.bge_correction_combo.setCurrentText(b["correction"])
        self.bge_smoothing_slider.setValue(int(b.get("smoothing", 50)))
        self.subsky_samples.setValue(int(b.get("subsky_samples", 20)))
        self.subsky_tolerance.setValue(float(b.get("subsky_tolerance", 2.0)))
        self.subsky_smooth.setValue(float(b.get("subsky_smooth", 0.5)))
        self.subsky_degree.setValue(int(b.get("subsky_degree", 2)))

        d = sd.get("denoise", {})
        if d.get("model"):
            self.denoise_model_combo.setCurrentText(d["model"])
        self.denoise_strength_slider.setValue(int(d.get("strength", 80)))
        self.denoise_batch.setValue(int(d.get("batch_size", 16)))
        self.denoise_gpu.setChecked(d.get("gpu", True))

        st = sd.get("stretch", {})
        if st.get("profile") in SENSOR_PROFILES:
            self.profile_combo.setCurrentText(st["profile"])
        if st.get("mode"):
            self.stretch_mode_combo.setCurrentText(st["mode"])
        self.log_d_spin.setValue(st.get("log_d", 2.0))
        self.auto_d_checkbox.setChecked(st.get("auto_log_d", True))
        self.protect_b_spin.setValue(st.get("protect_b", 6.0))
        self.target_bg_spin.setValue(st.get("target_bg", 0.20))
        self.convergence_spin.setValue(st.get("convergence", 2.0))
        self.color_grip_spin.setValue(st.get("color_grip", 1.0))
        self.linear_exp_spin.setValue(st.get("linear_expansion", 0.0))
        self.adaptive_anchor_checkbox.setChecked(st.get("adaptive_anchor", True))

        h = sd.get("histogram", {})
        for ch, controls in self.hist_controls.items():
            vals = h.get(ch, {})
            for k, spin in controls.items():
                if k in vals:
                    spin.setValue(float(vals[k]))

        self.chk_display_stretch.setChecked(
            sd.get("preview", {}).get("autostretch", True))

    def on_export_settings(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export pipeline settings",
            os.path.join(self.cwd, "s30_pipeline_settings.json"),
            "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._collect_settings(), f, indent=2)
            self.status_label.setText(f"Settings exported: {os.path.basename(path)}")
            self.siril.log(f"Settings exported to {path}", LogColor.GREEN)
        except Exception as e:
            QMessageBox.critical(self, "Export failed", str(e))

    def on_save_file(self):
        """Save the image currently loaded in Siril, letting the user pick
        format (FITS / JPEG / PNG / TIFF) and location via a save dialog,
        using Siril's own save commands (not a raw pixel dump)."""
        try:
            loaded = self.siril.is_image_loaded()
        except Exception:
            loaded = False
        if not loaded:
            QMessageBox.information(self, "No image",
                                    "No image is currently loaded in Siril.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Save current image", self.cwd,
            "FITS (*.fit *.fits);;JPEG (*.jpg *.jpeg);;PNG (*.png);;"
            "TIFF (*.tif *.tiff)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        base = os.path.splitext(path)[0]
        command_by_ext = {
            ".fit": "save", ".fits": "save",
            ".jpg": "savejpg", ".jpeg": "savejpg",
            ".png": "savepng",
            ".tif": "savetif", ".tiff": "savetif",
        }
        cmd_name = command_by_ext.get(ext)
        if cmd_name is None:
            QMessageBox.warning(self, "Unsupported format",
                                f"Don't know how to save a '{ext or '(no extension)'}' "
                                "file. Choose FITS, JPEG, PNG or TIFF.")
            return

        def job(progress):
            progress(f"Saving {os.path.basename(path)}...", 0.3)
            self.siril.cmd(cmd_name, f'"{base}"')
            progress(f"Saved: {os.path.basename(path)}", 1.0)
            self.siril.log(f"Image saved: {path}", LogColor.GREEN)
        self._launch([job])

    def on_expand_all_stages(self):
        """'⌄ Expand All' — selects (checks) and expands every stage at
        once. Sets both the header checkbox and the expand arrow
        directly for every stage, rather than checking the box alone
        and relying on _on_enabled_toggle's box->arrow sync to cascade
        — a stage that's already checked (or already expanded) would
        never fire that toggled signal, so relying on it here could
        silently leave a stage out of sync instead of guaranteeing
        every single one ends up both checked and expanded."""
        for box, expand_btn in self._stage_toggle_pairs:
            box.setChecked(True)
            expand_btn.setChecked(True)
        self.status_label.setText("Selected and expanded all stages.")

    def on_collapse_all_stages(self):
        """'⌃ Collapse All' — the reverse of on_expand_all_stages: sets
        both the header checkbox and the expand arrow directly for
        every stage, unconditionally, so every stage ends up both
        unchecked and collapsed regardless of its starting state (see
        on_expand_all_stages for why relying on the toggled signal
        alone isn't enough — e.g. Auto Gradient Removal starts
        unchecked but expanded, so its checkbox is already at the
        target state here and would never fire that signal)."""
        for box, expand_btn in self._stage_toggle_pairs:
            box.setChecked(False)
            expand_btn.setChecked(False)
        self.status_label.setText("Deselected and collapsed all stages.")

    def on_import_settings(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Import pipeline settings", self.cwd, "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, encoding="utf-8") as f:
                sd = json.load(f)
            self._apply_settings(sd)
            self.status_label.setText(f"Settings imported: {os.path.basename(path)}")
            self.siril.log(f"Settings imported from {path}", LogColor.GREEN)
        except Exception as e:
            QMessageBox.critical(self, "Import failed", str(e))

    def on_reset_pipeline(self):
        """'↺ Reset' — resets every stage's settings to their built-in
        defaults, clears all before/after previews and undo history, and
        asks for a new session folder, for starting a fresh pipeline run
        without closing and reopening the window. Doesn't touch anything
        already saved to disk, and leaves whatever's currently loaded in
        Siril itself alone until a stage is run again."""
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(
                self, "Processing", "A stage is still running. Please "
                "wait for it to finish before resetting.")
            return
        reply = QMessageBox.question(
            self, "Reset pipeline",
            "This resets every stage's settings to their defaults and "
            "clears all previews and undo history for a fresh run, then "
            "asks you to pick a new session folder.\n\n"
            "It doesn't touch any files already saved to disk, and the "
            "image currently loaded in Siril is left as-is until you run "
            "a stage again.\n\nContinue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        # settings -> built-in defaults (every _apply_settings lookup
        # falls back to its default when the dict has no matching key)
        self._apply_settings({})

        # clear previews / undo history
        self.snapshots = {}
        self.stage_backups = {}
        for btn in self.undo_buttons.values():
            btn.setEnabled(False)
        self._last_run_stage_idx = None
        self._subsky_boxes = None
        self._pending_crop_box = None
        self._ann_base_canvas = None
        self._ann_drawn = []
        self._last_annotated_canvas = None
        self._last_watermarked_canvas = None
        self.date_range = None
        self.preview_stage_combo.setCurrentIndex(0)
        self._refresh_preview()
        self.image_info_label.setText("No image loaded.")
        self.status_label.setText("Ready.")
        self.progress_bar.setVisible(False)
        self.progress_bar.setValue(0)
        self.progress_pct_label.setVisible(False)
        self.progress_time_label.setVisible(False)

        # pick a new session folder
        selected = QFileDialog.getExistingDirectory(
            self, "Select the folder that contains the 'lights' directory",
            self.cwd, QFileDialog.Option.ShowDirsOnly)
        if selected:
            self._set_working_dir(selected)

        self.siril.log(
            "Pipeline reset — settings, previews, and undo history "
            "cleared.", LogColor.BLUE)

    # ------------------------------------------------------------- keyboard

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._cancel_pending_crop():
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape and self._cancel_ann_pick_mode():
            event.accept()
            return
        super().keyPressEvent(event)

    # ---------------------------------------------------------------- closing

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            QMessageBox.warning(self, "Processing", "A stage is still running. "
                                "Please wait for it to finish before closing.")
            event.ignore()
            return
        reply = QMessageBox.question(
            self, "Close S30 Pro Pipeline",
            "Close the pipeline window?\n\n"
            "Use \"Save File...\" first if you want to keep the current "
            "image — the image already loaded in Siril itself is not "
            "affected by closing this window.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            event.ignore()
            return
        try:
            self.siril.disconnect()
        except Exception:
            pass
        # Only now is it safe to remove cached intermediate results (e.g.
        # the StarNet star/starless split) — they're kept on disk for the
        # whole session so palette re-runs don't pay for StarNet twice.
        try:
            if getattr(self, "_temp_dir", None) and os.path.isdir(self._temp_dir):
                shutil.rmtree(self._temp_dir, ignore_errors=True)
        except Exception:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    win = UnifiedPipelineWindow()
    if getattr(win, "initialization_successful", False):
        win.show()
        sys.exit(app.exec())
    sys.exit(0)


if __name__ == "__main__":
    main()
