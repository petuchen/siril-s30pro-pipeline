"""Crop stage mixin for UnifiedPipelineWindow."""

import numpy as np

from PyQt6.QtGui import QImage, QPainter
from PyQt6.QtWidgets import (
    QCheckBox, QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel, QPushButton,
)

import sirilpy as s
from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_CROP


class CropMixin:
    def _build_stage_crop(self):
        box, v = self._stage_box(2, "Crop")
        self.stage_crop_box = box
        self._pending_crop_box = None  # (fx, fy, fw, fh) fractions, set by draw-box

        self.crop_auto_checkbox = QCheckBox("Auto crop (5% off each side)")
        self.crop_auto_checkbox.setChecked(True)
        v.addWidget(self.crop_auto_checkbox)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)
        g.setColumnStretch(3, 1)
        self.crop_margins = {}
        for i, (key, label) in enumerate((("left", "Left %"), ("right", "Right %"),
                                          ("top", "Top %"), ("bottom", "Bottom %"))):
            spin = QDoubleSpinBox()
            spin.setRange(0.0, 40.0)
            spin.setSingleStep(0.5)
            spin.setValue(5.0)
            self.crop_margins[key] = spin
            g.addWidget(QLabel(label + ":"), i // 2, (i % 2) * 2)
            g.addWidget(spin, i // 2, (i % 2) * 2 + 1)
        v.addLayout(g)

        def toggle_manual(checked):
            for spin in self.crop_margins.values():
                spin.setEnabled(not checked)
            if checked:
                # switching back to auto crop discards any drawn box
                self._clear_pending_crop_box()
        self.crop_auto_checkbox.toggled.connect(toggle_manual)
        toggle_manual(True)

        # rotate — applied first, before any cropping below, so a tilted
        # frame gets straightened and the (now ragged/black) corners it
        # leaves behind can be trimmed off by the margins or drawn box
        rot_row, self.crop_rotate_spin = self._slider_spin_row(
            "Rotate (°):", -180.0, 180.0, 0.1, 0.0, 1,
            "Rotate the image before cropping. Positive is counter-"
            "clockwise. Siril crops to the original frame size after "
            "rotating (no black borders), so set the margins/drawn box "
            "below generously enough to trim whatever the rotation "
            "leaves ragged at the edges. The preview updates live as you "
            "drag this — it's a quick on-screen approximation (Qt "
            "rotating the already-rendered preview image), not the same "
            "interpolation Siril's own `rotate` command uses, so treat it "
            "as a guide for framing/angle, not a pixel-exact result.",
            on_change=lambda _val: self._update_crop_rotate_preview())
        v.addLayout(rot_row)

        # manual crop by drawing a box in the preview
        draw_row = QHBoxLayout()
        draw_row.setSpacing(10)
        self.crop_draw_btn = QPushButton("⬚  Draw crop box in preview")
        self.crop_draw_btn.setCheckable(True)
        self.crop_draw_btn.setToolTip(
            "Click, then drag a rectangle on the preview panel. This only\n"
            "marks the box and switches off Auto crop — press \"Run this\n"
            "stage\" below to actually crop.")
        self.crop_draw_btn.toggled.connect(self._toggle_crop_draw)
        draw_row.addWidget(self.crop_draw_btn)
        draw_row.addStretch()
        v.addLayout(draw_row)
        self.crop_draw_hint = QLabel("")
        self.crop_draw_hint.setObjectName("SubHeader")
        self.crop_draw_hint.setWordWrap(True)
        v.addWidget(self.crop_draw_hint)

        row, self.stage_crop_run = self._run_row(
            lambda: self._launch([self._exec_stage_crop]), undo_stage=IDX_CROP)
        v.addLayout(row)
        return box

    def _update_crop_rotate_preview(self):
        """Live preview for the Rotate slider/spinbox: rotate the cached
        un-rotated base image (see _on_preview_fetch_succeeded, which
        keeps self._crop_rotate_base_img fresh whenever Crop's own
        "before" preview gets fetched) with QPainter and show it on both
        sides of the split view, in place of the plain base.

        This is a quick on-screen approximation, not a re-run of Siril's
        `rotate` command — doing that live, on every slider tick, would
        mean a full Siril IPC round-trip per tick, which is exactly the
        kind of thing PreviewFetchWorker was built to avoid doing
        synchronously (see S30Pro_Pipeline.py's _refresh_preview). Qt's
        own rotation is cheap enough to just do directly here.

        Only meaningful while the Crop stage hasn't run yet (once it has,
        the preview shows Crop's real before/after snapshot instead —
        see _refresh_preview's snapshot-exists fast path, which this
        never overrides). If nothing's cached yet (e.g. the background
        fetch of the current Siril image hasn't completed), this is a
        harmless no-op; it'll catch up once that fetch lands.
        """
        base = getattr(self, "_crop_rotate_base_img", None)
        compare = getattr(self, "compare", None)
        if base is None or compare is None:
            return
        if self.preview_stage_combo.currentIndex() != IDX_CROP:
            return
        angle = self.crop_rotate_spin.value()
        if abs(angle) < 1e-6:
            compare.set_images(base, base)
            return
        w, h = base.width(), base.height()
        canvas = QImage(base.size(), base.format())
        canvas.fill(0)  # black where the rotation leaves gaps at the corners
        p = QPainter(canvas)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.translate(w / 2.0, h / 2.0)
        p.rotate(-angle)  # Qt rotates clockwise for +angle; tooltip promises
                          # positive = counter-clockwise, so negate
        p.translate(-w / 2.0, -h / 2.0)
        p.drawImage(0, 0, base)
        p.end()
        compare.set_images(canvas, canvas)

    def _toggle_crop_draw(self, checked):
        compare = getattr(self, "compare", None)
        if compare is None:
            return
        if checked:
            # manual box mode overrides margin-based auto crop
            self.crop_auto_checkbox.setChecked(False)
        compare.set_select_mode(checked)
        if checked:
            self.crop_draw_hint.setText(
                "Drag a box on the preview to mark the crop. Click the "
                "button again to cancel.")
        elif not self._pending_crop_box:
            self.crop_draw_hint.setText("")

    def _on_crop_selection(self, fx, fy, fw, fh):
        """Preview rubber-band finished → just remember the box; the actual
        crop happens when the stage is run."""
        self.crop_draw_btn.setChecked(False)  # also exits select mode
        self._pending_crop_box = (fx, fy, fw, fh)
        self.crop_draw_hint.setText(
            f"Box marked ({fw*100:.0f}% × {fh*100:.0f}% of the image) — "
            "press \"Run this stage\" below to crop.")

    def _clear_pending_crop_box(self, *_args):
        self._pending_crop_box = None
        draw_btn = getattr(self, "crop_draw_btn", None)
        hint = getattr(self, "crop_draw_hint", None)
        if hint is not None and (draw_btn is None or not draw_btn.isChecked()):
            hint.setText("")
        compare = getattr(self, "compare", None)
        if compare is not None:
            compare.clear_pending_selection()

    def _cancel_pending_crop(self):
        """Esc pressed anywhere in the window — cancel an in-progress drag
        or an already-marked crop box. Returns True if there was anything
        to cancel (so the caller can decide whether to consume the key)."""
        drawing = self.crop_draw_btn.isChecked()
        had_pending = bool(getattr(self, "_pending_crop_box", None))
        if not drawing and not had_pending:
            return False
        if drawing:
            self.crop_draw_btn.setChecked(False)  # also exits select mode
        self._clear_pending_crop_box()
        self.status_label.setText("Crop box canceled.")
        return True

    def _do_siril_crop(self, x, y, cw, ch):
        """Crop the loaded image, robust to Siril GUI state.

        Siril's `crop` command refuses to run while a GUI preview is open
        (e.g. a dialog preview, or leftover state from an earlier crop),
        which broke sequential crops. Strategy:
          1. clear any leftover selection (harmless if none),
          2. try the native `crop` (best: Siril updates the WCS/plate-solve),
          3. on failure, fall back to a pixel-level crop through
             set_image_pixeldata — always works, but invalidates the
             plate solve, so we warn that a re-solve may be needed for
             any later plate-solve-dependent step.
        """
        try:
            self.siril.cmd("boxselect", "-clear")
        except Exception:
            pass
        try:
            self.siril.cmd("crop", str(x), str(y), str(cw), str(ch))
            try:  # don't leave a selection behind that blocks the NEXT crop
                self.siril.cmd("boxselect", "-clear")
            except Exception:
                pass
            return
        except (s.DataError, s.CommandError, s.SirilError) as e:
            self.siril.log(
                f"Siril 'crop' refused ({e}) — falling back to a direct "
                "pixel crop. If a preview dialog is open in Siril, closing "
                "it lets the native crop work again.", LogColor.SALMON)
        img = self._get_current_image()
        if img.ndim == 3:
            cropped = img[:, y:y + ch, x:x + cw]
        else:
            cropped = img[y:y + ch, x:x + cw]
        cropped = np.ascontiguousarray(cropped)
        with self.siril.image_lock():
            self.siril.undo_save_state("AstroPipeline: crop (fallback)")
            self.siril.set_image_pixeldata(cropped)
        self.siril.log(
            "Cropped via pixel fallback — the plate-solve solution is now "
            "stale; re-run 'platesolve' if a later step needs it.",
            LogColor.SALMON)

    def _exec_stage_crop(self, progress):
        progress("Crop: fetching image...", 0.05)
        before = self._get_current_image()
        _, h, w = before.shape if before.ndim == 3 else (1,) + before.shape

        rotate_deg = self.crop_rotate_spin.value()
        if abs(rotate_deg) > 1e-6:
            progress(f"Crop: rotating {rotate_deg:.1f}°...", 0.15)
            try:
                self.siril.cmd("rotate", f"{rotate_deg:.2f}")
            except (s.DataError, s.CommandError, s.SirilError) as e:
                raise RuntimeError(f"Rotate failed: {e}") from e
            # Siril's default `rotate` crops back to the original frame
            # size (no -nocrop passed), so w/h from `before` above still
            # describe the rotated image's dimensions correctly.

        pending = getattr(self, "_pending_crop_box", None)
        if pending is not None:
            fx, fy, fw, fh = pending
            x = int(round(fx * w))
            y = int(round(fy * h))
            cw = int(round(fw * w))
            ch = int(round(fh * h))
            x = max(0, min(x, w - 2))
            y = max(0, min(y, h - 2))
            cw = max(16, min(cw, w - x))
            ch = max(16, min(ch, h - y))
            if cw < 32 or ch < 32:
                raise RuntimeError("Drawn crop box is too small (min 32 px).")
            progress(f"Crop: {w}x{h} → {cw}x{ch} (drawn box)...", 0.3)
        else:
            if self.crop_auto_checkbox.isChecked():
                ml = mr = mt = mb = 5.0
            else:
                ml = self.crop_margins["left"].value()
                mr = self.crop_margins["right"].value()
                mt = self.crop_margins["top"].value()
                mb = self.crop_margins["bottom"].value()
            x = int(w * ml / 100.0)
            y = int(h * mt / 100.0)
            cw = w - x - int(w * mr / 100.0)
            ch = h - y - int(h * mb / 100.0)
            if cw < 32 or ch < 32:
                raise RuntimeError("Crop margins too large — nothing would remain.")
            if not (x > 0 or y > 0 or cw < w or ch < h):
                if abs(rotate_deg) <= 1e-6:
                    progress("Crop: nothing to do (0% margins, no rotation).", 1.0)
                    return
                # 0% margins but a rotation was applied above — still a
                # real change to record, just skip the no-op crop itself.
                after = self._get_current_image()
                self._finish_stage(
                    IDX_CROP, before, after, "Crop: done.",
                    f"Rotated {rotate_deg:.1f}° (no crop, 0% margins)",
                    progress=progress)
                return
            progress(f"Crop: {w}x{h} → {cw}x{ch}...", 0.3)

        self._do_siril_crop(x, y, cw, ch)
        after = self._get_current_image()
        self._pending_crop_box = None  # cleared here (worker thread); UI
                                        # label is refreshed in _on_snapshot_ready
        msg = f"Cropped: {w}x{h} → {cw}x{ch}"
        if abs(rotate_deg) > 1e-6:
            msg = f"Rotated {rotate_deg:.1f}° then " + msg[0].lower() + msg[1:]
        self._finish_stage(IDX_CROP, before, after,
                           "Crop: done.", msg,
                           progress=progress)
