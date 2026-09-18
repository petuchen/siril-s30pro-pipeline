"""Remove Stars (StarNet) stage mixin for UnifiedPipelineWindow.

Also owns the "held stars" hand-off mechanism used by the Stretch stage
(`_reconcile_held_stars`, `_manual_readd_stars`) — these operate on
`self.held_stars` / `self.palette_star_cache`, state that is only ever
populated by `_exec_stage_stars` below, so they stay grouped with this
stage even though `_reconcile_held_stars` is called from other stages
(Touch, Hist) as a safety-net fallback if Stretch hasn't run yet.
"""

import os
import math
import hashlib

import numpy as np

from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QPushButton

import sirilpy as s
from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_STARS


class StarsMixin:
    def _build_stage_stars(self):
        # Title stays literal English for now — stage titles move
        # together in Phase 7 (see stage_watermark.py's comment).
        box, v = self._stage_box(6, "Remove Stars (StarNet)",
                                 enabled_check=False)
        self.stage_stars_box = box

        self.stars_info_label = QLabel(self.tr("stars_info"))
        self.stars_info_label.setObjectName("SubHeader")
        self.stars_info_label.setWordWrap(True)
        v.addWidget(self.stars_info_label)

        srow = QHBoxLayout()
        srow.setSpacing(10)
        self.stars_strength_row_label = QLabel(self.tr("stars_strength_label"))
        srow.addWidget(self.stars_strength_row_label)
        self.star_strength_spin = QDoubleSpinBox()
        self.star_strength_spin.setRange(0.0, 1.0)
        self.star_strength_spin.setSingleStep(0.05)
        self.star_strength_spin.setValue(1.0)
        self.star_strength_spin.setToolTip(self.tr("stars_strength_tooltip"))
        srow.addWidget(self.star_strength_spin)
        self.stars_asinh_row_label = QLabel(self.tr("stars_asinh_label"))
        srow.addWidget(self.stars_asinh_row_label)
        self.star_asinh_spin = QDoubleSpinBox()
        self.star_asinh_spin.setRange(1.0, 100.0)
        self.star_asinh_spin.setSingleStep(0.5)
        self.star_asinh_spin.setValue(8.0)
        self.star_asinh_spin.setToolTip(self.tr("stars_asinh_tooltip"))
        srow.addWidget(self.star_asinh_spin)
        srow.addStretch()
        v.addLayout(srow)

        self.stars_cache_label = QLabel(self.tr("stars_cache_label_default"))
        self.stars_cache_label.setObjectName("SubHeader")
        self.stars_cache_label.setWordWrap(True)
        v.addWidget(self.stars_cache_label)

        manual_row = QHBoxLayout()
        manual_row.setSpacing(10)
        self.manual_readd_stars_btn = QPushButton(self.tr("stars_manual_btn"))
        self.manual_readd_stars_btn.setToolTip(self.tr("stars_manual_tooltip"))
        self.manual_readd_stars_btn.clicked.connect(
            lambda: self._launch([self._manual_readd_stars]))
        manual_row.addWidget(self.manual_readd_stars_btn)
        manual_row.addStretch()
        v.addLayout(manual_row)

        row, self.stage_stars_run = self._run_row(
            lambda: self._launch([self._exec_stage_stars]),
            undo_stage=IDX_STARS)
        v.addLayout(row)
        return box

    def retranslate_ui_stars(self):
        self.stars_info_label.setText(self.tr("stars_info"))
        self.stars_strength_row_label.setText(self.tr("stars_strength_label"))
        self.star_strength_spin.setToolTip(self.tr("stars_strength_tooltip"))
        self.stars_asinh_row_label.setText(self.tr("stars_asinh_label"))
        self.star_asinh_spin.setToolTip(self.tr("stars_asinh_tooltip"))
        # stars_cache_label holds transient, state-dependent text — see
        # _stars_cache_state, set alongside every place this label's
        # text changes (default / reused-from-cache / freshly-cached).
        state = getattr(self, "_stars_cache_state", "default")
        self.stars_cache_label.setText(self.tr({
            "default": "stars_cache_label_default",
            "reused": "stars_cache_reused",
            "cached": "stars_cache_saved",
        }[state]))
        self.manual_readd_stars_btn.setText(self.tr("stars_manual_btn"))
        self.manual_readd_stars_btn.setToolTip(self.tr("stars_manual_tooltip"))

    @staticmethod
    def _array_fingerprint(arr):
        """Cheap, fast fingerprint of a numpy array's contents — used to
        detect whether the image feeding the palette stage has actually
        changed (so cached StarNet results can be safely reused)."""
        if arr.ndim == 3:
            sample = np.ascontiguousarray(arr[:, ::37, ::37])
        else:
            sample = np.ascontiguousarray(arr[::37, ::37])
        h = hashlib.md5(sample.tobytes()).hexdigest()
        return f"{arr.shape}_{arr.dtype}_{h}"

    def _exec_stage_stars(self, progress):
        """Standalone star removal (StarNet), run before Denoise.

        The removed star layer is held in memory (and cached to disk,
        fingerprinted against the source image) — the Stretch stage
        stretches it separately with a gentle asinh and recombines it at
        the end; every later stage has a fallback re-add, plus the manual
        '⭐ Add Stars Back Now' button.
        """
        progress(self.tr("stars_progress_fetching"), 0.05)
        before = self._get_current_image()

        fp = self._array_fingerprint(before)
        cache = self.palette_star_cache
        if (cache.get("fingerprint") == fp
                and cache.get("starless_path")
                and os.path.isfile(cache["starless_path"])
                and os.path.isfile(cache["stars_path"])):
            progress(self.tr("stars_progress_reusing"), 0.3)
            starless = np.load(cache["starless_path"])
            stars = np.load(cache["stars_path"])
            self.siril.log("Remove stars: reused cached StarNet result "
                           "(source image unchanged)", LogColor.BLUE)
            self._stars_cache_state = "reused"
            self.palette_cache_updated.emit(self.tr("stars_cache_reused"))
            # cache path skips StarNet, so push the starless image ourselves
            self._set_current_image(starless, "AstroPipeline: remove stars")
        else:
            progress(self.tr("stars_progress_running"), 0.1)
            try:
                self.siril.cmd("starnet", "-stretch", "-nostarmask")
            except (s.DataError, s.CommandError, s.SirilError) as e:
                raise RuntimeError(
                    self.tr("stars_error_starnet_failed").format(e=e))
            starless = self._get_current_image()
            if starless.shape != before.shape:
                raise RuntimeError(self.tr("stars_error_size_mismatch"))
            stars = np.clip(before - starless, 0.0, 1.0)
            progress(self.tr("stars_progress_caching"), 0.8)
            starless_path = os.path.join(self._temp_dir, "stars_starless.npy")
            stars_path = os.path.join(self._temp_dir, "stars_layer.npy")
            np.save(starless_path, starless)
            np.save(stars_path, stars)
            self.palette_star_cache = {
                "fingerprint": fp, "starless_path": starless_path,
                "stars_path": stars_path,
            }
            self._stars_cache_state = "cached"
            self.palette_cache_updated.emit(self.tr("stars_cache_saved"))

        self.held_stars = stars
        self.stage_backups[IDX_STARS] = before
        self.snapshots_raw_after[IDX_STARS] = starless
        self._store_snapshot(IDX_STARS, before, starless, True, True)
        progress("Remove stars: done — star layer held.", 1.0)
        self.siril.log(
            "Stars removed and held — they will be stretched separately and "
            "recombined at the end of the Stretch stage (or use '⭐ Add "
            "Stars Back Now' anytime).", LogColor.GREEN)

    def _reconcile_held_stars(self, arr, progress=None):
        """Safety net for every stage *after* Stretch.

        The Palette stage's "hold stars until after stretch" option is meant
        to be consumed by the Stretch stage (which stretches the stars
        separately with a gentle asinh curve). But if Stretch is left
        unchecked, skipped, or the user jumps straight to a later stage,
        that hand-off never happens and the stars would otherwise vanish
        from the final image with no explanation. This re-adds them here
        with a plain screen blend (the same recombination used when "hold
        stars" is off) so they are never silently lost — just less
        optimally stretched than if Stretch had done it.

        Returns (array, changed) — changed is True if stars were re-added.
        """
        held = getattr(self, "held_stars", None)
        if held is None:
            return arr, False
        self.held_stars = None  # consume it — never re-applied twice
        if held.shape != arr.shape:
            self.siril.log(
                "Remove Stars held back a star layer for the Stretch stage, "
                "but its size no longer matches the current image (probably a "
                "stage was re-run out of order) — could not re-add the "
                "stars automatically. Re-run the Remove Stars stage to "
                "re-capture them at the current size.", LogColor.SALMON)
            return arr, False
        strength = self.star_strength_spin.value()
        if strength <= 0.001:
            return arr, False
        if progress:
            progress(self.tr("stars_reconcile_progress"), 0.02)
        self.siril.log(
            "Stretch stage hasn't run yet — re-adding the stars held back "
            "by the Palette stage now as a fallback, using the same gentle "
            "asinh stretch the Stretch stage would have applied, so they "
            "aren't lost (and aren't left looking too faint).",
            LogColor.SALMON)
        k = self.star_asinh_spin.value()
        stars_str = np.arcsinh(k * np.clip(held, 0.0, 1.0)) / math.asinh(k)
        stars_str = np.clip(stars_str, 0.0, 1.0)
        out = 1.0 - (1.0 - arr) * (1.0 - stars_str * strength)
        return np.clip(out, 0.0, 1.0).astype(np.float32), True

    def _manual_readd_stars(self, progress):
        """'⭐ Add Stars Back Now' — manual safety valve.

        Blends the saved star layer onto whatever image is currently loaded
        in Siril, independent of stage order or the automatic hand-off.
        Looks first at the in-memory held_stars buffer (freshest), then
        falls back to the star layer StarNet cached to disk on the last run
        (persists even if 'hold stars' was off, or the buffer was already
        consumed by some other stage). Use this any time stars are missing
        from the current image and the automatic recombination didn't do it.
        """
        progress(self.tr("stars_manual_progress_looking"), 0.1)
        stars = getattr(self, "held_stars", None)
        source_desc = "held from the last Remove Stars run"
        if stars is None:
            cache = getattr(self, "palette_star_cache", {}) or {}
            stars_path = cache.get("stars_path")
            if stars_path and os.path.isfile(stars_path):
                stars = np.load(stars_path)
                source_desc = "star layer cached to disk from the last StarNet run"
        if stars is None:
            raise RuntimeError(self.tr("stars_error_no_layer"))

        before = self._get_current_image()
        if stars.shape != before.shape:
            raise RuntimeError(self.tr("stars_error_shape_mismatch").format(
                shape1=stars.shape, shape2=before.shape))

        strength = self.star_strength_spin.value()
        if strength <= 0.001:
            raise RuntimeError(self.tr("stars_error_zero_strength"))

        progress(self.tr("stars_manual_progress_blending"), 0.5)
        # The saved star layer is the raw, linear (unstretched) residual
        # StarNet split off — tiny pixel values next to an already-stretched
        # final image, so blending it in directly used to look barely
        # visible. Apply the same gentle asinh stretch the Stretch stage
        # itself uses (via the Remove Stars panel's asinh-strength slider)
        # so stars actually look like stars regardless of how far along the
        # pipeline the current image is.
        k = self.star_asinh_spin.value()
        stars_str = np.arcsinh(k * np.clip(stars, 0.0, 1.0)) / math.asinh(k)
        stars_str = np.clip(stars_str, 0.0, 1.0)
        after = 1.0 - (1.0 - before) * (1.0 - stars_str * strength)
        after = np.clip(after, 0.0, 1.0).astype(np.float32)
        self._set_current_image(after, "AstroPipeline: stars added back (manual)")
        self.held_stars = None  # consumed — avoid a later stage adding them again

        # Update the before/after preview for whatever stage is currently
        # shown — this button changes Siril's actual image data, but unlike
        # every stage's own _exec_stage_* function it has no snapshot slot
        # of its own, so without this the change was real but invisible in
        # the preview panel until you switched stages or reloaded.
        idx = self.preview_stage_combo.currentIndex()
        self._store_snapshot(idx, before, after, True, True)

        progress(self.tr("stars_manual_progress_done"), 1.0)
        self.siril.log(
            f"Stars added back manually ({source_desc}, "
            f"strength {strength:.2f})", LogColor.GREEN)
