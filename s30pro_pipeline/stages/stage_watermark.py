"""Watermark stage mixin for UnifiedPipelineWindow."""

import os
import math
from datetime import datetime

import numpy as np
import cv2

from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSpinBox, QFileDialog,
)

from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_WM, WATERMARK_POSITIONS
from s30pro_pipeline.image_utils import to_hwc_float


# Canonical (English) field key -> i18n key for its checkbox label —
# also doubles as the label used in _WM_LABEL_MAP below for the field
# names *baked into the image* (see that constant's own comment for
# why those stay English-only regardless of self.lang).
_WM_FIELD_DEFS = [
    # (field key, i18n key, checked by default)
    ("object", "wm_field_object", True),
    ("date", "wm_field_date", True),
    ("telescope", "wm_field_telescope", True),
    ("integration", "wm_field_integration", False),
    ("fov", "wm_field_fov", False),
    ("size", "wm_field_size", False),
    ("bortle", "wm_field_bortle", False),
]

# Canonical (English) position value -> i18n key for its combo entry.
# The combo's *value* (read via currentData(), never currentText())
# always stays one of WATERMARK_POSITIONS' own English strings — both
# because settings JSON round-trips that exact string (see
# _collect_settings/_apply_settings) and because _render_watermark
# matches against it with plain "Right"/"Left"/"Top" substring checks;
# only the displayed label is translated.
_WM_POSITION_KEYS = {
    "Bottom-Right": "wm_pos_bottom_right", "Bottom-Left": "wm_pos_bottom_left",
    "Bottom-Center": "wm_pos_bottom_center", "Top-Right": "wm_pos_top_right",
    "Top-Left": "wm_pos_top_left", "Top-Center": "wm_pos_top_center",
}

# Same pattern for the integration-time unit combo — currentData() is
# always "Minutes"/"Hours"/"Seconds" (matched by
# _gather_watermark_fields and saved in settings JSON); only the shown
# text is translated.
_WM_UNIT_KEYS = [
    ("Minutes", "wm_unit_minutes"),
    ("Hours", "wm_unit_hours"),
    ("Seconds", "wm_unit_seconds"),
]

# Field labels baked directly into the image's pixels by cv2.putText
# (see _render_watermark) — these can NOT be translated to Chinese:
# OpenCV's built-in Hershey fonts have no CJK glyphs at all, so
# anything beyond Latin/basic punctuation would render as empty boxes.
# Properly supporting CJK watermark text would need a real font-
# rendering pipeline (e.g. compositing with PIL/Pillow and a CJK TTF)
# — out of scope for this UI-only i18n pass. The *panel* around this
# (checkboxes, tooltips) is still fully bilingual; only the pixels
# baked into the photo itself stay English.
_WM_LABEL_MAP = {
    "object": "Object", "date": "Date", "integration": "Integration",
    "telescope": "Telescope", "fov": "FOV", "size": "Image Size",
    "bortle": "Bortle",
}


class WatermarkMixin:
    def _build_stage_watermark(self):
        # Title stays the literal "Watermark" for now, not self.tr(...):
        # the pane header AND the sidebar rail both draw stage titles
        # from the one shared STAGES list in constants.py (see
        # ui_shell.py's StageRail/RAIL_LABELS), so translating just this
        # stage's title here would leave it out of sync with the rail
        # entry until every stage's title is handled together — that's
        # Phase 7 (main window chrome) in the i18n rollout plan.
        box, v = self._stage_box(13, "Watermark", enabled_check=False)
        self.stage_wm_box = box

        self.wm_info_label = QLabel(self.tr("wm_info"))
        self.wm_info_label.setObjectName("SubHeader")
        self.wm_info_label.setWordWrap(True)
        v.addWidget(self.wm_info_label)

        self.wm_field_checkboxes = {}
        fields_row = QGridLayout()
        fields_row.setHorizontalSpacing(10)
        fields_row.setVerticalSpacing(6)
        for i, (key, i18n_key, default_on) in enumerate(_WM_FIELD_DEFS):
            cb = QCheckBox(self.tr(i18n_key))
            cb.setChecked(default_on)
            self.wm_field_checkboxes[key] = cb
            fields_row.addWidget(cb, i // 2, i % 2)
        v.addLayout(fields_row)

        integration_unit_row = QHBoxLayout()
        integration_unit_row.setSpacing(10)
        self.wm_integration_unit_label = QLabel(
            self.tr("wm_integration_unit_label"))
        integration_unit_row.addWidget(self.wm_integration_unit_label)
        self.wm_integration_unit_combo = QComboBox()
        for value, i18n_key in _WM_UNIT_KEYS:
            self.wm_integration_unit_combo.addItem(self.tr(i18n_key), value)
        self.wm_integration_unit_combo.setToolTip(
            self.tr("wm_integration_unit_tooltip"))
        integration_unit_row.addWidget(self.wm_integration_unit_combo, 1)
        v.addLayout(integration_unit_row)

        author_row = QHBoxLayout()
        author_row.setSpacing(10)
        self.wm_author_checkbox = QCheckBox(self.tr("wm_author"))
        self.wm_author_checkbox.setToolTip(self.tr("wm_author_tooltip"))
        author_row.addWidget(self.wm_author_checkbox)
        self.wm_author_edit = QLineEdit()
        self.wm_author_edit.setPlaceholderText(
            self.tr("wm_author_placeholder"))
        author_row.addWidget(self.wm_author_edit, 1)
        v.addLayout(author_row)

        opts_row = QHBoxLayout()
        opts_row.setSpacing(10)
        self.wm_position_label = QLabel(self.tr("wm_position_label"))
        opts_row.addWidget(self.wm_position_label)
        self.wm_position_combo = QComboBox()
        for value in WATERMARK_POSITIONS:
            self.wm_position_combo.addItem(
                self.tr(_WM_POSITION_KEYS[value]), value)
        opts_row.addWidget(self.wm_position_combo, 1)
        self.wm_opacity_label = QLabel(self.tr("wm_opacity_label"))
        opts_row.addWidget(self.wm_opacity_label)
        self.wm_alpha_spin = QSpinBox()
        self.wm_alpha_spin.setRange(0, 100)
        self.wm_alpha_spin.setValue(55)
        self.wm_alpha_spin.setSuffix("%")
        self.wm_alpha_spin.setToolTip(self.tr("wm_opacity_tooltip"))
        opts_row.addWidget(self.wm_alpha_spin)
        v.addLayout(opts_row)

        self.wm_two_col_checkbox = QCheckBox(self.tr("wm_two_col"))
        self.wm_two_col_checkbox.setToolTip(self.tr("wm_two_col_tooltip"))
        v.addWidget(self.wm_two_col_checkbox)

        row, self.stage_wm_run = self._run_row(
            lambda: self._launch([self._exec_stage_watermark]), undo_stage=IDX_WM)
        v.addLayout(row)

        save_row = QHBoxLayout()
        self.wm_save_btn = QPushButton(self.tr("wm_save_btn"))
        self.wm_save_btn.setToolTip(self.tr("wm_save_tooltip"))
        self.wm_save_btn.clicked.connect(self.on_save_watermarked_image)
        save_row.addWidget(self.wm_save_btn)
        self.wm_remove_all_btn = QPushButton(self.tr("wm_remove_all_btn"))
        self.wm_remove_all_btn.setToolTip(self.tr("wm_remove_all_tooltip"))
        self.wm_remove_all_btn.clicked.connect(self._remove_all_watermarks)
        save_row.addWidget(self.wm_remove_all_btn)
        save_row.addStretch()
        v.addLayout(save_row)
        return box

    def retranslate_ui_watermark(self):
        """Re-applies every Watermark widget's text/tooltip to the
        current self.lang — see retranslate_ui's docstring for when
        this runs. Combo boxes are rebuilt in place (clear + repopulate
        with translated labels) rather than using setItemText, since
        that's the simplest way to keep each item's underlying
        currentData() value untouched while its displayed text
        changes; current selection is restored by that same data value
        so mid-edit choices survive a language toggle."""
        self.wm_info_label.setText(self.tr("wm_info"))
        for key, i18n_key, _default_on in _WM_FIELD_DEFS:
            self.wm_field_checkboxes[key].setText(self.tr(i18n_key))
        self.wm_integration_unit_label.setText(
            self.tr("wm_integration_unit_label"))
        self.wm_integration_unit_combo.setToolTip(
            self.tr("wm_integration_unit_tooltip"))
        cur_unit = self.wm_integration_unit_combo.currentData()
        self.wm_integration_unit_combo.clear()
        for value, i18n_key in _WM_UNIT_KEYS:
            self.wm_integration_unit_combo.addItem(self.tr(i18n_key), value)
        idx = self.wm_integration_unit_combo.findData(cur_unit)
        if idx >= 0:
            self.wm_integration_unit_combo.setCurrentIndex(idx)
        self.wm_author_checkbox.setText(self.tr("wm_author"))
        self.wm_author_checkbox.setToolTip(self.tr("wm_author_tooltip"))
        self.wm_author_edit.setPlaceholderText(
            self.tr("wm_author_placeholder"))
        self.wm_position_label.setText(self.tr("wm_position_label"))
        cur_pos = self.wm_position_combo.currentData()
        self.wm_position_combo.clear()
        for value in WATERMARK_POSITIONS:
            self.wm_position_combo.addItem(
                self.tr(_WM_POSITION_KEYS[value]), value)
        idx = self.wm_position_combo.findData(cur_pos)
        if idx >= 0:
            self.wm_position_combo.setCurrentIndex(idx)
        self.wm_opacity_label.setText(self.tr("wm_opacity_label"))
        self.wm_alpha_spin.setToolTip(self.tr("wm_opacity_tooltip"))
        self.wm_two_col_checkbox.setText(self.tr("wm_two_col"))
        self.wm_two_col_checkbox.setToolTip(self.tr("wm_two_col_tooltip"))
        self.wm_save_btn.setText(self.tr("wm_save_btn"))
        self.wm_save_btn.setToolTip(self.tr("wm_save_tooltip"))
        self.wm_remove_all_btn.setText(self.tr("wm_remove_all_btn"))
        self.wm_remove_all_btn.setToolTip(self.tr("wm_remove_all_tooltip"))

    @staticmethod
    def _clean_telescope_name(raw):
        """Strip a trailing '_<serial-number>' suffix some smart telescopes
        append to the TELESCOP/INSTRUME FITS header (e.g. 'ZWO Seestar S30
        Pro_2409020001' -> 'ZWO Seestar S30 Pro'). Left alone if there's no
        underscore to split on."""
        raw = (raw or "").strip()
        return raw.split("_", 1)[0].strip() if "_" in raw else raw

    def _gather_watermark_fields(self):
        """Same underlying data as the info bar (_update_image_info),
        without icons and with the telescope name's serial-number suffix
        stripped. Returns {field_key: display_string}; a key is omitted if
        that data isn't available, matching the info bar's own behavior."""
        fields = {}
        try:
            hdr = self.siril.get_image_fits_header(return_as="dict")
        except Exception:
            return fields

        obj = str(hdr.get("OBJECT", "")).strip()
        if obj and obj.lower() != "unknown":
            fields["object"] = obj

        if self.date_range:
            d0, d1 = self.date_range
            fields["date"] = d0 if d0 == d1 else f"{d0} → {d1}"
        else:
            date_obs = str(hdr.get("DATE-OBS", ""))
            if date_obs:
                fields["date"] = date_obs.split("T")[0]

        try:
            live = float(hdr.get("LIVETIME", 0) or 0)
            cnt = int(hdr.get("STACKCNT", 0) or 0)
            exp = float(hdr.get("EXPTIME", 0) or 0)
            if live <= 0 and cnt and exp:
                live = cnt * exp
            if live > 0:
                unit = getattr(self, "wm_integration_unit_combo", None)
                # currentData(), not currentText() — see the matching
                # comment in _build_stage_watermark: the combo's shown
                # label is translated, but this comparison needs the
                # canonical English value.
                unit_text = unit.currentData() if unit else "Minutes"
                if unit_text == "Hours":
                    txt = f"{live / 3600.0:.1f} h"
                elif unit_text == "Seconds":
                    txt = f"{live:.0f} s"
                else:
                    txt = f"{live / 60.0:.0f} min"
                if cnt and exp:
                    txt += f" ({cnt}×{exp:.0f}s)"
                fields["integration"] = txt
        except Exception:
            pass

        try:
            w_px = int(hdr.get("NAXIS1", 0) or 0)
            h_px = int(hdr.get("NAXIS2", 0) or 0)
            scale = 0.0
            try:
                cd11 = float(hdr.get("CD1_1", 0) or 0)
                cd12 = float(hdr.get("CD1_2", 0) or 0)
                cd21 = float(hdr.get("CD2_1", 0) or 0)
                cd22 = float(hdr.get("CD2_2", 0) or 0)
                det = abs(cd11 * cd22 - cd12 * cd21)
                if det > 0:
                    scale = math.sqrt(det) * 3600.0
                else:
                    cdelt = abs(float(hdr.get("CDELT1", 0) or 0))
                    if cdelt > 1e-9:
                        scale = cdelt * 3600.0
            except Exception:
                pass
            if scale <= 0:
                focal = float(hdr.get("FOCALLEN", 0) or 0)
                pxsz = float(hdr.get("XPIXSZ", 0) or 0)
                if focal > 0 and pxsz > 0:
                    scale = 206.265 * pxsz / focal
            if w_px and h_px and scale > 0:
                fov_w = scale * w_px / 3600.0
                fov_h = scale * h_px / 3600.0
                fields["fov"] = f"{fov_w:.2f}°×{fov_h:.2f}°"
            if w_px and h_px:
                fields["size"] = f"{w_px}×{h_px} px"
        except Exception:
            pass

        tele = str(hdr.get("TELESCOP", "") or hdr.get("INSTRUME", "")).strip()
        if tele:
            fields["telescope"] = self._clean_telescope_name(tele)

        if self.estimated_bortle:
            b = self.estimated_bortle
            fields["bortle"] = f"Bortle {b['bortle']} ({b['name']})"

        return fields

    @staticmethod
    def _render_watermark(hwc, fields_selected, position, alpha,
                          two_column=False):
        """Draw a semi-transparent info block onto `hwc` ((h,w,3) float
        0..1, raw FITS row-order — row 0 is the bottom of the image) and
        return a BGR uint8 canvas *in display orientation* (flipped once
        from `hwc`, matching Siril's own on-screen display). `fields_selected`
        is an ordered list of (label, value) strings already filtered to
        what the user checked. Uses HERSHEY_DUPLEX (cleaner, less
        "technical-looking" than the HERSHEY_SIMPLEX font used elsewhere
        in this app) since this text is meant to look presentable on a
        finished image, not just legible for a quick diagnostic overlay.

        The flip matters here: text baked directly into a raw FITS-order
        array would come out upside-down once Siril flips the whole image
        for its own display (or the array is otherwise saved/shown
        right-side up elsewhere). Drawing on the display-oriented array
        instead means the caller
        must flip the *result* back to FITS order before pushing it back
        into Siril — see `_exec_stage_watermark`.

        `two_column`: lay the lines out in two side-by-side columns
        (roughly half the rows each) instead of one vertical list —
        wider block, but noticeably shorter."""
        canvas = (np.clip(np.flipud(hwc), 0.0, 1.0) * 255).astype(np.uint8)
        canvas = cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR)
        H, W = canvas.shape[:2]
        if not fields_selected:
            return canvas

        res_scale = float(np.clip(max(W, H) / 1600.0, 1.0, 4.0))
        font = cv2.FONT_HERSHEY_DUPLEX
        fs = 0.55 * res_scale
        th = max(1, int(round(fs * 1.8)))
        line_gap = int(round(10 * res_scale))
        pad = int(round(14 * res_scale))

        lines = [f"{label}: {value}" for label, value in fields_selected]
        sizes = [cv2.getTextSize(t, font, fs, th)[0] for t in lines]
        line_h = max(s[1] for s in sizes)

        if two_column and len(lines) > 1:
            half = (len(lines) + 1) // 2
            col1, col2 = lines[:half], lines[half:]
            col_gap = int(round(28 * res_scale))
            w1 = max(cv2.getTextSize(t, font, fs, th)[0][0] for t in col1)
            w2 = (max(cv2.getTextSize(t, font, fs, th)[0][0] for t in col2)
                  if col2 else 0)
            block_w = pad + w1 + (col_gap + w2 if col2 else 0) + pad
            n_rows = max(len(col1), len(col2))
            block_h = n_rows * (line_h + line_gap) + pad
        else:
            two_column = False
            text_w = max(s[0] for s in sizes)
            block_w = text_w + 2 * pad
            block_h = len(lines) * (line_h + line_gap) + pad
            col1, col2, w1, col_gap = lines, [], 0, 0

        margin = int(round(18 * res_scale))
        if "Right" in position:
            x0 = W - margin - block_w
        elif "Left" in position:
            x0 = margin
        else:  # Center
            x0 = (W - block_w) // 2
        y0 = margin if "Top" in position else H - margin - block_h
        x0 = int(np.clip(x0, 0, max(0, W - block_w)))
        y0 = int(np.clip(y0, 0, max(0, H - block_h)))
        x1, y1 = x0 + block_w, y0 + block_h

        overlay = canvas.copy()
        cv2.rectangle(overlay, (x0, y0), (x1, y1), (20, 18, 16), -1)
        canvas = cv2.addWeighted(overlay, alpha, canvas, 1.0 - alpha, 0)

        if two_column:
            for i in range(max(len(col1), len(col2))):
                ty = y0 + pad + line_h + i * (line_h + line_gap)
                if i < len(col1):
                    cv2.putText(canvas, col1[i], (x0 + pad, ty), font, fs,
                               (235, 235, 235), th, cv2.LINE_AA)
                if i < len(col2):
                    cv2.putText(canvas, col2[i],
                               (x0 + pad + w1 + col_gap, ty), font, fs,
                               (235, 235, 235), th, cv2.LINE_AA)
        else:
            ty = y0 + pad + line_h
            for text in lines:
                cv2.putText(canvas, text, (x0 + pad, ty), font, fs,
                           (235, 235, 235), th, cv2.LINE_AA)
                ty += line_h + line_gap

        return canvas

    def _exec_stage_watermark(self, progress):
        progress(self.tr("wm_progress_fetching"), 0.1)
        before = self._get_current_image()
        # Remembered once per "clean" streak so "Remove all watermarks" can
        # undo every watermark applied so far, not just the last run — the
        # per-stage Undo button already covers the single-last-run case.
        if getattr(self, "_wm_baseline", None) is None:
            self._wm_baseline = before.copy()
        hwc = to_hwc_float(before)

        progress(self.tr("wm_progress_gathering"), 0.3)
        available = self._gather_watermark_fields()
        # _WM_LABEL_MAP (module-level, see its own comment) deliberately
        # stays English — these are the labels baked into the image's
        # pixels, which OpenCV's Hershey fonts can't render in Chinese.
        selected = [(_WM_LABEL_MAP.get(key, key.title()), available[key])
                   for key, cb in self.wm_field_checkboxes.items()
                   if cb.isChecked() and key in available]
        author = self.wm_author_edit.text().strip()
        if self.wm_author_checkbox.isChecked() and author:
            selected.append(("Author", author))
        if not selected:
            raise RuntimeError(self.tr("wm_no_fields_error"))

        progress(self.tr("wm_progress_drawing"), 0.6)
        # currentData(), not currentText() — see _build_stage_watermark's
        # comment: the combo shows a translated label but its value is
        # always the canonical English position string _render_watermark
        # matches against.
        position = self.wm_position_combo.currentData()
        alpha = self.wm_alpha_spin.value() / 100.0
        two_column = self.wm_two_col_checkbox.isChecked()
        # `canvas` comes back in display orientation (see _render_watermark's
        # docstring) — correct as-is for saving/exporting, but Siril's own
        # pixel data is FITS row-order, so it needs one more flip before
        # going back into the working image (otherwise the baked-in text
        # would appear upside-down once Siril displays it).
        canvas = self._render_watermark(hwc, selected, position, alpha,
                                        two_column=two_column)
        self._last_watermarked_canvas = canvas.copy()

        watermarked_hwc = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(
            np.float32) / 255.0
        watermarked_hwc = np.flipud(watermarked_hwc)
        after = np.transpose(watermarked_hwc, (2, 0, 1)).astype(np.float32)
        self._set_current_image(after, "AstroPipeline: watermark")
        self._finish_stage(
            IDX_WM, before, after, self.tr("wm_progress_done"),
            f"Watermark applied ({len(selected)} field(s), {position})",
            before_linear=False, after_linear=False, progress=progress)

    def on_save_watermarked_image(self):
        """Export the last watermarked canvas as JPEG or PNG, wherever the
        user chooses. Doesn't touch Siril or re-run the stage — just
        re-encodes the raster already produced by the last Watermark run."""
        canvas = getattr(self, "_last_watermarked_canvas", None)
        if canvas is None:
            QMessageBox.information(
                self, self.tr("wm_no_image_title"),
                self.tr("wm_no_image_body"))
            return
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        default_path = os.path.join(self.cwd, f"watermarked_{now}.jpg")
        path, _ = QFileDialog.getSaveFileName(
            self, self.tr("wm_save_dialog_title"), default_path,
            "JPEG (*.jpg *.jpeg);;PNG (*.png)")
        if not path:
            return
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext in (".jpg", ".jpeg"):
                cv2.imwrite(path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
            elif ext == ".png":
                cv2.imwrite(path, canvas, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            else:
                raise RuntimeError(self.tr("wm_unsupported_format").format(
                    ext=ext or "(none)"))
            self.status_label.setText(self.tr("wm_saved_status").format(
                name=os.path.basename(path)))
            self.siril.log(f"Watermarked image saved: {path}", LogColor.GREEN)
        except Exception as e:
            QMessageBox.critical(self, self.tr("wm_save_failed_title"), str(e))

    def _remove_all_watermarks(self):
        """Restore the image to how it looked before the very first
        Watermark run since the baseline was last captured — undoes every
        watermark applied so far in this streak, not just the last one
        (unlike the per-stage Undo button, which only reverts one run)."""
        baseline = getattr(self, "_wm_baseline", None)
        if baseline is None:
            QMessageBox.information(
                self, self.tr("wm_no_watermark_title"),
                self.tr("wm_no_image_body"))
            return
        reply = QMessageBox.question(
            self, self.tr("wm_remove_confirm_title"),
            self.tr("wm_remove_confirm_body"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def job(progress):
            progress(self.tr("wm_progress_removing"), 0.3)
            self._set_current_image(
                baseline, "AstroPipeline: remove all watermarks")
            self._store_snapshot(IDX_WM, baseline, baseline,
                                 before_linear=False, after_linear=False)
            progress(self.tr("wm_progress_removed"), 1.0)
            self.siril.log(
                "Watermark: all watermarks removed (restored pre-watermark "
                "image).", LogColor.GREEN)
        self._launch([job])

        self._wm_baseline = None
        self._last_watermarked_canvas = None
        self.stage_backups.pop(IDX_WM, None)
        btn = self.undo_buttons.get(IDX_WM)
        if btn is not None:
            btn.setEnabled(False)
