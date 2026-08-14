"""SCNR (green noise removal) stage mixin for UnifiedPipelineWindow."""

from PyQt6.QtWidgets import QLabel, QHBoxLayout, QComboBox, QDoubleSpinBox, QCheckBox

from s30pro_pipeline.constants import IDX_SCNR


class ScnrMixin:
    def _build_stage_scnr(self):
        box, v = self._stage_box(3, "Remove Green Noise (SCNR)")
        self.stage_scnr_box = box

        info = QLabel("Runs Siril's rmgreen command — removes the green cast "
                      "typical of OSC stacks. Safe to run more than once.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        scnr_row = QHBoxLayout()
        scnr_row.setSpacing(10)
        scnr_row.addWidget(QLabel("Type:"))
        self.scnr_type_combo = QComboBox()
        self.scnr_type_combo.addItems(["Average neutral", "Maximum neutral"])
        scnr_row.addWidget(self.scnr_type_combo, 1)
        scnr_row.addWidget(QLabel("Amount:"))
        self.scnr_amount = QDoubleSpinBox()
        self.scnr_amount.setRange(0.0, 1.0)
        self.scnr_amount.setSingleStep(0.05)
        self.scnr_amount.setValue(1.0)
        scnr_row.addWidget(self.scnr_amount)
        self.scnr_preserve_checkbox = QCheckBox("Preserve lightness")
        self.scnr_preserve_checkbox.setChecked(True)
        scnr_row.addWidget(self.scnr_preserve_checkbox)
        scnr_row.addStretch()
        v.addLayout(scnr_row)

        row, self.stage_scnr_run = self._run_row(
            lambda: self._launch([self._exec_stage_scnr]), undo_stage=IDX_SCNR)
        v.addLayout(row)
        return box

    def _exec_stage_scnr(self, progress):
        progress("SCNR: fetching image...", 0.1)
        before = self._get_current_image()
        progress("SCNR: removing green noise...", 0.4)
        args = ["rmgreen"]
        if not self.scnr_preserve_checkbox.isChecked():
            args.append("-nopreserve")
        args.append("0" if self.scnr_type_combo.currentIndex() == 0 else "1")
        args.append(f"{self.scnr_amount.value():.2f}")
        self.siril.cmd(*args)
        after = self._get_current_image()
        self._finish_stage(IDX_SCNR, before, after,
                           "SCNR: done.", "Green noise removed (SCNR)",
                           progress=progress)
