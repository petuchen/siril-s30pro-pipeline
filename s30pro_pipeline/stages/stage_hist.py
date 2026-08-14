"""Histogram Fine-Tune (per-channel MTF) stage mixin for UnifiedPipelineWindow."""

import numpy as np
import cv2

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QMessageBox, QPushButton,
)

from s30pro_pipeline.constants import IDX_HIST
from s30pro_pipeline.veralux_stretch import VeraLuxCore
from s30pro_pipeline.image_utils import to_hwc_float, make_qimage
from s30pro_pipeline.ui_widgets import HistogramEditor


class HistMixin:
    def _build_stage_hist(self):
        box, v = self._stage_box(10, "Histogram Fine-Tune — Per Channel",
                                 enabled_check=False)
        self.stage_hist_box = box

        info = QLabel("Drag the three points (⚫ shadows, ◾ midtones, ⚪ highlights) "
                      "on the histogram — the preview updates live. Pick a channel "
                      "to fine-tune colors separately.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        top = QHBoxLayout()
        top.setSpacing(8)
        self.hist_load_btn = QPushButton("📥  Load current image")
        self.hist_load_btn.setToolTip(
            "Grab the image currently loaded in Siril into the editor "
            "(histogram + live preview)")
        self.hist_load_btn.clicked.connect(self._load_hist_preview)
        top.addWidget(self.hist_load_btn)
        top.addStretch()
        top.addWidget(QLabel("Channel:"))
        self.hist_channel_combo = QComboBox()
        self.hist_channel_combo.addItems(["RGB", "R", "G", "B"])
        top.addWidget(self.hist_channel_combo)
        v.addLayout(top)

        self.hist_editor = HistogramEditor()
        v.addWidget(self.hist_editor)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        for col, name in enumerate(("Shadows", "Midtones", "Highlights")):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(lbl, 0, col + 1)
            g.setColumnStretch(col + 1, 1)

        self.hist_controls = {}
        colors = {"R": "#ff6b6b", "G": "#69db7c", "B": "#74a8ff", "RGB": "#ffffff"}
        for r, ch in enumerate(("RGB", "R", "G", "B")):
            lbl = QLabel(ch)
            lbl.setStyleSheet(f"color: {colors[ch]}; font-weight: bold;")
            g.addWidget(lbl, r + 1, 0)
            controls = {}
            for c, (key, lo, hi, default, step) in enumerate((
                    ("shadows", 0.0, 0.5, 0.0, 0.005),
                    ("midtones", 0.05, 0.95, 0.5, 0.01),
                    ("highlights", 0.5, 1.0, 1.0, 0.005))):
                spin = QDoubleSpinBox()
                spin.setRange(lo, hi)
                spin.setSingleStep(step)
                spin.setDecimals(3)
                spin.setValue(default)
                controls[key] = spin
                g.addWidget(spin, r + 1, c + 1)
            self.hist_controls[ch] = controls
        v.addLayout(g)

        reset_row = QHBoxLayout()
        reset_btn = QPushButton("↺  Reset")
        reset_btn.clicked.connect(self._reset_hist_controls)
        reset_row.addWidget(reset_btn)
        reset_row.addStretch()
        v.addLayout(reset_row)

        row, self.stage_hist_run = self._run_row(
            lambda: self._launch([self._exec_stage_hist]), undo_stage=IDX_HIST)
        v.addLayout(row)

        # --- wiring: graph <-> spinboxes <-> live preview
        self.hist_channel_combo.currentTextChanged.connect(
            self.hist_editor.set_channel)
        self.hist_editor.changed.connect(self._on_hist_editor_changed)
        for ch, controls in self.hist_controls.items():
            for spin in controls.values():
                spin.valueChanged.connect(self._on_hist_spin_changed)
        return box

    def _reset_hist_controls(self):
        for controls in self.hist_controls.values():
            controls["shadows"].setValue(0.0)
            controls["midtones"].setValue(0.5)
            controls["highlights"].setValue(1.0)
        for ch in self.hist_editor.params:
            self.hist_editor.set_params(ch, 0.0, 0.5, 1.0)
        self._schedule_hist_live()

    def _hist_params_from_ui(self, ch):
        c = self.hist_controls[ch]
        return (c["shadows"].value(), c["midtones"].value(),
                c["highlights"].value())

    def _apply_hist_params(self, img, progress=None):
        """Apply linked + per-channel MTF to a planar (3,h,w) or mono image."""
        def mtf_channel(data, sh, mid, hi):
            if hi <= sh + 1e-6:
                return data
            d = np.clip((data - sh) / (hi - sh), 0.0, 1.0)
            if abs(mid - 0.5) > 1e-4:
                d = VeraLuxCore.apply_mtf(d, mid)
            return d

        out = mtf_channel(img, *self._hist_params_from_ui("RGB"))
        if out.ndim == 3 and out.shape[0] == 3:
            for i, ch in enumerate(("R", "G", "B")):
                sh, mid, hi = self._hist_params_from_ui(ch)
                if sh > 0 or hi < 1.0 or abs(mid - 0.5) > 1e-4:
                    if progress:
                        progress(f"Histogram: adjusting {ch}...", 0.5 + i * 0.15)
                    out[i] = mtf_channel(out[i], sh, mid, hi)
        return np.clip(out, 0.0, 1.0).astype(np.float32)

    def _load_hist_preview(self):
        """Pull the current Siril image into the histogram editor + preview."""
        try:
            img = self._get_current_image()
        except Exception as e:
            QMessageBox.information(self, "No image", str(e))
            return
        hwc = to_hwc_float(img)
        h, w, _ = hwc.shape
        scale = min(1.0, 1100 / max(h, w))
        if scale < 1.0:
            hwc = cv2.resize(hwc, (int(w * scale), int(h * scale)),
                             interpolation=cv2.INTER_AREA)
        self.hist_proxy = hwc  # (h,w,3) float, display proxy
        self.hist_editor.set_image_data(hwc)
        self._update_hist_live()
        self.status_label.setText(
            "Histogram editor loaded — drag the points to fine-tune.")

    def _on_hist_editor_changed(self):
        """Graph marker moved → sync spinboxes (silently) → live preview."""
        ch = self.hist_editor.channel
        prm = self.hist_editor.params[ch]
        controls = self.hist_controls[ch]
        for key in ("shadows", "midtones", "highlights"):
            controls[key].blockSignals(True)
            controls[key].setValue(prm[key])
            controls[key].blockSignals(False)
        self._schedule_hist_live()

    def _on_hist_spin_changed(self):
        """Spinbox edited → sync graph → live preview."""
        for ch, controls in self.hist_controls.items():
            self.hist_editor.set_params(ch, controls["shadows"].value(),
                                        controls["midtones"].value(),
                                        controls["highlights"].value())
        self._schedule_hist_live()

    def _schedule_hist_live(self):
        if getattr(self, "hist_proxy", None) is not None:
            self._hist_timer.start(40)  # debounce for smooth dragging

    def _update_hist_live(self):
        if getattr(self, "hist_proxy", None) is None:
            return
        planar = np.transpose(self.hist_proxy, (2, 0, 1)).copy()
        applied = self._apply_hist_params(planar)
        applied_hwc = np.transpose(applied, (1, 2, 0))
        self.snapshots[IDX_HIST] = {
            "before": make_qimage(self.hist_proxy),
            "after": make_qimage(applied_hwc),
        }
        if self.preview_stage_combo.currentIndex() != IDX_HIST:
            self.preview_stage_combo.setCurrentIndex(IDX_HIST)
        else:
            self._refresh_preview()

    def _exec_stage_hist(self, progress):
        progress("Histogram: fetching image...", 0.05)
        before = self._get_current_image()
        before, _ = self._reconcile_held_stars(before, progress)
        progress("Histogram: applying stretch (full resolution)...", 0.3)
        after = self._apply_hist_params(before.copy(), progress)
        self._set_current_image(after, "AstroPipeline: histogram fine-tune")
        self._finish_stage(IDX_HIST, before, after,
                           "Histogram fine-tune: done.",
                           "Histogram fine-tune complete — pipeline finished!",
                           before_linear=False, after_linear=False,
                           autosave_name="final_finetuned", progress=progress)
