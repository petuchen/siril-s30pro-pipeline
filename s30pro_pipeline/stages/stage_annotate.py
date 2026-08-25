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
    QDoubleSpinBox, QFileDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
    QListWidget, QListWidgetItem, QMessageBox, QPlainTextEdit, QPushButton,
    QSpinBox, QVBoxLayout, QWidget,
)
from PyQt6.QtGui import QColor

from astropy.io import fits
from appdirs import user_data_dir

from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_ANN
from s30pro_pipeline.catalog_data import (
    BRIGHT_STARS, OPENNGC_URL, ANNOTATE_MAX_PER_CATALOG,
    CATALOG_COLORS, CATALOG_LABELS, OPENNGC_TYPE_LABELS,
    _ang_sep, _sexa_to_deg, _http_get,
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
                      "actually in the plate-solved field. Three steps "
                      "below: pick which objects to show, pick how they're "
                      "drawn (updates this panel immediately as you "
                      "change it), then run — after running, use the "
                      "action buttons to update, select, remove, or save "
                      "the result without re-querying any catalogue. "
                      "Messier/NGC/IC come from OpenNGC (downloaded once, "
                      "cached on disk); Sharpless and Lynds Dark Nebulae "
                      "come from live VizieR cone searches — real "
                      "structured data, not guessed from Siril's console "
                      "log. Saves an annotated JPG next to your data — "
                      "the FITS image itself is not modified.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        # ============================================== ① Objects to show
        # Everything that decides *which* stars/DSOs/constellations get
        # queried and labeled at all — catalogue toggles, magnitude/online
        # settings, and constellation-line settings. Collapsible (like the
        # Hubble Palette advanced-options pattern) so the common case
        # (defaults are fine, just run it) doesn't force scrolling past a
        # wall of catalogue checkboxes to reach step 2/3 below.
        obj_box, obj_v, _ = self._collapsible_section(
            "① Objects to show", start_expanded=True)

        # 2 columns throughout (swatch+checkbox, or label+control), one
        # item per row — keeps every row readable at the ~1/3-window-width
        # target; several checkbox labels here are long enough that a
        # wider multi-column layout would either overflow or force the
        # (non-wrapping) checkbox text to clip.
        og = QGridLayout()
        og.setHorizontalSpacing(10)
        og.setVerticalSpacing(8)
        og.setColumnStretch(1, 1)
        row = 0

        self.ann_stars_checkbox = QCheckBox("Stars (local catalogue)")
        self.ann_stars_checkbox.setChecked(True)
        self.ann_stars_checkbox.setToolTip(
            "Queries Siril's own local Bright Star Catalogue (3,661 stars, "
            "no internet needed) for stars in the field down to the star "
            "magnitude limit. Falls back to this script's own small "
            "bundled star list if Siril's conesearch command isn't "
            "available (Siril < 1.3).")
        og.addWidget(self._color_swatch(CATALOG_COLORS["star"]), row, 0)
        og.addWidget(self.ann_stars_checkbox, row, 1)
        row += 1
        og.addWidget(QLabel("Star mag limit:"), row, 0)
        self.ann_mag_spin = QDoubleSpinBox()
        self.ann_mag_spin.setRange(0.0, 12.0)
        self.ann_mag_spin.setSingleStep(0.5)
        self.ann_mag_spin.setValue(6.0)
        og.addWidget(self.ann_mag_spin, row, 1)
        row += 1

        self.ann_cat_messier_checkbox = QCheckBox("Messier")
        self.ann_cat_messier_checkbox.setChecked(True)
        self.ann_cat_messier_checkbox.setToolTip(
            "The 110 Messier objects, from OpenNGC (real RA/Dec, no "
            "coordinate guessing). Downloaded once and cached on disk — "
            "later runs use the cached copy, no internet needed.")
        og.addWidget(self._color_swatch(CATALOG_COLORS["messier"]), row, 0)
        og.addWidget(self.ann_cat_messier_checkbox, row, 1)
        row += 1

        self.ann_cat_ngc_checkbox = QCheckBox("NGC (New General Catalogue)")
        self.ann_cat_ngc_checkbox.setChecked(True)
        self.ann_cat_ngc_checkbox.setToolTip(
            "~8,000 NGC objects, from the same cached OpenNGC data as "
            "Messier above.")
        og.addWidget(self._color_swatch(CATALOG_COLORS["ngc"]), row, 0)
        og.addWidget(self.ann_cat_ngc_checkbox, row, 1)
        row += 1

        self.ann_cat_ic_checkbox = QCheckBox("IC (Index Catalogue)")
        self.ann_cat_ic_checkbox.setChecked(True)
        self.ann_cat_ic_checkbox.setToolTip(
            "~5,000 IC objects, from the same cached OpenNGC data as "
            "Messier above.")
        og.addWidget(self._color_swatch(CATALOG_COLORS["ic"]), row, 0)
        og.addWidget(self.ann_cat_ic_checkbox, row, 1)
        row += 1

        self.ann_cat_sh2_checkbox = QCheckBox("Sharpless (Sh2)")
        self.ann_cat_sh2_checkbox.setToolTip(
            "Sharpless catalogue of HII regions/emission nebulae, queried "
            "live from VizieR (catalogue VII/20) for the current field. "
            "Needs internet on every run — off by default for that "
            "reason.")
        og.addWidget(self._color_swatch(CATALOG_COLORS["sh2"]), row, 0)
        og.addWidget(self.ann_cat_sh2_checkbox, row, 1)
        row += 1

        self.ann_cat_ldn_checkbox = QCheckBox("Lynds Dark Nebulae (LdN)")
        self.ann_cat_ldn_checkbox.setToolTip(
            "Lynds Catalogue of Dark Nebulae, queried live from VizieR "
            "(catalogue VII/7A) for the current field. Needs internet on "
            "every run — off by default for that reason.")
        og.addWidget(self._color_swatch(CATALOG_COLORS["ldn"]), row, 0)
        og.addWidget(self.ann_cat_ldn_checkbox, row, 1)
        row += 1

        self.ann_online_checkbox = QCheckBox("All stars < mag limit (online BSC)")
        self.ann_online_checkbox.setToolTip(
            "Siril's local star catalogue covers the field well already; "
            "this additionally runs Siril's own online conesearch against "
            "the VizieR Bright Star Catalogue for every star below the "
            "star magnitude limit, for denser coverage. Needs internet.")
        og.addWidget(self.ann_online_checkbox, row, 0, 1, 2)
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
        og.addWidget(self.ann_const_checkbox, row, 0, 1, 2)
        row += 1

        self.ann_const_names_checkbox = QCheckBox("Show constellation names")
        self.ann_const_names_checkbox.setChecked(True)
        self.ann_const_names_checkbox.setToolTip(
            "Labels each drawn constellation with its name, centered over "
            "whichever part of its stick figure is inside the frame.")
        og.addWidget(self.ann_const_names_checkbox, row, 0, 1, 2)
        row += 1

        og.addWidget(QLabel("Line width:"), row, 0)
        self.ann_const_width_spin = QSpinBox()
        self.ann_const_width_spin.setRange(1, 8)
        self.ann_const_width_spin.setValue(1)
        self.ann_const_width_spin.setToolTip(
            "Thickness of the constellation lines, in pixels (scaled up "
            "automatically for high-resolution stacks).")
        og.addWidget(self.ann_const_width_spin, row, 1)
        row += 1

        og.addWidget(QLabel("Gap (px):"), row, 0)
        self.ann_const_gap_spin = QSpinBox()
        self.ann_const_gap_spin.setRange(0, 60)
        self.ann_const_gap_spin.setValue(8)
        self.ann_const_gap_spin.setToolTip(
            "Shortens each line segment by this many pixels from both "
            "ends, so lines don't touch the stars directly — 0 draws "
            "star-to-star with no gap.")
        og.addWidget(self.ann_const_gap_spin, row, 1)
        row += 1

        og.addWidget(QLabel("Color preset:"), row, 0)
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
        og.addWidget(self.ann_const_preset_combo, row, 1)
        row += 1

        self.ann_const_swatch = self._color_swatch(self.ann_const_color)
        self.ann_const_color_btn = QPushButton("Line color...")
        self.ann_const_color_btn.setToolTip(
            "Pick a custom color for the constellation lines themselves.")
        self.ann_const_color_btn.clicked.connect(
            lambda: self._pick_constellation_color("line"))
        og.addWidget(self.ann_const_swatch, row, 0)
        og.addWidget(self.ann_const_color_btn, row, 1)
        row += 1

        self.ann_const_name_swatch = self._color_swatch(
            self.ann_const_name_color)
        self.ann_const_name_color_btn = QPushButton("Name color...")
        self.ann_const_name_color_btn.setToolTip(
            "Pick a custom color for the constellation name labels — "
            "independent of the line color above.")
        self.ann_const_name_color_btn.clicked.connect(
            lambda: self._pick_constellation_color("name"))
        og.addWidget(self.ann_const_name_swatch, row, 0)
        og.addWidget(self.ann_const_name_color_btn, row, 1)
        row += 1
        obj_v.addLayout(og)

        self.ann_const_select_btn = QPushButton("🌌  Select constellations...")
        self.ann_const_select_btn.setToolTip(
            "Choose which of the 88 constellations get stick-figure lines "
            "drawn, if \"Constellation lines\" above is checked. Applies "
            "the next time the Annotate stage runs.")
        self.ann_const_select_btn.clicked.connect(
            self._show_constellation_selector_dialog)
        obj_v.addWidget(self.ann_const_select_btn)
        v.addWidget(obj_box)

        # ============================================ ② Annotation style
        # How the objects picked in step ① are actually drawn: marker
        # shape/color/thickness, label size and detail lines. The style
        # sub-panels (Circle/Open Cross/Label detail) show or hide
        # instantly as you change the controls above them — no need to
        # re-run the stage just to see which options apply to your choice.
        style_box, style_v, _ = self._collapsible_section(
            "② Annotation style", start_expanded=True)

        sg = QGridLayout()
        sg.setHorizontalSpacing(10)
        sg.setVerticalSpacing(8)
        sg.setColumnStretch(1, 1)

        sg.addWidget(QLabel("Label size:"), 0, 0)
        self.ann_size_spin = QDoubleSpinBox()
        self.ann_size_spin.setRange(0.5, 3.0)
        self.ann_size_spin.setSingleStep(0.1)
        self.ann_size_spin.setValue(1.0)
        sg.addWidget(self.ann_size_spin, 0, 1)

        sg.addWidget(QLabel("Marker style:"), 1, 0)
        self.ann_marker_style_combo = QComboBox()
        self.ann_marker_style_combo.addItems(
            ["Circle", "Open Cross", "Circle + Open Cross"])
        self.ann_marker_style_combo.setToolTip(
            "How each star/DSO marker is drawn. \"Open Cross\" is a "
            "reticle-style cross with a gap in the middle so it doesn't "
            "cover the object itself — its gap and arm length scale with "
            "the marker's size and are adjustable below. This panel "
            "updates immediately as you change the style.")
        sg.addWidget(self.ann_marker_style_combo, 1, 1)

        sg.addWidget(QLabel("Label distance (× radius):"), 2, 0)
        self.ann_cross_label_dist_spin = QDoubleSpinBox()
        self.ann_cross_label_dist_spin.setRange(-2.0, 5.0)
        self.ann_cross_label_dist_spin.setSingleStep(0.1)
        self.ann_cross_label_dist_spin.setValue(0.1)
        self.ann_cross_label_dist_spin.setToolTip(
            "Extra breathing room between the label text and the marker "
            "center, as a multiple of the marker's own radius — added on "
            "top of every label's normal placement distance (which, for "
            "Open Cross style, already includes the arm length below, "
            "plus a small fixed margin so text never touches the "
            "marker). Positive values push the label further out — "
            "useful to clear a stretched, multi-line label so it "
            "doesn't crowd Open Cross's arms; negative values pull it "
            "in closer than the normal default, down to a minimum where "
            "it would start overlapping the marker. Applies to every "
            "marker style, not just Open Cross.")
        sg.addWidget(self.ann_cross_label_dist_spin, 2, 1)
        style_v.addLayout(sg)

        # -------------------------------------------------- marker style groups
        self.ann_circle_style_box = QGroupBox("Circle style")
        circ_g = QGridLayout(self.ann_circle_style_box)
        circ_g.setHorizontalSpacing(10)
        circ_g.setVerticalSpacing(8)
        circ_g.setColumnStretch(1, 1)

        self.ann_circle_auto_th_checkbox = QCheckBox("Auto thickness")
        self.ann_circle_auto_th_checkbox.setChecked(True)
        self.ann_circle_auto_th_checkbox.setToolTip(
            "Scales the circle's stroke width with the image resolution "
            "and label size, same as before this option existed. Uncheck "
            "to set a fixed pixel thickness instead.")
        circ_g.addWidget(self.ann_circle_auto_th_checkbox, 0, 0, 1, 2)
        circ_g.addWidget(QLabel("Thickness (px):"), 1, 0)
        self.ann_circle_th_spin = QSpinBox()
        self.ann_circle_th_spin.setRange(1, 12)
        self.ann_circle_th_spin.setValue(2)
        self.ann_circle_th_spin.setEnabled(False)
        circ_g.addWidget(self.ann_circle_th_spin, 1, 1)

        self.ann_circle_custom_color_checkbox = QCheckBox(
            "Custom color (override per-catalogue colors)")
        self.ann_circle_custom_color_checkbox.setToolTip(
            "Off (default): each catalogue keeps its own color, matching "
            "the swatches above. On: every circle uses the single color "
            "picked below instead — labels keep their per-catalogue color "
            "either way.")
        circ_g.addWidget(self.ann_circle_custom_color_checkbox, 2, 0, 1, 2)
        self.ann_circle_color = (255, 255, 255)
        self.ann_circle_swatch = self._color_swatch(self.ann_circle_color)
        self.ann_circle_color_btn = QPushButton("Circle color...")
        self.ann_circle_color_btn.setEnabled(False)
        self.ann_circle_color_btn.clicked.connect(
            lambda: self._pick_marker_color("circle"))
        circ_g.addWidget(self.ann_circle_swatch, 3, 0)
        circ_g.addWidget(self.ann_circle_color_btn, 3, 1)
        style_v.addWidget(self.ann_circle_style_box)

        self.ann_cross_style_box = QGroupBox("Open Cross style")
        cross_g = QGridLayout(self.ann_cross_style_box)
        cross_g.setHorizontalSpacing(10)
        cross_g.setVerticalSpacing(8)
        cross_g.setColumnStretch(1, 1)

        self.ann_cross_auto_th_checkbox = QCheckBox("Auto thickness")
        self.ann_cross_auto_th_checkbox.setChecked(True)
        self.ann_cross_auto_th_checkbox.setToolTip(
            self.ann_circle_auto_th_checkbox.toolTip().replace(
                "circle's", "cross's"))
        cross_g.addWidget(self.ann_cross_auto_th_checkbox, 0, 0, 1, 2)
        cross_g.addWidget(QLabel("Thickness (px):"), 1, 0)
        self.ann_cross_th_spin = QSpinBox()
        self.ann_cross_th_spin.setRange(1, 12)
        self.ann_cross_th_spin.setValue(2)
        self.ann_cross_th_spin.setEnabled(False)
        cross_g.addWidget(self.ann_cross_th_spin, 1, 1)

        self.ann_cross_custom_color_checkbox = QCheckBox(
            "Custom color (override per-catalogue colors)")
        self.ann_cross_custom_color_checkbox.setToolTip(
            "Same idea as the circle's custom color above, independent of "
            "it — you can have a custom cross color with per-catalogue "
            "circle colors, or vice versa, or both/neither.")
        cross_g.addWidget(self.ann_cross_custom_color_checkbox, 2, 0, 1, 2)
        self.ann_cross_color = (255, 255, 255)
        self.ann_cross_swatch = self._color_swatch(self.ann_cross_color)
        self.ann_cross_color_btn = QPushButton("Cross color...")
        self.ann_cross_color_btn.setEnabled(False)
        self.ann_cross_color_btn.clicked.connect(
            lambda: self._pick_marker_color("cross"))
        cross_g.addWidget(self.ann_cross_swatch, 3, 0)
        cross_g.addWidget(self.ann_cross_color_btn, 3, 1)

        cross_g.addWidget(QLabel("Gap (× radius):"), 4, 0)
        self.ann_cross_gap_spin = QDoubleSpinBox()
        self.ann_cross_gap_spin.setRange(0.0, 3.0)
        self.ann_cross_gap_spin.setSingleStep(0.1)
        self.ann_cross_gap_spin.setValue(0.5)
        self.ann_cross_gap_spin.setToolTip(
            "How far each arm starts from the object's center, as a "
            "multiple of the marker's own radius — so it scales with the "
            "object's apparent size instead of being a fixed pixel gap.")
        cross_g.addWidget(self.ann_cross_gap_spin, 4, 1)
        cross_g.addWidget(QLabel("Arm length (× radius):"), 5, 0)
        self.ann_cross_arm_spin = QDoubleSpinBox()
        self.ann_cross_arm_spin.setRange(0.1, 3.0)
        self.ann_cross_arm_spin.setSingleStep(0.1)
        self.ann_cross_arm_spin.setValue(0.7)
        self.ann_cross_arm_spin.setToolTip(
            "Length of each of the 4 arm strokes, as a multiple of the "
            "marker's radius — also scales with object size.")
        cross_g.addWidget(self.ann_cross_arm_spin, 5, 1)

        cross_g.addWidget(QLabel("Label position:"), 6, 0)
        self.ann_cross_label_pos_combo = QComboBox()
        self.ann_cross_label_pos_combo.addItems(
            ["Auto (avoid overlap)", "NE", "NW", "SE", "SW"])
        self.ann_cross_label_pos_combo.setToolTip(
            "The open cross leaves its 4 diagonal corners clear of arms — "
            "pick one to always place the name there, or leave on Auto to "
            "let the same overlap-avoiding placement used for Circle "
            "style pick the best free spot (preferring this corner when "
            "you’ve chosen one)."
        )
        cross_g.addWidget(self.ann_cross_label_pos_combo, 6, 1)
        style_v.addWidget(self.ann_cross_style_box)

        def sync_marker_style_visibility(_text=None):
            style = self.ann_marker_style_combo.currentText()
            self.ann_circle_style_box.setVisible(
                style in ("Circle", "Circle + Open Cross"))
            self.ann_cross_style_box.setVisible(
                style in ("Open Cross", "Circle + Open Cross"))

        self.ann_marker_style_combo.currentTextChanged.connect(
            sync_marker_style_visibility)
        self.ann_circle_auto_th_checkbox.toggled.connect(
            lambda checked: self.ann_circle_th_spin.setEnabled(not checked))
        self.ann_cross_auto_th_checkbox.toggled.connect(
            lambda checked: self.ann_cross_th_spin.setEnabled(not checked))
        self.ann_circle_custom_color_checkbox.toggled.connect(
            self.ann_circle_color_btn.setEnabled)
        self.ann_cross_custom_color_checkbox.toggled.connect(
            self.ann_cross_color_btn.setEnabled)
        sync_marker_style_visibility()

        # -------------------------------------------------- label detail
        self.ann_label_detail_box = QGroupBox("Label detail")
        ld_v = QVBoxLayout(self.ann_label_detail_box)
        ld_v.setSpacing(8)
        ld_info = QLabel(
            "Adds extra lines under each object's name, drawn stacked in "
            "the same direction as the name itself, aligned to whichever "
            "side of the marker the label sits on. The built-in fields "
            "below only appear for Messier/NGC/IC objects (OpenNGC "
            "carries this data; stars/Sharpless/LdN don't) and only when "
            "that particular object actually has the field. Open Cross "
            "style's arm on the label's side (up or down) stretches "
            "automatically to reach a taller, multi-line label.")
        ld_info.setObjectName("SubHeader")
        ld_info.setWordWrap(True)
        ld_v.addWidget(ld_info)

        ld_g = QGridLayout()
        ld_g.setHorizontalSpacing(10)
        ld_g.setVerticalSpacing(4)
        self.ann_detail_type_checkbox = QCheckBox("Object type")
        self.ann_detail_type_checkbox.setToolTip(
            "e.g. \"Galaxy\", \"Open cluster\", \"Planetary nebula\".")
        ld_g.addWidget(self.ann_detail_type_checkbox, 0, 0)
        self.ann_detail_mag_checkbox = QCheckBox("Magnitude")
        self.ann_detail_mag_checkbox.setToolTip(
            "OpenNGC's V-Mag, falling back to B-Mag when V-Mag is "
            "missing.")
        ld_g.addWidget(self.ann_detail_mag_checkbox, 0, 1)
        self.ann_detail_const_checkbox = QCheckBox("Constellation")
        ld_g.addWidget(self.ann_detail_const_checkbox, 1, 0)
        self.ann_detail_size_checkbox = QCheckBox("Apparent size")
        self.ann_detail_size_checkbox.setToolTip(
            "OpenNGC's MajAx (apparent major axis), in arcminutes — the "
            "same value already used to size the marker itself.")
        ld_g.addWidget(self.ann_detail_size_checkbox, 1, 1)
        ld_v.addLayout(ld_g)

        ld_custom_label = QLabel("Custom lines (added to every label, in "
                                 "this order — type one label line per "
                                 "row of text):")
        ld_v.addWidget(ld_custom_label)
        self.ann_custom_lines_edit = QPlainTextEdit()
        self.ann_custom_lines_edit.setMaximumHeight(90)
        self.ann_custom_lines_edit.setPlaceholderText(
            "One label line per row, e.g.:\nSession 1\nBortle 4")
        self.ann_custom_lines_edit.setToolTip(
            "Freeform text appended under every object's name (and any "
            "built-in fields above) — the same text for every object, "
            "e.g. a session date or your own note. Each row of text you "
            "type is its own label line; blank rows are skipped.")
        ld_v.addWidget(self.ann_custom_lines_edit)
        style_v.addWidget(self.ann_label_detail_box)

        self.ann_show_overlay_checkbox = QCheckBox("Show annotation overlay")
        self.ann_show_overlay_checkbox.setChecked(True)
        self.ann_show_overlay_checkbox.setToolTip(
            "Uncheck to hide the markers/labels — running the stage will then "
            "just show the plain image (useful if you want to keep the stage "
            "in the pipeline but not clutter the preview/export with labels).")
        style_v.addWidget(self.ann_show_overlay_checkbox)
        v.addWidget(style_box)

        # ============================================ ③ Run / update / save
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
        self.ann_update_preview_btn = QPushButton("🔄  Update preview")
        self.ann_update_preview_btn.setToolTip(
            "Re-renders every currently shown object using the "
            "Annotation style panel's *current* settings — marker style, "
            "colors, thickness, cross geometry, label detail lines — "
            "without re-querying any catalogue or re-running plate "
            "solving, so it's much faster than Run when you're just "
            "iterating on how things look. Resets every object to the "
            "panel defaults, so any per-object 🎨 overrides are "
            "discarded — re-open \"Select objects...\" afterward to "
            "reapply them if you still want them. Doesn't affect "
            "constellation lines (uncheck \"Constellation lines\" and "
            "re-run to remove those).")
        self.ann_update_preview_btn.clicked.connect(
            self._update_annotation_preview)
        save_row2.addWidget(self.ann_update_preview_btn)
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

        self.ann_pick_btn = QPushButton("🖱  Pick object on image...")
        self.ann_pick_btn.setCheckable(True)
        self.ann_pick_btn.setToolTip(
            "Click this, then click anywhere on the preview image to add "
            "a custom object right there — its RA/Dec (from the same "
            "plate-solve WCS the stage already used) becomes its default "
            "name, styled with the Annotation style panel's current "
            "settings. Stays armed for multiple picks in a row; click "
            "this button again or press Esc to stop. Rename it, change "
            "its style, or remove it afterward via \"Select objects...\" "
            "🎨 editor, same as any catalogue object.")
        self.ann_pick_btn.toggled.connect(self._toggle_ann_pick_mode)
        v.addWidget(self.ann_pick_btn)
        self.ann_pick_hint = QLabel("")
        self.ann_pick_hint.setObjectName("SubHeader")
        self.ann_pick_hint.setWordWrap(True)
        v.addWidget(self.ann_pick_hint)
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
        (label, ra, dec, kind, size_arcmin, extra) with kind in
        {"messier","ngc","ic"}; size_arcmin is OpenNGC's MajAx (apparent
        major axis, arcminutes) as a float, or None if the row doesn't
        have one — used to size each object's marker to its real apparent
        footprint instead of a fixed generic radius. `extra` is a dict of
        whatever optional label-detail fields this row actually has
        (missing/blank fields are simply absent, not None-valued) —
        possible keys: "type" (friendly OpenNGC object type), "mag"
        (V-Mag, falling back to B-Mag, as a float), "const" (full
        constellation name from OpenNGC's 3-letter abbreviation), "size"
        (same value as size_arcmin, exposed here too so a caller building
        label lines doesn't need the separate positional field)."""
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

            extra = {}
            type_raw = (row.get("Type") or "").strip()
            if type_raw:
                extra["type"] = OPENNGC_TYPE_LABELS.get(type_raw, type_raw)
            mag_raw = row.get("V-Mag") or row.get("B-Mag")
            try:
                mag = float(mag_raw) if mag_raw not in (None, "") else None
            except (TypeError, ValueError):
                mag = None
            if mag is not None:
                extra["mag"] = mag
            const_raw = (row.get("Const") or "").strip()
            if const_raw:
                extra["const"] = CONSTELLATION_NAMES.get(
                    const_raw.title(), const_raw)
            if size_arcmin is not None:
                extra["size"] = size_arcmin

            out.append((label, ora, odec, kind, size_arcmin, extra))
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

    def _build_default_label_lines(self, label, extra):
        """Object name + whichever OpenNGC-sourced detail lines the Label
        detail panel currently has enabled + the panel's custom lines, in
        that order — the exact label content a fresh Annotate run would
        produce for this object. Shared by _exec_stage_ann's per-object
        loop and _default_style_for_object's "reset to panel default"
        (used by the per-object style editor), so both can never
        disagree about what "default" means. `extra` is the OpenNGC
        type/magnitude/constellation/size dict from _filter_openngc_rows
        (empty {} for stars/Sharpless/LdN, which OpenNGC doesn't cover)."""
        lines = [label]
        if self.ann_detail_type_checkbox.isChecked() and extra.get("type"):
            lines.append(extra["type"])
        if (self.ann_detail_mag_checkbox.isChecked()
                and extra.get("mag") is not None):
            lines.append(f"mag {extra['mag']:.1f}")
        if self.ann_detail_const_checkbox.isChecked() and extra.get("const"):
            lines.append(extra["const"])
        if self.ann_detail_size_checkbox.isChecked() and extra.get("size"):
            lines.append(f"{extra['size']:.1f}'")
        lines.extend(
            row.strip() for row in
            self.ann_custom_lines_edit.toPlainText().splitlines()
            if row.strip())
        return lines

    def _default_style_for_object(self, d):
        """Recompute one object's marker/label style exactly as
        _exec_stage_ann would today, from the Annotation style panel's
        *current* settings — used by the per-object style editor's
        "Reset to panel default" button so a per-object override can be
        discarded without re-running the whole stage. Needs `d["r"]`
        (marker radius) and `d["color"]` (catalogue color) already set;
        `d.get("extra", {})` drives the label-detail lines the same way
        _exec_stage_ann's own loop does."""
        marker_style_text = self.ann_marker_style_combo.currentText()
        marker_style = {
            "Circle": "circle", "Open Cross": "cross",
            "Circle + Open Cross": "both",
        }[marker_style_text]
        th = d.get("th", 2)
        circle_th = (th if self.ann_circle_auto_th_checkbox.isChecked()
                     else self.ann_circle_th_spin.value())
        circle_color_override = (
            self.ann_circle_color
            if self.ann_circle_custom_color_checkbox.isChecked() else None)
        cross_th = (th if self.ann_cross_auto_th_checkbox.isChecked()
                   else self.ann_cross_th_spin.value())
        cross_color_override = (
            self.ann_cross_color
            if self.ann_cross_custom_color_checkbox.isChecked() else None)
        label_pos_text = self.ann_cross_label_pos_combo.currentText()
        label_pref = {
            "NE": (1, -1), "NW": (-1, -1),
            "SE": (1, 1), "SW": (-1, 1),
        }.get(label_pos_text)
        if marker_style == "circle":
            label_pref = None
        r = d.get("r", 1) or 1
        return {
            "style": marker_style,
            "circle_th": circle_th,
            "circle_color": circle_color_override or d["color"],
            "cross_th": cross_th,
            "cross_color": cross_color_override or d["color"],
            "cross_gap": r * self.ann_cross_gap_spin.value(),
            "cross_arm": r * self.ann_cross_arm_spin.value(),
            "label_pref": label_pref,
            # Applies to every marker style, not just Open Cross — it's
            # a general "how far the label sits from the marker" offset
            # (see _layout_annotation_labels), even though the panel
            # control lives in the "Marker style" row above the style-
            # specific boxes since it isn't itself style-specific.
            "label_extra": r * self.ann_cross_label_dist_spin.value(),
            "label_lines": self._build_default_label_lines(
                d["label"], d.get("extra", {})),
            # No panel-level text color control exists (labels have always
            # used the catalogue color) — "default" simply means no
            # per-object override, same as before this option existed.
            "text_color": d["color"],
        }

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

        # Cached for "🖱 Pick object on image..." (_on_ann_point_picked),
        # which needs to convert a later click's pixel position back to
        # RA/Dec without re-reading the FITS header or re-running the
        # whole stage — this WCS/W/H trio is otherwise purely local to
        # this method.
        self._ann_wcs = wcs
        self._ann_img_w, self._ann_img_h = W, H

        show_overlay = self.ann_show_overlay_checkbox.isChecked()
        drawn = 0
        out_path = None

        if show_overlay:
            mag_limit = self.ann_mag_spin.value()
            targets = []  # (label, ra, dec, kind, size_arcmin, extra)
            seen = set()  # (round(ra,3), round(dec,3)) — de-dupe across queries

            def add_targets(items, kind):
                # Each item is (name, ra, dec) for stars/no-size sources,
                # (name, ra, dec, size_arcmin) for catalogues that carry an
                # apparent-size field — size_arcmin drives the marker radius
                # in the drawing pass below, defaulting to None (fixed
                # radius) when a source doesn't provide one — or (name, ra,
                # dec, size_arcmin, extra) for OpenNGC, whose `extra` dict
                # (type/magnitude/constellation) feeds the optional
                # label-detail lines below. Sources without a 5th element
                # simply get {} — no label-detail lines are drawn for
                # anything Annotate can't source that data for.
                for item in items:
                    name, ra, dec = item[0], item[1], item[2]
                    size = item[3] if len(item) > 3 else None
                    extra = item[4] if len(item) > 4 else {}
                    key = (round(ra, 3), round(dec, 3))
                    if key in seen:
                        continue
                    seen.add(key)
                    targets.append((name, ra, dec, kind, size, extra))

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
                    for name, ra_, dec_, kind, size_, extra_ in found:
                        by_kind[kind].append((name, ra_, dec_, size_, extra_))
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

                # Marker style — independent of the text-label styling
                # above (fs/th/color there keep driving the name text
                # regardless of marker style, so labels stay readable and
                # match their catalogue color either way). "circle" is the
                # only style that existed before this option was added, so
                # it reproduces the exact old appearance (auto thickness,
                # per-catalogue color, no label_pref) when left on its
                # default.
                marker_style_text = self.ann_marker_style_combo.currentText()
                marker_style = {
                    "Circle": "circle", "Open Cross": "cross",
                    "Circle + Open Cross": "both",
                }[marker_style_text]
                circle_th = (th if self.ann_circle_auto_th_checkbox.isChecked()
                             else self.ann_circle_th_spin.value())
                circle_color_override = (
                    self.ann_circle_color
                    if self.ann_circle_custom_color_checkbox.isChecked()
                    else None)
                cross_th = (th if self.ann_cross_auto_th_checkbox.isChecked()
                           else self.ann_cross_th_spin.value())
                cross_color_override = (
                    self.ann_cross_color
                    if self.ann_cross_custom_color_checkbox.isChecked()
                    else None)
                cross_gap_mult = self.ann_cross_gap_spin.value()
                cross_arm_mult = self.ann_cross_arm_spin.value()
                cross_label_dist_mult = self.ann_cross_label_dist_spin.value()
                # NE/NW/SE/SW map onto the same (dx,dy) convention already
                # used by _layout_annotation_labels' candidate ring: dx>0
                # is toward larger x (right/"E"), dy<0 is toward smaller y
                # (up/"N") in the already display-oriented canvas.
                label_pos_text = self.ann_cross_label_pos_combo.currentText()
                label_pref = {
                    "NE": (1, -1), "NW": (-1, -1),
                    "SE": (1, 1), "SW": (-1, 1),
                }.get(label_pos_text)
                if marker_style == "circle":
                    label_pref = None  # unchanged from pre-existing behavior

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

                # Optional label-detail lines (OpenNGC-sourced Type/
                # Magnitude/Constellation/Size, plus any freeform custom
                # lines from the panel below) drawn under the object name
                # — computed once here rather than per-object, since which
                # fields are enabled and the custom line list are both
                # global panel settings, not per-object.
                # Build the list of *drawable* objects (label + pixel
                # position + style) instead of drawing directly — this is
                # kept around as self._ann_drawn so "Select objects to
                # show..." can redraw a subset from the un-annotated base
                # canvas without re-querying any catalogue.
                drawable = []
                for i, (label, ra, dec, kind, size_arcmin, extra) in enumerate(targets):
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
                        "extra": extra,
                        "label_lines": self._build_default_label_lines(
                            label, extra),
                        "style": marker_style,
                        "circle_th": circle_th,
                        "circle_color": circle_color_override or color,
                        "cross_th": cross_th,
                        "cross_color": cross_color_override or color,
                        "cross_gap": r * cross_gap_mult,
                        "cross_arm": r * cross_arm_mult,
                        "label_pref": label_pref,
                        # Applies to every marker style — see the
                        # matching comment in _default_style_for_object.
                        "label_extra": r * cross_label_dist_mult,
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
        "ty" (the cv2.putText baseline-left anchor point of the LAST —
        bottommost — line; see _render_annotations for why that's the
        natural anchor for a multi-line block), "label_dx"/"label_dy"
        (the chosen direction, reused by _render_annotations for
        per-line alignment and, for Open Cross style, how far to
        stretch the matching arm), and returns `items`. Greedy: bigger
        markers (which are usually the more important/prominent
        objects) get first pick of their preferred slot; each object
        tries a ring of candidate positions around its marker and takes
        the first one that's fully on-canvas and collision-free, falling
        back to the least-bad (fewest/smallest overlaps, still on-canvas
        if at all possible) candidate, then a hard clamp to the canvas
        edge as a last resort so text is never cut off even in a very
        crowded corner."""

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
            lines = d.get("label_lines") or [d["label"]]
            tw, th_box, _line_heights, _line_gap = (
                AnnotateMixin._label_block_metrics(
                    lines, d["fs"], d["th"]))
            r, cx, cy, pad = d["r"], d["x"], d["y"], 4

            # Candidate anchor points on rings around the marker: 8
            # compass directions at an inner ring, then the same 8 a bit
            # farther out for crowded spots — right/upper-right first
            # since that's the conventional, least-surprising placement.
            dirs = [(1, 0), (1, -1), (1, 1), (0, -1), (0, 1),
                    (-1, 0), (-1, -1), (-1, 1)]
            # Open Cross style lets the caller prefer one of the 4 corners
            # (the diagonals its arms leave clear) — try that one first on
            # both rings, still falling back through the rest of the ring
            # for overlap/on-canvas avoidance if the preferred corner
            # doesn't work out. None (Circle style, or "Auto" chosen for
            # Open Cross) leaves the original order untouched.
            pref = d.get("label_pref")
            if pref in dirs:
                dirs = [pref] + [dd for dd in dirs if dd != pref]
            label_extra = d.get("label_extra", 0)
            candidates = []
            for ring in (1.0, 2.2):
                # Floored so a strongly negative "Label distance" (or a
                # tiny marker radius) can pull the label in close without
                # ever collapsing onto/through the marker center — 2px is
                # small enough to feel like "as close as possible" while
                # still leaving the label fully outside the marker.
                dist = max(2.0, r + pad + ring * 6 + label_extra)
                for dx, dy in dirs:
                    tx = (cx + dist if dx > 0 else
                          cx - dist - tw if dx < 0 else cx - tw / 2.0)
                    ty = (cy - dist if dy < 0 else
                          cy + dist + th_box if dy > 0 else
                          cy + th_box / 2.0)
                    candidates.append((tx, ty, dx, dy))

            best = None
            for tx, ty, dx, dy in candidates:
                tx_i, ty_i = int(round(tx)), int(round(ty))
                box = box_for(tx_i, ty_i, tw, th_box)
                in_bounds = (box[0] >= 0 and box[1] >= 0 and
                            box[2] <= W and box[3] <= H)
                overlap = sum(overlap_area(box, pb) for pb in placed_boxes)
                score = (0 if in_bounds else 1, overlap)
                if best is None or score < best[0]:
                    best = (score, tx_i, ty_i, box, dx, dy)
                if score == (0, 0):
                    break

            _, tx_i, ty_i, box, best_dx, best_dy = best
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
            d["label_dx"], d["label_dy"] = best_dx, best_dy
            placed_boxes.append(box)

        return items

    @staticmethod
    def _label_block_metrics(lines, fs, th):
        """Pixel metrics for a stack of label text lines at font scale
        `fs`/stroke thickness `th`: (block_w, block_h, line_heights,
        line_gap). block_w/block_h are the full multi-line block's
        bounding box (single-line labels — the common case, an object
        with no label-detail lines enabled — collapse to exactly the
        same numbers this used to compute inline, so existing Circle
        placements are unaffected). Shared by _layout_annotation_labels
        (to reserve the right amount of space) and _render_annotations
        (to actually draw each line at the right y) so the two can never
        disagree about how tall a block is."""
        line_gap = max(2, int(round(fs * 6)))
        line_heights = []
        block_w = 0
        for line in lines:
            (w, h), baseline = cv2.getTextSize(
                line, cv2.FONT_HERSHEY_SIMPLEX, fs, th)
            w += 2
            h += baseline
            block_w = max(block_w, w)
            line_heights.append(h)
        block_h = sum(line_heights) + line_gap * (len(lines) - 1)
        return block_w, block_h, line_heights, line_gap

    @staticmethod
    def _render_annotations(base_canvas, drawn):
        """Draw a list of annotation dicts (from _exec_stage_ann's
        `drawable`, or a filtered subset of self._ann_drawn) onto a copy of
        `base_canvas` (BGR uint8, un-annotated). Shared by the initial
        Annotate run and by "Select objects to show..." so both produce
        pixel-identical results for the objects they keep."""
        canvas = base_canvas.copy()
        for d in drawn:
            # "style" defaults to "circle" so annotation dicts cached by an
            # older version of this stage (before marker styles existed —
            # e.g. from a settings JSON's cached preview state) still draw
            # exactly as they always did.
            style = d.get("style", "circle")
            x, y = d["x"], d["y"]
            if style in ("circle", "both"):
                cv2.circle(canvas, (x, y), d["r"],
                          d.get("circle_color", d["color"]),
                          d.get("circle_th", d["th"]), cv2.LINE_AA)
            lines = d.get("label_lines") or [d["label"]]
            _blk_w, _blk_h, line_heights, line_gap = (
                AnnotateMixin._label_block_metrics(
                    lines, d["fs"], d["th"]))
            label_dy = d.get("label_dy", 0)
            if style in ("cross", "both"):
                cross_color = d.get("cross_color", d["color"])
                cross_th = d.get("cross_th", d["th"])
                gap = d.get("cross_gap", d["r"] * 0.5)
                arm = d.get("cross_arm", d["r"] * 0.7)
                # Open cross: 4 short strokes (N/S/E/W) that start `gap`
                # pixels from center and extend `arm` pixels further out —
                # never meeting in the middle, so the object itself stays
                # unobscured. Both distances were computed from the
                # marker's own radius (r * multiplier) back in
                # _exec_stage_ann, so they scale with the object's
                # apparent size automatically. When the label sits on
                # this arm's side and has more than one line (an
                # OpenNGC-detail or custom-line block), the arm's `arm`
                # length is stretched by the extra lines' stacked height
                # so it visually "reaches" toward the taller label
                # instead of stopping short of it.
                extra_reach = (0 if len(lines) <= 1 else
                              sum(line_heights[1:]) +
                              line_gap * (len(lines) - 1))
                for dx, dy in ((0, -1), (0, 1), (1, 0), (-1, 0)):
                    this_arm = arm
                    if extra_reach and dx == 0 and (
                            (dy < 0 and label_dy < 0) or
                            (dy > 0 and label_dy > 0)):
                        this_arm = arm + extra_reach
                    p1 = (int(round(x + dx * gap)), int(round(y + dy * gap)))
                    p2 = (int(round(x + dx * (gap + this_arm))),
                         int(round(y + dy * (gap + this_arm))))
                    cv2.line(canvas, p1, p2, cross_color, cross_th,
                            cv2.LINE_AA)
            # Multi-line label block: `ty` (from _layout_annotation_labels)
            # is the cv2.putText baseline of the LAST — bottommost — line,
            # matching the single-line convention exactly when there's
            # only one line. Earlier lines (object name first, then any
            # enabled detail/custom lines) stack upward from there. Each
            # line is horizontally aligned to match which side of the
            # marker the whole block was placed on (`label_dx`): right-
            # align (grow leftward from tx+block width) when the block
            # sits to the west of the marker, left-align (the original,
            # simple behavior) everywhere else — so the label always
            # reads as "attached" to its marker rather than drifting away
            # from it as line lengths vary.
            label_dx = d.get("label_dx", 1)
            tx, ty = d["tx"], d["ty"]
            n = len(lines)
            for i, line in enumerate(lines):
                # Lines after the first stack upward from the anchor;
                # i counts from the top so the last line (i == n-1) lands
                # exactly on ty.
                y_off = sum(line_heights[i + 1:n]) + line_gap * (n - 1 - i)
                line_ty = ty - y_off
                if label_dx < 0:
                    # Block sits west of the marker: `tx` is already the
                    # block's left edge (block width = widest line, from
                    # _label_block_metrics), so right-align each shorter
                    # line against that same right edge rather than
                    # having every line's right end drift to a different
                    # distance from the marker.
                    (lw, _lh), _bl = cv2.getTextSize(
                        line, cv2.FONT_HERSHEY_SIMPLEX, d["fs"], d["th"])
                    line_tx = tx + (_blk_w - (lw + 2))
                else:
                    line_tx = tx
                cv2.putText(canvas, line, (line_tx, line_ty),
                           cv2.FONT_HERSHEY_SIMPLEX, d["fs"], (0, 0, 0),
                           d["th"] + 2, cv2.LINE_AA)
                cv2.putText(canvas, line, (line_tx, line_ty),
                           cv2.FONT_HERSHEY_SIMPLEX, d["fs"],
                           d.get("text_color", d["color"]),
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

    def _update_annotation_preview(self):
        """'🔄 Update preview' — re-renders every currently shown object
        (self._ann_drawn) using the Annotation style panel's *current*
        settings, without re-querying any catalogue or re-running plate
        solving. Lets you tweak marker style/color/thickness/cross
        geometry/label detail in the panel and see the result on the
        actual annotated objects immediately, instead of having to
        re-run the whole stage (which re-queries every catalogue and
        re-detects stars) just to check how a style change looks.
        Recomputes every object from scratch via
        _default_style_for_object, so any per-object 🎨 overrides made
        through "Select objects to show..." are discarded — same
        trade-off as re-running the stage itself, just much faster."""
        base = getattr(self, "_ann_base_canvas", None)
        drawn = getattr(self, "_ann_drawn", None)
        if base is None:
            QMessageBox.information(
                self, "No annotated image",
                "Run the Annotate stage at least once first.")
            return
        if not drawn:
            QMessageBox.information(
                self, "Nothing to update",
                "The last Annotate run didn't label any objects.")
            return

        for d in drawn:
            d.update(self._default_style_for_object(d))
        H, W = base.shape[0], base.shape[1]
        self._layout_annotation_labels(drawn, W, H)
        new_canvas = self._render_annotations(base, drawn)
        self._ann_drawn = drawn
        self._last_annotated_canvas = new_canvas
        annotated_rgb = cv2.cvtColor(new_canvas, cv2.COLOR_BGR2RGB).astype(
            np.float32) / 255.0
        snap = self.snapshots.get(IDX_ANN, {})
        snap["after"] = make_qimage(annotated_rgb, fits_orientation=False)
        self.snapshots[IDX_ANN] = snap
        self.snapshot_ready.emit(IDX_ANN)
        self.status_label.setText(
            "Annotate: preview updated from the current panel settings.")
        self.siril.log(
            "Annotate: preview updated from the Annotation style panel's "
            "current settings (any per-object overrides were reset).",
            LogColor.GREEN)

    def _toggle_ann_pick_mode(self, checked):
        """'🖱 Pick object on image...' toggled — arms/disarms the preview
        panel's (self.compare) click-to-add-object mode. Requires the
        stage to have run at least once, since placing and naming a
        manually-picked object needs both the un-annotated base canvas
        (to redraw onto) and the plate-solve WCS (to turn the click into
        RA/Dec) that only exist after a run."""
        if checked:
            if (getattr(self, "_ann_base_canvas", None) is None
                    or getattr(self, "_ann_wcs", None) is None):
                QMessageBox.information(
                    self, "No annotated image",
                    "Run the Annotate stage at least once first.")
                self.ann_pick_btn.blockSignals(True)
                self.ann_pick_btn.setChecked(False)
                self.ann_pick_btn.blockSignals(False)
                return
            self.compare.set_point_pick_mode(True)
            self.ann_pick_hint.setText(
                "Pick mode armed — click a point on the preview image to "
                "add an object there. Click the button again or press "
                "Esc to stop.")
        else:
            self.compare.set_point_pick_mode(False)
            self.ann_pick_hint.setText("")

    def _cancel_ann_pick_mode(self):
        """Esc pressed anywhere in the window — exit "🖱 Pick object on
        image..." mode if it's currently armed. Returns True if there
        was anything to cancel, mirroring stage_crop.py's
        _cancel_pending_crop so S30Pro_Pipeline.py's keyPressEvent can
        try both the same way."""
        btn = getattr(self, "ann_pick_btn", None)
        if btn is None or not btn.isChecked():
            return False
        btn.setChecked(False)  # triggers _toggle_ann_pick_mode(False)
        self.status_label.setText("Pick object: stopped.")
        return True

    def _on_ann_point_picked(self, fx, fy):
        """CompareView.pointPicked — only ever fires while "🖱 Pick object
        on image..." is armed (CompareView only emits this signal in its
        own point_pick_mode). `fx`/`fy` are fractions (0..1) of the
        displayed image; converts that to a pixel position, then to RA/
        Dec via the WCS _exec_stage_ann cached on self, and appends a
        new manually-placed object styled with the Annotation style
        panel's current settings via _default_style_for_object — the
        exact same dict shape _exec_stage_ann itself produces, so the
        new object is fully editable (renamed, restyled, or removed)
        through the existing "Select objects..." 🎨 editor afterward."""
        base = getattr(self, "_ann_base_canvas", None)
        wcs = getattr(self, "_ann_wcs", None)
        if base is None or wcs is None:
            return
        H, W = base.shape[0], base.shape[1]
        xd = int(round(np.clip(fx, 0.0, 1.0) * W))
        yd = int(round(np.clip(fy, 0.0, 1.0) * H))
        xd = max(0, min(W - 1, xd))
        yd = max(0, min(H - 1, yd))
        # Undo the display-orientation flip _exec_stage_ann applies when
        # building `canvas` (row 0 = top there, matching Siril's on-
        # screen display) before asking the WCS — which still follows
        # the original FITS pixel grid (row 0 = bottom) — for this
        # pixel's sky position.
        y_wcs = H - 1 - yd
        try:
            world = wcs.wcs_pix2world(
                np.array([[xd, y_wcs]], dtype=np.float64), 0)
            ra, dec = float(world[0][0]), float(world[0][1])
        except Exception as e:
            QMessageBox.warning(
                self, "Pick object failed",
                f"Couldn't convert that point to RA/Dec: {e}")
            return

        label = f"RA {ra:.3f}° Dec {dec:+.3f}°"
        res_scale = float(np.clip(max(W, H) / 1600.0, 1.0, 6.0))
        size_mult = self.ann_size_spin.value() * res_scale
        fs = 0.85 * size_mult
        th = max(2, int(round(fs * 2.3)))
        r = max(9, int(round(32 * size_mult)))
        color = CATALOG_COLORS.get("custom", (200, 200, 200))

        d = {"label": label, "kind": "custom", "x": xd, "y": yd, "r": r,
            "color": color, "fs": fs, "th": th, "extra": {}}
        d.update(self._default_style_for_object(d))

        drawn = getattr(self, "_ann_drawn", None) or []
        drawn.append(d)
        self._ann_drawn = drawn
        self._layout_annotation_labels(drawn, W, H)
        new_canvas = self._render_annotations(base, drawn)
        self._last_annotated_canvas = new_canvas
        annotated_rgb = cv2.cvtColor(new_canvas, cv2.COLOR_BGR2RGB).astype(
            np.float32) / 255.0
        snap = self.snapshots.get(IDX_ANN, {})
        snap["after"] = make_qimage(annotated_rgb, fits_orientation=False)
        self.snapshots[IDX_ANN] = snap
        self.snapshot_ready.emit(IDX_ANN)
        self.status_label.setText(
            f"Pick object: added \"{label}\" — rename or restyle it via "
            "\"Select objects...\" 🎨.")
        self.siril.log(
            f"Annotate: manually added object \"{label}\" at pixel "
            f"({xd}, {yd}).", LogColor.GREEN)

    def _pick_marker_color(self, which):
        """'Circle color...' / 'Cross color...' — opens a standard color
        picker for the custom marker-override color (`which` is "circle"
        or "cross"), independent of the other marker/of the per-catalogue
        colors used when the matching "Custom color" checkbox is off.
        Mirrors _pick_constellation_color's swatch-update pattern."""
        attr = f"ann_{which}_color"
        swatch = getattr(self, f"ann_{which}_swatch")
        title = f"{which.capitalize()} marker color"
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

    _STYLE_KEY_TO_TEXT = {"circle": "Circle", "cross": "Open Cross",
                          "both": "Circle + Open Cross"}
    _TEXT_TO_STYLE_KEY = {v: k for k, v in _STYLE_KEY_TO_TEXT.items()}
    _POS_KEY_TO_TEXT = {(1, -1): "NE", (-1, -1): "NW",
                        (1, 1): "SE", (-1, 1): "SW"}
    _TEXT_TO_POS_KEY = {v: k for k, v in _POS_KEY_TO_TEXT.items()}
    _MISSING = object()  # sentinel: "this key didn't exist on d at all"

    def _show_object_style_dialog(self, d, on_update=None):
        """'🎨' per-row button inside "Select objects to show..." —
        customize a single object's marker style, colors/thickness, cross
        geometry, and label lines/text color, independent of the
        Annotation style panel's defaults (which keep applying to every
        other object).

        "🔄 Update" applies the dialog's current settings to `d`
        immediately and calls `on_update()` (if given — the caller's
        re-layout+redraw) without closing the dialog, so you can nudge a
        value and see the result right away, then keep adjusting. "↶
        Undo" steps back through the dialog's own edit history one field
        change at a time (not tied to Update — it works whether or not
        you've clicked Update yet). "↺ Reset to panel default" discards
        everything and recomputes from the Annotation style panel's
        current settings.

        On OK, does one final commit and returns True. On Cancel, if
        Update was ever clicked during this session, `d` is restored to
        exactly what it held when this dialog opened (so a "preview via
        Update, then Cancel" round-trip leaves nothing changed) and
        returns True so the caller redraws once more to show that
        reverted state; if Update was never clicked, nothing was ever
        touched and it returns False."""
        r = d.get("r", 1) or 1
        style_map = self._STYLE_KEY_TO_TEXT
        pos_map = self._POS_KEY_TO_TEXT

        # Snapshot every key this dialog can touch, remembering which ones
        # were genuinely absent (vs. present-but-falsy) so Cancel-after-
        # Update can restore `d` exactly, not leave stray None entries.
        style_keys = ("style", "circle_color", "circle_th", "cross_color",
                     "cross_th", "cross_gap", "cross_arm", "label_pref",
                     "label_extra", "label_lines", "text_color")
        orig_d = {k: d.get(k, self._MISSING) for k in style_keys}
        applied_update = {"flag": False}

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Object Style — {d['label']}")
        dlg.resize(360, 620)
        dv = QVBoxLayout(dlg)

        info = QLabel("Overrides just this object — the Annotation style "
                      "panel's settings are untouched and still apply to "
                      "every other object. \"Update\" previews changes "
                      "immediately without closing this dialog.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        dv.addWidget(info)

        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(6)
        g.setColumnStretch(1, 1)
        gr = 0

        g.addWidget(QLabel("Marker style:"), gr, 0)
        style_combo = QComboBox()
        style_combo.addItems(["Circle", "Open Cross", "Circle + Open Cross"])
        style_combo.setCurrentText(
            style_map.get(d.get("style", "circle"), "Circle"))
        g.addWidget(style_combo, gr, 1)
        gr += 1

        state = {"circle_color": d.get("circle_color", d["color"]),
                 "cross_color": d.get("cross_color", d["color"]),
                 "text_color": d.get("text_color", d["color"])}
        swatches = {}

        def make_color_picker(key, title):
            swatch = self._color_swatch(state[key])
            swatches[key] = swatch

            def pick():
                b_, g_, r_ = state[key]
                color = QColorDialog.getColor(QColor(r_, g_, b_), dlg, title)
                if color.isValid():
                    # checkpoint() AFTER the mutation, matching every other
                    # field here (spin/combo change signals fire once their
                    # widget already holds the new value) — checkpointing
                    # before the color change would capture the stale color
                    # as the new "current" snapshot, silently dropping it
                    # from undo history on the next change.
                    state[key] = (color.blue(), color.green(), color.red())
                    swatch.setStyleSheet(
                        f"background-color: rgb({color.red()},"
                        f"{color.green()},{color.blue()}); "
                        "border-radius: 3px; "
                        "border: 1px solid rgba(255,255,255,60);")
                    checkpoint()
            return swatch, pick

        circle_swatch, pick_circle_color = make_color_picker(
            "circle_color", "Marker color")
        circle_color_btn = QPushButton("Marker color...")
        circle_color_btn.setToolTip(
            "Color of the Circle marker (used when the marker style "
            "above is Circle or Circle + Open Cross).")
        circle_color_btn.clicked.connect(pick_circle_color)
        g.addWidget(circle_swatch, gr, 0)
        g.addWidget(circle_color_btn, gr, 1)
        gr += 1

        g.addWidget(QLabel("Marker thickness (px):"), gr, 0)
        circle_th_spin = QSpinBox()
        circle_th_spin.setRange(1, 12)
        circle_th_spin.setValue(int(round(d.get("circle_th", d.get("th", 2)))))
        g.addWidget(circle_th_spin, gr, 1)
        gr += 1

        text_swatch, pick_text_color = make_color_picker(
            "text_color", "Text color")
        text_color_btn = QPushButton("Text color...")
        text_color_btn.setToolTip(
            "Color of the label text itself, independent of the marker "
            "color(s).")
        text_color_btn.clicked.connect(pick_text_color)
        g.addWidget(text_swatch, gr, 0)
        g.addWidget(text_color_btn, gr, 1)
        gr += 1

        cross_swatch, pick_cross_color = make_color_picker(
            "cross_color", "Cross color")
        cross_color_btn = QPushButton("Cross color...")
        cross_color_btn.clicked.connect(pick_cross_color)
        g.addWidget(cross_swatch, gr, 0)
        g.addWidget(cross_color_btn, gr, 1)
        gr += 1

        g.addWidget(QLabel("Cross thickness (px):"), gr, 0)
        cross_th_spin = QSpinBox()
        cross_th_spin.setRange(1, 12)
        cross_th_spin.setValue(int(round(d.get("cross_th", d.get("th", 2)))))
        g.addWidget(cross_th_spin, gr, 1)
        gr += 1

        g.addWidget(QLabel("Cross gap (× radius):"), gr, 0)
        gap_spin = QDoubleSpinBox()
        gap_spin.setRange(0.0, 3.0)
        gap_spin.setSingleStep(0.1)
        gap_spin.setValue(round(d.get("cross_gap", r * 0.5) / r, 2))
        g.addWidget(gap_spin, gr, 1)
        gr += 1

        g.addWidget(QLabel("Cross arm (× radius):"), gr, 0)
        arm_spin = QDoubleSpinBox()
        arm_spin.setRange(0.1, 3.0)
        arm_spin.setSingleStep(0.1)
        arm_spin.setValue(round(d.get("cross_arm", r * 0.7) / r, 2))
        g.addWidget(arm_spin, gr, 1)
        gr += 1

        g.addWidget(QLabel("Label position:"), gr, 0)
        pos_combo = QComboBox()
        pos_combo.addItems(["Auto (avoid overlap)", "NE", "NW", "SE", "SW"])
        pos_combo.setCurrentText(
            pos_map.get(d.get("label_pref"), "Auto (avoid overlap)"))
        g.addWidget(pos_combo, gr, 1)
        gr += 1

        g.addWidget(QLabel("Label distance (× radius):"), gr, 0)
        dist_spin = QDoubleSpinBox()
        dist_spin.setRange(-2.0, 5.0)
        dist_spin.setSingleStep(0.1)
        dist_spin.setValue(round(d.get("label_extra", 0) / r, 2))
        dist_spin.setToolTip(
            "How far the label text sits from the marker, as a "
            "multiple of the marker's own radius, on top of the normal "
            "placement distance — negative values pull the label in "
            "closer, positive values push it further out. Applies "
            "regardless of marker style.")
        g.addWidget(dist_spin, gr, 1)
        gr += 1
        dv.addLayout(g)

        dv.addWidget(QLabel("Label lines (one per row of text):"))
        lines_edit = QPlainTextEdit()
        lines_edit.setMaximumHeight(110)
        lines_edit.setToolTip(
            "The object's name plus any detail/custom lines, top to "
            "bottom, one label line per row of text — type, delete, or "
            "reorder rows freely (this box has its own Ctrl+Z undo for "
            "text edits). This doesn't affect any other object.")
        lines_edit.setPlainText(
            "\n".join(d.get("label_lines", [d["label"]])))
        dv.addWidget(lines_edit)

        # ---------------------------------------------------- undo history
        # A lazy "checkpoint on change" stack: `last_state` always holds a
        # snapshot of every field taken right after the most recent change
        # (or the dialog's opening values, if nothing has changed yet).
        # Each checkpoint() call — wired to every field's change signal,
        # plus the color-pick actions above, which don't fire a plain
        # valueChanged/currentTextChanged — pushes that snapshot onto the
        # undo stack, then re-captures the (now current) state as the new
        # `last_state`. Undo pops the stack and restores it; `restoring`
        # suppresses checkpoint() while that restore is itself in
        # progress, so undoing/resetting never pollutes its own history.
        # Label-line text edits are deliberately NOT wired to checkpoint()
        # — checkpointing on every keystroke would make one Undo click
        # only step back a single character. lines_edit is a QPlainTextEdit
        # with its own native Ctrl+Z/Ctrl+Shift+Z text-undo instead; this
        # dialog's Undo still restores line text as part of whichever
        # other field's checkpoint most recently captured it (or via
        # Reset to panel default, which does checkpoint).
        undo_stack = []
        restoring = {"flag": False}

        def capture_state():
            return {
                "style": style_combo.currentText(),
                "circle_color": state["circle_color"],
                "cross_color": state["cross_color"],
                "text_color": state["text_color"],
                "circle_th": circle_th_spin.value(),
                "cross_th": cross_th_spin.value(),
                "gap": gap_spin.value(),
                "arm": arm_spin.value(),
                "pos": pos_combo.currentText(),
                "dist": dist_spin.value(),
                "lines": lines_edit.toPlainText(),
            }

        last_state = {"ref": capture_state()}

        def checkpoint():
            if restoring["flag"]:
                return
            undo_stack.append(last_state["ref"])
            last_state["ref"] = capture_state()
            undo_btn.setEnabled(True)

        def apply_state(st):
            restoring["flag"] = True
            try:
                style_combo.setCurrentText(st["style"])
                for key in ("circle_color", "cross_color", "text_color"):
                    state[key] = st[key]
                    rr, gg, bb = st[key][2], st[key][1], st[key][0]
                    swatches[key].setStyleSheet(
                        f"background-color: rgb({rr},{gg},{bb}); "
                        "border-radius: 3px; "
                        "border: 1px solid rgba(255,255,255,60);")
                circle_th_spin.setValue(int(round(st["circle_th"])))
                cross_th_spin.setValue(int(round(st["cross_th"])))
                gap_spin.setValue(st["gap"])
                arm_spin.setValue(st["arm"])
                pos_combo.setCurrentText(st["pos"])
                dist_spin.setValue(st["dist"])
                lines_edit.setPlainText(st["lines"])
            finally:
                restoring["flag"] = False

        def do_undo():
            if not undo_stack:
                return
            prev = undo_stack.pop()
            apply_state(prev)
            last_state["ref"] = prev
            undo_btn.setEnabled(bool(undo_stack))

        style_combo.currentTextChanged.connect(lambda _t: checkpoint())
        circle_th_spin.valueChanged.connect(lambda _v: checkpoint())
        cross_th_spin.valueChanged.connect(lambda _v: checkpoint())
        gap_spin.valueChanged.connect(lambda _v: checkpoint())
        arm_spin.valueChanged.connect(lambda _v: checkpoint())
        pos_combo.currentTextChanged.connect(lambda _t: checkpoint())
        dist_spin.valueChanged.connect(lambda _v: checkpoint())

        btn_row = QHBoxLayout()
        undo_btn = QPushButton("↶  Undo")
        undo_btn.setEnabled(False)
        undo_btn.setToolTip(
            "Steps back one field change at a time within this dialog "
            "(marker style, colors, thickness, cross geometry, or label "
            "lines) — independent of whether you've clicked Update.")
        undo_btn.clicked.connect(do_undo)
        btn_row.addWidget(undo_btn)

        reset_btn = QPushButton("↺  Reset to panel default")
        reset_btn.setToolTip(
            "Discards every override above and recomputes this object's "
            "style and label lines exactly as the Annotation style panel "
            "would produce them right now. Counts as a single undoable "
            "step.")

        def do_reset():
            defaults = self._default_style_for_object(d)
            new_state = {
                "style": style_map[defaults["style"]],
                "circle_color": defaults["circle_color"],
                "cross_color": defaults["cross_color"],
                "text_color": defaults["text_color"],
                "circle_th": defaults["circle_th"],
                "cross_th": defaults["cross_th"],
                "gap": defaults["cross_gap"] / r,
                "arm": defaults["cross_arm"] / r,
                "pos": pos_map.get(defaults["label_pref"],
                                   "Auto (avoid overlap)"),
                "dist": defaults["label_extra"] / r,
                "lines": "\n".join(defaults["label_lines"]),
            }
            apply_state(new_state)
            checkpoint()

        reset_btn.clicked.connect(do_reset)
        btn_row.addWidget(reset_btn)
        dv.addLayout(btn_row)

        def commit_to_d():
            style = self._TEXT_TO_STYLE_KEY[style_combo.currentText()]
            label_pref = (None if style == "circle" else
                         self._TEXT_TO_POS_KEY.get(pos_combo.currentText()))
            lines = [row.strip() for row in lines_edit.toPlainText().splitlines()
                    if row.strip()]
            if not lines:
                lines = [d["label"]]
            d["style"] = style
            d["circle_color"] = state["circle_color"]
            d["circle_th"] = circle_th_spin.value()
            d["cross_color"] = state["cross_color"]
            d["cross_th"] = cross_th_spin.value()
            d["cross_gap"] = r * gap_spin.value()
            d["cross_arm"] = r * arm_spin.value()
            d["label_pref"] = label_pref
            d["label_extra"] = r * dist_spin.value()  # applies to every style
            d["label_lines"] = lines
            d["text_color"] = state["text_color"]
            applied_update["flag"] = True

        def do_update():
            commit_to_d()
            if on_update:
                on_update()

        update_btn = QPushButton("🔄  Update")
        update_btn.setToolTip(
            "Applies these settings to the preview immediately, without "
            "closing this dialog — keep adjusting and clicking Update to "
            "see each change.")
        update_btn.clicked.connect(do_update)
        dv.addWidget(update_btn)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok |
            QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        dv.addWidget(buttons)

        if dlg.exec() != QDialog.DialogCode.Accepted:
            if not applied_update["flag"]:
                return False
            # Update was clicked at least once — put `d` back exactly as
            # it was before this dialog opened, deleting any key that
            # didn't exist originally rather than leaving a stray None.
            for k, v in orig_d.items():
                if v is self._MISSING:
                    d.pop(k, None)
                else:
                    d[k] = v
            return True

        commit_to_d()
        return True

    def _show_object_selector_dialog(self):
        """'☑ Select objects to show...' — pick which labeled objects stay
        visible, redrawing instantly from the cached un-annotated base
        canvas (no re-querying any catalogue). Each row also has a '🎨'
        button opening _show_object_style_dialog for that one object, so
        an individual star/DSO can use a different marker style, color,
        or label content than everything else drawn by the current
        Annotate run. Main-thread only (QDialog) — this is a button slot,
        never called from the worker thread."""
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

        H, W = base.shape[0], base.shape[1]
        # Snapshot what's on screen now so Cancel can restore it exactly —
        # both the visibility checklist AND any per-object style edits
        # made while this dialog was up apply live, not just on OK. A
        # shallow per-dict copy is enough: _show_object_style_dialog only
        # ever *rebinds* keys like "label_lines" to a brand-new list, it
        # never mutates an existing list/dict in place, so the copies
        # below keep referencing the untouched original values.
        original_drawn = list(drawn)
        original_snapshot = [dict(d) for d in drawn]
        original_canvas = self._last_annotated_canvas

        def apply_preview(kept_list):
            """Redraw from the un-annotated base with only `kept_list` and
            push the result straight into the preview + export canvas —
            called on every checkbox toggle and after every per-object
            style edit, not just when OK is pressed, so the preview
            reflects the current state in real time."""
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
        dlg.resize(420, 460)
        dv = QVBoxLayout(dlg)
        dlg_info = QLabel("Uncheck objects to hide them from the "
                          "annotated image (updates live). Click 🎨 to "
                          "give one object its own marker style, color, "
                          "or label content.")
        dlg_info.setObjectName("SubHeader")
        dlg_info.setWordWrap(True)
        dv.addWidget(dlg_info)

        lw = QListWidget()
        row_checks = []  # [(d, QCheckBox), ...] — parallel to `drawn`

        def rebuild_kept():
            return [d for d, cb in row_checks if cb.isChecked()]

        def on_visibility_changed(_checked=None):
            apply_preview(rebuild_kept())

        def redo_layout_and_preview():
            self._layout_annotation_labels(drawn, W, H)
            apply_preview(rebuild_kept())

        def open_style_editor(target_d):
            # on_update: fires on every "🔄 Update" click inside the style
            # dialog, so the live preview reflects each change while the
            # dialog is still open, not just after it closes.
            changed = self._show_object_style_dialog(
                target_d, on_update=redo_layout_and_preview)
            if changed:
                redo_layout_and_preview()

        for d in drawn:
            cat_label = CATALOG_LABELS.get(d["kind"], d["kind"].title())
            row_widget = QWidget()
            row_h = QHBoxLayout(row_widget)
            row_h.setContentsMargins(4, 2, 4, 2)
            cb = QCheckBox(f"{cat_label} — {d['label']}")
            r, gc, b = d["color"][2], d["color"][1], d["color"][0]
            cb.setStyleSheet(f"color: rgb({r},{gc},{b});")
            cb.setChecked(True)
            cb.toggled.connect(on_visibility_changed)
            row_h.addWidget(cb, 1)
            style_btn = QPushButton("🎨")
            style_btn.setFixedWidth(30)
            style_btn.setToolTip(
                "Customize this object's marker style, colors, and label "
                "lines — independent of the Annotation style panel's "
                "defaults.")
            style_btn.clicked.connect(
                lambda _checked=False, dd=d: open_style_editor(dd))
            row_h.addWidget(style_btn)
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            lw.addItem(item)
            lw.setItemWidget(item, row_widget)
            row_checks.append((d, cb))
        dv.addWidget(lw, 1)

        btn_row = QHBoxLayout()
        select_all_btn = QPushButton("Select All")
        deselect_all_btn = QPushButton("Deselect All (hide all)")
        select_all_btn.clicked.connect(
            lambda: [cb.setChecked(True) for _, cb in row_checks])
        deselect_all_btn.clicked.connect(
            lambda: [cb.setChecked(False) for _, cb in row_checks])
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
            # opened, undoing both the visibility checklist AND any
            # per-object style edits made while it was up. Restoring each
            # dict's contents in place (rather than just re-pointing
            # `drawn`) matters because other code (e.g. export) may hold
            # its own reference to these same dict objects.
            for d, snap in zip(drawn, original_snapshot):
                d.clear()
                d.update(snap)
            apply_preview(original_drawn)
            self._last_annotated_canvas = original_canvas
            self.status_label.setText("Select objects: canceled, no change.")
            return

        kept = rebuild_kept()
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

