"""Stretch (VeraLux HyperMetric) stage mixin for UnifiedPipelineWindow."""

import math

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QSlider,
)

from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_STR, SENSOR_PROFILES
from s30pro_pipeline.veralux_stretch import VeraLuxCore, veralux_stretch


class StretchMixin:
    def _build_stage4(self):
        box, v = self._stage_box(9, "Stretch — VeraLux HyperMetric")
        self.stage4_box = box

        g = QGridLayout()
        g.addWidget(QLabel("Sensor profile:"), 0, 0)
        self.profile_combo = QComboBox()
        self.profile_combo.addItems(list(SENSOR_PROFILES.keys()))
        self.profile_combo.setCurrentText("ZWO Seestar S30")
        g.addWidget(self.profile_combo, 0, 1)

        g.addWidget(QLabel("Mode:"), 1, 0)
        self.stretch_mode_combo = QComboBox()
        self.stretch_mode_combo.addItems(["Ready-to-Use", "Scientific"])
        g.addWidget(self.stretch_mode_combo, 1, 1)
        v.addLayout(g)

        # Log D — the main contrast/strength control — gets its own slider
        # row since it's the parameter you'll adjust most.
        d_row = QHBoxLayout()
        d_row.setSpacing(8)
        d_row.addWidget(QLabel("Log D:"))
        self.log_d_slider = QSlider(Qt.Orientation.Horizontal)
        self.log_d_slider.setRange(0, 700)   # ×100 of 0.0–7.0
        self.log_d_slider.setValue(200)
        d_row.addWidget(self.log_d_slider, 1)
        self.log_d_spin = QDoubleSpinBox()
        self.log_d_spin.setRange(0.0, 7.0)
        self.log_d_spin.setSingleStep(0.05)
        self.log_d_spin.setValue(2.0)
        d_row.addWidget(self.log_d_spin)
        v.addLayout(d_row)
        self._link_slider_spin(self.log_d_slider, self.log_d_spin, 100)

        # Target background — the other parameter worth a slider, since it
        # directly drives the auto Log D solver's result.
        bg_row = QHBoxLayout()
        bg_row.setSpacing(8)
        bg_row.addWidget(QLabel("Target bg:"))
        self.target_bg_slider = QSlider(Qt.Orientation.Horizontal)
        self.target_bg_slider.setRange(5, 50)   # ×100 of 0.05–0.50
        self.target_bg_slider.setValue(20)
        bg_row.addWidget(self.target_bg_slider, 1)
        self.target_bg_spin = QDoubleSpinBox()
        self.target_bg_spin.setRange(0.05, 0.5)
        self.target_bg_spin.setSingleStep(0.01)
        self.target_bg_spin.setValue(0.20)
        bg_row.addWidget(self.target_bg_spin)
        v.addLayout(bg_row)
        self._link_slider_spin(self.target_bg_slider, self.target_bg_spin, 100)

        # 2 columns (label, control), one param per row, instead of two
        # side-by-side pairs — "Convergence:" is long enough to crowd the
        # row at ~1/3-window width.
        g2 = QGridLayout()
        g2.setHorizontalSpacing(10)
        g2.setVerticalSpacing(8)
        g2.setColumnStretch(1, 1)

        g2.addWidget(QLabel("Protect b:"), 0, 0)
        self.protect_b_spin = QDoubleSpinBox()
        self.protect_b_spin.setRange(0.1, 30.0)
        self.protect_b_spin.setSingleStep(0.5)
        self.protect_b_spin.setValue(6.0)
        g2.addWidget(self.protect_b_spin, 0, 1)
        g2.addWidget(QLabel("Convergence:"), 1, 0)
        self.convergence_spin = QDoubleSpinBox()
        self.convergence_spin.setRange(0.1, 10.0)
        self.convergence_spin.setSingleStep(0.1)
        self.convergence_spin.setValue(2.0)
        g2.addWidget(self.convergence_spin, 1, 1)

        g2.addWidget(QLabel("Color grip:"), 2, 0)
        self.color_grip_spin = QDoubleSpinBox()
        self.color_grip_spin.setRange(0.0, 1.0)
        self.color_grip_spin.setSingleStep(0.05)
        self.color_grip_spin.setValue(1.0)
        g2.addWidget(self.color_grip_spin, 2, 1)
        g2.addWidget(QLabel("Linear exp:"), 3, 0)
        self.linear_exp_spin = QDoubleSpinBox()
        self.linear_exp_spin.setRange(0.0, 1.0)
        self.linear_exp_spin.setSingleStep(0.05)
        self.linear_exp_spin.setValue(0.0)
        g2.addWidget(self.linear_exp_spin, 3, 1)
        v.addLayout(g2)

        opts = QHBoxLayout()
        opts.setSpacing(14)
        self.auto_d_checkbox = QCheckBox("Auto Log D at run time")
        self.auto_d_checkbox.setChecked(True)
        self.auto_d_checkbox.setToolTip(
            "Solve the optimal Log D automatically when the stage runs")
        opts.addWidget(self.auto_d_checkbox)
        self.adaptive_anchor_checkbox = QCheckBox("Adaptive anchor")
        self.adaptive_anchor_checkbox.setChecked(True)
        opts.addWidget(self.adaptive_anchor_checkbox)
        opts.addStretch()
        v.addLayout(opts)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        # VeraLux-style solver button: fills the Log D spinbox from the image
        self.calc_d_btn = QPushButton("⚙  Auto Log D")
        self.calc_d_btn.setObjectName("AutoButton")
        self.calc_d_btn.setToolTip(
            "VeraLux smart solver: analyses the current image and computes the\n"
            "Log D that puts the sky background at the target level while\n"
            "backing off if any color channel would clip (Floating Sky Check).\n"
            "Fills the Log D box and switches Auto off so your value is used.")
        self.calc_d_btn.clicked.connect(self.on_calc_log_d)
        btn_row.addWidget(self.calc_d_btn, 1)
        reset_stretch_btn = QPushButton("↺  Reset")
        reset_stretch_btn.setToolTip(
            "Reset Log D, Protect b, Target bg, Convergence, Color grip, "
            "Linear expansion and the anchor/auto options to defaults "
            "(sensor profile and mode are left as-is).")
        reset_stretch_btn.clicked.connect(self._reset_stretch_controls)
        btn_row.addWidget(reset_stretch_btn)
        v.addLayout(btn_row)

        row, self.stage4_run = self._run_row(
            lambda: self._launch([self._exec_stage4]), undo_stage=IDX_STR)
        v.addLayout(row)
        return box

    @staticmethod
    def _link_slider_spin(slider, spin, factor):
        """Bidirectionally sync an int QSlider with a QDoubleSpinBox, where
        slider value = spin value * factor. Reused for Log D and Target bg."""
        def from_slider(val):
            spin.blockSignals(True)
            spin.setValue(val / factor)
            spin.blockSignals(False)

        def from_spin(val):
            slider.blockSignals(True)
            slider.setValue(int(round(val * factor)))
            slider.blockSignals(False)

        slider.valueChanged.connect(from_slider)
        spin.valueChanged.connect(from_spin)

    def _reset_stretch_controls(self):
        """Reset stage-6 parameters to VeraLux defaults. Sensor profile and
        Ready-to-Use/Scientific mode are intentionally left untouched."""
        self.log_d_spin.setValue(2.0)
        self.protect_b_spin.setValue(6.0)
        self.target_bg_spin.setValue(0.20)
        self.convergence_spin.setValue(2.0)
        self.color_grip_spin.setValue(1.0)
        self.linear_exp_spin.setValue(0.0)
        self.adaptive_anchor_checkbox.setChecked(True)
        self.auto_d_checkbox.setChecked(True)
        self.status_label.setText("Stretch parameters reset to defaults.")

    def _solve_log_d_from(self, img, progress=None):
        """VeraLux-style Log D solver with a per-channel 'Floating Sky'
        safety check.

        Three fixes over a naive single-shot median match:

        1. In Ready-to-Use mode, the final adaptive output scaling
           (adaptive_output_scaling) ALWAYS re-normalizes the result so the
           background median lands exactly on the Target Background slider,
           regardless of what Log D was used to get there. So solving Log D
           to also hit that same target directly on the raw anchored
           luminance is redundant — and on images that are mostly empty sky
           (anchored median sitting very close to 0), forcing that match
           can blow Log D up to an extreme value trying to lift a
           near-zero number all the way to e.g. 0.20. For RTU we instead
           solve toward a modest, fixed contrast target and let the final
           stage set the exact background. Scientific mode has no such
           rescue stage, so it still solves directly for the target.
        2. Crucially, "no clipping" has to be checked on the *reconstructed
           color channels*, not on luminance. The color step is
           final[c] = L_str * (ratio_c * (1-k) + k) — for a pixel whose
           ratio_R is well above 1 (a red/Hα-dominated nebula pixel — very
           common on OSC data, and made worse by sensor profiles like the
           Seestar's that down-weight green), final[R] can already exceed 1
           and clip to solid white/red *before* luminance itself looks
           anywhere near saturated. Checking luminance alone (as the first
           version of this solver did) misses exactly this case, which is
           what caused the persistent "very red" result. So this solver
           simulates the full RGB reconstruction on a pixel sample and
           checks the worst of the three channels.
        3. The check runs against the *default* Color Grip / Convergence
           values used at solve time, since those also affect how much a
           channel overshoots.
        """
        weights = SENSOR_PROFILES[self.profile_combo.currentText()]
        if self.adaptive_anchor_checkbox.isChecked():
            anchor = VeraLuxCore.calculate_anchor_adaptive(img, weights=weights)
        else:
            anchor = VeraLuxCore.calculate_anchor(img)

        is_rgb = img.ndim == 3 and img.shape[0] == 3
        flat = img.reshape(3, -1) if is_rgb else img.reshape(1, -1)
        n = flat.shape[1]
        stride = max(1, n // 400000)
        sample = np.ascontiguousarray(flat[:, ::stride])

        L_anch, img_anch = VeraLuxCore.extract_luminance(sample, anchor, weights)
        eps = 1e-9
        L_safe = L_anch + eps
        ratios = [img_anch[c] / L_safe for c in range(3)] if is_rgb else None

        b_val = self.protect_b_spin.value()
        convergence_power = self.convergence_spin.value()
        is_rtu = self.stretch_mode_combo.currentText() == "Ready-to-Use"
        target = min(self.target_bg_spin.value(), 0.10) if is_rtu \
            else self.target_bg_spin.value()

        log_d = VeraLuxCore.solve_log_d(L_anch, target, b_val)

        def worst_channel_clip_fraction(d):
            L_str = np.clip(
                VeraLuxCore.hyperbolic_stretch(L_anch, 10.0 ** d, b_val),
                0.0, 1.0)
            if not is_rgb:
                return float(np.mean(L_str > 0.995))
            k = np.power(L_str, convergence_power)
            worst = 0.0
            for c in range(3):
                channel = L_str * (ratios[c] * (1.0 - k) + k)
                worst = max(worst, float(np.mean(channel > 0.995)))
            return worst

        # Floating Sky Check: back off Log D while more than ~0.2% of the
        # sampled pixels would clip to white in ANY channel.
        for _ in range(30):
            if worst_channel_clip_fraction(log_d) <= 0.002 or log_d <= 0.05:
                break
            log_d = max(0.05, log_d - 0.15)

        return float(np.clip(log_d, 0.0, 7.0))

    def on_calc_log_d(self):
        """'Calculate Optimal Log D' button — runs the solver on the current
        image and fills the Log D spinbox (does not modify the image)."""
        def job(progress):
            progress("VeraLux solver: analysing image...", 0.2)
            img = self._get_current_image()
            log_d = self._solve_log_d_from(img, progress)
            self.log_d_solved.emit(float(log_d))
            progress(f"Optimal Log D = {log_d:.2f}", 1.0)
            self.siril.log(f"VeraLux solver: optimal Log D = {log_d:.2f}",
                           LogColor.BLUE)
        self._launch([job])

    def _on_log_d_solved(self, log_d):
        self.log_d_spin.setValue(log_d)
        self.auto_d_checkbox.setChecked(False)  # use the computed value

    def _exec_stage4(self, progress):
        progress("Stretch: fetching image...", 0.02)
        before = self._get_current_image()
        weights = SENSOR_PROFILES[self.profile_combo.currentText()]
        mode = ("ready_to_use" if self.stretch_mode_combo.currentText()
                == "Ready-to-Use" else "scientific")

        log_d = self.log_d_spin.value()
        if self.auto_d_checkbox.isChecked():
            progress("Stretch: solving optimal log D...", 0.1)
            log_d = self._solve_log_d_from(before)
            self.siril.log(f"VeraLux solver: log D = {log_d:.2f}", LogColor.BLUE)

        after = veralux_stretch(
            before, log_d, self.protect_b_spin.value(),
            self.convergence_spin.value(), weights,
            processing_mode=mode,
            target_bg=self.target_bg_spin.value(),
            color_grip=self.color_grip_spin.value(),
            linear_expansion=self.linear_exp_spin.value(),
            use_adaptive_anchor=self.adaptive_anchor_checkbox.isChecked(),
            progress=progress)

        # --- recombine stars held back by the Remove Stars stage (stretched
        #     separately with a gentle arcsinh so they stay tight & colorful)
        held = getattr(self, "held_stars", None)
        if held is not None:
            self.held_stars = None  # consumed either way — never re-applied twice
            if held.shape == after.shape:
                progress("Stretch: stretching stars separately (asinh)...", 0.9)
                k = self.star_asinh_spin.value()
                stars_str = np.arcsinh(k * np.clip(held, 0.0, 1.0)) / math.asinh(k)
                stars_str = np.clip(stars_str, 0.0, 1.0)
                strength = self.star_strength_spin.value()
                if strength > 0.001:
                    progress("Stretch: recombining stars with nebula...", 0.95)
                    after = 1.0 - (1.0 - after) * (1.0 - stars_str * strength)
                    after = np.clip(after, 0.0, 1.0).astype(np.float32)
                self.siril.log(
                    f"Stars recombined (asinh {k:.1f}, strength {strength:.2f})",
                    LogColor.GREEN)
            else:
                # Shape mismatch usually means a stage that changes image size
                # (e.g. Crop) was re-run out of order between Palette and here.
                # Rather than silently dropping the stars, say so clearly.
                self.siril.log(
                    "Remove Stars held back a star layer for this Stretch, but "
                    "its size no longer matches the current image (probably a "
                    "stage was re-run out of order) — could not recombine the "
                    "stars automatically. Re-run the Remove Stars stage to "
                    "re-capture them at the current size.", LogColor.SALMON)

        self._set_current_image(after, f"AstroPipeline: VeraLux stretch D={log_d:.2f}")
        self._finish_stage(IDX_STR, before, after,
                           "Stretch: done.", "Stretch complete!",
                           before_linear=True, after_linear=False,
                           autosave_name="final_stretched", progress=progress)
