"""Image-based Bortle-scale sky-brightness estimate (extracted
from S30Pro_Pipeline.py)."""

import numpy as np

__all__ = ["sqm_to_bortle", "ZP_REF_50MM", "BORTLE_NAMES"]

# =============================================================================
#  BORTLE SCALE — image-based estimate (Option C)
#
#  There is no calibrated photometric zero point available in this pipeline
#  (that would require full star-photometry against a catalog, which is what
#  Siril's SPCC does internally but doesn't expose as a reusable constant).
#  Instead we derive a defensible, clearly-labelled ESTIMATE:
#
#    1. Read the sky background level (robust sigma-clipped median) from 2-3
#       randomly chosen raw sub-frames straight out of the "lights" folder.
#    2. Convert ADU -> electrons/sec/pixel using the header's exposure time
#       and gain (defaulting to 1 e-/ADU if the header doesn't say).
#    3. Convert to a surface brightness in mag/arcsec^2 ("SQM-equivalent")
#       using the pixel scale (from FOCALLEN + XPIXSZ) and an assumed
#       instrumental zero point, scaled by aperture area relative to a
#       50 mm reference (APERTURE header field if present, else a f/5
#       guess from FOCALLEN, else 50 mm default).
#    4. Map the SQM-equivalent value to the standard 9-level Bortle table.
#
#  The absolute zero point (ZP_REF_50MM below) is a rough, uncalibrated
#  constant tuned so that typical background levels reported by smart
#  telescope users under known sky conditions land in a believable range.
#  Treat the resulting number as a ballpark comparison, not a certified SQM
#  reading — it is always shown with an "(est.)" tag in the UI.
# =============================================================================

BORTLE_NAMES = {
    1: "Excellent dark-sky site",
    2: "Typical truly dark site",
    3: "Rural sky",
    4: "Rural/suburban transition",
    5: "Suburban sky",
    6: "Bright suburban sky",
    7: "Suburban/urban transition",
    8: "City sky",
    9: "Inner-city sky",
}

# (SQM lower-bound mag/arcsec^2, Bortle class) sorted brightest->darkest is
# handled by descending SQM; a sky is class N if its SQM >= this bound.
BORTLE_SQM_BOUNDS = [
    (21.99, 1), (21.89, 2), (21.69, 3), (21.25, 4),
    (20.49, 5), (19.50, 6), (18.94, 7), (18.38, 8), (-99.0, 9),
]

ZP_REF_50MM = 23.5  # instrumental zero point at 50 mm aperture, gain=1 e-/ADU


def sqm_to_bortle(sqm):
    for bound, cls in BORTLE_SQM_BOUNDS:
        if sqm >= bound:
            return cls
    return 9

