"""Auto Gradient Removal (AGR) stage mixin for UnifiedPipelineWindow."""

import numpy as np

from PyQt6.QtWidgets import QCheckBox, QComboBox, QHBoxLayout, QLabel

from s30pro_pipeline.constants import IDX_AGR
from s30pro_pipeline.agr_math import agr_correct_image


_AGR_MODE_KEYS = [("subtract", "agr_mode_subtract"), ("divide", "agr_mode_divide")]


class AgrMixin:
    def _build_stage_agr(self):
        # Off by default (most images don't need it), but still one of the
        # small set of stages a beginner is expected to look at and decide
        # on — so it starts expanded even though unchecked, unlike the
        # other off-by-default stages (see _stage_box's start_expanded).
        # Title stays literal English for now — see stage_watermark.py's
        # comment: stage titles move together in Phase 7.
        box, v = self._stage_box(4, "Auto Gradient Removal",
                                 enabled_check=False, start_expanded=True)
        self.stage_agr_box = box

        self.agr_info_label = QLabel(self.tr("agr_info"))
        self.agr_info_label.setObjectName("SubHeader")
        self.agr_info_label.setWordWrap(True)
        v.addWidget(self.agr_info_label)

        row, self.agr_scale_spin = self._slider_spin_row(
            self.tr("agr_scale_label"), 1.0, 10.0, 0.5, 5.0, 1,
            self.tr("agr_scale_tooltip"))
        v.addLayout(row)

        row, self.agr_smoothness_spin = self._slider_spin_row(
            self.tr("agr_smoothness_label"), 0.0, 3.0, 0.1, 1.0, 1,
            self.tr("agr_smoothness_tooltip"))
        v.addLayout(row)

        self.agr_protect_checkbox = QCheckBox(self.tr("agr_protect"))
        self.agr_protect_checkbox.setChecked(True)
        self.agr_protect_checkbox.setToolTip(self.tr("agr_protect_tooltip"))
        v.addWidget(self.agr_protect_checkbox)

        row, self.agr_pthr_spin = self._slider_spin_row(
            self.tr("agr_pthr_label"), 0.0, 1.0, 0.005, 0.05, 3,
            self.tr("agr_pthr_tooltip"))
        v.addLayout(row)

        row, self.agr_pamt_spin = self._slider_spin_row(
            self.tr("agr_pamt_label"), 0.0, 1.0, 0.05, 0.5, 2,
            self.tr("agr_pamt_tooltip"))
        v.addLayout(row)

        self.agr_simplified_checkbox = QCheckBox(self.tr("agr_simplified"))
        self.agr_simplified_checkbox.setToolTip(
            self.tr("agr_simplified_tooltip"))
        v.addWidget(self.agr_simplified_checkbox)

        row, self.agr_degree_spin = self._slider_spin_row(
            self.tr("agr_degree_label"), 1, 6, 1, 2, 0,
            self.tr("agr_degree_tooltip"))
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
        self.agr_downsample_label = QLabel(self.tr("agr_downsample_label"))
        bottom_row.addWidget(self.agr_downsample_label)
        self.agr_downsample_combo = QComboBox()
        # Plain addItems, not addItem+data: these are digit strings, not
        # translated prose, so currentText() parsing (int(...)) downstream
        # is unaffected either way.
        self.agr_downsample_combo.addItems(["8", "4", "2", "1"])
        self.agr_downsample_combo.setCurrentText("4")
        self.agr_downsample_combo.setToolTip(
            self.tr("agr_downsample_tooltip"))
        bottom_row.addWidget(self.agr_downsample_combo)
        self.agr_mode_label = QLabel(self.tr("agr_mode_label"))
        bottom_row.addWidget(self.agr_mode_label)
        self.agr_mode_combo = QComboBox()
        # currentData(), not currentText() — see the settings-JSON
        # comment in S30Pro_Pipeline.py's _collect_settings/_apply_settings
        # for why the canonical English value has to be read separately
        # from the translated display label.
        for value, i18n_key in _AGR_MODE_KEYS:
            self.agr_mode_combo.addItem(self.tr(i18n_key), value)
        self.agr_mode_combo.setToolTip(self.tr("agr_mode_tooltip"))
        bottom_row.addWidget(self.agr_mode_combo)
        bottom_row.addStretch()
        v.addLayout(bottom_row)

        row, self.stage_agr_run = self._run_row(
            lambda: self._launch([self._exec_stage_agr]), undo_stage=IDX_AGR)
        v.addLayout(row)
        return box

    def retranslate_ui_agr(self):
        self.agr_info_label.setText(self.tr("agr_info"))
        self._retranslate_slider_row(
            self.agr_scale_spin, "agr_scale_label", "agr_scale_tooltip")
        self._retranslate_slider_row(
            self.agr_smoothness_spin, "agr_smoothness_label",
            "agr_smoothness_tooltip")
        self.agr_protect_checkbox.setText(self.tr("agr_protect"))
        self.agr_protect_checkbox.setToolTip(self.tr("agr_protect_tooltip"))
        self._retranslate_slider_row(
            self.agr_pthr_spin, "agr_pthr_label", "agr_pthr_tooltip")
        self._retranslate_slider_row(
            self.agr_pamt_spin, "agr_pamt_label", "agr_pamt_tooltip")
        self.agr_simplified_checkbox.setText(self.tr("agr_simplified"))
        self.agr_simplified_checkbox.setToolTip(
            self.tr("agr_simplified_tooltip"))
        self._retranslate_slider_row(
            self.agr_degree_spin, "agr_degree_label", "agr_degree_tooltip")
        self.agr_downsample_label.setText(self.tr("agr_downsample_label"))
        self.agr_downsample_combo.setToolTip(
            self.tr("agr_downsample_tooltip"))
        self.agr_mode_label.setText(self.tr("agr_mode_label"))
        cur_mode = self.agr_mode_combo.currentData()
        self.agr_mode_combo.clear()
        for value, i18n_key in _AGR_MODE_KEYS:
            self.agr_mode_combo.addItem(self.tr(i18n_key), value)
        idx = self.agr_mode_combo.findData(cur_mode)
        if idx >= 0:
            self.agr_mode_combo.setCurrentIndex(idx)
        self.agr_mode_combo.setToolTip(self.tr("agr_mode_tooltip"))

    def _exec_stage_agr(self, progress):
        progress(self.tr("agr_progress_fetching"), 0.02)
        before = self._get_current_image()          # CHW planar, float32, [0,1]
        mono = before.shape[0] == 1
        hwc = before[0] if mono else np.transpose(before, (1, 2, 0))

        scale = self.agr_scale_spin.value()
        smoothness = self.agr_smoothness_spin.value()
        downsample = int(self.agr_downsample_combo.currentText())
        mode = self.agr_mode_combo.currentData()  # see currentData() comment above
        protect = self.agr_protect_checkbox.isChecked()
        protect_threshold = self.agr_pthr_spin.value()
        protect_amount = self.agr_pamt_spin.value()
        simplified = self.agr_simplified_checkbox.isChecked()
        degree = int(self.agr_degree_spin.value())

        progress(self.tr("agr_progress_estimating"), 0.2)
        # agr_correct_image's own log callback messages (from
        # agr_math.py) stay English regardless of self.lang — they're a
        # separate module's internal progress text, out of scope for
        # this UI-only i18n pass (same boundary as Siril's own log
        # messages elsewhere in the app).
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
            IDX_AGR, before, after, self.tr("agr_progress_done"),
            f"Auto Gradient Removal complete ({model}, mode={mode})",
            progress=progress)
