"""Preprocess (Smart Telescope Stacking) stage mixin for UnifiedPipelineWindow."""

import os
import math
import random
import shutil
from datetime import datetime

import numpy as np
import cv2
from astropy.io import fits

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QGridLayout,
    QGroupBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSpinBox,
    QVBoxLayout,
)

import sirilpy as s
from sirilpy import LogColor

from s30pro_pipeline.constants import (
    TELESCOPES, FILTER_OPTIONS_MAP, FILTER_COMMANDS_MAP,
    SPCC_SENSOR_MAP,
)
from s30pro_pipeline.bortle import sqm_to_bortle, ZP_REF_50MM, BORTLE_NAMES
from s30pro_pipeline.veralux_stretch import VeraLuxCore


class Stage1Mixin:
    def _build_stage1(self):
        box, v = self._stage_box(1, "Preprocess — Smart Telescope Stacking")
        self.stage1_box = box

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)

        g.addWidget(QLabel("Telescope:"), 0, 0)
        self.telescope_combo = QComboBox()
        self.telescope_combo.addItems(TELESCOPES)
        self.telescope_combo.setCurrentText("ZWO Seestar S30 Pro")
        self.telescope_combo.currentTextChanged.connect(self._on_telescope_changed)
        g.addWidget(self.telescope_combo, 0, 1, 1, 3)

        g.addWidget(QLabel("Filter:"), 1, 0)
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(FILTER_OPTIONS_MAP["ZWO Seestar S30 Pro"])
        self.filter_combo.setCurrentText("LP (Narrowband)")
        g.addWidget(self.filter_combo, 1, 1, 1, 3)
        v.addLayout(g)

        cal = QHBoxLayout()
        cal.setSpacing(14)
        cal.addWidget(QLabel("Calibration:"))
        self.darks_checkbox = QCheckBox("Darks")
        self.flats_checkbox = QCheckBox("Flats")
        self.biases_checkbox = QCheckBox("Biases")
        for c in (self.darks_checkbox, self.flats_checkbox, self.biases_checkbox):
            cal.addWidget(c)
        cal.addStretch()
        v.addLayout(cal)

        # 2 columns (label, control) instead of a wide 5-column row — each
        # checkbox gets its own full-width row, with its numeric field(s)
        # stacked as label/control pairs right below it. Keeps every row
        # readable at the ~1/3-window-width target with no wrapping.
        g2 = QGridLayout()
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(8)
        g2.setColumnStretch(1, 1)

        self.drizzle_checkbox = QCheckBox("Drizzle")
        g2.addWidget(self.drizzle_checkbox, 0, 0, 1, 2)
        g2.addWidget(QLabel("Scale:"), 1, 0)
        self.drizzle_amount = QDoubleSpinBox()
        self.drizzle_amount.setRange(1.0, 3.0)
        self.drizzle_amount.setSingleStep(0.1)
        self.drizzle_amount.setValue(1.0)
        g2.addWidget(self.drizzle_amount, 1, 1)
        g2.addWidget(QLabel("Pixfrac:"), 2, 0)
        self.pixel_fraction = QDoubleSpinBox()
        self.pixel_fraction.setRange(0.1, 2.0)
        self.pixel_fraction.setSingleStep(0.05)
        self.pixel_fraction.setValue(1.0)
        g2.addWidget(self.pixel_fraction, 2, 1)

        self.feather_checkbox = QCheckBox("Feather")
        self.feather_checkbox.setToolTip(
            "Blends frame/panel edges over this many pixels when stacking.\n"
            "Together with per-frame background removal, this is the fix for\n"
            "visible strips at mosaic seams — try 100–300 px for mosaics.\n"
            "Only applies to the Average (rejection) stacking method below\n"
            "(Siril requires -maximize framing for this, which Median/Sum\n"
            "don't support).")
        g2.addWidget(self.feather_checkbox, 3, 0, 1, 2)
        g2.addWidget(QLabel("Amount:"), 4, 0)
        self.feather_amount = QSpinBox()
        self.feather_amount.setRange(5, 2000)
        self.feather_amount.setValue(20)
        g2.addWidget(self.feather_amount, 4, 1)

        self.overlap_norm_checkbox = QCheckBox("Normalize on overlaps")
        self.overlap_norm_checkbox.setToolTip(
            "Computes stack normalization from only the overlapping regions\n"
            "between tiles/frames, instead of whole images (Siril's\n"
            "-overlap_norm, requires -maximize framing — used with the\n"
            "Average (rejection) stacking method below only; Median/Sum\n"
            "don't support -maximize).\n"
            "Helps when tiles have very different content (e.g. one mostly\n"
            "nebula, another mostly blank sky) and a seam still shows up\n"
            "with plain normalization. Slower to compute — try without it\n"
            "first, enable only if seams persist.")
        g2.addWidget(self.overlap_norm_checkbox, 5, 0, 1, 2)
        v.addLayout(g2)

        # stacking method
        sm = QHBoxLayout()
        sm.setSpacing(10)
        sm.addWidget(QLabel("Stacking method:"))
        self.stack_method_combo = QComboBox()
        self.stack_method_combo.addItems(
            ["Average (rejection)", "Median (Milky Way Mode)", "Sum",
             "Comet Stack"])
        stack_method_tooltips = [
            "Average (rejection): the usual choice for deep-sky — sigma-clip\n"
            "rejection (3/3) with normalization and weighting. Registered\n"
            "frames are padded to their union/max footprint before stacking\n"
            "(widest possible field of view).",
            "Median: no rejection settings, more robust than sigma-clip at\n"
            "erasing something that only shows up in a few frames (e.g. a\n"
            "satellite or plane trail) — ZWO's own recommendation for wide,\n"
            "trail-prone shots like Seestar's Milky Way Mode. Siril doesn't\n"
            "support padding mismatched frame sizes for Median, so frames\n"
            "are cropped to their common overlap instead — the result's\n"
            "field of view may be a bit smaller than Average's.",
            "Sum: no normalization or rejection at all — for planetary/lucky\n"
            "imaging stacks, not typically useful for deep-sky or Milky Way.\n"
            "Also cropped to the common overlap, like Median.",
            "Comet Stack: produces two separate stacks from the same subs —\n"
            "one registered on the stars, one on the comet's own motion —\n"
            "then combines them so both look sharp. Needs two brief manual\n"
            "steps in Siril's own window partway through (comet picking,\n"
            "then Star Recomposition) since neither has a console command.\n"
            "Automatically disables Remove Background and Remove Stars\n"
            "below (this mode already does both as part of its own\n"
            "workflow).",
        ]
        # Per-item tooltips (shown while hovering an option in the open
        # dropdown list), in addition to the combo's own tooltip below.
        for i, tip in enumerate(stack_method_tooltips):
            self.stack_method_combo.setItemData(
                i, tip, Qt.ItemDataRole.ToolTipRole)
        self.stack_method_combo.setToolTip("\n".join(stack_method_tooltips))
        sm.addWidget(self.stack_method_combo, 1)
        v.addLayout(sm)

        # stacking weights (Average method only)
        wt = QHBoxLayout()
        wt.setSpacing(10)
        self.weighting_checkbox = QCheckBox("Stack weighting")
        self.weighting_checkbox.setToolTip(
            "Weight frames during stacking by quality metric. Only applies\n"
            "to the Average (rejection) stacking method above.")
        self.weighting_checkbox.setChecked(True)
        wt.addWidget(self.weighting_checkbox)
        self.weighting_method_combo = QComboBox()
        self.weighting_method_combo.addItems(
            ["Noise", "Number of Stars", "Weighted FWHM"])
        self.weighting_method_combo.setCurrentText("Weighted FWHM")
        wt.addWidget(self.weighting_method_combo, 1)
        v.addLayout(wt)

        # Comet Stack-only controls: rejection sigmas for the two final
        # stacks (comet sequence + star sequence), and the degree/samples
        # for the whole-sequence background removal that's part of this
        # mode's own workflow (step 3 in _exec_stage1_comet_stack) — same
        # widget style as the Siril subsky controls in Remove Background
        # (stage_bge.py) so it feels consistent with the rest of the app.
        self.comet_settings_box = QGroupBox("Comet Stack settings")
        cs_v = QVBoxLayout(self.comet_settings_box)
        cs_v.setSpacing(8)
        cs_info = QLabel(
            "Produces a comet-sharp stack and a stars-sharp stack from "
            "the same subs, then pauses twice for quick manual steps in "
            "Siril's own window (comet picking, then Star Recomposition) "
            "that have no console-command equivalent. Remove Background "
            "and Remove Stars below are disabled — this mode already "
            "does both as part of its own workflow.")
        cs_info.setObjectName("SubHeader")
        cs_info.setWordWrap(True)
        cs_v.addWidget(cs_info)
        cs_g = QGridLayout()
        cs_g.setHorizontalSpacing(10)
        cs_g.setVerticalSpacing(8)
        cs_g.setColumnStretch(1, 1)
        cs_g.setColumnStretch(3, 1)
        cs_g.addWidget(QLabel("Stack sigma low:"), 0, 0)
        self.comet_sigma_low_spin = QDoubleSpinBox()
        self.comet_sigma_low_spin.setRange(0.1, 10.0)
        self.comet_sigma_low_spin.setSingleStep(0.5)
        self.comet_sigma_low_spin.setValue(5.0)
        self.comet_sigma_low_spin.setToolTip(
            "Rejection sigma (low side) used for both the comet stack and\n"
            "the star stack (Siril's `stack ... rej low high`). 5/5 is a\n"
            "reasonable default; other combinations like 2/5 or 3/5 also\n"
            "work well on comet data — experiment if the result has too\n"
            "much or too little rejection.")
        cs_g.addWidget(self.comet_sigma_low_spin, 0, 1)
        cs_g.addWidget(QLabel("Stack sigma high:"), 0, 2)
        self.comet_sigma_high_spin = QDoubleSpinBox()
        self.comet_sigma_high_spin.setRange(0.1, 10.0)
        self.comet_sigma_high_spin.setSingleStep(0.5)
        self.comet_sigma_high_spin.setValue(5.0)
        self.comet_sigma_high_spin.setToolTip(
            self.comet_sigma_low_spin.toolTip())
        cs_g.addWidget(self.comet_sigma_high_spin, 0, 3)
        cs_g.addWidget(QLabel("Bkg degree:"), 1, 0)
        self.comet_subsky_degree_spin = QSpinBox()
        self.comet_subsky_degree_spin.setRange(1, 4)
        self.comet_subsky_degree_spin.setValue(1)
        self.comet_subsky_degree_spin.setToolTip(
            "Polynomial degree for the whole-sequence background removal\n"
            "(seqsubsky) this mode runs on the star-registered sequence,\n"
            "before star removal. 1 (linear) is the default.")
        cs_g.addWidget(self.comet_subsky_degree_spin, 1, 1)
        cs_g.addWidget(QLabel("Bkg samples:"), 1, 2)
        self.comet_subsky_samples_spin = QSpinBox()
        self.comet_subsky_samples_spin.setRange(4, 100)
        self.comet_subsky_samples_spin.setValue(20)
        self.comet_subsky_samples_spin.setToolTip(
            "Number of background sample points for the whole-sequence\n"
            "seqsubsky above.")
        cs_g.addWidget(self.comet_subsky_samples_spin, 1, 3)
        cs_v.addLayout(cs_g)
        v.addWidget(self.comet_settings_box)

        def sync_stack_method_enabled():
            method = self.stack_method_combo.currentText()
            is_avg = method == "Average (rejection)"
            is_comet = method == "Comet Stack"
            self.weighting_checkbox.setEnabled(is_avg)
            self.weighting_method_combo.setEnabled(
                is_avg and self.weighting_checkbox.isChecked())
            # Feather and Normalize-on-overlaps both require Siril's
            # -maximize framing, which is only used with Average — Median
            # and Sum use -framing=min (common-overlap crop) instead, so
            # these two don't apply there.
            self.feather_checkbox.setEnabled(is_avg)
            self.feather_amount.setEnabled(
                is_avg and self.feather_checkbox.isChecked())
            self.overlap_norm_checkbox.setEnabled(is_avg)
            self.comet_settings_box.setVisible(is_comet)
            self._sync_comet_bge_stars_disable(is_comet)
        self.stack_method_combo.currentTextChanged.connect(
            lambda _t: sync_stack_method_enabled())
        self.weighting_checkbox.toggled.connect(
            lambda _c: sync_stack_method_enabled())
        self.feather_checkbox.toggled.connect(
            lambda _c: sync_stack_method_enabled())
        sync_stack_method_enabled()

        # mosaic / registration quality
        # 2-column (label, control) grid instead of one wide row — the
        # "Per-frame background" checkbox label alone is long enough to
        # crowd out both spinboxes at ~1/3-window width in a single row.
        mos = QGridLayout()
        mos.setHorizontalSpacing(10)
        mos.setVerticalSpacing(8)
        mos.setColumnStretch(1, 1)
        mos.addWidget(QLabel("Distortion order:"), 0, 0)
        self.disto_order_spin = QSpinBox()
        self.disto_order_spin.setRange(1, 5)
        self.disto_order_spin.setValue(4)
        self.disto_order_spin.setToolTip(
            "SIP polynomial order used by the sequence plate solve to model\n"
            "lens distortion (needs the Gaia astrometry catalog).\n"
            "3–4 suits wide fields like smart telescopes; drop to 2–3 if\n"
            "solves fail on star-poor panels, raise to 5 only for extreme\n"
            "corner distortion. Default: 4.")
        mos.addWidget(self.disto_order_spin, 0, 1)
        self.seqsubsky_checkbox = QCheckBox("Per-frame background (mosaic seams)")
        self.seqsubsky_checkbox.setToolTip(
            "Runs seqsubsky (polynomial gradient removal, degree set below)\n"
            "on every calibrated sub before registration. Each mosaic panel\n"
            "has its own sky level/gradient — equalizing them BEFORE\n"
            "stacking is the main fix for bright strips at panel seams.\n"
            "Recommended for mosaics; harmless (slightly slower) for\n"
            "single-panel fields.")
        self.seqsubsky_checkbox.setChecked(True)
        mos.addWidget(self.seqsubsky_checkbox, 1, 0, 1, 2)
        mos.addWidget(QLabel("Degree:"), 2, 0)
        self.seqsubsky_degree_spin = QSpinBox()
        self.seqsubsky_degree_spin.setRange(1, 4)
        self.seqsubsky_degree_spin.setValue(1)
        self.seqsubsky_degree_spin.setToolTip(
            "Polynomial degree for the per-frame background removal above.\n"
            "1 (linear) is the default and suits a simple sky tilt. Raise to\n"
            "2–4 if a seam persists with degree 1 — this usually means the\n"
            "per-panel gradient is more complex than a flat tilt (e.g.\n"
            "radial vignetting-like falloff). Higher degrees are slower and\n"
            "can overfit on frames with little background to sample, so\n"
            "only raise it if you actually see the fix helping.")
        mos.addWidget(self.seqsubsky_degree_spin, 2, 1)
        v.addLayout(mos)

        # 2-per-row instead of 3-in-a-row — "SPCC color calibration" +
        # "Compression (Rice)" + "Clean up temp files" together are too
        # wide for a single row at ~1/3-window width.
        misc = QGridLayout()
        misc.setHorizontalSpacing(14)
        misc.setVerticalSpacing(6)
        self.spcc_checkbox = QCheckBox("SPCC color calibration")
        self.spcc_checkbox.setChecked(True)
        misc.addWidget(self.spcc_checkbox, 0, 0)
        self.compression_checkbox = QCheckBox("Compression (Rice)")
        self.compression_checkbox.setToolTip(
            "Compress intermediate FITS files to save disk space during processing")
        self.compression_checkbox.setChecked(True)
        misc.addWidget(self.compression_checkbox, 0, 1)
        self.cleanup_checkbox = QCheckBox("Clean up temp files")
        self.cleanup_checkbox.setChecked(True)
        misc.addWidget(self.cleanup_checkbox, 1, 0)
        v.addLayout(misc)

        combine_box, combine_v, self.combine_toggle_btn = self._collapsible_section(
            "Combine with existing master")
        combine_info = QLabel(
            "For when you already have a stacked FITS from an earlier "
            "session but the raw subs weren't kept. After stacking the "
            "lights above into a new master, this registers it against "
            "the file you pick here and combines the two with Siril's "
            "-weight=nbstack, so a master built from more subs "
            "correctly outweighs one built from fewer — needs the "
            "STACKCNT header Siril writes into every master it produces "
            "(use the override below if that file is missing it). Your "
            "original file is never modified.")
        combine_info.setObjectName("SubHeader")
        combine_info.setWordWrap(True)
        combine_v.addWidget(combine_info)

        self.combine_master_checkbox = QCheckBox("Combine with existing master")
        combine_v.addWidget(self.combine_master_checkbox)

        combine_path_row = QHBoxLayout()
        combine_path_row.setSpacing(8)
        self.combine_master_path_edit = QLineEdit()
        self.combine_master_path_edit.setReadOnly(True)
        self.combine_master_path_edit.setPlaceholderText("No file selected")
        combine_path_row.addWidget(self.combine_master_path_edit, 1)
        self.combine_master_browse_btn = QPushButton("Browse...")
        self.combine_master_browse_btn.clicked.connect(
            self._on_browse_combine_master)
        combine_path_row.addWidget(self.combine_master_browse_btn)
        combine_v.addLayout(combine_path_row)

        combine_subcount_row = QHBoxLayout()
        combine_subcount_row.setSpacing(8)
        combine_subcount_row.addWidget(QLabel("Sub count override:"))
        self.combine_master_subcount_spin = QSpinBox()
        self.combine_master_subcount_spin.setRange(0, 100000)
        self.combine_master_subcount_spin.setValue(0)
        self.combine_master_subcount_spin.setToolTip(
            "0 = trust whatever STACKCNT is already in that file's FITS "
            "header (if missing, Siril treats it as a single frame — "
            "likely under-weighting it badly). Set this if you know how "
            "many subs actually went into that master; it's written "
            "into a copy of the header before combining, never into "
            "your original file.")
        combine_subcount_row.addWidget(self.combine_master_subcount_spin)
        combine_subcount_row.addStretch()
        combine_v.addLayout(combine_subcount_row)

        v.addWidget(combine_box)

        def _on_combine_toggle(checked):
            for w in (self.combine_master_path_edit,
                     self.combine_master_browse_btn,
                     self.combine_master_subcount_spin):
                w.setEnabled(checked)
        self.combine_master_checkbox.toggled.connect(_on_combine_toggle)
        _on_combine_toggle(False)

        # local Gaia catalog status
        astro = "✅" if self.gaia_available else "❌"
        photo = "✅" if self.gaia_photo_available else "❌"
        gaia_label = QLabel(
            f"Local Gaia — astrometry (plate solve): {astro}    "
            f"photometry (SPCC): {photo}")
        gaia_label.setObjectName("SubHeader")
        gaia_label.setToolTip(
            "Local Gaia catalogues are configured in Siril Preferences → Astrometry.\n"
            "Without the astrometry catalogue, mosaics fall back to star registration.\n"
            "Without the photometry catalogue, SPCC uses the online catalogue.")
        v.addWidget(gaia_label)

        self.files_label = QLabel("")
        self.files_label.setObjectName("SubHeader")
        v.addWidget(self.files_label)

        row, self.stage1_run = self._run_row(lambda: self._launch([self._exec_stage1]))
        v.addLayout(row)
        return box

    def _sync_comet_bge_stars_disable(self, is_comet):
        """Comet Stack mode already removes background (whole-sequence
        seqsubsky) and stars (seqstarnet) as part of its own workflow —
        the standalone Remove Background / Remove Stars stages would be
        redundant (background already flat) or actively wrong (stars
        already gone) if left enabled afterward. Mirrors the same
        auto-disable-with-tooltip / restore-on-switch-away pattern this
        file already uses for feathering / overlap-norm / stack
        weighting when Median (Milky Way Mode) is selected (see
        sync_stack_method_enabled above and the 1.35.0/1.36.0
        CHANGELOG entries) — except here it reaches into two *other*
        stage cards (BgeMixin's stage2_box, StarsMixin's
        stage_stars_box) rather than just this stage's own controls.

        Guarded for call order: _build_stage1 runs before
        _build_stage2/_build_stage_stars build stage2_box/
        stage_stars_box (see _build_ui), so the very first call — made
        from _build_stage1 itself while wiring up the stack-method
        combo — has to no-op rather than raise AttributeError. By the
        time a user can actually switch to Comet Stack, the whole UI is
        built and this runs normally."""
        if not hasattr(self, "stage2_box") or not hasattr(
                self, "stage_stars_box"):
            return
        bge_tip = ("Disabled while Comet Stack is selected — that mode "
                   "already removes background from the whole sequence "
                   "(seqsubsky) as part of its own workflow. Switch "
                   "Stacking method away from Comet Stack to re-enable.")
        stars_tip = ("Disabled while Comet Stack is selected — that mode "
                     "already removes stars from the whole sequence "
                     "(seqstarnet) as part of its own workflow. Switch "
                     "Stacking method away from Comet Stack to re-enable.")
        if is_comet:
            if not getattr(self, "_comet_disabled_bge_stars", False):
                self._comet_prev_bge_checked = self.stage2_box.isChecked()
                self._comet_prev_stars_checked = \
                    self.stage_stars_box.isChecked()
                self._comet_disabled_bge_stars = True
            self.stage2_box.setChecked(False)
            self.stage2_box.setEnabled(False)
            self.stage2_box.setToolTip(bge_tip)
            self.stage_stars_box.setChecked(False)
            self.stage_stars_box.setEnabled(False)
            self.stage_stars_box.setToolTip(stars_tip)
        elif getattr(self, "_comet_disabled_bge_stars", False):
            self.stage2_box.setEnabled(True)
            self.stage2_box.setToolTip("")
            self.stage2_box.setChecked(self._comet_prev_bge_checked)
            self.stage_stars_box.setEnabled(True)
            self.stage_stars_box.setToolTip("")
            self.stage_stars_box.setChecked(self._comet_prev_stars_checked)
            self._comet_disabled_bge_stars = False

    def _on_browse_combine_master(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select existing master FITS", self.cwd,
            "FITS files (*.fits *.fit *.fits.fz *.fit.fz);;All files (*)")
        if path:
            self.combine_master_path_edit.setText(path)
    # Seestar's wide-angle camera (used by "Median (Milky Way Mode)"
    # stacking) is a physically different lens/sensor pair from the main
    # tele camera: 6mm focal length, Sony IMX586 sensor binned down to
    # ~1.7 micron effective pixel size at the 3840x2160 output resolution
    # (vs. 160mm / 2.9 micron for the tele camera). Some firmware versions
    # write incorrect or tele-camera-inherited FOCALLEN/XPIXSZ values into
    # wide-camera FITS headers, which is enough to make plate solving fail
    # outright even though the field itself would otherwise solve fine.
    # Overriding with the wide camera's real values via platesolve's own
    # -focal=/-pixelsize= arguments (which take precedence over whatever
    # is in the header) sidesteps that without needing a UI control.
    MILKYWAY_FOCAL_MM = 6.0
    MILKYWAY_PIXEL_UM = 1.7

    def _milkyway_solve_args(self):
        """Extra platesolve/seqplatesolve arguments to pass when the
        current run is using Milky Way Mode (wide-camera) stacking, so the
        solver uses the wide camera's real optics instead of a possibly
        wrong/inherited header value. Empty list otherwise."""
        if self.stack_method_combo.currentText() == "Median (Milky Way Mode)":
            return [f"-focal={self.MILKYWAY_FOCAL_MM}",
                    f"-pixelsize={self.MILKYWAY_PIXEL_UM}"]
        return []

    def _exec_stage1(self, progress):
        progress("Preprocess: starting...", 0.01)
        siril = self.siril
        cwd = self.cwd
        # Reset each run so a name from a previous, combine-enabled run
        # doesn't leak into this one if combine is now off (see
        # _save_result_named).
        self._combine_applied_this_run = False
        lights_dir = os.path.join(cwd, "lights")
        if not os.path.isdir(lights_dir):
            raise RuntimeError("No 'lights' directory found in the working directory.")

        # A held star layer from a previous Remove Stars run belongs to that
        # earlier stack, not the fresh one Preprocess is about to produce —
        # re-stacking makes a different image, so the old stars no longer
        # correspond to anything. Discard it (with a warning) rather than
        # silently carrying it forward to be composited onto the wrong image.
        if getattr(self, "held_stars", None) is not None:
            self.held_stars = None
            siril.log(
                "Preprocess re-run: discarded a star layer held back from "
                "an earlier Remove Stars run (it belonged to the previous "
                "stack, not this new one). Re-run Remove Stars after "
                "Preprocess finishes if you need it again.", LogColor.SALMON)

        # grab a raw sub for the 'before' preview
        before_arr = self._load_raw_light_preview(lights_dir)

        # estimate sky brightness / Bortle scale from 2-3 random raw subs
        # (never blocks stacking if it fails — just omitted from the info bar)
        progress("Preprocess: estimating sky brightness (Bortle, sample subs)...", 0.02)
        try:
            self.estimated_bortle = self._estimate_bortle_scale(lights_dir)
            if self.estimated_bortle:
                siril.log(
                    f"Estimated sky: Bortle {self.estimated_bortle['bortle']} "
                    f"({self.estimated_bortle['name']}), "
                    f"~{self.estimated_bortle['sqm']:.2f} mag/arcsec² "
                    f"[{self.estimated_bortle['n_samples']} sample(s), est.]",
                    LogColor.BLUE)
        except Exception as e:
            siril.log(f"Bortle estimate skipped: {e}", LogColor.SALMON)
            self.estimated_bortle = None

        # scan DATE-OBS across all lights → capture date range for the info bar
        try:
            self.date_range = self._scan_capture_dates(lights_dir)
        except Exception:
            self.date_range = None

        # clean previous runs
        proc_dir = os.path.join(cwd, "process")
        if os.path.isdir(proc_dir):
            shutil.rmtree(proc_dir, ignore_errors=True)

        siril.cmd("close")
        siril.cmd("cd", f'"{cwd}"')
        if self.compression_checkbox.isChecked():
            siril.cmd("setcompress", "1 -type=rice 16")
        else:
            siril.cmd("setcompress", "0")

        use_darks = self.darks_checkbox.isChecked()
        use_flats = self.flats_checkbox.isChecked()
        use_biases = self.biases_checkbox.isChecked()
        drizzle = self.drizzle_checkbox.isChecked()
        drizzle_amount = round(self.drizzle_amount.value(), 2)
        pixfrac = round(self.pixel_fraction.value(), 2)
        feather = self.feather_checkbox.isChecked()
        feather_amount = self.feather_amount.value()
        cleanup = self.cleanup_checkbox.isChecked()

        # ---- calibration masters
        for name, use in (("biases", use_biases), ("flats", use_flats),
                          ("darks", use_darks)):
            if use:
                progress(f"Preprocess: stacking {name}...", 0.05)
                self._convert_dir(name)
                self._stack_calibration(name)

        # ---- lights
        progress("Preprocess: converting lights...", 0.15)
        self._convert_dir("lights")
        seq_name = "lights_"

        progress("Preprocess: calibrating lights...", 0.25)
        cmd = ["calibrate", seq_name]
        if use_darks and self._master_exists("darks"):
            cmd += ["-dark=darks_stacked", "-cc=dark"]
        if use_flats and self._master_exists("flats"):
            cmd += ["-flat=flats_stacked"]
        if use_biases and self._master_exists("biases"):
            cmd += ["-bias=biases_stacked"]
        cmd += ["-cfa", "-equalize_cfa"]
        if not drizzle:
            cmd.append("-debayer")
        siril.cmd(*cmd)
        if cleanup:
            self._clean_process(seq_name)
        seq_name = "pp_" + seq_name

        # ---- per-frame background equalization (the main mosaic-seam fix:
        # each panel carries its own sky level/gradient; removing a simple
        # degree-1 background from every sub BEFORE registration stops
        # bright strips appearing where panels overlap)
        if self.seqsubsky_checkbox.isChecked():
            progress("Preprocess: per-frame background removal (seqsubsky)...",
                     0.33)
            try:
                siril.cmd("seqsubsky", seq_name,
                          str(self.seqsubsky_degree_spin.value()))
                if cleanup:
                    self._clean_process(seq_name)
                seq_name = "bkg_" + seq_name
            except (s.DataError, s.CommandError, s.SirilError) as e:
                siril.log(f"seqsubsky failed (continuing without it): {e}",
                          LogColor.SALMON)

        stack_method = self.stack_method_combo.currentText()

        if stack_method == "Comet Stack":
            # Comet Stack replaces everything from here through stacking
            # with its own two-registration workflow (star registration,
            # whole-sequence background/star removal, a spliced-in
            # registration patch, comet registration + Star Recomposition
            # — both GUI-only manual steps) — see
            # _exec_stage1_comet_stack for the full sequence and why. It
            # ends with Siril's currently-loaded image already being the
            # user's accepted, recomposited result, and its own
            # `siril.cmd("cd", "../")`, matching what the rest of this
            # method (combine-with-master / SPCC / save, below) expects.
            self._exec_stage1_comet_stack(progress, seq_name)
        else:
            # ---- registration (plate solve for mosaics if Gaia is
            # available, falling back to ordinary star-based registration
            # if it fails — e.g. "Image ... did not solve", expected for
            # very wide fields like Seestar's Milky Way Mode that span far
            # more sky than Siril's astrometric solver reliably handles
            # per-frame. Same fallback pattern as "Combine with existing
            # master" below.)
            plate_solved = False
            if self.gaia_available:
                progress("Preprocess: plate solving sequence...", 0.4)
                try:
                    siril.cmd("seqplatesolve", seq_name, "-nocache", "-force",
                              "-disto=ps_distortion",
                              f"-order={self.disto_order_spin.value()}",
                              "-radius=25", *self._milkyway_solve_args())
                    plate_solved = True
                except (s.DataError, s.CommandError, s.SirilError) as e:
                    siril.log(
                        f"Preprocess: plate-solve registration failed ({e}), "
                        "falling back to star-based registration.",
                        LogColor.SALMON)
            if not plate_solved:
                progress("Preprocess: registering (2-pass)...", 0.4)
                reg = ["register", seq_name, "-2pass"]
                if drizzle:
                    reg += ["-drizzle", f"-scale={drizzle_amount}", f"-pixfrac={pixfrac}"]
                siril.cmd(*reg)

            # Siril's "-maximize" framing (pad every frame to the union/max
            # canvas at stack time) only works with the Average+rejection
            # stack method — Median/Sum reject it outright ("Cannot upscale
            # or maximize framing with median stacking. Disabling"), and once
            # disabled, frames of differing sizes then abort stacking with
            # "input images have different sizes". So for Median/Sum, crop
            # every registered frame down to their common overlap instead
            # (-framing=min) — this guarantees uniform size without needing
            # stack's own -maximize at all. Trade-off: the Median/Sum result
            # only covers the overlap area, not the full union every frame
            # touched (Average still gets the wider union canvas).
            apply_framing = "max" if stack_method == "Average (rejection)" else "min"

            progress("Preprocess: applying registration...", 0.55)
            apply_cmd = ["seqapplyreg", seq_name, "-kernel=square",
                         f"-framing={apply_framing}"]
            if drizzle:
                apply_cmd += ["-drizzle", f"-scale={drizzle_amount}",
                              f"-pixfrac={pixfrac}"]
            siril.cmd(*apply_cmd)
            if cleanup:
                self._clean_process(seq_name)
            seq_name = "r_" + seq_name

            # ---- stacking (compression is always off for the final stack)
            progress("Preprocess: stacking...", 0.7)
            siril.cmd("setcompress", "0")
            if stack_method == "Sum":
                # Sum has no normalization/rejection/weighting (matches Siril's
                # own restriction — meant for planetary/lucky imaging stacks).
                stack_cmd = ["stack", seq_name, "sum", "-filter-included",
                             "-out=result"]
            elif stack_method == "Median (Milky Way Mode)":
                # No -maximize (unsupported here — frames are already
                # uniform size via -framing=min above), no weighting, and no
                # -feather/-overlap_norm (both require -maximize per Siril).
                stack_cmd = ["stack", seq_name, "med", "-norm=addscale",
                             "-output_norm", "-rgb_equal",
                             "-filter-included", "-32b", "-out=result"]
            else:  # Average (rejection) — the default
                stack_cmd = ["stack", seq_name, " rej 3 3", "-norm=addscale",
                             "-output_norm", "-rgb_equal", "-maximize",
                             "-filter-included", "-32b", "-out=result"]
                if self.weighting_checkbox.isChecked():
                    wmap = {"Number of Stars": "nbstars",
                            "Weighted FWHM": "wfwhm", "Noise": "noise"}
                    stack_cmd.append(
                        "-weight="
                        f"{wmap[self.weighting_method_combo.currentText()]}")
                if feather:
                    stack_cmd.append(f"-feather={feather_amount}")
                if self.overlap_norm_checkbox.isChecked():
                    stack_cmd.append("-overlap_norm")
            siril.cmd(*stack_cmd)
            if cleanup:
                self._clean_process(seq_name)

            siril.cmd("load", "result")
            siril.cmd("cd", "../")

        # ---- combine with an existing master from an earlier session
        # (no raw subs kept) — must happen before SPCC/save below so the
        # rest of the pipeline (and the saved file) sees the combined
        # result, not just this run's own stack.
        if (self.combine_master_checkbox.isChecked()
                and self.combine_master_path_edit.text().strip()):
            self._combine_with_existing_master(progress)

        # ---- SPCC
        if self.spcc_checkbox.isChecked():
            progress("Preprocess: plate solving result + SPCC...", 0.85)
            solved = False
            mw_args = self._milkyway_solve_args()
            is_milkyway = (self.stack_method_combo.currentText()
                           == "Median (Milky Way Mode)")
            try:
                siril.cmd("platesolve", "-force", *mw_args)
                solved = True
            except (s.DataError, s.CommandError, s.SirilError) as e:
                # Siril's own solver ("Generic Error" and similar) is known
                # to fail on some stacked Seestar images even though the
                # exact same image solves fine on nova.astrometry.net or a
                # local Astrometry.net install — likely due to onboard-
                # stacking edge artifacts confusing its star matcher. Retry
                # once with -localasnet (local Astrometry.net solve-field)
                # before giving up, matching the same "try the robust
                # method, then fall back" pattern used for registration
                # above. Requires a local Astrometry.net install (ansvr on
                # Windows, `brew install astrometry-net` on Mac) with index
                # files covering the field — if that isn't installed,
                # -localasnet will fail too and we fall through cleanly.
                siril.log(
                    f"Preprocess: plate-solve failed ({e}), retrying with "
                    "local Astrometry.net (-localasnet)...", LogColor.SALMON)
                try:
                    siril.cmd("platesolve", "-force", "-localasnet",
                              *mw_args)
                    solved = True
                except (s.DataError, s.CommandError, s.SirilError) as e2:
                    if is_milkyway:
                        # At Milky Way Mode's ~60-70 deg field of view, even
                        # -localasnet's header-hinted near-search (using
                        # FOCALLEN/XPIXSZ and the header's RA/Dec as a
                        # starting guess, searching only a small cone around
                        # it) reliably fails — confirmed by hand: the same
                        # field only solved once asked to search completely
                        # blindly. -blindpos/-blindres tell Astrometry.net
                        # to ignore those hints and search the whole sky at
                        # any scale, which is slower but far more robust for
                        # a field this wide. Also needs wide-scale index
                        # files (index-4116 through 4119 cover this FOV;
                        # see download_wide_field_index.sh) — without them
                        # this will fail just as fast as the hinted attempt.
                        siril.log(
                            f"Preprocess: -localasnet failed ({e2}), "
                            "retrying blindly (-blindpos -blindres) — "
                            "Milky Way Mode's wide field often needs a full "
                            "blind solve instead of a header-hinted one...",
                            LogColor.SALMON)
                        try:
                            siril.cmd("platesolve", "-force", "-localasnet",
                                      "-blindpos", "-blindres", *mw_args)
                            solved = True
                        except (s.DataError, s.CommandError,
                                s.SirilError) as e3:
                            siril.log(
                                f"Blind Astrometry.net solve also failed "
                                f"({e3}). SPCC and the Annotate stage need "
                                "a plate-solve solution — make sure the "
                                "wide-field index files (index-4116 to "
                                "4119) are installed and that Astrometry.net "
                                "can find them (astrometry.cfg's add_path).",
                                LogColor.SALMON)
                    else:
                        siril.log(
                            f"Astrometry.net fallback also failed ({e2}). "
                            "SPCC and the Annotate stage need a plate-solve "
                            "solution — if this keeps happening, install a "
                            "local Astrometry.net solver (solve-field) with "
                            "matching index files to enable -localasnet.",
                            LogColor.SALMON)
            if solved:
                try:
                    self._run_spcc()
                except (s.DataError, s.CommandError, s.SirilError) as e:
                    siril.log(f"SPCC failed (continuing): {e}",
                              LogColor.SALMON)

        # ---- save stacked result with a descriptive name
        file_name = self._save_result_named()
        progress("Preprocess: done.", 1.0)

        after_arr = self._get_current_image()
        self._store_snapshot(0, before_arr, after_arr,
                             before_linear=True, after_linear=True)
        siril.log(f"Preprocess complete: {file_name}", LogColor.GREEN)

    # ------------------------------------------------------- Comet Stack

    def _exec_stage1_comet_stack(self, progress, seq_name):
        """Comet Stack's front-portion of Preprocess: two separate
        registrations (one on the stars, one on the comet's own motion)
        from the same calibrated sequence, producing a comet-sharp stack
        and a stars-sharp stack that get recomposited into one image —
        see CHANGELOG 1.45.0 for the full rationale.

        Called from _exec_stage1 in place of its usual plate-solve/
        register/seqapplyreg/stack block, once `seq_name` is whatever
        calibrated (and optionally per-frame-background-corrected)
        sequence is ready to register — same cwd (self.cwd/process) as
        the rest of _exec_stage1. Ends with Siril's currently-loaded
        image being the user's accepted, recomposited comet+star result,
        and the same `siril.cmd("cd", "../")` the replaced block used to
        do, so _exec_stage1's shared tail (combine-with-master / SPCC /
        save) continues to work unmodified.

        Steps (Siril command sequence verified against `help` output —
        see the feature's design notes):
          1. (already done by the caller — seq_name is the converted/
             calibrated sequence)
          2. register seq_name -2pass; seqapplyreg -framing=current
             (falls back to -framing=max on failure)
          3. seqsubsky on the whole registered sequence
          4. seqstarnet on the whole background-subtracted sequence
             (drops the sequence's registration data — Siril limitation)
          5. splice the dropped registration data back in, in pure
             Python (_splice_seq_registration) — no Siril command exists
             for this
          6. load_seq to make Siril re-read the patched .seq file
          7. seqapplyreg BOTH the starless and the background-subtracted
             (still star-registered) sequences with matched framing, so
             the two final stacks are pixel-dimension-matched
          8. GUIDED PAUSE — comet/asteroid registration (GUI-only)
          9./10. stack the comet sequence and the star sequence
             separately (rej, adjustable sigma)
          11. GUIDED PAUSE — Star Recomposition (GUI-only)
        """
        siril = self.siril
        proc_dir = os.path.join(self.cwd, "process")
        sigma_low = round(self.comet_sigma_low_spin.value(), 2)
        sigma_high = round(self.comet_sigma_high_spin.value(), 2)
        subsky_degree = self.comet_subsky_degree_spin.value()
        subsky_samples = self.comet_subsky_samples_spin.value()

        # ---- 2. register the sequence on the stars
        progress("Comet Stack: registering on stars (2-pass)...", 0.40)
        siril.cmd("register", seq_name, "-2pass")
        self._seqapplyreg_current_then_max(seq_name)
        reg_seq = "r_" + seq_name

        # ---- 3. whole-sequence background extraction
        progress("Comet Stack: removing background from the whole "
                 "sequence (seqsubsky)...", 0.47)
        siril.cmd("seqsubsky", reg_seq, str(subsky_degree),
                  f"-samples={subsky_samples}")
        bkg_seq = "bkg_" + reg_seq

        # ---- 4. whole-sequence star removal (drops registration data)
        progress("Comet Stack: removing stars from the whole sequence "
                 "(seqstarnet)...", 0.54)
        siril.cmd("seqstarnet", bkg_seq, "-stretch", "-nostarmask")
        starless_seq = "starless_" + bkg_seq

        # ---- 5. splice the registration data seqstarnet dropped back in
        progress("Comet Stack: restoring registration data that "
                 "seqstarnet dropped...", 0.58)
        src_seq_path = os.path.join(proc_dir, f"{bkg_seq}.seq")
        dst_seq_path = os.path.join(proc_dir, f"{starless_seq}.seq")
        if not os.path.isfile(src_seq_path):
            raise RuntimeError(
                "Comet Stack: couldn't find "
                f"{os.path.basename(src_seq_path)} to copy registration "
                "data from — seqsubsky may have failed.")
        if not os.path.isfile(dst_seq_path):
            raise RuntimeError(
                "Comet Stack: couldn't find "
                f"{os.path.basename(dst_seq_path)} to splice "
                "registration data into — seqstarnet may have failed.")
        n_spliced = self._splice_seq_registration(src_seq_path, dst_seq_path)
        siril.log(
            f"Comet Stack: spliced {n_spliced} registration line(s) from "
            f"{os.path.basename(src_seq_path)} into "
            f"{os.path.basename(dst_seq_path)}.", LogColor.BLUE)

        # ---- 6. reload the now-patched sequence so Siril sees the splice
        siril.cmd("load_seq", starless_seq)

        # ---- 7. apply registration to both sequences, with matched framing
        progress("Comet Stack: applying registration to the comet and "
                 "star sequences (matched framing)...", 0.64)
        comet_input_seq = "r_" + starless_seq
        star_input_seq = "r_" + bkg_seq
        self._comet_seqapplyreg_matched(starless_seq, bkg_seq)

        # ---- 8. GUIDED PAUSE #1 — comet/asteroid registration (GUI-only,
        # no console command exists for this in Siril)
        comet_seq = "comet_" + comet_input_seq
        comet_seq_path = os.path.join(proc_dir, f"{comet_seq}.seq")
        instructions1 = (
            "Manual step required: in Siril's own window, go to the "
            "Registration tab. Set the registration method to 'Comet/"
            "Asteroid registration'. Make sure sequence "
            f"'{comet_input_seq}' is selected. On the first frame, draw "
            "a box around the comet's nucleus and click 'Pick object in "
            "#1'. Go to the last frame, draw a box around the comet, "
            "click 'Pick object in #2'. Click 'Register'. Siril will "
            f"create a new sequence named '{comet_seq}'. Once done, "
            "click Continue below.")
        self._guided_pause(
            "Comet Stack — Comet Registration (manual step)",
            instructions1,
            verify_fn=lambda: os.path.isfile(comet_seq_path),
            verify_error=(
                f"'{comet_seq}.seq' wasn't found in the process "
                "directory yet — the comet-registration step above "
                "doesn't look like it finished. Redo it in Siril's "
                "Registration tab, then click Continue again."))

        # ---- 9. / 10. stack the comet sequence and the star sequence
        progress("Comet Stack: stacking the comet sequence...", 0.75)
        siril.cmd("stack", comet_seq, f" rej {sigma_low} {sigma_high}",
                  "-out=comet_stack")
        progress("Comet Stack: stacking the star sequence...", 0.82)
        siril.cmd("stack", star_input_seq, f" rej {sigma_low} {sigma_high}",
                  "-out=star_stack")

        # ---- 11. GUIDED PAUSE #2 — Star Recomposition (GUI-only, no
        # console command exists for this in Siril)
        instructions2 = (
            "Manual step required: in Siril, go to Image Processing → "
            "Star Processing → Star Recomposition. Load 'comet_stack' "
            "and 'star_stack' as the two input images (use Linear mode, "
            "not auto-stretch, if you plan to apply your own stretch "
            "afterward — auto-stretch here can make manual stretch "
            "controls behave oddly). Click Apply. Once you're happy "
            "with the result, leave it as Siril's currently-loaded image "
            "and click Continue below — don't close or replace it.")
        self._guided_pause(
            "Comet Stack — Star Recomposition (manual step)",
            instructions2,
            verify_fn=lambda: siril.is_image_loaded(),
            verify_error=(
                "No image appears to be loaded in Siril — redo the Star "
                "Recomposition step (Image Processing → Star "
                "Processing → Star Recomposition), leave the result "
                "loaded, then click Continue again."))

        self._load_siril_current_into_stage(0, "Preprocess")
        siril.cmd("cd", "../")
        siril.log(
            "Comet Stack: recomposited comet+star image accepted as "
            "this run's Preprocess result.", LogColor.GREEN)

    def _seqapplyreg_current_then_max(self, seq_name):
        """seqapplyreg `seq_name` with -framing=current, falling back to
        -framing=max if that errors — the known fix for the Comet Stack
        workflow's registration-apply steps ('if you get an error with
        minimum framing try maximum framing'). Returns the framing
        string that actually succeeded."""
        siril = self.siril
        try:
            siril.cmd("seqapplyreg", seq_name, "-framing=current")
            return "current"
        except (s.DataError, s.CommandError, s.SirilError) as e:
            siril.log(
                f"Comet Stack: seqapplyreg -framing=current failed for "
                f"{seq_name} ({e}), retrying with -framing=max...",
                LogColor.SALMON)
            siril.cmd("seqapplyreg", seq_name, "-framing=max")
            return "max"

    def _comet_seqapplyreg_matched(self, seq_a, seq_b):
        """seqapplyreg both `seq_a` and `seq_b` with -framing=current; if
        either fails, redo BOTH with -framing=max instead of letting one
        succeed on a different framing than the other. The comet
        sequence and the star sequence share the same underlying
        registration data (see _splice_seq_registration) and must end up
        cropped identically so the two final stacks are pixel-dimension-
        matched for Star Recomposition — letting them diverge onto
        different framing methods would silently break that. Returns the
        framing string both sequences ended up using."""
        siril = self.siril
        try:
            siril.cmd("seqapplyreg", seq_a, "-framing=current")
            siril.cmd("seqapplyreg", seq_b, "-framing=current")
            return "current"
        except (s.DataError, s.CommandError, s.SirilError) as e:
            siril.log(
                f"Comet Stack: seqapplyreg -framing=current failed ({e}) "
                "— retrying BOTH sequences with -framing=max so they "
                "stay matched...", LogColor.SALMON)
            siril.cmd("seqapplyreg", seq_a, "-framing=max")
            siril.cmd("seqapplyreg", seq_b, "-framing=max")
            return "max"

    @staticmethod
    def _splice_seq_registration(src_seq_path, dst_seq_path):
        """Copy the registration-data block from the .seq file at
        `src_seq_path` into the .seq file at `dst_seq_path`, in the same
        relative position, and write the result back to `dst_seq_path`.
        Returns the number of registration lines copied.

        Why this exists: `seqstarnet` regenerates its output sequence's
        .seq file from scratch and does not carry over registration data
        — even when run on a sequence that already has 2-pass star
        registration baked into it from an earlier `register`/
        `seqapplyreg` step. There is no Siril command to reattach it;
        this is a pure text-file patch, run once right after
        `seqstarnet`, so the resulting starless sequence can be handed
        straight to `seqapplyreg` with the same registration/framing as
        the sequence it was derived from (see _exec_stage1_comet_stack).

        Per the .seq file format: registration data is a block of one or
        more lines starting with 'R' (one R-line per frame, or a single
        multi-value R1 line, depending on Siril version/registration
        method), positioned between a line starting with 'M0' and one
        starting with 'M1'. Both files are expected to have exactly one
        such M0/M1 pair; `src_seq_path` is expected to have a non-empty
        R-block between them, `dst_seq_path` is expected to have none
        (or, defensively, whatever it has there is discarded and
        replaced, rather than appended to, so this is safe to call more
        than once on the same destination file).

        Pure text manipulation, no Siril/PyQt dependency — kept as a
        standalone static method precisely so it can get direct unit
        test coverage against a small synthetic .seq file (see
        test_S30Pro_Pipeline_functions.py) without needing a live Siril
        install or a real .seq file on disk.

        Raises RuntimeError with a clear message (rather than silently
        writing a still-broken sequence file) if either file is missing
        the expected M0/M1 markers, or if the source has no R-lines to
        copy.
        """
        def _find_marker(lines, token):
            for i, line in enumerate(lines):
                if line.strip().split(" ", 1)[0] == token:
                    return i
            return -1

        with open(src_seq_path, "r", encoding="utf-8", newline="") as f:
            src_lines = f.readlines()
        m0_src = _find_marker(src_lines, "M0")
        m1_src = _find_marker(src_lines, "M1")
        if m0_src == -1 or m1_src == -1 or m1_src <= m0_src:
            raise RuntimeError(
                "_splice_seq_registration: couldn't find M0/M1 markers "
                f"in {src_seq_path!r} — can't locate its registration "
                "data.")
        r_block = [ln for ln in src_lines[m0_src + 1:m1_src]
                   if ln.lstrip().startswith("R")]
        if not r_block:
            raise RuntimeError(
                "_splice_seq_registration: no registration ('R'-"
                f"prefixed) lines found between M0 and M1 in "
                f"{src_seq_path!r} — the source sequence doesn't appear "
                "to have registration data.")

        with open(dst_seq_path, "r", encoding="utf-8", newline="") as f:
            dst_lines = f.readlines()
        m0_dst = _find_marker(dst_lines, "M0")
        m1_dst = _find_marker(dst_lines, "M1")
        if m0_dst == -1 or m1_dst == -1 or m1_dst <= m0_dst:
            raise RuntimeError(
                "_splice_seq_registration: couldn't find M0/M1 markers "
                f"in {dst_seq_path!r} — can't splice registration data "
                "into it.")

        # Drop any R-lines already sitting between the destination's own
        # M0/M1 (shouldn't normally happen — this is the sequence
        # seqstarnet just regenerated with none — but don't duplicate if
        # it does), then insert the copied block immediately before M1,
        # after whatever else (if anything) is already there.
        middle = [ln for ln in dst_lines[m0_dst + 1:m1_dst]
                  if not ln.lstrip().startswith("R")]
        new_lines = (dst_lines[:m0_dst + 1] + middle + r_block
                    + dst_lines[m1_dst:])

        with open(dst_seq_path, "w", encoding="utf-8", newline="") as f:
            f.writelines(new_lines)
        return len(r_block)

    @staticmethod
    def _patch_stackcnt_header(fits_path, override):
        """Read (and optionally overwrite) the STACKCNT header of the FITS
        file at `fits_path` in place — used by _combine_with_existing_master
        to inject a manual sub-count for an existing master that doesn't
        already carry one, so Siril's `-weight=nbstack` weights it
        correctly instead of treating it as a single frame. Handles both
        simple single-HDU FITS and compressed multi-HDU FITS (data in
        extension 1, matching `_load_raw_light_preview`'s HDU-selection
        logic). `override <= 0` means "don't change anything, just report
        what's there." Returns True if the file already had a positive
        STACKCNT (before any override was applied), False otherwise —
        kept as a pure(ish) file-mutating helper, separated from
        _combine_with_existing_master's Siril/UI calls, so it can be
        exercised directly against a synthetic FITS file in tests."""
        with fits.open(fits_path, mode="update") as hdul:
            hdu = hdul[1] if len(hdul) > 1 and hdul[0].data is None \
                else hdul[0]
            hdr = hdu.header
            had_stackcnt = int(hdr.get("STACKCNT") or 0) > 0
            if override > 0:
                hdr["STACKCNT"] = override
            hdul.flush()
        return had_stackcnt

    @staticmethod
    def _ensure_float32_fits(fits_path):
        """Rewrite the FITS file at `fits_path` in place as a normalized
        32-bit float image (Siril's on-disk convention: physical pixel
        values in [0, 1]), if it isn't one already. Used by
        _combine_with_existing_master so this run's own 32-bit float
        stack and an existing master of unknown/different bit depth
        (e.g. a 16-bit integer FITS) are guaranteed to match precision
        before Siril's `stack` command sees them — Siril's `convert`
        command only symlinks/copies FITS files as-is, it does not
        re-encode them, so relying on it (or on a plain Siril
        load/save round trip) to unify precision isn't reliable.

        Reuses VeraLuxCore.normalize_input for the same integer-ADU ->
        [0, 1] float scaling already used elsewhere in this script when
        reading raw/master FITS files directly, so an existing 16-bit
        master ends up on the same physical scale as a Siril-produced
        32-bit float master rather than 65535x too bright. Floating
        point files that are already normalized (max <= ~1.1) are left
        untouched (no-op rewrite skipped) other than a dtype cast.
        Handles both simple single-HDU FITS and compressed multi-HDU
        FITS (data in extension 1), matching the HDU-selection logic
        used by _patch_stackcnt_header / _load_raw_light_preview."""
        with fits.open(fits_path, mode="update") as hdul:
            idx = 1 if len(hdul) > 1 and hdul[0].data is None else 0
            hdu = hdul[idx]
            data = hdu.data
            if data is None:
                return
            if data.dtype == np.float32 and (
                    data.size == 0 or float(np.max(data)) <= 1.1):
                return
            normalized = VeraLuxCore.normalize_input(np.asarray(data))
            hdu.data = normalized.astype(np.float32)
            for key in ("BSCALE", "BZERO"):
                if key in hdu.header:
                    del hdu.header[key]
            hdul.flush()

    @staticmethod
    def _read_integration_seconds(fits_path):
        """Return (total_seconds, subs_count, per_sub_exptime) read from
        the FITS header at `fits_path`, using the same LIVETIME (else
        STACKCNT x EXPTIME) fallback already used elsewhere in this
        script (see the Preprocess image-info panel) — kept as one
        shared helper so combine's totals stay consistent with what's
        displayed/named everywhere else. Returns (0.0, 0, 0.0) if none
        of these headers are present. Handles both simple single-HDU
        FITS and compressed multi-HDU FITS (data in extension 1),
        matching the HDU-selection logic used by the other _combine_*
        helpers."""
        with fits.open(fits_path) as hdul:
            hdu = hdul[1] if len(hdul) > 1 and hdul[0].data is None \
                else hdul[0]
            hdr = hdu.header
            try:
                live = float(hdr.get("LIVETIME", 0) or 0)
            except (TypeError, ValueError):
                live = 0.0
            try:
                cnt = int(hdr.get("STACKCNT", 0) or 0)
            except (TypeError, ValueError):
                cnt = 0
            try:
                exp = float(hdr.get("EXPTIME", 0) or 0)
            except (TypeError, ValueError):
                exp = 0.0
        if live <= 0 and cnt and exp:
            live = cnt * exp
        return live, cnt, exp

    def _combine_with_existing_master(self, progress):
        """Combine this run's freshly-stacked master (already sitting at
        process/result<ext> and loaded as the current Siril image) with an
        existing already-stacked FITS from an earlier session whose raw
        subs weren't kept.

        Registers the two full images against each other (separate
        sessions rarely frame identically) then stacks just the two of
        them with Siril's -weight=nbstack, which weights each frame
        by its STACKCNT FITS header instead of averaging 50/50 — so a
        master built from many more subs correctly dominates one built
        from few. -norm=addscale also re-levels the two sessions' sky
        background/scale before combining, since sky conditions rarely
        match between sessions.

        Uses `convert` (not `link`) to build the 2-frame sequence,
        deliberately: `link` assumes every sequence member already shares
        the same format/bit depth, which is exactly the assumption that
        broke `calibrate` when a stray stacked file ended up alongside raw
        lights (see the 1.28.x-era bug report). `convert` itself only
        unifies *format*, not precision/bit depth (it just symlinks or
        copies FITS files as-is) — so before it runs, both copies are
        explicitly rewritten to normalized 32-bit float via
        `_ensure_float32_fits`, so an existing master with a different
        bit depth than this run's own 32-bit float stack doesn't make
        `stack` abort with "input images have different precision".

        Only ever touches a *copy* of the user's existing master file
        (for the optional sub-count header patch) — the original is never
        modified. Replaces the current Siril image with the combined
        result on success.

        Siril's own `stack` only sees two "frames" here (the two whole
        masters), so it would otherwise leave STACKCNT=2 and whatever
        single EXPTIME it inherits from one of them on the result —
        wildly understating the real combined integration time. Reads
        both sides' true integration time/sub count first (LIVETIME,
        else STACKCNT x EXPTIME) via _read_integration_seconds and
        patches the *sum* into the combined result's header before
        loading it, so the image-info panel and _save_result_named()'s
        auto-generated filename both reflect the real total. Also sets
        `self._combine_applied_this_run = True` on success so
        _save_result_named() names the output "..._combined" instead of
        "..._stacked", making a merged result identifiable by filename
        alone."""
        siril = self.siril
        src_path = self.combine_master_path_edit.text().strip()
        if not src_path or not os.path.isfile(src_path):
            raise RuntimeError(
                "Combine with existing master is enabled but no valid "
                "file is selected — pick one in the Preprocess stage, "
                "or turn the option off.")

        progress("Preprocess: combining with existing master...", 0.75)
        combine_dir = os.path.join(self.cwd, "process", "combine_masters")
        if os.path.isdir(combine_dir):
            shutil.rmtree(combine_dir, ignore_errors=True)
        os.makedirs(combine_dir, exist_ok=True)

        new_master_src = os.path.join(
            self.cwd, "process", f"result{self.fits_extension}")
        if not os.path.isfile(new_master_src):
            raise RuntimeError(
                "Combine with existing master: couldn't find this run's "
                "own stacked result to combine against.")
        shutil.copy2(
            new_master_src,
            os.path.join(combine_dir, f"new_session{self.fits_extension}"))

        # Copy (never touch the original) the existing master in, and
        # optionally patch its STACKCNT header with a manual override for
        # files that don't already carry one.
        prev_dst = os.path.join(combine_dir, f"prev_session{self.fits_extension}")
        shutil.copy2(src_path, prev_dst)
        override = self.combine_master_subcount_spin.value()
        try:
            had_stackcnt = self._patch_stackcnt_header(prev_dst, override)
        except Exception as e:
            siril.log(
                f"Combine: couldn't read/patch the existing master's "
                f"header ({e}) — continuing anyway.", LogColor.SALMON)
            had_stackcnt = True  # unknown — don't also fire the "missing" warning below
        if override == 0 and not had_stackcnt:
            siril.log(
                "Combine: the existing master has no STACKCNT header and "
                "no sub-count override was given — Siril will likely "
                "treat it as a single frame, which may under-weight it "
                "badly. Set the sub-count override in the Preprocess "
                "stage if you know how many subs went into it.",
                LogColor.SALMON)

        # `convert` just symlinks (or copies, if linking fails) FITS files
        # as-is rather than re-encoding them — it does NOT unify
        # precision/bit depth the way it unifies format, and a plain Siril
        # load/save round trip isn't a reliable way to force it either
        # (still hit "input images have different precision" from `stack`
        # after trying that). Rewrite both files to normalized 32-bit
        # float directly, in Python, before Siril ever touches them.
        new_dst = os.path.join(combine_dir, f"new_session{self.fits_extension}")
        try:
            self._ensure_float32_fits(new_dst)
            self._ensure_float32_fits(prev_dst)
        except Exception as e:
            siril.log(
                f"Combine: couldn't normalize both frames to 32-bit "
                f"float ({e}) — stacking may fail if their precision "
                "still doesn't match.", LogColor.SALMON)

        # Total integration time is this session's own subs PLUS the
        # existing master's — Siril's own `stack` only sees two "frames"
        # here (the two whole masters), so left alone it would report
        # STACKCNT=2 and whatever single EXPTIME it inherits from one of
        # them, wildly understating the real combined integration. Read
        # both sides now (prev_dst already reflects the sub-count
        # override, if one was given) and patch the true totals into the
        # combined result's header below, once it exists.
        new_time, new_cnt, _ = self._read_integration_seconds(new_dst)
        prev_time, prev_cnt, _ = self._read_integration_seconds(prev_dst)
        total_time = new_time + prev_time
        total_subs = new_cnt + prev_cnt
        if total_time > 0:
            siril.log(
                f"Combine: total integration time {total_time / 60.0:.0f} "
                f"min across {total_subs} subs ({new_cnt} new + "
                f"{prev_cnt} existing).", LogColor.BLUE)
        else:
            siril.log(
                "Combine: couldn't determine integration time from either "
                "frame's header (no LIVETIME and no STACKCNT/EXPTIME) — "
                "the combined result's exposure info will be inaccurate.",
                LogColor.SALMON)

        siril.cmd("cd", f'"{combine_dir}"')
        try:
            siril.cmd("convert", "combined", "-out=./")

            # Two independently-processed full masters (different
            # sessions — possibly different contrast, color balance, or
            # orientation) are a much harder registration target than raw
            # subs from one session: plain star-pattern matching can fail
            # to find enough common stars, and `register` then falls back
            # to identity transforms for both frames, which makes
            # `seqapplyreg` refuse to run at all ("Existing registration
            # data is a set of identity matrices... aborting"). Plate-
            # solve registration (matching real sky coordinates via WCS)
            # is far more robust to those differences, so prefer it when
            # local Gaia astrometry is available — same approach the main
            # lights-registration step above uses for mosaics.
            registered = False
            if self.gaia_available:
                try:
                    siril.cmd("seqplatesolve", "combined_", "-nocache",
                              "-force", "-disto=ps_distortion",
                              f"-order={self.disto_order_spin.value()}",
                              "-radius=25", *self._milkyway_solve_args())
                    registered = True
                except (s.DataError, s.CommandError, s.SirilError) as e:
                    siril.log(
                        f"Combine: plate-solve registration failed ({e}), "
                        "falling back to star-based registration.",
                        LogColor.SALMON)
            if not registered:
                try:
                    siril.cmd("register", "combined_")
                    registered = True
                except (s.DataError, s.CommandError, s.SirilError) as e:
                    siril.log(
                        f"Combine: star-based registration also failed "
                        f"({e}). Stacking without registration — check "
                        "the combined result carefully for misalignment.",
                        LogColor.SALMON)

            seq_for_stack = "combined_"
            if registered:
                try:
                    siril.cmd("seqapplyreg", "combined_", "-kernel=square",
                              "-framing=max")
                    seq_for_stack = "r_combined_"
                except (s.DataError, s.CommandError, s.SirilError) as e:
                    siril.log(
                        f"Combine: couldn't apply a registration "
                        f"transform ({e}) — this usually means the two "
                        "images turned out to already be aligned (or "
                        "Siril couldn't find enough common stars/"
                        "coordinates between them to compute one). "
                        "Stacking without re-aligning; check the "
                        "combined result carefully for misalignment "
                        "ghosting.", LogColor.SALMON)

            stack_cmd = ["stack", seq_for_stack, " rej 3 3",
                        "-norm=addscale", "-output_norm", "-rgb_equal",
                        "-weight=nbstack", "-32b",
                        "-out=combined_result"]
            siril.cmd(*stack_cmd)

            # Write the real combined totals (computed above) into the
            # result's header BEFORE loading it — the image-info panel
            # and _save_result_named() both read whatever header is on
            # the *currently loaded* image, so this has to land on disk
            # first for either of them to pick it up.
            result_path = os.path.join(
                combine_dir, f"combined_result{self.fits_extension}")
            if (total_time > 0 or total_subs > 0) and os.path.isfile(result_path):
                try:
                    with fits.open(result_path, mode="update") as hdul:
                        idx = 1 if len(hdul) > 1 and hdul[0].data is None else 0
                        hdr = hdul[idx].header
                        if total_time > 0:
                            hdr["LIVETIME"] = total_time
                        if total_subs > 0:
                            hdr["STACKCNT"] = total_subs
                        hdul.flush()
                except Exception as e:
                    siril.log(
                        f"Combine: couldn't write the combined total "
                        f"integration time into the result's header "
                        f"({e}).", LogColor.SALMON)

            siril.cmd("load", "combined_result")
        finally:
            siril.cmd("cd", f'"{self.cwd}"')

        self._combine_applied_this_run = True
        siril.log(
            "Combine: merged this session's stack with the existing "
            "master, weighted by sub count.", LogColor.GREEN)

    def _load_raw_light_preview(self, lights_dir):
        try:
            files = sorted(f for f in os.listdir(lights_dir) if f.lower().endswith(
                (".fits", ".fit", ".fits.fz", ".fit.fz")))
            if not files:
                return None
            with fits.open(os.path.join(lights_dir, files[0])) as hdul:
                hdu = hdul[1] if len(hdul) > 1 and hdul[0].data is None else hdul[0]
                data = hdu.data
                pattern = (hdu.header.get("BAYERPAT", "") or "").strip().upper()
            if data is None:
                return None
            data = VeraLuxCore.normalize_input(np.asarray(data))
            if data.ndim == 2 and pattern in ("RGGB", "BGGR", "GBRG", "GRBG"):
                code = {"RGGB": cv2.COLOR_BayerBG2RGB, "BGGR": cv2.COLOR_BayerRG2RGB,
                        "GBRG": cv2.COLOR_BayerGR2RGB, "GRBG": cv2.COLOR_BayerGB2RGB}[pattern]
                data = cv2.cvtColor((np.clip(data, 0, 1) * 65535).astype(np.uint16),
                                    code).astype(np.float32) / 65535.0
            return data
        except Exception:
            return None

    @staticmethod
    def _scan_capture_dates(lights_dir):
        """Return (min_date, max_date) as 'YYYY-MM-DD' strings from the
        DATE-OBS headers of every light frame, or None if none found.
        Header-only reads — fast even for hundreds of subs."""
        dates = []
        for fname in os.listdir(lights_dir):
            if fname.startswith(".") or not fname.lower().endswith(
                    (".fits", ".fit", ".fits.fz", ".fit.fz")):
                continue
            try:
                with fits.open(os.path.join(lights_dir, fname),
                               memmap=True) as hdul:
                    hdu = hdul[1] if len(hdul) > 1 and hdul[0].data is None \
                        else hdul[0]
                    d = str(hdu.header.get("DATE-OBS", "")).strip()
                if d:
                    dates.append(d.split("T")[0])
            except Exception:
                continue
        if not dates:
            return None
        return min(dates), max(dates)

    def _estimate_bortle_scale(self, lights_dir):
        """Estimate the Bortle sky class from 2-3 random raw sub-frames.

        This is Option C: no manual entry, no geolocation lookup — just the
        sky background level measured directly in the light frames. See the
        BORTLE_* constants above for the method and its caveats. Returns
        {"bortle", "name", "sqm", "n_samples"} or None if nothing usable
        could be read (e.g. headers missing exposure/pixel-scale info).
        """
        from astropy.stats import sigma_clipped_stats

        files = [f for f in os.listdir(lights_dir) if not f.startswith(".")
                 and f.lower().endswith((".fits", ".fit", ".fits.fz", ".fit.fz"))]
        if not files:
            return None
        k = min(3, len(files))
        sample_files = random.sample(files, k)

        sqm_values = []
        for fname in sample_files:
            try:
                with fits.open(os.path.join(lights_dir, fname)) as hdul:
                    hdu = hdul[1] if len(hdul) > 1 and hdul[0].data is None else hdul[0]
                    data = hdu.data
                    hdr = hdu.header
                if data is None:
                    continue
                data = np.asarray(data, dtype=np.float64)

                exptime = float(hdr.get("EXPTIME", 0) or 0)
                pxsz = float(hdr.get("XPIXSZ", 0) or 0)
                focal = float(hdr.get("FOCALLEN", 0) or 0)
                if exptime <= 0 or pxsz <= 0 or focal <= 0:
                    continue
                pixel_scale = 206.265 * pxsz / focal  # arcsec/pixel

                aperture_mm = float(hdr.get("APERTURE", 0) or 0)
                if aperture_mm <= 0:
                    aperture_mm = focal / 5.0  # typical f/5 smart-scope guess
                if aperture_mm <= 0:
                    aperture_mm = 50.0

                gain_e_per_adu = 1.0
                for key in ("EGAIN", "E-GAIN", "GAINE"):
                    v = hdr.get(key)
                    if v:
                        try:
                            gain_e_per_adu = float(v)
                            break
                        except (TypeError, ValueError):
                            pass

                # robust background level (sigma-clipped median, ignores stars)
                _, bg_median, _ = sigma_clipped_stats(data, sigma=3.0, maxiters=5)
                bg_adu = max(float(bg_median), 1e-6)

                e_per_sec_per_px = (bg_adu * gain_e_per_adu) / exptime
                flux_per_arcsec2 = e_per_sec_per_px / (pixel_scale ** 2)
                flux_per_arcsec2 = max(flux_per_arcsec2, 1e-9)

                zp = ZP_REF_50MM + 2.5 * math.log10((aperture_mm / 50.0) ** 2)
                sqm = zp - 2.5 * math.log10(flux_per_arcsec2)
                sqm_values.append(sqm)
            except Exception:
                continue

        if not sqm_values:
            return None

        avg_sqm = sum(sqm_values) / len(sqm_values)
        bortle = sqm_to_bortle(avg_sqm)
        return {"bortle": bortle, "name": BORTLE_NAMES[bortle],
                "sqm": avg_sqm, "n_samples": len(sqm_values)}

    def _convert_dir(self, dir_name):
        directory = os.path.join(self.cwd, dir_name)
        if not os.path.isdir(directory):
            raise RuntimeError(f"Directory not found: {directory}")
        self.siril.cmd("cd", dir_name)
        files = [f for f in os.listdir(directory)
                 if not f.startswith(".") and f.lower().endswith(
                     (".fit", ".fits", ".fit.fz", ".fits.fz"))]
        if len(files) == 1 and dir_name != "lights":
            # single master frame
            dst = os.path.join(self.cwd, "process",
                               f"{dir_name}_stacked{self.fits_extension}")
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copy2(os.path.join(directory, files[0]), dst)
            self.siril.cmd("cd", "..")
            self.siril.cmd("cd", "process")
            return False
        self.siril.cmd("link", dir_name, "-out=../process")
        self.siril.cmd("cd", "../process")
        return True

    def _stack_calibration(self, name):
        if name == "flats" and self._master_exists("biases"):
            self.siril.cmd("calibrate", "flats", "-bias=biases_stacked")
            self.siril.cmd("stack", "pp_flats rej 3 3", "-norm=mul",
                           "-out=flats_stacked")
        elif name == "flats":
            self.siril.cmd("stack", "flats rej 3 3", "-norm=mul",
                           "-out=flats_stacked")
        else:
            self.siril.cmd("stack", f"{name} rej 3 3 -nonorm",
                           f"-out={name}_stacked")
        self.siril.cmd("cd", "..")

    def _master_exists(self, name):
        return os.path.exists(os.path.join(
            self.cwd, "process", f"{name}_stacked{self.fits_extension}"))

    def _clean_process(self, prefix):
        proc = os.path.join(self.cwd, "process")
        if not os.path.isdir(proc):
            return
        for f in os.listdir(proc):
            base, ext = os.path.splitext(f.lower())
            if base in ("result",) or base.endswith("_stacked"):
                continue
            if f.startswith(prefix):
                try:
                    os.remove(os.path.join(proc, f))
                except OSError:
                    pass

    def _run_spcc(self):
        scope = self.chosen_telescope
        sensor = SPCC_SENSOR_MAP.get(scope, scope)
        args = [f"-oscsensor={sensor}", "-catalog=localgaia",
                "-whiteref=Average Spiral Galaxy"]
        filt = self.filter_combo.currentText()
        filter_args = FILTER_COMMANDS_MAP.get(scope, {}).get(filt)
        args.extend(filter_args if filter_args else ["-oscfilter=UV/IR Block"])
        self.siril.cmd("spcc", *[f'"{a}"' for a in args])

    def _save_result_named(self):
        """Auto-save the current stacked (or combined) result under a
        descriptive, pre-built name — same pattern as the other stages'
        export helpers (on_save_annotated_image, on_save_watermarked_image
        pre-fill a default filename too, just interactively). When this
        run combined with an existing master from an earlier session
        (see _combine_with_existing_master), the name gets a "_combined"
        suffix instead of "_stacked" so it's clear from the filename
        alone, and the sub count/average exposure reflect the *true*
        combined total (LIVETIME / STACKCNT, patched in by the combine
        step) rather than this run's own subs only."""
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        combined = getattr(self, "_combine_applied_this_run", False)
        suffix = "combined" if combined else "stacked"
        try:
            hdr = self.siril.get_image_fits_header(return_as="dict")
            obj = hdr.get("OBJECT", "Unknown").strip().replace(" ", "_")
            cnt = int(hdr.get("STACKCNT", 0) or 0)
            live = float(hdr.get("LIVETIME", 0) or 0)
            # Prefer the true average per-sub exposure (total time / sub
            # count) when available — accurate even when combine merged
            # two sessions shot at different exposure lengths, unlike the
            # raw EXPTIME header (a single frame's own value).
            exp = int(round(live / cnt)) if live > 0 and cnt \
                else int(hdr.get("EXPTIME", 0) or 0)
            name = f"{obj}_{cnt:03d}x{exp}sec_{now}_{suffix}"
        except Exception:
            name = f"result_{now}_{suffix}"
        self.siril.cmd("save", name)
        return name

