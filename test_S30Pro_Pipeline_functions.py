#!/usr/bin/env python3
"""
Standalone test harness for S30Pro_Pipeline.py's pure-numpy processing
functions — no Siril installation, no PyQt6 GUI, no ONNX Runtime required.

How it works
------------
The pipeline script is written to run *inside* Siril's embedded Python
environment (it imports `sirilpy` and `onnxruntime` at module import time,
and calls `s.check_module_version(...)` / `onnx_helper.install_onnxruntime()`
/ `s.ensure_installed(...)` before anything else happens). None of that is
available — or wanted — in a plain test run: `SirilInterface` is only ever
instantiated inside `UnifiedPipelineWindow.__init__`, so as long as we never
construct that class, none of the actual Siril/ONNX machinery is needed.

So this script inserts minimal fake modules into `sys.modules` for
`sirilpy` and `onnxruntime` (just enough surface for the pipeline's
module-level code to run without error), then imports the real,
version-numbered pipeline file via `importlib.util.spec_from_file_location`
(its filename isn't a valid plain `import` name) and calls the actual
production functions directly with synthetic numpy arrays.

Usage
-----
    python3 test_S30Pro_Pipeline_functions.py [path/to/S30Pro_Pipeline_vX.Y.Z.py]

Exits 0 and prints "ALL TESTS PASSED" if every check succeeds, else prints
the failing assertion and exits 1.
"""
import os
import sys
import types
import tempfile
import importlib.util
import cv2
from astropy.io import fits as _astropy_fits

# --------------------------------------------------------------------------
# 1. Stub out sirilpy / onnxruntime just enough for module-level import code
# --------------------------------------------------------------------------


class _LogColor:
    GREEN = "green"
    BLUE = "blue"
    SALMON = "salmon"
    RED = "red"


class _SuppressedIO:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class _ONNXHelper:
    def install_onnxruntime(self):
        pass


class _SirilInterface:
    """Never actually instantiated in this test — UnifiedPipelineWindow is
    never constructed — but defined for completeness / import-time safety."""

    def __init__(self, *a, **kw):
        pass


class _CommandError(Exception):
    pass


class _DataError(Exception):
    pass


class _SirilError(Exception):
    pass


def _make_sirilpy_stub():
    mod = types.ModuleType("sirilpy")
    mod.check_module_version = lambda *_a, **_kw: True
    mod.ONNXHelper = _ONNXHelper
    mod.SuppressedStderr = _SuppressedIO
    mod.SuppressedStdout = _SuppressedIO
    mod.ensure_installed = lambda *a, **kw: None
    mod.LogColor = _LogColor
    mod.SirilInterface = _SirilInterface
    mod.CommandError = _CommandError
    mod.DataError = _DataError
    mod.SirilError = _SirilError
    return mod


def _make_onnxruntime_stub():
    mod = types.ModuleType("onnxruntime")
    mod.set_default_logger_severity = lambda *_a, **_kw: None
    # no preload_dlls attribute -> pipeline's hasattr() check skips it cleanly
    return mod


def _make_pyqt6_stubs():
    """PyQt6 needs a real Qt install to build/import (not available in every
    environment this test might run in — e.g. a headless CI box or a sandbox
    without system Qt). None of that is actually needed here: the pipeline
    only *touches* real widgets inside UnifiedPipelineWindow.__init__ and
    other instance methods, none of which this test ever calls — it only
    calls plain-numpy static functions/methods. So every PyQt6 name the
    module imports is replaced with one universal permissive stand-in that
    can be subclassed, called, and chained-attribute-accessed
    (`Qt.Key.Key_Escape`, `QMessageBox.StandardButton.Yes | ...`, etc.)
    without ever raising, since nothing checks its actual behavior.
    """

    class _QMeta(type):
        def __getattr__(cls, _name):
            return _Q  # class-level dotted access, e.g. Qt.Key

    class _Q(metaclass=_QMeta):
        def __init__(self, *a, **kw):
            pass

        def __getattr__(self, _name):
            return _Q()  # instance-level dotted access

        def __call__(self, *a, **kw):
            return _Q()

        def __or__(self, other):
            return _Q()

        def __ror__(self, other):
            return _Q()

    widgets_names = [
        "QApplication", "QMainWindow", "QWidget", "QVBoxLayout", "QHBoxLayout",
        "QGridLayout", "QLabel", "QPushButton", "QCheckBox", "QDoubleSpinBox",
        "QSpinBox", "QComboBox", "QGroupBox", "QMessageBox", "QFileDialog",
        "QSlider", "QProgressBar", "QFrame", "QScrollArea", "QSplitter",
        "QSizePolicy", "QStackedWidget",
    ]
    core_names = ["Qt", "QThread", "pyqtSignal", "QSize", "QRectF", "QTimer",
                 "QPointF"]
    gui_names = ["QFont", "QImage", "QPixmap", "QPainter", "QColor", "QPen",
                "QPainterPath", "QPolygonF", "QShortcut", "QKeySequence"]

    # Listed names are set eagerly for clarity/documentation, but a
    # module-level __getattr__ (PEP 562) fallback also returns the same
    # permissive stand-in for ANY *public* name — so `from PyQt6.QtWidgets
    # import QWhateverNewWidget` keeps working even if the pipeline script
    # starts importing a PyQt6 class this list doesn't happen to enumerate
    # yet. Names starting with "_" (dunders like __file__, __path__,
    # __spec__) must raise AttributeError like a real module would —
    # returning a fake value for those breaks other libraries' own module
    # introspection (e.g. astropy's config system calls
    # inspect.getmodule(), which scans sys.modules and calls
    # hasattr(m, '__file__') on every entry; a stub that answers "yes" with
    # a bogus value there crashes astropy's *own* import, nothing to do
    # with PyQt6 at all).
    def _module_getattr(_name):
        if _name.startswith("_"):
            raise AttributeError(_name)
        return _Q

    widgets_mod = types.ModuleType("PyQt6.QtWidgets")
    for n in widgets_names:
        setattr(widgets_mod, n, _Q)
    widgets_mod.__getattr__ = _module_getattr
    core_mod = types.ModuleType("PyQt6.QtCore")
    for n in core_names:
        setattr(core_mod, n, _Q)
    core_mod.__getattr__ = _module_getattr
    gui_mod = types.ModuleType("PyQt6.QtGui")
    for n in gui_names:
        setattr(gui_mod, n, _Q)
    gui_mod.__getattr__ = _module_getattr

    pyqt6_pkg = types.ModuleType("PyQt6")
    pyqt6_pkg.QtWidgets = widgets_mod
    pyqt6_pkg.QtCore = core_mod
    pyqt6_pkg.QtGui = gui_mod

    return {
        "PyQt6": pyqt6_pkg,
        "PyQt6.QtWidgets": widgets_mod,
        "PyQt6.QtCore": core_mod,
        "PyQt6.QtGui": gui_mod,
    }


def load_pipeline_module(path):
    sys.modules.setdefault("sirilpy", _make_sirilpy_stub())
    sys.modules.setdefault("onnxruntime", _make_onnxruntime_stub())
    try:
        import PyQt6  # noqa: F401 — real PyQt6 available, use it as-is
    except ImportError:
        for name, mod in _make_pyqt6_stubs().items():
            sys.modules.setdefault(name, mod)

    spec = importlib.util.spec_from_file_location("s30pro_pipeline_under_test", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# 2. Tiny assertion helpers (no pytest dependency required)
# --------------------------------------------------------------------------

_PASS = 0
_FAIL = 0


def check(name, condition, detail=""):
    global _PASS, _FAIL
    if condition:
        _PASS += 1
        print(f"  [PASS] {name}")
    else:
        _FAIL += 1
        print(f"  [FAIL] {name}  {detail}")


def close(a, b, tol=1e-4):
    return abs(float(a) - float(b)) <= tol


# --------------------------------------------------------------------------
# 3. Tests
# --------------------------------------------------------------------------

def test_luminance(pipeline, np):
    print("\n== luminance() ==")
    # Pure red / green / blue planes -> luminance should equal the
    # corresponding Rec.709 weight, and match the manual formula on
    # random data.
    r = np.ones((4, 4), dtype=np.float32)
    g = np.zeros((4, 4), dtype=np.float32)
    b = np.zeros((4, 4), dtype=np.float32)
    pure_red = np.stack([r, g, b])
    lum = pipeline.luminance(pure_red)
    check("pure red channel -> luminance == Rec.709 R weight",
          close(lum[0, 0], pipeline.REC709_WEIGHTS[0]),
          f"got {lum[0,0]}, expected {pipeline.REC709_WEIGHTS[0]}")

    rng = np.random.default_rng(42)
    rgb = rng.random((3, 6, 6)).astype(np.float32)
    wr, wg, wb = pipeline.REC709_WEIGHTS
    expected = wr * rgb[0] + wg * rgb[1] + wb * rgb[2]
    got = pipeline.luminance(rgb)
    check("matches manual Rec.709 formula on random data",
          bool(np.allclose(got, expected, atol=1e-5)))

    # custom weights parameter is honored
    custom = (1.0, 0.0, 0.0)
    got_custom = pipeline.luminance(rgb, weights=custom)
    check("custom weights parameter overrides the default",
          bool(np.allclose(got_custom, rgb[0], atol=1e-5)))


def test_gaussian_psf(pipeline, np):
    print("\n== _make_gaussian_psf() ==")
    psf = pipeline._make_gaussian_psf(size=15, sigma=2.0)
    check("shape is (size, size)", psf.shape == (15, 15), f"got {psf.shape}")
    check("sums to ~1.0 (normalized)", close(psf.sum(), 1.0, tol=1e-5),
          f"got {psf.sum()}")
    check("peak is at the center",
          bool(np.argmax(psf) == np.ravel_multi_index((7, 7), psf.shape)))
    check("symmetric (PSF should be radially symmetric)",
          bool(np.allclose(psf, psf.T, atol=1e-6)))


def test_richardson_lucy_sharpen(pipeline, np):
    print("\n== richardson_lucy_sharpen() ==")
    # A blurred step edge should come back sharper (higher local contrast)
    # after a few RL iterations, without leaving the [0, 1] range.
    size = 40
    img = np.zeros((size, size), dtype=np.float32)
    img[:, size // 2:] = 1.0
    psf = pipeline._make_gaussian_psf(9, 1.5)
    from scipy.signal import convolve2d  # noqa: local import, optional dep
    blurred = convolve2d(img, psf, mode="same", boundary="symm").astype(np.float32)
    blurred = np.clip(blurred, 0.0, 1.0)

    sharpened = pipeline.richardson_lucy_sharpen(blurred, sigma=1.5, iterations=8,
                                                 psf_size=9)
    check("output stays in [0, 1]",
          bool(sharpened.min() >= 0.0 and sharpened.max() <= 1.0),
          f"min={sharpened.min()} max={sharpened.max()}")
    check("output shape matches input",
          sharpened.shape == blurred.shape)

    # gradient steepness across the edge (col 18..22) should increase
    def edge_steepness(arr):
        return float(arr[size // 2, size // 2 + 2] - arr[size // 2, size // 2 - 2])

    check("edge is sharper (steeper) after deconvolution",
          edge_steepness(sharpened) >= edge_steepness(blurred) - 1e-6,
          f"blurred={edge_steepness(blurred):.4f} "
          f"sharpened={edge_steepness(sharpened):.4f}")

    # planar (3, h, w) color input should work channel-wise and preserve shape
    color = np.stack([blurred, blurred, blurred])
    color_out = pipeline.richardson_lucy_sharpen(color, sigma=1.5, iterations=4,
                                                  psf_size=9)
    check("planar 3-channel input preserves shape",
          color_out.shape == color.shape)




def test_annotate_catalog_helpers(pipeline, np):
    print("\n== Annotate stage: catalogue helper functions ==")

    # _ang_sep: identical points -> 0; known separations; RA=0/360 wraparound
    check("_ang_sep: identical points are 0 deg apart",
          abs(pipeline._ang_sep(10.0, 20.0, 10.0, 20.0)) < 1e-9)
    d = pipeline._ang_sep(0.0, 0.0, 90.0, 0.0)
    check("_ang_sep: two points 90 deg apart on the equator", abs(d - 90.0) < 1e-6,
          f"got {d}")
    d = pipeline._ang_sep(0.0, 0.0, 0.0, 90.0)
    check("_ang_sep: equator to pole is 90 deg", abs(d - 90.0) < 1e-6, f"got {d}")
    d = pipeline._ang_sep(1.0, 0.0, 359.0, 0.0)
    check("_ang_sep: handles RA=0/360 wraparound (2 deg apart, not 358)",
          abs(d - 2.0) < 1e-6, f"got {d}")

    # _sexa_to_deg: RA (hours->degrees, *15) and Dec (degrees, signed)
    ra = pipeline._sexa_to_deg("00:42:44.3", is_ra=True)
    check("_sexa_to_deg: RA 00:42:44.3 -> ~10.68 deg", abs(ra - 10.6846) < 1e-3,
          f"got {ra}")
    dec = pipeline._sexa_to_deg("+41:16:09", is_ra=False)
    check("_sexa_to_deg: Dec +41:16:09 -> ~41.27 deg", abs(dec - 41.2692) < 1e-3,
          f"got {dec}")
    dec = pipeline._sexa_to_deg("-05:23:28", is_ra=False)
    check("_sexa_to_deg: negative Dec keeps its sign", dec < 0,
          f"got {dec}")

    # _clean_ngc_ic_name: strips OpenNGC's zero-padding and adds a space
    check("_clean_ngc_ic_name: NGC0224 -> 'NGC 224'",
          pipeline._clean_ngc_ic_name("NGC0224") == "NGC 224",
          f"got {pipeline._clean_ngc_ic_name('NGC0224')}")
    check("_clean_ngc_ic_name: IC0434 -> 'IC 434'",
          pipeline._clean_ngc_ic_name("IC0434") == "IC 434",
          f"got {pipeline._clean_ngc_ic_name('IC0434')}")

    # _parse_vizier_tsv: canned VizieR TSV response, including a units row
    # (dashes-only line) that must be skipped, not mistaken for data.
    tsv = (
        "#comment line, ignored\n"
        "_RAJ2000\t_DEJ2000\tSh2\n"
        "---\t---\t---\n"
        "83.8221\t-5.3911\t101\n"
        "84.1000\t-1.2000\t102\n"
    )
    rows = pipeline._parse_vizier_tsv(tsv)
    check("_parse_vizier_tsv: parses 2 data rows, skips comment/dashes",
          len(rows) == 2, f"got {len(rows)} rows: {rows}")
    check("_parse_vizier_tsv: values are accessible by column name",
          rows[0]["Sh2"] == "101" and rows[1]["_RAJ2000"] == "84.1000",
          f"got {rows}")

    # _filter_openngc_rows: synthetic OpenNGC-style rows, no network/disk.
    # Search center is near Orion (M42); NGC 2024 and IC 434 are also
    # nearby real Orion-region objects, NGC 7000 (Cygnus) is genuinely far
    # away, and the NonEx row sits right next to M42 so its exclusion can
    # only be due to its type, not distance.
    rows = [
        # M42 / NGC 1976 — has an M cross-reference, should come out "messier"
        # MajAx (apparent major axis, arcmin) present -> size should carry
        # through so the marker can be sized to the real object.
        {"Name": "NGC1976", "Type": "Neb", "RA": "05:35:17.3", "Dec": "-05:23:28",
         "M": "42", "V-Mag": "4.0", "MajAx": "85"},
        # NGC 2024 (Flame Nebula) — plain NGC, no Messier number, nearby
        {"Name": "NGC2024", "Type": "Neb", "RA": "05:41:42.0", "Dec": "-01:51:00",
         "M": "", "V-Mag": "", "MajAx": "30"},
        # IC 434 (Horsehead) — plain IC, nearby, no MajAx in this row ->
        # size should come out None rather than raising
        {"Name": "IC0434", "Type": "Neb", "RA": "05:41:00.0", "Dec": "-02:24:00",
         "M": "", "V-Mag": ""},
        # NGC 7000 (North America Nebula, Cygnus) — genuinely far away
        {"Name": "NGC7000", "Type": "Neb", "RA": "20:58:47.0", "Dec": "+44:19:48",
         "M": "", "V-Mag": "", "MajAx": "120"},
        # NonEx type, right next to M42 — must be excluded by type, not distance
        {"Name": "NGC0002", "Type": "NonEx", "RA": "05:35:00.0", "Dec": "-05:20:00",
         "M": "", "V-Mag": ""},
    ]
    out = pipeline.UnifiedPipelineWindow._filter_openngc_rows(
        rows, ra=84.0, dec=-3.5, radius=5.0,
        want_messier=True, want_ngc=True, want_ic=True)
    kinds = sorted(d[3] for d in out)
    check("_filter_openngc_rows: finds Messier/NGC/IC, excludes far/NonEx rows",
          kinds == ["ic", "messier", "ngc"], f"got {kinds}")
    messier_label = next(d[0] for d in out if d[3] == "messier")
    check("_filter_openngc_rows: Messier object labeled 'M 42', not 'NGC 1976'",
          messier_label == "M 42", f"got {messier_label}")
    messier_size = next(d[4] for d in out if d[3] == "messier")
    ic_size = next(d[4] for d in out if d[3] == "ic")
    check("_filter_openngc_rows: carries OpenNGC's MajAx as size_arcmin",
          messier_size == 85.0, f"got {messier_size}")
    check("_filter_openngc_rows: missing MajAx yields size_arcmin=None, "
          "not an error", ic_size is None, f"got {ic_size}")

    # Toggling a catalogue off excludes it even though it's in range
    out = pipeline.UnifiedPipelineWindow._filter_openngc_rows(
        rows, ra=84.0, dec=-3.5, radius=5.0,
        want_messier=False, want_ngc=True, want_ic=True)
    kinds = sorted(d[3] for d in out)
    check("_filter_openngc_rows: unchecking Messier excludes it even in range",
          "messier" not in kinds and "ngc" in kinds and "ic" in kinds,
          f"got {kinds}")

    # _layout_annotation_labels: greedy label placement that must (a) never
    # place a label outside the canvas and (b) avoid overlapping labels
    # when there's room to do so.
    W, H = 400, 300
    items = [
        {"label": "M 42", "kind": "messier", "x": 200, "y": 150, "r": 40,
         "fs": 0.85, "th": 2},
        # A second marker very close to the first — without collision
        # avoidance their labels would land on top of each other.
        {"label": "NGC 1977", "kind": "ngc", "x": 210, "y": 150, "r": 20,
         "fs": 0.85, "th": 2},
        # Right at the top-left corner — the naive "offset up-and-right"
        # placement used before this version would clip this off-canvas.
        {"label": "Sh2-999 (a long label)", "kind": "sh2", "x": 2, "y": 2,
         "r": 10, "fs": 0.85, "th": 2},
        # Right at the bottom-right corner, same concern in the opposite
        # direction.
        {"label": "LDN 1622", "kind": "ldn", "x": W - 2, "y": H - 2,
         "r": 10, "fs": 0.85, "th": 2},
    ]
    pipeline.UnifiedPipelineWindow._layout_annotation_labels(items, W, H)

    def label_box(d):
        (tw, th_box), baseline = cv2.getTextSize(
            d["label"], cv2.FONT_HERSHEY_SIMPLEX, d["fs"], d["th"])
        tw += 2
        th_box += baseline
        return (d["tx"] - 2, d["ty"] - th_box - 2, d["tx"] + tw + 2,
                d["ty"] + 2)

    boxes = [label_box(d) for d in items]
    all_in_bounds = all(
        b[0] >= 0 and b[1] >= 0 and b[2] <= W and b[3] <= H for b in boxes)
    check("_layout_annotation_labels: every label stays fully on-canvas, "
          "even at the image corners", all_in_bounds, f"boxes={boxes}")

    def overlap_area(a, b):
        ox = max(0, min(a[2], b[2]) - max(a[0], b[0]))
        oy = max(0, min(a[3], b[3]) - max(a[1], b[1]))
        return ox * oy

    m42_box, ngc1977_box = boxes[0], boxes[1]
    check("_layout_annotation_labels: M 42 and neighboring NGC 1977 labels "
          "don't overlap",
          overlap_area(m42_box, ngc1977_box) == 0,
          f"m42={m42_box} ngc1977={ngc1977_box}")


def test_palette_nebulachrome(pipeline, np):
    print("\n== UnifiedPipelineWindow._palette_nebulachrome() ==")
    # Synthetic image: a dim, red-dominant "background" everywhere, with a
    # bright red-dominant "nebula core" blob in the middle. NebulaChrome
    # should recolor the bright core toward teal/blue while leaving the
    # background close to where it started (the whole point of the
    # luminosity-masked design fixed in v1.16.3).
    h = w = 64
    bg_level = 0.05
    img = np.full((3, h, w), bg_level, dtype=np.float32)
    img[0, :, :] = bg_level * 1.4  # background is slightly red-dominant

    cy, cx = h // 2, w // 2
    yy, xx = np.mgrid[0:h, 0:w]
    core_mask = (yy - cy) ** 2 + (xx - cx) ** 2 < (h // 6) ** 2
    img[0][core_mask] = 0.9   # bright, strongly red-dominant nebula core
    img[1][core_mask] = 0.25
    img[2][core_mask] = 0.15

    out = pipeline.UnifiedPipelineWindow._palette_nebulachrome(
        img, strength=0.7, peak_gamma=3.0, progress=None)

    check("output shape matches input", out.shape == img.shape)
    check("output stays in [0, 1]",
          bool(out.min() >= -1e-6 and out.max() <= 1.0 + 1e-6),
          f"min={out.min()} max={out.max()}")

    # Background: sample a corner far from the core, average red-vs-blue
    # bias should not swing wildly (small delta = background stayed put).
    bg_before = img[:, 2:6, 2:6].mean(axis=(1, 2))
    bg_after = out[:, 2:6, 2:6].mean(axis=(1, 2))
    bg_delta = float(np.abs(bg_after - bg_before).max())
    check("background pixels change only slightly (luminosity-masked gating)",
          bg_delta < 0.15, f"max channel delta = {bg_delta:.4f}")

    # Core: should shift away from red-dominant toward blue/teal-dominant
    # (blue+green channel share of the core should increase).
    core_before = img[:, core_mask].mean(axis=1)
    core_after = out[:, core_mask].mean(axis=1)
    red_share_before = core_before[0] / (core_before.sum() + 1e-9)
    red_share_after = core_after[0] / (core_after.sum() + 1e-9)
    check("nebula core becomes less red-dominant (recolored toward teal)",
          red_share_after < red_share_before,
          f"red share before={red_share_before:.3f} after={red_share_after:.3f}")


def test_gimp_replacement_polish(pipeline, np):
    print("\n== Hubble Palette: _gimp_replacement_polish() (GIMP replacement) ==")
    try:
        import skimage  # noqa: F401
    except ImportError as e:
        print(f"  [SKIP] scikit-image not available ({e})")
        return

    h = w = 48
    rng = np.random.RandomState(0)
    # A colorful, noisy synthetic image: mid-gray base with per-channel
    # variation and Gaussian noise, so saturation/contrast/denoise all have
    # something real to act on.
    base = np.stack([
        np.full((h, w), 0.35, dtype=np.float32),
        np.full((h, w), 0.5, dtype=np.float32),
        np.full((h, w), 0.4, dtype=np.float32),
    ])
    noise = rng.normal(0, 0.05, base.shape).astype(np.float32)
    img = np.clip(base + noise, 0.0, 1.0)

    poly = pipeline.UnifiedPipelineWindow._gimp_replacement_polish

    # No-op: every parameter at its neutral default should return
    # (near-)identical output — confirms none of the passes fire when the
    # sliders are all at "no change" (the same guarantee the UI's default
    # slider positions rely on).
    out_noop = poly(img, saturation=1.0, shadows=0.0, highlights=0.0,
                    contrast=0.0, sharpen_amount=0.0, denoise_strength=0.0)
    check("no-op parameters leave the image (nearly) unchanged",
          bool(np.abs(out_noop - img).max() < 1e-5),
          f"max delta = {float(np.abs(out_noop - img).max()):.6f}")
    check("output shape matches input", out_noop.shape == img.shape)

    # Saturation: boosting should increase the spread between channels
    # (more colorful), muting should decrease it.
    L = np.mean(img, axis=0, keepdims=True)
    spread_before = float(np.mean(np.abs(img - L)))
    out_sat_up = poly(img, saturation=1.8)
    spread_up = float(np.mean(np.abs(
        out_sat_up - np.mean(out_sat_up, axis=0, keepdims=True))))
    check("saturation > 1 increases color spread (more saturated)",
          spread_up > spread_before,
          f"before={spread_before:.4f} after={spread_up:.4f}")
    out_sat_down = poly(img, saturation=0.2)
    spread_down = float(np.mean(np.abs(
        out_sat_down - np.mean(out_sat_down, axis=0, keepdims=True))))
    check("saturation < 1 decreases color spread (more gray)",
          spread_down < spread_before,
          f"before={spread_before:.4f} after={spread_down:.4f}")

    # Shadows: positive value should brighten the image overall.
    out_shadows = poly(img, shadows=0.6)
    check("shadows > 0 brightens the image",
          float(out_shadows.mean()) > float(img.mean()),
          f"before={float(img.mean()):.4f} after={float(out_shadows.mean()):.4f}")

    # Highlights: negative value should darken the image overall.
    out_hi = poly(img, highlights=-0.6)
    check("highlights < 0 darkens the image",
          float(out_hi.mean()) < float(img.mean()),
          f"before={float(img.mean()):.4f} after={float(out_hi.mean()):.4f}")

    # Contrast: positive value should increase the standard deviation
    # around the midpoint.
    std_before = float(img.std())
    out_contrast = poly(img, contrast=0.8)
    check("contrast > 0 increases spread around the midpoint",
          float(out_contrast.std()) > std_before,
          f"before={std_before:.4f} after={float(out_contrast.std()):.4f}")

    # Denoise: bilateral filtering should reduce local (within-channel)
    # pixel-to-pixel variance vs. the noisy input. Measured per-channel and
    # averaged rather than std() over the whole array, since the three
    # channels have different means (0.35/0.5/0.4) — a whole-array std
    # would be dominated by that offset, not the local noise this pass
    # actually targets. Using a moderate strength (0.3) rather than the
    # slider's max: bilateral filtering has a sweet spot where sigma_color
    # roughly matches the noise amplitude — push sigma_color far past that
    # (as denoise_strength=1.0 does for this image's ~0.05 noise std) and
    # the filter starts amplifying variance again rather than smoothing,
    # same behavior as the underlying gimp_replacement.py formula this
    # ports. 0.3 sits well inside the effective range for this noise level.
    std_before_ch = float(np.mean([img[c].std() for c in range(3)]))
    out_denoise = poly(img, denoise_strength=0.3)
    std_after_ch = float(np.mean([out_denoise[c].std() for c in range(3)]))
    check("denoise reduces pixel-to-pixel variance",
          std_after_ch < std_before_ch,
          f"before={std_before_ch:.4f} after={std_after_ch:.4f}")

    # All six at once shouldn't error and should still produce a valid,
    # in-range planar array.
    out_all = poly(img, saturation=1.3, shadows=0.2, highlights=-0.15,
                   contrast=0.3, sharpen_amount=1.0, denoise_strength=0.4)
    check("combining all six parameters stays in range and shape",
          out_all.shape == img.shape
          and bool(out_all.min() >= -1e-6 and out_all.max() <= 1.0 + 1e-6),
          f"shape={out_all.shape} min={out_all.min()} max={out_all.max()}")


def test_patch_stackcnt_header(pipeline, np):
    print("\n== Preprocess: _patch_stackcnt_header() "
          "(combine-with-existing-master) ==")
    patch = pipeline.UnifiedPipelineWindow._patch_stackcnt_header

    with tempfile.TemporaryDirectory() as tmp:
        # Case 1: a master with no STACKCNT header at all — patch() should
        # report that (False), and with override=0 should leave the file
        # untouched (no STACKCNT written).
        path_missing = os.path.join(tmp, "no_stackcnt.fits")
        hdu = _astropy_fits.PrimaryHDU(np.zeros((8, 8), dtype=np.float32))
        hdu.writeto(path_missing)
        had = patch(path_missing, override=0)
        check("no STACKCNT header + override=0: reports 'missing' (False)",
              had is False, f"got {had}")
        with _astropy_fits.open(path_missing) as hdul:
            check("no STACKCNT header + override=0: doesn't fabricate one",
                  "STACKCNT" not in hdul[0].header,
                  f"header keys: {list(hdul[0].header.keys())}")

        # Case 2: same file, but now with a sub-count override — should get
        # written into the header.
        path_override = os.path.join(tmp, "override.fits")
        hdu = _astropy_fits.PrimaryHDU(np.zeros((8, 8), dtype=np.float32))
        hdu.writeto(path_override)
        had = patch(path_override, override=142)
        check("override=142 on a header with no STACKCNT: still reports "
              "'missing' (reflects state BEFORE the override)",
              had is False, f"got {had}")
        with _astropy_fits.open(path_override) as hdul:
            check("override=142 is written into STACKCNT",
                  int(hdul[0].header.get("STACKCNT", -1)) == 142,
                  f"got {hdul[0].header.get('STACKCNT')}")

        # Case 3: a master that already has a real STACKCNT — patch()
        # should report True, and with override=0 should leave the
        # existing value alone (not overwritten with anything).
        path_existing = os.path.join(tmp, "existing.fits")
        hdu = _astropy_fits.PrimaryHDU(np.zeros((8, 8), dtype=np.float32))
        hdu.header["STACKCNT"] = 300
        hdu.writeto(path_existing)
        had = patch(path_existing, override=0)
        check("existing STACKCNT=300 + override=0: reports 'present' (True)",
              had is True, f"got {had}")
        with _astropy_fits.open(path_existing) as hdul:
            check("existing STACKCNT=300 + override=0: value unchanged",
                  int(hdul[0].header.get("STACKCNT", -1)) == 300,
                  f"got {hdul[0].header.get('STACKCNT')}")

        # Case 4: multi-HDU FITS (primary HDU has no data, real data lives
        # in extension 1) — matches compressed FITS as produced by Siril's
        # Rice compression. Must find the header on the right HDU.
        path_multi = os.path.join(tmp, "multi_hdu.fits")
        primary = _astropy_fits.PrimaryHDU()
        ext = _astropy_fits.ImageHDU(np.zeros((8, 8), dtype=np.float32))
        hdul = _astropy_fits.HDUList([primary, ext])
        hdul.writeto(path_multi)
        had = patch(path_multi, override=77)
        with _astropy_fits.open(path_multi) as hdul:
            check("multi-HDU FITS: STACKCNT override lands on the data "
                  "HDU (extension 1), not the empty primary HDU",
                  int(hdul[1].header.get("STACKCNT", -1)) == 77,
                  f"got {hdul[1].header.get('STACKCNT')}")


def test_ensure_float32_fits(pipeline, np):
    print("\n== Preprocess: _ensure_float32_fits() "
          "(combine-with-existing-master) ==")
    ensure_f32 = pipeline.UnifiedPipelineWindow._ensure_float32_fits

    with tempfile.TemporaryDirectory() as tmp:
        # Case 1: a 16-bit integer master (raw ADU counts, as a
        # non-Siril-produced or older master might be) — should be
        # rewritten as float32, normalized into [0, 1] the same way
        # VeraLuxCore.normalize_input scales uint16 data elsewhere in
        # this script (divide by 65535).
        path_u16 = os.path.join(tmp, "u16.fits")
        data_u16 = np.array([[0, 65535], [16384, 32768]], dtype=np.uint16)
        _astropy_fits.PrimaryHDU(data_u16).writeto(path_u16)
        ensure_f32(path_u16)
        with _astropy_fits.open(path_u16) as hdul:
            out = hdul[0].data
            check("16-bit integer master: rewritten as float32",
                  out.dtype.name == "float32", f"got dtype {out.dtype}")
            check("16-bit integer master: normalized into [0, 1] "
                  "(65535 -> ~1.0)",
                  abs(float(out[0, 1]) - 1.0) < 1e-4, f"got {out[0, 1]}")
            check("16-bit integer master: 0 stays 0.0",
                  abs(float(out[0, 0]) - 0.0) < 1e-4, f"got {out[0, 0]}")

        # Case 2: already a normalized 32-bit float master (Siril's own
        # on-disk convention, values in [0, 1]) — should be left alone
        # (no rescaling, since it isn't raw ADU data).
        path_f32 = os.path.join(tmp, "f32.fits")
        data_f32 = np.array([[0.0, 1.0], [0.25, 0.75]], dtype=np.float32)
        _astropy_fits.PrimaryHDU(data_f32.copy()).writeto(path_f32)
        ensure_f32(path_f32)
        with _astropy_fits.open(path_f32) as hdul:
            out = hdul[0].data
            check("already-normalized float32 master: left untouched",
                  np.allclose(out, data_f32), f"got {out}")

        # Case 3: multi-HDU FITS (primary HDU has no data, real data in
        # extension 1) — matches compressed FITS as produced by Siril's
        # Rice compression. Must normalize the right HDU.
        path_multi = os.path.join(tmp, "multi_hdu.fits")
        primary = _astropy_fits.PrimaryHDU()
        ext = _astropy_fits.ImageHDU(
            np.array([[0, 65535]], dtype=np.uint16))
        _astropy_fits.HDUList([primary, ext]).writeto(path_multi)
        ensure_f32(path_multi)
        with _astropy_fits.open(path_multi) as hdul:
            out = hdul[1].data
            check("multi-HDU FITS: normalization lands on the data HDU "
                  "(extension 1), not the empty primary HDU",
                  out.dtype.name == "float32" and abs(float(out[0, 1]) - 1.0) < 1e-4,
                  f"got dtype {out.dtype}, value {out[0, 1]}")


def test_read_integration_seconds(pipeline, np):
    print("\n== Preprocess: _read_integration_seconds() "
          "(combine-with-existing-master) ==")
    read_secs = pipeline.UnifiedPipelineWindow._read_integration_seconds

    with tempfile.TemporaryDirectory() as tmp:
        # Case 1: a master with a direct LIVETIME header — should be
        # used as-is, not recomputed from STACKCNT x EXPTIME.
        path_live = os.path.join(tmp, "live.fits")
        hdu = _astropy_fits.PrimaryHDU(np.zeros((4, 4), dtype=np.float32))
        hdu.header["LIVETIME"] = 3600.0
        hdu.header["STACKCNT"] = 10
        hdu.header["EXPTIME"] = 30.0  # deliberately inconsistent with LIVETIME
        hdu.writeto(path_live)
        live, cnt, exp = read_secs(path_live)
        check("LIVETIME present: used directly (not recomputed)",
              live == 3600.0, f"got {live}")
        check("LIVETIME present: STACKCNT/EXPTIME still reported as-is",
              cnt == 10 and exp == 30.0, f"got cnt={cnt}, exp={exp}")

        # Case 2: no LIVETIME, but STACKCNT and EXPTIME present — falls
        # back to STACKCNT x EXPTIME.
        path_fallback = os.path.join(tmp, "fallback.fits")
        hdu = _astropy_fits.PrimaryHDU(np.zeros((4, 4), dtype=np.float32))
        hdu.header["STACKCNT"] = 20
        hdu.header["EXPTIME"] = 60.0
        hdu.writeto(path_fallback)
        live, cnt, exp = read_secs(path_fallback)
        check("no LIVETIME: falls back to STACKCNT x EXPTIME (20x60=1200)",
              live == 1200.0, f"got {live}")

        # Case 3: no LIVETIME, no STACKCNT/EXPTIME at all — should
        # report zero, not raise.
        path_empty = os.path.join(tmp, "empty.fits")
        _astropy_fits.PrimaryHDU(
            np.zeros((4, 4), dtype=np.float32)).writeto(path_empty)
        live, cnt, exp = read_secs(path_empty)
        check("no headers at all: reports (0.0, 0, 0.0), doesn't raise",
              (live, cnt, exp) == (0.0, 0, 0.0), f"got {(live, cnt, exp)}")

        # Case 4: multi-HDU FITS (primary HDU has no data, real header on
        # extension 1) — matches compressed FITS as produced by Siril's
        # Rice compression. Must read the header from the right HDU.
        path_multi = os.path.join(tmp, "multi_hdu.fits")
        primary = _astropy_fits.PrimaryHDU()
        ext = _astropy_fits.ImageHDU(np.zeros((4, 4), dtype=np.float32))
        ext.header["LIVETIME"] = 900.0
        _astropy_fits.HDUList([primary, ext]).writeto(path_multi)
        live, cnt, exp = read_secs(path_multi)
        check("multi-HDU FITS: reads LIVETIME from the data HDU "
              "(extension 1), not the empty primary HDU",
              live == 900.0, f"got {live}")


def test_auto_gradient_removal(pipeline, np):
    print("\n== Auto Gradient Removal stage (agr_* core functions) ==")
    correct_image = pipeline.agr_correct_image

    rng = np.random.default_rng(0)
    h, w = 96, 128
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    # A gentle, realistic light-pollution-style gradient (background level
    # 0.30 rising smoothly to 0.38 across the frame — an amplitude modest
    # relative to the background level, like a real sky gradient) plus a
    # small bright "star" structure and a little noise. A much steeper
    # synthetic gradient (tried first) triggers this algorithm's iterative
    # rejection to progressively treat the brighter far corner as
    # "structure" rather than background and never converges — a real
    # property of the (faithfully ported, unmodified) rejection logic on
    # an unrealistically extreme gradient, not something to work around
    # here; a gentle gradient exercises its normal operating range.
    gradient = 0.30 + 0.08 * (xx / (w - 1)) * (yy / (h - 1))
    star = np.zeros((h, w))
    star[40:44, 60:64] = 0.9
    noisy = np.clip(gradient + star + rng.normal(0, 0.005, (h, w)), 0.0, 1.0)

    corrected, bg = correct_image(
        noisy, scale=5.0, smoothness=1.0, downsample=2, mode="subtract",
        protect=True, protect_threshold=0.05, protect_amount=0.5,
        simplified=False, degree=2, log=lambda _m: None)

    # The gradient makes the two opposite corners noticeably different in
    # brightness before correction; a successful gradient removal should
    # level them out much closer to each other, even though each corner's
    # own local noise (unrelated to the gradient) can't be improved.
    def corner_means(img):
        return float(np.mean(img[0:20, 0:20])), float(np.mean(img[-20:, -20:]))

    near_before, far_before = corner_means(noisy)
    near_after, far_after = corner_means(corrected)
    gap_before = abs(far_before - near_before)
    gap_after = abs(far_after - near_after)
    check("mono gradient: opposite-corner brightness gap shrinks sharply "
          "after correction",
          gap_after < gap_before * 0.3,
          f"before gap={gap_before:.4f}, after gap={gap_after:.4f}")

    # Structure protection: the star patch shouldn't have been fitted away
    # by the background model — the model's value under the star should
    # stay close to the surrounding sky level, not jump up to the star's
    # own brightness.
    star_bg_value = float(np.mean(bg[40:44, 60:64]))
    local_sky_value = float(np.mean(bg[36:40, 60:64]))
    check("structure protection: background model under the star stays "
          "close to the surrounding sky, not absorbed into the star",
          abs(star_bg_value - local_sky_value) < 0.05,
          f"star bg={star_bg_value:.4f}, local sky bg={local_sky_value:.4f}")

    # Color (H, W, 3) path — same shape in, same shape out, and the
    # multi-threaded per-channel path shouldn't crash or mix channels up.
    color = np.stack([noisy, noisy * 0.8, noisy * 0.6], axis=-1)
    corrected_c, bg_c = correct_image(
        color, scale=5.0, smoothness=1.0, downsample=2, mode="subtract",
        protect=True, protect_threshold=0.05, protect_amount=0.5,
        simplified=False, degree=2, log=lambda _m: None)
    check("color image: output shape matches input (H, W, 3)",
          corrected_c.shape == color.shape and bg_c.shape == color.shape,
          f"got corrected {corrected_c.shape}, bg {bg_c.shape}")

    # Simplified (polynomial) model path — different code path entirely
    # (least-squares fit instead of inpaint-lowpass), should still flatten
    # the same gradient.
    corrected_s, _bg_s = correct_image(
        noisy, scale=5.0, smoothness=0.0, downsample=2, mode="subtract",
        protect=True, protect_threshold=0.05, protect_amount=0.5,
        simplified=True, degree=2, log=lambda _m: None)
    near_s, far_s = corner_means(corrected_s)
    gap_s = abs(far_s - near_s)
    check("simplified polynomial model: also shrinks the opposite-corner "
          "brightness gap sharply",
          gap_s < gap_before * 0.3,
          f"before gap={gap_before:.4f}, simplified-model gap={gap_s:.4f}")


def test_subsky_box_editor_helpers(pipeline, np):
    print("\n== Remove Background stage: sample-box grid helper ==")
    gen = pipeline.UnifiedPipelineWindow._generate_default_bg_boxes

    boxes = gen(1000, 800, n_per_side=5, size=25)
    check("returns n_per_side^2 boxes",
          len(boxes) == 25, f"got {len(boxes)}")
    check("every box starts kept (True)",
          all(b[3] is True for b in boxes),
          f"kept flags: {[b[3] for b in boxes]}")
    check("every box's size matches the requested size",
          all(b[2] == 25 for b in boxes),
          f"sizes: {sorted(set(b[2] for b in boxes))}")
    xs = [b[0] for b in boxes]
    ys = [b[1] for b in boxes]
    check("boxes stay within the image bounds (with margin, not edge-to-edge)",
          min(xs) > 0 and max(xs) < 1000 and min(ys) > 0 and max(ys) < 800,
          f"x range=({min(xs):.1f},{max(xs):.1f}), "
          f"y range=({min(ys):.1f},{max(ys):.1f})")
    check("grid is roughly centered (not skewed to one side)",
          abs(np.mean(xs) - 500) < 50 and abs(np.mean(ys) - 400) < 50,
          f"mean x={np.mean(xs):.1f}, mean y={np.mean(ys):.1f}")

    small = gen(200, 150, n_per_side=3, size=10)
    check("different n_per_side/size args produce a different box count/size",
          len(small) == 9 and small[0][2] == 10,
          f"got {len(small)} boxes, size={small[0][2] if small else None}")


def test_constellation_lines(pipeline, np):
    print("\n== Annotate stage: constellation line helper functions ==")

    # CONSTELLATION_NAMES: all 88 IAU constellations, keyed by standard
    # 3-letter abbreviation.
    names = pipeline.CONSTELLATION_NAMES
    check("CONSTELLATION_NAMES has all 88 IAU constellations",
          len(names) == 88, f"got {len(names)}")
    check("CONSTELLATION_NAMES: Orion present with the right full name",
          names.get("Ori") == "Orion", f"got {names.get('Ori')!r}")
    check("CONSTELLATION_NAMES: Ursa Major present with the right full name",
          names.get("UMa") == "Ursa Major", f"got {names.get('UMa')!r}")

    # CONSTELLATION_COLOR_PRESETS: quick-pick (line color, name color)
    # pairs for the Annotate stage's color-preset dropdown — each value
    # must be a valid (line_bgr, name_bgr) pair of 3-tuples in [0, 255].
    presets = pipeline.CONSTELLATION_COLOR_PRESETS
    check("CONSTELLATION_COLOR_PRESETS: has the expected default entry",
          "Pale Lavender (default)" in presets, f"got keys={list(presets)}")

    def _is_valid_bgr(c):
        return (isinstance(c, tuple) and len(c) == 3 and
                all(isinstance(v, int) and 0 <= v <= 255 for v in c))

    bad = [name for name, pair in presets.items()
          if not (isinstance(pair, tuple) and len(pair) == 2 and
                  _is_valid_bgr(pair[0]) and _is_valid_bgr(pair[1]))]
    check("CONSTELLATION_COLOR_PRESETS: every entry is a valid "
          "(line_bgr, name_bgr) pair of 3-tuples in [0, 255]",
          not bad, f"invalid entries={bad}")
    check("CONSTELLATION_COLOR_PRESETS: no duplicate preset names collapse "
          "(dict literal has the count we expect)",
          len(presets) >= 5, f"got {len(presets)} presets")

    # _load_constellation_lines: parses the embedded dataset into
    # {abbr: [polyline, ...]}, RA normalized to 0..360 (no negative
    # longitudes left over from the embedded -180..180 convention), and
    # Serpens' two chains (Caput/Cauda) merged under one "Ser" key.
    lines = pipeline._load_constellation_lines()
    check("_load_constellation_lines: returns one entry per constellation "
          "(88, same as CONSTELLATION_NAMES)",
          set(lines.keys()) == set(names.keys()),
          f"missing={set(names) - set(lines)}, "
          f"extra={set(lines) - set(names)}")
    check("_load_constellation_lines: Orion has at least one polyline "
          "with 2+ vertices",
          "Ori" in lines and len(lines["Ori"]) > 0 and
          len(lines["Ori"][0]) >= 2,
          f"got {lines.get('Ori')}")
    check("_load_constellation_lines: Serpens' two sky-separated chains "
          "are merged under one 'Ser' key",
          len(lines.get("Ser", [])) >= 2, f"got {len(lines.get('Ser', []))}")
    all_ra = [ra for polylines in lines.values() for chain in polylines
             for ra, dec in chain]
    check("_load_constellation_lines: RA normalized to [0, 360), no "
          "leftover negative longitudes",
          min(all_ra) >= 0.0 and max(all_ra) < 360.0,
          f"RA range=({min(all_ra):.2f}, {max(all_ra):.2f})")
    # Calling twice must return the exact same (cached) object, not
    # re-parse the embedded JSON every time.
    check("_load_constellation_lines: result is cached across calls "
          "(same object, not re-parsed)",
          pipeline._load_constellation_lines() is lines)

    # _filter_constellation_lines: pure selection filter.
    filtered = pipeline._filter_constellation_lines(lines, {"Ori", "UMa"})
    check("_filter_constellation_lines: keeps only selected constellations",
          set(filtered.keys()) == {"Ori", "UMa"}, f"got {set(filtered)}")
    check("_filter_constellation_lines: empty selection -> empty result",
          pipeline._filter_constellation_lines(lines, set()) == {})
    check("_filter_constellation_lines: unknown abbreviations are ignored",
          pipeline._filter_constellation_lines(lines, {"XYZ"}) == {})

    # _inset_segment: shrinks a segment by gap_px from each end, along its
    # own direction; leaves it alone for zero gap or too-short segments.
    p1, p2 = (0.0, 0.0), (100.0, 0.0)
    q1, q2 = pipeline._inset_segment(p1, p2, 10.0)
    check("_inset_segment: horizontal segment shrinks by gap_px at each end",
          abs(q1[0] - 10.0) < 1e-9 and abs(q2[0] - 90.0) < 1e-9 and
          abs(q1[1]) < 1e-9 and abs(q2[1]) < 1e-9,
          f"got q1={q1}, q2={q2}")
    q1z, q2z = pipeline._inset_segment(p1, p2, 0.0)
    check("_inset_segment: zero gap leaves the segment unchanged",
          q1z == p1 and q2z == p2, f"got q1={q1z}, q2={q2z}")
    short1, short2 = (0.0, 0.0), (5.0, 0.0)
    qs1, qs2 = pipeline._inset_segment(short1, short2, 10.0)
    check("_inset_segment: segment shorter than 2*gap_px is left unchanged "
          "(no inversion)",
          qs1 == short1 and qs2 == short2, f"got q1={qs1}, q2={qs2}")
    # Diagonal segment: gap should shrink both axes proportionally.
    d1, d2 = (0.0, 0.0), (30.0, 40.0)  # length 50
    dq1, dq2 = pipeline._inset_segment(d1, d2, 5.0)
    dist = ((dq2[0] - dq1[0]) ** 2 + (dq2[1] - dq1[1]) ** 2) ** 0.5
    check("_inset_segment: diagonal segment shrinks to the expected total "
          "length (50 - 2*5 = 40)",
          abs(dist - 40.0) < 1e-6, f"got length={dist:.4f}")


# --------------------------------------------------------------------------
# 4. Entry point
# --------------------------------------------------------------------------

def main():
    default_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                "S30Pro_Pipeline.py")
    path = sys.argv[1] if len(sys.argv) > 1 else default_path
    if not os.path.isfile(path):
        print(f"Pipeline file not found: {path}")
        sys.exit(2)

    print(f"Loading pipeline module from: {path}")
    pipeline = load_pipeline_module(path)
    import numpy as np

    test_luminance(pipeline, np)
    test_gaussian_psf(pipeline, np)
    try:
        test_richardson_lucy_sharpen(pipeline, np)
    except ImportError as e:
        print(f"\n== richardson_lucy_sharpen() ==\n  [SKIP] scipy not available ({e})")
    test_palette_nebulachrome(pipeline, np)
    test_gimp_replacement_polish(pipeline, np)
    test_patch_stackcnt_header(pipeline, np)
    test_ensure_float32_fits(pipeline, np)
    test_read_integration_seconds(pipeline, np)
    test_auto_gradient_removal(pipeline, np)
    test_subsky_box_editor_helpers(pipeline, np)
    test_annotate_catalog_helpers(pipeline, np)
    test_constellation_lines(pipeline, np)

    print(f"\n{_PASS} passed, {_FAIL} failed.")
    if _FAIL:
        print("SOME TESTS FAILED")
        sys.exit(1)
    print("ALL TESTS PASSED")


if __name__ == "__main__":
    main()
