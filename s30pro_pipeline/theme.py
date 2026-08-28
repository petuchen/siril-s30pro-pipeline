"""Global Qt stylesheet — v2.0.0 ("Industry" wireframe theme, dark).

Replaces the rounded steel-blue theme of 1.x. Rules of the theme, in one
line: square corners, hairline borders, no surface fills except the one
solid accent button and the selected-row field. Every colour below is a
step of a single steel-blue ramp on a near-black ground; nothing else.

Read STYLE_GUIDE.md before adding a colour, a radius or a font size —
new UI is expected to compose from the tokens and object names here, not
to introduce its own.
"""

__all__ = ["STYLESHEET", "TOKENS", "BG0", "BG1", "BG2", "FIELD", "LINE",
           "LINE2", "ACCENT", "ACCENT_HI", "ACCENT_DIM", "TXT", "TXT2",
           "MUTED", "MUTED2", "OFF", "FONT_UI", "FONT_COND"]

# =============================================================================
#  TOKENS  — the whole palette. Nine greys, three accents. No other colour.
# =============================================================================

BG0 = "#0f1114"      # window ground, rail, footers
BG1 = "#14161a"      # panes
BG2 = "#1b1e24"      # raised chrome (title/status strips)
FIELD = "#1d2d3d"    # accent-900: the one tinted fill (selected row, tabs)
LINE = "#23272e"      # structural hairline (between panes, rows)
LINE2 = "#2b3038"     # control hairline (borders of inputs, frames)

ACCENT = "#94bce3"    # accent-400 — the accent on a dark ground
ACCENT_HI = "#b5d9fd"  # accent-300 — hover
ACCENT_DIM = "#2c455d"  # accent-800 — outline of ghost/secondary controls

TXT = "#e7e7ea"       # primary text
TXT2 = "#c8cdd4"      # control labels
MUTED = "#98989b"     # secondary text
MUTED2 = "#5d6570"    # captions, group headers
OFF = "#3f454e"       # disabled / off

# Barlow first, then the closest widely-installed condensed/neutral faces,
# so the window still looks intentional on a machine without Barlow.
FONT_UI = '"Barlow", "Inter", "Segoe UI", sans-serif'
FONT_COND = '"Barlow Condensed", "Barlow", "DejaVu Sans Condensed", sans-serif'

TOKENS = {k: v for k, v in list(globals().items()) if k.isupper()}

# Type scale (pt) — five sizes, no others.
PT_HERO = 15      # pane title
PT_LEAD = 11.5    # ribbon target name, primary button
PT_BODY = 9.5     # default
PT_SMALL = 9      # captions, row meta
PT_MICRO = 8      # group headers (always uppercase + letter-spaced)

STYLESHEET = f"""
/* ---------------------------------------------------------------- base */
QWidget {{ background-color: {BG1}; color: {TXT};
           font-family: {FONT_UI}; font-size: {PT_BODY}pt; }}
QMainWindow, QDialog {{ background-color: {BG0}; }}
QToolTip {{ background-color: {BG2}; color: {TXT}; border: 1px solid {LINE2};
            padding: 6px; font-size: {PT_SMALL}pt; }}

QLabel {{ background: transparent; color: {TXT2}; }}
QLabel#Hero {{ font-family: {FONT_COND}; font-size: {PT_HERO}pt;
               font-weight: 600; color: #ffffff; }}
QLabel#Lead {{ font-family: {FONT_COND}; font-size: {PT_LEAD}pt;
               font-weight: 600; color: #ffffff; }}
QLabel#GroupHead {{ font-family: {FONT_COND}; font-size: {PT_MICRO}pt;
                    font-weight: 600; letter-spacing: 2px; color: {MUTED2}; }}
QLabel#Kicker {{ font-family: {FONT_COND}; font-size: {PT_MICRO}pt;
                 font-weight: 600; letter-spacing: 2px; color: {ACCENT}; }}
QLabel#SubHeader {{ color: {MUTED}; font-size: {PT_SMALL}pt; }}
QLabel#Caption {{ color: {MUTED2}; font-size: {PT_SMALL}pt; }}
QLabel#StatusLabel {{ color: {ACCENT}; font-size: {PT_SMALL}pt; }}
QLabel#Mono {{ font-family: "SF Mono", "Consolas", monospace;
               font-size: {PT_SMALL}pt; color: {MUTED2}; }}

/* Kept for compatibility with 1.x stage code that still sets these. */
QLabel#Header {{ font-family: {FONT_COND}; font-size: {PT_HERO}pt;
                 font-weight: 600; color: #ffffff; }}
QLabel#StageTitle {{ font-family: {FONT_COND}; font-size: {PT_LEAD}pt;
                     font-weight: 600; color: #ffffff; }}
QLabel#StageBadge {{ color: {ACCENT}; font-family: {FONT_COND};
                     font-weight: 600; min-width: 18px; }}

/* -------------------------------------------------------------- frames */
/* Stage panels are line drawings, never filled cards. */
QGroupBox {{ background: transparent; border: 1px solid {LINE2};
             border-radius: 0; margin-top: 8px;
             padding: 14px 12px 12px 12px;
             font-family: {FONT_COND}; font-weight: 600;
             letter-spacing: 1px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 6px;
                    color: {ACCENT}; font-size: {PT_MICRO}pt; }}
/* The logical stage container: no chrome of its own, no visible checkbox —
   its enabled state is driven by the proxy checkbox in the pane header. */
QGroupBox#StagePanel {{ border: 0; margin: 0; padding: 0;
                        background: transparent; }}
QGroupBox#StagePanel::title {{ width: 0; height: 0; padding: 0; margin: 0; }}
QGroupBox#StagePanel::indicator {{ width: 0; height: 0; }}
QFrame#Hairline {{ background: {LINE}; border: 0; max-height: 1px; }}
QFrame#VRule {{ background: {LINE}; border: 0; max-width: 1px; }}

/* ------------------------------------------------------------- controls */
QCheckBox {{ spacing: 8px; background: transparent; color: {TXT2}; }}
QCheckBox::indicator {{ width: 14px; height: 14px; border: 1px solid {OFF};
                        border-radius: 0; background: transparent; }}
QCheckBox::indicator:hover {{ border-color: {ACCENT}; }}
QCheckBox::indicator:checked {{ background-color: {ACCENT};
                                border-color: {ACCENT}; }}

QComboBox, QDoubleSpinBox, QSpinBox, QLineEdit, QPlainTextEdit {{
    background: transparent; color: {TXT}; border: 1px solid {LINE2};
    border-radius: 0; padding: 5px 8px;
    selection-background-color: {FIELD}; }}
QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover, QLineEdit:hover,
QPlainTextEdit:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: 0; width: 18px; }}
QComboBox::down-arrow {{ width: 0; height: 0;
    border-left: 4px solid transparent; border-right: 4px solid transparent;
    border-top: 5px solid {MUTED2}; margin-right: 6px; }}
QComboBox QAbstractItemView {{ background-color: {BG2}; color: {TXT};
    selection-background-color: {FIELD}; border: 1px solid {LINE2};
    outline: 0; }}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    background: transparent; border: 0; width: 14px; }}

QSlider {{ min-height: 20px; background: transparent; }}
QSlider::groove:horizontal {{ background: {LINE}; height: 4px;
                              border-radius: 0; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; height: 4px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 3px; height: 14px;
                              margin: -5px 0; border-radius: 0; }}
QSlider::groove:horizontal:disabled {{ background: {LINE}; }}
QSlider::sub-page:horizontal:disabled {{ background: {OFF}; }}
QSlider::handle:horizontal:disabled {{ background: {OFF}; }}

/* -------------------------------------------------------------- buttons */
/* Default = secondary: outlined, transparent. */
QPushButton {{ background: transparent; color: {TXT2};
    border: 1px solid {LINE2}; border-radius: 0; padding: 7px 12px;
    font-family: {FONT_COND}; font-weight: 600; letter-spacing: 1px; }}
QPushButton:hover {{ border-color: {ACCENT}; color: #ffffff; }}
QPushButton:pressed {{ background: {FIELD}; }}
QPushButton:disabled {{ color: {OFF}; border-color: {LINE}; }}

/* The one solid object on the board. Lives in the rail footer (212px
   wide, minus margins) alongside Import/Export, so it's sized to that
   column rather than the old full pane-width primary button. */
QPushButton#RunAll {{ background-color: {ACCENT}; color: {BG0}; border: 0;
    font-size: {PT_SMALL}pt; letter-spacing: 1px; padding: 9px 10px; }}
QPushButton#RunAll:hover {{ background-color: {ACCENT_HI}; }}
QPushButton#RunAll:pressed {{ background-color: {ACCENT}; }}
QPushButton#RunAll:disabled {{ background-color: {LINE}; color: {OFF}; }}

/* Per-stage run: solid too, one size down — it is the pane's own primary. */
QPushButton#StageRun {{ background-color: {ACCENT}; color: {BG0}; border: 0;
                        padding: 9px 14px; }}
QPushButton#StageRun:hover {{ background-color: {ACCENT_HI}; }}
QPushButton#StageRun:disabled {{ background-color: {LINE}; color: {OFF}; }}

QPushButton#Ghost {{ border-color: {ACCENT_DIM}; color: {ACCENT};
                     padding: 6px 10px; font-size: {PT_SMALL}pt; }}
QPushButton#Ghost:hover {{ background: {FIELD}; color: #ffffff; }}
QPushButton#Link {{ border: 0; color: {ACCENT}; padding: 2px 4px;
                    font-size: {PT_SMALL}pt; letter-spacing: 1px; }}
QPushButton#Link:hover {{ color: {ACCENT_HI}; }}
/* 1.x names kept so un-migrated stage code still looks right. */
QPushButton#LoadCurrentBtn {{ border: 0; color: {ACCENT}; padding: 2px 4px;
                              font-size: {PT_SMALL}pt; }}
QPushButton#LoadCurrentBtn:hover {{ color: {ACCENT_HI}; }}
QPushButton#AutoButton {{ border-color: {ACCENT_DIM}; color: {ACCENT}; }}
QPushButton#AutoButton:hover {{ background: {FIELD}; color: #ffffff; }}
QPushButton#CollapseHeader {{ border: 0; color: {ACCENT}; text-align: left;
    padding: 4px 2px; font-size: {PT_SMALL}pt; letter-spacing: 1px; }}
QPushButton#CollapseHeader:hover {{ color: {ACCENT_HI}; }}
QPushButton#StageExpandBtn {{ border: 0; color: {ACCENT}; padding: 2px; }}

/* Segmented control: buttons in a checkable QButtonGroup, no gaps. */
QPushButton#Seg {{ border: 1px solid {LINE2}; color: {MUTED};
    padding: 7px 12px; font-family: {FONT_UI}; font-weight: 400;
    letter-spacing: 0; }}
QPushButton#Seg:hover {{ color: #ffffff; }}
QPushButton#Seg:checked {{ background-color: {ACCENT}; color: {BG0};
                           border-color: {ACCENT}; }}
/* 1.x preview A/B buttons use this name. */
QPushButton#ABBtn {{ border: 1px solid {LINE2}; color: {MUTED};
    padding: 6px 12px; font-family: {FONT_UI}; font-weight: 400;
    letter-spacing: 0; }}
QPushButton#ABBtn:hover {{ color: #ffffff; }}
QPushButton#ABBtn:checked {{ background-color: {ACCENT}; color: {BG0};
                             border-color: {ACCENT}; }}

QPushButton#StepTab {{ border: 0; border-bottom: 2px solid transparent;
    color: {MUTED}; padding: 10px 4px; font-size: {PT_SMALL}pt;
    letter-spacing: 1px; }}
QPushButton#StepTab:hover {{ color: #ffffff; }}
QPushButton#StepTab:checked {{ color: #ffffff; background: {FIELD};
                               border-bottom-color: {ACCENT}; }}

QToolButton#Overflow {{ background: transparent; color: {MUTED};
    border: 1px solid {LINE2}; border-radius: 0; padding: 6px 10px; }}
QToolButton#Overflow:hover {{ border-color: {ACCENT}; color: #ffffff; }}
QMenu {{ background: {BG2}; border: 1px solid {LINE2}; padding: 4px; }}
QMenu::item {{ padding: 6px 22px 6px 14px; color: {TXT2}; }}
QMenu::item:selected {{ background: {FIELD}; color: #ffffff; }}
QMenu::item:disabled {{ color: {OFF}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 4px 2px; }}

/* --------------------------------------------------------- shell chrome */
QWidget#Rail {{ background: {BG0}; border-right: 1px solid {LINE}; }}
QFrame#RailRow {{ background: transparent; border: 0;
                  border-left: 3px solid transparent; }}
QFrame#RailRow:hover {{ background: #16191e; }}
QFrame#RailRow[active="true"] {{ background: {FIELD};
                                 border-left: 3px solid {ACCENT}; }}
QLabel#RailNum {{ font-family: {FONT_COND}; font-size: {PT_SMALL}pt;
                  color: {MUTED2}; }}
QLabel#RailName {{ color: {MUTED}; }}
QLabel#RailName[state="active"] {{ color: #ffffff; }}
QLabel#RailName[state="done"] {{ color: {MUTED}; }}
QLabel#RailName[state="off"] {{ color: {MUTED2}; }}
QLabel#RailFlag {{ font-family: {FONT_COND}; font-size: {PT_MICRO}pt;
                   letter-spacing: 1px; color: {OFF}; }}
QLabel#RailFlag[state="done"] {{ color: {ACCENT}; }}
QLabel#RailFlag[state="active"] {{ color: {ACCENT}; }}

QWidget#Ribbon {{ background: {BG0}; border-bottom: 1px solid {LINE}; }}
QWidget#Pane {{ background: {BG1}; border-right: 1px solid {LINE}; }}
QWidget#PaneFooter {{ background: {BG0}; border-top: 1px solid {LINE}; }}
QWidget#Preview {{ background: {BG0}; }}
QWidget#PreviewToolbar {{ background: {BG0};
                          border-bottom: 1px solid {LINE}; }}
QFrame#ImageFrame {{ background: #0a0c11; border: 1px solid {LINE2};
                     border-radius: 0; }}
QWidget#ObjectList {{ background: {BG1}; border-left: 1px solid {LINE}; }}

QProgressBar {{ border: 0; border-radius: 0; background: {LINE};
    text-align: center; color: {TXT}; max-height: 4px;
    min-height: 4px; font-size: 1px; }}
QProgressBar::chunk {{ background-color: {ACCENT}; }}

QSplitter::handle {{ background: transparent; }}
QSplitter::handle:hover {{ background: {ACCENT_DIM}; }}

QScrollArea {{ border: 0; background: transparent; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {LINE2}; border-radius: 0;
                               min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {MUTED2}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ------------------------------------------------------------- disabled */
QLabel:disabled, QCheckBox:disabled {{ color: {OFF}; }}
QLabel#Hero:disabled, QLabel#StageTitle:disabled {{ color: {MUTED2}; }}
QCheckBox::indicator:disabled {{ border-color: {LINE}; background: transparent; }}
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled,
QLineEdit:disabled, QPlainTextEdit:disabled {{
    color: {OFF}; border-color: {LINE}; }}
"""
