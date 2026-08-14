"""Auto Gradient Removal (AGR) stage mixin for UnifiedPipelineWindow."""

import numpy as np

from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel

from s30pro_pipeline.constants import IDX_AGR
from s30pro_pipeline.agr_math import agr_correct_image


class AgrMixin:
    def _build_stage_agr(self):
        box, v = self._stage_box(4, "Auto Gradient Removal", enabled_check=False)
        self.stage_agr_box = box

        info = QLabel("Ported from Siril's own AutoGradientRemoval script "
                      "(Cyril Richard). Places no sample points at all — "
                      "fits the background on every pixel that survives "
                      "an iterative robust rejection of structures (stars, "
                      "nebulae, galaxies). Pure numpy, no AI model or GPU "
                      "needed. Off by default; enable it instead of (or "
                      "before) Remove Background below when GraXpert isn't "
                      "installed or subsky's sample points aren't landing "
                      "well.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        row, self.agr_scale_spin = self._slider_spin_row(
            "Scale:", 1.0, 10.0, 0.5, 5.0, 1,
            "Relative scale of the multiscale model. Higher = smoother "
            "(large-scale only); lower = follows more complex/local "
            "gradients.")
        v.addLayout(row)

        row, self.agr_smoothness_spin = self._slider_spin_row(
            "Smoothness:", 0.0, 3.0, 0.1, 1.0, 1,
            "Extra smoothing of the final model. Higher gives a softer, "
            "more gradual background; 0 leaves the fitted model untouched.")
        v.addLayout(row)

        self.agr_protect_checkbox = QCheckBox("Structure protection")
        self.agr_protect_checkbox.setChecked(True)
        self.agr_protect_checkbox.setToolTip(
            "Mask extended bright structures (nebulae) so they are not "
            "absorbed into the model.")
        v.addWidget(self.agr_protect_checkbox)

        row, self.agr_pthr_spin = self._slider_spin_row(
            "    Protection threshold:", 0.0, 1.0, 0.005, 0.05, 3,
            "Brightness above the model at which a pixel is treated as a "
            "structure. Lower = protects more.")
        v.addLayout(row)

        row, self.agr_pamt_spin = self._slider_spin_row(
            "    Protection amount:", 0.0, 1.0, 0.05, 0.5, 2,
            "How far the protection mask grows around detected structures.")
        v.addLayout(row)

        self.agr_simplified_checkbox = QCheckBox("Simplified model")
        self.agr_simplified_checkbox.setToolTip(
            "Replace the multiscale model with a stiff polynomial. Use it "
            "when a nebula fills the frame and the default model hollows "
            "it out.")
        v.addWidget(self.agr_simplified_checkbox)

        row, self.agr_degree_spin = self._slider_spin_row(
            "    Model degree:", 1, 6, 1, 2, 0,
            "Polynomial degree of the simplified model. Lower = stiffer "
            "(degree 1 = plane).")
        v.addLayout(row)

        def sync_agr_enabled():
            protect = self.agr_protect_checkbox.isChecked()
            self.agr_pthr_spin.setEnabled(protect)
            self.agr_pamt_spin.setEnabled(protect)
            self.agr_degree_spin.setEnabled(self.agr_simplified_checkbox.isChecked())
        self.agr_protect_checkbox.toggled.connect(sync_agr_enabled)
        self.agr_simplified_checkbox.toggled.connect(sync_agr_enabled)
        sync_agr_enabled()

        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(10)
        bottom_row.addWidget(QLabel("Downsample:"))
        self.agr_downsample_combo = QComboBox()
        self.agr_downsample_combo.addItems(["8", "4", "2", "1"])
        self.agr_downsample_combo.setCurrentText("4")
        self.agr_downsample_combo.setToolTip(
            "Internal working scale factor. Higher = faster but coarser; "
            "the background scale itself is unaffected.")
        bottom_row.addWidget(self.agr_downsample_combo)
        bottom_row.addWidget(QLabel("Mode:"))
        self.agr_mode_combo = QComboBox()
        self.agr_mode_combo.addItems(["subtract", "divide"])
        self.agr_mode_combo.setToolTip(
            "subtract: additive gradient. divide: multiplicative "
            "(vignetting/flat).")
        bottom_row.addWidget(self.agr_mode_combo)
        bottom_row.addStretch()
        v.addLayout(bottom_row)

        row, self.stage_agr_run = self._run_row(
            lambda: self._launch([self._exec_stage_agr]), undo_stage=IDX_AGR)
        v.addLayout(row)
        return box

    def _exec_stage_agr(self, progress):
        progress("Auto Gradient Removal: fetching image...", 0.02)
        before = self._get_current_image()          # CHW planar, float32, [0,1]
        mono = before.shape[0] == 1
        hwc = before[0] if mono else np.transpose(before, (1, 2, 0))

        scale = self.agr_scale_spin.value()
        smoothness = self.agr_smoothness_spin.value()
        downsample = int(self.agr_downsample_combo.currentText())
        mode = self.agr_mode_combo.currentText()
        protect = self.agr_protect_checkbox.isChecked()
        protect_threshold = self.agr_pthr_spin.value()
        protect_amount = self.agr_pamt_spin.value()
        simplified = self.agr_simplified_checkbox.isChecked()
        degree = int(self.agr_degree_spin.value())

        progress("Auto Gradient Removal: estimating background...", 0.2)
        corrected_hwc, _bg_hwc = agr_correct_image(
            hwc.astype(np.float64), scale, smoothness, downsample, mode,
            protect=protect, protect_threshold=protect_threshold,
            protect_amount=protect_amount, simplified=simplified,
            degree=degree,
            log=lambda m: progress(f"Auto Gradient Removal: {m}", 0.6))

        corrected_hwc = np.clip(corrected_hwc, 0.0, 1.0).astype(np.float32)
        after = corrected_hwc[np.newaxis, ...] if mono else \
            np.transpose(corrected_hwc, (2, 0, 1))
        after = np.ascontiguousarray(after.astype(np.float32))

        model = (f"simplified deg{degree}" if simplified
                 else f"multiscale scale{scale}")
        self._set_current_image(
            after,
            f"AstroPipeline: AutoGradientRemoval ({model}, "
            f"smoothness={smoothness}, protect={protect}, mode={mode})")
        self._finish_stage(
            IDX_AGR, before, after, "Auto Gradient Removal: done.",
            f"Auto Gradient Removal complete ({model}, mode={mode})",
            progress=progress)
