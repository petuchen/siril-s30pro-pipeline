"""Centralized bilingual (English / 繁體中文) UI strings for the S30 Pro
Pipeline plugin's PyQt6 interface.

This is the scaffolding for an incremental, stage-by-stage rollout —
see CHANGELOG.md for the plan. Only the shared/window-chrome strings
needed to stand up the language toggle itself are populated so far;
each stage file's own labels, tooltips and dialogs get their own keys
added (prefixed by stage name) as that stage is converted.

Usage: call `self.tr("some_key")` from anywhere on UnifiedPipelineWindow
(every stage mixin is composed into that one class, so `self.tr` is
available everywhere) to get the string in whichever language is
currently selected (`self.lang`, one of LANGUAGES). A key with no
translation for the current language falls back to English, and a
totally unknown key falls back to the raw key string itself — so a
forgotten translation shows up as visibly wrong (English text where
Chinese was expected, or a raw snake_case key) instead of crashing the
UI, which matters while a stage is only partially converted.
"""

LANGUAGES = ("en", "zh")
DEFAULT_LANGUAGE = "en"

# Each key's value is {"en": "...", "zh": "..."}. Keys are grouped by
# which file owns them; shared/window-chrome keys (used from
# S30Pro_Pipeline.py itself, not any one stage) have no stage prefix.
STRINGS = {
    # ---- shared / window chrome -----------------------------------
    # The toggle button always shows the *other* language's name, i.e.
    # what clicking it will switch you to — matching index.html's
    # existing EN/繁體中文 toggle convention.
    "lang_toggle": {"en": "中文", "zh": "EN"},
    # Every stage's Run/Undo row (_run_row in S30Pro_Pipeline.py) shares
    # these — translating them here covers every stage at once, not
    # just the ones already converted to self.tr(...).
    "run_this_stage": {"en": "Run this stage", "zh": "執行此步驟"},
    "undo_btn": {"en": "↩  Undo", "zh": "↩  復原"},
    "undo_tooltip": {
        "en": "Restore the image as it was before this stage ran",
        "zh": "將影像還原成執行此步驟之前的樣子"},
    # Shared by every _info_row(...) "Details" popup-trigger button
    # (Preprocess's Combine/Batch stacking sections, etc.).
    "info_details_btn": {"en": "ⓘ Details", "zh": "ⓘ 詳細資訊"},

    # Stage rail (ui_shell.py's RailRow/StageRail) + pane header
    # (PaneHeader, built per-stage in ui_v2.py's _stage_box). Neither
    # widget class knows about self.tr(...) — they're plain QWidgets
    # with no window reference — so S30Pro_Pipeline.py's
    # retranslate_ui_chrome() re-applies these keys directly onto their
    # already-public QLabel attributes (row.name, row.setToolTip(...),
    # header.title, header.set_description(...)) after a language
    # toggle, rather than the widgets calling self.tr() themselves. The
    # short "chrome_rail_*" labels are what the rail (and the preview
    # toolbar's stage stepper) show; "chrome_title_*" is the fuller
    # pane-header title each stage passes to _stage_box(); indices match
    # constants.STAGES / IDX_PP..IDX_WM (0-12).
    "chrome_rail_0": {"en": "Preprocess", "zh": "前處理"},
    "chrome_rail_1": {"en": "Crop", "zh": "裁切"},
    "chrome_rail_2": {"en": "Remove Green", "zh": "去除綠色"},
    "chrome_rail_3": {"en": "Auto Gradient", "zh": "自動去梯度"},
    "chrome_rail_4": {"en": "Remove Background", "zh": "移除背景"},
    "chrome_rail_5": {"en": "Remove Stars", "zh": "移除星點"},
    "chrome_rail_6": {"en": "Denoise", "zh": "降噪"},
    "chrome_rail_7": {"en": "Hubble Palette", "zh": "哈伯色盤"},
    "chrome_rail_8": {"en": "Stretch", "zh": "拉伸"},
    "chrome_rail_9": {"en": "Histogram", "zh": "直方圖"},
    "chrome_rail_10": {"en": "Final Touch", "zh": "最終潤飾"},
    "chrome_rail_11": {"en": "Annotate", "zh": "標記"},
    "chrome_rail_12": {"en": "Watermark", "zh": "浮水印"},

    "chrome_title_0": {
        "en": "Preprocess — Smart Telescope Stacking",
        "zh": "前處理——智慧望遠鏡疊圖"},
    "chrome_title_1": {"en": "Crop", "zh": "裁切"},
    "chrome_title_2": {
        "en": "Remove Green Noise (SCNR)", "zh": "去除綠色雜訊（SCNR）"},
    "chrome_title_3": {"en": "Auto Gradient Removal", "zh": "自動去梯度"},
    "chrome_title_4": {"en": "Remove Background", "zh": "移除背景"},
    "chrome_title_5": {"en": "Remove Stars (StarNet)", "zh": "移除星點（StarNet）"},
    "chrome_title_6": {"en": "Denoise — GraXpert AI", "zh": "降噪——GraXpert AI"},
    "chrome_title_7": {
        "en": "Hubble Palette — Synthetic SHO/HOO",
        "zh": "哈伯色盤——合成 SHO／HOO"},
    "chrome_title_8": {
        "en": "Stretch — VeraLux HyperMetric",
        "zh": "拉伸——VeraLux HyperMetric"},
    "chrome_title_9": {
        "en": "Histogram Fine-Tune — Per Channel",
        "zh": "直方圖微調——逐通道"},
    "chrome_title_10": {
        "en": "Final Touch — Photo Adjustments",
        "zh": "最終潤飾——照片調整"},
    "chrome_title_11": {
        "en": "Annotate — Stars & Deep-Sky Objects",
        "zh": "標記——星點與深空天體"},
    "chrome_title_12": {"en": "Watermark", "zh": "浮水印"},

    # One-line "why you need this" per stage (ui_v2.py's STAGE_BLURBS),
    # shown under the pane title.
    "chrome_blurb_0": {
        "en": "Aligns and averages hundreds of short exposures into one "
              "deep image, then calibrates the colours against star "
              "catalogues.",
        "zh": "把數百張短曝光子畫幅對齊並平均疊合成一張深空影像，再依星表"
              "校正色彩。"},
    "chrome_blurb_1": {
        "en": "Trims the ragged edges left by the telescope's drift, "
              "with an optional rotate first.",
        "zh": "裁掉望遠鏡追蹤漂移留下的參差邊緣，可選擇先旋轉影像。"},
    "chrome_blurb_2": {
        "en": "Removes the green cast colour cameras tend to produce.",
        "zh": "去除彩色相機常見的綠色偏色。"},
    "chrome_blurb_3": {
        "en": "A tunable gradient-flattening pass — useful on its own, "
              "or as a milder pre-pass before Remove Background.",
        "zh": "可調整的漸層抹平步驟——可單獨使用，也可作為「移除背景」前"
              "較溫和的前置處理。"},
    "chrome_blurb_4": {
        "en": "Flattens the sky glow from light pollution and moonlight "
              "so the object stands out.",
        "zh": "抹平光害與月光造成的天空輝光，讓拍攝目標更突出。"},
    "chrome_blurb_5": {
        "en": "Separates stars from the nebulosity so later stages can "
              "work on one without the other.",
        "zh": "把星點與星雲本體分離，讓後續步驟可以只處理其中一者。"},
    "chrome_blurb_6": {
        "en": "AI noise reduction — removes grain from faint areas "
              "while keeping stars and detail.",
        "zh": "AI 降噪——去除暗部顆粒感，同時保留星點與細節。"},
    "chrome_blurb_7": {
        "en": "Remaps emission-nebula colours into the gold-and-teal "
              "Hubble look.",
        "zh": "把發射星雲的色彩重新對應成金色與青綠色的哈伯風格。"},
    "chrome_blurb_8": {
        "en": "Brightens the image from almost black to visible without "
              "destroying the colours.",
        "zh": "把幾乎全黑的影像拉亮到可見範圍，同時不破壞色彩。"},
    "chrome_blurb_9": {
        "en": "Per-channel colour balance after the big stretch.",
        "zh": "在大幅拉伸之後逐通道調整色彩平衡。"},
    "chrome_blurb_10": {
        "en": "The familiar last-mile polish: brightness, contrast, "
              "saturation, sharpening.",
        "zh": "熟悉的最後潤飾：亮度、對比、飽和度、銳化。"},
    "chrome_blurb_11": {
        "en": "Labels stars and deep-sky objects in the plate-solved "
              "field.",
        "zh": "在已完成天球解算的視野中標記星點與深空天體。"},
    "chrome_blurb_12": {
        "en": "Draws a semi-transparent info block onto the image for "
              "sharing.",
        "zh": "在影像上繪製半透明資訊區塊，方便分享。"},

    # StageRail's 4 phase group headers.
    "chrome_group_stack": {"en": "STACK", "zh": "疊圖"},
    "chrome_group_clean": {"en": "CLEAN", "zh": "清理"},
    "chrome_group_stretch": {"en": "STRETCH", "zh": "拉伸"},
    "chrome_group_finish": {"en": "FINISH", "zh": "收尾"},

    # Undo progress text (S30Pro_Pipeline.py's on_undo_stage) — the
    # matching siril.log(...) line stays English-only per the usual
    # log-vs-UI convention and keeps using the raw STAGES[idx] string.
    "chrome_undoing_status": {
        "en": "Undoing {stage}...", "zh": "正在復原「{stage}」..."},
    "chrome_undone_status": {
        "en": "{stage} undone.", "zh": "「{stage}」已復原。"},

    # ---- stage: Auto Gradient Removal (stage_agr.py) ----------------
    "agr_info": {
        "en": "Ported from Siril's own AutoGradientRemoval script "
              "(Cyril Richard). Places no sample points at all — fits "
              "the background on every pixel that survives an "
              "iterative robust rejection of structures (stars, "
              "nebulae, galaxies). Pure numpy, no AI model or GPU "
              "needed. Off by default; enable it instead of (or "
              "before) Remove Background below when GraXpert isn't "
              "installed or subsky's sample points aren't landing "
              "well.",
        "zh": "移植自 Siril 自身的 AutoGradientRemoval script（作者 "
              "Cyril Richard）。完全不需要放置取樣點——對每個「通過反覆"
              "強健式結構剔除（星點、星雲、星系）」的像素直接擬合背景。"
              "純 numpy 運算，不需要 AI 模型或 GPU。預設關閉；當沒有安"
              "裝 GraXpert，或 subsky 的取樣點抓得不理想時，可以改用（"
              "或先於）下方的「移除背景」使用此步驟。"},
    "agr_scale_label": {"en": "Scale:", "zh": "尺度："},
    "agr_scale_tooltip": {
        "en": "Relative scale of the multiscale model. Higher = "
              "smoother (large-scale only); lower = follows more "
              "complex/local gradients.",
        "zh": "多尺度模型的相對尺度。數值越高，模型越平滑（只反映大尺度"
              "變化）；數值越低，越能跟隨較複雜的局部漸層。"},
    "agr_smoothness_label": {"en": "Smoothness:", "zh": "平滑度："},
    "agr_smoothness_tooltip": {
        "en": "Extra smoothing of the final model. Higher gives a "
              "softer, more gradual background; 0 leaves the fitted "
              "model untouched.",
        "zh": "對最終模型額外套用的平滑處理。數值越高，背景越柔和漸"
              "進；0 則完全不處理擬合出的模型。"},
    "agr_protect": {"en": "Structure protection", "zh": "結構保護"},
    "agr_protect_tooltip": {
        "en": "Mask extended bright structures (nebulae) so they are "
              "not absorbed into the model.",
        "zh": "遮罩大範圍明亮結構（例如星雲），避免它們被誤判成背景納"
              "入模型。"},
    "agr_pthr_label": {
        "en": "    Protection threshold:", "zh": "    保護門檻："},
    "agr_pthr_tooltip": {
        "en": "Brightness above the model at which a pixel is treated "
              "as a structure. Lower = protects more.",
        "zh": "像素亮度高出模型多少時，會被視為結構。數值越低，保護範"
              "圍越大。"},
    "agr_pamt_label": {
        "en": "    Protection amount:", "zh": "    保護幅度："},
    "agr_pamt_tooltip": {
        "en": "How far the protection mask grows around detected "
              "structures.",
        "zh": "保護遮罩會從偵測到的結構向外擴張多少範圍。"},
    "agr_simplified": {"en": "Simplified model", "zh": "簡化模型"},
    "agr_simplified_tooltip": {
        "en": "Replace the multiscale model with a stiff polynomial. "
              "Use it when a nebula fills the frame and the default "
              "model hollows it out.",
        "zh": "用一個較僵硬的多項式取代多尺度模型。當星雲佔滿整個畫面、"
              "預設模型把星雲中心挖空時，可改用此模式。"},
    "agr_degree_label": {"en": "    Model degree:", "zh": "    模型階數："},
    "agr_degree_tooltip": {
        "en": "Polynomial degree of the simplified model. Lower = "
              "stiffer (degree 1 = plane).",
        "zh": "簡化模型的多項式階數。數值越低越僵硬（1 階＝平面）。"},
    "agr_downsample_label": {"en": "Downsample:", "zh": "降取樣："},
    "agr_downsample_tooltip": {
        "en": "Internal working scale factor. Higher = faster but "
              "coarser; the background scale itself is unaffected.",
        "zh": "內部運算時的縮放倍率。數值越高運算越快但越粗略；不影響"
              "背景本身的尺度。"},
    "agr_mode_label": {"en": "Mode:", "zh": "模式："},
    "agr_mode_subtract": {"en": "subtract", "zh": "相減"},
    "agr_mode_divide": {"en": "divide", "zh": "相除"},
    "agr_mode_tooltip": {
        "en": "subtract: additive gradient. divide: multiplicative "
              "(vignetting/flat).",
        "zh": "相減：處理加性漸層。相除：處理乘性效應（例如暗角／平場"
              "類型的問題）。"},
    "agr_progress_fetching": {
        "en": "Auto Gradient Removal: fetching image...",
        "zh": "自動去除漸層：正在讀取影像..."},
    "agr_progress_estimating": {
        "en": "Auto Gradient Removal: estimating background...",
        "zh": "自動去除漸層：正在估算背景..."},
    "agr_progress_done": {
        "en": "Auto Gradient Removal: done.", "zh": "自動去除漸層：完成。"},

    # ---- stage: Histogram Fine-Tune (stage_hist.py) -----------------
    # Channel identifiers ("RGB"/"R"/"G"/"B") are deliberately NOT
    # translated anywhere in this stage — they're read back as dict
    # keys (self.hist_controls[ch], self.hist_editor.params[ch]) and
    # wired straight through a Qt signal (currentTextChanged), and
    # they're conventional international notation for color channels
    # rather than prose that needs localizing.
    "hist_info": {
        "en": "Drag the three points (⚫ shadows, ◾ midtones, ⚪ "
              "highlights) on the histogram — the preview updates "
              "live. Pick a channel to fine-tune colors separately.",
        "zh": "拖曳直方圖上的三個控制點（⚫ 陰影、◾ 中間調、⚪ 高光）——"
              "預覽會即時更新。可選擇個別色版分開微調顏色。"},
    "hist_load_btn": {
        "en": "📥  Load current image", "zh": "📥  載入目前影像"},
    "hist_load_tooltip": {
        "en": "Grab the image currently loaded in Siril into the "
              "editor (histogram + live preview)",
        "zh": "把 Siril 目前載入的影像抓進編輯器（直方圖＋即時預覽）"},
    "hist_channel_label": {"en": "Channel:", "zh": "色版："},
    "hist_col_shadows": {"en": "Shadows", "zh": "陰影"},
    "hist_col_midtones": {"en": "Midtones", "zh": "中間調"},
    "hist_col_highlights": {"en": "Highlights", "zh": "高光"},
    "hist_reset_btn": {"en": "↺  Reset", "zh": "↺  重設"},
    "hist_no_image_title": {"en": "No image", "zh": "沒有影像"},
    "hist_loaded_status": {
        "en": "Histogram editor loaded — drag the points to fine-tune.",
        "zh": "直方圖編輯器已載入——拖曳控制點進行微調。"},
    "hist_progress_adjusting": {
        "en": "Histogram: adjusting {ch}...", "zh": "直方圖：正在調整 {ch}..."},
    "hist_progress_fetching": {
        "en": "Histogram: fetching image...", "zh": "直方圖：正在讀取影像..."},
    "hist_progress_applying": {
        "en": "Histogram: applying stretch (full resolution)...",
        "zh": "直方圖：正在套用拉伸（完整解析度）..."},
    "hist_progress_done": {
        "en": "Histogram fine-tune: done.", "zh": "直方圖微調：完成。"},

    # ---- stage: Crop (stage_crop.py) --------------------------------
    "crop_auto": {
        "en": "Auto crop (5% off each side)", "zh": "自動裁切（四邊各裁 5%）"},
    "crop_margin_left": {"en": "Left %", "zh": "左邊 %"},
    "crop_margin_right": {"en": "Right %", "zh": "右邊 %"},
    "crop_margin_top": {"en": "Top %", "zh": "上邊 %"},
    "crop_margin_bottom": {"en": "Bottom %", "zh": "下邊 %"},
    "crop_rotate_label": {"en": "Rotate (°):", "zh": "旋轉（°）："},
    "crop_rotate_tooltip": {
        "en": "Rotate the image before cropping. Positive is counter-"
              "clockwise. Siril crops to the original frame size after "
              "rotating (no black borders), so set the margins/drawn "
              "box below generously enough to trim whatever the "
              "rotation leaves ragged at the edges. The preview "
              "updates live as you drag this — it's a quick on-screen "
              "approximation (Qt rotating the already-rendered preview "
              "image), not the same interpolation Siril's own `rotate` "
              "command uses, so treat it as a guide for "
              "framing/angle, not a pixel-exact result.",
        "zh": "在裁切之前先旋轉影像。正值為逆時針。Siril 旋轉後會裁回原"
              "始畫幅尺寸（不留黑邊），所以下方的邊距／手繪裁切框要留得"
              "夠寬，才能修掉旋轉造成的參差邊緣。拖曳時預覽會即時更"
              "新——這只是螢幕上的快速近似效果（Qt 直接旋轉已算好的預"
              "覽影像），並非 Siril `rotate` 指令實際使用的內插方式，"
              "請把它當作構圖／角度的參考，而非逐像素精確的結果。"},
    "crop_draw_btn": {
        "en": "⬚  Draw crop box in preview", "zh": "⬚  在預覽中手繪裁切框"},
    "crop_draw_tooltip": {
        "en": "Click, then drag a rectangle on the preview panel. This "
              "only\nmarks the box and switches off Auto crop — press "
              "\"Run this\nstage\" below to actually crop.",
        "zh": "點擊後，在預覽面板上拖曳出一個矩形。這只會標記裁切框，"
              "並\n關閉「自動裁切」——實際裁切請按下方的「執行此步"
              "驟」。"},
    "crop_draw_hint_dragging": {
        "en": "Drag a box on the preview to mark the crop. Click the "
              "button again to cancel.",
        "zh": "在預覽上拖曳出一個框來標記裁切範圍。再按一次按鈕可取"
              "消。"},
    "crop_box_marked": {
        "en": "Box marked ({w:.0f}% × {h:.0f}% of the image) — press "
              "\"{run}\" below to crop.",
        "zh": "裁切框已標記（影像的 {w:.0f}% × {h:.0f}%）——按下方的"
              "「{run}」進行裁切。"},
    "crop_canceled_status": {"en": "Crop box canceled.", "zh": "已取消裁切框。"},
    "crop_progress_fetching": {
        "en": "Crop: fetching image...", "zh": "裁切：正在讀取影像..."},
    "crop_progress_rotating": {
        "en": "Crop: rotating {deg:.1f}°...", "zh": "裁切：正在旋轉 {deg:.1f}°..."},
    "crop_progress_drawn_box": {
        "en": "Crop: {w}x{h} → {cw}x{ch} (drawn box)...",
        "zh": "裁切：{w}x{h} → {cw}x{ch}（手繪框）..."},
    "crop_progress_sizing": {
        "en": "Crop: {w}x{h} → {cw}x{ch}...", "zh": "裁切：{w}x{h} → {cw}x{ch}..."},
    "crop_progress_nothing": {
        "en": "Crop: nothing to do (0% margins, no rotation).",
        "zh": "裁切：沒有需要處理的內容（邊距 0%，未旋轉）。"},
    "crop_progress_done": {"en": "Crop: done.", "zh": "裁切：完成。"},
    "crop_error_too_small": {
        "en": "Drawn crop box is too small (min 32 px).",
        "zh": "手繪的裁切框太小（最小 32 px）。"},
    "crop_error_margins": {
        "en": "Crop margins too large — nothing would remain.",
        "zh": "裁切邊距太大——影像會完全裁光。"},

    # ---- stage: Denoise (stage_denoise.py) --------------------------
    # The long GPU/CoreML troubleshooting tooltips (model combo, batch
    # size, GPU acceleration checkbox) are deliberately left English-
    # only for this pass — dense technical/debugging prose (error
    # message fragments, GitHub issue references) where a careful
    # translation would take real effort for comparatively low payoff
    # versus the short, always-visible labels below. Flagged as a known
    # gap rather than silently skipped; can be added in a later pass.
    "den_model_label": {"en": "Model:", "zh": "模型："},
    "den_no_models_found": {"en": "No models found", "zh": "找不到模型"},
    "den_strength_label": {"en": "Strength:", "zh": "強度："},
    "den_batch_label": {"en": "Batch size:", "zh": "批次大小："},
    "den_gpu": {"en": "GPU acceleration", "zh": "GPU 加速"},
    "den_no_model_error": {
        "en": "No GraXpert denoise model found. Download one via "
              "GraXpert or the GraXpert-AI script's Model Manager.",
        "zh": "找不到 GraXpert 去噪模型。請透過 GraXpert 或 GraXpert-AI "
              "script 的 Model Manager 下載一個模型。"},
    "den_progress_fetching": {
        "en": "Denoise: fetching image...", "zh": "去噪：正在讀取影像..."},
    "den_progress_done": {"en": "Denoise: done.", "zh": "去噪：完成。"},

    # ---- stage: Stretch / VeraLux HyperMetric (stage_stretch.py) ----
    # Sensor profile names (self.profile_combo, from SENSOR_PROFILES)
    # are NOT translated — they're manufacturer/model names (e.g. "ZWO
    # Seestar S30"), not prose, and are used as dict keys via
    # currentText() in several places.
    "str_profile_label": {"en": "Sensor profile:", "zh": "感光元件設定檔："},
    "str_mode_label": {"en": "Mode:", "zh": "模式："},
    "str_mode_rtu": {"en": "Ready-to-Use", "zh": "即用模式"},
    "str_mode_scientific": {"en": "Scientific", "zh": "科學模式"},
    "str_log_d_label": {"en": "Log D:", "zh": "Log D："},
    "str_target_bg_label": {"en": "Target bg:", "zh": "目標背景："},
    "str_protect_b_label": {"en": "Protect b:", "zh": "保護參數 b："},
    "str_convergence_label": {"en": "Convergence:", "zh": "收斂速度："},
    "str_color_grip_label": {"en": "Color grip:", "zh": "色彩抓取："},
    "str_linear_exp_label": {"en": "Linear exp:", "zh": "線性擴展："},
    "str_auto_d": {"en": "Auto Log D at run time", "zh": "執行時自動計算 Log D"},
    "str_auto_d_tooltip": {
        "en": "Solve the optimal Log D automatically when the stage runs",
        "zh": "在此步驟執行時自動求解最佳的 Log D"},
    "str_adaptive_anchor": {"en": "Adaptive anchor", "zh": "自適應錨點"},
    "str_calc_d_btn": {"en": "⚙  Auto Log D", "zh": "⚙  自動計算 Log D"},
    "str_calc_d_tooltip": {
        "en": "VeraLux smart solver: analyses the current image and "
              "computes the\nLog D that puts the sky background at the "
              "target level while\nbacking off if any color channel "
              "would clip (Floating Sky Check).\nFills the Log D box "
              "and switches Auto off so your value is used.",
        "zh": "VeraLux 智慧求解器：分析目前的影像，計算出能讓天空背景達"
              "到\n目標亮度的 Log D，同時在任何色版可能過曝時自動回"
              "退（懸浮天空檢查）。\n會填入 Log D 欄位並關閉「自動」，"
              "改用求解出的值。"},
    "str_reset_btn": {"en": "↺  Reset", "zh": "↺  重設"},
    "str_reset_tooltip": {
        "en": "Reset Log D, Protect b, Target bg, Convergence, Color "
              "grip, Linear expansion and the anchor/auto options to "
              "defaults (sensor profile and mode are left as-is).",
        "zh": "把 Log D、保護參數 b、目標背景、收斂速度、色彩抓取、線性"
              "擴展，以及錨點／自動選項全部重設為預設值（感光元件設定檔"
              "與模式維持不變）。"},
    "str_reset_status": {
        "en": "Stretch parameters reset to defaults.",
        "zh": "拉伸參數已重設為預設值。"},
    "str_solver_progress": {
        "en": "VeraLux solver: analysing image...",
        "zh": "VeraLux 求解器：正在分析影像..."},
    "str_solver_result_progress": {
        "en": "Optimal Log D = {d:.2f}", "zh": "最佳 Log D = {d:.2f}"},
    "str_progress_fetching": {
        "en": "Stretch: fetching image...", "zh": "拉伸：正在讀取影像..."},
    "str_progress_solving": {
        "en": "Stretch: solving optimal log D...", "zh": "拉伸：正在求解最佳 log D..."},
    "str_progress_stars": {
        "en": "Stretch: stretching stars separately (asinh)...",
        "zh": "拉伸：正在單獨拉伸星點（asinh）..."},
    "str_progress_recombining": {
        "en": "Stretch: recombining stars with nebula...",
        "zh": "拉伸：正在把星點與星雲重新合成..."},
    "str_progress_done": {"en": "Stretch: done.", "zh": "拉伸：完成。"},

    # ---- stage: Final Touch (stage_touch.py) ------------------------
    "touch_info": {
        "en": "iPhone-style finishing: brightness, contrast, "
              "saturation, shadows/highlights and sharpening. Load "
              "the image, drag sliders, watch the live preview, then "
              "run to apply at full resolution.",
        "zh": "iPhone 風格的最終潤飾：亮度、對比、飽和度、陰影／高光與"
              "銳化。載入影像後拖曳滑桿，即時預覽效果，再執行以套用到"
              "完整解析度。"},
    "touch_load_btn": {"en": "📥  Load image", "zh": "📥  載入影像"},
    "touch_load_tooltip": {
        "en": "Load the image currently in Siril into this stage's "
              "live preview.",
        "zh": "把 Siril 目前的影像載入這個步驟的即時預覽。"},
    "touch_reset_btn": {"en": "↺  Reset", "zh": "↺  重設"},
    "touch_slider_brightness": {"en": "☀ Brightness", "zh": "☀ 亮度"},
    "touch_slider_contrast": {"en": "◐ Contrast", "zh": "◐ 對比"},
    "touch_slider_saturation": {"en": "🎨 Saturation", "zh": "🎨 飽和度"},
    "touch_slider_shadows": {"en": "🌑 Shadows", "zh": "🌑 陰影"},
    "touch_slider_highlights": {"en": "🌕 Highlights", "zh": "🌕 高光"},
    "touch_slider_sharpen": {"en": "◇ Sharpen", "zh": "◇ 銳化"},
    "touch_sharpen_method_label": {
        "en": "Sharpen method:", "zh": "銳化方式："},
    "touch_sharpen_unsharp": {
        "en": "Unsharp Mask (fast)", "zh": "反差遮罩（快速）"},
    "touch_sharpen_rl": {
        "en": "Richardson-Lucy Deconvolution (recovers detail)",
        "zh": "Richardson-Lucy 反卷積（還原細節）"},
    "touch_sharpen_tooltip": {
        "en": "Unsharp Mask boosts existing edge contrast (cheap, "
              "safe).\nRichardson-Lucy Deconvolution estimates the "
              "blur PSF and inverts it — recovers more real detail "
              "(same idea as AstroSharp / PixInsight deconvolution) "
              "but is slower and can ring on noisy data. The Sharpen "
              "slider sets its iteration count.",
        "zh": "反差遮罩（Unsharp Mask）是增強既有邊緣對比（成本低、較"
              "安全）。\nRichardson-Lucy 反卷積會估算模糊點擴散函數並反"
              "向還原——能還原更多真實細節（與 AstroSharp／PixInsight "
              "的反卷積是同樣原理），但速度較慢，在雜訊較多的資料上可"
              "能出現振鈴效應。「銳化」滑桿控制其疊代次數。"},
    "touch_no_image_title": {"en": "No image", "zh": "沒有影像"},
    "touch_loaded_status": {
        "en": "Final Touch loaded — drag the sliders.",
        "zh": "最終潤飾已載入——拖曳滑桿即可調整。"},
    "touch_progress_fetching": {
        "en": "Final touch: fetching image...", "zh": "最終潤飾：正在讀取影像..."},
    "touch_progress_applying": {
        "en": "Final touch: applying adjustments (full resolution)...",
        "zh": "最終潤飾：正在套用調整（完整解析度）..."},
    "touch_progress_done": {
        "en": "Final touch: done.", "zh": "最終潤飾：完成。"},

    # ---- stage: Remove Background / BGE (stage_bge.py) --------------
    # bge_method_combo (GraXpert AI / Siril subsky) reads currentIndex()
    # everywhere, so it's safe to translate freely. bge_model_combo's
    # items are dynamic filesystem model names, like Denoise's — never
    # translated. bge_correction_combo ("subtraction"/"division") is
    # read via currentData(), same pattern as the other combos above.
    "bge_method_label": {"en": "Method:", "zh": "方法："},
    "bge_method_graxpert": {"en": "GraXpert AI", "zh": "GraXpert AI"},
    "bge_method_rbf": {"en": "Siril subsky — RBF", "zh": "Siril subsky — RBF"},
    "bge_method_poly": {
        "en": "Siril subsky — Polynomial", "zh": "Siril subsky — 多項式"},
    "bge_model_label": {"en": "Model:", "zh": "模型："},
    "bge_no_models_found": {"en": "No models found", "zh": "找不到模型"},
    "bge_correction_label": {"en": "Correction:", "zh": "校正方式："},
    "bge_correction_subtraction": {"en": "subtraction", "zh": "相減"},
    "bge_correction_division": {"en": "division", "zh": "相除"},
    "bge_smoothing_label": {"en": "Smoothing:", "zh": "平滑度："},
    "bge_samples_label": {"en": "Samples:", "zh": "取樣點數："},
    "bge_tolerance_label": {"en": "Tolerance:", "zh": "容差："},
    "bge_rbf_smooth_label": {"en": "RBF smooth:", "zh": "RBF 平滑："},
    "bge_poly_degree_label": {"en": "Poly degree:", "zh": "多項式階數："},
    "bge_subsky_info": {
        "en": "Siril's built-in background extraction — fast, no AI "
              "model needed. RBF handles complex gradients; polynomial "
              "suits simple linear gradients.",
        "zh": "Siril 內建的背景萃取功能——速度快，不需要 AI 模型。RBF "
              "適合複雜漸層；多項式適合簡單的線性漸層。"},
    "bge_boxes_btn": {"en": "🖼  Edit sample boxes...", "zh": "🖼  編輯取樣框..."},
    "bge_boxes_tooltip": {
        "en": "See the background sample boxes over the current "
              "image, click one to toggle it off/on, or click empty "
              "space to add a new one. The kept boxes are used instead "
              "of Siril's own automatic placement the next time this "
              "stage runs.",
        "zh": "在目前影像上顯示背景取樣框，點擊某個框可切換開關，或點擊"
              "空白處新增一個。保留下來的取樣框，會在此步驟下次執行時"
              "取代 Siril 自動放置的取樣點。"},
    "bge_boxes_status_default": {
        "en": "Using Siril's automatic sample placement (default).",
        "zh": "目前使用 Siril 自動放置的取樣點（預設）。"},
    "bge_dialog_title": {
        "en": "Preview & Edit Background Sample Boxes",
        "zh": "預覽與編輯背景取樣框"},
    "bge_dialog_info": {
        "en": "Click a box to toggle it off (red) or back on (green). "
              "Click empty space to add a new one there. The kept "
              "(green) boxes are used instead of Siril's automatic "
              "placement the next time this stage runs with a Siril "
              "subsky method.",
        "zh": "點擊某個框可切換為關閉（紅色）或開啟（綠色）。點擊空白處"
              "可在該處新增一個。保留下來的（綠色）取樣框，會在此步驟"
              "下次以 Siril subsky 方式執行時，取代 Siril 的自動放"
              "置。"},
    "bge_new_box_size_label": {"en": "New box size (px):", "zh": "新取樣框大小（px）："},
    "bge_regen_btn": {
        "en": "Regenerate default grid", "zh": "重新產生預設網格"},
    "bge_select_all_btn": {"en": "Select All", "zh": "全選"},
    "bge_deselect_all_btn": {"en": "Deselect All", "zh": "全部取消"},
    "bge_no_image_title": {"en": "No image", "zh": "沒有影像"},
    "bge_no_image_loaded": {
        "en": "No image loaded in Siril.", "zh": "Siril 目前沒有載入影像。"},
    "bge_no_boxes_title": {"en": "No boxes kept", "zh": "沒有保留任何取樣框"},
    "bge_no_boxes_body": {
        "en": "Every sample box was deselected — reverting to Siril's "
              "automatic placement instead of an empty sample set.",
        "zh": "所有取樣框都被取消了——已改回 Siril 的自動放置，而不是"
              "使用空的取樣集合。"},
    "bge_boxes_status_custom": {
        "en": "{n} custom sample box(es) set — will be used instead of "
              "Siril's automatic placement next time this stage runs. "
              "Click above to edit again, or Regenerate/select none to "
              "go back to automatic.",
        "zh": "已設定 {n} 個自訂取樣框——此步驟下次執行時將取代 Siril "
              "的自動放置。點擊上方按鈕可再次編輯，或重新產生／全部取"
              "消以改回自動模式。"},
    "bge_status_custom": {
        "en": "Remove background: {n} custom sample box(es) set.",
        "zh": "移除背景：已設定 {n} 個自訂取樣框。"},
    "bge_no_model_error": {
        "en": "No GraXpert background-extraction model found. Download "
              "one via GraXpert or the GraXpert-AI script's Model "
              "Manager — or switch the Method to Siril subsky.",
        "zh": "找不到 GraXpert 背景萃取模型。請透過 GraXpert 或 "
              "GraXpert-AI script 的 Model Manager 下載一個模型——或把"
              "「方法」切換為 Siril subsky。"},
    "bge_progress_fetching": {
        "en": "Remove background: fetching image...",
        "zh": "移除背景：正在讀取影像..."},
    "bge_progress_correcting": {
        "en": "Remove background: applying correction...",
        "zh": "移除背景：正在套用校正..."},
    "bge_progress_subsky": {
        "en": "Remove background: running Siril subsky...",
        "zh": "移除背景：正在執行 Siril subsky..."},
    "bge_progress_done": {
        "en": "Remove background: done.", "zh": "移除背景：完成。"},

    # ---- stage: Remove Stars / StarNet (stage_stars.py) -------------
    "stars_info": {
        "en": "Separates stars from nebulosity with StarNet so the "
              "later stages (denoise, palette, stretch) work on the "
              "starless image. The star layer is kept and stretched "
              "separately (gentle asinh) at the end of the Stretch "
              "stage, then recombined — keeping stars tight and "
              "colorful. Requires the StarNet executable to be set in "
              "Siril Preferences → Miscellaneous.",
        "zh": "使用 StarNet 把星點與星雲分離，讓後續步驟（去噪、調色、"
              "拉伸）都在無星影像上進行。星點圖層會被保留，並在「拉伸」"
              "步驟最後單獨用溫和的 asinh 曲線拉伸後再合成回去——讓星點"
              "保持緊緻、色彩鮮明。需要先在 Siril 偏好設定 → 雜項中設"
              "定 StarNet 執行檔路徑。"},
    "stars_strength_label": {"en": "Star strength:", "zh": "星點強度："},
    "stars_strength_tooltip": {
        "en": "Brightness of the stars when they are added back.\n"
              "1.0 = original brightness, lower = fainter stars, 0 = "
              "starless.",
        "zh": "星點加回時的亮度。\n1.0＝原始亮度，數值越低星點越暗淡，"
              "0＝完全無星。"},
    "stars_asinh_label": {"en": "Star stretch (asinh):", "zh": "星點拉伸（asinh）："},
    "stars_asinh_tooltip": {
        "en": "Intensity of the separate star stretch applied at the "
              "end of\nthe Stretch stage. 7–8 keeps stars tight and "
              "colorful.",
        "zh": "「拉伸」步驟最後單獨套用在星點上的拉伸強度。\n7–8 能讓星"
              "點保持緊緻、色彩鮮明。"},
    "stars_cache_label_default": {
        "en": "No star layer yet — running this stage calls StarNet "
              "once and caches the result until the source image "
              "changes or the window closes.",
        "zh": "尚未產生星點圖層——執行此步驟會呼叫一次 StarNet，並快取"
              "結果，直到來源影像改變或視窗關閉為止。"},
    "stars_manual_btn": {"en": "⭐ Add Stars Back Now", "zh": "⭐ 立即加回星點"},
    "stars_manual_tooltip": {
        "en": "Manual safety valve: blends the saved star layer onto "
              "whatever image is currently loaded in Siril right now, "
              "regardless of which stage you're on. Use this any time "
              "the automatic star\nhand-off (Remove Stars → Stretch) "
              "didn't put the stars back.\nWorks from the held-stars "
              "buffer if present, otherwise from the star layer "
              "cached to disk on the last StarNet run.",
        "zh": "手動保險機制：不論目前在哪個步驟，都會把已儲存的星點圖層"
              "混合到 Siril 目前載入的影像上。\n只要自動星點交接（「移"
              "除星點」→「拉伸」）沒有把星點加回來，隨時都可以用這個按"
              "鈕。\n優先使用記憶體中暫存的星點圖層，若沒有則改用最近一"
              "次 StarNet 執行時快取到硬碟的星點圖層。"},
    "stars_progress_fetching": {
        "en": "Remove stars: fetching image...", "zh": "移除星點：正在讀取影像..."},
    "stars_progress_reusing": {
        "en": "Remove stars: reusing cached StarNet result...",
        "zh": "移除星點：正在重複使用快取的 StarNet 結果..."},
    "stars_cache_reused": {
        "en": "✓ Reused cached star layer (StarNet skipped) — kept on "
              "disk until the source image changes or the window closes.",
        "zh": "✓ 已重複使用快取的星點圖層（跳過 StarNet）——會保留在硬"
              "碟上，直到來源影像改變或視窗關閉為止。"},
    "stars_progress_running": {
        "en": "Remove stars: running StarNet (may take a while)...",
        "zh": "移除星點：正在執行 StarNet（可能需要一段時間）..."},
    "stars_error_starnet_failed": {
        "en": "StarNet failed. Make sure the StarNet executable is set "
              "in Siril Preferences → Miscellaneous. ({e})",
        "zh": "StarNet 執行失敗。請確認已在 Siril 偏好設定 → 雜項中設定"
              "好 StarNet 執行檔路徑。（{e}）"},
    "stars_error_size_mismatch": {
        "en": "StarNet returned an unexpected image size.",
        "zh": "StarNet 回傳的影像尺寸不符預期。"},
    "stars_progress_caching": {
        "en": "Remove stars: caching star layer to disk...",
        "zh": "移除星點：正在把星點圖層快取到硬碟..."},
    "stars_cache_saved": {
        "en": "✓ Star layer cached to disk — repeat runs on this same "
              "image skip StarNet. Deleted when the window closes.",
        "zh": "✓ 星點圖層已快取到硬碟——對同一張影像重複執行時會跳過 "
              "StarNet。視窗關閉時會刪除。"},
    "stars_progress_done": {
        "en": "Remove stars: done — star layer held.",
        "zh": "移除星點：完成——星點圖層已保留。"},
    "stars_reconcile_progress": {
        "en": "Re-adding stars held back from the Palette stage "
              "(Stretch hasn't run yet)...",
        "zh": "正在加回從「調色」步驟保留下來的星點（「拉伸」尚未執"
              "行）..."},
    "stars_manual_progress_looking": {
        "en": "Add stars: looking for a saved star layer...",
        "zh": "加回星點：正在尋找已儲存的星點圖層..."},
    "stars_error_no_layer": {
        "en": "No star layer available to add back. Run the Remove "
              "Stars stage at least once, then try this button.",
        "zh": "沒有可加回的星點圖層。請先至少執行一次「移除星點」步"
              "驟，再按這個按鈕。"},
    "stars_error_shape_mismatch": {
        "en": "The saved star layer {shape1} doesn't match the "
              "current image {shape2} — likely a crop or resize "
              "happened since the stars were removed. Re-run the "
              "Remove Stars stage to recapture them at the current "
              "size.",
        "zh": "已儲存的星點圖層 {shape1} 與目前影像 {shape2} 尺寸不符"
              "——可能是移除星點之後做過裁切或縮放。請重新執行「移除星"
              "點」步驟，以目前的尺寸重新擷取星點。"},
    "stars_error_zero_strength": {
        "en": "Star strength is set to 0 in the Remove Stars stage — "
              "raise it above 0 before adding stars back.",
        "zh": "「移除星點」步驟中的星點強度目前是 0——請先調高後再加回"
              "星點。"},
    "stars_manual_progress_blending": {
        "en": "Add stars: blending stars onto the current image...",
        "zh": "加回星點：正在把星點混合到目前的影像..."},
    "stars_manual_progress_done": {"en": "Add stars: done.", "zh": "加回星點：完成。"},

    # ---- stage: Hubble Palette (stage_palette.py) -------------------
    # Preset names (self.palette_preset_combo, from PALETTE_PRESETS) and
    # channel letters ("R"/"G"/"B", "Hα weight"/"OIII weight" row/column
    # identifiers) are NOT translated — presets are dict keys shared
    # with constants.py's PALETTE_PRESETS/PALETTE_TO_PROFILE and with
    # settings JSON (currentText()), and channel letters are
    # conventional notation, same reasoning as stage_hist.py.
    "pal_info": {
        "en": "For dual-band (LP filter) data on emission nebulae. "
              "Extracts Hα from red and OIII from green+blue, then "
              "remixes them into a false-color palette. No real SII "
              "exists on an OSC camera — SHO here is synthetic. Turn "
              "SPCC off in stage 1 when using this. Tip: run stage 5 "
              "(Remove Stars) first so the palette only recolors the "
              "nebula, not the stars.",
        "zh": "適用於雙頻（LP 濾鏡）拍攝的發射星雲資料。從紅色通道萃取"
              "Hα，從綠＋藍通道萃取 OIII，再重新混合成假色調色盤。OSC "
              "相機沒有真正的 SII 訊號——這裡的 SHO 是合成出來的。使用"
              "此功能時，請在步驟 1 關閉 SPCC。小技巧：先執行步驟 5"
              "（移除星點），這樣調色只會影響星雲，不會影響星點。"},
    "pal_mode_label": {"en": "Mode:", "zh": "模式："},
    "pal_mode_mix": {
        "en": "Channel mix (SHO / HOO)", "zh": "通道混合（SHO／HOO）"},
    "pal_mode_nebulachrome": {
        "en": "NebulaChrome (deep palette)", "zh": "NebulaChrome（深度調色）"},
    "pal_mode_tooltip": {
        "en": "Channel mix: extract Hα/OIII and remix with the weights "
              "below.\nNebulaChrome: background neutralization + "
              "bright-core white\nreference (pushes the Hα core toward "
              "teal while the faint rim\nstays red — no channel math), "
              "followed by a saturation /\nshadows-highlights polish "
              "and a deconvolution sharpen pass. The\nrecolor/"
              "saturation are luminosity-masked to the nebula "
              "itself\n(Peak isolation slider) so the background "
              "doesn't pick up a\ncolor cast, then the whole result is "
              "blended against the\noriginal by the Recolor strength "
              "slider below.",
        "zh": "通道混合：萃取 Hα／OIII，用下方權重重新混合。\nNebulaChrome："
              "背景中性化＋明亮核心白點參考\n（讓 Hα 核心偏向青綠色，同"
              "時邊緣較暗的部分維持紅色——不做\n通道數學運算），接著做"
              "飽和度／陰影高光潤飾與反卷積銳化。\n重新上色／飽和度都會"
              "依亮度遮罩限制在星雲本體上\n（尖峰隔離滑桿），避免背景染"
              "上色偏，最後整體結果再依\n下方的重新上色強度滑桿與原圖"
              "混合。"},
    "pal_preset_label": {"en": "Preset:", "zh": "預設集："},
    "pal_ha_weight": {"en": "Hα weight", "zh": "Hα 權重"},
    "pal_oiii_weight": {"en": "OIII weight", "zh": "OIII 權重"},
    "pal_linfit": {"en": "Linear fit OIII to Hα", "zh": "OIII 線性擬合至 Hα"},
    "pal_linfit_tooltip": {
        "en": "Rescales the (usually much weaker) OIII signal so its "
              "background\nand spread match Hα before mixing — "
              "recommended.",
        "zh": "在混合前，把（通常弱得多的）OIII 訊號重新縮放，讓它的背"
              "景\n與分佈範圍與 Hα 一致——建議開啟。"},
    "pal_auto_profile": {
        "en": "Auto-set stretch profile (narrowband)",
        "zh": "自動設定拉伸設定檔（窄頻）"},
    "pal_nc_strength_label": {
        "en": "NebulaChrome recolor strength:", "zh": "NebulaChrome 重新上色強度："},
    "pal_nc_strength_tooltip": {
        "en": "How strongly to blend the NebulaChrome recolor/polish/"
              "sharpen result against the original — 100% is the full "
              "effect, lower values keep more of the original color. "
              "This is what keeps the effect controllable instead of "
              "overcorrecting like the old Color Calibration trick did.",
        "zh": "NebulaChrome 重新上色／潤飾／銳化結果與原圖混合的強"
              "度——100% 為完整效果，數值越低保留越多原始色彩。這讓效果"
              "可控，不會像舊版「色彩校正技巧」那樣過度校正。"},
    "pal_nc_peak_label": {
        "en": "NebulaChrome peak isolation:", "zh": "NebulaChrome 尖峰隔離："},
    "pal_nc_peak_tooltip": {
        "en": "How sharply the recolor/saturation is restricted to "
              "bright nebula structure vs. the sky background — an "
              "automatic luminosity mask. Higher = a harder cutoff "
              "(background stays untouched even if it isn't perfectly "
              "neutral), lower = a softer, more gradual falloff. Fixes "
              "the background picking up a blue cast from the recolor.",
        "zh": "重新上色／飽和度限制在明亮星雲結構（相對於天空背景）的嚴"
              "格程度——一種自動亮度遮罩。數值越高，區隔越明確（即使背"
              "景不夠中性，也維持不受影響）；數值越低，過渡越柔和漸"
              "進。可修正背景因重新上色而染上藍色偏色的問題。"},
    "pal_gimp_toggle": {
        "en": "GIMP replacement polish", "zh": "GIMP 替代潤飾"},
    "pal_gimp_toggle_tooltip": {
        "en": "Click to expand/collapse — collapsed by default since "
              "this is an optional extra pass most people won't need.",
        "zh": "點擊以展開／收合——預設為收合狀態，因為這是大多數人不需"
              "要的選用額外步驟。"},
    "pal_gimp_info": {
        "en": "Colors ▸ Saturation, Colors ▸ Shadows-Highlights, "
              "Colors ▸ Brightness-Contrast, Filters ▸ Enhance ▸ "
              "Sharpen, and Filters ▸ Enhance ▸ Noise Reduction, "
              "folded into one tunable, repeatable step (from "
              "gimp_replacement.py) instead of a manual TIFF "
              "round-trip through GIMP. Runs after the recolor above, "
              "on whichever mode you picked. All sliders default to "
              "\"no change\".",
        "zh": "把 GIMP 的 Colors ▸ Saturation、Colors ▸ "
              "Shadows-Highlights、Colors ▸ Brightness-Contrast、"
              "Filters ▸ Enhance ▸ Sharpen 與 Filters ▸ Enhance ▸ "
              "Noise Reduction，整合成一個可調整、可重複執行的步驟"
              "（來自 gimp_replacement.py），取代手動把 TIFF 匯出到 "
              "GIMP 來回處理。會在上方重新上色之後執行，不論你選的是哪"
              "個模式。所有滑桿預設都是「不改變」。"},
    "pal_gimp_apply": {
        "en": "Apply GIMP replacement polish", "zh": "套用 GIMP 替代潤飾"},
    "pal_gimp_apply_tooltip": {
        "en": "When off, none of the sliders below have any effect — "
              "the Hubble Palette stage output is just the recolor "
              "result above, same as before this option existed.",
        "zh": "關閉時，下方所有滑桿都不會生效——「Hubble 調色盤」步驟的"
              "輸出就只是上方的重新上色結果，與新增此選項之前相同。"},
    "pal_gimp_saturation": {"en": "🎨 Saturation", "zh": "🎨 飽和度"},
    "pal_gimp_saturation_tooltip": {
        "en": "Colors ▸ Saturation. 100% = unchanged, HSV saturation "
              "channel scaled by this factor.",
        "zh": "對應 Colors ▸ Saturation。100%＝不變，依此倍率縮放 HSV "
              "飽和度通道。"},
    "pal_gimp_shadows": {"en": "🌑 Shadows", "zh": "🌑 陰影"},
    "pal_gimp_shadows_tooltip": {
        "en": "Colors ▸ Shadows-Highlights (shadows side). Positive "
              "lifts dark tones — can reveal hidden detail but also "
              "lifts noise.",
        "zh": "對應 Colors ▸ Shadows-Highlights（陰影側）。正值會提亮暗"
              "部——可能揭露隱藏細節，但也會提升雜訊。"},
    "pal_gimp_highlights": {"en": "🌕 Highlights", "zh": "🌕 高光"},
    "pal_gimp_highlights_tooltip": {
        "en": "Colors ▸ Shadows-Highlights (highlights/white-point "
              "side). Negative pulls down bright tones.",
        "zh": "對應 Colors ▸ Shadows-Highlights（高光／白點側）。負值會"
              "壓低亮部。"},
    "pal_gimp_contrast": {"en": "◐ Contrast", "zh": "◐ 對比"},
    "pal_gimp_contrast_tooltip": {
        "en": "Colors ▸ Brightness-Contrast (contrast only — "
              "brightness isn't part of this workflow, Stretch already "
              "handles that).",
        "zh": "對應 Colors ▸ Brightness-Contrast（僅對比——亮度不在此流"
              "程中處理，「拉伸」步驟已經處理過了）。"},
    "pal_gimp_sharpen": {"en": "◇ Sharpen", "zh": "◇ 銳化"},
    "pal_gimp_sharpen_tooltip": {
        "en": "Filters ▸ Enhance ▸ Sharpen (Unsharp Mask). Kept gentle "
              "by design in the tutorial, since AstroSharp/"
              "deconvolution does the heavier sharpening pass later.",
        "zh": "對應 Filters ▸ Enhance ▸ Sharpen（反差遮罩）。刻意設計得"
              "較溫和，因為 AstroSharp／反卷積會在稍後做更強的銳化。"},
    "pal_gimp_denoise": {"en": "✦ Denoise", "zh": "✦ 去噪"},
    "pal_gimp_denoise_tooltip": {
        "en": "Filters ▸ Enhance ▸ Noise Reduction — edge-preserving "
              "bilateral denoise, a light manual touch-up (not the AI "
              "Denoise stage earlier in the pipeline).",
        "zh": "對應 Filters ▸ Enhance ▸ Noise Reduction——保邊雙邊濾波去"
              "噪，屬於輕度的手動微調（不是前面管線中的 AI 去噪步"
              "驟）。"},
    "pal_gimp_reset_btn": {"en": "↺  Reset", "zh": "↺  重設"},
    "pal_stretch_ran_title": {
        "en": "Stretch already ran", "zh": "拉伸已經執行過"},
    "pal_stretch_ran_body": {
        "en": "The Stretch stage has already run. Hubble Palette "
              "normally runs before Stretch — applying it now will "
              "recombine channels on an already-stretched (non-linear) "
              "image, which may look unexpected.\n\nRun Palette anyway?",
        "zh": "「拉伸」步驟已經執行過了。Hubble 調色盤通常應該在拉伸之"
              "前執行——現在套用會在已經拉伸過（非線性）的影像上重新混"
              "合色版，結果可能與預期不同。\n\n仍要執行調色盤嗎？"},
    "pal_error_rgb_required": {
        "en": "Hubble palette requires an RGB image (mono images have "
              "no channels to remix).",
        "zh": "Hubble 調色盤需要 RGB 影像（單色影像沒有色版可以重新混"
              "合）。"},
    "pal_progress_fetching": {
        "en": "Palette: fetching image...", "zh": "調色盤：正在讀取影像..."},
    "pal_progress_extracting": {
        "en": "Palette: extracting Hα / OIII...",
        "zh": "調色盤：正在萃取 Hα／OIII..."},
    "pal_progress_linfit": {
        "en": "Palette: linear-fitting OIII to Hα...",
        "zh": "調色盤：正在把 OIII 線性擬合至 Hα..."},
    "pal_progress_mixing": {
        "en": "Palette: mixing '{preset}'...", "zh": "調色盤：正在混合「{preset}」..."},
    "pal_progress_gimp": {
        "en": "Palette: GIMP replacement polish...",
        "zh": "調色盤：正在套用 GIMP 替代潤飾..."},
    "pal_progress_done": {"en": "Palette: done.", "zh": "調色盤：完成。"},
    "pal_gimp_progress_saturation": {
        "en": "GIMP polish: saturation...", "zh": "GIMP 潤飾：正在調整飽和度..."},
    "pal_gimp_progress_tone": {
        "en": "GIMP polish: shadows/highlights...",
        "zh": "GIMP 潤飾：正在調整陰影／高光..."},
    "pal_gimp_progress_contrast": {
        "en": "GIMP polish: contrast...", "zh": "GIMP 潤飾：正在調整對比..."},
    "pal_gimp_progress_sharpen": {
        "en": "GIMP polish: sharpen...", "zh": "GIMP 潤飾：正在銳化..."},
    "pal_gimp_progress_denoise": {
        "en": "GIMP polish: noise reduction...", "zh": "GIMP 潤飾：正在降噪..."},
    "pal_nc_progress_neutralize": {
        "en": "NebulaChrome: background neutralization...",
        "zh": "NebulaChrome：正在中性化背景..."},
    "pal_nc_progress_mask": {
        "en": "NebulaChrome: building luminosity mask...",
        "zh": "NebulaChrome：正在建立亮度遮罩..."},
    "pal_nc_progress_whiteref": {
        "en": "NebulaChrome: white reference from nebula core...",
        "zh": "NebulaChrome：正在依星雲核心建立白點參考..."},
    "pal_nc_progress_polish": {
        "en": "NebulaChrome: saturation & tone polish...",
        "zh": "NebulaChrome：正在潤飾飽和度與色調..."},
    "pal_nc_progress_sharpen": {
        "en": "NebulaChrome: deconvolution sharpen...",
        "zh": "NebulaChrome：正在進行反卷積銳化..."},
    "pal_nc_progress_blending": {
        "en": "NebulaChrome: blending...", "zh": "NebulaChrome：正在混合..."},

    # ---- stage: SCNR (stage_scnr.py) --------------------------------
    "scnr_info": {
        "en": "Runs Siril's rmgreen command — removes the green cast "
              "typical of OSC stacks. Safe to run more than once.",
        "zh": "執行 Siril 的 rmgreen 指令——移除彩色相機(OSC)疊圖常見的偏"
              "綠色偏色。可以重複執行，沒有問題。"},
    "scnr_type_label": {"en": "Type:", "zh": "類型："},
    "scnr_type_avg": {"en": "Average neutral", "zh": "平均中性"},
    "scnr_type_max": {"en": "Maximum neutral", "zh": "最大中性"},
    "scnr_amount_label": {"en": "Amount:", "zh": "強度："},
    "scnr_preserve": {"en": "Preserve lightness", "zh": "保留明度"},
    "scnr_progress_fetching": {
        "en": "SCNR: fetching image...", "zh": "SCNR：正在讀取影像..."},
    "scnr_progress_removing": {
        "en": "SCNR: removing green noise...", "zh": "SCNR：正在移除綠色雜訊..."},
    "scnr_progress_done": {"en": "SCNR: done.", "zh": "SCNR：完成。"},

    # ---- stage: Watermark (stage_watermark.py) ---------------------
    "wm_title": {"en": "Watermark", "zh": "浮水印"},
    "wm_info": {
        "en": "Draws a semi-transparent info block onto the image using "
              "the fields checked below (same data as the info bar "
              "above, without icons), plus an optional free-text Author "
              "credit line. Saves the block into the working image — "
              "use Undo to remove it.",
        "zh": "在影像上繪製一個半透明的資訊區塊，內容取自下方勾選的欄位"
              "（與上方資訊列相同的資料，但不含圖示），並可額外加上一行"
              "自由輸入的作者／版權文字。這個區塊會直接存進工作用影像——"
              "要移除的話請使用「復原」。"},
    "wm_field_object": {"en": "Object name", "zh": "目標名稱"},
    "wm_field_date": {"en": "Date", "zh": "日期"},
    "wm_field_telescope": {"en": "Telescope", "zh": "望遠鏡"},
    "wm_field_integration": {"en": "Integration time", "zh": "總曝光時間"},
    "wm_field_fov": {"en": "FOV", "zh": "視野範圍"},
    "wm_field_size": {"en": "Image size", "zh": "影像尺寸"},
    "wm_field_bortle": {"en": "Bortle estimate", "zh": "波特爾等級估計"},
    "wm_integration_unit_label": {
        "en": "Integration time unit:", "zh": "總曝光時間單位："},
    # Same pattern as wm_pos_* above: displayed text is translated, but
    # the combo's underlying value (currentData()) stays the canonical
    # English "Minutes"/"Hours"/"Seconds" used by
    # _gather_watermark_fields's own comparison and by settings JSON.
    "wm_unit_minutes": {"en": "Minutes", "zh": "分鐘"},
    "wm_unit_hours": {"en": "Hours", "zh": "小時"},
    "wm_unit_seconds": {"en": "Seconds", "zh": "秒"},
    "wm_integration_unit_tooltip": {
        "en": "Unit used to display the Integration time field above.\n"
              "Minutes is the default (e.g. \"180 min\"); switch to "
              "Hours for\nvery long sessions or Seconds for short ones. "
              "The sub count × exposure detail (e.g. \"360×30s\") is "
              "always shown alongside it when available.",
        "zh": "上方「總曝光時間」欄位顯示所用的單位。\n"
              "預設為分鐘（例如「180 min」）；拍攝時數很長時可切換為小時，"
              "很短時可切換為秒。只要資料可取得，張數×單張曝光的細節"
              "（例如「360×30s」）一律會一併顯示。"},
    "wm_author": {"en": "Author", "zh": "作者"},
    "wm_author_tooltip": {
        "en": "Adds a free-text credit line (typically your name or "
              "handle) to the watermark block — this isn't read from "
              "the image's metadata like the fields above, you type it "
              "yourself.",
        "zh": "在浮水印區塊加上一行自由輸入的credit文字（通常是你的名字"
              "或帳號）——這不像上面的欄位是從影像metadata讀取，而是"
              "由你自己輸入。"},
    "wm_author_placeholder": {"en": "Your name...", "zh": "你的名字..."},
    "wm_position_label": {"en": "Position:", "zh": "位置："},
    # Display text for WATERMARK_POSITIONS (constants.py) — the combo's
    # underlying *value* stays the canonical English string from that
    # list (read via currentData(), not currentText()) since it's also
    # used for settings JSON round-tripping and _render_watermark's own
    # "Right"/"Left"/"Top" substring matching; only the shown label is
    # translated.
    "wm_pos_bottom_right": {"en": "Bottom-Right", "zh": "右下"},
    "wm_pos_bottom_left": {"en": "Bottom-Left", "zh": "左下"},
    "wm_pos_bottom_center": {"en": "Bottom-Center", "zh": "下方置中"},
    "wm_pos_top_right": {"en": "Top-Right", "zh": "右上"},
    "wm_pos_top_left": {"en": "Top-Left", "zh": "左上"},
    "wm_pos_top_center": {"en": "Top-Center", "zh": "上方置中"},
    "wm_opacity_label": {"en": "Opacity:", "zh": "不透明度："},
    "wm_opacity_tooltip": {
        "en": "Opacity of the watermark's background block — 0% is "
              "fully see-through, 100% is a solid block.",
        "zh": "浮水印背景區塊的不透明度——0% 完全透明，100% 為實色區塊。"},
    "wm_two_col": {"en": "Two-column layout", "zh": "雙欄排列"},
    "wm_two_col_tooltip": {
        "en": "Lays the checked fields out in two side-by-side columns "
              "instead of one long vertical list — makes the block "
              "wider but noticeably shorter, useful when several fields "
              "are checked and you don't want the watermark to dominate "
              "the image's height.",
        "zh": "把勾選的欄位排成左右兩欄，而不是一長串直排——區塊會變寬，"
              "但明顯變矮，適合勾了很多欄位、又不想讓浮水印佔掉太多影像"
              "高度的情況。"},
    "wm_save_btn": {"en": "💾  Save image...", "zh": "💾  儲存影像..."},
    "wm_save_tooltip": {
        "en": "Export the last watermarked result as JPEG or PNG, "
              "wherever you choose.",
        "zh": "把最近一次的浮水印結果匯出成 JPEG 或 PNG，儲存到你選擇的"
              "位置。"},
    "wm_remove_all_btn": {"en": "🗑  Remove all", "zh": "🗑  全部移除"},
    "wm_remove_all_tooltip": {
        "en": "Restores the image to how it looked before the very "
              "first Watermark run in this session — undoes every "
              "watermark you've applied so far, not just the last one "
              "(the Undo button above only reverts the most recent "
              "run).",
        "zh": "把影像還原成這個工作階段第一次執行「浮水印」之前的樣子——"
              "會撤銷目前為止套用過的所有浮水印，不只是最近一次（上方的"
              "「復原」按鈕只會還原最近一次執行）。"},
    "wm_no_image_title": {"en": "No watermarked image", "zh": "尚無浮水印影像"},
    "wm_no_image_body": {
        "en": "Run the Watermark stage at least once first.",
        "zh": "請先至少執行一次「浮水印」步驟。"},
    "wm_save_dialog_title": {
        "en": "Save watermarked image", "zh": "儲存已加浮水印的影像"},
    "wm_save_failed_title": {"en": "Save failed", "zh": "儲存失敗"},
    "wm_no_watermark_title": {
        "en": "No watermark to remove", "zh": "沒有可移除的浮水印"},
    "wm_remove_confirm_title": {
        "en": "Remove all watermarks", "zh": "移除所有浮水印"},
    "wm_progress_fetching": {
        "en": "Watermark: fetching image...", "zh": "浮水印：正在讀取影像..."},
    "wm_progress_gathering": {
        "en": "Watermark: gathering info fields...",
        "zh": "浮水印：正在收集資訊欄位..."},
    "wm_progress_drawing": {
        "en": "Watermark: drawing...", "zh": "浮水印：正在繪製..."},
    "wm_progress_done": {"en": "Watermark: done.", "zh": "浮水印：完成。"},
    "wm_no_fields_error": {
        "en": "Nothing to watermark: no metadata fields are both checked "
              "and available in this image (check at least one, or make "
              "sure the image has the relevant header info, e.g. "
              "OBJECT, DATE-OBS, TELESCOP), and the Author field is "
              "either unchecked or empty.",
        "zh": "沒有可加上浮水印的內容：沒有任何metadata欄位同時符合「已"
              "勾選」且「這張影像有這項資料」（請至少勾選一項，或確認影"
              "像標頭有相關資訊，例如 OBJECT、DATE-OBS、TELESCOP），而"
              "「作者」欄位也未勾選或為空白。"},
    "wm_unsupported_format": {
        "en": "Unsupported format '{ext}' — choose .jpg or .png.",
        "zh": "不支援的格式「{ext}」——請選擇 .jpg 或 .png。"},
    "wm_saved_status": {
        "en": "Watermarked image saved: {name}",
        "zh": "已儲存加上浮水印的影像：{name}"},
    "wm_progress_removing": {
        "en": "Removing all watermarks...", "zh": "正在移除所有浮水印..."},
    "wm_progress_removed": {
        "en": "All watermarks removed.", "zh": "所有浮水印已移除。"},
    "wm_remove_confirm_body": {
        "en": "Restore the image to how it looked before any watermark "
              "was applied? This undoes every Watermark run so far, not "
              "just the last one.",
        "zh": "要把影像還原成套用任何浮水印之前的樣子嗎？這會撤銷目前為"
              "止所有的「浮水印」執行紀錄，不只是最近一次。"},

    # ---- stage: Preprocess / Smart Telescope Stacking (stage1_preprocess.py)
    # Everything that only ever reaches Siril's own external log console
    # (siril.log(...) / self._log_safe(...) calls) stays English
    # throughout this stage, same convention as _finish_stage's log_msg
    # elsewhere — that includes almost all of _platesolve_result,
    # _combine_registered_masters and _combine_with_existing_master's
    # narration. Only strings that reach THIS app's own UI (widget
    # labels/tooltips, the progress bar, RuntimeErrors shown via
    # QMessageBox.critical in _on_failed, and the two Comet Stack guided-
    # pause dialogs) are translated below. Telescope names
    # (self.telescope_combo, from TELESCOPES) and filter names
    # (self.filter_combo, from FILTER_OPTIONS_MAP) are not translated —
    # they're manufacturer/product names and dict keys, same reasoning as
    # stage_stretch.py's sensor profiles.
    "s1_telescope_label": {"en": "Telescope:", "zh": "望遠鏡："},
    "s1_filter_label": {"en": "Filter:", "zh": "濾鏡："},
    "s1_calibration_label": {"en": "Calibration:", "zh": "校正："},
    "s1_darks": {"en": "Darks", "zh": "暗場"},
    "s1_flats": {"en": "Flats", "zh": "平場"},
    "s1_biases": {"en": "Biases", "zh": "偏壓"},
    "s1_drizzle": {"en": "Drizzle", "zh": "Drizzle"},
    "s1_scale_label": {"en": "Scale:", "zh": "縮放倍率："},
    "s1_pixfrac_label": {"en": "Pixfrac:", "zh": "Pixfrac："},
    "s1_feather": {"en": "Feather", "zh": "羽化邊緣"},
    "s1_feather_tooltip": {
        "en": "Blends frame/panel edges over this many pixels when stacking.\n"
              "Together with per-frame background removal, this is the fix for\n"
              "visible strips at mosaic seams — try 100–300 px for mosaics.\n"
              "Only applies to the Average (rejection) stacking method below\n"
              "(Siril requires -maximize framing for this, which Median/Sum\n"
              "don't support).",
        "zh": "疊圖時，在這麼多像素範圍內混合每個畫格／拼接面板的邊緣。\n"
              "搭配逐格背景移除，是修正馬賽克拼接接縫處可見條紋的方"
              "法——拼接影像可嘗試 100–300 px。\n只適用於下方的「平均（剔"
              "除）」疊圖方式\n（Siril 需要 -maximize 取景方式才能使用此"
              "功能，Median／Sum 不支援）。"},
    "s1_amount_label": {"en": "Amount:", "zh": "數量："},
    "s1_overlap_norm": {"en": "Normalize on overlaps", "zh": "依重疊區域正規化"},
    "s1_overlap_norm_tooltip": {
        "en": "Computes stack normalization from only the overlapping regions\n"
              "between tiles/frames, instead of whole images (Siril's\n"
              "-overlap_norm, requires -maximize framing — used with the\n"
              "Average (rejection) stacking method below only; Median/Sum\n"
              "don't support -maximize).\n"
              "Helps when tiles have very different content (e.g. one mostly\n"
              "nebula, another mostly blank sky) and a seam still shows up\n"
              "with plain normalization. Slower to compute — try without it\n"
              "first, enable only if seams persist.",
        "zh": "只依拼接面板／畫格之間重疊的區域計算疊圖正規化，而不是用整"
              "張影像（Siril 的 -overlap_norm，需要 -maximize 取景方"
              "式——只適用於下方的「平均（剔除）」疊圖方式；Median／Sum 不"
              "支援 -maximize）。\n適合各拼接面板內容差異很大時使用（例如"
              "一張幾乎全是星雲、另一張幾乎全是空白天空），這種情況下即使"
              "用一般正規化，接縫仍可能出現。運算較慢——建議先不開啟，若"
              "接縫仍持續出現再開啟。"},
    "s1_stacking_method_label": {"en": "Stacking method:", "zh": "疊圖方式："},
    "s1_stack_avg": {"en": "Average (rejection)", "zh": "平均（剔除）"},
    "s1_stack_median": {
        "en": "Median (Milky Way Mode)", "zh": "中位數（銀河模式）"},
    "s1_stack_sum": {"en": "Sum", "zh": "加總"},
    "s1_stack_comet": {"en": "Comet Stack", "zh": "彗星疊圖"},
    "s1_stack_tip_avg": {
        "en": "Average (rejection): the usual choice for deep-sky — sigma-clip\n"
              "rejection (3/3) with normalization and weighting. Registered\n"
              "frames are padded to their union/max footprint before stacking\n"
              "(widest possible field of view).",
        "zh": "平均（剔除）：深空攝影的一般選擇——搭配正規化與加權的 "
              "sigma-clip 剔除（3/3）。已配準的畫格會先擴展到所有畫格的聯集／最"
              "大範圍再疊圖（取得最大可能視野）。"},
    "s1_stack_tip_median": {
        "en": "Median: no rejection settings, more robust than sigma-clip at\n"
              "erasing something that only shows up in a few frames (e.g. a\n"
              "satellite or plane trail) — ZWO's own recommendation for wide,\n"
              "trail-prone shots like Seestar's Milky Way Mode. Siril doesn't\n"
              "support padding mismatched frame sizes for Median, so frames\n"
              "are cropped to their common overlap instead — the result's\n"
              "field of view may be a bit smaller than Average's.",
        "zh": "中位數：沒有剔除設定，比 sigma-clip 更擅長消除只出現在少數"
              "畫格中的東西（例如衛星或飛機軌跡）——這是 ZWO 官方對於像"
              "Seestar 銀河模式這種廣角、容易拍到軌跡的拍攝建議方式。"
              "Siril 的中位數疊圖不支援擴展不同尺寸的畫格，因此改為裁切到"
              "共同重疊區域——結果的視野可能會比平均疊圖略小。"},
    "s1_stack_tip_sum": {
        "en": "Sum: no normalization or rejection at all — for planetary/lucky\n"
              "imaging stacks, not typically useful for deep-sky or Milky Way.\n"
              "Also cropped to the common overlap, like Median.",
        "zh": "加總：完全不做正規化或剔除——適合行星／幸運成像疊圖，一般"
              "不適合深空或銀河攝影。同樣會裁切到共同重疊區域，與中位數"
              "相同。"},
    "s1_stack_tip_comet": {
        "en": "Comet Stack: produces two separate stacks from the same subs —\n"
              "one registered on the stars, one on the comet's own motion —\n"
              "then combines them so both look sharp. Needs two brief manual\n"
              "steps in Siril's own window partway through (comet picking,\n"
              "then Star Recomposition) since neither has a console command.\n"
              "Automatically disables Remove Background and Remove Stars\n"
              "below (this mode already does both as part of its own\n"
              "workflow).",
        "zh": "彗星疊圖：從同一批原始畫格產生兩份獨立的疊圖——一份依星點配"
              "準，一份依彗星自身的運動配準——再合併兩者，讓星點與彗星都"
              "清晰銳利。過程中需要在 Siril 自己的視窗中做兩個簡短的手動"
              "步驟（挑選彗星、以及星點重組），因為這兩者都沒有對應的主控"
              "台指令。會自動關閉下方的「移除背景」與「移除星點」（此模式"
              "本身的流程已經包含這兩項工作）。"},
    "s1_weighting": {"en": "Stack weighting", "zh": "疊圖加權"},
    "s1_weighting_tooltip": {
        "en": "Weight frames during stacking by quality metric. Only applies\n"
              "to the Average (rejection) stacking method above.",
        "zh": "疊圖時依品質指標為每個畫格加權。只適用於上方的「平均（剔"
              "除）」疊圖方式。"},
    "s1_weight_noise": {"en": "Noise", "zh": "雜訊"},
    "s1_weight_nbstars": {"en": "Number of Stars", "zh": "星點數量"},
    "s1_weight_wfwhm": {"en": "Weighted FWHM", "zh": "加權 FWHM"},
    "s1_comet_settings_title": {
        "en": "Comet Stack settings", "zh": "彗星疊圖設定"},
    "s1_comet_info": {
        "en": "Produces a comet-sharp stack and a stars-sharp stack from "
              "the same subs, then pauses twice for quick manual steps in "
              "Siril's own window (comet picking, then Star Recomposition) "
              "that have no console-command equivalent. Remove Background "
              "and Remove Stars below are disabled — this mode already "
              "does both as part of its own workflow.",
        "zh": "從同一批原始畫格產生一份彗星清晰的疊圖與一份星點清晰的疊"
              "圖，過程中會暫停兩次，在 Siril 自己的視窗中進行簡短手動步"
              "驟（挑選彗星、以及星點重組），因為這兩者都沒有對應的主控台"
              "指令。下方的「移除背景」與「移除星點」會被關閉——此模式本"
              "身的流程已經包含這兩項工作。"},
    "s1_sigma_low_label": {"en": "Stack sigma low:", "zh": "疊圖 sigma 下限："},
    "s1_sigma_tooltip": {
        "en": "Rejection sigma (low side) used for both the comet stack and\n"
              "the star stack (Siril's `stack ... rej low high`). 5/5 is a\n"
              "reasonable default; other combinations like 2/5 or 3/5 also\n"
              "work well on comet data — experiment if the result has too\n"
              "much or too little rejection.",
        "zh": "彗星疊圖與星點疊圖共用的剔除 sigma（下限，Siril 的 `stack "
              "... rej low high`）。5/5 是合理的預設值；2/5 或 3/5 等其他"
              "組合在彗星資料上也可能效果不錯——如果剔除過多或過少，可以"
              "自行嘗試調整。"},
    "s1_sigma_high_label": {"en": "Stack sigma high:", "zh": "疊圖 sigma 上限："},
    "s1_bkg_degree_label": {"en": "Bkg degree:", "zh": "背景階數："},
    "s1_bkg_degree_tooltip": {
        "en": "Polynomial degree for the whole-sequence background removal\n"
              "(seqsubsky) this mode runs on the star-registered sequence,\n"
              "before star removal. 1 (linear) is the default.",
        "zh": "此模式在星點配準完成的序列上、移除星點之前，對整個序列執行"
              "背景移除（seqsubsky）所使用的多項式階數。預設為 1（線"
              "性）。"},
    "s1_bkg_samples_label": {"en": "Bkg samples:", "zh": "背景取樣點數："},
    "s1_bkg_samples_tooltip": {
        "en": "Number of background sample points for the whole-sequence\n"
              "seqsubsky above.",
        "zh": "上方整個序列 seqsubsky 所使用的背景取樣點數。"},
    "s1_distortion_order_label": {"en": "Distortion order:", "zh": "畸變階數："},
    "s1_distortion_order_tooltip": {
        "en": "SIP polynomial order used by the sequence plate solve to model\n"
              "lens distortion (needs the Gaia astrometry catalog).\n"
              "3–4 suits wide fields like smart telescopes; drop to 2–3 if\n"
              "solves fail on star-poor panels, raise to 5 only for extreme\n"
              "corner distortion. Default: 4.",
        "zh": "序列解算天球座標時，用來建模鏡頭畸變的 SIP 多項式階數（需"
              "要 Gaia 天測目錄）。\n3–4 適合像智慧望遠鏡這類廣角視野；若"
              "星點稀少的面板解算失敗可降到 2–3，只有在邊角畸變非常嚴重時"
              "才提高到 5。預設值：4。"},
    "s1_seqsubsky": {
        "en": "Per-frame background (mosaic seams)", "zh": "逐格背景（拼接接縫）"},
    "s1_seqsubsky_tooltip": {
        "en": "Runs seqsubsky (polynomial gradient removal, degree set below)\n"
              "on every calibrated sub before registration. Each mosaic panel\n"
              "has its own sky level/gradient — equalizing them BEFORE\n"
              "stacking is the main fix for bright strips at panel seams.\n"
              "Recommended for mosaics; harmless (slightly slower) for\n"
              "single-panel fields.",
        "zh": "在配準之前，對每張已校正的原始畫格執行 seqsubsky（多項式漸"
              "層移除，階數見下方設定）。每個拼接面板都有自己的天空亮"
              "度／漸層——在疊圖之前先把它們拉平，是修正面板接縫處出現亮"
              "條紋的主要方法。建議拼接影像開啟；單一面板的視野開啟也無"
              "妨（只是稍微變慢）。"},
    "s1_degree_label": {"en": "Degree:", "zh": "階數："},
    "s1_seqsubsky_degree_tooltip": {
        "en": "Polynomial degree for the per-frame background removal above.\n"
              "1 (linear) is the default and suits a simple sky tilt. Raise to\n"
              "2–4 if a seam persists with degree 1 — this usually means the\n"
              "per-panel gradient is more complex than a flat tilt (e.g.\n"
              "radial vignetting-like falloff). Higher degrees are slower and\n"
              "can overfit on frames with little background to sample, so\n"
              "only raise it if you actually see the fix helping.",
        "zh": "上方逐格背景移除所使用的多項式階數。預設為 1（線性），適合"
              "簡單的天空傾斜。若階數 1 仍有接縫，可提高到 2–4——這通常代"
              "表每個面板的漸層比單純的傾斜更複雜（例如類似暗角的放射狀衰"
              "減）。階數越高運算越慢，且在可取樣背景較少的畫格上容易過度"
              "擬合，只有在確實看到效果改善時才建議提高。"},
    "s1_spcc": {"en": "SPCC color calibration", "zh": "SPCC 色彩校正"},
    "s1_compression": {"en": "Compression (Rice)", "zh": "壓縮（Rice）"},
    "s1_compression_tooltip": {
        "en": "Compress intermediate FITS files to save disk space during processing",
        "zh": "在處理過程中壓縮中繼 FITS 檔案以節省磁碟空間"},
    "s1_cleanup": {"en": "Clean up temp files", "zh": "清除暫存檔案"},
    "s1_combine_title": {
        "en": "Combine with existing master", "zh": "與現有主檔合併"},
    "s1_combine_info_summary": {
        "en": "For merging in an already-stacked FITS from an earlier "
              "session that kept no raw subs.",
        "zh": "用於合併先前工作階段已疊圖完成、但未保留原始畫格的 FITS "
              "檔案。"},
    "s1_combine_info_full": {
        "en": "For when you already have a stacked FITS from an earlier "
              "session but the raw subs weren't kept.\n\n"
              "After stacking the lights above into a new master, this "
              "registers it against the file you pick here and combines "
              "the two with Siril's -weight=nbstack, so a master built "
              "from more subs correctly outweighs one built from fewer "
              "— needs the STACKCNT header Siril writes into every "
              "master it produces (use the override below if that file "
              "is missing it).\n\n"
              "Your original file is never modified.",
        "zh": "適用於你已有先前工作階段疊圖完成的 FITS 檔案、但沒有保留原"
              "始畫格的情況。\n\n把上方的 lights 疊圖成新的主檔之後，這個"
              "功能會將它與你在這裡選擇的檔案配準，並用 Siril 的 "
              "-weight=nbstack 合併兩者，讓由較多畫格組成的主檔正確地在加"
              "權上勝過由較少畫格組成的——需要該檔案有 Siril 疊圖時寫入的"
              "STACKCNT 標頭（若缺少，可用下方的覆寫選項補上）。\n\n"
              "你的原始檔案永遠不會被修改。"},
    "s1_no_file_selected": {"en": "No file selected", "zh": "尚未選擇檔案"},
    "s1_browse_btn": {"en": "Browse...", "zh": "瀏覽…"},
    "s1_subcount_label": {"en": "Sub count override:", "zh": "畫格數覆寫："},
    "s1_subcount_tooltip": {
        "en": "0 = trust whatever STACKCNT is already in that file's FITS "
              "header (if missing, Siril treats it as a single frame — "
              "likely under-weighting it badly). Set this if you know how "
              "many subs actually went into that master; it's written "
              "into a copy of the header before combining, never into "
              "your original file.",
        "zh": "0＝信任該檔案 FITS 標頭中已有的 STACKCNT 值（若缺少，"
              "Siril 會把它當成單一畫格——很可能嚴重低估其權重）。若你知"
              "道實際用了多少畫格組成該主檔，可在此設定；此設定只會寫入"
              "合併前的標頭副本，絕不會寫回你的原始檔案。"},
    "s1_batch_title": {"en": "Batch stacking", "zh": "分批疊圖"},
    "s1_batch_info_summary": {
        "en": "For sessions with too many subs to stack all at once "
              "(memory or disk pressure).",
        "zh": "適用於畫格數量太多、無法一次全部疊圖的工作階段（記憶體或"
              "磁碟空間吃緊）。"},
    "s1_batch_info_full": {
        "en": "For sessions with too many subs to stack all at once "
              "(memory or disk pressure).\n\n"
              "Every sub in the session is still registered together "
              "in one pass, exactly like a normal run — that part was "
              "never actually the problem. Only the memory-heavy "
              "rejection-stacking step is split into groups of the "
              "size below, each group stacking its own frame range out "
              "of that one shared, already-registered sequence.\n\n"
              "Every group's master is scale- and rotation-aligned with "
              "every other (same registration pass, same reference "
              "frame) — but each group's own framing is computed from "
              "just that group's own subset of shifts, so groups can "
              "still come out different physical sizes. The final "
              "combine reconciles that with a light, shift-only "
              "registration pass (Siril's -transf=shift — no rotation "
              "or scale for it to get wrong) before a weighted stack "
              "(-weight=nbstack, so a group built from more subs "
              "correctly outweighs one built from fewer).\n\n"
              "Calibration masters are still built once and shared by "
              "every group; SPCC and \"Combine with existing master\" "
              "still run once, on the final assembled result. Not "
              "compatible with Comet Stack mode.",
        "zh": "適用於畫格數量太多、無法一次全部疊圖的工作階段（記憶體或磁"
              "碟空間吃緊）。\n\n工作階段中的每張畫格仍然會在同一次流程"
              "中一起配準，與一般執行完全相同——這部分本來就不是問題所"
              "在。只有耗費記憶體較多的剔除疊圖步驟，會被拆分成下方大小"
              "的群組，每個群組從同一份共用、已配準完成的序列中，疊圖自"
              "己那段畫格範圍。\n\n每個群組的主檔在縮放與旋轉上都彼此對齊"
              "（同一次配準流程、同一個參考畫格）——但每個群組自己的取景"
              "範圍，是依該群組自身那部分位移計算出來的，因此群組之間的"
              "實際尺寸仍可能不同。最終合併時，會用一次輕量、僅有位移的配"
              "準流程（Siril 的 -transf=shift——沒有旋轉或縮放可能出"
              "錯）來調和這個差異，再進行加權疊圖（-weight=nbstack，讓由"
              "較多畫格組成的群組在加權上正確勝過較少畫格的群組）。\n\n"
              "校正主檔仍然只建立一次、由所有群組共用；SPCC 與「與現有主"
              "檔合併」也仍然只在最終組合完成的結果上執行一次。不支援與彗"
              "星疊圖模式同時使用。"},
    "s1_batch_checkbox": {"en": "Batch stacking", "zh": "分批疊圖"},
    "s1_subs_per_batch_label": {"en": "Subs per batch:", "zh": "每批畫格數："},
    "s1_subs_per_batch_tooltip": {
        "en": "How many light frames go into each batch. Lower uses less "
              "memory/disk per batch but means more (slower) combine "
              "rounds; higher is faster overall but each batch costs "
              "more. 100 is a reasonable starting point — if you're "
              "still hitting memory limits with 100, try 50.",
        "zh": "每一批包含多少張 light 畫格。數值越低，每批用的記憶體／磁"
              "碟越少，但合併輪次會變多（較慢）；數值越高整體較快，但每批"
              "的成本較高。100 是合理的起始值——如果 100 仍會碰到記憶體上"
              "限，可以試試 50。"},
    "s1_gaia_label": {
        "en": "Local Gaia — astrometry (plate solve): {astro}    "
              "photometry (SPCC): {photo}",
        "zh": "本機 Gaia — 天測（解算）：{astro}    測光（SPCC）：{photo}"},
    "s1_gaia_tooltip": {
        "en": "Local Gaia catalogues are configured in Siril Preferences → Astrometry.\n"
              "Without the astrometry catalogue, mosaics fall back to star registration.\n"
              "Without the photometry catalogue, SPCC uses the online catalogue.",
        "zh": "本機 Gaia 目錄可在 Siril 偏好設定 → 天測 中設定。\n若沒有天測目"
              "錄，拼接影像會改用星點配準。\n若沒有測光目錄，SPCC 會改用線"
              "上目錄。"},
    "s1_select_master_dialog_title": {
        "en": "Select existing master FITS", "zh": "選擇現有的主檔 FITS"},

    "s1_progress_starting": {
        "en": "Preprocess: starting...", "zh": "前處理：正在開始..."},
    "s1_progress_bortle": {
        "en": "Preprocess: estimating sky brightness (Bortle, sample subs)...",
        "zh": "前處理：正在估計天空亮度（波特爾等級，抽樣畫格）..."},
    "s1_progress_stacking_cal": {
        "en": "Preprocess: stacking {name}...", "zh": "前處理：正在疊圖 {name}..."},
    "s1_progress_converting": {
        "en": "Preprocess: converting lights...", "zh": "前處理：正在轉換 lights..."},
    "s1_progress_calibrating": {
        "en": "Preprocess: calibrating lights...", "zh": "前處理：正在校正 lights..."},
    "s1_progress_seqsubsky": {
        "en": "Preprocess: per-frame background removal (seqsubsky)...",
        "zh": "前處理：正在進行逐格背景移除（seqsubsky）..."},
    "s1_progress_platesolve_seq": {
        "en": "Preprocess: plate solving sequence...",
        "zh": "前處理：正在對序列進行天球解算..."},
    "s1_progress_registering": {
        "en": "Preprocess: registering (2-pass)...", "zh": "前處理：正在配準（兩階段）..."},
    "s1_progress_applying_reg": {
        "en": "Preprocess: applying registration...", "zh": "前處理：正在套用配準..."},
    "s1_progress_stacking": {
        "en": "Preprocess: stacking...", "zh": "前處理：正在疊圖..."},
    "s1_progress_platesolve_result": {
        "en": "Preprocess: plate solving result...", "zh": "前處理：正在對結果進行天球解算..."},
    "s1_progress_done": {"en": "Preprocess: done.", "zh": "前處理：完成。"},
    "s1_progress_batch_starting": {
        "en": "Preprocess: starting batch stacking...",
        "zh": "前處理：正在開始分批疊圖..."},
    "s1_progress_batch_range": {
        "en": "stacking frames {start}-{end} ({n} subs)...",
        "zh": "正在疊圖畫格 {start}-{end}（共 {n} 張）..."},
    "s1_progress_combining_batches": {
        "en": "Preprocess: combining all batches into one result...",
        "zh": "前處理：正在把所有批次合併成單一結果..."},
    "s1_progress_combine_master": {
        "en": "Preprocess: combining with existing master...",
        "zh": "前處理：正在與現有主檔合併..."},
    "s1_comet_progress_register": {
        "en": "Comet Stack: registering on stars (2-pass)...",
        "zh": "彗星疊圖：正在依星點配準（兩階段）..."},
    "s1_comet_progress_seqsubsky": {
        "en": "Comet Stack: removing background from the whole "
              "sequence (seqsubsky)...",
        "zh": "彗星疊圖：正在移除整個序列的背景（seqsubsky）..."},
    "s1_comet_progress_seqstarnet": {
        "en": "Comet Stack: removing stars from the whole sequence "
              "(seqstarnet)...",
        "zh": "彗星疊圖：正在移除整個序列的星點（seqstarnet）..."},
    "s1_comet_progress_splice": {
        "en": "Comet Stack: restoring registration data that "
              "seqstarnet dropped...",
        "zh": "彗星疊圖：正在還原 seqstarnet 遺失的配準資料..."},
    "s1_comet_progress_apply_reg": {
        "en": "Comet Stack: applying registration to the comet and "
              "star sequences (matched framing)...",
        "zh": "彗星疊圖：正在為彗星序列與星點序列套用配準（取景方式一"
              "致）..."},
    "s1_comet_progress_stack_comet": {
        "en": "Comet Stack: stacking the comet sequence...",
        "zh": "彗星疊圖：正在疊圖彗星序列..."},
    "s1_comet_progress_stack_star": {
        "en": "Comet Stack: stacking the star sequence...",
        "zh": "彗星疊圖：正在疊圖星點序列..."},

    "s1_error_no_lights_dir": {
        "en": "No 'lights' directory found in the working directory.",
        "zh": "工作目錄中找不到「lights」資料夾。"},
    "s1_error_batch_comet_unsupported": {
        "en": "Batch stacking doesn't support Comet Stack mode — its "
              "manual guided-pause steps don't make sense repeated "
              "per batch. Turn off Batch stacking, or switch "
              "Stacking method away from Comet Stack.",
        "zh": "分批疊圖不支援彗星疊圖模式——其手動引導步驟不適合每批重"
              "複進行。請關閉分批疊圖，或將疊圖方式改成彗星疊圖以外的選"
              "項。"},
    "s1_error_batch_feather_unsupported": {
        "en": "Batch stacking doesn't support feathering or overlap "
              "normalization — both need Siril's -maximize at stack "
              "time, which has to stay off per-batch so every "
              "batch's master comes out the same physical size (see "
              "the Batch stacking Details popup for why). Turn off "
              "feathering/overlap normalization, or turn off Batch "
              "stacking.",
        "zh": "分批疊圖不支援羽化邊緣或依重疊區域正規化——這兩者都需要"
              "Siril 在疊圖時使用 -maximize，但每批都必須關閉此選項，才能"
              "讓每批主檔的實際尺寸一致（原因請見「分批疊圖」的詳細資訊彈"
              "窗）。請關閉羽化邊緣／依重疊區域正規化，或關閉分批疊圖。"},
    "s1_error_no_fits_found": {
        "en": "No FITS light frames found in 'lights'.",
        "zh": "「lights」資料夾中找不到任何 FITS light 畫格。"},
    "s1_error_batch_no_result": {
        "en": "stacking didn't produce a result file.",
        "zh": "疊圖沒有產生結果檔案。"},
    "s1_error_comet_src_seq_missing": {
        "en": "Comet Stack: couldn't find {name} to copy registration "
              "data from — seqsubsky may have failed.",
        "zh": "彗星疊圖：找不到 {name}，無法從中複製配準資料——seqsubsky "
              "可能失敗了。"},
    "s1_error_comet_dst_seq_missing": {
        "en": "Comet Stack: couldn't find {name} to splice "
              "registration data into — seqstarnet may have failed.",
        "zh": "彗星疊圖：找不到 {name}，無法將配準資料接入其中——"
              "seqstarnet 可能失敗了。"},
    "s1_error_combine_no_file": {
        "en": "Combine with existing master is enabled but no valid "
              "file is selected — pick one in the Preprocess stage, "
              "or turn the option off.",
        "zh": "已開啟「與現有主檔合併」，但尚未選擇有效的檔案——請在「前"
              "處理」步驟中選擇一個檔案，或關閉此選項。"},
    "s1_error_combine_no_own_result": {
        "en": "Combine with existing master: couldn't find this run's "
              "own stacked result to combine against.",
        "zh": "與現有主檔合併：找不到此次執行自己的疊圖結果可供合併。"},

    "s1_comet_pause1_title": {
        "en": "Comet Stack — Comet Registration (manual step)",
        "zh": "彗星疊圖 — 彗星配準（手動步驟）"},
    "s1_comet_pause1_body": {
        "en": "Manual step required: in Siril's own window, go to the "
              "Registration tab. Set the registration method to 'Comet/"
              "Asteroid registration'. Make sure sequence "
              "'{comet_input_seq}' is selected. On the first frame, draw "
              "a box around the comet's nucleus and click 'Pick object in "
              "#1'. Go to the last frame, draw a box around the comet, "
              "click 'Pick object in #2'. Click 'Register'. Siril will "
              "create a new sequence named '{comet_seq}'. Once done, "
              "click Continue below.",
        "zh": "需要手動操作：在 Siril 自己的視窗中，前往「配準」分頁。把"
              "配準方式設為「彗星／小行星配準」。確認已選取序列 "
              "「{comet_input_seq}」。在第一格畫格上，框選彗星核心並點擊"
              "「Pick object in #1」。前往最後一格畫格，框選彗星，點擊"
              "「Pick object in #2」。點擊「Register」。Siril 會建立一個"
              "名為「{comet_seq}」的新序列。完成後，請點擊下方的「繼"
              "續」。"},
    "s1_comet_pause1_verify_error": {
        "en": "'{comet_seq}.seq' wasn't found in the process "
              "directory yet — the comet-registration step above "
              "doesn't look like it finished. Redo it in Siril's "
              "Registration tab, then click Continue again.",
        "zh": "process 資料夾中尚未找到「{comet_seq}.seq」——上方的彗星配"
              "準步驟看起來還沒完成。請在 Siril 的「配準」分頁中重新執"
              "行，再次點擊「繼續」。"},
    "s1_comet_pause2_title": {
        "en": "Comet Stack — Star Recomposition (manual step)",
        "zh": "彗星疊圖 — 星點重組（手動步驟）"},
    "s1_comet_pause2_body": {
        "en": "Manual step required: in Siril, go to Image Processing → "
              "Star Processing → Star Recomposition. Load 'comet_stack' "
              "and 'star_stack' as the two input images (use Linear mode, "
              "not auto-stretch, if you plan to apply your own stretch "
              "afterward — auto-stretch here can make manual stretch "
              "controls behave oddly). Click Apply. Once you're happy "
              "with the result, leave it as Siril's currently-loaded image "
              "and click Continue below — don't close or replace it.",
        "zh": "需要手動操作：在 Siril 中，前往「Image Processing → Star "
              "Processing → Star Recomposition」。載入「comet_stack」與"
              "「star_stack」作為兩張輸入影像（如果之後打算自行拉伸，請使"
              "用線性模式而非自動拉伸——這裡的自動拉伸可能讓手動拉伸控制"
              "行為異常）。點擊「Apply」。對結果滿意後，保持它為 Siril 目"
              "前載入的影像，並點擊下方的「繼續」——請勿關閉或替換它。"},
    "s1_comet_pause2_verify_error": {
        "en": "No image appears to be loaded in Siril — redo the Star "
              "Recomposition step (Image Processing → Star "
              "Processing → Star Recomposition), leave the result "
              "loaded, then click Continue again.",
        "zh": "Siril 目前似乎沒有載入任何影像——請重新執行星點重組步驟"
              "（Image Processing → Star Processing → Star "
              "Recomposition），保留結果為載入狀態，再次點擊「繼續」。"},

    # ---- stage: Annotate (stage_annotate.py) ------------------------
    # siril.log(...)/self._log_safe(...)-only text stays English, same
    # convention as every other stage. Two combo boxes are deliberately
    # NOT translated: ann_marker_style_combo (+ the per-object style
    # dialog's local `style_combo`) and ann_cross_label_pos_combo (+
    # dialog's `pos_combo`) — their displayed text ("Circle"/"Open
    # Cross"/"Circle + Open Cross", "NE"/"NW"/"SE"/"SW"/"Auto (avoid
    # overlap)") is read back via currentText() through several
    # module-level bidirectional dicts (_STYLE_KEY_TO_TEXT/
    # _TEXT_TO_STYLE_KEY, _POS_KEY_TO_TEXT/_TEXT_TO_POS_KEY) that are
    # shared across _default_style_for_object, _exec_stage_ann's own
    # marker-style branch, and the per-object style dialog's
    # capture/apply/reset logic — converting every one of those call
    # sites to currentData() safely, without automated UI test
    # coverage for this stage, was judged disproportionate to the
    # payoff versus the risk of a subtle behavioral regression;
    # NE/NW/SE/SW are compass abbreviations anyway (same reasoning as
    # channel letters elsewhere). CATALOG_LABELS/CATALOG_COLORS
    # (catalog_data.py) and CONSTELLATION_COLOR_PRESETS preset names
    # (constants shared with settings JSON / currentText() lookups)
    # are also not translated — same "proper noun / dict key" reasoning
    # as sensor profiles and palette presets elsewhere.
    "ann_info": {
        "en": "Labels stars and deep-sky objects for whatever's "
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
              "the FITS image itself is not modified.",
        "zh": "為目前這張已完成天球解算的影像，標記星點與深空天體。下方"
              "共三個步驟：選擇要顯示哪些物件、選擇要如何繪製它們（更"
              "改設定時本面板會立即更新）、然後執行——執行完成後，可用"
              "動作按鈕更新、選取、移除或儲存結果，不需要重新查詢任何"
              "目錄。Messier／NGC／IC 資料來自 OpenNGC（下載一次後快取"
              "在本機）；Sharpless 與 Lynds 暗星雲資料則來自即時的 "
              "VizieR 錐形搜尋——都是真實的結構化資料，不是從 Siril 主"
              "控台日誌猜測出來的。會在你的資料旁儲存一張加註影像的 "
              "JPG——不會修改 FITS 影像本身。"},
    "ann_step1_title": {"en": "① Objects to show", "zh": "① 要顯示的物件"},
    "ann_stars_checkbox": {
        "en": "Stars (local catalogue)", "zh": "星點（本機目錄）"},
    "ann_stars_tooltip": {
        "en": "Queries Siril's own local Bright Star Catalogue (3,661 stars, "
              "no internet needed) for stars in the field down to the star "
              "magnitude limit. Falls back to this script's own small "
              "bundled star list if Siril's conesearch command isn't "
              "available (Siril < 1.3).",
        "zh": "查詢 Siril 內建的本機亮星目錄（Bright Star Catalogue，3,661 "
              "顆星，不需要網路），列出視野中亮度達星等上限的星點。若 "
              "Siril 的 conesearch 指令無法使用（Siril < 1.3），則改用本 "
              "script 內建的小型星點清單。"},
    "ann_star_mag_label": {"en": "Star mag limit:", "zh": "星等上限："},
    "ann_cat_messier": {"en": "Messier", "zh": "Messier"},
    "ann_cat_messier_tooltip": {
        "en": "The 110 Messier objects, from OpenNGC (real RA/Dec, no "
              "coordinate guessing). Downloaded once and cached on disk — "
              "later runs use the cached copy, no internet needed.",
        "zh": "110 個 Messier 天體，資料來自 OpenNGC（真實的赤經／赤緯座"
              "標，不是猜測出來的）。只會下載一次並快取在本機——之後執行"
              "會直接使用快取，不需要網路。"},
    "ann_cat_ngc": {"en": "NGC", "zh": "NGC"},
    "ann_cat_ngc_tooltip": {
        "en": "New General Catalogue — ~8,000 NGC objects, from the same "
              "cached OpenNGC data as Messier above.",
        "zh": "New General Catalogue——約 8,000 個 NGC 天體，資料來源與上"
              "方 Messier 相同，都是快取的 OpenNGC 資料。"},
    "ann_cat_ic": {"en": "IC", "zh": "IC"},
    "ann_cat_ic_tooltip": {
        "en": "Index Catalogue — ~5,000 IC objects, from the same cached "
              "OpenNGC data as Messier above.",
        "zh": "Index Catalogue——約 5,000 個 IC 天體，資料來源與上方 "
              "Messier 相同，都是快取的 OpenNGC 資料。"},
    "ann_cat_sh2": {"en": "Sharpless (Sh2)", "zh": "Sharpless（Sh2）"},
    "ann_cat_sh2_tooltip": {
        "en": "Sharpless catalogue of HII regions/emission nebulae, queried "
              "live from VizieR (catalogue VII/20) for the current field. "
              "Needs internet on every run — off by default for that "
              "reason.",
        "zh": "Sharpless 電離氫區／發射星雲目錄，針對目前視野即時從 "
              "VizieR（目錄 VII/20）查詢。每次執行都需要網路——因此預設"
              "為關閉。"},
    "ann_cat_ldn": {"en": "Lynds Dark Nebulae", "zh": "Lynds 暗星雲"},
    "ann_cat_ldn_tooltip": {
        "en": "Lynds Catalogue of Dark Nebulae (LdN), queried live from "
              "VizieR (catalogue VII/7A) for the current field. Needs "
              "internet on every run — off by default for that reason.",
        "zh": "Lynds 暗星雲目錄（LdN），針對目前視野即時從 VizieR（目錄 "
              "VII/7A）查詢。每次執行都需要網路——因此預設為關閉。"},
    "ann_online": {
        "en": "All stars < mag limit (online)", "zh": "所有低於星等上限的星（線上）"},
    "ann_online_tooltip": {
        "en": "Siril's local star catalogue covers the field well already; "
              "this additionally runs Siril's own online conesearch against "
              "the VizieR Bright Star Catalogue (BSC) for every star below "
              "the star magnitude limit, for denser coverage. Needs "
              "internet.",
        "zh": "Siril 的本機星點目錄已能很好地涵蓋視野；此選項會額外執行 "
              "Siril 自己的線上 conesearch，向 VizieR 亮星目錄（BSC）查詢"
              "所有低於星等上限的星，以取得更密集的涵蓋範圍。需要網路。"},
    "ann_const": {"en": "Constellation lines", "zh": "星座連線"},
    "ann_const_tooltip": {
        "en": "Draws stick-figure lines between bright stars for whichever "
              "constellations are (at least partly) in the plate-solved "
              "field. Line topology is a widely used amateur/planetarium "
              "\"connect the dots\" set (from the open-source d3-celestial "
              "project), embedded and fully offline — the IAU only defines "
              "official constellation *boundaries*, not lines, so different "
              "atlases draw slightly different stick figures for the same "
              "constellation. Use \"Select constellations...\" below to "
              "leave some out.",
        "zh": "為（至少部分）落在已解算視野中的星座，在亮星之間繪製連"
              "線。連線的拓樸取自業餘／星象館常用的「連連看」資料集（來"
              "自開源的 d3-celestial 專案），完全內建、離線可用——IAU 只"
              "定義了星座的官方*邊界*，並未定義連線方式，所以不同星圖對"
              "同一星座畫出的連線可能略有不同。可用下方的「選擇星"
              "座…」排除部分星座。"},
    "ann_const_names": {
        "en": "Show constellation names", "zh": "顯示星座名稱"},
    "ann_const_names_tooltip": {
        "en": "Labels each drawn constellation with its name, centered over "
              "whichever part of its stick figure is inside the frame.",
        "zh": "為每個已繪製的星座標上名稱，置中顯示在其連線落在畫面內的"
              "部分上方。"},
    "ann_line_width_label": {"en": "Line width:", "zh": "線寬："},
    "ann_line_width_tooltip": {
        "en": "Thickness of the constellation lines, in pixels (scaled up "
              "automatically for high-resolution stacks).",
        "zh": "星座連線的粗細，單位為像素（高解析度疊圖會自動放大）。"},
    "ann_gap_label": {"en": "Gap (px):", "zh": "間隔（px）："},
    "ann_gap_tooltip": {
        "en": "Shortens each line segment by this many pixels from both "
              "ends, so lines don't touch the stars directly — 0 draws "
              "star-to-star with no gap.",
        "zh": "把每段連線兩端各縮短這麼多像素，讓線條不會直接碰到星點"
              "——0 則從星點畫到星點，沒有間隔。"},
    "ann_color_preset_label": {"en": "Color preset:", "zh": "顏色預設集："},
    "ann_color_preset_tooltip": {
        "en": "Quick-pick a matched line/name color scheme. Picking either "
              "color manually below switches this back to \"Custom\".",
        "zh": "快速選擇一組搭配好的連線／名稱顏色組合。手動挑選下方任一"
              "顏色時，會自動切回「自訂」。"},
    "ann_line_color_btn": {"en": "Line color...", "zh": "連線顏色…"},
    "ann_line_color_tooltip": {
        "en": "Pick a custom color for the constellation lines themselves.",
        "zh": "為星座連線本身選擇自訂顏色。"},
    "ann_name_color_btn": {"en": "Name color...", "zh": "名稱顏色…"},
    "ann_name_color_tooltip": {
        "en": "Pick a custom color for the constellation name labels — "
              "independent of the line color above.",
        "zh": "為星座名稱標籤選擇自訂顏色——與上方的連線顏色互不影響。"},
    "ann_select_const_btn": {
        "en": "🌌  Select constellations...", "zh": "🌌  選擇星座…"},
    "ann_select_const_tooltip": {
        "en": "Choose which of the 88 constellations get stick-figure lines "
              "drawn, if \"Constellation lines\" above is checked. Applies "
              "the next time the Annotate stage runs.",
        "zh": "若已勾選上方的「星座連線」，可在此選擇 88 個星座中要繪製"
              "哪些連線。此設定會在「標記」步驟下次執行時套用。"},
    "ann_step2_title": {"en": "② Annotation style", "zh": "② 標記樣式"},
    "ann_label_size_label": {"en": "Label size:", "zh": "標籤大小："},
    "ann_marker_style_label": {"en": "Marker style:", "zh": "標記樣式："},
    "ann_marker_style_tooltip": {
        "en": "How each star/DSO marker is drawn. \"Open Cross\" is a "
              "reticle-style cross with a gap in the middle so it doesn't "
              "cover the object itself — its gap and arm length scale with "
              "the marker's size and are adjustable below. This panel "
              "updates immediately as you change the style.",
        "zh": "每個星點／深空天體標記的繪製方式。「Open Cross」是一種中"
              "間有間隔的十字準星樣式，不會蓋住物件本身——其間隔與臂長會"
              "隨標記大小縮放，並可在下方調整。更改樣式時本面板會立即"
              "更新。"},
    "ann_label_distance_label": {
        "en": "Label distance (× radius):", "zh": "標籤距離（× 半徑）："},
    "ann_label_distance_tooltip": {
        "en": "Extra breathing room between the label text and the marker "
              "center, as a multiple of the marker's own radius — added on "
              "top of every label's normal placement distance (which, for "
              "Open Cross style, already includes the arm length below, "
              "plus a small fixed margin so text never touches the "
              "marker). Positive values push the label further out — "
              "useful to clear a stretched, multi-line label so it "
              "doesn't crowd Open Cross's arms; negative values pull it "
              "in closer than the normal default, down to a minimum where "
              "it would start overlapping the marker. Applies to every "
              "marker style, not just Open Cross.",
        "zh": "標籤文字與標記中心之間額外保留的空間，以標記自身半徑的倍"
              "數表示——會加在每個標籤原本的擺放距離之上（對 Open Cross "
              "樣式而言，原本的距離已包含下方的臂長，再加上一小段固定邊"
              "距，避免文字碰到標記）。正值會把標籤推得更遠——適合用來"
              "為較長、多行的標籤讓出空間，避免擠到 Open Cross 的臂；負"
              "值則會把標籤拉得比預設更近，最小可拉到快要與標記重疊為"
              "止。對所有標記樣式都適用，不只是 Open Cross。"},
    "ann_circle_style_title": {"en": "Circle style", "zh": "圓圈樣式"},
    "ann_auto_thickness": {"en": "Auto thickness", "zh": "自動粗細"},
    "ann_circle_auto_thickness_tooltip": {
        "en": "Scales the circle's stroke width with the image resolution "
              "and label size, same as before this option existed. Uncheck "
              "to set a fixed pixel thickness instead.",
        "zh": "讓圓圈的線寬隨影像解析度與標籤大小縮放，與新增此選項之前"
              "的行為相同。取消勾選可改為設定固定的像素粗細。"},
    "ann_thickness_px_label": {"en": "Thickness (px):", "zh": "粗細（px）："},
    "ann_custom_color_override": {
        "en": "Custom color override", "zh": "自訂顏色覆寫"},
    "ann_circle_custom_color_tooltip": {
        "en": "Off (default): each catalogue keeps its own color, matching "
              "the swatches above. On: every circle uses the single color "
              "picked below instead — labels keep their per-catalogue color "
              "either way.",
        "zh": "關閉（預設）：每個目錄維持自己的顏色，與上方色塊相符。開"
              "啟：所有圓圈改用下方選擇的單一顏色——不論哪種情況，標籤都"
              "會維持各自目錄的顏色。"},
    "ann_circle_color_btn": {"en": "Circle color...", "zh": "圓圈顏色…"},
    "ann_cross_style_title": {"en": "Open Cross style", "zh": "Open Cross 樣式"},
    "ann_cross_custom_color_tooltip": {
        "en": "Same idea as the circle's custom color above, independent of "
              "it — you can have a custom cross color with per-catalogue "
              "circle colors, or vice versa, or both/neither.",
        "zh": "與上方圓圈的自訂顏色概念相同，但彼此獨立——你可以讓十字使"
              "用自訂顏色、圓圈維持各目錄顏色，或反過來，或兩者都自訂／"
              "都不自訂。"},
    "ann_cross_color_btn": {"en": "Cross color...", "zh": "十字顏色…"},
    "ann_cross_gap_label": {"en": "Gap (× radius):", "zh": "間隔（× 半徑）："},
    "ann_cross_gap_tooltip": {
        "en": "How far each arm starts from the object's center, as a "
              "multiple of the marker's own radius — so it scales with the "
              "object's apparent size instead of being a fixed pixel gap.",
        "zh": "每個臂從物件中心起算的起始距離，以標記自身半徑的倍數表"
              "示——會隨物件的視面積縮放，而不是固定的像素間隔。"},
    "ann_cross_arm_label": {
        "en": "Arm length (× radius):", "zh": "臂長（× 半徑）："},
    "ann_cross_arm_tooltip": {
        "en": "Length of each of the 4 arm strokes, as a multiple of the "
              "marker's radius — also scales with object size.",
        "zh": "4 個臂各自的長度，以標記半徑的倍數表示——同樣會隨物件大小"
              "縮放。"},
    "ann_label_position_label": {"en": "Label position:", "zh": "標籤位置："},
    "ann_label_position_tooltip": {
        "en": "The open cross leaves its 4 diagonal corners clear of arms — "
              "pick one to always place the name there, or leave on Auto to "
              "let the same overlap-avoiding placement used for Circle "
              "style pick the best free spot (preferring this corner when "
              "you’ve chosen one).",
        "zh": "Open Cross 的 4 個對角保持淨空、沒有臂——可指定其中一個角"
              "固定放置名稱，或維持「自動」讓系統使用與圓圈樣式相同的避"
              "免重疊邏輯選出最佳空位（若已指定某個角，會優先使用該"
              "角）。"},
    "ann_label_detail_title": {"en": "Label detail", "zh": "標籤細節"},
    "ann_label_detail_info": {
        "en": "Adds extra lines under each object's name, drawn stacked in "
              "the same direction as the name itself, aligned to whichever "
              "side of the marker the label sits on. The built-in fields "
              "below only appear for Messier/NGC/IC objects (OpenNGC "
              "carries this data; stars/Sharpless/LdN don't) and only when "
              "that particular object actually has the field. Open Cross "
              "style's arm on the label's side (up or down) stretches "
              "automatically to reach a taller, multi-line label.",
        "zh": "在每個物件名稱下方加上額外的文字行，與名稱本身同方向堆"
              "疊，並對齊標記所在的那一側。下方的內建欄位只會出現在 "
              "Messier／NGC／IC 天體上（因為只有 OpenNGC 提供這些資料；"
              "星點／Sharpless／LdN 沒有），而且只在該物件確實擁有該欄"
              "位時才顯示。Open Cross 樣式在標籤那一側（上或下）的臂會"
              "自動伸長，以容納較高、多行的標籤。"},
    "ann_detail_type": {"en": "Object type", "zh": "物件類型"},
    "ann_detail_type_tooltip": {
        "en": "e.g. \"Galaxy\", \"Open cluster\", \"Planetary nebula\".",
        "zh": "例如「星系」、「疏散星團」、「行星狀星雲」。"},
    "ann_detail_mag": {"en": "Magnitude", "zh": "星等"},
    "ann_detail_mag_tooltip": {
        "en": "OpenNGC's V-Mag, falling back to B-Mag when V-Mag is "
              "missing.",
        "zh": "OpenNGC 的 V 星等，若缺少則改用 B 星等。"},
    "ann_detail_const": {"en": "Constellation", "zh": "所在星座"},
    "ann_detail_size": {"en": "Apparent size", "zh": "視面積"},
    "ann_detail_size_tooltip": {
        "en": "OpenNGC's MajAx (apparent major axis), in arcminutes — the "
              "same value already used to size the marker itself.",
        "zh": "OpenNGC 的 MajAx（視長軸），單位為角分——與用來決定標記大"
              "小的數值相同。"},
    "ann_custom_lines_label": {
        "en": "Custom lines (added to every label, in this order — type "
              "one label line per row of text):",
        "zh": "自訂行（會依此順序加到每個標籤上——每行文字對應一行標"
              "籤）："},
    "ann_custom_lines_placeholder": {
        "en": "One label line per row, e.g.:\nSession 1\nBortle 4",
        "zh": "每行文字對應一行標籤，例如：\n第一夜\n波特爾 4 級"},
    "ann_custom_lines_tooltip": {
        "en": "Freeform text appended under every object's name (and any "
              "built-in fields above) — the same text for every object, "
              "e.g. a session date or your own note. Each row of text you "
              "type is its own label line; blank rows are skipped.",
        "zh": "附加在每個物件名稱（以及上方任何已啟用欄位）下方的自由文"
              "字——每個物件都會使用相同文字，例如拍攝日期或你自己的備"
              "註。每一行輸入的文字都會成為獨立的一行標籤；空白行會被略"
              "過。"},
    "ann_show_overlay": {
        "en": "Show annotation overlay", "zh": "顯示標記疊層"},
    "ann_show_overlay_tooltip": {
        "en": "Uncheck to hide the markers/labels — running the stage will then "
              "just show the plain image (useful if you want to keep the stage "
              "in the pipeline but not clutter the preview/export with labels).",
        "zh": "取消勾選可隱藏標記／標籤——執行此步驟時只會顯示未加註的原"
              "始影像（適合想保留此步驟在流程中、但不想讓預覽／匯出畫面"
              "被標籤佔滿的情況）。"},
    "ann_bake": {
        "en": "Bake into image (for Watermark & later stages)",
        "zh": "烘焙進影像（供浮水印及後續步驟使用）"},
    "ann_bake_tooltip": {
        "en": "By default, annotation markers/labels only appear in the "
              "exported JPG/PNG and this stage's own before/after preview — "
              "the actual image handed to Siril (and any later stage, "
              "including Watermark) stays unmarked, so \"Remove all\" and "
              "re-running this stage are always non-destructive. Check this "
              "to also bake the markers/labels into that working image "
              "itself, so Watermark (or anything else run after Annotate) "
              "shows them too. Undo still restores the pre-annotation image "
              "either way.",
        "zh": "預設情況下，標記／標籤只會出現在匯出的 JPG／PNG 以及此步"
              "驟自己的前／後預覽中——實際交給 Siril（以及浮水印等任何後"
              "續步驟）的影像維持不變，所以「全部移除」以及重新執行此步"
              "驟永遠不會造成破壞。勾選此選項可將標記／標籤也烘焙進工作"
              "用影像本身，讓浮水印（或標記之後執行的任何步驟）也能看到"
              "它們。不論哪種情況，「復原」都能還原成標記前的影像。"},
    "ann_select_objects_btn": {
        "en": "Select objects...", "zh": "選擇物件…"},
    "ann_select_objects_tooltip": {
        "en": "Pick which of the labeled objects stay visible — unchecking "
              "one removes it from the preview and export immediately, no "
              "need to re-run the stage.",
        "zh": "選擇已標記的物件中，哪些要保持顯示——取消勾選某個物件會立"
              "即將它從預覽與匯出中移除，不需要重新執行此步驟。"},
    "ann_pick_object_btn": {
        "en": "Pick object on image...", "zh": "在影像上挑選物件…"},
    "ann_pick_object_tooltip": {
        "en": "Click this, then click anywhere on the preview image to add "
              "a custom object right there — its RA/Dec (from the same "
              "plate-solve WCS the stage already used) becomes its default "
              "name, styled with the Annotation style panel's current "
              "settings. Stays armed for multiple picks in a row; click "
              "this button again or press Esc to stop. Rename it, change "
              "its style, or remove it afterward via \"Select objects...\" "
              "🎨 editor, same as any catalogue object.",
        "zh": "點擊此按鈕後，再點擊預覽影像上的任何位置，即可在該處新增"
              "一個自訂物件——它的赤經／赤緯（取自此步驟已使用的天球解算 "
              "WCS）會成為預設名稱，並套用標記樣式面板目前的設定。此模式"
              "會持續啟用，可連續挑選多個；再次點擊此按鈕或按 Esc 可停"
              "止。之後可透過「選擇物件…」的 🎨 編輯器為它重新命名、更改"
              "樣式或移除，與任何目錄物件相同。"},
    "ann_update_preview_btn": {
        "en": "Update preview", "zh": "更新預覽"},
    "ann_update_preview_tooltip": {
        "en": "Re-renders every currently shown object using the "
              "Annotation style panel's *current* settings — marker style, "
              "colors, thickness, cross geometry, label detail lines — "
              "without re-querying any catalogue or re-running plate "
              "solving, so it's much faster than Run when you're just "
              "iterating on how things look. Resets every object to the "
              "panel defaults, so any per-object 🎨 overrides are "
              "discarded — re-open \"Select objects...\" afterward to "
              "reapply them if you still want them. Doesn't affect "
              "constellation lines (uncheck \"Constellation lines\" and "
              "re-run to remove those).",
        "zh": "使用標記樣式面板*目前*的設定——標記樣式、顏色、粗細、十字"
              "幾何、標籤細節行——重新繪製目前顯示的每個物件，不需要重新"
              "查詢任何目錄或重新進行天球解算，所以比「執行」快得多，適"
              "合單純調整外觀時使用。會把每個物件重設為面板預設值，因此"
              "任何個別物件的 🎨 覆寫都會被捨棄——之後可重新開啟「選擇物"
              "件…」重新套用（如果還需要的話）。不影響星座連線（取消勾"
              "選「星座連線」並重新執行才能移除）。"},
    "ann_remove_all_btn": {"en": "Remove all", "zh": "全部移除"},
    "ann_remove_all_tooltip": {
        "en": "Hide every labeled object at once — one click, no need to "
              "open \"Select objects to show...\" and uncheck them "
              "individually. Non-destructive, same as unchecking every "
              "object there: the underlying FITS image is never touched, "
              "and re-running the stage brings the labels back. Doesn't "
              "affect constellation lines — uncheck \"Constellation lines\" "
              "and re-run to remove those.",
        "zh": "一次隱藏所有已標記的物件——只需一鍵，不需要開啟「選擇要顯"
              "示的物件…」逐一取消勾選。此操作不會造成破壞，效果與在該處"
              "逐一取消勾選相同：底層 FITS 影像永遠不會被更動，重新執行"
              "此步驟就能讓標籤恢復。不影響星座連線——取消勾選「星座連"
              "線」並重新執行才能移除。"},
    "ann_save_image_btn": {"en": "Save image...", "zh": "儲存影像…"},
    "ann_save_image_tooltip": {
        "en": "Export the last annotated result as JPEG or PNG, wherever "
              "you choose.",
        "zh": "把最近一次的標記結果匯出成 JPEG 或 PNG，儲存到你選擇的位"
              "置。"},
    "ann_import_btn": {
        "en": "Import annotation details...", "zh": "匯入標記詳細資料…"},
    "ann_import_tooltip": {
        "en": "Load a previously saved annotated_*.json (auto-saved next "
              "to the JPG every time this stage actually runs — see the "
              "Run button above; \"Update preview\" doesn't write a new "
              "one, but \"Save annotation details...\" below does, on "
              "demand) and redraw exactly those objects onto the current "
              "un-annotated base canvas — no catalogue queries or plate "
              "solving needed. Meant for re-applying a saved annotation "
              "set to the same image it came from; a warning appears if "
              "the file's image size doesn't match the current one, since "
              "every position would then be off.",
        "zh": "載入先前儲存的 annotated_*.json（每次此步驟實際執行時都會"
              "自動儲存在 JPG 旁——見上方的「執行」按鈕；「更新預覽」不會"
              "產生新檔案，但下方的「儲存標記詳細資料…」可依需要隨時儲"
              "存），並把其中的物件精確地重繪到目前未加註的基底畫布上"
              "——不需要查詢任何目錄或重新進行天球解算。適合把已儲存的標"
              "記集合重新套用到它原本產生的同一張影像上；若檔案的影像尺"
              "寸與目前不符會顯示警告，因為所有位置屆時都會偏移。"},
    "ann_save_json_btn": {
        "en": "Save annotation details...", "zh": "儲存標記詳細資料…"},
    "ann_save_json_tooltip": {
        "en": "Write the objects currently shown — including any per-object "
              "🎨 style edits made via \"Select objects...\" — straight to a "
              "JSON file now, without re-running the stage. The auto-saved "
              "JSON from the last Run doesn't include those edits, since a "
              "run always rebuilds its object list from the catalogues; "
              "this is the only way to capture them.",
        "zh": "把目前顯示的物件——包括透過「選擇物件…」做的任何個別 🎨 樣"
              "式編輯——直接寫入 JSON 檔案，不需要重新執行此步驟。上次"
              "「執行」自動儲存的 JSON 不包含這些編輯，因為每次執行都會"
              "從目錄重新建立物件清單；這是唯一能保留這些編輯的方式。"},
    "ann_pick_btn_tooltip": {
        "en": "Click this, then click anywhere on the preview image to add "
              "a custom object right there — its RA/Dec (from the same "
              "plate-solve WCS the stage already used) becomes its default "
              "name, styled with the Annotation style panel's current "
              "settings. Stays armed for multiple picks in a row; click "
              "this button again or press Esc to stop. Rename it, change "
              "its style, or remove it afterward via \"Select objects...\" "
              "🎨 editor, same as any catalogue object.",
        "zh": "點擊此按鈕後，再點擊預覽影像上的任何位置，即可在該處新增"
              "一個自訂物件——它的赤經／赤緯（取自此步驟已使用的天球解算 "
              "WCS）會成為預設名稱，並套用標記樣式面板目前的設定。此模式"
              "會持續啟用，可連續挑選多個；再次點擊此按鈕或按 Esc 可停"
              "止。之後可透過「選擇物件…」的 🎨 編輯器為它重新命名、更改"
              "樣式或移除，與任何目錄物件相同。"},
    "ann_pick_hint_armed": {
        "en": "Pick mode armed — click a point on the preview image to "
              "add an object there. Click the button again or press "
              "Esc to stop.",
        "zh": "已啟用挑選模式——點擊預覽影像上的任一點即可在該處新增物"
              "件。再次點擊按鈕或按 Esc 可停止。"},

    "ann_progress_reading_solution": {
        "en": "Annotate: reading plate-solve solution...",
        "zh": "標記：正在讀取天球解算結果..."},
    "ann_progress_local_stars": {
        "en": "Annotate: querying Siril's local star catalogue...",
        "zh": "標記：正在查詢 Siril 本機星點目錄..."},
    "ann_progress_field_coverage": {
        "en": "Annotate: computing field coverage...",
        "zh": "標記：正在計算視野範圍..."},
    "ann_progress_openngc": {
        "en": "Annotate: fetching Messier/NGC/IC (OpenNGC)...",
        "zh": "標記：正在取得 Messier／NGC／IC（OpenNGC）..."},
    "ann_progress_sh2": {
        "en": "Annotate: querying Sharpless catalogue (VizieR)...",
        "zh": "標記：正在查詢 Sharpless 目錄（VizieR）..."},
    "ann_progress_ldn": {
        "en": "Annotate: querying Lynds Dark Nebulae (VizieR)...",
        "zh": "標記：正在查詢 Lynds 暗星雲（VizieR）..."},
    "ann_progress_online_bsc": {
        "en": "Annotate: querying Siril's online Bright Star "
              "Catalogue (VizieR)...",
        "zh": "標記：正在查詢 Siril 線上亮星目錄（VizieR）..."},
    "ann_progress_drawing_labels": {
        "en": "Annotate: drawing labels...", "zh": "標記：正在繪製標籤..."},
    "ann_progress_const_lines": {
        "en": "Annotate: drawing constellation lines...",
        "zh": "標記：正在繪製星座連線..."},
    "ann_progress_done": {
        "en": "Annotate: done — {drawn} objects labeled{suffix}.",
        "zh": "標記：完成——已標記 {drawn} 個物件{suffix}。"},
    "ann_const_suffix": {
        "en": ", {n} constellation(s)", "zh": "，{n} 個星座"},
    "ann_progress_overlay_hidden": {
        "en": "Annotate: overlay hidden — showing plain image.",
        "zh": "標記：已隱藏疊層——僅顯示原始影像。"},

    "ann_error_no_platesolve": {
        "en": "No valid plate-solve solution in the image header. "
              "Run plate solving (stage 1 with SPCC, or Siril's "
              "'platesolve') before annotating.",
        "zh": "影像標頭中沒有有效的天球解算結果。請先執行天球解算（步驟 "
              "1 開啟 SPCC，或使用 Siril 的「platesolve」）再進行標記。"},
    "ann_error_unsupported_format": {
        "en": "Unsupported format '{ext}' — choose .jpg or .png.",
        "zh": "不支援的格式「{ext}」——請選擇 .jpg 或 .png。"},

    "ann_no_image_title": {"en": "No annotated image", "zh": "尚無標記影像"},
    "ann_no_image_body": {
        "en": "Run the Annotate stage at least once first.",
        "zh": "請先至少執行一次「標記」步驟。"},
    "ann_nothing_to_remove_title": {
        "en": "Nothing to remove", "zh": "沒有可移除的內容"},
    "ann_nothing_to_update_title": {
        "en": "Nothing to update", "zh": "沒有可更新的內容"},
    "ann_nothing_to_select_title": {
        "en": "Nothing to select", "zh": "沒有可選擇的內容"},
    "ann_nothing_labeled_body": {
        "en": "The last Annotate run didn't label any objects.",
        "zh": "上一次「標記」執行沒有標記任何物件。"},
    "ann_import_dialog_title": {
        "en": "Import annotation details", "zh": "匯入標記詳細資料"},
    "ann_import_failed_title": {"en": "Import failed", "zh": "匯入失敗"},
    "ann_import_failed_body": {
        "en": "Couldn't read \"{name}\": {e}",
        "zh": "無法讀取「{name}」：{e}"},
    "ann_size_mismatch_title": {
        "en": "Image size mismatch", "zh": "影像尺寸不符"},
    "ann_size_mismatch_body": {
        "en": "This file was saved for a {jw}×{jh} image, "
              "but the current one is {w}×{h} — imported object "
              "positions will likely be wrong. Importing anyway.",
        "zh": "此檔案是針對 {jw}×{jh} 的影像儲存的，但目前的影像是 "
              "{w}×{h}——匯入的物件位置很可能會不正確。仍會繼續匯入。"},
    "ann_pick_failed_title": {"en": "Pick object failed", "zh": "挑選物件失敗"},
    "ann_pick_failed_body": {
        "en": "Couldn't convert that point to RA/Dec: {e}",
        "zh": "無法把該點轉換成赤經／赤緯：{e}"},
    "ann_nothing_to_save_title": {"en": "Nothing to save", "zh": "沒有可儲存的內容"},
    "ann_nothing_to_save_body": {
        "en": "Run the Annotate stage at least once first — there are "
              "no labeled objects to save yet.",
        "zh": "請先至少執行一次「標記」步驟——目前還沒有已標記的物件可"
              "儲存。"},
    "ann_save_failed_title": {"en": "Save failed", "zh": "儲存失敗"},

    "ann_const_dialog_title": {
        "en": "Select Constellations", "zh": "選擇星座"},
    "ann_const_dialog_info": {
        "en": "Uncheck constellations to leave their lines out "
              "the next time Annotate runs:",
        "zh": "取消勾選的星座，將在「標記」下次執行時不繪製連線："},
    "ann_select_all_btn": {"en": "Select All", "zh": "全選"},
    "ann_deselect_all_btn": {"en": "Deselect All", "zh": "全部取消"},
    "ann_const_status": {
        "en": "Constellations: {n} of {total} selected — re-run "
              "Annotate to apply.",
        "zh": "星座：已選擇 {total} 個中的 {n} 個——重新執行「標記」以套"
              "用。"},

    "ann_style_dialog_title": {
        "en": "Object Style — {label}", "zh": "物件樣式 — {label}"},
    "ann_style_dialog_info": {
        "en": "Overrides just this object — the Annotation style "
              "panel's settings are untouched and still apply to "
              "every other object. \"Update\" previews changes "
              "immediately without closing this dialog.",
        "zh": "只覆寫這個物件——標記樣式面板的設定不受影響，仍會套用到其"
              "他所有物件。「更新」會立即預覽變更，不會關閉此對話框。"},
    "ann_marker_color_btn": {"en": "Marker color...", "zh": "標記顏色…"},
    "ann_marker_color_tooltip": {
        "en": "Color of the Circle marker (used when the marker style "
              "above is Circle or Circle + Open Cross).",
        "zh": "圓圈標記的顏色（當上方的標記樣式為「Circle」或「Circle + "
              "Open Cross」時使用）。"},
    "ann_marker_thickness_label": {
        "en": "Marker thickness (px):", "zh": "標記粗細（px）："},
    "ann_text_color_btn": {"en": "Text color...", "zh": "文字顏色…"},
    "ann_text_color_tooltip": {
        "en": "Color of the label text itself, independent of the marker "
              "color(s).",
        "zh": "標籤文字本身的顏色，與標記顏色互不影響。"},
    "ann_cross_thickness_label": {
        "en": "Cross thickness (px):", "zh": "十字粗細（px）："},
    "ann_cross_gap_dialog_label": {
        "en": "Cross gap (× radius):", "zh": "十字間隔（× 半徑）："},
    "ann_cross_arm_dialog_label": {
        "en": "Cross arm (× radius):", "zh": "十字臂長（× 半徑）："},
    "ann_label_distance_dialog_tooltip": {
        "en": "How far the label text sits from the marker, as a "
              "multiple of the marker's own radius, on top of the normal "
              "placement distance — negative values pull the label in "
              "closer, positive values push it further out. Applies "
              "regardless of marker style.",
        "zh": "標籤文字與標記之間的距離，以標記自身半徑的倍數表示，會加"
              "在原本的擺放距離之上——負值會把標籤拉得更近，正值會推得更"
              "遠。不論標記樣式為何都適用。"},
    "ann_label_lines_label": {
        "en": "Label lines (one per row of text):",
        "zh": "標籤行（每行文字對應一行）："},
    "ann_label_lines_tooltip": {
        "en": "The object's name plus any detail/custom lines, top to "
              "bottom, one label line per row of text — type, delete, or "
              "reorder rows freely (this box has its own Ctrl+Z undo for "
              "text edits). This doesn't affect any other object.",
        "zh": "物件名稱加上任何細節／自訂行，由上到下，每行文字對應一行"
              "標籤——可自由輸入、刪除或調整順序（此欄位有自己的 Ctrl+Z "
              "文字復原功能）。不會影響其他任何物件。"},
    "ann_undo_btn": {"en": "↶  Undo", "zh": "↶  復原"},
    "ann_undo_tooltip": {
        "en": "Steps back one field change at a time within this dialog "
              "(marker style, colors, thickness, cross geometry, or label "
              "lines) — independent of whether you've clicked Update.",
        "zh": "在此對話框中，每次退回一項欄位變更（標記樣式、顏色、粗"
              "細、十字幾何或標籤行）——不論是否點過「更新」都可使用。"},
    "ann_reset_default_btn": {
        "en": "↺  Reset to panel default", "zh": "↺  重設為面板預設值"},
    "ann_reset_default_tooltip": {
        "en": "Discards every override above and recomputes this object's "
              "style and label lines exactly as the Annotation style panel "
              "would produce them right now. Counts as a single undoable "
              "step.",
        "zh": "捨棄上方所有覆寫設定，並依標記樣式面板目前的設定重新計算"
              "此物件的樣式與標籤行。此動作算作單一一次可復原的步驟。"},
    "ann_update_btn": {"en": "🔄  Update", "zh": "🔄  更新"},
    "ann_update_tooltip": {
        "en": "Applies these settings to the preview immediately, without "
              "closing this dialog — keep adjusting and clicking Update to "
              "see each change.",
        "zh": "立即把這些設定套用到預覽，不會關閉此對話框——可持續調整並"
              "點擊「更新」以查看每次變更的結果。"},
    "ann_circle_marker_color_title": {
        "en": "Circle marker color", "zh": "圓圈標記顏色"},
    "ann_cross_marker_color_title": {
        "en": "Cross marker color", "zh": "十字標記顏色"},
    "ann_const_line_color_title": {
        "en": "Constellation line color", "zh": "星座連線顏色"},
    "ann_const_name_color_title": {
        "en": "Constellation name color", "zh": "星座名稱顏色"},

    "ann_selector_dialog_title": {
        "en": "Select Objects to Show", "zh": "選擇要顯示的物件"},
    "ann_selector_dialog_info": {
        "en": "Uncheck objects to hide them from the "
              "annotated image (updates live). Click 🎨 to "
              "give one object its own marker style, color, "
              "or label content.",
        "zh": "取消勾選物件可從標記影像中隱藏它們（即時更新）。點擊 🎨 "
              "可為某個物件設定專屬的標記樣式、顏色或標籤內容。"},
    "ann_style_btn_tooltip": {
        "en": "Customize this object's marker style, colors, and label "
              "lines — independent of the Annotation style panel's "
              "defaults.",
        "zh": "自訂這個物件的標記樣式、顏色與標籤行——與標記樣式面板的預"
              "設值互不影響。"},
    "ann_deselect_all_hide_btn": {
        "en": "Deselect All (hide all)", "zh": "全部取消（全部隱藏）"},
    "ann_selector_canceled_status": {
        "en": "Select objects: canceled, no change.",
        "zh": "選擇物件：已取消，沒有變更。"},
    "ann_selector_hid_status": {
        "en": "Hid {n} object(s) ({shown} shown). Use \"Save annotated "
              "image...\" to export.",
        "zh": "已隱藏 {n} 個物件（顯示 {shown} 個）。可使用「儲存標記影"
              "像…」匯出。"},

    "ann_save_json_dialog_title": {
        "en": "Save annotation details", "zh": "儲存標記詳細資料"},
    "ann_save_image_dialog_title": {
        "en": "Save annotated image", "zh": "儲存標記影像"},

    "ann_removed_all_status": {
        "en": "All annotations removed.", "zh": "已移除所有標記。"},
    "ann_preview_updated_status": {
        "en": "Annotate: preview updated from the current panel settings.",
        "zh": "標記：已依目前的面板設定更新預覽。"},
    "ann_pick_stopped_status": {
        "en": "Pick object: stopped.", "zh": "挑選物件：已停止。"},
    "ann_pick_added_status": {
        "en": "Pick object: added \"{label}\" — rename or restyle it via "
              "\"Select objects...\" 🎨.",
        "zh": "挑選物件：已新增「{label}」——可透過「選擇物件…」的 🎨 重新"
              "命名或調整樣式。"},
    "ann_details_saved_status": {
        "en": "Annotation details saved: {name}",
        "zh": "標記詳細資料已儲存：{name}"},
    "ann_image_saved_status": {
        "en": "Annotated image saved: {name}",
        "zh": "已儲存標記影像：{name}"},
    "ann_imported_status": {
        "en": "Imported {n} object(s) from {name}.",
        "zh": "已從 {name} 匯入 {n} 個物件。"},
}


def tr(lang, key):
    """Look up `key` in `lang` ("en" or "zh"). Falls back to English,
    then to the raw key, so a missing translation is visible rather
    than raising — important while stages are converted incrementally
    and most keys don't exist yet."""
    entry = STRINGS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get(DEFAULT_LANGUAGE) or key
