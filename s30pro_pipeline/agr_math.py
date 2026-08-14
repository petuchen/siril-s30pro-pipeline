"""Auto Gradient Removal number-crunching (adapted from
AutoGradientRemoval.py; extracted from S30Pro_Pipeline.py)."""

import threading
import concurrent.futures
import numpy as np
import cv2

__all__ = [
    "agr_box1d", "agr_lowpass", "agr_mad_sigma", "agr_poly_basis",
    "agr_poly_fit", "agr_inpaint_lowpass", "agr_structure_mask",
    "agr_estimate_background", "agr_downsample", "agr_resize_bilinear",
    "agr_correct_channel", "agr_correct_image",
]

# =============================================================================
#  AUTO GRADIENT REMOVAL  (adapted from AutoGradientRemoval.py, Cyril
#  Richard 2026 — Siril's own automatic background/gradient correction
#  script, ported here as its own pipeline stage). Places no sample
#  points: the background is fitted on every pixel that survives an
#  iterative robust rejection of structures (stars, nebulae, galaxies).
#  Pure numpy, no AI model/GPU needed — a lighter-weight alternative to
#  GraXpert AI and a fully automatic alternative to Siril subsky's
#  sample-point placement, for whenever either of those isn't ideal.
# =============================================================================

def agr_box1d(a, r, axis):
    """One separable box blur of radius r along `axis`, via running sums."""
    if r < 1:
        return a
    n = a.shape[axis]
    w = 2 * r + 1
    pad = [(0, 0)] * a.ndim
    pad[axis] = (r, r)
    ap = np.pad(a, pad, mode="edge")
    cs = np.cumsum(ap, axis=axis)
    z = np.zeros_like(np.take(cs, [0], axis=axis))
    cs = np.concatenate([z, cs], axis=axis)
    hi = [slice(None)] * a.ndim; hi[axis] = slice(w, w + n)
    lo = [slice(None)] * a.ndim; lo[axis] = slice(0, n)
    return (cs[tuple(hi)] - cs[tuple(lo)]) / w


def agr_lowpass(img, r, passes=3):
    """Gaussian-like separable low-pass = `passes` box blurs."""
    a = img.astype(np.float64, copy=False)   # agr_box1d returns fresh arrays anyway
    for _ in range(passes):
        a = agr_box1d(a, r, axis=1)
        a = agr_box1d(a, r, axis=0)
    return a


def agr_mad_sigma(x):
    """Robust (median, sigma) from the Median Absolute Deviation."""
    med = np.median(x)
    mad = np.median(np.abs(x - med))
    return med, 1.4826 * mad + 1e-12


def agr_poly_basis(h, w, degree):
    """Tensor polynomial basis terms x^i*y^j (i+j<=degree) on [-1,1]^2."""
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    xn = xx / max(1, w - 1) * 2.0 - 1.0
    yn = yy / max(1, h - 1) * 2.0 - 1.0
    terms = []
    for i in range(degree + 1):
        for j in range(degree + 1 - i):
            terms.append((xn ** i) * (yn ** j))
    return terms


def agr_poly_fit(ch, mask, terms):
    """Least-squares fit of the polynomial basis over masked pixels."""
    A = np.stack([t[mask] for t in terms], axis=1)
    b = ch[mask]
    coef, *_ = np.linalg.lstsq(A, b, rcond=None)
    model = np.zeros(ch.shape, dtype=np.float64)
    for c, t in zip(coef, terms):
        model += c * t
    return model


def agr_inpaint_lowpass(img, mask, radius, n_fill=10, passes=2):
    """Robust smooth fill that bridges arbitrarily large rejected holes.

    Harmonic-style inpainting: repeatedly low-pass then restore the kept
    pixels. Each pass diffuses background ~radius into the holes, so n_fill
    passes bridge holes up to ~n_fill*radius wide -- unlike a single
    normalized convolution which collapses to ~0 inside big holes.
    """
    if not mask.any():
        return np.zeros(img.shape, dtype=np.float64)
    if mask.all():                       # no holes: the fill loop is a no-op
        return agr_lowpass(img, radius, passes)
    known_mean = float(img[mask].mean())
    filled = np.where(mask, img, known_mean).astype(np.float64)
    for _ in range(n_fill):
        sm = agr_lowpass(filled, radius, passes)
        filled = np.where(mask, img, sm)
    return agr_lowpass(filled, radius, passes)


def agr_structure_mask(residual, model_radius, protect_threshold, protect_amount):
    """Spatially-coherent mask of EXTENDED bright structures to protect.

    Detect pixels brighter than the model by > protect_threshold, then grow
    the detection so the whole structure (with its dim wings) is covered.
    Returns True where a structure is to be excluded from the fit.
    """
    det = (residual > protect_threshold).astype(np.float64)
    if det.max() == 0:
        return np.zeros(residual.shape, dtype=bool)
    grow_r = max(1, int(round(model_radius * (0.5 + protect_amount))))
    grown = agr_lowpass(det, grow_r, passes=2)
    cutoff = (1.0 - protect_amount) * 0.5 + 1e-3
    return grown > cutoff


def agr_estimate_background(ch, radius, smoothness=0.4, high_k=2.0, low_k=4.0,
                            protect=True, protect_threshold=0.05, protect_amount=0.5,
                            simplified=False, degree=2, n_iter=20, passes=3,
                            log=print):
    """Iterative background model for one 2D channel.

    Default: multiscale smooth surface fitted on the background pixels, with
    structure protection. simplified=True swaps it for a stiff polynomial of
    the given degree (the simplified model, best for nebulae that fill the
    frame). Common to both: robust high/low rejection + convergence.
    """
    radius = max(1, int(round(radius)))
    terms = agr_poly_basis(ch.shape[0], ch.shape[1], degree) if simplified else None

    def fit(keep):
        if simplified:
            return agr_poly_fit(ch, keep, terms)
        return agr_inpaint_lowpass(ch, keep, radius, passes=passes)

    keep = np.ones(ch.shape, dtype=bool)
    model = fit(keep)
    prev = keep.sum()
    min_keep = max(16, int(0.02 * keep.size))

    for it in range(n_iter):
        residual = ch - model
        ref = residual[keep] if keep.any() else residual.ravel()
        med, sigma = agr_mad_sigma(ref)
        new_keep = (residual <= med + high_k * sigma) & \
                   (residual >= med - low_k * sigma)
        if protect:
            struct = agr_structure_mask(residual - med, radius,
                                        protect_threshold, protect_amount)
            new_keep &= ~struct
        if new_keep.sum() < min_keep:            # never empty the fit set
            thr = np.percentile(residual, 100 * min_keep / residual.size)
            new_keep = residual <= thr
        model = fit(new_keep)

        kept = int(new_keep.sum())
        change = abs(kept - prev) / keep.size
        log(f"  iteration {it + 1}: {100 * kept / keep.size:.1f}% kept")
        keep = new_keep
        prev = kept
        if it > 0 and change < 1e-4:
            log("  converged")
            break
    else:
        log("  maximum iterations reached")

    if smoothness > 0:
        model = agr_lowpass(model, max(1, int(round(radius * smoothness))), passes)
    return model


def agr_downsample(img, f):
    """Area-average downsample by integer factor f (block mean)."""
    if f <= 1:
        return img.astype(np.float64, copy=True)
    h, w = img.shape
    hh, ww = (h // f) * f, (w // f) * f
    return img[:hh, :ww].reshape(hh // f, f, ww // f, f).mean(axis=(1, 3))


def agr_resize_bilinear(img, oh, ow):
    """Bilinear resize of a 2D array to (oh, ow)."""
    h, w = img.shape
    if (h, w) == (oh, ow):
        return img.astype(np.float64, copy=True)
    ys = np.linspace(0, h - 1, oh)
    xs = np.linspace(0, w - 1, ow)
    y0 = np.floor(ys).astype(int); y1 = np.minimum(y0 + 1, h - 1)
    x0 = np.floor(xs).astype(int); x1 = np.minimum(x0 + 1, w - 1)
    wy = (ys - y0)[:, None]; wx = (xs - x0)[None, :]
    Ia = img[np.ix_(y0, x0)]; Ib = img[np.ix_(y0, x1)]
    Ic = img[np.ix_(y1, x0)]; Id = img[np.ix_(y1, x1)]
    top = Ia * (1 - wx) + Ib * wx
    bot = Ic * (1 - wx) + Id * wx
    return top * (1 - wy) + bot * wy


def agr_correct_channel(ch, scale, smoothness, downsample, mode,
                        protect=True, protect_threshold=0.05, protect_amount=0.5,
                        simplified=False, degree=2, log=print):
    """Gradient-correct one 2D channel. Returns (corrected, background)."""
    h, w = ch.shape
    small = agr_downsample(ch, downsample)
    # Scale is a RELATIVE scale: higher = smoother model.
    # Map it to a smoothing radius as a fraction of the image (resolution
    # independent): scale 5 -> ~5% of the smaller image dimension.
    radius = max(1, int(round(scale / 100.0 * min(small.shape))))
    model_small = agr_estimate_background(
        small, radius, smoothness=smoothness, protect=protect,
        protect_threshold=protect_threshold, protect_amount=protect_amount,
        simplified=simplified, degree=degree, log=log)
    bg = agr_resize_bilinear(model_small, h, w)
    level = float(np.median(bg))
    if mode == "divide":
        corrected = ch / np.maximum(bg, 1e-6) * level
    else:
        corrected = ch - bg + level
    return corrected, bg


def agr_correct_image(image, scale, smoothness, downsample, mode, protect=True,
                      protect_threshold=0.05, protect_amount=0.5,
                      simplified=False, degree=2, log=print):
    """Handle mono (H,W) or color (H,W,3). Returns (corrected, background)."""
    kw = dict(protect=protect, protect_threshold=protect_threshold,
             protect_amount=protect_amount, simplified=simplified,
             degree=degree)
    if image.ndim == 2:
        return agr_correct_channel(image, scale, smoothness, downsample, mode,
                                   log=log, **kw)
    out = np.empty_like(image, dtype=np.float64)
    bg = np.empty_like(image, dtype=np.float64)
    n = image.shape[2]

    # The per-channel work is heavy NumPy (box blur, lstsq, medians) that
    # releases the GIL, so running the channels in threads overlaps them
    # instead of doing them one after another. The functions are pure (no
    # shared state), so this is thread-safe; only `log` touches Siril and is
    # serialised behind a lock.
    log_lock = threading.Lock()

    def process(c):
        def clog(msg):
            with log_lock:
                log(f"[ch {c + 1}/{n}] {msg}")
        return c, agr_correct_channel(image[..., c], scale, smoothness,
                                      downsample, mode, log=clog, **kw)

    with concurrent.futures.ThreadPoolExecutor(max_workers=n) as ex:
        for c, (corr, bgc) in ex.map(process, range(n)):
            out[..., c] = corr
            bg[..., c] = bgc
    return out, bg

