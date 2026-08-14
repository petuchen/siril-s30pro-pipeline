"""Hubble Palette (synthetic SHO/HOO + NebulaChrome) stage mixin for
UnifiedPipelineWindow."""

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QMessageBox, QPushButton, QSlider, QVBoxLayout,
    QWidget,
)

from s30pro_pipeline.constants import (
    IDX_PAL, IDX_STR, PALETTE_PRESETS, PALETTE_TO_PROFILE, SENSOR_PROFILES,
    luminance,
)
from s30pro_pipeline.graxpert_helpers import richardson_lucy_sharpen

SLIDER_VALUE_LABEL_WIDTH = 40


class PaletteMixin:
    def _build_stage_palette(self):
        box, v = self._stage_box(8, "Hubble Palette — Synthetic SHO/HOO",
                                 enabled_check=False)
        self.stage_pal_box = box

        info = QLabel("For dual-band (LP filter) data on emission nebulae. "
                      "Extracts Hα from red and OIII from green+blue, then "
                      "remixes them into a false-color palette. No real SII "
                      "exists on an OSC camera — SHO here is synthetic. "
                      "Turn SPCC off in stage 1 when using this. Tip: run "
                      "stage 5 (Remove Stars) first so the palette only "
                      "recolors the nebula, not the stars.")
        info.setObjectName("SubHeader")
        info.setWordWrap(True)
        v.addWidget(info)

        mrow = QHBoxLayout()
        mrow.setSpacing(10)
        mrow.addWidget(QLabel("Mode:"))
        self.palette_mode_combo = QComboBox()
        self.palette_mode_combo.addItems(
            ["Channel mix (SHO / HOO)",
             "NebulaChrome (deep palette)"])
        self.palette_mode_combo.setToolTip(
            "Channel mix: extract Hα/OIII and remix with the weights below.\n"
            "NebulaChrome: background neutralization + bright-core white\n"
            "reference (pushes the Hα core toward teal while the faint rim\n"
            "stays red — no channel math), followed by a saturation /\n"
            "shadows-highlights polish and a deconvolution sharpen pass. The\n"
            "recolor/saturation are luminosity-masked to the nebula itself\n"
            "(Peak isolation slider) so the background doesn't pick up a\n"
            "color cast, then the whole result is blended against the\n"
            "original by the Recolor strength slider below.")
        self.palette_mode_combo.currentIndexChanged.connect(
            self._on_palette_mode_changed)
        mrow.addWidget(self.palette_mode_combo, 1)
        v.addLayout(mrow)

        top = QHBoxLayout()
        top.setSpacing(10)
        top.addWidget(QLabel("Preset:"))
        self.palette_preset_combo = QComboBox()
        self.palette_preset_combo.addItems(list(PALETTE_PRESETS.keys()))
        self.palette_preset_combo.setCurrentText("SHO — golden dynamic")
        self.palette_preset_combo.currentTextChanged.connect(
            self._on_palette_preset_changed)
        top.addWidget(self.palette_preset_combo, 1)
        v.addLayout(top)

        # weight matrix:  out = w_ha * Ha + w_oiii * OIII
        g = QGridLayout()
        g.setHorizontalSpacing(10)
        g.setVerticalSpacing(8)
        for col, name in enumerate(("Hα weight", "OIII weight")):
            lbl = QLabel(name)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            g.addWidget(lbl, 0, col + 1)
            g.setColumnStretch(col + 1, 1)
        colors = {"R": "#ff6b6b", "G": "#69db7c", "B": "#74a8ff"}
        self.palette_weights = {}
        for r, ch in enumerate(("R", "G", "B")):
            lbl = QLabel(ch)
            lbl.setStyleSheet(f"color: {colors[ch]}; font-weight: bold;")
            g.addWidget(lbl, r + 1, 0)
            pair = []
            for c in range(2):
                spin = QDoubleSpinBox()
                spin.setRange(0.0, 1.5)
                spin.setSingleStep(0.05)
                spin.setDecimals(2)
                pair.append(spin)
                g.addWidget(spin, r + 1, c + 1)
            self.palette_weights[ch] = pair
        v.addLayout(g)

        # Own row each (was one crowded row) — the two labels together were
        # too wide for the ~1/3-window-width target.
        self.palette_linfit_checkbox = QCheckBox("Linear fit OIII to Hα")
        self.palette_linfit_checkbox.setChecked(True)
        self.palette_linfit_checkbox.setToolTip(
            "Rescales the (usually much weaker) OIII signal so its background\n"
            "and spread match Hα before mixing — recommended.")
        v.addWidget(self.palette_linfit_checkbox)
        self.palette_set_profile_checkbox = QCheckBox(
            "Auto-set stretch profile (narrowband)")
        self.palette_set_profile_checkbox.setChecked(True)
        v.addWidget(self.palette_set_profile_checkbox)

        nc_row = QHBoxLayout()
        nc_row.setSpacing(10)
        nc_row.addWidget(QLabel("NebulaChrome recolor strength:"))
        self.palette_nebulachrome_strength = QSlider(Qt.Orientation.Horizontal)
        self.palette_nebulachrome_strength.setRange(0, 100)
        self.palette_nebulachrome_strength.setValue(70)
        self.palette_nebulachrome_strength.setToolTip(
            "How strongly to blend the NebulaChrome recolor/polish/sharpen "
            "result against the original — 100% is the full effect, lower "
            "values keep more of the original color. This is what keeps the "
            "effect controllable instead of overcorrecting like the old "
            "Color Calibration trick did.")
        nc_row.addWidget(self.palette_nebulachrome_strength, 1)
        self.palette_nebulachrome_strength_label = QLabel("70%")
        self.palette_nebulachrome_strength_label.setMinimumWidth(
            SLIDER_VALUE_LABEL_WIDTH)
        self.palette_nebulachrome_strength.valueChanged.connect(
            lambda val: self.palette_nebulachrome_strength_label.setText(f"{val}%"))
        nc_row.addWidget(self.palette_nebulachrome_strength_label)
        v.addLayout(nc_row)

        nc_peak_row = QHBoxLayout()
        nc_peak_row.setSpacing(10)
        nc_peak_row.addWidget(QLabel("NebulaChrome peak isolation:"))
        self.palette_nebulachrome_peak = QSlider(Qt.Orientation.Horizontal)
        self.palette_nebulachrome_peak.setRange(100, 600)
        self.palette_nebulachrome_peak.setValue(300)
        self.palette_nebulachrome_peak.setToolTip(
            "How sharply the recolor/saturation is restricted to bright "
            "nebula structure vs. the sky background — an automatic "
            "luminosity mask. Higher = a harder cutoff (background stays "
            "untouched even if it isn't perfectly neutral), lower = a "
            "softer, more gradual falloff. Fixes the background picking up "
            "a blue cast from the recolor.")
        nc_peak_row.addWidget(self.palette_nebulachrome_peak, 1)
        self.palette_nebulachrome_peak_label = QLabel("3.0")
        self.palette_nebulachrome_peak_label.setMinimumWidth(
            SLIDER_VALUE_LABEL_WIDTH)
        self.palette_nebulachrome_peak.valueChanged.connect(
            lambda val: self.palette_nebulachrome_peak_label.setText(f"{val/100:.1f}"))
        nc_peak_row.addWidget(self.palette_nebulachrome_peak_label)
        v.addLayout(nc_peak_row)

        gimp_box = QGroupBox()
        gv = QVBoxLayout(gimp_box)
        gv.setContentsMargins(10, 6, 10, 10)
        gv.setSpacing(8)

        self.palette_gimp_toggle_btn = QPushButton(
            "▸  GIMP replacement polish")
        self.palette_gimp_toggle_btn.setObjectName("CollapseHeader")
        self.palette_gimp_toggle_btn.setCheckable(True)
        self.palette_gimp_toggle_btn.setChecked(False)
        self.palette_gimp_toggle_btn.setToolTip(
            "Click to expand/collapse — collapsed by default since this "
            "is an optional extra pass most people won't need.")
        gv.addWidget(self.palette_gimp_toggle_btn)

        gimp_content = QWidget()
        gimp_content.setVisible(False)
        gcv = QVBoxLayout(gimp_content)
        gcv.setContentsMargins(0, 2, 0, 0)
        gcv.setSpacing(8)
        gv.addWidget(gimp_content)

        gimp_info = QLabel(
            "Colors ▸ Saturation, Colors ▸ Shadows-Highlights, Colors ▸ "
            "Brightness-Contrast, Filters ▸ Enhance ▸ Sharpen, and "
            "Filters ▸ Enhance ▸ Noise Reduction, folded into one "
            "tunable, repeatable step (from gimp_replacement.py) instead "
            "of a manual TIFF round-trip through GIMP. Runs after the "
            "recolor above, on whichever mode you picked. All sliders "
            "default to \"no change\".")
        gimp_info.setObjectName("SubHeader")
        gimp_info.setWordWrap(True)
        gcv.addWidget(gimp_info)

        self.palette_gimp_checkbox = QCheckBox("Apply GIMP replacement polish")
        self.palette_gimp_checkbox.setToolTip(
            "When off, none of the sliders below have any effect — the "
            "Hubble Palette stage output is just the recolor result above, "
            "same as before this option existed.")
        gcv.addWidget(self.palette_gimp_checkbox)

        gg = QGridLayout()
        gg.setHorizontalSpacing(10)
        gg.setVerticalSpacing(8)
        gg.setColumnStretch(1, 1)
        self.palette_gimp_sliders = {}
        self.palette_gimp_labels = {}
        gimp_specs = (
            ("saturation", "🎨 Saturation", 0, 200, 100,
             "Colors ▸ Saturation. 100% = unchanged, HSV saturation "
             "channel scaled by this factor."),
            ("shadows", "🌑 Shadows", -100, 100, 0,
             "Colors ▸ Shadows-Highlights (shadows side). Positive lifts "
             "dark tones — can reveal hidden detail but also lifts noise."),
            ("highlights", "🌕 Highlights", -100, 100, 0,
             "Colors ▸ Shadows-Highlights (highlights/white-point side). "
             "Negative pulls down bright tones."),
            ("contrast", "◐ Contrast", -100, 100, 0,
             "Colors ▸ Brightness-Contrast (contrast only — brightness "
             "isn't part of this workflow, Stretch already handles that)."),
            ("sharpen", "◇ Sharpen", 0, 100, 0,
             "Filters ▸ Enhance ▸ Sharpen (Unsharp Mask). Kept gentle by "
             "design in the tutorial, since AstroSharp/deconvolution does "
             "the heavier sharpening pass later."),
            ("denoise", "✦ Denoise", 0, 100, 0,
             "Filters ▸ Enhance ▸ Noise Reduction — edge-preserving "
             "bilateral denoise, a light manual touch-up (not the AI "
             "Denoise stage earlier in the pipeline)."),
        )
        for r, (key, label, lo, hi, default, tip) in enumerate(gimp_specs):
            lbl = QLabel(label + ":")
            lbl.setToolTip(tip)
            gg.addWidget(lbl, r, 0)
            sl = QSlider(Qt.Orientation.Horizontal)
            sl.setRange(lo, hi)
            sl.setValue(default)
            sl.setToolTip(tip)
            gg.addWidget(sl, r, 1)
            val = QLabel(str(default))
            val.setMinimumWidth(SLIDER_VALUE_LABEL_WIDTH)
            val.setAlignment(Qt.AlignmentFlag.AlignRight)
            gg.addWidget(val, r, 2)
            sl.valueChanged.connect(
                lambda v_, lb=val: lb.setText(str(v_)))
            self.palette_gimp_sliders[key] = sl
            self.palette_gimp_labels[key] = val
        gcv.addLayout(gg)

        gimp_reset_btn = QPushButton("↺  Reset")
        gimp_reset_btn.clicked.connect(self._reset_palette_gimp_controls)
        gcv.addWidget(gimp_reset_btn)

        v.addWidget(gimp_box)

        def _on_gimp_collapse_toggle(checked):
            gimp_content.setVisible(checked)
            arrow = "▾" if checked else "▸"
            self.palette_gimp_toggle_btn.setText(
                f"{arrow}  GIMP replacement polish")
        self.palette_gimp_toggle_btn.toggled.connect(_on_gimp_collapse_toggle)

        def _on_gimp_toggle(checked):
            gg_enabled = checked
            for sl in self.palette_gimp_sliders.values():
                sl.setEnabled(gg_enabled)
            for lbl in self.palette_gimp_labels.values():
                lbl.setEnabled(gg_enabled)
        self.palette_gimp_checkbox.toggled.connect(_on_gimp_toggle)
        _on_gimp_toggle(False)

        self._on_palette_preset_changed(self.palette_preset_combo.currentText())
        self._on_palette_mode_changed(self.palette_mode_combo.currentIndex())

        row, self.stage_pal_run = self._run_row(
            self._run_palette_stage, undo_stage=IDX_PAL)
        v.addLayout(row)
        return box

    def _run_palette_stage(self):
        """Run-button slot for the Palette stage. Palette recombines Hα/OIII
        and is normally meant to run *before* Stretch — running it after
        Stretch has already produced a non-linear image is unusual and used
        to happen silently, so confirm first. Must run on the main thread
        (QMessageBox), before handing off to the worker via `_launch`."""
        if IDX_STR in self.stage_backups:
            reply = QMessageBox.question(
                self, "Stretch already ran",
                "The Stretch stage has already run. Hubble Palette normally "
                "runs before Stretch — applying it now will recombine "
                "channels on an already-stretched (non-linear) image, which "
                "may look unexpected.\n\nRun Palette anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No)
            if reply != QMessageBox.StandardButton.Yes:
                return
        self._launch([self._exec_stage_palette])

    def _on_palette_preset_changed(self, preset):
        weights = PALETTE_PRESETS.get(preset)
        custom = weights is None
        mix_mode = (getattr(self, "palette_mode_combo", None) is None
                    or self.palette_mode_combo.currentIndex() == 0)
        for ch, pair in self.palette_weights.items():
            for i, spin in enumerate(pair):
                spin.setEnabled(custom and mix_mode)
                if not custom:
                    spin.blockSignals(True)
                    spin.setValue(weights[ch][i])
                    spin.blockSignals(False)
        # suggest matching stretch profile (stretch card may not be built yet)
        if (getattr(self, "profile_combo", None) is not None
                and getattr(self, "palette_set_profile_checkbox", None) is not None
                and self.palette_set_profile_checkbox.isChecked()):
            prof = PALETTE_TO_PROFILE.get(preset)
            if prof in SENSOR_PROFILES:
                self.profile_combo.setCurrentText(prof)

    def _on_palette_mode_changed(self, idx):
        """Enable/disable channel-mix controls vs. NebulaChrome controls."""
        mix = idx == 0
        self.palette_preset_combo.setEnabled(mix)
        self.palette_linfit_checkbox.setEnabled(mix)
        custom = PALETTE_PRESETS.get(
            self.palette_preset_combo.currentText()) is None
        for pair in self.palette_weights.values():
            for spin in pair:
                spin.setEnabled(mix and custom)
        nc_slider = getattr(self, "palette_nebulachrome_strength", None)
        if nc_slider is not None:
            nc_slider.setEnabled(not mix)
        nc_peak = getattr(self, "palette_nebulachrome_peak", None)
        if nc_peak is not None:
            nc_peak.setEnabled(not mix)

    def _reset_palette_gimp_controls(self):
        defaults = {"saturation": 100, "shadows": 0, "highlights": 0,
                    "contrast": 0, "sharpen": 0, "denoise": 0}
        for key, sl in self.palette_gimp_sliders.items():
            sl.blockSignals(True)
            sl.setValue(defaults[key])
            sl.blockSignals(False)
            self.palette_gimp_labels[key].setText(str(defaults[key]))

    @staticmethod
    def _gimp_replacement_polish(img, saturation=1.0, shadows=0.0,
                                 highlights=0.0, contrast=0.0,
                                 sharpen_amount=0.0, denoise_strength=0.0,
                                 progress=None):
        """Pure-Python stand-in for the manual GIMP finishing pass in the
        "Rosette Nebula Hubble Palette" tutorial workflow — GIMP Colors >
        Saturation, Colors > Shadows-Highlights, Colors > Brightness-
        Contrast (contrast only), Filters > Enhance > Sharpen (Unsharp
        Mask), and Filters > Enhance > Noise Reduction (bilateral) — ported
        from the standalone gimp_replacement.py prototype so it runs as one
        tunable, repeatable step inside the Hubble Palette stage instead of
        a manual TIFF round-trip through GIMP.

        img: planar (3,h,w) float 0..1. Parameters mirror
        gimp_replacement.py's functions exactly (adjust_saturation,
        adjust_shadows_highlights, adjust_brightness_contrast's contrast
        term, sharpen, reduce_noise):
          saturation        1.0 = unchanged, >1 boosts, <1 mutes (HSV S)
          shadows           -1..1, >0 lifts dark tones
          highlights        -1..1, <0 pulls down bright tones
          contrast          -1..1 gain around the midpoint, 0 = unchanged
          sharpen_amount    0..~2.5, unsharp mask amount, 0 = off
          denoise_strength  0..1, edge-preserving bilateral denoise, 0 = off
        Applied in the same order as the manual GIMP workflow: saturation,
        then shadows/highlights, then contrast, then sharpen, then
        denoise."""
        from skimage.color import rgb2hsv, hsv2rgb
        from skimage.filters import unsharp_mask
        from skimage.restoration import denoise_bilateral

        out = np.transpose(img.astype(np.float32), (1, 2, 0))
        out = np.clip(out, 0.0, 1.0)

        if abs(saturation - 1.0) > 1e-3:
            if progress:
                progress("GIMP polish: saturation...", 0.15)
            hsv = rgb2hsv(out)
            hsv[..., 1] = np.clip(hsv[..., 1] * saturation, 0.0, 1.0)
            out = np.clip(hsv2rgb(hsv), 0.0, 1.0)

        if abs(shadows) > 1e-3 or abs(highlights) > 1e-3:
            if progress:
                progress("GIMP polish: shadows/highlights...", 0.35)
            if abs(shadows) > 1e-3:
                weight = 1.0 - out
                out = out + shadows * weight * out
            if abs(highlights) > 1e-3:
                weight = out
                out = out + highlights * weight * (1.0 - out)
            out = np.clip(out, 0.0, 1.0)

        if abs(contrast) > 1e-3:
            if progress:
                progress("GIMP polish: contrast...", 0.5)
            out = np.clip((out - 0.5) * (1.0 + contrast) + 0.5, 0.0, 1.0)

        if sharpen_amount > 1e-3:
            if progress:
                progress("GIMP polish: sharpen...", 0.7)
            out = np.clip(
                unsharp_mask(out, radius=2.0, amount=sharpen_amount,
                            channel_axis=-1),
                0.0, 1.0)

        if denoise_strength > 1e-3:
            if progress:
                progress("GIMP polish: noise reduction...", 0.9)
            out = np.clip(
                denoise_bilateral(
                    out, sigma_color=0.05 + 0.2 * denoise_strength,
                    sigma_spatial=5, channel_axis=-1),
                0.0, 1.0)

        return np.transpose(out, (2, 0, 1)).astype(np.float32)

    @staticmethod
    def _palette_nebulachrome(img, strength=0.7, peak_gamma=3.0, progress=None):
        """NebulaChrome — consolidated pseudo-Hubble recolor, replacing the
        old "Color Calibration trick" (which applied a hard background/white
        -reference correction at full force and often overcorrected into a
        flat, blown-out look). Three passes, each pulled from a standalone
        prototype script and merged here:

          1. Background neutralization + bright-core white reference (from
             siril_hubble_palette.py) — pushes the Hα-dominated core toward
             teal while the faint outer rim stays red/gold, same idea as the
             old trick but now just one ingredient instead of the whole thing.
          2. Saturation + shadows/highlights polish (from gimp_replacement.py)
             to make the recolor read clearly instead of looking washed out.
          3. Richardson-Lucy deconvolution sharpen (from
             deconvolution_sharpen.py, reusing the same richardson_lucy_sharpen
             helper as the Final Touch stage) to bring out nebula structure.

        Passes 1's white-reference scale and pass 2's saturation boost are
        both *luminosity-masked*: computed once as if applied at full force,
        then blended in per-pixel by how bright that pixel is relative to
        the sky background vs. the nebula peak (an automatic luminosity
        mask, `peak_gamma` controls how hard that cutoff is). Without this,
        the white-reference step is a flat per-channel multiply applied to
        *every* pixel including the background — and since the blue channel
        under a dual-band filter is mostly crosstalk/noise rather than real
        OIII signal, the multiplier strong enough to pull the bright core
        toward teal also drags that background noise into a visible blue
        cast. Gating by luminosity keeps the background close to untouched
        while the nebula itself still gets the full effect.

        The full-strength result of all three passes is then blended against
        the original image by `strength` (0..1) — this blend is what actually
        fixes "doesn't work very well": instead of an all-or-nothing swap,
        NebulaChrome fades smoothly from "no change" (0%) to "full effect"
        (100%), so it can be dialed back instead of overcorrecting.
        img: planar (3,h,w) float 0..1."""
        orig = img.astype(np.float32).copy()
        out = orig.copy()

        # --- pass 1: background neutralization + bright-core white ref ---
        if progress:
            progress("NebulaChrome: background neutralization...", 0.2)
        L = luminance(out)
        stride = max(1, L.size // 2000000)
        Ls = L.flatten()[::stride]
        bg_level = float(np.percentile(Ls, 5.0))
        lo_mask = L <= bg_level
        if np.count_nonzero(lo_mask) > 100:
            bkg = np.array([np.median(out[c][lo_mask]) for c in range(3)])
            target = float(np.mean(bkg))
            for c in range(3):
                out[c] = out[c] - (bkg[c] - target)
            out = np.clip(out, 0.0, 1.0)

        # Luminosity mask: 0 at/below the sky background level, ramping up
        # to 1 near the nebula's brightest structure, with `peak_gamma`
        # steepening the ramp so only genuine nebula signal counts — this
        # is what keeps the recolor/saturation off the background.
        if progress:
            progress("NebulaChrome: building luminosity mask...", 0.35)
        L2 = luminance(out)
        L2s = L2.flatten()[::stride]
        bg_level2 = float(np.percentile(L2s, 5.0))
        peak_level = float(np.percentile(L2s, 99.0))
        t = np.clip((L2 - bg_level2) / max(peak_level - bg_level2, 1e-6), 0.0, 1.0)
        mask = t * t * (3.0 - 2.0 * t)          # smoothstep
        mask = mask ** max(1.0, float(peak_gamma))  # steeper = harder cutoff

        if progress:
            progress("NebulaChrome: white reference from nebula core...", 0.45)
        hi_mask = L2 >= peak_level
        if np.count_nonzero(hi_mask) > 100:
            ref = np.array([float(np.mean(out[c][hi_mask]))
                            for c in range(3)]) + 1e-9
            scale = float(np.mean(ref)) / ref
            for c in range(3):
                # gated: background (mask≈0) stays unscaled, nebula peak
                # (mask≈1) gets the full white-reference correction
                out[c] = out[c] * (1.0 + mask * (scale[c] - 1.0))
        out = np.clip(out, 0.0, 1.0)

        # --- pass 2: saturation + shadows/highlights polish ---
        if progress:
            progress("NebulaChrome: saturation & tone polish...", 0.6)
        Lp = luminance(out)
        sat_boost = 1.0 + 0.35 * mask  # gated: no boost on the background
        for c in range(3):
            out[c] = Lp + (out[c] - Lp) * sat_boost
        out = np.clip(out, 0.0, 1.0)
        weight = 1.0 - out
        out = np.clip(out + 0.12 * mask * weight * out, 0.0, 1.0)        # lift shadows (nebula only)
        weight = out
        out = np.clip(out - 0.06 * mask * weight * (1.0 - out), 0.0, 1.0)  # tame highlights (nebula only)

        # --- pass 3: deconvolution sharpen (recover nebula structure) ---
        if progress:
            progress("NebulaChrome: deconvolution sharpen...", 0.8)
        out = richardson_lucy_sharpen(out, sigma=1.7, iterations=8)

        # blend the full-strength result against the original
        if progress:
            progress("NebulaChrome: blending...", 0.95)
        strength = float(np.clip(strength, 0.0, 1.0))
        final = orig * (1.0 - strength) + out * strength
        return np.clip(final, 0.0, 1.0).astype(np.float32)

    def _exec_stage_palette(self, progress):
        progress("Palette: fetching image...", 0.05)
        before = self._get_current_image()
        if not (before.ndim == 3 and before.shape[0] == 3):
            raise RuntimeError("Hubble palette requires an RGB image "
                               "(mono images have no channels to remix).")
        source = before

        nebulachrome_mode = self.palette_mode_combo.currentIndex() == 1
        if nebulachrome_mode:
            preset = "NebulaChrome"
            strength = self.palette_nebulachrome_strength.value() / 100.0
            peak_gamma = self.palette_nebulachrome_peak.value() / 100.0
            after = self._palette_nebulachrome(source, strength, peak_gamma, progress)
        else:
            progress("Palette: extracting Hα / OIII...", 0.2)
            ha = source[0].astype(np.float32)
            oiii = (0.5 * source[1] + 0.5 * source[2]).astype(np.float32)

            if self.palette_linfit_checkbox.isChecked():
                progress("Palette: linear-fitting OIII to Hα...", 0.35)
                med_h = float(np.median(ha))
                mad_h = float(np.median(np.abs(ha - med_h))) + 1e-9
                med_o = float(np.median(oiii))
                mad_o = float(np.median(np.abs(oiii - med_o))) + 1e-9
                oiii = (oiii - med_o) * (mad_h / mad_o) + med_h
                oiii = np.clip(oiii, 0.0, 1.0)

            preset = self.palette_preset_combo.currentText()
            progress(f"Palette: mixing '{preset}'...", 0.6)
            after = np.zeros_like(before)
            for i, ch in enumerate(("R", "G", "B")):
                w_ha = self.palette_weights[ch][0].value()
                w_o = self.palette_weights[ch][1].value()
                after[i] = w_ha * ha + w_o * oiii
            after = np.clip(after, 0.0, 1.0).astype(np.float32)

        if self.palette_gimp_checkbox.isChecked():
            progress("Palette: GIMP replacement polish...", 0.85)
            g = self.palette_gimp_sliders
            after = self._gimp_replacement_polish(
                after,
                saturation=g["saturation"].value() / 100.0,
                shadows=g["shadows"].value() / 100.0,
                highlights=g["highlights"].value() / 100.0,
                contrast=g["contrast"].value() / 100.0,
                sharpen_amount=g["sharpen"].value() / 100.0 * 2.5,
                denoise_strength=g["denoise"].value() / 100.0,
                progress=progress)
            preset = f"{preset} + GIMP polish"

        self._set_current_image(after, f"AstroPipeline: palette {preset}")
        self._finish_stage(IDX_PAL, before, after,
                           "Palette: done.", f"Palette applied: {preset}",
                           progress=progress)
