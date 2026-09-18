"""SCNR (green noise removal) stage mixin for UnifiedPipelineWindow."""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QDoubleSpinBox, QCheckBox

from s30pro_pipeline.constants import IDX_SCNR


class ScnrMixin:
    def _build_stage_scnr(self):
        # Title stays literal English for now — see stage_watermark.py's
        # _build_stage_watermark comment: stage titles are handled all
        # together in Phase 7 (main window chrome), not per-stage.
        box, v = self._stage_box(3, "Remove Green Noise (SCNR)")
        self.stage_scnr_box = box

        self.scnr_info_label = QLabel(self.tr("scnr_info"))
        self.scnr_info_label.setObjectName("SubHeader")
        self.scnr_info_label.setWordWrap(True)
        v.addWidget(self.scnr_info_label)

        # Two rows instead of one — four controls (combo, label, spin,
        # checkbox) side by side don't fit the ~300-480px pane at any
        # window width without forcing it to scroll sideways.
        type_row = QHBoxLayout()
        type_row.setSpacing(10)
        self.scnr_type_row_label = QLabel(self.tr("scnr_type_label"))
        type_row.addWidget(self.scnr_type_row_label)
        self.scnr_type_combo = QComboBox()
        # Plain addItems (not addItem+data) is fine here, unlike
        # Watermark's combos: the code below reads currentIndex(), not
        # currentText(), so a translated display label can't break
        # anything downstream.
        self.scnr_type_combo.addItems(
            [self.tr("scnr_type_avg"), self.tr("scnr_type_max")])
        type_row.addWidget(self.scnr_type_combo, 1)
        v.addLayout(type_row)

        amount_row = QHBoxLayout()
        amount_row.setSpacing(10)
        self.scnr_amount_label = QLabel(self.tr("scnr_amount_label"))
        amount_row.addWidget(self.scnr_amount_label)
        self.scnr_amount = QDoubleSpinBox()
        self.scnr_amount.setRange(0.0, 1.0)
        self.scnr_amount.setSingleStep(0.05)
        self.scnr_amount.setValue(1.0)
        amount_row.addWidget(self.scnr_amount)
        self.scnr_preserve_checkbox = QCheckBox(self.tr("scnr_preserve"))
        self.scnr_preserve_checkbox.setChecked(True)
        amount_row.addWidget(self.scnr_preserve_checkbox)
        amount_row.addStretch()
        v.addLayout(amount_row)

        row, self.stage_scnr_run = self._run_row(
            lambda: self._launch([self._exec_stage_scnr]), undo_stage=IDX_SCNR)
        v.addLayout(row)
        return box

    def retranslate_ui_scnr(self):
        self.scnr_info_label.setText(self.tr("scnr_info"))
        self.scnr_type_row_label.setText(self.tr("scnr_type_label"))
        cur = self.scnr_type_combo.currentIndex()
        self.scnr_type_combo.setItemText(0, self.tr("scnr_type_avg"))
        self.scnr_type_combo.setItemText(1, self.tr("scnr_type_max"))
        self.scnr_type_combo.setCurrentIndex(cur)
        self.scnr_amount_label.setText(self.tr("scnr_amount_label"))
        self.scnr_preserve_checkbox.setText(self.tr("scnr_preserve"))

    def _exec_stage_scnr(self, progress):
        progress(self.tr("scnr_progress_fetching"), 0.1)
        before = self._get_current_image()
        progress(self.tr("scnr_progress_removing"), 0.4)
        args = ["rmgreen"]
        if not self.scnr_preserve_checkbox.isChecked():
            args.append("-nopreserve")
        args.append("0" if self.scnr_type_combo.currentIndex() == 0 else "1")
        args.append(f"{self.scnr_amount.value():.2f}")
        self.siril.cmd(*args)
        after = self._get_current_image()
        self._finish_stage(IDX_SCNR, before, after,
                           self.tr("scnr_progress_done"),
                           "Green noise removed (SCNR)",
                           progress=progress)
