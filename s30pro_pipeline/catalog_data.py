"""Deep-sky-object catalogue constants and small geometry/network
helpers used by the Annotate stage's catalogue cone-searches
(extracted from S30Pro_Pipeline.py)."""

import re
import csv
import math
import urllib.request
import urllib.parse

__all__ = [
    "BRIGHT_STARS", "OPENNGC_URL", "VIZIER_URL",
    "ANNOTATE_MAX_PER_CATALOG", "CATALOG_COLORS", "CATALOG_LABELS",
    "_ang_sep", "_sexa_to_deg", "_http_get", "_parse_vizier_tsv",
    "_vizier_cone", "_clean_ngc_ic_name",
]

# Named bright stars (proper name, RA, Dec, Vmag) — fallback list used only
# if Siril's own local star `conesearch` is unavailable (Siril < 1.3).
BRIGHT_STARS = [
    ("Sirius", 101.287, -16.716, -1.46), ("Canopus", 95.988, -52.696, -0.74),
    ("Arcturus", 213.915, 19.182, -0.05), ("Vega", 279.235, 38.784, 0.03),
    ("Capella", 79.172, 45.998, 0.08), ("Rigel", 78.634, -8.202, 0.13),
    ("Procyon", 114.826, 5.225, 0.34), ("Betelgeuse", 88.793, 7.407, 0.50),
    ("Achernar", 24.429, -57.237, 0.46), ("Hadar", 210.956, -60.373, 0.61),
    ("Altair", 297.696, 8.868, 0.77), ("Acrux", 186.650, -63.099, 0.76),
    ("Aldebaran", 68.980, 16.509, 0.85), ("Antares", 247.352, -26.432, 1.09),
    ("Spica", 201.298, -11.161, 0.97), ("Pollux", 116.329, 28.026, 1.14),
    ("Fomalhaut", 344.413, -29.622, 1.16), ("Deneb", 310.358, 45.280, 1.25),
    ("Mimosa", 191.930, -59.689, 1.25), ("Regulus", 152.093, 11.967, 1.35),
    ("Adhara", 104.656, -28.972, 1.50), ("Castor", 113.650, 31.888, 1.58),
    ("Shaula", 263.402, -37.104, 1.62), ("Gacrux", 187.791, -57.113, 1.63),
    ("Bellatrix", 81.283, 6.350, 1.64), ("Elnath", 81.573, 28.608, 1.65),
    ("Alnilam", 84.053, -1.202, 1.69), ("Alnitak", 85.190, -1.943, 1.77),
    ("Alioth", 193.507, 55.960, 1.77), ("Dubhe", 165.932, 61.751, 1.79),
    ("Mirfak", 51.081, 49.861, 1.80), ("Wezen", 107.098, -26.393, 1.84),
    ("Kaus Australis", 276.043, -34.385, 1.85), ("Alkaid", 206.885, 49.313, 1.86),
    ("Menkalinan", 89.882, 44.947, 1.90), ("Alhena", 99.428, 16.399, 1.93),
    ("Mirzam", 95.675, -17.956, 1.98), ("Alphard", 141.897, -8.659, 1.98),
    ("Polaris", 37.955, 89.264, 1.98), ("Hamal", 31.793, 23.462, 2.00),
    ("Diphda", 10.897, -17.987, 2.04), ("Mizar", 200.981, 54.925, 2.04),
    ("Nunki", 283.816, -26.297, 2.06), ("Mirach", 17.433, 35.620, 2.05),
    ("Alpheratz", 2.097, 29.090, 2.06), ("Rasalhague", 263.734, 12.560, 2.07),
    ("Kochab", 222.676, 74.156, 2.08), ("Saiph", 86.939, -9.670, 2.09),
    ("Denebola", 177.265, 14.572, 2.13), ("Algol", 47.042, 40.956, 2.12),
    ("Eltanin", 269.152, 51.489, 2.23), ("Schedar", 10.127, 56.537, 2.24),
    ("Caph", 2.295, 59.150, 2.27), ("Enif", 326.046, 9.875, 2.39),
    ("Alderamin", 319.645, 62.585, 2.46), ("Gamma Cas", 14.177, 60.717, 2.47),
]

# Deep-sky-object catalogue sources, all queried by real sky position (never
# by trying to scrape Siril's own bundled catalogues through catsearch's
# free-text console log — see CHANGELOG 1.23.1 vs 1.26.0 for that history):
#   - Messier / NGC / IC   -> OpenNGC (github.com/mattiaverga/OpenNGC),
#                             downloaded once and cached on disk — real
#                             structured RA/Dec/type/magnitude columns.
#   - Sharpless (Sh2)      -> VizieR catalogue VII/20, live cone search.
#   - Lynds Dark Neb (LdN) -> VizieR catalogue VII/7A, live cone search.
OPENNGC_URL = ("https://raw.githubusercontent.com/mattiaverga/OpenNGC/"
               "master/database_files/NGC.csv")
VIZIER_URL = "https://vizier.cds.unistra.fr/viz-bin/asu-tsv"
ANNOTATE_MAX_PER_CATALOG = 300  # safety cap against cluttered wide fields

# One color per catalogue "kind" so objects from different catalogues are
# visually distinguishable in the preview/export (BGR, for cv2 drawing).
CATALOG_COLORS = {
    "star": (120, 220, 255),      # warm yellow
    "messier": (255, 190, 90),    # sky blue
    "ngc": (140, 255, 140),       # green
    "ic": (255, 140, 220),        # pink/magenta
    "sh2": (60, 160, 255),        # orange
    "ldn": (200, 200, 200),       # neutral gray (dark nebulae)
}
CATALOG_LABELS = {
    "star": "Star", "messier": "Messier", "ngc": "NGC", "ic": "IC",
    "sh2": "Sharpless", "ldn": "LDN",
}

def _ang_sep(ra1, dec1, ra2, dec2):
    """Great-circle angular separation between two RA/Dec points, in
    degrees. Uses the standard spherical law-of-cosines formula, which
    handles the RA=0/360 wraparound correctly (unlike a naive |ra1-ra2|
    subtraction)."""
    r = math.radians
    d = (math.sin(r(dec1)) * math.sin(r(dec2)) +
         math.cos(r(dec1)) * math.cos(r(dec2)) * math.cos(r(ra1 - ra2)))
    return math.degrees(math.acos(max(-1.0, min(1.0, d))))


def _sexa_to_deg(text, is_ra):
    """Parse a colon-separated sexagesimal coordinate string (e.g.
    "00:42:44.3" or "+41:16:09") into decimal degrees. `is_ra` multiplies
    the result by 15 to convert hours to degrees."""
    parts = text.strip().replace(":", " ").split()
    if not parts:
        raise ValueError(f"empty coordinate string: {text!r}")
    sign = -1.0 if parts[0].lstrip().startswith("-") else 1.0
    vals = [abs(float(p)) for p in parts]
    deg = vals[0] + vals[1] / 60.0 + (vals[2] if len(vals) > 2 else 0.0) / 3600.0
    if is_ra:
        deg *= 15.0
    return sign * deg


def _http_get(url, timeout=60):
    req = urllib.request.Request(
        url, headers={"User-Agent": "S30Pro-Pipeline-Annotate/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _parse_vizier_tsv(text):
    """Parse VizieR's classic TSV cone-search response into a list of
    {column: value} dicts. Separated from the HTTP fetch (`_vizier_cone`)
    so this parsing logic can be unit-tested with a canned response
    string, without needing network access."""
    lines = [ln for ln in text.splitlines() if ln and not ln.startswith("#")]
    rows, header = [], None
    for line in lines:
        cells = line.split("\t")
        if header is None:
            if "_RAJ2000" in cells:
                header = cells
            continue
        if set(line) <= set("-\t "):          # dashes separator row
            continue
        row = dict(zip(header, (c.strip() for c in cells)))
        try:
            float(row["_RAJ2000"])
        except (KeyError, ValueError):        # units row / junk
            continue
        rows.append(row)
    return rows


def _vizier_cone(source, ra, dec, radius_deg, out_cols, timeout=60):
    """Cone search on VizieR's classic TSV interface; returns a list of
    {column: value} dicts. `_RAJ2000`/`_DEJ2000` (computed decimal-degree
    columns) are always requested in addition to `out_cols`."""
    params = {
        "-source": source,
        "-c": "%f %+f" % (ra, dec),
        "-c.rd": "%f" % radius_deg,
        "-out.add": "_RAJ2000,_DEJ2000",
        "-out": ",".join(out_cols),
        "-out.max": "100000",
    }
    text = _http_get(VIZIER_URL + "?" + urllib.parse.urlencode(params),
                     timeout=timeout)
    return _parse_vizier_tsv(text)


def _clean_ngc_ic_name(raw):
    """"NGC0224" -> "NGC 224", "IC0434" -> "IC 434" (OpenNGC zero-pads
    catalogue numbers and omits the space)."""
    raw = raw.strip()
    for prefix in ("NGC", "IC"):
        if raw.startswith(prefix):
            num = raw[len(prefix):].lstrip("0") or "0"
            return f"{prefix} {num}"
    return raw


