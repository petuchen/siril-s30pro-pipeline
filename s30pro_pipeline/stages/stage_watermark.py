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


class WatermarkMixin:
    def _build_stage_watermark(self):
        box, v = self._stage_box(13, "Watermark", enabled_check=False)
        self.stage_wm_box = box

        info = QLabel("Draws a semi-transparent info block onto the image "
                      "using the fields checked below (same data as the "
                      "info bar above, without icons), plus an optional "
                      "free-text Author credit line. Saves the block into "
                      "the working image — use Undo to remove it.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        self.wm_field_checkboxes = {}
        fields_row = QGridLayout()
        fields_row.setHorizontalSpacing(10)
        fields_row.setVerticalSpacing(6)
        # (field key, checkbox label, checked by default)
        field_defs = [
            ("object", "Object name", True),
            ("date", "Date", True),
            ("telescope", "Telescope", True),
            ("integration", "Integration time", False),
            ("fov", "FOV", False),
            ("size", "Image size", False),
            ("bortle", "Bortle estimate", False),
        ]
        for i, (key, label, default_on) in enumerate(field_defs):
            cb = QCheckBox(label)
            cb.setChecked(default_on)
            self.wm_field_checkboxes[key] = cb
            fields_row.addWidget(cb, i // 2, i % 2)
        v.addLayout(fields_row)

        integration_unit_row = QHBoxLayout()
        integration_unit_row.setSpacing(10)
        integration_unit_row.addWidget(QLabel("Integration time unit:"))
        self.wm_integration_unit_combo = QComboBox()
        self.wm_integration_unit_combo.addItems(["Minutes", "Hours", "Seconds"])
        self.wm_integration_unit_combo.setToolTip(
            "Unit used to display the Integration time field above.\n"
            "Minutes is the default (e.g. \"180 min\"); switch to Hours for\n"
            "very long sessions or Seconds for short ones. The sub "
            "count × exposure detail (e.g. \"360×30s\") is always shown "
            "alongside it when available.")
        integration_unit_row.addWidget(self.wm_integration_unit_combo, 1)
        v.addLayout(integration_unit_row)

        author_row = QHBoxLayout()
        author_row.setSpacing(10)
        self.wm_author_checkbox = QCheckBox("Author")
        self.wm_author_checkbox.setToolTip(
            "Adds a free-text credit line (typically your name or handle) "
            "to the watermark block — this isn't read from the image's "
            "metadata like the fields above, you type it yourself.")
        author_row.addWidget(self.wm_author_checkbox)
        self.wm_author_edit = QLineEdit()
        self.wm_author_edit.setPlaceholderText("Your name...")
        author_row.addWidget(self.wm_author_edit, 1)
        v.addLayout(author_row)

        opts_row = QHBoxLayout()
        opts_row.setSpacing(10)
        opts_row.addWidget(QLabel("Position:"))
        self.wm_position_combo = QComboBox()
        self.wm_position_combo.addItems(WATERMARK_POSITIONS)
        opts_row.addWidget(self.wm_position_combo, 1)
        opts_row.addWidget(QLabel("Opacity:"))
        self.wm_alpha_spin = QSpinBox()
        self.wm_alpha_spin.setRange(0, 100)
        self.wm_alpha_spin.setValue(55)
        self.wm_alpha_spin.setSuffix("%")
        self.wm_alpha_spin.setToolTip(
            "Opacity of the watermark's background block — 0% is fully "
            "see-through, 100% is a solid block.")
        opts_row.addWidget(self.wm_alpha_spin)
        v.addLayout(opts_row)

        self.wm_two_col_checkbox = QCheckBox("Two-column layout")
        self.wm_two_col_checkbox.setToolTip(
            "Lays the checked fields out in two side-by-side columns "
            "instead of one long vertical list — makes the block wider "
            "but noticeably shorter, useful when several fields are "
            "checked and you don't want the watermark to dominate the "
            "image's height.")
        v.addWidget(self.wm_two_col_checkbox)

        row, self.stage_wm_run = self._run_row(
            lambda: self._launch([self._exec_stage_watermark]), undo_stage=IDX_WM)
        v.addLayout(row)

        save_row = QHBoxLayout()
        self.wm_save_btn = QPushButton("💾  Save image...")
        self.wm_save_btn.setToolTip(
            "Export the last watermarked result as JPEG or PNG, wherever "
            "you choose.")
        self.wm_save_btn.clicked.connect(self.on_save_watermarked_image)
        save_row.addWidget(self.wm_save_btn)
        self.wm_remove_all_btn = QPushButton("🗑  Remove all")
        self.wm_remove_all_btn.setToolTip(
            "Restores the image to how it looked before the very first "
            "Watermark run in this session — undoes every watermark "
            "you've applied so far, not just the last one (the Undo "
            "button above only reverts the most recent run).")
        self.wm_remove_all_btn.clicked.connect(self._remove_all_watermarks)
        save_row.addWidget(self.wm_remove_all_btn)
        save_row.addStretch()
        v.addLayout(save_row)
        return box

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
                unit_text = unit.currentText() if unit else "Minutes"
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
        progress("Watermark: fetching image...", 0.1)
        before = self._get_current_image()
        # Remembered once per "clean" streak so "Remove all watermarks" can
        # undo every watermark applied so far, not just the last run — the
        # per-stage Undo button already covers the single-last-run case.
        if getattr(self, "_wm_baseline", None) is None:
            self._wm_baseline = before.copy()
        hwc = to_hwc_float(before)

        progress("Watermark: gathering info fields...", 0.3)
        available = self._gather_watermark_fields()
        label_map = {
            "object": "Object", "date": "Date", "integration": "Integration",
            "telescope": "Telescope", "fov": "FOV", "size": "Image Size",
            "bortle": "Bortle",
        }
        selected = [(label_map.get(key, key.title()), available[key])
                   for key, cb in self.wm_field_checkboxes.items()
                   if cb.isChecked() and key in available]
        author = self.wm_author_edit.text().strip()
        if self.wm_author_checkbox.isChecked() and author:
            selected.append(("Author", author))
        if not selected:
            raise RuntimeError(
                "Nothing to watermark: no metadata fields are both "
                "checked and available in this image (check at least one, "
                "or make sure the image has the relevant header info, e.g. "
                "OBJECT, DATE-OBS, TELESCOP), and the Author field is "
                "either unchecked or empty.")

        progress("Watermark: drawing...", 0.6)
        position = self.wm_position_combo.currentText()
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
            IDX_WM, before, after, "Watermark: done.",
            f"Watermark applied ({len(selected)} field(s), {position})",
            before_linear=False, after_linear=False, progress=progress)

    def on_save_watermarked_image(self):
        """Export the last watermarked canvas as JPEG or PNG, wherever the
        user chooses. Doesn't touch Siril or re-run the stage — just
        re-encodes the raster already produced by the last Watermark run."""
        canvas = getattr(self, "_last_watermarked_canvas", None)
        if canvas is None:
            QMessageBox.information(
                self, "No watermarked image",
                "Run the Watermark stage at least once first.")
            return
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        default_path = os.path.join(self.cwd, f"watermarked_{now}.jpg")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save watermarked image", default_path,
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
                raise RuntimeError(
                    f"Unsupported format '{ext or '(none)'}' — choose .jpg or .png.")
            self.status_label.setText(
                f"Watermarked image saved: {os.path.basename(path)}")
            self.siril.log(f"Watermarked image saved: {path}", LogColor.GREEN)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

    def _remove_all_watermarks(self):
        """Restore the image to how it looked before the very first
        Watermark run since the baseline was last captured — undoes every
        watermark applied so far in this streak, not just the last one
        (unlike the per-stage Undo button, which only reverts one run)."""
        baseline = getattr(self, "_wm_baseline", None)
        if baseline is None:
            QMessageBox.information(
                self, "No watermark to remove",
                "Run the Watermark stage at least once first.")
            return
        reply = QMessageBox.question(
            self, "Remove all watermarks",
            "Restore the image to how it looked before any watermark was "
            "applied? This undoes every Watermark run so far, not just "
            "the last one.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return

        def job(progress):
            progress("Removing all watermarks...", 0.3)
            self._set_current_image(
                baseline, "AstroPipeline: remove all watermarks")
            self._store_snapshot(IDX_WM, baseline, baseline,
                                 before_linear=False, after_linear=False)
            progress("All watermarks removed.", 1.0)
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
