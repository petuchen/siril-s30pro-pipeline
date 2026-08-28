"""Standalone Qt widgets used by the pipeline UI: the before/after
compare view, the interactive histogram editor, and the background
worker thread (extracted from S30Pro_Pipeline.py)."""

import numpy as np
import cv2
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import (QImage, QPixmap, QPainter, QColor, QPen,
                         QPainterPath, QPolygonF)

from .image_utils import display_autostretch
from .theme import ACCENT

__all__ = ["CompareView", "HistogramEditor", "Worker"]

# =============================================================================
#  BEFORE / AFTER COMPARE WIDGET
# =============================================================================

class CompareView(QWidget):
    """Split before/after viewer with a draggable divider.

    Also supports a 'selection mode' (used by the Crop stage's draw-a-box
    feature): while active, dragging draws a rubber-band rectangle instead
    of panning, and on release `selectionMade` is emitted with the box as
    fractions (x, y, w, h in 0..1) of the displayed image."""

    selectionMade = pyqtSignal(float, float, float, float)
    pointPicked = pyqtSignal(float, float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.before = None   # QImage
        self.after = None    # QImage
        self.split = 0.5
        self.mode = "split"  # split | before | after
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self._drag_divider = False
        self._panning = False
        self._pan_start = None
        self.select_mode = False
        self._sel_start = None   # QPointF (widget coords), live drag only
        self._sel_end = None
        self._pending_sel = None  # (fx, fy, fw, fh) fractions — persists in
                                   # the preview after mouse release, until
                                   # explicitly cleared (Run stage or Esc)
        self.point_pick_mode = False  # single-click "add an object here"
                                       # mode (Annotate's manual-pick tool)
        self._last_ref_size = None  # (iw, ih) of the last shown before/after
        self.setMinimumSize(420, 380)
        self.setMouseTracking(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_select_mode(self, on):
        self.select_mode = bool(on)
        self._sel_start = self._sel_end = None
        if on:
            # starting a fresh drag replaces any previously marked box
            self._pending_sel = None
        self.setCursor(Qt.CursorShape.CrossCursor if on
                       else Qt.CursorShape.OpenHandCursor)

    def set_point_pick_mode(self, on):
        """Toggle the single-click "add an object here" mode (used by
        Annotate's "🖱 Pick object on image..." button). Unlike
        select_mode's click-and-drag rubber band, a single click in this
        mode immediately emits `pointPicked(fx, fy)` — fractions (0..1)
        of the displayed image — from mousePressEvent, no drag needed."""
        self.point_pick_mode = bool(on)
        self.setCursor(Qt.CursorShape.CrossCursor if on
                       else Qt.CursorShape.OpenHandCursor)
        self.update()
        self.update()

    def clear_pending_selection(self):
        """Remove the persisted crop-box marker from the preview (called
        after the crop actually runs, or when it's canceled)."""
        self._pending_sel = None
        self.update()

    def set_images(self, before, after):
        """Swap in new before/after images, keeping the current zoom level's
        *effective* on-screen scale — so a stage that changes the image's
        pixel dimensions (like Crop) doesn't make the preview suddenly
        snap to a fresh 'fit whole panel' view."""
        new_ref = after or before
        if new_ref is not None:
            new_size = (new_ref.width(), new_ref.height())
            old_size = self._last_ref_size
            w, h = self.width(), self.height()
            if (old_size and old_size != new_size
                    and old_size[0] > 0 and old_size[1] > 0
                    and new_size[0] > 0 and new_size[1] > 0
                    and w > 0 and h > 0):
                old_fit = min(w / old_size[0], h / old_size[1])
                new_fit = min(w / new_size[0], h / new_size[1])
                if old_fit > 0 and new_fit > 0:
                    effective_scale = old_fit * self.zoom
                    self.zoom = float(np.clip(effective_scale / new_fit, 0.15, 25.0))
            self._last_ref_size = new_size
        self.before, self.after = before, after
        self.update()

    def set_mode(self, mode):
        self.mode = mode
        self.update()

    # ------------------------------------------------------------ zoom / pan

    def reset_view(self):
        self.zoom = 1.0
        self.pan = [0.0, 0.0]
        self.update()

    def zoom_by(self, factor, center=None):
        ref = self.after or self.before
        old = self.zoom
        new = float(np.clip(old * factor, 0.15, 25.0))
        if abs(new - old) < 1e-6:
            return
        if ref is not None and center is not None:
            rect = self._image_rect(ref)
            if rect.width() > 0:
                fx = (center.x() - rect.left()) / rect.width()
                fy = (center.y() - rect.top()) / rect.height()
                self.zoom = new
                nrect = self._image_rect(ref)
                self.pan[0] += center.x() - (nrect.left() + fx * nrect.width())
                self.pan[1] += center.y() - (nrect.top() + fy * nrect.height())
            else:
                self.zoom = new
        else:
            self.zoom = new
        self.update()

    def wheelEvent(self, e):
        if self.select_mode:
            # Zooming while marking a crop box shifts the image under the
            # cursor mid-drag, making it near-impossible to draw an accurate
            # box (trackpads especially tend to fire wheel events during a
            # click-drag gesture). Zoom/pan first, then draw the box.
            e.ignore()
            return
        factor = 1.25 if e.angleDelta().y() > 0 else 0.8
        self.zoom_by(factor, e.position())

    def _image_rect(self, img):
        if img is None:
            return QRectF()
        w, h = self.width(), self.height()
        iw, ih = img.width(), img.height()
        scale = min(w / iw, h / ih) * self.zoom
        dw, dh = iw * scale, ih * scale
        return QRectF((w - dw) / 2 + self.pan[0], (h - dh) / 2 + self.pan[1],
                      dw, dh)

    def resizeEvent(self, event):
        """While the user is drawing a manual crop box — or one is marked
        and waiting for "Run this stage" — the displayed image's scale is
        always recomputed from this widget's current pixel size (see
        `_image_rect`). If something elsewhere in the layout nudges this
        panel's geometry during that workflow (e.g. a sidebar hint label
        changing size), the image would silently rescale under the
        cursor even though the user never touched zoom. Lock the
        *effective* on-screen scale across that window, the same trick
        `set_images` already uses to stop the preview from "snapping" when
        the image's own pixel dimensions change (e.g. after a crop runs).
        Outside of that window, resizing still behaves as a normal
        fit-to-panel view."""
        super().resizeEvent(event)
        ref = self.after or self.before
        old = event.oldSize()
        if (ref is None or not (self.select_mode or self._pending_sel is not None)
                or not old.isValid() or old.width() <= 0 or old.height() <= 0):
            return
        iw, ih = ref.width(), ref.height()
        new = self.size()
        if iw <= 0 or ih <= 0 or new.width() <= 0 or new.height() <= 0:
            return
        old_fit = min(old.width() / iw, old.height() / ih)
        new_fit = min(new.width() / iw, new.height() / ih)
        if old_fit > 0 and new_fit > 0:
            effective_scale = old_fit * self.zoom
            self.zoom = float(np.clip(effective_scale / new_fit, 0.15, 25.0))

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.fillRect(self.rect(), QColor("#101216"))
        ref = self.after or self.before
        if ref is None:
            p.setPen(QColor("#4a5160"))
            f = p.font(); f.setPointSize(11); p.setFont(f)
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "No preview yet\nRun a pipeline stage to see before / after")
            return
        rect = self._image_rect(ref)

        def draw(img, clip_left=None, clip_right=None):
            if img is None:
                return
            src = QRectF(0, 0, img.width(), img.height())
            if clip_left is not None or clip_right is not None:
                p.save()
                cl = rect.left() if clip_left is None else clip_left
                cr = rect.right() if clip_right is None else clip_right
                p.setClipRect(QRectF(cl, rect.top(), cr - cl, rect.height()))
                p.drawImage(rect, img, src)
                p.restore()
            else:
                p.drawImage(rect, img, src)

        if self.mode == "before":
            draw(self.before if self.before else self.after)
        elif self.mode == "after":
            draw(self.after if self.after else self.before)
        else:
            sx = rect.left() + rect.width() * self.split
            draw(self.before, clip_right=sx)
            draw(self.after, clip_left=sx)
            # divider
            pen = QPen(QColor("#ffffff"), 2)
            p.setPen(pen)
            p.drawLine(int(sx), int(rect.top()), int(sx), int(rect.bottom()))
            p.setBrush(QColor(ACCENT))
            p.setPen(Qt.PenStyle.NoPen)
            cy = rect.center().y()
            p.drawEllipse(int(sx) - 9, int(cy) - 9, 18, 18)
            p.setPen(QColor("#0d1117"))
            f = p.font(); f.setBold(True); p.setFont(f)
            p.drawText(QRectF(sx - 9, cy - 9, 18, 18),
                       Qt.AlignmentFlag.AlignCenter, "⇔")
        # labels
        p.setPen(QColor(255, 255, 255, 225))
        f = p.font(); f.setPointSize(11); f.setBold(True); p.setFont(f)
        if self.mode in ("split", "before") and self.before is not None:
            p.fillRect(int(rect.left()) + 10, int(rect.top()) + 10, 78, 28,
                       QColor(0, 0, 0, 160))
            p.drawText(int(rect.left()) + 20, int(rect.top()) + 29, "BEFORE")
        if self.mode in ("split", "after") and self.after is not None:
            p.fillRect(int(rect.right()) - 78, int(rect.top()) + 10, 68, 28,
                       QColor(0, 0, 0, 160))
            p.drawText(int(rect.right()) - 68, int(rect.top()) + 29, "AFTER")

        # crop-selection rubber band (live drag) or persisted crop-box marker
        if self.select_mode:
            p.setPen(QPen(QColor(ACCENT), 1, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            hint_f = p.font(); hint_f.setPointSize(10); hint_f.setBold(True)
            p.setFont(hint_f)
            p.setPen(QColor(255, 255, 255, 235))
            p.fillRect(6, self.height() - 30, 430, 22, QColor(0, 0, 0, 160))
            p.drawText(12, self.height() - 14,
                       "CROP MODE — drag a box on the image (scroll-zoom locked)")
            if self._sel_start is not None and self._sel_end is not None:
                sel = QRectF(self._sel_start, self._sel_end).normalized()
                p.fillRect(sel, QColor(46, 74, 143, 60))
                p.setPen(QPen(QColor(ACCENT), 2, Qt.PenStyle.DashLine))
                p.drawRect(sel)
        elif self._pending_sel is not None:
            fx, fy, fw, fh = self._pending_sel
            sel = QRectF(rect.left() + fx * rect.width(),
                        rect.top() + fy * rect.height(),
                        fw * rect.width(), fh * rect.height())
            p.fillRect(sel, QColor(46, 74, 143, 60))
            p.setPen(QPen(QColor(ACCENT), 2, Qt.PenStyle.DashLine))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRect(sel)
            f = p.font(); f.setPointSize(10); f.setBold(True); p.setFont(f)
            p.setPen(QColor(255, 255, 255, 235))
            p.fillRect(6, self.height() - 30, 430, 22, QColor(0, 0, 0, 160))
            p.drawText(12, self.height() - 14,
                       "Crop box marked — Run this stage to crop, or Esc to cancel")
        elif self.point_pick_mode:
            f = p.font(); f.setPointSize(10); f.setBold(True); p.setFont(f)
            p.setPen(QColor(255, 255, 255, 235))
            p.fillRect(6, self.height() - 30, 430, 22, QColor(0, 0, 0, 160))
            p.drawText(12, self.height() - 14,
                       "PICK MODE — click a point to add an object, or Esc to stop")

    def _divider_x(self):
        ref = self.after or self.before
        if ref is None:
            return None
        rect = self._image_rect(ref)
        return rect.left() + rect.width() * self.split

    def mousePressEvent(self, e):
        pos = e.position()
        if self.point_pick_mode:
            ref = self.after or self.before
            if ref is not None:
                rect = self._image_rect(ref)
                if (rect.width() > 0 and rect.height() > 0
                        and rect.contains(pos)):
                    fx = (pos.x() - rect.left()) / rect.width()
                    fy = (pos.y() - rect.top()) / rect.height()
                    self.pointPicked.emit(fx, fy)
            return
        if self.select_mode:
            self._sel_start = pos
            self._sel_end = pos
            self.update()
            return
        dx = self._divider_x()
        if (self.mode == "split" and dx is not None
                and abs(pos.x() - dx) <= 14):
            self._drag_divider = True
            self._update_split(pos.x())
        else:
            self._panning = True
            self._pan_start = (pos.x(), pos.y(), self.pan[0], self.pan[1])
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, e):
        pos = e.position()
        if self.select_mode:
            if self._sel_start is not None:
                self._sel_end = pos
                self.update()
            return
        if self._drag_divider:
            self._update_split(pos.x())
        elif self._panning and self._pan_start is not None:
            sx, sy, px, py = self._pan_start
            self.pan[0] = px + (pos.x() - sx)
            self.pan[1] = py + (pos.y() - sy)
            self.update()
        else:
            # hover cursor hint: resize arrows near divider, open hand elsewhere
            dx = self._divider_x()
            if self.mode == "split" and dx is not None and \
                    abs(pos.x() - dx) <= 14:
                self.setCursor(Qt.CursorShape.SplitHCursor)
            else:
                self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseReleaseEvent(self, e):
        if self.select_mode and self._sel_start is not None:
            sel = QRectF(self._sel_start, self._sel_end).normalized()
            self._sel_start = self._sel_end = None
            ref = self.after or self.before
            if ref is not None and sel.width() > 6 and sel.height() > 6:
                rect = self._image_rect(ref)
                if rect.width() > 0 and rect.height() > 0:
                    clipped = sel.intersected(rect)
                    if clipped.width() > 4 and clipped.height() > 4:
                        fx = (clipped.left() - rect.left()) / rect.width()
                        fy = (clipped.top() - rect.top()) / rect.height()
                        fw = clipped.width() / rect.width()
                        fh = clipped.height() / rect.height()
                        self._pending_sel = (fx, fy, fw, fh)
                        self.selectionMade.emit(fx, fy, fw, fh)
            self.update()
            return
        self._drag_divider = False
        self._panning = False
        self._pan_start = None
        self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, e):
        if self.select_mode:
            return
        self.reset_view()

    def _update_split(self, x):
        ref = self.after or self.before
        if ref is None:
            return
        rect = self._image_rect(ref)
        if rect.width() > 0:
            self.split = float(np.clip((x - rect.left()) / rect.width(), 0.0, 1.0))
            self.update()

# =============================================================================
#  INTERACTIVE HISTOGRAM EDITOR  (stage 6)
# =============================================================================

CH_COLORS = {"R": QColor(255, 90, 90), "G": QColor(105, 219, 124),
             "B": QColor(116, 168, 255), "RGB": QColor(235, 235, 235)}


class HistogramEditor(QWidget):
    """RGB histogram with three draggable points (shadows / midtones /
    highlights) for the active channel. Emits `changed` while dragging."""

    changed = pyqtSignal()

    MARGIN_B = 18  # bottom strip for the marker handles

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist = None          # list of up to 3 normalized arrays (256 bins)
        self.channel = "RGB"
        self.params = {ch: {"shadows": 0.0, "midtones": 0.5, "highlights": 1.0}
                       for ch in ("RGB", "R", "G", "B")}
        self._drag = None         # which marker is being dragged
        self.setMinimumHeight(150)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.CrossCursor)

    # ------------------------------------------------------------------- data

    def set_image_data(self, hwc):
        """Compute per-channel histograms from an (h,w,3) float 0..1 proxy."""
        if hwc is None:
            self.hist = None
            self.update()
            return
        hists = []
        for c in range(3):
            h, _ = np.histogram(hwc[:, :, c], bins=256, range=(0.0, 1.0))
            hists.append(h.astype(np.float64))
        peak = max(np.max(h) for h in hists) or 1.0
        # sqrt scaling so faint tails stay visible
        self.hist = [np.sqrt(h / peak) for h in hists]
        self.update()

    def set_channel(self, ch):
        self.channel = ch
        self.update()

    def set_params(self, ch, shadows, midtones, highlights):
        self.params[ch] = {"shadows": shadows, "midtones": midtones,
                           "highlights": highlights}
        if ch == self.channel:
            self.update()

    # ---------------------------------------------------------------- helpers

    def _plot_rect(self):
        return QRectF(6, 6, self.width() - 12, self.height() - 12 - self.MARGIN_B)

    def _marker_positions(self):
        """x pixel positions of (shadows, midtones, highlights) markers."""
        r = self._plot_rect()
        p = self.params[self.channel]
        sh, mid, hi = p["shadows"], p["midtones"], p["highlights"]
        x_sh = r.left() + sh * r.width()
        x_hi = r.left() + hi * r.width()
        x_mid = r.left() + (sh + mid * (hi - sh)) * r.width()
        return x_sh, x_mid, x_hi

    # ------------------------------------------------------------------ paint

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor("#101216"))
        r = self._plot_rect()

        # grid
        p.setPen(QPen(QColor(255, 255, 255, 18), 1))
        for i in range(1, 4):
            x = r.left() + r.width() * i / 4
            p.drawLine(int(x), int(r.top()), int(x), int(r.bottom()))

        if self.hist is not None:
            p.setCompositionMode(QPainter.CompositionMode.CompositionMode_Plus)
            for arr, col in zip(self.hist, (CH_COLORS["R"], CH_COLORS["G"],
                                            CH_COLORS["B"])):
                c = QColor(col)
                c.setAlpha(120)
                path = QPainterPath()
                path.moveTo(r.left(), r.bottom())
                step = r.width() / 255.0
                for i, v in enumerate(arr):
                    path.lineTo(r.left() + i * step, r.bottom() - v * r.height())
                path.lineTo(r.right(), r.bottom())
                path.closeSubpath()
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(c)
                p.drawPath(path)
            p.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver)
        else:
            p.setPen(QColor("#4a5160"))
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter,
                       "Click 'Load current image' to begin")

        # markers of active channel
        col = CH_COLORS[self.channel]
        x_sh, x_mid, x_hi = self._marker_positions()
        for x, style in ((x_sh, Qt.PenStyle.SolidLine),
                         (x_mid, Qt.PenStyle.DashLine),
                         (x_hi, Qt.PenStyle.SolidLine)):
            p.setPen(QPen(col, 1.4, style))
            p.drawLine(int(x), int(r.top()), int(x), int(r.bottom()))

        # bottom handles (triangles)
        p.setPen(Qt.PenStyle.NoPen)
        for x, fill in ((x_sh, QColor("#000000")), (x_mid, QColor("#808080")),
                        (x_hi, QColor("#ffffff"))):
            tri = QPolygonF([QPointF(x, r.bottom() + 3),
                             QPointF(x - 7, r.bottom() + self.MARGIN_B),
                             QPointF(x + 7, r.bottom() + self.MARGIN_B)])
            p.setBrush(col)
            p.drawPolygon(tri)
            inner = QPolygonF([QPointF(x, r.bottom() + 6),
                               QPointF(x - 4, r.bottom() + self.MARGIN_B - 2),
                               QPointF(x + 4, r.bottom() + self.MARGIN_B - 2)])
            p.setBrush(fill)
            p.drawPolygon(inner)

        # readout
        prm = self.params[self.channel]
        p.setPen(QColor(255, 255, 255, 170))
        f = p.font()
        f.setPointSize(8)
        p.setFont(f)
        p.drawText(int(r.left()) + 4, int(r.top()) + 12,
                   f"{self.channel}   S {prm['shadows']:.3f}   "
                   f"M {prm['midtones']:.3f}   H {prm['highlights']:.3f}")

    # ------------------------------------------------------------------ mouse

    def _pick_marker(self, x):
        x_sh, x_mid, x_hi = self._marker_positions()
        cands = [("shadows", abs(x - x_sh)), ("midtones", abs(x - x_mid)),
                 ("highlights", abs(x - x_hi))]
        cands.sort(key=lambda t: t[1])
        return cands[0][0] if cands[0][1] < 16 else None

    def mousePressEvent(self, e):
        self._drag = self._pick_marker(e.position().x())
        if self._drag:
            self._move_marker(e.position().x())

    def mouseMoveEvent(self, e):
        if self._drag:
            self._move_marker(e.position().x())

    def mouseReleaseEvent(self, e):
        self._drag = None

    def mouseDoubleClickEvent(self, e):
        self.params[self.channel] = {"shadows": 0.0, "midtones": 0.5,
                                     "highlights": 1.0}
        self.update()
        self.changed.emit()

    def _move_marker(self, x):
        r = self._plot_rect()
        t = float(np.clip((x - r.left()) / r.width(), 0.0, 1.0))
        prm = self.params[self.channel]
        if self._drag == "shadows":
            prm["shadows"] = min(t, prm["highlights"] - 0.02)
        elif self._drag == "highlights":
            prm["highlights"] = max(t, prm["shadows"] + 0.02)
        elif self._drag == "midtones":
            span = prm["highlights"] - prm["shadows"]
            prm["midtones"] = float(np.clip(
                (t - prm["shadows"]) / max(span, 1e-6), 0.05, 0.95))
        self.update()
        self.changed.emit()


# =============================================================================
#  WORKER THREAD
# =============================================================================

class Worker(QThread):
    progressed = pyqtSignal(str, float)
    failed = pyqtSignal(str)
    succeeded = pyqtSignal()

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.fn(lambda msg, p=0.0: self.progressed.emit(msg, p))
            self.succeeded.emit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.failed.emit(str(e))


class PreviewFetchWorker(QThread):
    """Runs a zero-argument callable off the GUI thread and reports its
    result back via signals — specifically for
    UnifiedPipelineWindow._refresh_preview()'s "no snapshot yet for this
    stage, so show whatever Siril currently has loaded instead" path,
    which fetches Siril's full-resolution current image and runs it
    through the display stretch/QImage conversion. That's real work
    (easily a second or more on a typical smart-telescope stack), and
    _refresh_preview() fires on every stage-navigation click for any
    stage that hasn't run yet this session — done synchronously on the
    GUI thread, each of those clicks would briefly freeze the whole
    window. Not a replacement for `Worker` above, which drives a full
    stage's execution with progress reporting; this is for the much
    lighter, much more frequent "just show me the current image" case,
    with no progress reporting of its own.

    `fn` is expected to return a QImage (or None) on success, or raise —
    `RuntimeError` specifically means "nothing loaded in Siril yet",
    which is a normal, expected outcome (see _get_current_image), not a
    real failure, so it gets its own `empty` signal instead of `failed`."""
    succeeded = pyqtSignal(object)  # QImage
    empty = pyqtSignal()
    failed = pyqtSignal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            result = self.fn()
        except RuntimeError:
            self.empty.emit()
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.failed.emit(str(e))
        else:
            self.succeeded.emit(result)

