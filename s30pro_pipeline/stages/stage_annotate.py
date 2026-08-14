"""Annotate (stars, deep-sky objects, constellation lines) stage mixin for
UnifiedPipelineWindow."""

import os
import csv
import math
import tempfile
from datetime import datetime

import numpy as np
import cv2

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QColorDialog, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QSpinBox,
    QVBoxLayout,
)
from PyQt6.QtGui import QColor

from astropy.io import fits
from appdirs import user_data_dir

from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_ANN
from s30pro_pipeline.catalog_data import (
    BRIGHT_STARS, OPENNGC_URL, ANNOTATE_MAX_PER_CATALOG,
    CATALOG_COLORS, CATALOG_LABELS, _ang_sep, _sexa_to_deg, _http_get,
    _vizier_cone, _clean_ngc_ic_name,
)
from s30pro_pipeline.constellation_data import (
    CONSTELLATION_NAMES, CONSTELLATION_COLOR_PRESETS,
    _load_constellation_lines, _filter_constellation_lines, _inset_segment,
)
from s30pro_pipeline.image_utils import to_hwc_float, make_qimage


class AnnotateMixin:
    @staticmethod
    def _color_swatch(bgr_color):
        """A small colored square QLabel used next to each catalogue
        checkbox in the Annotate stage, so the UI's colors visually match
        what gets drawn in the preview."""
        lbl = QLabel()
        lbl.setFixedSize(14, 14)
        r, g, b = bgr_color[2], bgr_color[1], bgr_color[0]
        lbl.setStyleSheet(
            f"background-color: rgb({r},{g},{b}); border-radius: 3px; "
            "border: 1px solid rgba(255,255,255,60);")
        return lbl

    def _build_stage_ann(self):
        box, v = self._stage_box(12, "Annotate — Stars & Deep-Sky Objects",
                                 enabled_check=False)
        self.stage_ann_box = box

        info = QLabel("Labels stars and deep-sky objects for whatever's "
                      "actually in the plate-solved field. Messier/NGC/IC "
                      "come from OpenNGC (downloaded once, cached on disk); "
                      "Sharpless and Lynds Dark Nebulae come from live "
                      "VizieR cone searches — real structured data, not "
                      "guessed from Siril's console log. Each catalogue "
                      "gets its own color, shown next to its checkbox "
                      "below. Use \"Select objects to show...\" after "
                      "running to pick individual objects — changes apply "
                      "to the preview immediately. Constellation "
                      "stick-figure lines are a separate, always-offline "
                      "layer — pick which constellations to include with "
                      "\"Select constellations...\". Saves an annotated "
                      "JPG next to your data — the FITS image itself is "
                      "not modified.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        # 2 columns throughout (swatch+checkbox, or label+control), one
        # item per row — keeps every row readable at the ~1/3-window-width
        # target; several checkbox labels here are long enough that a
        # wider multi-column layout would either overflow or force the
        # (non-wrapping) checkbox text to clip.
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        g.setColumnStretch(1, 1)
        row = 0

        self.ann_stars_checkbox = QCheckBox("Stars (local catalogue)")
        self.ann_stars_checkbox.setChecked(True)
        self.ann_stars_checkbox.setToolTip(
            "Queries Siril's own local Bright Star Catalogue (3,661 stars, "
            "no internet needed) for stars in the field down to the star "
            "magnitude limit. Falls back to this script's own small "
            "bundled star list if Siril's conesearch command isn't "
            "available (Siril < 1.3).")
        g.addWidget(self._color_swatch(CATALOG_COLORS["star"]), row, 0)
        g.addWidget(self.ann_stars_checkbox, row, 1)
        row += 1
        g.addWidget(QLabel("Star mag limit:"), row, 0)
        self.ann_mag_spin = QDoubleSpinBox()
        self.ann_mag_spin.setRange(0.0, 12.0)
        self.ann_mag_spin.setSingleStep(0.5)
        self.ann_mag_spin.setValue(6.0)
        g.addWidget(self.ann_mag_spin, row, 1)
        row += 1

        self.ann_cat_messier_checkbox = QCheckBox("Messier")
        self.ann_cat_messier_checkbox.setChecked(True)
        self.ann_cat_messier_checkbox.setToolTip(
            "The 110 Messier objects, from OpenNGC (real RA/Dec, no "
            "coordinate guessing). Downloaded once and cached on disk — "
            "later runs use the cached copy, no internet needed.")
        g.addWidget(self._color_swatch(CATALOG_COLORS["messier"]), row, 0)
        g.addWidget(self.ann_cat_messier_checkbox, row, 1)
        row += 1

        self.ann_cat_ngc_checkbox = QCheckBox("NGC (New General Catalogue)")
        self.ann_cat_ngc_checkbox.setChecked(True)
        self.ann_cat_ngc_checkbox.setToolTip(
            "~8,000 NGC objects, from the same cached OpenNGC data as "
            "Messier above.")
        g.addWidget(self._color_swatch(CATALOG_COLORS["ngc"]), row, 0)
        g.addWidget(self.ann_cat_ngc_checkbox, row, 1)
        row += 1

        self.ann_cat_ic_checkbox = QCheckBox("IC (Index Catalogue)")
        self.ann_cat_ic_checkbox.setChecked(True)
        self.ann_cat_ic_checkbox.setToolTip(
            "~5,000 IC objects, from the same cached OpenNGC data as "
            "Messier above.")
        g.addWidget(self._color_swatch(CATALOG_COLORS["ic"]), row, 0)
        g.addWidget(self.ann_cat_ic_checkbox, row, 1)
        row += 1

        self.ann_cat_sh2_checkbox = QCheckBox("Sharpless (Sh2)")
        self.ann_cat_sh2_checkbox.setToolTip(
            "Sharpless catalogue of HII regions/emission nebulae, queried "
            "live from VizieR (catalogue VII/20) for the current field. "
            "Needs internet on every run — off by default for that "
            "reason.")
        g.addWidget(self._color_swatch(CATALOG_COLORS["sh2"]), row, 0)
        g.addWidget(self.ann_cat_sh2_checkbox, row, 1)
        row += 1

        self.ann_cat_ldn_checkbox = QCheckBox("Lynds Dark Nebulae (LdN)")
        self.ann_cat_ldn_checkbox.setToolTip(
            "Lynds Catalogue of Dark Nebulae, queried live from VizieR "
            "(catalogue VII/7A) for the current field. Needs internet on "
            "every run — off by default for that reason.")
        g.addWidget(self._color_swatch(CATALOG_COLORS["ldn"]), row, 0)
        g.addWidget(self.ann_cat_ldn_checkbox, row, 1)
        row += 1

        g.addWidget(QLabel("Label size:"), row, 0)
        self.ann_size_spin = QDoubleSpinBox()
        self.ann_size_spin.setRange(0.5, 3.0)
        self.ann_size_spin.setSingleStep(0.1)
        self.ann_size_spin.setValue(1.0)
        g.addWidget(self.ann_size_spin, row, 1)
        row += 1

        # -------------------------------------------------- constellation lines
        # Selection defaults to every constellation; picked by abbreviation
        # (CONSTELLATION_NAMES keys) via the "Select constellations..."
        # dialog below, not a per-item checkbox in this grid (88 of them
        # wouldn't fit).
        self.ann_const_selected = set(CONSTELLATION_NAMES.keys())
        _default_preset = "Pale Lavender (default)"
        self.ann_const_color, self.ann_const_name_color = \
            CONSTELLATION_COLOR_PRESETS[_default_preset]
        self.ann_const_checkbox = QCheckBox("Constellation lines")
        self.ann_const_checkbox.setToolTip(
            "Draws stick-figure lines between bright stars for whichever "
            "constellations are (at least partly) in the plate-solved "
            "field. Line topology is a widely used amateur/planetarium "
            "\"connect the dots\" set (from the open-source d3-celestial "
            "project), embedded and fully offline — the IAU only defines "
            "official constellation *boundaries*, not lines, so different "
            "atlases draw slightly different stick figures for the same "
            "constellation. Use \"Select constellations...\" below to "
            "leave some out.")
        g.addWidget(self.ann_const_checkbox, row, 0, 1, 2)
        row += 1

        self.ann_const_names_checkbox = QCheckBox("Show constellation names")
        self.ann_const_names_checkbox.setChecked(True)
        self.ann_const_names_checkbox.setToolTip(
            "Labels each drawn constellation with its name, centered over "
            "whichever part of its stick figure is inside the frame.")
        g.addWidget(self.ann_const_names_checkbox, row, 0, 1, 2)
        row += 1

        g.addWidget(QLabel("Line width:"), row, 0)
        self.ann_const_width_spin = QSpinBox()
        self.ann_const_width_spin.setRange(1, 8)
        self.ann_const_width_spin.setValue(1)
        self.ann_const_width_spin.setToolTip(
            "Thickness of the constellation lines, in pixels (scaled up "
            "automatically for high-resolution stacks).")
        g.addWidget(self.ann_const_width_spin, row, 1)
        row += 1

        g.addWidget(QLabel("Gap (px):"), row, 0)
        self.ann_const_gap_spin = QSpinBox()
        self.ann_const_gap_spin.setRange(0, 60)
        self.ann_const_gap_spin.setValue(8)
        self.ann_const_gap_spin.setToolTip(
            "Shortens each line segment by this many pixels from both "
            "ends, so lines don't touch the stars directly — 0 draws "
            "star-to-star with no gap.")
        g.addWidget(self.ann_const_gap_spin, row, 1)
        row += 1

        g.addWidget(QLabel("Color preset:"), row, 0)
        self.ann_const_preset_combo = QComboBox()
        self.ann_const_preset_combo.addItem("Custom")
        self.ann_const_preset_combo.addItems(
            list(CONSTELLATION_COLOR_PRESETS.keys()))
        self.ann_const_preset_combo.setCurrentText(_default_preset)
        self.ann_const_preset_combo.setToolTip(
            "Quick-pick a matched line/name color scheme. Picking either "
            "color manually below switches this back to \"Custom\".")
        self.ann_const_preset_combo.currentTextChanged.connect(
            self._apply_constellation_preset)
        g.addWidget(self.ann_const_preset_combo, row, 1)
        row += 1

        self.ann_const_swatch = self._color_swatch(self.ann_const_color)
        self.ann_const_color_btn = QPushButton("Line color...")
        self.ann_const_color_btn.setToolTip(
            "Pick a custom color for the constellation lines themselves.")
        self.ann_const_color_btn.clicked.connect(
            lambda: self._pick_constellation_color("line"))
        g.addWidget(self.ann_const_swatch, row, 0)
        g.addWidget(self.ann_const_color_btn, row, 1)
        row += 1

        self.ann_const_name_swatch = self._color_swatch(
            self.ann_const_name_color)
        self.ann_const_name_color_btn = QPushButton("Name color...")
        self.ann_const_name_color_btn.setToolTip(
            "Pick a custom color for the constellation name labels — "
            "independent of the line color above.")
        self.ann_const_name_color_btn.clicked.connect(
            lambda: self._pick_constellation_color("name"))
        g.addWidget(self.ann_const_name_swatch, row, 0)
        g.addWidget(self.ann_const_name_color_btn, row, 1)
        row += 1

        self.ann_online_checkbox = QCheckBox("All stars < mag limit (online BSC)")
        self.ann_online_checkbox.setToolTip(
            "Siril's local star catalogue covers the field well already; "
            "this additionally runs Siril's own online conesearch against "
            "the VizieR Bright Star Catalogue for every star below the "
            "star magnitude limit, for denser coverage. Needs internet.")
        g.addWidget(self.ann_online_checkbox, row, 0, 1, 2)
        row += 1

        self.ann_show_overlay_checkbox = QCheckBox("Show annotation overlay")
        self.ann_show_overlay_checkbox.setChecked(True)
        self.ann_show_overlay_checkbox.setToolTip(
            "Uncheck to hide the markers/labels — running the stage will then "
            "just show the plain image (useful if you want to keep the stage "
            "in the pipeline but not clutter the preview/export with labels).")
        g.addWidget(self.ann_show_overlay_checkbox, row, 0, 1, 2)
        v.addLayout(g)

        row, self.stage_ann_run = self._run_row(
            lambda: self._launch([self._exec_stage_ann]), undo_stage=IDX_ANN)
        v.addLayout(row)

        # 2 buttons per row instead of 4 in one — same width fix already
        # applied to the bottom Save/Export/Reset/Close row.
        save_row1 = QHBoxLayout()
        self.ann_save_btn = QPushButton("💾  Save image...")
        self.ann_save_btn.setToolTip(
            "Export the last annotated result as JPEG or PNG, wherever "
            "you choose.")
        self.ann_save_btn.clicked.connect(self.on_save_annotated_image)
        save_row1.addWidget(self.ann_save_btn)
        self.ann_select_btn = QPushButton("☑  Select objects...")
        self.ann_select_btn.setToolTip(
            "Pick which of the labeled objects stay visible — unchecking "
            "one removes it from the preview and export immediately, no "
            "need to re-run the stage.")
        self.ann_select_btn.clicked.connect(self._show_object_selector_dialog)
        save_row1.addWidget(self.ann_select_btn)
        v.addLayout(save_row1)

        save_row2 = QHBoxLayout()
        self.ann_const_select_btn = QPushButton("🌌  Select constellations...")
        self.ann_const_select_btn.setToolTip(
            "Choose which of the 88 constellations get stick-figure lines "
            "drawn, if \"Constellation lines\" above is checked. Applies "
            "the next time the Annotate stage runs.")
        self.ann_const_select_btn.clicked.connect(
            self._show_constellation_selector_dialog)
        save_row2.addWidget(self.ann_const_select_btn)
        self.ann_remove_all_btn = QPushButton("🗑  Remove all")
        self.ann_remove_all_btn.setToolTip(
            "Hide every labeled object at once — one click, no need to "
            "open \"Select objects to show...\" and uncheck them "
            "individually. Non-destructive, same as unchecking every "
            "object there: the underlying FITS image is never touched, "
            "and re-running the stage brings the labels back. Doesn't "
            "affect constellation lines — uncheck \"Constellation lines\" "
            "and re-run to remove those.")
        self.ann_remove_all_btn.clicked.connect(self._remove_all_annotations)
        save_row2.addWidget(self.ann_remove_all_btn)
        v.addLayout(save_row2)
        return box

    # ------------------------------------------- Siril catalogue (conesearch)
    # Used only for stars — Siril's own bundled/online Bright Star Catalogue
    # conesearch has always worked reliably (unlike catsearch's per-name,
    # log-scraped lookups this script used to rely on for DSOs — see
    # CHANGELOG 1.23.1/1.26.0).

    def _run_siril_conesearch(self, mag_limit, cat=None, label="catalog"):
        """Query Siril's own `conesearch` command (Siril 1.3+, scriptable)
        against the currently loaded, plate-solved image and return a list
        of (name, ra, dec) tuples parsed from its CSV export.

        `cat=None` uses Siril's local offline catalogue — for stars this is
        the bundled Bright Star Catalogue (3,661 stars); passing e.g.
        `cat="bsc"` queries the matching online VizieR catalogue instead.

        Returns an empty list (never raises) if the command isn't available
        (older Siril) or produces nothing usable — callers fall back to the
        script's own hardcoded lists in that case.
        """
        fd, csv_path = tempfile.mkstemp(suffix=".csv", prefix="s30_conesearch_")
        os.close(fd)
        try:
            args = ["conesearch"]
            if mag_limit is not None:
                args.append(f"{mag_limit:.2f}")
            if cat:
                args.append(f"-cat={cat}")
            args.append("-log=off")
            args.append("-tag=off")
            args.append(f"-out={csv_path}")
            self.siril.cmd(*args)
            if not os.path.isfile(csv_path) or os.path.getsize(csv_path) == 0:
                return []
            return self._parse_conesearch_csv(csv_path)
        except Exception as e:
            self.siril.log(
                f"Siril conesearch ({label}) unavailable or failed, falling "
                f"back to this script's own list: {e}", LogColor.SALMON)
            return []
        finally:
            try:
                os.remove(csv_path)
            except OSError:
                pass

    @staticmethod
    def _parse_conesearch_csv(path):
        """Flexible CSV parser for `conesearch -out=` results — column
        names aren't strictly pinned down across Siril catalogues (ra/dec
        vs RAJ2000/DEJ2000, name vs id, etc.), so this looks for common
        variants rather than assuming one exact schema."""
        try:
            with open(path, newline="", encoding="utf-8", errors="replace") as f:
                lines = [ln for ln in f if not ln.lstrip().startswith("#")]
        except OSError:
            return []
        if not lines:
            return []
        reader = csv.DictReader(lines)
        if not reader.fieldnames:
            return []
        norm = {fn: fn.strip().lower() for fn in reader.fieldnames}

        def pick(row, *candidates):
            for orig, low in norm.items():
                if low in candidates:
                    v = row.get(orig)
                    if v not in (None, ""):
                        return v
            return None

        out = []
        for row in reader:
            ra = pick(row, "ra", "raj2000")
            dec = pick(row, "dec", "dej2000", "decl", "de")
            if ra is None or dec is None:
                continue
            try:
                ra_f, dec_f = float(ra), float(dec)
            except (TypeError, ValueError):
                continue
            name = pick(row, "name", "id", "designation", "object") or ""
            name = str(name).strip()
            if not name:
                continue
            out.append((name, ra_f, dec_f))
        return out

    # -------------------------------------------- deep-sky catalogue sources

    def _fetch_openngc_rows(self):
        """Download (once, cached on disk under this script's own appdirs
        data directory) and parse the OpenNGC database — real structured
        Messier/NGC/IC data (RA/Dec/type/magnitude columns), instead of
        trying to scrape Siril's own bundled catalogues through catsearch's
        free-text console log (see CHANGELOG 1.26.0). Also cached in memory
        for the life of this window, so re-running the stage doesn't
        re-parse ~14,000 rows every time."""
        if getattr(self, "_openngc_rows", None) is not None:
            return self._openngc_rows
        cache_dir = os.path.join(user_data_dir(appname="S30ProPipeline"),
                                 "catalogs")
        os.makedirs(cache_dir, exist_ok=True)
        cache_path = os.path.join(cache_dir, "OpenNGC.csv")
        if not os.path.isfile(cache_path):
            data = _http_get(OPENNGC_URL, timeout=120)
            with open(cache_path, "w", encoding="utf-8") as f:
                f.write(data)
        with open(cache_path, encoding="utf-8") as f:
            rows = list(csv.DictReader(f, delimiter=";"))
        self._openngc_rows = rows
        return rows

    @staticmethod
    def _filter_openngc_rows(rows, ra, dec, radius, want_messier, want_ngc,
                             want_ic):
        """Pure filtering logic over already-fetched OpenNGC rows — kept
        separate from `_fetch_openngc_rows`'s I/O so it can be unit-tested
        with synthetic rows, no network or disk needed. Returns a list of
        (label, ra, dec, kind, size_arcmin) with kind in
        {"messier","ngc","ic"}; size_arcmin is OpenNGC's MajAx (apparent
        major axis, arcminutes) as a float, or None if the row doesn't
        have one — used to size each object's marker to its real apparent
        footprint instead of a fixed generic radius."""
        out = []
        for row in rows:
            name_raw = (row.get("Name") or "").strip()
            if (row.get("Type") in ("NonEx", "Dup") or not name_raw
                    or not row.get("RA") or not row.get("Dec")):
                continue
            is_messier = bool(row.get("M"))
            is_ic = name_raw.startswith("IC")
            kind = "messier" if is_messier else ("ic" if is_ic else "ngc")
            if kind == "messier" and not want_messier:
                continue
            if kind == "ic" and not want_ic:
                continue
            if kind == "ngc" and not want_ngc:
                continue
            try:
                ora = _sexa_to_deg(row["RA"], is_ra=True)
                odec = _sexa_to_deg(row["Dec"], is_ra=False)
            except (ValueError, IndexError):
                continue
            if _ang_sep(ra, dec, ora, odec) > radius:
                continue
            if kind == "messier":
                try:
                    label = f"M {int(row['M'])}"
                except (TypeError, ValueError):
                    label = _clean_ngc_ic_name(name_raw)
            else:
                label = _clean_ngc_ic_name(name_raw)
            try:
                size_arcmin = float(row.get("MajAx") or "")
                if not (size_arcmin > 0):
                    size_arcmin = None
            except (TypeError, ValueError):
                size_arcmin = None
            out.append((label, ora, odec, kind, size_arcmin))
        return out

    def _objects_openngc(self, ra, dec, radius, want_messier, want_ngc,
                         want_ic):
        return self._filter_openngc_rows(
            self._fetch_openngc_rows(), ra, dec, radius, want_messier,
            want_ngc, want_ic)

    @staticmethod
    def _objects_sh2(ra, dec, radius):
        """Returns (label, ra, dec, size_arcmin). VizieR VII/20's "Diam"
        column is the nebula's apparent diameter in arcminutes — used the
        same way as OpenNGC's MajAx, to size the marker to the real
        object instead of a fixed radius."""
        rows = _vizier_cone("VII/20", ra, dec, radius, ["Sh2", "Diam"])
        out = []
        for r in rows:
            if not r.get("Sh2"):
                continue
            try:
                size = float(r.get("Diam") or "")
                if not (size > 0):
                    size = None
            except (TypeError, ValueError):
                size = None
            out.append((f"Sh2-{r.get('Sh2', '?')}", float(r["_RAJ2000"]),
                        float(r["_DEJ2000"]), size))
        return out

    @staticmethod
    def _objects_ldn(ra, dec, radius):
        """Returns (label, ra, dec, size_arcmin). VizieR VII/7A gives dark
        nebula extent as "Area" in square degrees rather than a diameter,
        so approximate an equivalent circular diameter from it
        (diam = 2 * sqrt(area / pi))."""
        rows = _vizier_cone("VII/7A", ra, dec, radius, ["LDN", "Area"])
        out = []
        for r in rows:
            if not r.get("LDN"):
                continue
            try:
                area_deg2 = float(r.get("Area") or "")
                size = (2.0 * math.sqrt(area_deg2 / math.pi) * 60.0
                        if area_deg2 > 0 else None)
            except (TypeError, ValueError):
                size = None
            out.append((f"LDN {r.get('LDN', '?')}", float(r["_RAJ2000"]),
                        float(r["_DEJ2000"]), size))
        return out

    def _draw_constellation_lines(self, canvas, wcs, W, H):
        """Draws the selected constellations' stick-figure lines (and, if
        enabled, name labels) directly onto `canvas` (BGR uint8, display
        orientation, mutated in place). Returns the number of
        constellations that ended up with at least one on-canvas segment.
        Independent of the DSO/star marker system in _exec_stage_ann:
        lines come from the fixed embedded dataset in
        _load_constellation_lines(), not a per-run catalogue query."""
        import warnings

        selected = getattr(self, "ann_const_selected", None)
        if not selected:
            return 0
        lines_by_const = _filter_constellation_lines(
            _load_constellation_lines(), selected)
        if not lines_by_const:
            return 0

        # Same resolution-scaling idea as the marker/label sizing below in
        # _exec_stage_ann, computed independently here since this method
        # can be called before that block runs.
        res_scale = float(np.clip(max(W, H) / 1600.0, 1.0, 6.0))
        width_px = max(1, int(round(
            self.ann_const_width_spin.value() * res_scale)))
        gap_px = self.ann_const_gap_spin.value() * res_scale
        color = self.ann_const_color
        name_color = getattr(self, "ann_const_name_color", color)
        show_names = self.ann_const_names_checkbox.isChecked()
        fs = 0.6 * res_scale
        th = max(1, int(round(fs * 2.0)))

        drawn_count = 0
        with warnings.catch_warnings():
            # Same rationale as _exec_stage_ann's own suppression block:
            # SIP/WCS solvers legitimately fail to converge to full
            # precision for points far from the plate-solve center (very
            # common here — constellation figures routinely extend well
            # beyond the field), which would otherwise flood the console
            # with a per-point UserWarning.
            warnings.simplefilter("ignore")
            for abbr, polylines in lines_by_const.items():
                onscreen_pts = []
                any_segment = False
                for chain in polylines:
                    if len(chain) < 2:
                        continue
                    ras = np.array([p[0] for p in chain], dtype=np.float64)
                    decs = np.array([p[1] for p in chain], dtype=np.float64)
                    try:
                        xs, ys = wcs.wcs_world2pix(ras, decs, 0)
                    except Exception:
                        continue
                    pix = []
                    for x, y in zip(xs, ys):
                        if not (np.isfinite(x) and np.isfinite(y)):
                            pix.append(None)
                            continue
                        xd = float(np.clip(x, -1e6, 1e6))
                        yd = float(np.clip(H - 1 - y, -1e6, 1e6))
                        pix.append((xd, yd))
                        if 0 <= xd < W and 0 <= yd < H:
                            onscreen_pts.append((xd, yd))
                    for p1, p2 in zip(pix, pix[1:]):
                        if p1 is None or p2 is None:
                            continue
                        q1, q2 = _inset_segment(p1, p2, gap_px)
                        cv2.line(canvas,
                                (int(round(q1[0])), int(round(q1[1]))),
                                (int(round(q2[0])), int(round(q2[1]))),
                                color, width_px, cv2.LINE_AA)
                        any_segment = True
                if any_segment:
                    drawn_count += 1
                    if show_names and onscreen_pts:
                        cx = int(round(
                            sum(p[0] for p in onscreen_pts) / len(onscreen_pts)))
                        cy = int(round(
                            sum(p[1] for p in onscreen_pts) / len(onscreen_pts)))
                        name = CONSTELLATION_NAMES.get(abbr, abbr)
                        cv2.putText(canvas, name, (cx, cy),
                                   cv2.FONT_HERSHEY_SIMPLEX, fs, (0, 0, 0),
                                   th + 2, cv2.LINE_AA)
                        cv2.putText(canvas, name, (cx, cy),
                                   cv2.FONT_HERSHEY_SIMPLEX, fs, name_color,
                                   th, cv2.LINE_AA)
        return drawn_count

    def _exec_stage_ann(self, progress):
        from astropy.wcs import WCS
        import warnings

        progress("Annotate: reading plate-solve solution...", 0.05)
        hdr_str = self.siril.get_image_fits_header()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            header = fits.Header.fromstring(hdr_str, sep="\n")
            # RGB FITS files carry 3 axes; celestial WCS (and SIP distortion)
            # is strictly 2D, so restrict to the first two axes.
            wcs = WCS(header, naxis=2).celestial
        if not wcs.has_celestial or wcs.wcs.crval[0] == 0 and \
                wcs.wcs.crval[1] == 0:
            raise RuntimeError(
                "No valid plate-solve solution in the image header. "
                "Run plate solving (stage 1 with SPCC, or Siril's 'platesolve') "
                "before annotating.")

        before_img = self._get_current_image()
        img, stars_reconciled = self._reconcile_held_stars(before_img, progress)
        if stars_reconciled:
            # Push the recombined image back into Siril too, not just the
            # annotated JPG, so the saved FITS isn't left starless.
            self._set_current_image(
                img, "AstroPipeline: stars re-added (fallback, before annotate)")
        hwc = to_hwc_float(img)
        H, W, _ = hwc.shape
        # match Siril's display orientation (FITS row 0 = bottom)
        canvas = np.flipud(hwc)
        canvas = (np.clip(canvas, 0, 1) * 255).astype(np.uint8)
        canvas = cv2.cvtColor(canvas, cv2.COLOR_RGB2BGR)

        show_overlay = self.ann_show_overlay_checkbox.isChecked()
        drawn = 0
        out_path = None

        if show_overlay:
            mag_limit = self.ann_mag_spin.value()
            targets = []  # (label, ra, dec, kind, size_arcmin)
            seen = set()  # (round(ra,3), round(dec,3)) — de-dupe across queries

            def add_targets(items, kind):
                # Each item is (name, ra, dec) for stars/no-size sources, or
                # (name, ra, dec, size_arcmin) for catalogues that carry an
                # apparent-size field — size_arcmin drives the marker radius
                # in the drawing pass below, defaulting to None (fixed
                # radius) when a source doesn't provide one.
                for item in items:
                    name, ra, dec = item[0], item[1], item[2]
                    size = item[3] if len(item) > 3 else None
                    key = (round(ra, 3), round(dec, 3))
                    if key in seen:
                        continue
                    seen.add(key)
                    targets.append((name, ra, dec, kind, size))

            if self.ann_stars_checkbox.isChecked():
                progress("Annotate: querying Siril's local star catalogue...",
                         0.1)
                stars = self._run_siril_conesearch(mag_limit, cat=None,
                                                    label="local stars")
                if stars:
                    add_targets(stars, "star")
                else:
                    # Older Siril without conesearch, or the query failed —
                    # fall back to this script's own bundled bright-star list.
                    for name, ra, dec, mag in BRIGHT_STARS:
                        if mag <= mag_limit:
                            add_targets([(name, ra, dec)], "star")

            # Field center + radius from the plate-solve WCS — a real API
            # call (wcs_pix2world), not anything scraped from a log — used
            # to drive bulk cone searches against real catalogue sources
            # below, one query per catalogue instead of walking a list of
            # candidate names one at a time.
            want_messier = self.ann_cat_messier_checkbox.isChecked()
            want_ngc = self.ann_cat_ngc_checkbox.isChecked()
            want_ic = self.ann_cat_ic_checkbox.isChecked()
            want_sh2 = self.ann_cat_sh2_checkbox.isChecked()
            want_ldn = self.ann_cat_ldn_checkbox.isChecked()
            cra = cdec = radius = None
            if want_messier or want_ngc or want_ic or want_sh2 or want_ldn:
                progress("Annotate: computing field coverage...", 0.15)
                try:
                    corners = np.array(
                        [[0, 0], [W - 1, 0], [0, H - 1], [W - 1, H - 1],
                         [W / 2.0, H / 2.0]], dtype=np.float64)
                    world = wcs.wcs_pix2world(corners, 0)
                    cra, cdec = float(world[4][0]), float(world[4][1])
                    radius = 0.0
                    for wra, wdec in world[:4]:
                        radius = max(radius, _ang_sep(cra, cdec, wra, wdec))
                    radius *= 1.02  # small margin
                except Exception as e:
                    self.siril.log(
                        "Annotate: couldn't compute field coverage from the "
                        f"plate-solve WCS, skipping catalogue lookups: {e}",
                        LogColor.SALMON)
                    want_messier = want_ngc = want_ic = want_sh2 = want_ldn = False

            if want_messier or want_ngc or want_ic:
                progress("Annotate: fetching Messier/NGC/IC (OpenNGC)...", 0.25)
                try:
                    found = self._objects_openngc(
                        cra, cdec, radius, want_messier, want_ngc, want_ic)
                    by_kind = {"messier": [], "ngc": [], "ic": []}
                    for name, ra_, dec_, kind, size_ in found:
                        by_kind[kind].append((name, ra_, dec_, size_))
                    for kind, items in by_kind.items():
                        if items:
                            add_targets(items[:ANNOTATE_MAX_PER_CATALOG], kind)
                except Exception as e:
                    self.siril.log(
                        f"Annotate: OpenNGC (Messier/NGC/IC) fetch failed: "
                        f"{e}", LogColor.SALMON)

            if want_sh2:
                progress("Annotate: querying Sharpless catalogue (VizieR)...",
                         0.35)
                try:
                    add_targets(
                        self._objects_sh2(cra, cdec, radius)[:ANNOTATE_MAX_PER_CATALOG],
                        "sh2")
                except Exception as e:
                    self.siril.log(
                        f"Annotate: Sharpless (VizieR) query failed: {e}",
                        LogColor.SALMON)

            if want_ldn:
                progress("Annotate: querying Lynds Dark Nebulae (VizieR)...",
                         0.45)
                try:
                    add_targets(
                        self._objects_ldn(cra, cdec, radius)[:ANNOTATE_MAX_PER_CATALOG],
                        "ldn")
                except Exception as e:
                    self.siril.log(
                        f"Annotate: LDN (VizieR) query failed: {e}",
                        LogColor.SALMON)

            # All world<->pixel conversions below go through SIP/WCS iterative
            # solvers that legitimately fail to converge to full precision for
            # points near the field edge or far from the plate-solve center.
            # That's expected and harmless (we just skip those points), but
            # astropy raises a UserWarning *per point*, which can flood Siril's
            # console with dozens of "failed to converge" messages and make it
            # look like the stage has hung or crashed. Suppress for this block.
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")

                if self.ann_online_checkbox.isChecked():
                    progress("Annotate: querying Siril's online Bright Star "
                             "Catalogue (VizieR)...", 0.55)
                    online_stars = self._run_siril_conesearch(
                        mag_limit, cat="bsc", label="online BSC")
                    add_targets(online_stars, "star")

                progress("Annotate: drawing labels...", 0.65)
                # Scale markers/text with the image's actual pixel resolution
                # (a 4000px-wide Seestar stack shouldn't get the same 10px
                # circle as a 1000px preview). 1600px is the reference size
                # the base constants below were tuned for; floor at 1.0 so
                # small images don't shrink further, cap at 6.0 so huge
                # images don't get absurd markers.
                res_scale = float(np.clip(max(W, H) / 1600.0, 1.0, 6.0))
                size_mult = self.ann_size_spin.value() * res_scale
                fs = 0.85 * size_mult
                th = max(2, int(round(fs * 2.3)))
                r_star = max(6, int(round(22 * size_mult)))
                r_dso = max(9, int(round(32 * size_mult)))
                # Cap real-size markers so a genuinely huge catalogue entry
                # (e.g. Barnard's Loop) never swallows the whole frame.
                r_dso_max = int(min(W, H) * 0.22)

                # Degrees-per-pixel, for converting an object's apparent
                # angular size (arcmin, from OpenNGC/VizieR) into an
                # on-image marker radius that matches its real footprint.
                try:
                    from astropy.wcs.utils import proj_plane_pixel_scales
                    px_scale_deg = float(
                        np.mean(np.abs(proj_plane_pixel_scales(wcs))))
                    if not (px_scale_deg > 0):
                        px_scale_deg = None
                except Exception:
                    px_scale_deg = None

                # Convert all targets in one vectorized call instead of one
                # SkyCoord + world_to_pixel per object — faster and produces a
                # single (suppressed) warning batch instead of one per point.
                if targets:
                    ras = np.array([t[1] for t in targets], dtype=np.float64)
                    decs = np.array([t[2] for t in targets], dtype=np.float64)
                    try:
                        xs, ys = wcs.wcs_world2pix(ras, decs, 0)
                    except Exception:
                        xs = ys = None
                else:
                    xs = ys = None

                # Build the list of *drawable* objects (label + pixel
                # position + style) instead of drawing directly — this is
                # kept around as self._ann_drawn so "Select objects to
                # show..." can redraw a subset from the un-annotated base
                # canvas without re-querying any catalogue.
                drawable = []
                for i, (label, ra, dec, kind, size_arcmin) in enumerate(targets):
                    if xs is None:
                        continue
                    x, y = float(xs[i]), float(ys[i])
                    if not np.isfinite(x) or not np.isfinite(y):
                        continue
                    if not (0 <= x < W and 0 <= y < H):
                        continue
                    yd = int(H - 1 - y)  # display-orientation flip
                    xd = int(x)
                    color = CATALOG_COLORS.get(kind, (200, 200, 200))
                    r = r_star if kind == "star" else r_dso
                    if kind != "star" and size_arcmin and px_scale_deg:
                        # Marker radius = half the object's real apparent
                        # diameter, in pixels — clamped so it's never
                        # smaller than the generic marker (tiny/point-like
                        # catalogue entries) nor absurdly large.
                        r_real = (size_arcmin / 60.0 / 2.0) / px_scale_deg
                        r = int(round(
                            np.clip(r_real, r_dso, r_dso_max)))
                    drawable.append({
                        "label": label, "kind": kind, "x": xd, "y": yd,
                        "r": r, "color": color, "fs": fs, "th": th,
                    })
                self._layout_annotation_labels(drawable, W, H)
                drawn = len(drawable)

            # Constellation lines are baked directly into `canvas` here,
            # before it's snapshotted as _ann_base_canvas below — unlike
            # the DSO/star markers above, they come from a fixed embedded
            # dataset rather than a per-run catalogue query, so there's no
            # "drawable" list to cache for a later live redraw. That means
            # "Select objects to show..."/"Remove all annotations" don't
            # affect them; toggle "Constellation lines" and re-run instead.
            const_drawn = 0
            if self.ann_const_checkbox.isChecked():
                progress("Annotate: drawing constellation lines...", 0.63)
                try:
                    const_drawn = self._draw_constellation_lines(
                        canvas, wcs, W, H)
                except Exception as e:
                    self.siril.log(
                        f"Annotate: constellation lines failed: {e}",
                        LogColor.SALMON)

            self._ann_base_canvas = canvas.copy()  # un-annotated, for redraws
            self._ann_drawn = drawable
            canvas = self._render_annotations(self._ann_base_canvas, drawable)

            now = datetime.now().strftime("%Y-%m-%d_%H%M")
            out_path = os.path.join(self.cwd, f"annotated_{now}.jpg")
            cv2.imwrite(out_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 95])
        else:
            self._ann_base_canvas = canvas.copy()
            self._ann_drawn = []

        # keep the raw BGR canvas around so "Save annotated image..." and
        # "Select objects to show..." can work from it without re-running
        # detection
        self._last_annotated_canvas = canvas.copy()

        annotated_rgb = cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB).astype(
            np.float32) / 255.0
        # `canvas`/`annotated_rgb` are already in display orientation (see
        # the np.flipud a few lines up) — the same orientation make_qimage
        # now applies automatically to every other stage's raw arrays, so
        # pass fits_orientation=False here to avoid flipping an
        # already-flipped canvas back the wrong way. That matters
        # especially for the rendered text: a pixel flip doesn't re-render
        # glyphs, it just turns them upside down, so a second flip here
        # cannot be "undone" by flipping marker positions alone.
        self.snapshots[IDX_ANN] = {
            "before": make_qimage(np.flipud(hwc), fits_orientation=False),
            "after": make_qimage(annotated_rgb, fits_orientation=False),
        }
        self.snapshot_ready.emit(IDX_ANN)

        self.stage_backups[IDX_ANN] = before_img
        self.snapshots_raw_after[IDX_ANN] = img
        self._last_run_stage_idx = IDX_ANN

        if show_overlay:
            const_suffix = (f", {const_drawn} constellation"
                           f"{'s' if const_drawn != 1 else ''}"
                           if const_drawn else "")
            progress(f"Annotate: done — {drawn} objects labeled"
                     f"{const_suffix}.", 1.0)
            self.siril.log(f"Annotated image saved: {out_path} "
                           f"({drawn} objects{const_suffix})", LogColor.GREEN)
        else:
            progress("Annotate: overlay hidden — showing plain image.", 1.0)
            self.siril.log("Annotate: overlay hidden, no labels drawn.",
                           LogColor.BLUE)

    @staticmethod
    def _layout_annotation_labels(items, W, H):
        """Choose a text position for each annotation marker in `items`
        (dicts with "label"/"x"/"y"/"r"/"fs"/"th" already set), avoiding
        overlap with already-placed labels and guaranteeing every label
        stays fully inside the [0,W)x[0,H) canvas — the two complaints
        with the fixed offset-from-marker approach this replaces (labels
        piling on top of each other in crowded fields, and labels getting
        clipped by the image edge near the border).

        Mutates each dict in `items` in place, adding/overwriting "tx"/
        "ty" (the cv2.putText baseline-left anchor point), and returns
        `items`. Greedy: bigger markers (which are usually the more
        important/prominent objects) get first pick of their preferred
        slot; each object tries a ring of candidate positions around its
        marker and takes the first one that's fully on-canvas and
        collision-free, falling back to the least-bad (fewest/smallest
        overlaps, still on-canvas if at all possible) candidate, then a
        hard clamp to the canvas edge as a last resort so text is never
        cut off even in a very crowded corner."""

        def box_for(tx, ty, tw, th_box):
            # cv2.putText's anchor point is the text's bottom-left corner.
            pad = 2
            return (tx - pad, ty - th_box - pad, tx + tw + pad, ty + pad)

        def overlap_area(a, b):
            ox = max(0, min(a[2], b[2]) - max(a[0], b[0]))
            oy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
            return ox * oy

        placed_boxes = []
        # Bigger markers claim their preferred spot first; smaller/fainter
        # objects fill in around them, which tends to keep the visually
        # dominant object's label closest to it.
        order = sorted(range(len(items)), key=lambda i: -items[i].get("r", 0))

        for idx in order:
            d = items[idx]
            (tw, th_box), baseline = cv2.getTextSize(
                d["label"], cv2.FONT_HERSHEY_SIMPLEX, d["fs"], d["th"])
            tw += 2
            th_box += baseline
            r, cx, cy, pad = d["r"], d["x"], d["y"], 4

            # Candidate anchor points on rings around the marker: 8
            # compass directions at an inner ring, then the same 8 a bit
            # farther out for crowded spots — right/upper-right first
            # since that's the conventional, least-surprising placement.
            dirs = [(1, 0), (1, -1), (1, 1), (0, -1), (0, 1),
                    (-1, 0), (-1, -1), (-1, 1)]
            candidates = []
            for ring in (1.0, 2.2):
                dist = r + pad + ring * 6
                for dx, dy in dirs:
                    tx = (cx + dist if dx > 0 else
                          cx - dist - tw if dx < 0 else cx - tw / 2.0)
                    ty = (cy - dist if dy < 0 else
                          cy + dist + th_box if dy > 0 else
                          cy + th_box / 2.0)
                    candidates.append((tx, ty))

            best = None
            for tx, ty in candidates:
                tx_i, ty_i = int(round(tx)), int(round(ty))
                box = box_for(tx_i, ty_i, tw, th_box)
                in_bounds = (box[0] >= 0 and box[1] >= 0 and
                            box[2] <= W and box[3] <= H)
                overlap = sum(overlap_area(box, pb) for pb in placed_boxes)
                score = (0 if in_bounds else 1, overlap)
                if best is None or score < best[0]:
                    best = (score, tx_i, ty_i, box)
                if score == (0, 0):
                    break

            _, tx_i, ty_i, box = best
            # Guarantee no clipping even if every candidate collided or ran
            # off-canvas (very crowded corner) by clamping the chosen box
            # fully inside the frame as a last resort.
            dx0 = max(0, -box[0])
            dx1 = min(0, W - box[2])
            dy0 = max(0, -box[1])
            dy1 = min(0, H - box[3])
            shift_x = dx0 if dx0 else dx1
            shift_y = dy0 if dy0 else dy1
            if shift_x or shift_y:
                tx_i += int(shift_x)
                ty_i += int(shift_y)
                box = (box[0] + shift_x, box[1] + shift_y,
                       box[2] + shift_x, box[3] + shift_y)

            d["tx"], d["ty"] = tx_i, ty_i
            placed_boxes.append(box)

        return items

    @staticmethod
    def _render_annotations(base_canvas, drawn):
        """Draw a list of annotation dicts (from _exec_stage_ann's
        `drawable`, or a filtered subset of self._ann_drawn) onto a copy of
        `base_canvas` (BGR uint8, un-annotated). Shared by the initial
        Annotate run and by "Select objects to show..." so both produce
        pixel-identical results for the objects they keep."""
        canvas = base_canvas.copy()
        for d in drawn:
            cv2.circle(canvas, (d["x"], d["y"]), d["r"], d["color"], d["th"],
                      cv2.LINE_AA)
            cv2.putText(canvas, d["label"], (d["tx"], d["ty"]),
                       cv2.FONT_HERSHEY_SIMPLEX, d["fs"], (0, 0, 0),
                       d["th"] + 2, cv2.LINE_AA)
            cv2.putText(canvas, d["label"], (d["tx"], d["ty"]),
                       cv2.FONT_HERSHEY_SIMPLEX, d["fs"], d["color"],
                       d["th"], cv2.LINE_AA)
        return canvas

    def _remove_all_annotations(self):
        """'🗑 Remove all annotations' — one-click equivalent of unchecking
        every object in "Select objects to show..." and pressing OK.
        Mirrors the Watermark stage's "Remove all watermarks" button, but
        Annotate never touches the underlying FITS pixel data in the
        first place (it's a redraw of a cached un-annotated base canvas),
        so unlike Watermark's remove-all this needs no pixel-level
        restore — just redraw with an empty kept-objects list."""
        base = getattr(self, "_ann_base_canvas", None)
        drawn = getattr(self, "_ann_drawn", None)
        if base is None:
            QMessageBox.information(
                self, "No annotated image",
                "Run the Annotate stage at least once first.")
            return
        if not drawn:
            QMessageBox.information(
                self, "Nothing to remove",
                "The last Annotate run didn't label any objects.")
            return

        new_canvas = self._render_annotations(base, [])
        self._ann_drawn = []
        self._last_annotated_canvas = new_canvas
        annotated_rgb = cv2.cvtColor(new_canvas, cv2.COLOR_BGR2RGB).astype(
            np.float32) / 255.0
        snap = self.snapshots.get(IDX_ANN, {})
        snap["after"] = make_qimage(annotated_rgb, fits_orientation=False)
        self.snapshots[IDX_ANN] = snap
        self.snapshot_ready.emit(IDX_ANN)
        self.status_label.setText("All annotations removed.")
        self.siril.log(
            "Annotate: all annotations removed from the preview/export "
            "(FITS image untouched). Re-run the stage to bring them "
            "back.", LogColor.GREEN)

    def _pick_constellation_color(self, target):
        """'Line color...' / 'Name color...' — opens a standard color
        picker for the constellation line color or the name-label color
        independently (`target` is "line" or "name"), seeded with the
        current color, and updates that control's preview swatch.
        Switches the preset dropdown to "Custom" (blocking its own signal
        so that doesn't immediately overwrite the color just picked).
        Doesn't touch anything already drawn — applies the next time the
        Annotate stage runs."""
        attr = "ann_const_color" if target == "line" else "ann_const_name_color"
        swatch = (self.ann_const_swatch if target == "line"
                  else self.ann_const_name_swatch)
        title = ("Constellation line color" if target == "line"
                 else "Constellation name color")
        b, g_, r = getattr(self, attr)
        initial = QColor(r, g_, b)
        color = QColorDialog.getColor(initial, self, title)
        if not color.isValid():
            return
        setattr(self, attr, (color.blue(), color.green(), color.red()))
        swatch.setStyleSheet(
            f"background-color: rgb({color.red()},{color.green()},"
            f"{color.blue()}); border-radius: 3px; "
            "border: 1px solid rgba(255,255,255,60);")
        self.ann_const_preset_combo.blockSignals(True)
        self.ann_const_preset_combo.setCurrentText("Custom")
        self.ann_const_preset_combo.blockSignals(False)

    def _apply_constellation_preset(self, preset_name):
        """Fired when the "Color preset" dropdown changes. "Custom" is a
        no-op placeholder (reached after a manual color pick, or if a
        saved settings file had no matching preset) — any named preset
        sets both the line and name colors and refreshes both swatches."""
        if preset_name not in CONSTELLATION_COLOR_PRESETS:
            return
        line_color, name_color = CONSTELLATION_COLOR_PRESETS[preset_name]
        self.ann_const_color = line_color
        self.ann_const_name_color = name_color
        for color, swatch in ((line_color, self.ann_const_swatch),
                              (name_color, self.ann_const_name_swatch)):
            b, g_, r = color
            swatch.setStyleSheet(
                f"background-color: rgb({r},{g_},{b}); border-radius: 3px; "
                "border: 1px solid rgba(255,255,255,60);")

    def _show_constellation_selector_dialog(self):
        """'🌌 Select constellations...' — pick which of the 88
        constellations get their stick-figure lines drawn. Unlike
        "Select objects to show...", this doesn't redraw live: line
        positions come from a fixed, always-offline dataset queried fresh
        at run time (not per-run catalogue results cached on this
        object), so there's nothing to redraw from here — it just edits
        `self.ann_const_selected`, used the next time Annotate runs."""
        dlg = QDialog(self)
        dlg.setWindowTitle("Select Constellations")
        dlg.resize(340, 480)
        dv = QVBoxLayout(dlg)
        info = QLabel("Uncheck constellations to leave their lines out "
                      "the next time Annotate runs:")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        dv.addWidget(info)
        lw = QListWidget()
        abbrs = sorted(CONSTELLATION_NAMES,
                      key=lambda a: CONSTELLATION_NAMES[a])
        for abbr in abbrs:
            item = QListWidgetItem(CONSTELLATION_NAMES[abbr])
            item.setData(Qt.ItemDataRole.UserRole, abbr)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(
                Qt.CheckState.Checked if abbr in self.ann_const_selected
                else Qt.CheckState.Unchecked)
            lw.addItem(item)
        dv.addWidget(lw, 1)

        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All")
        select_all_btn.clicked.connect(
            lambda: [lw.item(i).setCheckState(Qt.CheckState.Checked)
                    for i in range(lw.count())])
        deselect_all_btn.clicked.connect(
            lambda: [lw.item(i).setCheckState(Qt.CheckState.Unchecked)
                    for i in range(lw.count())])
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

        self.ann_const_selected = {
            lw.item(i).data(Qt.ItemDataRole.UserRole)
            for i in range(lw.count())
            if lw.item(i).checkState() == Qt.CheckState.Checked}
        n = len(self.ann_const_selected)
        msg = (f"Constellations: {n} of {len(CONSTELLATION_NAMES)} "
              "selected — re-run Annotate to apply.")
        self.status_label.setText(msg)
        self.siril.log(f"Select constellations: {msg}", LogColor.GREEN)

    def _show_object_selector_dialog(self):
        """'☑ Select objects to show...' — pick which labeled objects stay
        visible, redrawing instantly from the cached un-annotated base
        canvas (no re-querying any catalogue). Main-thread only (QDialog) —
        this is a button slot, never called from the worker thread."""
        base = getattr(self, "_ann_base_canvas", None)
        drawn = getattr(self, "_ann_drawn", None)
        if base is None:
            QMessageBox.information(
                self, "No annotated image",
                "Run the Annotate stage at least once first.")
            return
        if not drawn:
            QMessageBox.information(
                self, "Nothing to select",
                "The last Annotate run didn't label any objects.")
            return

        # Snapshot what's on screen now so Cancel can restore it exactly —
        # the checklist below applies live as you toggle it, not just on OK.
        original_drawn = list(drawn)
        original_canvas = self._last_annotated_canvas

        def apply_preview(kept_list):
            """Redraw from the un-annotated base with only `kept_list` and
            push the result straight into the preview + export canvas —
            called on every checkbox toggle, not just when OK is pressed,
            so the preview reflects the checklist in real time."""
            new_canvas = self._render_annotations(base, kept_list)
            self._ann_drawn = kept_list
            self._last_annotated_canvas = new_canvas
            # Single-flip orientation, matching how _exec_stage_ann builds
            # this stage's preview (see the comment there) — flipping again
            # here would mirror the text right back.
            annotated_rgb = cv2.cvtColor(new_canvas, cv2.COLOR_BGR2RGB).astype(
                np.float32) / 255.0
            snap = self.snapshots.get(IDX_ANN, {})
            snap["after"] = make_qimage(annotated_rgb, fits_orientation=False)
            self.snapshots[IDX_ANN] = snap
            self.snapshot_ready.emit(IDX_ANN)

        dlg = QDialog(self)
        dlg.setWindowTitle("Select Objects to Show")
        dlg.resize(380, 440)
        dv = QVBoxLayout(dlg)
        dlg_info = QLabel("Uncheck objects to hide them from the "
                          "annotated image (updates live):")
        dlg_info.setObjectName("SubHeader")
        dlg_info.setWordWrap(True)
        dv.addWidget(dlg_info)
        lw = QListWidget()
        for d in drawn:
            cat_label = CATALOG_LABELS.get(d["kind"], d["kind"].title())
            item = QListWidgetItem(f"{cat_label} — {d['label']}")
            r, gc, b = d["color"][2], d["color"][1], d["color"][0]
            item.setForeground(QColor(r, gc, b))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Checked)
            lw.addItem(item)
        dv.addWidget(lw, 1)

        def on_item_changed(_item):
            kept_now = [d for i, d in enumerate(drawn)
                       if lw.item(i).checkState() == Qt.CheckState.Checked]
            apply_preview(kept_now)

        lw.itemChanged.connect(on_item_changed)

        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All (hide all)")
        select_all_btn.clicked.connect(
            lambda: [lw.item(i).setCheckState(Qt.CheckState.Checked)
                    for i in range(lw.count())])
        deselect_all_btn.clicked.connect(
            lambda: [lw.item(i).setCheckState(Qt.CheckState.Unchecked)
                    for i in range(lw.count())])
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
            # Cancel — put back exactly what was showing before this dialog
            # opened, undoing any live preview changes made while it was up.
            apply_preview(original_drawn)
            self._last_annotated_canvas = original_canvas
            self.status_label.setText("Select objects: canceled, no change.")
            return

        kept = [d for i, d in enumerate(drawn)
               if lw.item(i).checkState() == Qt.CheckState.Checked]
        hidden_count = len(original_drawn) - len(kept)
        msg = (f"Hid {hidden_count} object"
              f"{'s' if hidden_count != 1 else ''} "
              f"({len(kept)} shown). Use \"Save annotated image...\" "
              "to export.")
        self.status_label.setText(msg)
        self.siril.log(f"Select objects: {msg}", LogColor.GREEN)

    def on_save_annotated_image(self):
        """Export the last annotated (or plain, if the overlay is hidden)
        canvas from the Annotate stage as JPEG or PNG, wherever the user
        chooses. Doesn't touch Siril or re-run detection — just re-encodes
        the raster already produced by the last Annotate run."""
        canvas = getattr(self, "_last_annotated_canvas", None)
        if canvas is None:
            QMessageBox.information(
                self, "No annotated image",
                "Run the Annotate stage at least once first.")
            return
        now = datetime.now().strftime("%Y-%m-%d_%H%M")
        default_path = os.path.join(self.cwd, f"annotated_{now}.jpg")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save annotated image", default_path,
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
            self.status_label.setText(f"Annotated image saved: {os.path.basename(path)}")
            self.siril.log(f"Annotated image saved: {path}", LogColor.GREEN)
        except Exception as e:
            QMessageBox.critical(self, "Save failed", str(e))

