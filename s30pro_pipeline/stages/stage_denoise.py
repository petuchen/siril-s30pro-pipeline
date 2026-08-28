"""Denoise (GraXpert AI) stage mixin for UnifiedPipelineWindow.

Note: named `_build_stage3` / `_exec_stage3` in the original monolithic
class (a legacy numbering carried over from an earlier revision of the
pipeline) — this is the Denoise stage, distinct from Remove Stars
(`_build_stage_stars` / `_exec_stage_stars`, IDX_STARS) despite both
having "stage3"/"stars"-adjacent naming. Verified via IDX_DEN usage and
the "Denoise — GraXpert AI" box title before extracting.
"""

import numpy as np

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QCheckBox, QComboBox, QGridLayout, QHBoxLayout, QLabel, QSlider, QSpinBox

from sirilpy import LogColor

from s30pro_pipeline.constants import IDX_DEN
from s30pro_pipeline import graxpert_helpers
from s30pro_pipeline.graxpert_helpers import get_available_local_models, graxpert_denoise


class DenoiseMixin:
    def _build_stage3(self):
        box, v = self._stage_box(7, "Denoise — GraXpert AI")
        self.stage3_box = box

        g = QGridLayout()
        g.addWidget(QLabel("Model:"), 0, 0)
        self.denoise_model_combo = QComboBox()
        self.denoise_models = get_available_local_models("denoise-ai-models")
        self.denoise_model_combo.addItems(sorted(self.denoise_models.keys())
                                          or ["No models found"])
        self.denoise_model_combo.setToolTip(
            "Known issue on Mac: the 3.x denoise models (3.0.0/3.0.1/3.0.2)\n"
            "fail to compile under CoreML with an 'Espresso exception:\n"
            "Invalid blob shape' error, so GPU acceleration silently falls\n"
            "back to CPU for them (see the Denoise completion log). This is\n"
            "a bug in the 3.x model's ONNX export, not a setting here — see\n"
            "github.com/Steffenhir/GraXpert/issues/178. If you hit that on\n"
            "GPU acceleration, a 2.x model compiles and runs on GPU fine.")
        if self.denoise_models:
            self.denoise_model_combo.setCurrentIndex(
                self.denoise_model_combo.count() - 1)
        g.addWidget(self.denoise_model_combo, 0, 1)
        v.addLayout(g)

        st = QHBoxLayout()
        st.addWidget(QLabel("Strength:"))
        self.denoise_strength_slider = QSlider(Qt.Orientation.Horizontal)
        self.denoise_strength_slider.setRange(0, 100)
        self.denoise_strength_slider.setValue(80)
        st.addWidget(self.denoise_strength_slider)
        self.denoise_strength_label = QLabel("0.80")
        self.denoise_strength_slider.valueChanged.connect(
            lambda val: self.denoise_strength_label.setText(f"{val/100:.2f}"))
        st.addWidget(self.denoise_strength_label)
        v.addLayout(st)

        adv = QHBoxLayout()
        adv.addWidget(QLabel("Batch size:"))
        self.denoise_batch = QSpinBox()
        self.denoise_batch.setRange(1, 32)
        # GPU on by default → start with a saturating batch. There is no
        # per-core control for Apple GPU/ANE (CoreML schedules that itself);
        # batch size is the lever that keeps the accelerator busy — tiles
        # are tiny (~0.8 MB each), so even 32 is only ~25 MB.
        self.denoise_batch.setValue(16)
        self.denoise_batch.setToolTip(
            "Tiles processed per inference call. Larger batches keep the\n"
            "GPU / Apple Neural Engine saturated (the closest thing to\n"
            "'using all cores' — CoreML/CUDA schedule cores automatically).\n"
            "16–32 recommended with GPU acceleration; use 2–4 on CPU-only\n"
            "machines where large batches just add latency per tile.")
        adv.addWidget(self.denoise_batch)
        self.denoise_gpu = QCheckBox("GPU acceleration")
        self.denoise_gpu.setChecked(True)
        self.denoise_gpu.setToolTip(
            "Runs the AI model on the platform accelerator via ONNX Runtime:\n"
            "• Mac (Apple Silicon): CoreML — the model runs on the Apple GPU /\n"
            "  Neural Engine (ONNX has no 'MPS' provider; CoreML is Apple's\n"
            "  equivalent).\n"
            "• Windows/Linux: CUDA or DirectML if available.\n"
            "Falls back to CPU automatically; the Siril log shows which\n"
            "provider was actually used after each run.")
        # keep batch size sensible for the selected device: accelerators
        # want big batches (saturation), CPUs want small ones (latency)
        self.denoise_gpu.toggled.connect(
            lambda on: self.denoise_batch.setValue(16 if on else 4))
        adv.addWidget(self.denoise_gpu)
        adv.addStretch()
        v.addLayout(adv)

        row, self.stage3_run = self._run_row(
            lambda: self._launch([self._exec_stage3]), undo_stage=IDX_DEN)
        v.addLayout(row)
        return box

    def _exec_stage3(self, progress):
        model_name = self.denoise_model_combo.currentText()
        model_path = self.denoise_models.get(model_name)
        if not model_path:
            raise RuntimeError(
                "No GraXpert denoise model found. Download one via GraXpert "
                "or the GraXpert-AI script's Model Manager.")
        progress("Denoise: fetching image...", 0.02)
        before = self._get_current_image()
        denoised = graxpert_denoise(
            before.copy(), model_path,
            batch_size=self.denoise_batch.value(),
            gpu=self.denoise_gpu.isChecked(),
            progress=progress)
        strength = self.denoise_strength_slider.value() / 100.0
        after = denoised if strength >= 0.999 else \
            denoised * strength + before * (1.0 - strength)
        after = after.astype(np.float32)
        self._set_current_image(after, f"AstroPipeline: denoise {strength:.2f}")
        # GPU was requested but the run still ended up on CPU: this used to
        # be a silent fallback with no way to tell whether an accelerator
        # was even attempted. Surface whatever diagnostics
        # graxpert_helpers.make_onnx_session() recorded, since on Mac this
        # is a known onnxruntime/CoreML reliability issue (not something
        # this plugin controls), and the actual reason — an exception vs.
        # sirilpy not offering a GPU provider at all vs. a cached decision
        # in Siril's own onnx config — points to a different next step.
        provider = graxpert_helpers.LAST_ONNX_PROVIDER
        if self.denoise_gpu.isChecked() and provider == "CPUExecutionProvider":
            requested = graxpert_helpers.LAST_ONNX_REQUESTED_PROVIDERS
            err = graxpert_helpers.LAST_ONNX_FALLBACK_ERROR
            if err:
                if "Espresso exception" in err and "Invalid blob shape" in err:
                    # Confirmed match against a known upstream bug: the 3.x
                    # denoise models' ONNX export doesn't compile under
                    # CoreML on Mac at all (same error, same tensor shapes,
                    # reported against GraXpert's own desktop app —
                    # github.com/Steffenhir/GraXpert/issues/178). Not
                    # something this plugin or its settings can work
                    # around; a 2.x model is reported to compile and run
                    # on GPU fine.
                    self.siril.log(
                        f"Denoise: GPU acceleration failed because the "
                        f"selected model doesn't compile under CoreML on "
                        f"Mac (known bug in the 3.x denoise models' ONNX "
                        f"export — see github.com/Steffenhir/GraXpert/"
                        f"issues/178). Fell back to CPU. Try a 2.x model "
                        f"instead if you want GPU acceleration.",
                        LogColor.SALMON)
                else:
                    self.siril.log(
                        f"Denoise: GPU acceleration was requested but "
                        f"creating the ONNX session with {requested} "
                        f"failed, so it fell back to CPU. Error: {err}",
                        LogColor.SALMON)
            elif requested and requested != ["CPUExecutionProvider"]:
                self.siril.log(
                    f"Denoise: GPU acceleration was requested and "
                    f"{requested} was attempted with no error, but the "
                    f"session still reports CPUExecutionProvider as active. "
                    f"sirilpy may have a cached provider decision — see "
                    f"siril_onnx.conf in Siril's config folder.",
                    LogColor.SALMON)
            else:
                self.siril.log(
                    "Denoise: GPU acceleration was requested but sirilpy "
                    "did not offer a GPU provider for this platform/model, "
                    "so it ran on CPU.", LogColor.SALMON)
        self._finish_stage(
            IDX_DEN, before, after, "Denoise: done.",
            f"Denoising complete (execution provider: {provider})",
            progress=progress)
