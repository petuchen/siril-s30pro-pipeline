"""Final Touch (photo adjustments) stage mixin for UnifiedPipelineWindow."""

import numpy as np
import cv2

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QMessageBox, QPushButton,
    QSlider,
)

from s30pro_pipeline.constants import IDX_TOUCH, luminance
from s30pro_pipeline.graxpert_helpers import richardson_lucy_sharpen
from s30pro_pipeline.image_utils import to_hwc_float, make_qimage

SLIDER_VALUE_LABEL_WIDTH = 40


class TouchMixin:
    def _build_stage_touch(self):
        box, v = self._stage_box(11, "Final Touch — Photo Adjustments",
                                 enabled_check=False)
        self.stage_touch_box = box

        info = QLabel("iPhone-style finishing: brightness, contrast, saturation, "
                      "shadows/highlights and sharpening. Load the image, drag "
                      "sliders, watch the live preview, then run to apply at "
                      "full resolution.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        top = QHBoxLayout()
        self.touch_load_btn = QPushButton("📥  Load current image")
        self.touch_load_btn.clicked.connect(self._load_touch_preview)
        top.addWidget(self.touch_load_btn)
        top.addStretch()
        reset_btn = QPushButton("↺  Reset")
        reset_btn.clicked.connect(self._reset_touch_controls)
        top.addWidget(reset_btn)
        v.addLayout(top)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)
        self.touch_sliders = {}
        self.touch_labels = {}
        specs = (("brightness", "☀ Brightness", -100, 100, 0),
                 ("contrast", "◐ Contrast", -100, 100, 0),
                 ("saturation", "🎨 Saturation", 0, 200, 100),
                 ("shadows", "🌑 Shadows", -100, 100, 0),
                 ("highlights", "🌕 Highlights", -100, 100, 0),
                 ("sharpen", "◇ Sharpen", 0, 100, 0))
        for r, (key, label, lo, hi, default) in enumerate(specs):
            g.addWidget(QLabel(label + ":"), r, 0)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(default)
            sl.valueChanged.connect(self._on_touch_changed)
            g.addWidget(sl, r, 1)
            val = QLabel(str(default))
            val.setMinimumWidth(SLIDER_VALUE_LABEL_WIDTH)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            g.addWidget(val, r, 2)
            self.touch_sliders[key] = sl
            self.touch_labels[key] = val
        v.addLayout(g)

        srow = QHBoxLayout()
        srow.addWidget(QLabel("Sharpen method:"))
        self.touch_sharpen_mode_combo = QComboBox()
        self.touch_sharpen_mode_combo.addItems(
            ["Unsharp Mask (fast)", "Richardson-Lucy Deconvolution (recovers detail)"])
        self.touch_sharpen_mode_combo.setToolTip(
            "Unsharp Mask boosts existing edge contrast (cheap, safe).\n"
            "Richardson-Lucy Deconvolution estimates the blur PSF and inverts "
            "it — recovers more real detail (same idea as AstroSharp / "
            "PixInsight deconvolution) but is slower and can ring on noisy "
            "data. The Sharpen slider sets its iteration count.")
        self.touch_sharpen_mode_combo.currentIndexChanged.connect(
            self._on_touch_changed)
        srow.addWidget(self.touch_sharpen_mode_combo, 1)
        v.addLayout(srow)

        row, self.stage_touch_run = self._run_row(
            lambda: self._launch([self._exec_stage_touch]), undo_stage=IDX_TOUCH)
        v.addLayout(row)
        return box

    def _reset_touch_controls(self):
        defaults = {"brightness": 0, "contrast": 0, "saturation": 100,
                    "shadows": 0, "highlights": 0, "sharpen": 0}
        for key, sl in self.touch_sliders.items():
            sl.blockSignals(True)
            sl.setValue(defaults[key])
            sl.blockSignals(False)
            self.touch_labels[key].setText(str(defaults[key]))
        self.touch_sharpen_mode_combo.setCurrentIndex(0)
        self._schedule_touch_live()

    def _apply_touch_params(self, img):
        """Apply photo adjustments to a planar (3,h,w) or mono float image."""
        out = img.astype(np.float32).copy()
        b = self.touch_sliders["brightness"].value() / 100.0
        c = self.touch_sliders["contrast"].value() / 100.0
        sat = self.touch_sliders["saturation"].value() / 100.0
        sh = self.touch_sliders["shadows"].value() / 100.0
        hl = self.touch_sliders["highlights"].value() / 100.0
        shp = self.touch_sliders["sharpen"].value() / 100.0
        deconv_mode = (getattr(self, "touch_sharpen_mode_combo", None) is not None
                        and self.touch_sharpen_mode_combo.currentIndex() == 1)

        if abs(b) > 1e-3:  # exposure-style brightness
            out = np.clip(out * (2.0 ** b), 0.0, 1.0)
        if abs(c) > 1e-3:
            out = np.clip((out - 0.5) * (1.0 + c) + 0.5, 0.0, 1.0)
        if out.ndim == 3 and out.shape[0] == 3 and abs(sat - 1.0) > 1e-3:
            L = luminance(out)
            for i in range(3):
                out[i] = L + (out[i] - L) * sat
            out = np.clip(out, 0.0, 1.0)
        if abs(sh) > 1e-3:  # lift/crush dark tones, weighted away from bright pixels
            weight = 1.0 - out
            out = np.clip(out + sh * weight * out, 0.0, 1.0)
        if abs(hl) > 1e-3:  # pull/lift bright tones, weighted away from dark pixels
            weight = out
            out = np.clip(out + hl * weight * (1.0 - out), 0.0, 1.0)
        if shp > 1e-3:
            if deconv_mode:
                # Richardson-Lucy deconvolution — recovers real detail by
                # inverting an estimated blur PSF (AstroSharp-style), rather
                # than just boosting existing edge contrast.
                iterations = max(1, int(round(2 + shp * 28)))  # slider -> 3..30 iters
                out = richardson_lucy_sharpen(out, sigma=1.8, iterations=iterations)
            elif out.ndim == 3:
                for i in range(out.shape[0]):
                    blur = cv2.GaussianBlur(out[i], (0, 0), 2.0)
                    out[i] = np.clip(out[i] + 1.5 * shp * (out[i] - blur), 0, 1)
            else:
                blur = cv2.GaussianBlur(out, (0, 0), 2.0)
                out = np.clip(out + 1.5 * shp * (out - blur), 0, 1)
        return out.astype(np.float32)

    def _load_touch_preview(self):
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
        self.touch_proxy = hwc
        self._update_touch_live()
        self.status_label.setText("Final Touch loaded — drag the sliders.")

    def _on_touch_changed(self):
        for key, sl in self.touch_sliders.items():
            self.touch_labels[key].setText(str(sl.value()))
        self._schedule_touch_live()

    def _schedule_touch_live(self):
        if getattr(self, "touch_proxy", None) is not None:
            self._touch_timer.start(40)

    def _update_touch_live(self):
        if getattr(self, "touch_proxy", None) is None:
            return
        planar = np.transpose(self.touch_proxy, (2, 0, 1)).copy()
        applied = np.transpose(self._apply_touch_params(planar), (1, 2, 0))
        self.snapshots[IDX_TOUCH] = {
            "before": make_qimage(self.touch_proxy),
            "after": make_qimage(applied),
        }
        if self.preview_stage_combo.currentIndex() != IDX_TOUCH:
            self.preview_stage_combo.setCurrentIndex(IDX_TOUCH)
        else:
            self._refresh_preview()

    def _exec_stage_touch(self, progress):
        progress("Final touch: fetching image...", 0.05)
        before = self._get_current_image()
        before, _ = self._reconcile_held_stars(before, progress)
        progress("Final touch: applying adjustments (full resolution)...", 0.4)
        after = self._apply_touch_params(before)
        self._set_current_image(after, "AstroPipeline: final touch")
        self._finish_stage(IDX_TOUCH, before, after,
                           "Final touch: done.", "Final touch applied",
                           before_linear=False, after_linear=False,
                           autosave_name="final_touched", progress=progress)
