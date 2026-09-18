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


_BGE_METHOD_KEYS = ["bge_method_graxpert", "bge_method_rbf", "bge_method_poly"]
_BGE_CORRECTION_KEYS = [
    ("subtraction", "bge_correction_subtraction"),
    ("division", "bge_correction_division"),
]


class BgeMixin:
    def _build_stage2(self):
        # Title stays literal English for now — stage titles move
        # together in Phase 7 (see stage_watermark.py's comment).
        box, v = self._stage_box(5, "Remove Background")
        self.stage2_box = box

        m = QHBoxLayout()
        m.setSpacing(10)
        self.bge_method_row_label = QLabel(self.tr("bge_method_label"))
        m.addWidget(self.bge_method_row_label)
        self.bge_method_combo = QComboBox()
        # Plain addItems: read via currentIndex() everywhere, never
        # currentText(), so translated labels are safe here.
        self.bge_method_combo.addItems(
            [self.tr(k) for k in _BGE_METHOD_KEYS])
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
        self.bge_model_row_label = QLabel(self.tr("bge_model_label"))
        g.addWidget(self.bge_model_row_label, 0, 0)
        self.bge_model_combo = QComboBox()
        self.bge_models = get_available_local_models("bge-ai-models")
        self.bge_model_combo.addItems(
            sorted(self.bge_models.keys())
            or [self.tr("bge_no_models_found")])
        if self.bge_models:
            self.bge_model_combo.setCurrentIndex(self.bge_model_combo.count() - 1)
        g.addWidget(self.bge_model_combo, 0, 1)
        self.bge_correction_row_label = QLabel(self.tr("bge_correction_label"))
        g.addWidget(self.bge_correction_row_label, 1, 0)
        self.bge_correction_combo = QComboBox()
        # currentData(), not currentText() — see S30Pro_Pipeline.py's
        # settings-JSON comment and _exec_stage2's own comment below.
        for value, i18n_key in _BGE_CORRECTION_KEYS:
            self.bge_correction_combo.addItem(self.tr(i18n_key), value)
        g.addWidget(self.bge_correction_combo, 1, 1)
        gx_v.addLayout(g)

        sm = QHBoxLayout()
        self.bge_smoothing_row_label = QLabel(self.tr("bge_smoothing_label"))
        sm.addWidget(self.bge_smoothing_row_label)
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
        self.bge_samples_row_label = QLabel(self.tr("bge_samples_label"))
        sg.addWidget(self.bge_samples_row_label, 0, 0)
        self.subsky_samples = QSpinBox()
        self.subsky_samples.setRange(4, 100)
        self.subsky_samples.setValue(20)
        sg.addWidget(self.subsky_samples, 0, 1)
        self.bge_tolerance_row_label = QLabel(self.tr("bge_tolerance_label"))
        sg.addWidget(self.bge_tolerance_row_label, 0, 2)
        self.subsky_tolerance = QDoubleSpinBox()
        self.subsky_tolerance.setRange(0.1, 10.0)
        self.subsky_tolerance.setSingleStep(0.1)
        self.subsky_tolerance.setValue(2.0)
        sg.addWidget(self.subsky_tolerance, 0, 3)
        self.bge_rbf_smooth_row_label = QLabel(self.tr("bge_rbf_smooth_label"))
        sg.addWidget(self.bge_rbf_smooth_row_label, 1, 0)
        self.subsky_smooth = QDoubleSpinBox()
        self.subsky_smooth.setRange(0.0, 1.0)
        self.subsky_smooth.setSingleStep(0.05)
        self.subsky_smooth.setValue(0.5)
        sg.addWidget(self.subsky_smooth, 1, 1)
        self.bge_poly_degree_row_label = QLabel(self.tr("bge_poly_degree_label"))
        sg.addWidget(self.bge_poly_degree_row_label, 1, 2)
        self.subsky_degree = QSpinBox()
        self.subsky_degree.setRange(1, 4)
        self.subsky_degree.setValue(2)
        sg.addWidget(self.subsky_degree, 1, 3)
        ss_v.addLayout(sg)
        self.bge_subsky_info_label = QLabel(self.tr("bge_subsky_info"))
        self.bge_subsky_info_label.setObjectName("SubHeader")
        self.bge_subsky_info_label.setWordWrap(True)
        ss_v.addWidget(self.bge_subsky_info_label)
        self.subsky_boxes_btn = QPushButton(self.tr("bge_boxes_btn"))
        self.subsky_boxes_btn.setToolTip(self.tr("bge_boxes_tooltip"))
        self.subsky_boxes_btn.clicked.connect(self._open_subsky_box_editor)
        ss_v.addWidget(self.subsky_boxes_btn)
        self.subsky_boxes_status = QLabel(self.tr("bge_boxes_status_default"))
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

    def retranslate_ui_bge(self):
        self.bge_method_row_label.setText(self.tr("bge_method_label"))
        cur_method = self.bge_method_combo.currentIndex()
        for i, key in enumerate(_BGE_METHOD_KEYS):
            self.bge_method_combo.setItemText(i, self.tr(key))
        self.bge_method_combo.setCurrentIndex(cur_method)
        self.bge_model_row_label.setText(self.tr("bge_model_label"))
        if not self.bge_models and self.bge_model_combo.count() == 1:
            self.bge_model_combo.setItemText(0, self.tr("bge_no_models_found"))
        self.bge_correction_row_label.setText(self.tr("bge_correction_label"))
        cur_corr = self.bge_correction_combo.currentData()
        self.bge_correction_combo.clear()
        for value, i18n_key in _BGE_CORRECTION_KEYS:
            self.bge_correction_combo.addItem(self.tr(i18n_key), value)
        idx = self.bge_correction_combo.findData(cur_corr)
        if idx >= 0:
            self.bge_correction_combo.setCurrentIndex(idx)
        self.bge_smoothing_row_label.setText(self.tr("bge_smoothing_label"))
        self.bge_samples_row_label.setText(self.tr("bge_samples_label"))
        self.bge_tolerance_row_label.setText(self.tr("bge_tolerance_label"))
        self.bge_rbf_smooth_row_label.setText(self.tr("bge_rbf_smooth_label"))
        self.bge_poly_degree_row_label.setText(self.tr("bge_poly_degree_label"))
        self.bge_subsky_info_label.setText(self.tr("bge_subsky_info"))
        self.subsky_boxes_btn.setText(self.tr("bge_boxes_btn"))
        self.subsky_boxes_btn.setToolTip(self.tr("bge_boxes_tooltip"))
        # subsky_boxes_status holds transient, state-dependent text — see
        # _open_subsky_box_editor, which sets either the default text or
        # a custom-box-count summary depending on self._subsky_boxes.
        custom = getattr(self, "_subsky_boxes", None)
        if custom:
            self.subsky_boxes_status.setText(
                self.tr("bge_boxes_status_custom").format(n=len(custom)))
        else:
            self.subsky_boxes_status.setText(
                self.tr("bge_boxes_status_default"))

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
            QMessageBox.warning(self, self.tr("bge_no_image_title"), str(e))
            return

        hwc = to_hwc_float(arr)
        stretched = display_autostretch(hwc) if self.chk_display_stretch.isChecked() \
            else hwc
        qimg = make_qimage(stretched)
        img_w, img_h = qimg.width(), qimg.height()
        if img_w <= 0 or img_h <= 0:
            QMessageBox.warning(self, self.tr("bge_no_image_title"),
                                self.tr("bge_no_image_loaded"))
            return

        max_dim = 800.0
        scale = min(1.0, max_dim / max(img_w, img_h))
        disp_w, disp_h = max(1, int(img_w * scale)), max(1, int(img_h * scale))

        existing = getattr(self, "_subsky_boxes", None)
        boxes = ([[x, y, sz, True] for x, y, sz in existing] if existing
                else self._generate_default_bg_boxes(img_w, img_h))

        dlg = QDialog(self)
        dlg.setWindowTitle(self.tr("bge_dialog_title"))
        dv = QVBoxLayout(dlg)
        info = QLabel(self.tr("bge_dialog_info"))
        info.setWordWrap(True)
        dv.addWidget(info)

        canvas = QLabel()
        canvas.setFixedSize(disp_w, disp_h)
        canvas.setCursor(Qt.CursorShape.CrossCursor)
        dv.addWidget(canvas)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel(self.tr("bge_new_box_size_label")))
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
        regen_btn = QPushButton(self.tr("bge_regen_btn"))

        def do_regen():
            boxes.clear()
            boxes.extend(self._generate_default_bg_boxes(img_w, img_h))
            redraw()
        regen_btn.clicked.connect(do_regen)
        select_all_btn = QPushButton(self.tr("bge_select_all_btn"))
        select_all_btn.clicked.connect(
            lambda: ([b.__setitem__(3, True) for b in boxes], redraw()))
        deselect_all_btn = QPushButton(self.tr("bge_deselect_all_btn"))
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
                self, self.tr("bge_no_boxes_title"), self.tr("bge_no_boxes_body"))
            self._subsky_boxes = None
            self.subsky_boxes_status.setText(
                self.tr("bge_boxes_status_default"))
            return
        self._subsky_boxes = kept
        self.subsky_boxes_status.setText(
            self.tr("bge_boxes_status_custom").format(n=len(kept)))
        self.status_label.setText(
            self.tr("bge_status_custom").format(n=len(kept)))

    def _exec_stage2(self, progress):
        method = self.bge_method_combo.currentIndex()
        progress(self.tr("bge_progress_fetching"), 0.02)
        before = self._get_current_image()

        if method == 0:  # GraXpert AI
            model_name = self.bge_model_combo.currentText()
            model_path = self.bge_models.get(model_name)
            if not model_path:
                raise RuntimeError(self.tr("bge_no_model_error"))
            background = graxpert_extract_background(
                before, model_path,
                smoothing=self.bge_smoothing_slider.value() / 100.0,
                progress=progress)
            progress(self.tr("bge_progress_correcting"), 0.9)
            # currentData(), not currentText() — see the settings-JSON
            # comment in S30Pro_Pipeline.py.
            after = graxpert_apply_correction(
                before, background, self.bge_correction_combo.currentData())
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
            progress(self.tr("bge_progress_subsky"), 0.4)
            self.siril.cmd(*args)
            after = self._get_current_image()
            label = "Siril subsky (RBF)" if method == 1 else \
                f"Siril subsky (poly deg {self.subsky_degree.value()})"
            if used_custom_boxes:
                label += f", {len(custom_boxes)} custom sample boxes"

        self._finish_stage(IDX_BGE, before, after,
                           self.tr("bge_progress_done"),
                           f"Background extraction complete ({label})",
                           progress=progress)
