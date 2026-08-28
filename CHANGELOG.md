# S30 Pro Pipeline — Changelog

## 2.1.2

* **Added: diagnostics when Denoise's "GPU acceleration" is checked but
  the run still uses CPU.** `graxpert_helpers.make_onnx_session()`
  previously fell back to `CPUExecutionProvider` silently on any
  exception, with no way to tell whether an accelerator was ever
  attempted. It now records which providers were actually requested
  and, if session creation raised, the exception itself
  (`LAST_ONNX_REQUESTED_PROVIDERS`, `LAST_ONNX_FALLBACK_ERROR`). The
  Denoise stage's completion log surfaces this whenever GPU was
  requested but the result was CPU — distinguishing "CoreML raised an
  error", "CoreML was accepted but the session still reports CPU as
  active" (possibly a stale cached provider decision in Siril's own
  `siril_onnx.conf`), and "sirilpy didn't offer a GPU provider at all"
  — three different situations that previously looked identical.

## 2.1.1

* **Fixed confusing wording: the enable checkbox at the top of each
  stage's pane was also labeled "Run this stage"** — identical text to
  the button at the bottom of the pane that actually executes the
  stage immediately, making the two easy to mix up. The checkbox only
  toggles whether the stage participates in Run Full Pipeline; it
  doesn't run anything by itself. Renamed to "Enable stage", matching
  the wording already used by the "Enable all stages"/"Disable all
  stages" bulk actions in the overflow menu.

## 2.1.0

* **Added: live percentage and elapsed-time readout next to the
  progress bar.** The ribbon's progress bar is shortened (200px → 120px,
  its own built-in percentage text turned off) to make room for two new
  labels beside it: a percentage (updated on every progress() call, same
  as the bar) and an elapsed-time clock that ticks once a second on its
  own timer — so it stays live even during stages that go a long
  stretch between progress updates, rather than only updating when one
  happens to fire.

## 2.0.4

* **Improved: the split preview's right half no longer goes blank for a
  stage that hasn't run yet.** For a stage with no snapshot,
  `_refresh_preview()`'s background fetch was showing the current Siril
  image as "before" with `None` for "after" — leaving the right half of
  the split view black, which read as broken rather than "nothing to
  compare yet". Now shows the same image on both sides instead, so the
  split divider still works (drag it and both halves match) without
  implying a stage result that doesn't exist. Each stage's before/after
  once it *has* run is unchanged — this only affects the not-yet-run
  case.

## 2.0.3

* **Fixed: "Run this stage" could stall with nothing happening, even on
  the very first stage.** Introduced by 2.0.2: opening the window kicks
  off a background `PreviewFetchWorker` fetch for whichever stage has no
  snapshot yet (stage 1, on a fresh launch), and `_launch()` had no guard
  against starting the stage-execution `Worker` while that fetch was
  still in flight — two threads then called into the same Siril
  connection at once, which hangs rather than errors. `_launch()` now
  queues the run request instead (`_pending_launch`) if a preview fetch
  is in progress, and fires it from the fetch's completion handler once
  the connection is free.

## 2.0.2

* **Fixed: switching to a stage that hasn't run yet could briefly stall
  the window.** `_refresh_preview()` fires on every stage-navigation
  click (rail or stepper); for a stage with no snapshot yet it falls
  back to fetching Siril's current full-resolution image and running it
  through the display stretch, the same real work that used to block
  the launch itself before v2.0.1's fix — except this path runs on
  every click, not just once at startup. Moved that fetch to a new
  `PreviewFetchWorker` background thread so stage navigation no longer
  freezes the window while it runs. Only one fetch runs at a time: a
  click that arrives while one is already in flight, or while a stage
  is actively executing (sharing the same Siril connection as the
  pipeline's stage-execution thread), is queued and re-run once the
  in-flight work finishes instead of overlapping it.

## 2.0.1

* **Fixed: the pipeline window could take a long time to even appear
  after launching.** The v2 window shell's `_build_ui()` ended with an
  unconditional call to `_refresh_preview()`, which fetches Siril's
  *full-resolution* current image and runs it through the display
  stretch/QImage conversion — real work, easily a few seconds on a
  typical smart-telescope stack (tens of megapixels). Since
  `_build_ui()` runs inside `__init__()`, which runs *before* the
  window is shown, that whole fetch+stretch blocked the window from
  appearing at all, on every launch where Siril already had an image
  loaded (the normal case — you stack, then launch the pipeline).
  Deferred with `QTimer.singleShot(0, ...)` so the window now appears
  immediately; the preview populates a beat later instead of gating
  the launch itself.
* **Fixed: startup crash "no FITS image" right after opening the
  pipeline**, before loading anything. `_get_current_image()` called
  sirilpy's `get_image_pixeldata()`, which raises its own `SirilError`
  directly when nothing's loaded (it never returns `None`) — the
  existing `if data is None: raise RuntimeError(...)` guard never
  caught that case, so the exception propagated uncaught out of the
  new startup preview-refresh call and crashed window construction.
  Normalized to `RuntimeError` so every existing caller that already
  expects/catches that (the preview refresh, "Use Siril's image", and
  every stage's execution on the worker thread) is covered.

## 2.0.0

* **Rebuilt window: new dark "Industry" theme, permanent stage rail,
  one-stage-at-a-time settings pane.** The 13 stages become a permanent
  left rail (grouped Stack / Clean / Stretch / Finish) that doubles as
  the progress display, replacing the old scrolling column of thirteen
  stacked cards — the settings panel now shows one stage at a time.
  Each stage keeps two or three controls visible in the pane with the
  rest behind an ADVANCED disclosure (collapsed by default, with a note
  on how many settings are inside and whether they're at defaults).
* Image info and run progress move to a session ribbon across the top
  of the window. The four bottom buttons collapse to one primary
  (Run Full Pipeline), one secondary (Save image) and an overflow menu;
  settings JSON import/export gets a permanent home in the rail footer.
  "Use Siril's image" moves to the top of each stage as a
  "Starting from" row.
* "Expand All" / "Collapse All" are gone — with one stage on screen at
  a time there's nothing to expand; their enable/disable job moved into
  the overflow menu ("Enable all stages" / "Disable all stages").
* New dark theme (`theme.py`): square corners, hairline borders, one
  steel-blue accent on a near-black ground — replaces the rounded,
  filled 1.x look. Every 1.x widget object name is preserved so
  un-migrated stage code keeps working unchanged.
* Window adapts below 1180px width (rail collapses to numbers only,
  ribbon detail tucks behind a disclosure); minimum window size is now
  960x640.
* New internal modules: `s30pro_pipeline/ui_shell.py` (`StageRail`,
  `SessionRibbon`, `PaneHeader`, `ActionBar`, `AdvancedSection`) and
  `s30pro_pipeline/ui_v2.py` (`UiV2Mixin`, providing the new
  `_build_ui`/`_stage_box`). The old `_build_ui`/`_stage_box` in
  `S30Pro_Pipeline.py` are removed now that every stage boots on v2.

## 1.56.0

* **New: "📥 Import annotation details..." button.** The companion
  `annotated_*.json` file 1.55.0 started auto-saving with every
  Annotate run can now be loaded back in — this button reads a
  previously saved JSON and redraws exactly those objects onto the
  current un-annotated base canvas, with no catalogue queries or plate
  solving involved. Meant for re-applying a saved annotation set back
  onto the same image it came from (reopening this session later, or
  after a later stage that doesn't move pixels), not a general "restore
  any annotation onto any image" tool — a warning appears (import still
  proceeds) if the file's saved image size doesn't match the current
  one, since every object's position would then be off. Like "Select
  objects to show...", importing fully replaces what's currently shown
  rather than adding to it.
* The JSON export gained two fields (`label_font_scale`,
  `label_thickness_px`) needed for a full round-trip reconstruction —
  previously the font size/stroke thickness used to draw each label
  weren't recorded at all, which the new Import feature surfaced as a
  gap. Older `annotated_*.json` files (from 1.55.0) missing these
  still import fine, falling back to generic defaults.

## 1.55.0

* **New: Annotate now auto-saves a companion JSON file with every run.**
  Alongside the usual `annotated_YYYY-MM-DD_HHMM.jpg`, the stage now
  also writes `annotated_YYYY-MM-DD_HHMM.json` — a machine-readable
  record of every labeled object in that run: name, catalogue kind,
  RA/Dec (degrees), apparent size (arcmin), OpenNGC detail fields
  (type/magnitude/constellation) when available, and the full on-image
  style that produced the picture (pixel position, marker style,
  marker/cross/text colors as `[R, G, B]`, thickness, cross geometry,
  label lines). Written automatically at the end of every actual Run —
  same persistence point as the JPG itself, so later interactive edits
  ("Select objects to show...", "Remove all annotations", "🖱 Pick
  object on image...") update the live preview but don't rewrite this
  file; the next Run does. A JSON-write failure is logged but never
  fails the Annotate run — the JPG is already safely saved by then
  either way.

## 1.54.2

* **README: Troubleshooting and Changelog's "Recent highlights" tables
  are now collapsed by default** (`<details>`/`<summary>` — GitHub
  renders these as native click-to-expand disclosure widgets), so the
  README reads shorter for anyone scrolling through it top to bottom.
  Both section headings stay visible and expand on click; nothing was
  removed, just tucked behind a fold.

## 1.54.1

* **"Expand All"/"Collapse All" now also select/deselect every stage,
  and one row with "Import settings".** Follow-up to 1.54.0: those two
  buttons previously only changed visibility, leaving every stage's
  own enabled checkbox untouched — they now check/uncheck every
  stage too, matching the header-checkbox behavior already in place
  (checking a stage expands it, unchecking one collapses it). Also
  fixed an edge case this surfaced: a stage that's already sitting at
  the target checked state (e.g. Auto Gradient Removal, off by default
  but expanded) wouldn't fire its usual checkbox->arrow sync, so
  "Collapse All" could silently leave it expanded — both buttons now
  set each stage's checkbox and arrow directly instead of relying on
  that signal firing. "Import settings", "Expand All", and "Collapse
  All" also moved onto one row with equal-width buttons, instead of
  two rows with "Import settings" alone on top.
* **New: README badges** — version, license, minimum Siril version,
  supported platforms, and last-commit date, right under the title.

## 1.54.0

* **New "⌄ Expand All" / "⌃ Collapse All" buttons**, next to "⤒ Import
  settings" at the top of the left panel. Show or hide every stage's
  settings at once — a pure visibility toggle, exactly like clicking
  each stage's own ▸/▾ arrow one at a time, and doesn't change which
  stages are actually enabled to run.

## 1.53.1

* **Unchecking a stage now collapses it too.** 1.53.0's new ▸/▾ arrow
  auto-expanded a stage when its header checkbox was checked, but left
  it expanded if you later unchecked it. It now stays in sync both
  ways: checking a stage expands it, unchecking one collapses it back
  out of the way — so the panel stays as short as possible once you've
  settled on which stages you want. The arrow itself still works
  independently at any time, so you can still peek at a stage's
  settings without enabling it.

## 1.53.0

* **Stage cards are now collapsible, defaulting to a clean beginner
  layout.** Each of the 13 stage cards now has its own ▸/▾ arrow next
  to the title, independent of the header checkbox that controls
  whether the stage actually runs — clicking it shows or hides that
  stage's "Use Siril's image" button and all of its own settings,
  without changing whether it's enabled. Stages 1 (Preprocess), 2
  (Crop), 3 (Remove Green/SCNR), 4 (Auto Gradient Removal), 5 (Remove
  Background), 7 (Denoise), and 9 (Stretch) — the minimum path from raw
  subs to a finished image — start expanded; the other 6 (Remove Stars,
  Hubble Palette, Histogram Fine-Tune, Final Touch, Annotate,
  Watermark) start collapsed, out of the way until you want them.
  Checking a stage's header checkbox always expands it too, so enabling
  something never leaves it hidden; unchecking never auto-collapses,
  so a stage you've opened to look at stays open either way.
* **New: "Beginner quick path" section in the HTML guide's "The 13
  Stages Explained" page.** A short table + checklist covering just
  stages 1, 2, 3, 4, 5, 7, and 9 — one line of guidance each — for a
  first-time user who wants a complete, presentable result without
  reading the full 13-stage breakdown first. The full stage-by-stage
  explanations remain right below it for anyone who wants to go
  further.

## 1.52.1

* **Fixed: per-object style editor's Undo could skip a step after
  picking colors.** Found during a review pass over the Annotate
  panel's script. The dialog's checkpoint-based undo stack checkpointed
  *before* applying a picked Marker/Cross/Text color instead of after
  (every other field checkpoints after its value changes) — so the
  snapshot taken right after a color pick still held the stale color,
  and a second color pick in the same session would silently drop the
  in-between state from the undo history. No user-visible symptom
  besides "Undo" occasionally reverting two changes at once after
  multiple color picks; fixed by moving the checkpoint to after the
  color is applied, matching every other field in the dialog.

## 1.52.0

* **Fixed: "Label distance" control had no effect for Circle-style
  markers.** The Annotation panel's "Label distance (× radius)" slider,
  and its equivalent in the per-object 🎨 style editor, silently did
  nothing unless an object's marker style was Open Cross — now it
  applies to every marker style, and the panel-level control has moved
  out of the Open Cross-only section into the general style row (right
  after "Marker style") so it's always visible, matching its now-
  universal behavior.
* **Fixed: label distance couldn't go small enough.** Both label-distance
  sliders only allowed 0 and up, but 0 still left a fixed ~10px gap
  between label and marker — there was no way to ask for anything
  closer. Both sliders now allow negative values (down to -2.0×radius),
  which pull the label in tighter than the old minimum; a floor clamp
  keeps the label from ever colliding with or crossing through the
  marker itself, even at the most negative setting.
* **Custom lines / Label lines are now a text box, not a list.** The
  Annotation panel's "Custom lines" section and the per-object 🎨 style
  editor's "Label lines" section both used to require adding one line
  at a time via a text field + "+ Add" button. Both are now a single
  multi-line text box — type or paste as many lines as you want, one
  per row, and each row becomes its own label line (blank rows are
  skipped). The per-object editor's text box keeps its own native
  Ctrl+Z for undoing text edits, on top of the dialog's existing Undo
  button for every other setting.

## 1.51.0

* **New feature: manually pick objects on the image.** A new "🖱 Pick
  object on image..." button on the Annotate panel arms a click-to-add
  mode on the preview — click any point on the image and a new object
  is added right there, using its RA/Dec (from the same plate-solve WCS
  the stage already uses) as its default name (e.g. "RA 83.822° Dec
  -5.391°"), styled with the Annotation style panel's current settings.
  Stays armed for adding several points in a row; click the button
  again or press Esc to stop. The new object shows up in "Select
  objects to show..." like any catalogue object, where its 🎨 editor
  can rename it (the RA/Dec default is just a starting point — edit the
  first label line to call it whatever you like), restyle it, or remove
  it. (`CompareView` gained a reusable single-click "point pick" mode
  alongside its existing crop rubber-band selection mode, for this.)
* **Per-object style editor cleanup.** "Circle color..." / "Circle
  thickness" are renamed "Marker color..." / "Marker thickness". Text
  color moved up to sit directly under Marker thickness, ahead of every
  Cross-specific control (color, thickness, gap, arm, label position/
  distance) — so the two most commonly used color pickers (Marker,
  Text) are right at the top, before any of the Open Cross-only
  settings below them.

## 1.50.0

* **Open Cross "Label distance (× radius)" default lowered from 0.3 to
  0.1** — a tighter default spacing between the label and the marker
  center, closer to what most objects need; still a 0.1-step slider from
  0 to 3, so any distance remains reachable.
* **New: per-object text color, in the 🎨 per-object style editor.** A
  "Text color..." picker alongside the existing Circle/Cross color
  pickers lets one object's label text use a different color than its
  marker(s) or the panel's per-catalogue default — independent of every
  other object, same as the rest of that dialog.
* **New: "🔄 Update" button inside the per-object style editor.** Applies
  the dialog's current settings to the live preview immediately, without
  closing the dialog — nudge a value, see the result, keep adjusting.
  Cancelling after clicking Update now correctly reverts the object to
  exactly what it held before the dialog opened.
* **New: "↶ Undo" button inside the per-object style editor.** Steps
  back through the dialog's own edit history one field change at a
  time — marker style, either color, thickness, cross geometry, label
  position/distance, or label-line edits — independent of whether
  Update has been clicked. "↺ Reset to panel default" now counts as a
  single undoable step too.
* **New: "🔄 Update preview" button on the Annotate panel itself.**
  Re-renders every currently shown object using the Annotation style
  panel's *current* settings (marker style, colors, thickness, cross
  geometry, label detail lines) without re-querying any catalogue or
  re-running plate solving — much faster than the full Run button for
  iterating on how things look. Resets every object to the panel
  defaults, so per-object 🎨 overrides are discarded by this (same
  trade-off as re-running the stage, just far quicker); doesn't affect
  constellation lines, which still need a full re-run to change.

## 1.49.0

* **New feature: per-object annotation style overrides.** Every row in
  "☑ Select objects to show..." now has a 🎨 button that opens a small
  editor for that one object — marker style (Circle/Open Cross/both),
  circle and cross colors and thickness, cross gap/arm/label position/
  label distance, and the label's text lines (add/edit/remove freely,
  same as the panel's own custom-lines list) — completely independent
  of the Annotation style panel, which keeps applying to every other
  object. Edits apply immediately to the live preview, same as toggling
  visibility, and a "↺ Reset to panel default" button in the editor
  discards the override and recomputes that object's style/label lines
  exactly as a fresh Annotate run would. Cancelling "Select objects to
  show..." now also undoes any per-object style edits made while it was
  open, not just visibility changes. Like the rest of "Select objects
  to show...", overrides are a post-run preview/export adjustment —
  re-running the Annotate stage regenerates every object from the panel
  defaults, so overrides don't persist across a re-run (nor through
  Export/Import settings, which only ever captured panel-level state).

## 1.48.0

* **Annotate panel reorganized into a clear 3-step flow.** The stage card
  is now three collapsible/ordered sections instead of one long wall of
  controls: "① Objects to show" (catalogue toggles, star magnitude limit,
  online BSC, and all constellation-line settings, including "Select
  constellations..."), "② Annotation style" (label size, marker style,
  the Circle/Open Cross style panels, Label detail, and the overlay
  toggle — sub-panels still show/hide immediately as the marker style
  dropdown changes), and the existing Run/Undo row plus action buttons
  (Save image, Select objects, Remove all) for updating the result
  in place after running.
* **Open Cross style moved after the object catalogue section** (was
  previously above it), so the panel now reads top-to-bottom in the
  same order you'd actually use it: pick objects, then pick style.
* **New "Label distance (× radius)" control for Open Cross style.**
  Separate from the existing arm length, this adds extra breathing room
  between the label text and the marker center — a multiple of the
  marker's radius, on top of the arm length — so a label (especially a
  multi-line one from the Label detail feature) can be pulled further
  out to clear the cross's arms instead of crowding them. Defaults to
  0.3, matching the prior fixed spacing closely enough that existing
  saved settings look the same until adjusted. Round-trips through
  Export/Import settings.

## 1.47.0

* **New feature: OpenNGC label detail + custom label lines for Annotate.**
  Object labels can now show more than just the name. A new "Label
  detail" panel offers four OpenNGC-sourced fields — object type (e.g.
  "Nebula", "Open cluster"), magnitude, constellation, and apparent size
  — each as its own checkbox; any combination can be on at once. There's
  also a "Custom lines" list where you can type your own extra lines
  (double-click to edit, "+ Add"/"- Remove" to manage the list) — handy
  for notes that don't come from a catalogue at all. Every enabled field
  and custom line is drawn as its own line below the object name, so a
  fully-loaded label reads name, then type, then magnitude, then
  constellation, then size, then any custom lines, top to bottom. Each
  line is horizontally aligned to match whichever side of the marker the
  label was placed on (left-aligned when the label sits to the east,
  right-aligned when it sits to the west), so a multi-line block still
  reads as clearly "attached" to its marker instead of drifting off to
  one side. For Open Cross marker style, the N or S arm (whichever side
  the label landed on) automatically stretches longer as more lines are
  added, so the cross visually reaches toward the taller label instead
  of stopping short of it. All of the above round-trips through Export/
  Import settings.

## 1.46.0

* **New feature: Open Cross marker style for Annotate, alongside the
  existing circle.** A new "Marker style" dropdown offers Circle (the
  original, unchanged default), Open Cross, or both together. The Open
  Cross is a reticle-style marker made of 4 short strokes (N/S/E/W) that
  stop short of the object's center on both ends, so it never covers
  the star or DSO it's pointing at — unlike the circle, which sits
  right on top of it. Both styles get independent thickness (auto, or a
  fixed pixel value) and color controls, each with its own "Custom
  color" toggle — off keeps each catalogue's own color, matching the
  swatches next to the catalogue checkboxes, same as before; on
  overrides every marker of that style with a single picked color. The
  cross's gap-from-center and arm length are set as multiples of the
  marker's own radius (not fixed pixels), so they scale automatically
  with each object's apparent size the same way the marker radius
  already does. Since an open cross leaves its 4 diagonal corners clear
  while a circle surrounds the object on every side, there's also a new
  "Label position" option (NE/NW/SE/SW, or Auto) for Open Cross style —
  picking a corner tells the existing overlap-avoiding label placement
  to prefer that spot first, instead of always working out the least-bad
  position on its own. All of the above round-trips through Export/
  Import settings.

## 1.45.0

* **New feature: Comet Stack mode.** A fourth option in Preprocess's
  Stacking method dropdown, alongside Average/Median/Sum, for comet and
  asteroid targets. The problem it solves: a moving object needs two
  *different* registrations from the same subs — one aligned on the
  stars (so the comet trails/smudges) and one aligned on the comet's own
  motion (so the stars trail and the comet is sharp) — and Siril has no
  single stacking mode that produces both from one sequence. Comet Stack
  registers the sequence on the stars, runs a whole-sequence background
  removal and star removal (`seqstarnet`) to isolate the comet, then
  re-applies the *original* star-based registration to both the starless
  (comet) and the background-subtracted (star) sequences with matched
  framing — so the two eventual stacks come out pixel-dimension-matched
  and ready to recombine. One wrinkle had to be worked around by hand:
  `seqstarnet` regenerates its output sequence's `.seq` file from scratch
  and drops the registration data Siril had already computed for it —
  there's no console command to reattach it, so this splices it back in
  directly as a text-file patch (new `_splice_seq_registration()` helper,
  with its own unit tests) before continuing. Adjustable rejection
  sigmas (default 5.0/5.0) and background-removal degree/samples are
  exposed in a new settings group that appears when Comet Stack is
  selected; picking it also auto-disables (and greys out, with a
  tooltip) the Remove Background and Remove Stars stages below, since
  Comet Stack already does both of those itself as part of its own
  workflow — switching back to another stacking method restores whatever
  those two checkboxes were set to before.

  Two steps genuinely can't be scripted and need a few seconds of manual
  work in Siril's own window — the pipeline pauses for each with clear
  on-screen instructions and a Continue button:
  1. **Comet registration** — Siril's "Comet/Asteroid registration" tool
     needs you to pick the comet's nucleus on the first and last frame by
     hand; there's no equivalent console command.
  2. **Star Recomposition** — combining the comet stack and star stack
     into one sharp image is a GUI-only tool (Image Processing → Star
     Processing → Star Recomposition) with no scriptable counterpart
     either.

  Once you click Continue after Star Recomposition, the rest of the
  pipeline (Stretch, Histogram, Final Touch, Annotate, Watermark, ...)
  runs completely unchanged on the recomposited result, same as any
  other stacking method.

## 1.44.0

* **Internal refactor: split the ~6,700-line `UnifiedPipelineWindow` class
  into a base orchestrator plus per-stage mixin classes (Phase 2 of the
  two-phase modularization started in 1.43.0).** No user-facing behavior
  changes — this is pure code motion. The single monolithic window class
  previously held all thirteen pipeline stages' UI-building and execution
  logic directly; each stage's methods (both its `_build_stage*` UI
  construction and its `_exec_stage*` run logic, which used to live in
  two separate, far-apart sections of the file) now live together in
  their own file under a new `s30pro_pipeline/stages/` subpackage —
  `Stage1Mixin`, `CropMixin`, `ScnrMixin`, `AgrMixin`, `BgeMixin`,
  `DenoiseMixin`, `StarsMixin`, `PaletteMixin`, `StretchMixin`,
  `HistMixin`, `TouchMixin`, `AnnotateMixin`, `WatermarkMixin` — and
  `UnifiedPipelineWindow` now composes them via multiple inheritance.
  Shared orchestration (settings import/export, run-all, undo/snapshot
  bookkeeping, image I/O helpers) stays in the base class. The main
  script dropped from about 6,970 to about 1,770 lines; the new stage
  files range from 55 to about 1,300 lines each. Verified with the full
  87-test suite plus a per-file static-analysis pass (compile +
  undefined-name check on every new file individually, not just the
  combined result) before and after the split. If you keep a local copy
  of this project, the `s30pro_pipeline/` folder (now including its
  `stages/` subfolder) still needs to be copied alongside
  `S30Pro_Pipeline.py` — same requirement as 1.43.0, nothing new to do
  if you already copy the whole folder.

## 1.43.0

* **Internal refactor: split the single 8,862-line script into a small
  package (Phase 1 of a two-phase modularization).** No user-facing
  behavior changes. Ten self-contained pieces that don't depend on the
  main window's Qt state — the VeraLux stretch core, GraXpert helper
  functions, the auto-gradient-removal math, the stylesheet, shared
  constants, the Bortle-scale estimator, catalog/constellation lookup
  data, and reusable UI widgets (`CompareView`, `HistogramEditor`,
  `Worker`) — now live under a new `s30pro_pipeline/` folder next to
  `S30Pro_Pipeline.py`, imported explicitly rather than pasted inline.
  The main script (still the one you point Siril's Scripts menu at)
  dropped from 8,862 to about 6,970 lines. Verified with the full
  87-test suite plus a static-analysis pass for missing imports before
  and after the split; the remaining ~6,700-line main window class is
  unchanged and is the target of a follow-up Phase 2 split. If you keep
  a local copy of this project, make sure the new `s30pro_pipeline/`
  folder is copied alongside `S30Pro_Pipeline.py` — the script won't
  run without it.

## 1.42.0

* **Constellation lines and names now have independent colors, plus a
  color-preset dropdown.** Annotate's constellation options previously
  shared one color for both the stick-figure lines and the name labels.
  Now there's a separate "Line color..." and "Name color..." picker
  (each with its own swatch), and a new "Color preset" dropdown with six
  curated matched line/name color schemes (Pale Lavender, Sky Blue, Warm
  Gold, Classic White, Muted Red, Soft Green) to quick-pick from instead
  of always reaching for the color dialog. Picking a preset sets both
  colors at once; manually picking either color afterward switches the
  dropdown back to "Custom". Both colors (and the preset name, for
  round-tripping) are saved/restored with Export/Import settings.

## 1.41.0

* **Blind Astrometry.net solve as a further fallback for Milky Way Mode.**
  Confirmed by hand that Milky Way Mode's ~60-70 degree stacked field
  reliably fails `-localasnet`'s normal header-hinted near-search (using
  the header's RA/Dec and focal/pixel size as a starting guess, searching
  only a small cone around it) even with wide-field index files
  installed, but solves once asked to search completely blindly. When
  stacking method is "Median (Milky Way Mode)" and the plain `-localasnet`
  attempt (added in 1.40.0) also fails, the SPCC plate-solve step now
  retries once more with `-blindpos -blindres` before giving up. Only
  runs on the final stacked image (once), not per-frame — plate solving
  isn't needed for Milky Way Mode's per-frame registration, which already
  uses star-based alignment.

## 1.40.0

* **Plate-solving fix for stacked Seestar images that kept failing to
  solve** ("No valid plate-solve solution in the image header" when
  Annotate ran afterward), even though the same image solves fine on
  nova.astrometry.net. The Preprocess stage's SPCC plate-solve step now
  retries once with `-localasnet` (local Astrometry.net's `solve-field`)
  if Siril's own solver fails, before giving up — requires a local
  Astrometry.net install (ansvr on Windows, `brew install astrometry-net`
  on Mac) with index files covering the field; without one, the fallback
  simply fails too and SPCC/Annotate are skipped as before, with a log
  message explaining why.
* **Correct optics for "Median (Milky Way Mode)" wide-camera stacking.**
  All plate-solve calls (registration, SPCC, and combine-with-existing-
  master) now pass the Seestar wide camera's real focal length (6mm) and
  effective pixel size (~1.7 micron) via `-focal=`/`-pixelsize=` when
  Milky Way Mode stacking is selected, instead of trusting whatever
  FOCALLEN/XPIXSZ ended up in the header — some firmware versions carry
  over the main tele camera's values (160mm / 2.9 micron) into wide-
  camera FITS headers, which is enough on its own to make the solve fail.

## 1.39.0

* **Control panel narrowed to roughly 1/3 of the window width, with
  every stage's layout reworked to stay fully readable at that width —
  no horizontal scrolling needed to see any option.** Splitter now uses
  1:2 stretch factors (was a fixed-width left panel absorbing none of a
  window resize) so the ~1/3:2/3 ratio holds as the window is resized,
  not just on first launch. Specific fixes:
  - Every stage header's "Use Siril's image" button moved to its own
    row below the title (was sharing a row with it) — several stage
    titles ("Preprocess — Smart Telescope Stacking", "Annotate — Stars
    & Deep-Sky Objects") were long enough to force the header row wider
    than the panel on their own; the title label also now wraps as a
    safety net.
  - Collapsed several wide multi-column parameter grids (Preprocess's
    Drizzle/Scale/Pixfrac row, mosaic distortion/background row,
    SPCC/Compression/Cleanup row; Stretch's Protect b/Convergence/Color
    grip/Linear exp row; Annotate's entire catalogue/constellation
    grid) to 2 columns (or one item per row), instead of 4-5 columns
    side by side.
  - Annotate's 4-button row ("Save annotated image.../Select objects to
    show.../Select constellations.../Remove all annotations") split
    into two 2-button rows, same fix already applied to the bottom
    Save/Export/Reset/Close row in 1.38.0.
  - Shortened several button/checkbox labels that don't wrap by default
    (QCheckBox/QPushButton text) and could otherwise get visually
    clipped at the narrower width — e.g. "Calculate Optimal Log D" →
    "Auto Log D", "Two-column layout (wider, thinner block)" →
    "Two-column layout", "All stars < mag limit (Siril's online Bright
    Star Catalogue)" → "All stars < mag limit (online BSC)" (full
    wording stays in each control's tooltip).
  - Tightened the global stylesheet slightly (button/combo/spinbox
    padding, base font 10pt → 9.5pt) to buy back a bit more horizontal
    room across every stage without changing any control's behavior.

## 1.38.0

* **The bottom 4 buttons (Save File / Export settings / Reset / Close
  Pipeline) are now split across two rows of 2 instead of one row of
  4** — a single row of four labeled buttons pushed the left panel
  wider than it needed to be. Order is unchanged: Save File / Export
  settings on top, Reset / Close Pipeline below.

## 1.37.0

* **Annotate: added constellation stick-figure lines.** New
  "Constellation lines" option draws lines between bright stars for
  whichever of the 88 IAU constellations are (at least partly) in the
  plate-solved field, with optional name labels. Line topology comes
  from an embedded dataset (adapted from the open-source d3-celestial
  project) — fully offline, no cache or internet needed, unlike the
  Messier/NGC/Sharpless catalogues above it. Configurable: line width,
  line color, a gap (in pixels) so lines don't touch the stars directly,
  whether to show names, and a "Select constellations..." dialog to
  leave specific ones out. This is a separate visual layer from the
  DSO/star markers — it's not affected by "Select objects to show..." or
  "Remove all annotations"; toggle "Constellation lines" and re-run to
  add or remove it. Note there's no single "official" IAU line set (the
  IAU only defines constellation boundaries, not connect-the-dots
  lines), so this is one commonly used stick-figure convention, not a
  definitive one.

## 1.36.0

* **Stacking method: "Median" is now labeled "Median (Milky Way Mode)"**
  in the dropdown, so the recommended choice for Seestar's Milky Way
  Mode is visible at a glance instead of needing to check the tooltip.
  Older exported settings JSON files that saved the plain "Median"
  value still restore correctly. Each option in the dropdown also now
  has its own tooltip that pops up while hovering it in the open list
  (previously only the closed combo box itself had one).
* **Button row reorganized: Export settings moved next to Save File /
  Close Pipeline, and a new Reset button added.** The bottom row is
  now Save File / Export settings / Reset / Close Pipeline (Import
  settings stays at the top). Reset resets every stage's settings to
  their defaults, clears all before/after previews and undo history,
  and asks you to pick a new session folder — for starting a fresh
  pipeline run without closing and reopening the window. Asks for
  confirmation first; doesn't touch anything already saved to disk or
  the image currently loaded in Siril.

## 1.35.0

* **Fixed: Median/Sum stacking crashed with "Cannot upscale or maximize
  framing with median stacking. Disabling" followed by "input images
  have different sizes. Stacking failed".** Siril's `-maximize` framing
  (pads every registered frame to the union/max canvas at stack time)
  only works with the Average+rejection method — Median and Sum reject
  it outright, and once disabled there was nothing left to reconcile
  frames of differing sizes, so stacking aborted. Now the registration
  apply step (`seqapplyreg`) uses `-framing=min` (crop every frame down
  to their common overlap) instead of `-framing=max` whenever Median or
  Sum is selected, guaranteeing uniform frame sizes without needing
  `-maximize` at all — and `-maximize`/`-feather`/`-overlap_norm` (all
  three require `-maximize`) are no longer passed to the Median stack
  command. Trade-off: Median/Sum results now cover only the area common
  to every frame, not the full union each frame individually touched —
  Average still gets the wider union canvas. Feather, Normalize on
  overlaps, and Stack weighting are now automatically greyed out
  whenever Median or Sum is selected, since none of them apply there.

## 1.34.0

* **Fixed: Preprocess's main registration step had no fallback when
  plate-solving failed** — `Image ... did not solve` (a real crash
  users hit with, e.g., Seestar's Milky Way Mode, whose field of view
  is far wider than a typical target and much harder for Siril's
  astrometric solver to handle per-frame). Whenever a local Gaia
  astrometry catalog is configured, registration always went through
  `seqplatesolve` with no way to disable it and no fallback if it
  failed — the previous code just logged a warning and moved on with
  whatever (possibly no) registration data existed, corrupting
  everything downstream. Now falls back to ordinary star-pattern
  registration (`register -2pass`) automatically when plate-solving
  fails, mirroring the same fallback pattern "Combine with existing
  master" already used for its own registration step.

## 1.33.0

* **Preprocess: "Stacking method" dropdown** — Average (rejection) /
  Median / Sum, default Average (rejection, unchanged from before).
  Previously the main lights stack was hardcoded to sigma-clip
  rejection average (`rej 3 3`). Median is now selectable and
  recommended for Seestar's Milky Way Mode subs and any other wide,
  satellite/plane-trail-prone shots — per ZWO's own guidance, median
  combine is more robust than sigma-clip rejection at erasing a trail
  that only appears in a handful of frames. Sum is also exposed for
  completeness (planetary/lucky-imaging use, not typically useful for
  deep-sky or Milky Way). Stack weighting (and its quality-metric
  choice) only applies to Average and is automatically greyed out when
  Median or Sum is selected, since Siril doesn't support weighting or
  rejection on those methods.

## 1.32.0

* **Watermark: integration time unit toggle.** The existing "Integration
  time" field now has a Minutes / Hours / Seconds dropdown (default:
  Minutes) controlling how the total exposure time is displayed in the
  watermark block — e.g. "180 min", "3.0 h", or "10800 s". The
  sub-count × per-sub-exposure detail (e.g. "360×30s") is still shown
  alongside it when available, regardless of unit.

## 1.31.0

* **Preprocess: "Normalize on overlaps" checkbox**, next to Feather in the
  mosaic settings — wires up Siril's `-overlap_norm` flag on the final
  `stack` call (requires `-maximize` framing, already used here).
  Computes the stack's normalization coefficients only from the regions
  where tiles/frames actually overlap, instead of from whole images —
  useful when tiles have very different content (e.g. one mostly
  nebula, another mostly blank sky) and a mosaic seam still shows up
  with plain normalization. Off by default (Siril's own docs note it's
  slower to compute and recommend trying without it first).
* **Preprocess: per-frame background removal now has a Degree spinner**
  (1–4, default 1) next to the "Per-frame background (mosaic seams)"
  checkbox. Previously the underlying `seqsubsky` call was hardcoded to
  a degree-1 (linear) polynomial; now the degree is user-adjustable, so
  a more complex per-panel gradient (e.g. radial vignetting-like
  falloff) that a flat linear tilt can't remove can be fit with a
  higher-order polynomial instead — matching Siril's own `subsky`
  degree options.

## 1.30.0

* **Crop stage: rotate before crop.** Added a Rotate (°) slider + number
  spinbox (-180° to 180°, 0.1° steps) to the Crop stage, applied via
  Siril's `rotate` command before any margin crop runs. Enabling only a
  rotation (no margins) still records and completes the stage.
* **New "Auto Gradient Removal" stage** (stage 4 of 13, inserted right
  before Remove Background — every stage after it renumbered
  accordingly). Ports the AutoGradientRemoval script's iterative
  robust background/gradient estimator directly into the pipeline as
  its own stage, with the same controls: Scale, Smoothness,
  Downsample, correction Mode (subtract/divide), structure Protection
  (threshold + amount) to keep stars/nebulae out of the background fit,
  and an optional Simplified polynomial model (with a Degree spinner)
  for faster/simpler gradients. Color images are corrected per-channel
  in parallel via a thread pool.
* **Remove Background (Siril subsky): preview & edit sample boxes.**
  New "🖼 Preview & edit sample boxes..." button opens an interactive
  canvas over the current image showing an editable grid of background
  sample boxes (green = kept, red = excluded). Click a box to toggle
  it, click empty space to add a new one, adjust new-box size, or
  Regenerate/Select All/Deselect All. Confirmed boxes are pushed to
  Siril via `set_image_bgsamples()` right before `subsky` runs, so
  subsky uses the curated boxes instead of its own automatic
  placement — with a defensive fallback (and log message) to Siril's
  automatic placement if the installed sirilpy doesn't support it.
* **"Use Siril's image" button on every stage.** Each stage card now has
  a small button in its header that refreshes that stage's "before"
  preview from whatever is currently loaded in Siril — useful when work
  happened outside the pipeline (e.g. manual Siril commands, another
  script) but should still be picked up by a later stage here.
* **Annotate stage: "Remove all annotations" button**, mirroring the
  existing Watermark stage's clear-all action — removes every currently
  drawn label/marker in one click without touching the underlying FITS
  pixel data (same non-destructive overlay redraw already used for
  individual annotation toggling).

## 1.29.5

* Two "Combine with existing master" improvements:
  * Total integration time is now the sum of this run's own subs and
    the existing master's, instead of whatever Siril's `stack` naturally
    wrote for what it only sees as a 2-frame combine (STACKCNT=2, one
    inherited EXPTIME — wildly understating the real total). A new
    `_read_integration_seconds` helper reads each side's true LIVETIME
    (falling back to STACKCNT × EXPTIME), and the sum is patched into the
    combined result's header before it's loaded, so both the image-info
    panel and the auto-generated filename reflect the real combined
    integration time and sub count.
  * The auto-saved output filename now gets a "_combined" suffix instead
    of "_stacked" whenever combine ran, so a merged result is
    identifiable from the filename alone — matching the same
    pre-built-descriptive-name convention already used by the other
    stages' save actions (e.g. Annotate/Watermark's export dialogs
    pre-fill a descriptive default name for the user).

## 1.29.4

* 1.29.3's fix for "input images have different precision" (`set32bits`
  plus a Siril `load`/`save` round trip) didn't actually work — the same
  crash persisted (`Command 'stack' failed: Generic error`, with the log
  showing both files read back as "32 bits" even though one still had a
  different underlying pixel format). Replaced that approach with a
  direct, reliable fix: both copies are now rewritten in Python (new
  `_ensure_float32_fits` helper, using astropy) to genuine normalized
  32-bit float — matching Siril's own on-disk float convention and
  reusing the same integer-ADU-to-[0,1] scaling (`VeraLuxCore.
  normalize_input`) already used elsewhere in this script for reading
  raw/master FITS files — before Siril's `convert`/`stack` ever touch
  them, instead of relying on a Siril command round trip to do it.

## 1.29.3

* Fixed another follow-on crash in "Combine with existing master":
  `Stacking error: input images have different precision` /
  `Opening image 1 failed`. Siril's `convert` command only symlinks (or
  copies, if linking isn't possible) FITS files as-is — it does not
  re-encode them, so it never actually unified precision/bit depth
  between this run's own 32-bit float stack and an existing master
  saved at a different bit depth (e.g. 16-bit integer), which `stack`
  then refuses to combine once it tries to read both frames. Now forces
  `set32bits` and re-saves both frames (via `load`/`save`) right after
  copying them into the combine folder and before converting,
  registering, or stacking — so both inputs are guaranteed to be
  32-bit float going in, regardless of what precision the original
  files were saved at.

## 1.29.2

* Fixed the follow-on crash after 1.29.1's registration-fallback fix:
  `Command 'stack' failed: Argument error` /
  `Unexpected argument to stacking '-weight_from_nbstack', aborting.`
  The combine-master stack call used `-weight_from_nbstack`, a flag
  syntax this Siril build doesn't recognize. Every other weighted stack
  call in this script (Preprocess's own optional weighting method)
  already uses the `-weight=<mode>` syntax instead, and that's what this
  Siril install actually accepts. Switched the combine step to match:
  `-weight=nbstack`. Also updated the feature's UI description and code
  comments, which previously referenced the non-working flag name.

## 1.29.1

* Fixed "Combine with existing master" (added in 1.29.0) crashing with
  `Command 'seqapplyreg' failed: Generic error` — Siril's log showed
  the real cause: `Existing registration data is a set of identity
  matrices, no transformation would be applied, aborting`. Two
  independently-processed full masters (different sessions, possibly
  different contrast/color balance/orientation) are a much harder
  registration target than raw subs from a single session — plain
  star-pattern matching (`register ... -2pass`) can fail to find enough
  common stars and falls back to identity transforms for both frames,
  which makes `seqapplyreg` refuse to run at all.
  * Now prefers plate-solve registration (matching real sky coordinates
    via WCS, the same approach the main lights-registration step
    already uses for mosaics) when local Gaia astrometry is available —
    far more robust to processing differences between sessions than
    star-pattern shape matching.
  * Falls back to plain star-based registration (without `-2pass`,
    which is meant for large sequences and isn't a good fit for
    exactly two frames) if Gaia astrometry isn't available or
    plate-solving fails.
  * If registration still can't be applied, stacks the two frames
    without re-aligning instead of crashing, with a clear log warning
    so you know to check the combined result for misalignment.

## 1.29.0

* Preprocess: added a new collapsible "Combine with an existing master
  (previous session, no raw subs)" section — for when you already have
  a stacked FITS from an earlier session but the raw sub-exposures
  weren't kept, so it can't just be re-stacked from scratch alongside
  new data.
  * Pick that file in the new section (Browse... button, path shown
    read-only). After this run's own `lights` are stacked as usual,
    the pipeline registers your existing master against this run's
    fresh stack, then combines the two with Siril's
    `-weight_from_nbstack` — each session is weighted by its
    `STACKCNT` FITS header (how many subs actually went into it)
    instead of being averaged 50/50, so a master built from many more
    subs correctly dominates one built from few.
  * A "Sub count override" spinbox lets you manually set the sub count
    for masters that don't already carry a `STACKCNT` header (a copy
    of the header is patched, not the original file — your source
    file is never modified). The pipeline logs a warning if the
    existing master has no `STACKCNT` and no override was given, since
    the combine would otherwise likely under-weight it.
  * Deliberately uses Siril's `convert` command (not `link`) to build
    the two-frame sequence — `link` assumes every sequence member
    already shares the same format/bit depth, which is exactly the
    assumption that broke `calibrate` when a stray stacked file ended
    up alongside raw lights (see the 1.28.x-era bug report); `convert`
    normalizes each file into a consistent format first.
  * Added a reusable `_collapsible_section` UI helper (same
    collapsed-by-default pattern introduced for 1.28.1's GIMP polish
    block) for this new section.
  * New settings JSON keys under `preprocess`: `combine_master_enabled`,
    `combine_master_path`, `combine_master_subcount`.

## 1.28.2

* Fixed a Qt startup warning: `qt.qpa.fonts: Populating font family
  aliases took ... ms. Replace uses of missing font family "Segoe UI"
  with one that exists to avoid this cost.` The global stylesheet
  explicitly named `'Segoe UI'`, `'SF Pro Text'`, and `'Helvetica
  Neue'` — Windows/macOS-only font names — so on platforms without
  them (e.g. Linux) Qt spent a one-time pass building a font-alias
  table before falling back to a default font anyway. Switched to the
  generic `sans-serif` CSS family, which Qt maps directly to the
  platform's default UI font with no alias lookup. No visual or
  behavioral change — just removes that startup-log warning.

## 1.28.1

* Hubble Palette: the "GIMP replacement polish" block is now collapsed
  by default — click its header to expand — since it's an optional
  extra pass most people won't need every run. Also dropped the "Ports
  the manual GIMP finishing pass from the 'Rosette Nebula Hubble
  Palette' tutorial workflow —" lead-in sentence from its description
  (the rest of the description already explains what it does).
* UI consistency pass: every "Reset" button (Stretch, Histogram, Final
  Touch, Hubble Palette's GIMP polish) now uses the same "↺  Reset"
  label instead of four different phrasings ("Reset", "Reset values",
  "↺ Reset", "Reset polish sliders"). Every slider's numeric readout
  across the app now shares one consistent minimum width
  (`SLIDER_VALUE_LABEL_WIDTH`) instead of each stage picking its own
  (34px vs 38px). Added a reusable collapsible-section header style
  (`CollapseHeader`) for the new GIMP polish section, matching the
  app's existing accent-color/bold conventions.

## 1.28.0

* Hubble Palette: added an optional "GIMP replacement polish" block —
  Saturation, Shadows, Highlights, Contrast, Sharpen, and Denoise, each
  independently tunable and off by default.
  * Ports the manual GIMP finishing pass from the "Rosette Nebula Hubble
    Palette" tutorial workflow (GIMP Colors > Saturation, Colors >
    Shadows-Highlights, Colors > Brightness-Contrast, Filters > Enhance
    > Sharpen, Filters > Enhance > Noise Reduction) into one tunable,
    repeatable pipeline step, so it no longer requires a manual
    TIFF round-trip through GIMP.
  * Implementation is a direct port of the standalone
    `gimp_replacement.py` prototype: HSV saturation scaling, tone-curve
    shadow-lift/highlight-pull, midpoint contrast, `skimage`'s
    `unsharp_mask`, and `denoise_bilateral` — same math, same
    parameter meanings, now exposed as sliders instead of CLI flags.
  * Runs after the Hubble Palette recolor (either Channel mix or
    NebulaChrome mode, whichever is selected), so it applies to
    whichever palette result you're using.
  * Every slider defaults to "no change" — enabling the "Apply GIMP
    replacement polish" checkbox is required before any of them have
    an effect, so existing Hubble Palette settings/behavior are
    unaffected unless you opt in.
  * New settings JSON keys under `palette`: `gimp_polish_enabled` and
    `gimp_polish` (saturation/shadows/highlights/contrast/sharpen/
    denoise slider values).

## 1.27.0

* Annotate: markers for Messier/NGC/IC/Sharpless/LdN objects are now
  sized to the object's real apparent diameter instead of a fixed
  generic circle.
  * OpenNGC rows carry a `MajAx` (apparent major axis, arcmin) column,
    now parsed and passed through `_filter_openngc_rows`.
  * VizieR's Sharpless catalogue (VII/20) carries a `Diam` (arcmin)
    column, used the same way.
  * VizieR's Lynds Dark Nebulae catalogue (VII/7A) only gives an `Area`
    (square degrees) field, so an equivalent circular diameter is
    derived from it (`diam = 2 * sqrt(area / pi)`).
  * The apparent size is converted to an on-image pixel radius using the
    plate solve's actual pixel scale (`astropy.wcs.utils.
    proj_plane_pixel_scales`), then clamped so a huge catalogue entry
    (e.g. Barnard's Loop) can't swallow the whole frame, and a
    point-like one never shrinks below the old fixed minimum. Objects
    with no size data (or stars) keep the previous fixed-radius marker.
* Annotate: replaced the fixed offset-from-marker label placement with
  a greedy layout pass (`_layout_annotation_labels`) that tries a ring
  of candidate positions around each marker, picks the first one that's
  fully inside the image and doesn't overlap an already-placed label,
  and falls back to the least-bad on-canvas candidate (or a hard clamp
  to the frame edge) if every candidate collides. Bigger markers are
  placed first so the most visually prominent objects keep the
  conventional near-marker label position. This fixes both overlapping
  text in crowded fields and labels getting cut off at the image edge.

## 1.26.0

* Annotate is back, rebuilt from scratch on a completely different data
  source. 1.25.0 removed the stage entirely after `catsearch`-based DSO
  resolution proved fundamentally unreliable (free-text console log
  scraping, no documented format). This version replaces that layer
  with the same approach used by a user-supplied working reference
  script: structured data pulled independently of Siril's own console
  output.
  * **Messier / NGC / IC** — sourced from the OpenNGC database
    (github.com/mattiaverga/OpenNGC), downloaded once and cached on
    disk (`appdirs` user data dir), then filtered in-memory against the
    plate-solved field's RA/Dec/radius (computed via `astropy.wcs`
    pixel↔sky conversion on the image corners, not by scraping Siril's
    log). Messier objects are labeled "M 42" etc. rather than by their
    NGC number.
  * **Sharpless (Sh2) and Lynds Dark Nebulae (LdN)** — live cone
    searches against VizieR (catalogues VII/20 and VII/7A) for the same
    field, since these aren't in OpenNGC.
  * **Stars** — unchanged: Siril's own `conesearch` command (local
    Bright Star Catalogue, or `-cat=bsc` for the online version), which
    was never the source of the earlier failures.
  * New catalog checkboxes (Messier, NGC, IC, Sharpless, LdN, plus
    Stars) so you can choose which types get plotted; each catalog has
    its own annotation color, shown as a swatch next to its checkbox in
    the stage UI and reused in the object-selector dialog.
  * A "Select objects to show..." dialog (reusing the same live-preview
    pattern as the 1.19.0/1.20.0 "Remove Annotations" dialog) lists
    every object found in-field with a checkbox; ticking/unticking
    updates the pipeline preview immediately, without re-querying any
    catalog.
  * Undo (reverts to the un-annotated image) and "Save annotated
    image..." are both back.
  * Messier/NGC/IC are on by default (one-time cached download, no
    per-run network cost after the first). Sharpless/LdN are off by
    default since they require a live VizieR query on every run.
  * The remaining stages were renumbered again — Annotate is stage 11
    and Watermark is stage 12, restoring the 12-stage pipeline.

## 1.25.0

* Removed the Annotate stage entirely — the UI card, the catsearch/
  conesearch helper functions, the `DSO_NAMES`/`BRIGHT_STARS` catalogs,
  the "Save annotated image...", "Remove Annotations...", and "Open
  Siril's Annotate tool" buttons, and its settings JSON keys
  (`stages_enabled.annotate` and the `annotate` block).
  Despite the 1.22.0 SIMBAD fix, the 1.22.2 magnitude-limit fix, the
  1.23.1 redesign around Siril's own `catsearch` command, and the 1.24.1
  regex fix for Siril's comma-separated RA/Dec wording, resolving Siril's
  bundled Messier/NGC/IC/Sharpless/LdN catalogues reliably from a script
  never panned out — `catsearch` only exposes results through
  free-text console log messages with no documented, stable format, so
  parsing it back out was fundamentally best-effort. Siril's own native
  Annotate tool (Tools → Astrometry → Annotate... inside Siril itself)
  remains the reliable way to label deep-sky objects; it isn't
  reachable from a script's automated pipeline, only interactively.
  The remaining stages were renumbered — Watermark is now stage 11
  (previously 12), and the pipeline has 11 stages total (previously 12).

## 1.24.1

* Annotate: fixed a bug where the catsearch-based deep-sky-object lookup
  (added in 1.23.1) reported zero results for every single object it
  tried, regardless of whether that object actually fell inside the
  plate-solved frame. Siril's `catsearch` command does resolve names
  correctly and does print their coordinates to the console log, e.g.:
  ```
  Object M62 (exact match: M62) was found in the Messier catalogue at:
  17h01m12.87s, -30°06'44.70"
  Object M62 record was found but is not within the bounds of the image
  ```
  but the RA/Dec-extracting regex added in 1.23.1 only accepted
  whitespace between the RA and Dec halves ("05h35m17s -05d23m28s"),
  while Siril's actual wording separates them with a comma
  ("17h01m12.87s, -30°06'44.70\""). That mismatch made every parse
  attempt fail silently, so `_catsearch_objects` never returned a single
  resolved coordinate — hence "0 objects labeled" and a blank overlay no
  matter what was checked. Fixed by accepting an optional comma (in
  addition to whitespace) as the separator. The existing pixel-bounds
  check in `_exec_stage_ann` already restricts what gets drawn to objects
  that land inside the current plate-solved frame — Siril's own "not
  within the bounds of the image" message for an out-of-frame object is
  expected and harmless, and no longer prevents parsing the objects that
  *are* in frame.

## 1.24.0

* Watermark: added an "Author" field — a free-text credit line (e.g. your
  name or handle) you type yourself, separate from the metadata-driven
  fields above it (which come from the image's FITS header). Included in
  the watermark block when its checkbox is ticked and the text isn't
  empty; saved/restored with the rest of the Watermark settings in
  exported JSON.
* Housekeeping: the script's own docstring changelog was getting long
  enough to make the file harder to skim, so from this version on it
  only keeps a short summary of the last few releases inline. The full,
  detailed version history now lives here in CHANGELOG.md and in the
  HTML docs (`S30Pro_Pipeline_README.html`) — nothing was deleted, it
  just moved out of the script.

## 1.23.2

* Annotate: added a "🔭 Open Siril's Annotate tool..." button that pops
  Siril's own native Annotate dialog (Tools -> Astrometry -> Annotate...)
  so you can browse or search its real bundled Messier/NGC/IC/LdN/
  Sharpless/star/constellation catalogues directly in Siril's own window.
  This is a manual companion, separate from "Run this stage" above: Siril
  doesn't hand back what you find in there, so it can't feed this stage's
  own preview or export — that keeps coming exclusively from the
  automated `catsearch` lookup this stage runs itself. Objects you do
  search for in Siril's own tool get saved to Siril's catalogue though,
  so this stage's next automated `catsearch` pass finds them there
  immediately instead of needing an online SIMBAD lookup. Requires
  sirilpy 1.0.20+ (`open_dialog`/`DialogID` support); on older sirilpy
  the button explains this and points you at Siril's own menu instead.

## 1.23.1

* Annotate: redesigned the deep-sky-object source, branching from 1.22.2
  (the brief 1.23.0 release that shipped a 134-entry hardcoded Messier/
  NGC/IC coordinate+magnitude table has been superseded — that traded
  one problem for another the user didn't want: a database to maintain
  inside the script). Removed the "Galaxies (PGC)" and "Named DSOs
  (SIMBAD)" cone-search options entirely — PGC only covers galaxies, and
  SIMBAD via `conesearch` never reliably surfaced named objects even
  after the 1.22.2 magnitude fix.
* Replaced them with a single "Named DSOs — Messier / NGC / IC" option
  that resolves object names one at a time through Siril's own
  `catsearch` command — the same name-resolution Siril's own Annotate
  tool uses internally, checking Siril's bundled local Messier/NGC/IC/
  Sharpless/LdN catalogues first and only falling back to an online
  SIMBAD lookup for names it doesn't recognize locally. This script only
  supplies a short, ordered list of catalogue designations (DSO_NAMES —
  just strings like "M42", "NGC 7000", nothing else); every coordinate
  comes from Siril itself, so no coordinate/magnitude database is kept
  here. `catsearch` doesn't hand back structured data through the normal
  command interface, so this parses the RA/Dec out of Siril's console
  log after each call — best-effort by nature (not a documented, stable
  API), silently skipping anything it can't resolve or parse rather than
  failing the whole stage.
* Added a "DSO count limit" spinbox (default 60) as the independent
  DSO-side control alongside the existing star magnitude limit — it
  caps how many names (in roughly most-famous-first order) get tried,
  standing in for a magnitude filter since no per-object brightness data
  is kept anymore.
* Undo, "Save annotated image...", and "Remove Annotations..." are
  unchanged — they work on the drawn-object list regardless of source.

## 1.22.2

* Annotate: fixed "Named DSOs (SIMBAD)" returning zero or almost no
  objects. It was passing the star magnitude-limit spinner (default 6.0)
  to the SIMBAD query, but that's tuned for stars — most Messier/NGC/IC
  objects are fainter than magnitude 6, so the query was silently
  filtered down to nothing (this is why unchecking Galaxies could leave
  "nothing to show", and why checking Galaxies only ever showed PGC
  galaxies, never named DSOs). It now queries SIMBAD without that limit,
  the same way the PGC galaxy query already does, so Siril applies its
  own generous default depth (magnitude 13) for that catalogue instead.

## 1.22.1

* Fixed this app's preview panel showing every stage upside-down
  compared to Siril's own on-screen display. Siril (and FITS generally)
  stores row 0 as the bottom of the image, and Siril flips it before
  showing it on screen; this app's `make_qimage()` never did that same
  flip for ordinary stage arrays, so the preview panel was rendering raw
  FITS row-order data directly — vertically flipped relative to Siril's
  real display. Only the Annotate stage happened to look right, because
  it already flipped its own canvas internally (needed so its baked-in
  text wouldn't render upside-down). `make_qimage()` now applies that
  same flip by default for every stage, so the preview panel matches
  Siril's own display consistently across all stages.
* Fixed a related, more serious bug this uncovered in Watermark: it was
  drawing its text directly onto the raw (unflipped) FITS-order array
  before pushing the result back into Siril's actual working image —
  meaning the baked-in watermark text would have appeared upside-down
  once Siril displayed it (or once the FITS/JPG was opened elsewhere),
  the same class of bug fixed for Annotate's text back in 1.20.0.
  Watermark now draws on a display-oriented canvas and flips the result
  back to FITS order before handing it to Siril, so the text comes out
  right-side-up both in Siril's own display and in the saved image.

## 1.22.0

* Annotate: added a "Named DSOs (SIMBAD)" option. Siril's own on-screen
  annotation overlay (Messier/NGC/IC/Sharpless/LdN) is a GUI-only
  feature with no scriptable export, so this app was previously only
  able to query Siril's `conesearch -cat=pgc` (PGC/HyperLeda), which is
  galaxies only — most Messier objects and many NGC/IC objects are
  nebulae or star clusters, not galaxies, so they never appeared even
  though Siril's own preview shows them. This new option additionally
  queries Siril's conesearch against SIMBAD (a general database covering
  all object types, not just stars, despite being listed under Siril's
  "stars" catalogues), which should surface most of what was missing.
  Enabled by default, capped at 60 objects per run, needs internet.
* Watermark: added a "Remove all watermarks" button — restores the image
  to how it looked before the very first Watermark run in this session,
  undoing every watermark applied so far (the existing Undo button only
  reverts the single most recent run).
* Watermark: added a "Two-column layout" option — lays the checked
  fields out in two side-by-side columns instead of one vertical list,
  for a wider but noticeably shorter block.

## 1.21.1

* Crop stage: fixed the preview image's on-screen size drifting while
  drawing a manual crop box (and after it was marked, before running the
  stage). The panel's rendered scale was always recomputed purely from
  the widget's current pixel size, so any layout-driven resize of the
  preview panel during that workflow silently rescaled the image under
  the cursor. The preview panel now locks its effective on-screen scale
  for the whole "drawing a box" / "box marked, not yet run" window, so
  only an explicit zoom (scroll wheel or the +/- buttons) changes the
  size — matching the fix already applied in 1.14.1 for size changes
  caused by the crop actually running.

## 1.21.0

* New final stage: Watermark. Draws a semi-transparent info block onto
  the image with a plain (icon-free) text block using OpenCV's cleaner
  HERSHEY_DUPLEX font instead of the technical-looking SIMPLEX font used
  elsewhere:
  - Pick which fields to show: Object name, Date, Integration time,
    Telescope (with any "_serial-number" suffix stripped, e.g.
    "ZWO Seestar S30 Pro_2409020001" -> "ZWO Seestar S30 Pro"), FOV,
    image size, Bortle estimate — same data already shown in the info
    bar, just rendered onto the image itself.
  - Position: Top-Left / Top-Right / Bottom-Left / Bottom-Right /
    Top-Center / Bottom-Center.
  - Background block opacity is adjustable (0-100%).
  - Undo button (restores the image from before the stage ran) and a
    "Save watermarked image..." button (export as JPEG/PNG), matching
    the Annotate stage's pattern.

## 1.20.0

* Fixed mirrored/upside-down annotation text in this app's own preview
  panel. The annotated canvas is drawn once, already flipped to match
  Siril's own on-screen orientation (needed for the exported JPG to look
  right) — but the preview snapshot was then flipping that same
  already-correct raster a second time for display, which inverts pixel
  *positions* correctly but leaves rendered glyphs upside down (a raster
  flip mirrors text, it doesn't re-render it). The preview now uses the
  same single-flip orientation as the exported JPG for both its before
  and after images — text reads correctly in both places now, at the
  cost of the Annotate tab's preview being oriented differently than
  other stages' tabs when you switch between them (a cosmetic
  side-effect of fixing the text, not a new bug).
* "Remove Annotations..." now updates the preview live as you check/
  uncheck objects, instead of only after pressing OK. Canceling the
  dialog reverts to whatever was shown before you opened it.

## 1.19.0

* Annotate stage: new "🗑 Remove Annotations..." button opens a checklist
  of every object currently labeled on the image — uncheck individual
  objects to remove just those, or use Select All / Deselect All to keep
  or clear everything. Removal redraws instantly from the un-annotated
  base image (no re-querying Siril's catalogues) and updates both the
  preview and the exportable annotated canvas.
* Annotate stage now has an Undo button (previously the only stage
  without one), restoring the image Siril had loaded before the stage
  ran — relevant when "stars added back (fallback)" kicks in during
  Annotate, which does modify Siril's loaded image.

## 1.18.0

* Annotate stage now sources objects from Siril's own catalogues instead
  of this script's hardcoded star/DSO lists, via Siril's scriptable
  `conesearch` command:
  - Named bright stars: queries Siril's local Bright Star Catalogue
    (3,661 stars) for whatever's actually in the plate-solved field,
    replacing the old fixed ~52-star list.
  - "All stars < mag limit (online)" now runs `conesearch -cat=bsc`
    (Siril's own VizieR bridge) instead of this script's own
    astroquery/Vizier query — the `astroquery` dependency is gone.
  - Deep-sky objects: queries Siril's PGC/HyperLeda catalog via
    `conesearch -cat=pgc`, replacing the old fixed ~50 "famous object"
    list — labeled by catalog number (e.g. "PGC 5194"), since Siril
    doesn't expose a scriptable bulk export of its named Messier/NGC
    catalogues (those are a GUI-only overlay). PGC is galaxies only, so
    this trades "curated famous nebulae/clusters with common names" for
    "every real galaxy Siril's catalogue knows about in the field,
    numbered." Capped at 60 drawn per run to keep dense fields legible.
  - Both old hardcoded lists (BRIGHT_STARS, FAMOUS_DSOS) are kept as an
    automatic fallback if `conesearch` isn't available (Siril < 1.3) or
    returns nothing usable, so nothing breaks on older Siril versions.

## 1.17.2

* Preprocess (Stage 1) defaults updated: Telescope = ZWO Seestar S30 Pro,
  Filter = LP (Narrowband), Stack weighting = on (Weighted FWHM),
  Compression (Rice) = on, Per-frame background (mosaic seams) = on.
  Darks/Flats/Biases, Drizzle, Feather stay off; Drizzle scale/Pixfrac
  stay 1.0; Distortion order stays 4; SPCC and cleanup stay on (unchanged
  from before).

## 1.17.1

* Preview panel polish: the BEFORE/AFTER split-view labels, the crop-mode
  hint text, and the Before/Split/After + zoom/fit toolbar buttons were all
  quite small (8pt labels, cramped button padding) — sized up for a more
  legible, commercial feel. Info-bar text also bumped from 9pt to 9.5pt.
* Fixed faint re-added stars: "⭐ Add Stars Back Now" and the automatic
  held-stars fallback (`_reconcile_held_stars`, used when Stretch is
  skipped) were blending the *linear* (unstretched) star layer straight
  onto an already-stretched, bright final image — linear star pixel values
  are tiny next to stretched image values, so the stars barely showed up.
  Both paths now apply the same gentle arcsinh stretch the Stretch stage
  itself uses (using the Remove Stars panel's own asinh-strength slider)
  before blending, so stars come back looking like stars.

## 1.17.0

Structural cleanup:
* New shared `luminance()` helper replaces 4 copies of the inline
  Rec.709 (0.2126/0.7152/0.0722) formula scattered across NebulaChrome
  and Final Touch saturation code.
* New shared `_finish_stage()` helper replaces the repeated backup /
  snapshot / progress / log "tail" duplicated across 8 of the 11
  pipeline stages (Crop, SCNR, Remove Background, Denoise, Palette,
  Stretch, Histogram, Final Touch) and now also tracks the last stage
  that ran (used by the new Ctrl+Z shortcut, below).
* Removed dead code: unused `self.drizzle_status` flag (written, never
  read) and `VeraLuxCore._last_diag` (never referenced after being set).

Real footguns fixed:
* Undo on the Histogram or Final Touch stage now also resets that
  stage's sliders back to their defaults, matching the restored image
  (previously the image reverted but the sliders stayed wherever you'd
  left them, so the panel and the image disagreed).
* Running the Hubble Palette stage after Stretch has already run now
  asks for confirmation first — Palette recombines Hα/OIII, which
  should normally happen before Stretch; doing it after is unusual and
  was previously silent.
* Preprocess (Stage 1) now discards a stale held-star layer left over
  from a previous Remove Stars run if you re-run Preprocess afterwards
  (a fresh stack is a different image, so the old star layer no longer
  corresponds to anything) — a warning is logged instead of it being
  silently carried forward.
* Audited every use of the "held stars" hand-off (`_reconcile_held_stars`)
  across Histogram, Final Touch, Annotate and Stretch — confirmed the
  safety net was already applied consistently to every stage that runs
  after Stretch; no change needed there.

Missing safety/UX niceties:
* Bare `except: pass` blocks around the auto-save-on-stage-completion
  calls (Final Touch, Stretch, Histogram) now log a SALMON warning on
  failure instead of failing silently.
* Keyboard shortcuts: Ctrl+S (Save File...), Ctrl+Z (undo the most
  recently run stage), Ctrl+Return (Run whole pipeline).
* You can now drag and drop a folder onto the window to set the
  working directory, instead of only via the file-picker dialog.

## 1.16.5

* Fixed "⭐ Add Stars Back Now" appearing to do nothing. It was correctly
  blending the stars into Siril's actual image data, but never updated the
  before/after preview panel (no other stage's snapshot machinery ran for
  it) — so the change was real but invisible until you switched stages or
  reloaded. It now refreshes the preview for the currently selected stage
  immediately, same as every other action in the app.

## 1.16.4

* Crop stage: mouse-wheel/trackpad scroll no longer zooms the preview while
  drawing a crop box — it was shifting the image under the cursor mid-drag,
  making it impossible to draw an accurate box (very common on trackpads,
  which send wheel events during a click-drag gesture).

## 1.16.3

* NebulaChrome: fixed the background picking up a blue/teal cast. The
  white-reference recolor and saturation boost were previously applied
  uniformly to every pixel, including the sky background — since the blue
  channel under a dual-band filter is mostly crosstalk/noise rather than
  real signal, the multiplier needed to push the bright core toward teal
  also amplified that noise everywhere. Both passes are now gated by a
  luminosity mask (background ≈ untouched, nebula peak ≈ full effect),
  with a new "Peak isolation" slider controlling how sharp that cutoff is
  — like an automatic luminosity mask.

## 1.16.2

* Stage cards: unchecking the header checkbox now visibly greys out that
  stage's whole panel (labels, dropdowns, sliders, buttons), not just
  disabling clicks with no visual change. The dark theme didn't previously
  define disabled-state colors for most widget types, so a "disabled"
  control still rendered in full brightness.

## 1.16.1

* Crop stage: the drawn crop box now stays visible in the preview after you
  release the mouse (tracking zoom/pan), instead of disappearing. It clears
  when you press "Run this stage" (crop applied) or Esc (cancel).

## 1.16.0

* Added a "Save File..." button below Run Full Pipeline — saves the
  current Siril image as FITS, JPEG, PNG or TIFF via Siril's own
  save/savejpg/savepng/savetif commands, wherever you choose.
* Added a "Close Pipeline" button. Closing the window (via this button or
  the window's own close control) now always asks for confirmation first.
* Annotate stage: star/DSO marker size and label text size now scale with
  the image's actual pixel resolution (previously the marker radius never
  scaled with resolution at all, which is why it looked tiny on large
  stacks). Added a "Show annotation overlay" checkbox to hide the markers/
  labels entirely, and a "Save annotated image..." button to export the
  overlay as JPEG or PNG wherever you choose (in addition to the existing
  automatic timestamped JPG save).

## 1.15.0

* Hubble Palette stage: replaced the "Color Calibration trick" mode (which
  often overcorrected and looked flat) with NebulaChrome — a consolidated
  pseudo-Hubble recolor combining background neutralization + bright-core
  white reference, a saturation/shadows-highlights polish pass, and a
  Richardson-Lucy deconvolution sharpen, blended against the original by
  an adjustable Recolor strength slider instead of applied at full force.

## 1.14.1

* Crop stage: drawing a box in the preview no longer crops immediately on
  mouse release. It now just stores the box (and switches off Auto crop);
  the actual crop happens when you press "Run this stage", same as the
  margin-based crop.
* Crop stage: drawing a box automatically unchecks Auto crop.
* Preview panel: when a stage changes the image's pixel dimensions (as
  Crop always does), the preview no longer snaps back to a fresh "fit to
  panel" view. It keeps the same effective zoom level you had.

## 1.14.0

* Final Touch stage: added Shadows / Highlights sliders (tone-curve lift/
  pull on dark and bright tones, same idea as GIMP's Shadows-Highlights).
* Final Touch stage: Sharpen now supports two modes — the original Unsharp

