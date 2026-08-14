"""VeraLux HyperMetric Stretch core (adapted from
VeraLux_HyperMetric_Stretch.py; extracted from S30Pro_Pipeline.py)."""

import numpy as np

from .constants import REC709_WEIGHTS

__all__ = [
    "VeraLuxCore", "adaptive_output_scaling", "apply_soft_clip",
    "veralux_stretch",
]

# =============================================================================
#  VERALUX CORE  (adapted from VeraLux_HyperMetric_Stretch.py)
# =============================================================================

class VeraLuxCore:

    @staticmethod
    def normalize_input(img_data):
        img_data = np.nan_to_num(img_data, nan=0.0, posinf=None, neginf=0.0)
        dtype = img_data.dtype
        f = img_data.astype(np.float32)
        if np.issubdtype(dtype, np.integer):
            if dtype == np.uint8:
                return f / 255.0
            if dtype == np.uint16:
                return f / 65535.0
            if dtype == np.int16:
                return f / 32767.0
            return f / 4294967295.0
        cur_max = float(np.max(img_data)) if img_data.size else 1.0
        if cur_max <= 1.1:
            return f
        if cur_max < 100000.0:
            return f / 65535.0
        return f / 4294967295.0

    @staticmethod
    def calculate_anchor(d):
        if d.ndim == 3 and d.shape[0] == 3:
            stride = max(1, d.size // 500000)
            floors = [np.percentile(d[c].flatten()[::stride], 0.5) for c in range(3)]
            return max(0.0, min(floors) - 0.00025)
        base = d[0] if (d.ndim == 3 and d.shape[0] == 1) else d
        stride = max(1, base.size // 200000)
        return max(0.0, np.percentile(base.flatten()[::stride], 0.5) - 0.00025)

    @staticmethod
    def calculate_anchor_adaptive(d, weights=None):
        if weights is None:
            weights = REC709_WEIGHTS
        if d.ndim == 3 and d.shape[0] == 3:
            r, g, b = weights
            base = r * d[0] + g * d[1] + b * d[2]
        elif d.ndim == 3 and d.shape[0] == 1:
            base = d[0]
        else:
            base = d
        stride = max(1, base.size // 2000000)
        sample = base.flatten()[::stride]
        hist, edges = np.histogram(sample, bins=65536, range=(0.0, 1.0))
        hs = np.convolve(hist, np.ones(50) / 50, mode="same")
        start = 100
        if np.max(hs[:start]) > 0:
            start = 0
        peak = int(np.argmax(hs[start:]) + start)
        target = float(hs[peak]) * 0.06
        cands = np.where(hs[:peak] < target)[0]
        anchor = edges[cands[-1]] if len(cands) else np.percentile(sample, 0.5)
        return max(0.0, anchor)

    @staticmethod
    def extract_luminance(d, anchor, weights):
        r, g, b = weights
        a = np.maximum(d - anchor, 0.0)
        if d.ndim == 3 and d.shape[0] == 3:
            L = r * a[0] + g * a[1] + b * a[2]
        elif d.ndim == 2 and d.shape[0] == 3:
            # Flattened RGB sample (3,N), e.g. from a subsampled solver —
            # same weighted-sum luminance, just without the H,W shape.
            L = r * a[0] + g * a[1] + b * a[2]
        elif d.ndim == 3 and d.shape[0] == 1:
            L = a[0]
            a = a[0]
        else:
            L = a
        return L, a

    @staticmethod
    def hyperbolic_stretch(data, D, b, SP=0.0):
        D, b = max(D, 0.1), max(b, 0.1)
        t1 = np.arcsinh(D * (data - SP) + b)
        t2 = np.arcsinh(b)
        nf = np.arcsinh(D * (1.0 - SP) + b) - t2
        if abs(nf) < 1e-12:
            nf = 1e-6
        return (t1 - t2) / nf

    @staticmethod
    def solve_log_d(luma_sample, target_median, b_val):
        med = np.median(luma_sample)
        if med < 1e-9:
            return 2.0
        lo, hi, best = 0.0, 7.0, 2.0
        for _ in range(40):
            mid = (lo + hi) / 2.0
            v = VeraLuxCore.hyperbolic_stretch(med, 10.0 ** mid, b_val)
            if abs(v - target_median) < 0.0001:
                best = mid
                break
            if v < target_median:
                lo = mid
            else:
                hi = mid
            best = mid
        return best

    @staticmethod
    def apply_mtf(data, m):
        t1 = (m - 1.0) * data
        t2 = (2.0 * m - 1.0) * data - m
        with np.errstate(divide="ignore", invalid="ignore"):
            r = t1 / t2
        return np.nan_to_num(r, nan=0.0, posinf=1.0, neginf=0.0)

    @staticmethod
    def apply_linear_expansion(data, factor):
        if factor <= 0.001:
            return data
        factor = float(np.clip(factor, 0.0, 1.0))
        abs_max = float(np.max(data))
        use_abs = False
        if abs_max > 0.001:
            idx = np.argmax(data)
            ym, xm = np.unravel_index(idx, data.shape)
            win = data[max(0, ym - 1):min(data.shape[0], ym + 2),
                       max(0, xm - 1):min(data.shape[1], xm + 2)]
            nb = win[win < abs_max]
            if nb.size > 0 and np.max(nb) >= abs_max * 0.20:
                use_abs = True
        stride = max(1, data.size // 500000)
        sample = data.flatten()[::stride]
        low = np.percentile(sample, 0.001)
        high = abs_max if use_abs else np.percentile(sample, 99.999)
        if high <= low:
            return data
        norm = np.clip((data - low) / (high - low), 0.0, 1.0)
        return data * (1.0 - factor) + norm * factor


RTU_PEDESTAL = 0.001
RTU_SOFT_CEIL_PERCENTILE = 99.0


def adaptive_output_scaling(img, weights, target_bg=0.20, progress=None):
    lr, lg, lb = weights
    is_rgb = img.ndim == 3 and img.shape[0] == 3
    L_raw = lr * img[0] + lg * img[1] + lb * img[2] if is_rgb else img
    med, std, mn = float(np.median(L_raw)), float(np.std(L_raw)), float(np.min(L_raw))
    floor = max(mn, med - 2.7 * std)
    abs_max = float(np.max(L_raw))
    valid_max = True
    if abs_max > 0.001:
        idx = np.argmax(L_raw)
        ym, xm = np.unravel_index(idx, L_raw.shape)
        win = L_raw[max(0, ym - 1):min(L_raw.shape[0], ym + 2),
                    max(0, xm - 1):min(L_raw.shape[1], xm + 2)]
        nb = win[win < abs_max]
        if nb.size > 0 and np.max(nb) < abs_max * 0.20:
            valid_max = False
    if is_rgb:
        stride = max(1, img[0].size // 500000)
        ceil = max(np.percentile(img[c].flatten()[::stride],
                                 RTU_SOFT_CEIL_PERCENTILE) for c in range(3))
    else:
        stride = max(1, L_raw.size // 200000)
        ceil = np.percentile(L_raw.flatten()[::stride], RTU_SOFT_CEIL_PERCENTILE)
    if ceil <= floor:
        ceil = floor + 1e-6
    if abs_max <= ceil:
        abs_max = ceil + 1e-6
    scale = (0.98 - RTU_PEDESTAL) / (ceil - floor + 1e-9)
    if valid_max:
        scale = min(scale, (1.0 - RTU_PEDESTAL) / (abs_max - floor + 1e-9))

    def expand(c):
        return np.clip((c - floor) * scale + RTU_PEDESTAL, 0.0, 1.0)

    if is_rgb:
        for i in range(3):
            img[i] = expand(img[i])
        L = lr * img[0] + lg * img[1] + lb * img[2]
    else:
        img = expand(L_raw)
        L = img
    bg = float(np.median(L))
    if 0.0 < bg < 1.0 and abs(bg - target_bg) > 1e-3:
        m = (bg * (target_bg - 1.0)) / (bg * (2.0 * target_bg - 1.0) - target_bg)
        if is_rgb:
            for i in range(3):
                img[i] = VeraLuxCore.apply_mtf(img[i], m)
        else:
            img = VeraLuxCore.apply_mtf(img, m)
    return img


def apply_soft_clip(img, threshold=0.98, rolloff=2.0):
    def sc(c):
        mask = c > threshold
        r = c.copy()
        if np.any(mask):
            t = np.clip((c[mask] - threshold) / (1.0 - threshold + 1e-9), 0.0, 1.0)
            r[mask] = threshold + (1.0 - threshold) * (1.0 - np.power(1.0 - t, rolloff))
        return np.clip(r, 0.0, 1.0)
    if img.ndim == 3:
        for i in range(img.shape[0]):
            img[i] = sc(img[i])
    else:
        img = sc(img)
    return img


def veralux_stretch(img_data, log_D, protect_b, convergence_power,
                    weights, processing_mode="ready_to_use", target_bg=0.20,
                    color_grip=1.0, shadow_convergence=0.0, linear_expansion=0.0,
                    use_adaptive_anchor=True, progress=None):
    if progress:
        progress("Stretch: normalization & analysis...", 0.05)
    img = VeraLuxCore.normalize_input(img_data)
    if img.ndim == 3 and img.shape[0] != 3 and img.shape[2] == 3:
        img = img.transpose(2, 0, 1)
    is_rgb = img.ndim == 3 and img.shape[0] == 3

    if use_adaptive_anchor:
        anchor = VeraLuxCore.calculate_anchor_adaptive(img, weights=weights)
    else:
        anchor = VeraLuxCore.calculate_anchor(img)

    if progress:
        progress("Stretch: extracting luminance...", 0.2)
    L_anch, img_anch = VeraLuxCore.extract_luminance(img, anchor, weights)
    eps = 1e-9
    L_safe = L_anch + eps
    if is_rgb:
        ratios = [img_anch[c] / L_safe for c in range(3)]

    if progress:
        progress(f"Stretch: applying IHS (log D={log_D:.2f})...", 0.4)
    L_str = np.clip(VeraLuxCore.hyperbolic_stretch(L_anch, 10.0 ** log_D, protect_b),
                    0.0, 1.0)

    if processing_mode != "ready_to_use" and float(linear_expansion) > 0.001:
        L_str = np.clip(VeraLuxCore.apply_linear_expansion(
            L_str, float(linear_expansion)), 0.0, 1.0)

    if progress:
        progress("Stretch: color convergence...", 0.6)
    if is_rgb:
        final = np.zeros_like(img)
        k = np.power(L_str, convergence_power)
        for c in range(3):
            final[c] = L_str * (ratios[c] * (1.0 - k) + k)
        needs_hybrid = (color_grip < 1.0) or (shadow_convergence > 0.01)
        if needs_hybrid:
            D_val = 10.0 ** log_D
            scalar = np.zeros_like(final)
            for c in range(3):
                scalar[c] = VeraLuxCore.hyperbolic_stretch(img_anch[c], D_val, protect_b)
            scalar = np.clip(scalar, 0.0, 1.0)
            grip = np.full_like(L_str, color_grip)
            if shadow_convergence > 0.01:
                grip = grip * np.power(L_str, shadow_convergence)
            final = final * grip + scalar * (1.0 - grip)
    else:
        final = L_str

    final = np.clip(final * (1.0 - 0.005) + 0.005, 0.0, 1.0).astype(np.float32)

    if processing_mode == "ready_to_use":
        if progress:
            progress("Stretch: adaptive output scaling...", 0.8)
        final = adaptive_output_scaling(final, weights, float(target_bg))
        final = apply_soft_clip(final, 0.98, 2.0)
    return final

