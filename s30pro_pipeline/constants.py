"""Telescope/sensor/filter lookup tables, stage indices, and
palette presets shared across the pipeline (extracted from
S30Pro_Pipeline.py)."""

__all__ = [
    "TELESCOPES", "FILTER_OPTIONS_MAP", "DUALBAND_ARGS",
    "FILTER_COMMANDS_MAP", "SPCC_SENSOR_MAP", "TELESCOPE_HEADER_MAP",
    "SENSOR_PROFILES", "DEFAULT_PROFILE", "REC709_WEIGHTS", "luminance",
    "TELESCOPE_TO_PROFILE", "STAGES", "IDX_PP", "IDX_CROP", "IDX_SCNR",
    "IDX_AGR", "IDX_BGE", "IDX_STARS", "IDX_DEN", "IDX_PAL", "IDX_STR",
    "IDX_HIST", "IDX_TOUCH", "IDX_ANN", "IDX_WM", "WATERMARK_POSITIONS",
    "PALETTE_PRESETS", "PALETTE_TO_PROFILE",
]

# =============================================================================
#  TELESCOPE / SPCC DATA  (from Naztronomy Smart Telescope PP)
# =============================================================================

TELESCOPES = [
    "ZWO Seestar S30", "ZWO Seestar S30 Pro", "ZWO Seestar S50",
    "Dwarf Mini", "Dwarf 3", "Dwarf 2", "Celestron Origin",
    "Unistellar eVscope 1 / eQuinox 1", "Unistellar eVscope 2 / eQuinox 2",
    "Unistellar Odyssey / Odyssey Pro",
]

FILTER_OPTIONS_MAP = {
    "ZWO Seestar S30": ["No Filter (Broadband)", "LP (Narrowband)"],
    "ZWO Seestar S30 Pro": ["No Filter (Broadband)", "LP (Narrowband)"],
    "ZWO Seestar S50": ["No Filter (Broadband)", "LP (Narrowband)"],
    "Dwarf Mini": ["Astro filter (UV/IR)", "Dual-Band"],
    "Dwarf 3": ["Astro filter (UV/IR)", "Dual-Band"],
    "Dwarf 2": ["Astro filter (UV/IR)"],
    "Celestron Origin": ["No Filter (Broadband)"],
    "Unistellar eVscope 1 / eQuinox 1": ["No Filter (Broadband)"],
    "Unistellar eVscope 2 / eQuinox 2": ["No Filter (Broadband)"],
    "Unistellar Odyssey / Odyssey Pro": ["No Filter (Broadband)"],
}

DUALBAND_ARGS = ["-narrowband", "-rwl=656.28", "-rbw=18", "-gwl=500.70",
                 "-gbw=30", "-bwl=500.70", "-bbw=30"]
FILTER_COMMANDS_MAP = {
    "ZWO Seestar S30": {"No Filter (Broadband)": ["-oscfilter=UV/IR Block"],
                        "LP (Narrowband)": ["-oscfilter=ZWO Seestar LP"]},
    "ZWO Seestar S30 Pro": {"No Filter (Broadband)": ["-oscfilter=UV/IR Block"],
                            "LP (Narrowband)": ["-oscfilter=ZWO Seestar LP"]},
    "ZWO Seestar S50": {"No Filter (Broadband)": ["-oscfilter=UV/IR Block"],
                        "LP (Narrowband)": ["-oscfilter=ZWO Seestar LP"]},
    "Dwarf Mini": {"Astro filter (UV/IR)": ["-oscfilter=UV/IR Block"],
                   "Dual-Band": DUALBAND_ARGS},
    "Dwarf 3": {"Astro filter (UV/IR)": ["-oscfilter=UV/IR Block"],
                "Dual-Band": DUALBAND_ARGS},
    "Dwarf 2": {"Astro filter (UV/IR)": ["-oscfilter=UV/IR Block"]},
    "Celestron Origin": {"No Filter (Broadband)": ["-oscfilter=UV/IR Block"]},
}

SPCC_SENSOR_MAP = {
    "ZWO Seestar S30 Pro": "Sony IMX585",
    "Dwarf 3": "Sony IMX678",
    "Dwarf Mini": "Sony IMX662",
    "Unistellar eVscope 1 / eQuinox 1": "Sony IMX224",
    "Unistellar eVscope 2 / eQuinox 2": "Sony IMX415",
    "Unistellar Odyssey / Odyssey Pro": "Sony IMX415",
}

TELESCOPE_HEADER_MAP = {
    "ZWO Seestar S30 Pro": "ZWO Seestar S30 Pro",
    "ZWO Seestar S30": "ZWO Seestar S30",
    "Seestar S50": "ZWO Seestar S50",
    "Seestar S30": "ZWO Seestar S30",
    "S50": "ZWO Seestar S50",
    "DWARF mini": "Dwarf Mini",
    "DWARFIII": "Dwarf 3",
    "DWARF 3": "Dwarf 3",
    "DWARFII": "Dwarf 2",
    "DWARF II": "Dwarf 2",
    "Origin": "Celestron Origin",
    "eVscope v1.0": "Unistellar eVscope 1 / eQuinox 1",
    "eVscope v2.0": "Unistellar eVscope 2 / eQuinox 2",
    "odyssey": "Unistellar Odyssey / Odyssey Pro",
}

# =============================================================================
#  SENSOR PROFILES  (from VeraLux HyperMetric Stretch)
# =============================================================================

SENSOR_PROFILES = {
    "Rec.709 (Recommended)": (0.2126, 0.7152, 0.0722),
    "ZWO Seestar S50 (IMX462)": (0.3333, 0.4866, 0.1801),
    "ZWO Seestar S30": (0.2928, 0.5053, 0.2019),
    "Sony IMX571 (ASI2600/QHY268)": (0.2944, 0.5021, 0.2035),
    "Sony IMX455 (ASI6200/QHY600)": (0.2987, 0.5001, 0.2013),
    "Sony IMX585 (STARVIS 2)": (0.3431, 0.4822, 0.1747),
    "Sony IMX662 (STARVIS 2)": (0.3430, 0.4821, 0.1749),
    "Sony IMX678 (STARVIS 2)": (0.3426, 0.4825, 0.1750),
    "Sony IMX533 (ASI533)": (0.2910, 0.5072, 0.2018),
    "Sony IMX224 (ASI224)": (0.3402, 0.4765, 0.1833),
    "Canon EOS (Modern)": (0.2600, 0.5200, 0.2200),
    "Nikon DSLR (Modern)": (0.2650, 0.5100, 0.2250),
    "Narrowband HOO": (0.5000, 0.2500, 0.2500),
    "Narrowband SHO": (0.3333, 0.3400, 0.3267),
}
DEFAULT_PROFILE = "Rec.709 (Recommended)"
REC709_WEIGHTS = SENSOR_PROFILES[DEFAULT_PROFILE]


def luminance(planar_rgb, weights=REC709_WEIGHTS):
    """Weighted per-channel luminance of a (3, H, W) planar RGB array.

    Shared helper — replaces several previously-duplicated inline copies
    of the same "wr*R + wg*G + wb*B" formula (NebulaChrome palette recolor,
    Final Touch saturation). Defaults to Rec.709 weights, matching the
    sensor-profile table above.
    """
    wr, wg, wb = weights
    return wr * planar_rgb[0] + wg * planar_rgb[1] + wb * planar_rgb[2]

TELESCOPE_TO_PROFILE = {
    "ZWO Seestar S50": "ZWO Seestar S50 (IMX462)",
    "ZWO Seestar S30": "ZWO Seestar S30",
    # User preference: the S30 Pro uses the dedicated Seestar S30 stretch
    # profile as its default (not the generic IMX585 sensor weights).
    "ZWO Seestar S30 Pro": "ZWO Seestar S30",
    "Dwarf 3": "Sony IMX678 (STARVIS 2)",
    "Dwarf Mini": "Sony IMX662 (STARVIS 2)",
}


STAGES = ["1. Preprocess", "2. Crop", "3. Remove Green (SCNR)",
          "4. Auto Gradient Removal", "5. Remove Background",
          "6. Remove Stars", "7. Denoise", "8. Hubble Palette",
          "9. Stretch", "10. Histogram Fine-Tune", "11. Final Touch",
          "12. Annotate", "13. Watermark"]
(IDX_PP, IDX_CROP, IDX_SCNR, IDX_AGR, IDX_BGE, IDX_STARS, IDX_DEN, IDX_PAL,
 IDX_STR, IDX_HIST, IDX_TOUCH, IDX_ANN, IDX_WM) = range(13)

WATERMARK_POSITIONS = ["Bottom-Right", "Bottom-Left", "Bottom-Center",
                       "Top-Right", "Top-Left", "Top-Center"]

# Synthetic palette mixes from dual-band OSC data.
# Each output channel = w_ha * Ha  +  w_oiii * OIII
PALETTE_PRESETS = {
    "HOO — natural bicolor": {"R": (1.0, 0.0), "G": (0.0, 1.0), "B": (0.0, 1.0)},
    "SHO — classic Hubble": {"R": (1.0, 0.0), "G": (0.3, 0.7), "B": (0.0, 1.0)},
    "SHO — golden dynamic": {"R": (1.0, 0.0), "G": (0.6, 0.4), "B": (0.0, 1.0)},
    # Blue-highlight look: G keeps mostly OIII while B gets boosted OIII,
    # pulling teal/blue structures apart from the greens like classic HST work.
    "SHO — blue highlights": {"R": (1.0, 0.0), "G": (0.35, 0.65), "B": (0.0, 1.3)},
    "Custom": None,
}
PALETTE_TO_PROFILE = {
    "HOO — natural bicolor": "Narrowband HOO",
    "SHO — classic Hubble": "Narrowband SHO",
    "SHO — golden dynamic": "Narrowband SHO",
    "SHO — blue highlights": "Narrowband SHO",
    "Custom": "Narrowband SHO",
}
