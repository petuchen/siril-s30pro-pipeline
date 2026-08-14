"""Remove Background (BGE) stage mixin for UnifiedPipelineWindow."""

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QGridLayout,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QSizePolicy, QSlider,
    QSpinBox, QStackedWidget, QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QColor, QPainter, QPen, QPixmap

import sirilpy as s
from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_BGE
from s30pro_pipeline.graxpert_helpers import (
    get_available_local_models, graxpert_extract_background,
    graxpert_apply_correction,
)
from s30pro_pipeline.image_utils import to_hwc_float, display_autostretch, make_qimage


class BgeMixin:
    def _build_stage2(self):
        box, v = self._stage_box(5, "Remove Background")
        self.stage2_box = box

        m = QHBoxLayout()
        m.setSpacing(10)
        m.addWidget(QLabel("Method:"))
        self.bge_method_combo = QComboBox()
        self.bge_method_combo.addItems(
            ["GraXpert AI", "Siril subsky — RBF", "Siril subsky — Polynomial"])
        m.addWidget(self.bge_method_combo, 1)
        v.addLayout(m)

        self.bge_params_stack = QStackedWidget()
        self.bge_params_stack.setSizePolicy(QSizePolicy.Policy.Preferred,
                                            QSizePolicy.Policy.Fixed)

        # --- page 0: GraXpert AI
        gx_page = QWidget()
        gx_v = QVBoxLayout(gx_page)
        gx_v.setContentsMargins(0, 0, 0, 0)
        gx_v.setSpacing(8)
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setColumnStretch(1, 1)
        g.addWidget(QLabel("Model:"), 0, 0)
        self.bge_model_combo = QComboBox()
        self.bge_models = get_available_local_models("bge-ai-models")
        self.bge_model_combo.addItems(sorted(self.bge_models.keys())
                                      or ["No models found"])
        if self.bge_models:
            self.bge_model_combo.setCurrentIndex(self.bge_model_combo.count() - 1)
        g.addWidget(self.bge_model_combo, 0, 1)
        g.addWidget(QLabel("Correction:"), 1, 0)
        self.bge_correction_combo = QComboBox()
        self.bge_correction_combo.addItems(["subtraction", "division"])
        g.addWidget(self.bge_correction_combo, 1, 1)
        gx_v.addLayout(g)

        sm = QHBoxLayout()
        sm.addWidget(QLabel("Smoothing:"))
        self.bge_smoothing_slider = QSlider(Qt.Orientation.Horizontal)
        self.bge_smoothing_slider.setRange(0, 100)
        self.bge_smoothing_slider.setValue(50)
        sm.addWidget(self.bge_smoothing_slider)
        self.bge_smoothing_label = QLabel("0.50")
        self.bge_smoothing_slider.valueChanged.connect(
            lambda val: self.bge_smoothing_label.setText(f"{val/100:.2f}"))
        sm.addWidget(self.bge_smoothing_label)
        gx_v.addLayout(sm)
        self.bge_params_stack.addWidget(gx_page)

        # --- page 1: Siril subsky (shared by RBF and Polynomial)
        ss_page = QWidget()
        ss_v = QVBoxLayout(ss_page)
        ss_v.setContentsMargins(0, 0, 0, 0)
        ss_v.setSpacing(8)
        sg = QGridLayout()
        sg.setHorizontalSpacing(10)
        sg.setColumnStretch(1, 1)
        sg.setColumnStretch(3, 1)
        sg.addWidget(QLabel("Samples:"), 0, 0)
        self.subsky_samples = QSpinBox()
        self.subsky_samples.setRange(4, 100)
        self.subsky_samples.setValue(20)
        sg.addWidget(self.subsky_samples, 0, 1)
        sg.addWidget(QLabel("Tolerance:"), 0, 2)
        self.subsky_tolerance = QDoubleSpinBox()
        self.subsky_tolerance.setRange(0.1, 10.0)
        self.subsky_tolerance.setSingleStep(0.1)
        self.subsky_tolerance.setValue(2.0)
        sg.addWidget(self.subsky_tolerance, 0, 3)
        sg.addWidget(QLabel("RBF smooth:"), 1, 0)
        self.subsky_smooth = QDoubleSpinBox()
        self.subsky_smooth.setRange(0.0, 1.0)
        self.subsky_smooth.setSingleStep(0.05)
        self.subsky_smooth.setValue(0.5)
        sg.addWidget(self.subsky_smooth, 1, 1)
        sg.addWidget(QLabel("Poly degree:"), 1, 2)
        self.subsky_degree = QSpinBox()
        self.subsky_degree.setRange(1, 4)
        self.subsky_degree.setValue(2)
        sg.addWidget(self.subsky_degree, 1, 3)
        ss_v.addLayout(sg)
        ss_info = QLabel("Siril's built-in background extraction — fast, no AI "
                         "model needed. RBF handles complex gradients; "
                         "polynomial suits simple linear gradients.")
        ss_info.setObjectName("SubHeader")
        ss_info.setWordWrap(True)
        ss_v.addWidget(ss_info)
        self.subsky_boxes_btn = QPushButton("🖼  Edit sample boxes...")
        self.subsky_boxes_btn.setToolTip(
            "See the background sample boxes over the current image, "
            "click one to toggle it off/on, or click empty space to add "
            "a new one. The kept boxes are used instead of Siril's own "
            "automatic placement the next time this stage runs.")
        self.subsky_boxes_btn.clicked.connect(self._open_subsky_box_editor)
        ss_v.addWidget(self.subsky_boxes_btn)
        self.subsky_boxes_status = QLabel("Using Siril's automatic sample "
                                          "placement (default).")
        self.subsky_boxes_status.setObjectName("SubHeader")
        self.subsky_boxes_status.setWordWrap(True)
        ss_v.addWidget(self.subsky_boxes_status)
        self.bge_params_stack.addWidget(ss_page)

        v.addWidget(self.bge_params_stack)
        self.bge_method_combo.currentIndexChanged.connect(
            lambda i: self.bge_params_stack.setCurrentIndex(0 if i == 0 else 1))

        row, self.stage2_run = self._run_row(
            lambda: self._launch([self._exec_stage2]), undo_stage=IDX_BGE)
        v.addLayout(row)
        return box

    @staticmethod
    def _generate_default_bg_boxes(img_w, img_h, n_per_side=5, size=25):
        """Evenly-spaced starting grid of candidate background sample
        boxes — [x, y, size, kept] in image pixel coordinates, kept=True
        for all of them. Siril doesn't expose its own auto-placement
        algorithm for inspection/editing (only get/set/clear on whatever
        is currently set), so this is a simple placeholder grid meant to
        be hand-curated in the box editor afterwards: deselect boxes
        that land on stars/nebulae, add extras in gaps."""
        margin_x, margin_y = img_w * 0.08, img_h * 0.08
        xs = np.linspace(margin_x, img_w - margin_x, n_per_side)
        ys = np.linspace(margin_y, img_h - margin_y, n_per_side)
        return [[float(x), float(y), size, True] for y in ys for x in xs]

    def _open_subsky_box_editor(self):
        """'🖼 Preview & edit sample boxes...' — shows the current image
        with an editable grid of background-sample boxes over it. Click
        a box to toggle it off/on; click empty space to add a new one.
        The kept boxes are stored in self._subsky_boxes and, the next
        time this stage runs with a Siril subsky method, are pushed to
        Siril via set_image_bgsamples() so subsky uses them instead of
        auto-placing its own (per the sirilpy docs: subsky only
        auto-regenerates sample points when none have been provided)."""
        try:
            arr = self._get_current_image()
        except RuntimeError as e:
            QMessageBox.warning(self, "No image", str(e))
            return

        hwc = to_hwc_float(arr)
        stretched = display_autostretch(hwc) if self.chk_display_stretch.isChecked() \
            else hwc
        qimg = make_qimage(stretched)
        img_w, img_h = qimg.width(), qimg.height()
        if img_w <= 0 or img_h <= 0:
            QMessageBox.warning(self, "No image", "No image loaded in Siril.")
            return

        max_dim = 800.0
        scale = min(1.0, max_dim / max(img_w, img_h))
        disp_w, disp_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))

        existing = getattr(self, "_subsky_boxes", None)
        boxes = ([[x, y, sz, True] for x, y, sz in existing] if existing
                else self._generate_default_bg_boxes(img_w, img_h))

        dlg = QDialog(self)
        dlg.setWindowTitle("Preview & Edit Background Sample Boxes")
        dv = QVBoxLayout(dlg)
        info = QLabel(
            "Click a box to toggle it off (red) or back on (green). "
            "Click empty space to add a new one there. The kept (green) "
            "boxes are used instead of Siril's automatic placement the "
            "next time this stage runs with a Siril subsky method.")
        info.setWordWrap(True)
        dv.addWidget(info)

        canvas = QLabel()
        canvas.setFixedSize(disp_w, disp_h)
        canvas.setCursor(Qt.CursorShape.CrossCursor)
        dv.addWidget(canvas)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("New box size (px):"))
        size_spin = QSpinBox()
        size_spin.setRange(8, 300)
        size_spin.setValue(25)
        size_row.addWidget(size_spin)
        size_row.addStretch()
        dv.addLayout(size_row)

        base_pixmap = QPixmap.fromImage(qimg).scaled(
            disp_w, disp_h, Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation)

        def redraw():
            pix = QPixmap(base_pixmap)
            painter = QPainter(pix)
            for x, y, sz, kept in boxes:
                dx, dy = x * scale, y * scale
                dsz = max(4.0, sz * scale)
                painter.setPen(QPen(
                    QColor(60, 220, 90) if kept else QColor(230, 60, 60), 2))
                painter.drawRect(int(dx - dsz / 2), int(dy - dsz / 2),
                                 int(dsz), int(dsz))
            painter.end()
            canvas.setPixmap(pix)

        def on_click(ev):
            pos = ev.position().toPoint() if hasattr(ev, "position") else ev.pos()
            ix, iy = pos.x() / scale, pos.y() / scale
            for b in reversed(boxes):
                x, y, sz, kept = b
                if abs(ix - x) <= sz / 2 and abs(iy - y) <= sz / 2:
                    b[3] = not kept
                    redraw()
                    return
            boxes.append([ix, iy, float(size_spin.value()), True])
            redraw()

        canvas.mousePressEvent = on_click
        redraw()

        btn_row = QHBoxLayout()
        regen_btn = QPushButton("Regenerate default grid")

        def do_regen():
            boxes.clear()
            boxes.extend(self._generate_default_bg_boxes(img_w, img_h))
            redraw()
        regen_btn.clicked.connect(do_regen)
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(
            lambda: ([b.__setitem__(3, True) for b in boxes], redraw()))
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(
            lambda: ([b.__setitem__(3, False) for b in boxes], redraw()))
        btn_row.addWidget(regen_btn)
        btn_row.addWidget(select_all_btn)
        btn_row.addWidget(deselect_all_btn)
        btn_row.addStretch()
        dv.addLayout(btn_row)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dv.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            return

        kept = [(x, y, sz) for x, y, sz, k in boxes if k]
        if not kept:
            QMessageBox.warning(
                self, "No boxes kept",
                "Every sample box was deselected — reverting to Siril's "
                "automatic placement instead of an empty sample set.")
            self._subsky_boxes = None
            self.subsky_boxes_status.setText(
                "Using Siril's automatic sample placement (default).")
            return
        self._subsky_boxes = kept
        self.subsky_boxes_status.setText(
            f"{len(kept)} custom sample box(es) set — will be used "
            "instead of Siril's automatic placement next time this "
            "stage runs. Click above to edit again, or Regenerate/select "
            "none to go back to automatic.")
        self.status_label.setText(
            f"Remove background: {len(kept)} custom sample box(es) set.")

    def _exec_stage2(self, progress):
        method = self.bge_method_combo.currentIndex()
        progress("Remove background: fetching image...", 0.02)
        before = self._get_current_image()

        if method == 0:  # GraXpert AI
            model_name = self.bge_model_combo.currentText()
            model_path = self.bge_models.get(model_name)
            if not model_path:
                raise RuntimeError(
                    "No GraXpert background-extraction model found. Download one "
                    "via GraXpert or the GraXpert-AI script's Model Manager — "
                    "or switch the Method to Siril subsky.")
            background = graxpert_extract_background(
                before, model_path,
                smoothing=self.bge_smoothing_slider.value() / 100.0,
                progress=progress)
            progress("Remove background: applying correction...", 0.9)
            after = graxpert_apply_correction(
                before, background, self.bge_correction_combo.currentText())
            self._set_current_image(after, "AstroPipeline: GraXpert BGE")
            label = "GraXpert AI"
        else:  # Siril subsky
            custom_boxes = getattr(self, "_subsky_boxes", None)
            used_custom_boxes = False
            if custom_boxes:
                try:
                    self.siril.clear_image_bgsamples()
                    self.siril.set_image_bgsamples([
                        s.BGSample(position=(x, y), size=int(round(sz)))
                        for x, y, sz in custom_boxes])
                    used_custom_boxes = True
                except (AttributeError, s.DataError, s.CommandError,
                        s.SirilError) as e:
                    self.siril.log(
                        f"Remove background: couldn't apply the custom "
                        f"sample boxes ({e}) — this needs a newer sirilpy "
                        "than what's installed. Falling back to Siril's "
                        "automatic sample placement.", LogColor.SALMON)
            args = ["subsky"]
            if method == 1:
                args.append("-rbf")
                args.append(f"-smooth={self.subsky_smooth.value():.2f}")
            else:
                args.append(str(self.subsky_degree.value()))
            args.append(f"-samples={self.subsky_samples.value()}")
            args.append(f"-tolerance={self.subsky_tolerance.value():.1f}")
            progress("Remove background: running Siril subsky...", 0.4)
            self.siril.cmd(*args)
            after = self._get_current_image()
            label = "Siril subsky (RBF)" if method == 1 else \
                f"Siril subsky (poly deg {self.subsky_degree.value()})"
            if used_custom_boxes:
                label += f", {len(custom_boxes)} custom sample boxes"

        self._finish_stage(IDX_BGE, before, after,
                           "Remove background: done.",
                           f"Background extraction complete ({label})",
                           progress=progress)
