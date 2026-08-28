"""GraXpert AI model discovery, background extraction, denoise,
and Richardson-Lucy deconvolution sharpen (extracted from
S30Pro_Pipeline.py)."""

import os
import copy
import numpy as np
import cv2
import sirilpy as s
import onnxruntime
from appdirs import user_data_dir
from skimage.restoration import richardson_lucy as _skimage_richardson_lucy

# Own ONNXHelper instance -- separate from the main script's, so it gets
# its own install_onnxruntime() call too (idempotent -- the main script's
# header already triggered the actual pip-level install; this just makes
# sure this instance's own setup runs regardless of whether ONNXHelper
# keeps any state on the instance vs. system-wide).
onnx_helper = s.ONNXHelper()
onnx_helper.install_onnxruntime()

__all__ = [
    "get_available_local_models", "make_onnx_session", "gaussian_kernel",
    "_make_gaussian_psf", "richardson_lucy_sharpen",
    "graxpert_extract_background", "graxpert_apply_correction",
    "graxpert_denoise", "LAST_ONNX_PROVIDER",
    "LAST_ONNX_REQUESTED_PROVIDERS", "LAST_ONNX_FALLBACK_ERROR",
]


def get_available_local_models(subdir):
    """Return {model_name: model.onnx path} from the GraXpert data dir."""
    models_dir = os.path.join(user_data_dir(appname="GraXpert"), subdir)
    model_paths = {}
    if os.path.isdir(models_dir):
        for sub in sorted(os.listdir(models_dir)):
            p = os.path.join(models_dir, sub, "model.onnx")
            if os.path.isfile(p):
                model_paths[sub] = p
    return model_paths


LAST_ONNX_PROVIDER = "unknown"
# Diagnostics for "GPU was requested but the run used CPU" reports — see
# stage_denoise.py's completion log, which surfaces these when that
# mismatch happens. Previously this fell back to CPU silently on any
# exception, with no way to tell whether the accelerator was never
# offered, was offered and failed, or was accepted but not actually used.
LAST_ONNX_REQUESTED_PROVIDERS = []
LAST_ONNX_FALLBACK_ERROR = None


def make_onnx_session(ai_path, gpu):
    """Create an ONNX session, preferring the platform's accelerator.

    'GPU' here means whatever the platform offers through ONNX Runtime:
    CUDA/DirectML on PC, and on Apple Silicon the CoreML Execution
    Provider — which runs the model on the Mac's GPU / Neural Engine
    (ONNX Runtime has no 'MPS' provider; CoreML is the Apple equivalent).
    sirilpy's ONNXHelper installs the right onnxruntime build and orders
    the providers accordingly; we record which one actually got used so
    the log can show it.
    """
    global LAST_ONNX_PROVIDER, LAST_ONNX_REQUESTED_PROVIDERS, \
        LAST_ONNX_FALLBACK_ERROR
    LAST_ONNX_FALLBACK_ERROR = None
    with s.SuppressedStderr():
        providers = onnx_helper.get_execution_providers_ordered(gpu)
        LAST_ONNX_REQUESTED_PROVIDERS = list(providers)
        try:
            sess = onnxruntime.InferenceSession(ai_path, providers=providers)
        except Exception as e:
            LAST_ONNX_FALLBACK_ERROR = str(e)
            sess = onnxruntime.InferenceSession(
                ai_path, providers=["CPUExecutionProvider"])
    try:
        LAST_ONNX_PROVIDER = sess.get_providers()[0]
    except Exception:
        LAST_ONNX_PROVIDER = "unknown"
    return sess

# =============================================================================
#  GRAXPERT BACKGROUND EXTRACTION  (adapted from GraXpert-AI.py)
# =============================================================================

def gaussian_kernel(sigma):
    size = int(8.0 * sigma + 1.0)
    if size % 2 == 0:
        size += 1
    return (size, size)


# =============================================================================
#  RICHARDSON-LUCY DECONVOLUTION SHARPEN  (Final Touch stage, deconvolution
#  mode — same technique AstroSharp/PixInsight deconvolution use: estimate
#  the blur PSF and invert it, instead of just boosting edge contrast the
#  way Unsharp Mask does)
# =============================================================================

def _make_gaussian_psf(size=15, sigma=2.0):
    ax = np.arange(-(size // 2), size // 2 + 1, dtype=np.float32)
    xx, yy = np.meshgrid(ax, ax)
    psf = np.exp(-(xx ** 2 + yy ** 2) / (2 * sigma ** 2))
    return (psf / psf.sum()).astype(np.float32)


def richardson_lucy_sharpen(img, sigma=1.8, iterations=15, psf_size=15):
    """Deconvolution-based sharpening. img: planar (3,h,w) or mono (h,w)
    float 0..1. Returns same shape/dtype. More iterations = more
    aggressive sharpening (and more ringing risk on noisy data), mirroring
    AstroSharp's aggressiveness slider."""
    psf = _make_gaussian_psf(psf_size, sigma)
    iterations = max(1, int(iterations))

    def _rl_channel(chan):
        chan = np.clip(chan.astype(np.float32), 1e-6, 1.0)
        return _skimage_richardson_lucy(chan, psf, num_iter=iterations, clip=False)

    if img.ndim == 3 and img.shape[0] == 3:
        out = np.stack([_rl_channel(img[c]) for c in range(3)], axis=0)
    else:
        out = _rl_channel(img)
    return np.clip(out, 0.0, 1.0).astype(np.float32)


def graxpert_extract_background(image, ai_path, smoothing=0.5, progress=None):
    """image: float32 (h,w,c)-agnostic; accepts planar. Returns background."""
    was_mono = False
    if image.ndim == 2:
        was_mono = True
        image = np.expand_dims(image, -1)
    was_planar = False
    if image.shape[0] < 4 and image.ndim == 3 and image.shape[0] < image.shape[1] \
            and image.shape[0] < image.shape[2]:
        was_planar = True
        image = np.transpose(image, (1, 2, 0))

    original_shape = image.shape
    num_colors = image.shape[-1]
    if num_colors == 1:
        was_mono = True
    padding = 8
    if progress:
        progress("BG: preparing image...", 0.05)
    small = cv2.resize(image, dsize=(256 - 2 * padding, 256 - 2 * padding),
                       interpolation=cv2.INTER_LINEAR)
    if small.ndim == 2:
        small = np.expand_dims(small, -1)
    small = np.pad(small, ((padding, padding), (padding, padding), (0, 0)), mode="edge")

    median, mad = [], []
    for c in range(num_colors):
        median.append(np.median(small[:, :, c]))
        mad.append(np.median(np.abs(small[:, :, c] - median[c])))

    small = (small - median) / mad * 0.04
    small = np.clip(small, -1.0, 1.0)
    if num_colors == 1:
        small = np.moveaxis(np.array([small[:, :, 0]] * 3), 0, -1)

    if progress:
        progress("BG: running AI inference...", 0.35)
    session = make_onnx_session(ai_path, gpu=False)  # CPU: fast & robust for BGE
    background, session = onnx_helper.run(
        session, ai_path, None, {"gen_input_image": np.expand_dims(small, axis=0)})
    background = background[0][0]

    if progress:
        progress("BG: post-processing...", 0.7)
    background = background / 0.04 * mad + median
    if smoothing != 0:
        sig = smoothing * 20
        background = cv2.GaussianBlur(background, ksize=gaussian_kernel(sig),
                                      sigmaX=sig, sigmaY=sig)
    if padding != 0:
        background = background[padding:-padding, padding:-padding, :]
    sig = 3.0
    background = cv2.GaussianBlur(background, ksize=gaussian_kernel(sig),
                                  sigmaX=sig, sigmaY=sig)
    background = cv2.resize(background, dsize=(original_shape[1], original_shape[0]),
                            interpolation=cv2.INTER_LINEAR)

    if was_mono and background.ndim == 3:
        background = background[:, :, 0]
    elif background.ndim == 2 and len(original_shape) == 3:
        background = np.expand_dims(background, -1)
    if was_planar:
        if background.ndim == 2:
            background = np.expand_dims(background, 0)
        else:
            background = np.transpose(background, (2, 0, 1))
    return background


def graxpert_apply_correction(image, background, correction_type="subtraction"):
    corrected = copy.deepcopy(image)
    if correction_type == "subtraction":
        corrected = corrected - background + np.mean(background)
    else:  # division
        num_colors = 3 if corrected.ndim > 2 else 1
        if num_colors == 1:
            corrected = corrected / background * np.mean(corrected)
        else:
            for c in range(num_colors):
                corrected[c] = corrected[c] / background[c] * np.mean(corrected[c])
    return np.clip(corrected, 0.0, 1.0)



def graxpert_denoise(image, ai_path, batch_size=4, gpu=True,
                     window_size=256, stride=128, progress=None):
    """image: float32 planar or hwc, values 0..1. Returns denoised (same layout)."""
    if image.shape[0] < image.shape[1] and image.shape[0] <= 4:
        image = np.transpose(image, (1, 2, 0))
        planar = True
    else:
        planar = False

    batch_size = int(np.clip(batch_size, 1, 32))
    if batch_size & (batch_size - 1) != 0:
        batch_size = 2 ** batch_size.bit_length() // 2

    median = np.median(image[::4, ::4, :], axis=[0, 1])
    mad = np.median(np.abs(image[::4, ::4, :] - median), axis=[0, 1])
    model_threshold = 1.0 if ("1.0.0" in ai_path or "1.1.0" in ai_path) else 10.0

    num_colors = image.shape[-1]
    if num_colors == 1:
        image = np.moveaxis(np.array([image[:, :, 0]] * 3), 0, -1)

    H, W, _ = image.shape
    offset = int((window_size - stride) / 2)
    h, w, _ = image.shape
    ith, itw = int(h / stride) + 1, int(w / stride) + 1
    dh, dw = ith * stride - h, itw * stride - w
    image = np.concatenate((image, image[(h - dh):, :, :]), axis=0)
    image = np.concatenate((image, image[:, (w - dw):, :]), axis=1)
    h, w, _ = image.shape
    image = np.concatenate((image, image[(h - offset):, :, :]), axis=0)
    image = np.concatenate((image[:offset, :, :], image), axis=0)
    image = np.concatenate((image, image[:, (w - offset):, :]), axis=1)
    image = np.concatenate((image[:, :offset, :], image), axis=1)

    output = copy.deepcopy(image)
    session = make_onnx_session(ai_path, gpu)
    last_p = 0

    for b in range(0, ith * itw + batch_size, batch_size):
        tiles, tile_copies = [], []
        for t_idx in range(batch_size):
            index = b + t_idx
            i, j = index % ith, index // ith
            if i >= ith or j >= itw:
                break
            x, y = stride * i, stride * j
            tile = image[x:x + window_size, y:y + window_size, :]
            tile = (tile - median) / mad * 0.04
            tile_copies.append(np.copy(tile))
            tiles.append(np.clip(tile, -model_threshold, model_threshold))
        if not tiles:
            continue
        tiles = np.array(tiles)
        result, session = onnx_helper.run(session, ai_path, None,
                                          {"gen_input_image": tiles},
                                          return_first_output=True)
        out_tiles = np.array(list(result))
        for t_idx, tile in enumerate(out_tiles):
            index = b + t_idx
            i, j = index % ith, index // ith
            if i >= ith or j >= itw:
                break
            x, y = stride * i, stride * j
            tile = np.where(tile_copies[t_idx] < model_threshold, tile,
                            tile_copies[t_idx])
            tile = tile / 0.04 * mad + median
            tile = tile[offset:offset + stride, offset:offset + stride, :]
            output[x + offset:stride * (i + 1) + offset,
                   y + offset:stride * (j + 1) + offset, :] = tile
        p = int(b / (ith * itw + batch_size) * 100)
        if p > last_p and progress:
            progress(f"Denoise: {p}%", p / 100)
            last_p = p

    output = output[offset:H + offset, offset:W + offset, :]
    if num_colors == 1:
        output = np.moveaxis(np.array([output[:, :, 0]]), 0, -1)
    if planar:
        output = np.transpose(output, (2, 0, 1))
    return output

