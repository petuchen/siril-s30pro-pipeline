"""Small image-format conversion helpers shared across stages
(extracted from S30Pro_Pipeline.py)."""

import numpy as np
import cv2
from PyQt6.QtGui import QImage

from .veralux_stretch import VeraLuxCore

__all__ = ["to_hwc_float", "display_autostretch", "make_qimage"]

# =============================================================================
#  DISPLAY HELPERS
# =============================================================================

PREVIEW_MAX = 1600  # long-side limit for preview rendering


def to_hwc_float(img):
    """Return (h,w,3) float32 0..1 from planar/mono/uint16 input."""
    img = VeraLuxCore.normalize_input(np.asarray(img))
    if img.ndim == 3 and img.shape[0] <= 4:  # planar (c,h,w)
        img = np.transpose(img, (1, 2, 0))
    if img.ndim == 2:
        img = np.stack([img] * 3, axis=-1)
    if img.shape[-1] == 1:
        img = np.repeat(img, 3, axis=-1)
    return np.clip(img.astype(np.float32), 0.0, 1.0)


def display_autostretch(hwc, linked=True):
    """Simple display-only autostretch (Siril-like MTF), input (h,w,3) 0..1."""
    out = hwc.copy()
    sample = out[::4, ::4, :]
    med = np.median(sample)
    mad = np.median(np.abs(sample - med)) + 1e-9
    if med > 0.15:  # already stretched enough for display
        return out
    shadows = max(0.0, med - 2.8 * mad)
    rng = 1.0 - shadows
    out = np.clip((out - shadows) / (rng + 1e-9), 0.0, 1.0)
    med2 = np.median(out[::4, ::4, :])
    target = 0.22
    if med2 > 1e-6:
        m = (med2 * (target - 1.0)) / (med2 * (2.0 * target - 1.0) - target)
        out = VeraLuxCore.apply_mtf(out, m)
    return np.clip(out, 0.0, 1.0)


def make_qimage(hwc, fits_orientation=True):
    """(h,w,3) float 0..1 -> QImage (downscaled for preview).

    Siril (and FITS generally) stores row 0 as the BOTTOM of the image;
    every stage's raw before/after array is in that orientation as it
    comes out of Siril. Siril's own on-screen display flips it before
    showing it, so `fits_orientation=True` (the default) does the same
    flip here — this is what makes this app's preview panel match what
    Siril itself shows, instead of appearing upside-down relative to it.

    Pass `fits_orientation=False` for a canvas a caller has *already*
    flipped into display orientation itself (e.g. the Watermark stage,
    which draws text in display orientation before rendering so the
    glyphs aren't baked in upside-down) — flipping those again here would
    undo that and re-invert the text."""
    if fits_orientation:
        hwc = np.flipud(hwc)
    h, w, _ = hwc.shape
    scale = min(1.0, PREVIEW_MAX / max(h, w))
    if scale < 1.0:
        hwc = cv2.resize(hwc, (int(w * scale), int(h * scale)),
                         interpolation=cv2.INTER_AREA)
    arr = np.ascontiguousarray((np.clip(hwc, 0, 1) * 255).astype(np.uint8))
    h2, w2, _ = arr.shape
    qimg = QImage(arr.data, w2, h2, w2 * 3, QImage.Format.Format_RGB888)
    return qimg.copy()  # deep copy: detach from numpy buffer

