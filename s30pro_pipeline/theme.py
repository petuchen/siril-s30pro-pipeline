"""Global Qt stylesheet (extracted from S30Pro_Pipeline.py)."""

__all__ = ["STYLESHEET"]

# =============================================================================
#  THEME
# =============================================================================

ACCENT = "#7aa2ff"
ACCENT_DARK = "#2e4a8f"
BG0 = "#14161a"
BG1 = "#1b1e24"
BG2 = "#232730"
TXT = "#d7dce4"

STYLESHEET = f"""
QWidget {{ background-color: {BG1}; color: {TXT}; font-size: 9.5pt;
           font-family: sans-serif; }}
QMainWindow {{ background-color: {BG0}; }}
QToolTip {{ background-color: {BG2}; color: #ffffff; border: 1px solid {ACCENT}; padding: 4px; }}

QGroupBox {{ background-color: {BG2}; border: 1px solid #30353f; border-radius: 10px;
             margin-top: 10px; padding: 14px 8px 8px 8px; font-weight: bold; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 12px; padding: 0 6px; color: {ACCENT}; }}

QLabel {{ background: transparent; color: #c4cad4; }}
QLabel#StageTitle {{ color: #ffffff; font-size: 11pt; font-weight: bold; }}
QLabel#StageBadge {{ background-color: {ACCENT_DARK}; color: #ffffff; border-radius: 11px;
                     min-width: 22px; max-width: 22px; min-height: 22px; max-height: 22px;
                     font-weight: bold; }}
QLabel#Header {{ color: #ffffff; font-size: 15pt; font-weight: bold; }}
QLabel#SubHeader {{ color: #8b93a1; font-size: 9.5pt; }}
QLabel#StatusLabel {{ color: {ACCENT}; font-size: 9.5pt; }}

QCheckBox {{ spacing: 7px; background: transparent; }}
QCheckBox::indicator {{ width: 15px; height: 15px; border: 1px solid #4a5160;
                        border-radius: 4px; background: {BG1}; }}
QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}

QComboBox, QDoubleSpinBox, QSpinBox {{
    background-color: {BG1}; color: #ffffff; border: 1px solid #3a4150;
    border-radius: 6px; padding: 3px 5px; }}
QComboBox:hover, QDoubleSpinBox:hover, QSpinBox:hover {{ border-color: {ACCENT}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox::down-arrow {{ width: 0; height: 0; border-left: 4px solid transparent;
    border-right: 4px solid transparent; border-top: 6px solid #8892a3; margin-right: 6px; }}
QComboBox QAbstractItemView {{ background-color: {BG2}; color: #ffffff;
    selection-background-color: {ACCENT_DARK}; border: 1px solid #3a4150; }}

QSlider {{ min-height: 22px; background: transparent; }}
QSlider::groove:horizontal {{ background: #333a47; height: 5px; border-radius: 2px; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; height: 5px; border-radius: 2px; }}
QSlider::handle:horizontal {{ background: #ffffff; width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px; }}

QPushButton {{ background-color: #343b48; color: #e8ecf2; border: none;
    border-radius: 7px; padding: 6px 9px; font-weight: 600; }}
QPushButton:hover {{ background-color: #40495a; }}
QPushButton:disabled {{ background-color: #262b33; color: #5b6270; }}
QPushButton#RunAll {{ background-color: {ACCENT}; color: #0d1117; font-size: 11pt; padding: 10px; }}
QPushButton#RunAll:hover {{ background-color: #93b4ff; }}
QPushButton#StageRun {{ background-color: {ACCENT_DARK}; }}
QPushButton#StageRun:hover {{ background-color: #3a5cb0; }}
QPushButton#LoadCurrentBtn {{ background-color: transparent; color: {ACCENT};
    border: 1px solid {ACCENT_DARK}; padding: 2px 8px; font-size: 8.5pt; }}
QPushButton#LoadCurrentBtn:hover {{ background-color: {ACCENT_DARK}; color: #ffffff; }}
QPushButton#AutoButton {{ background-color: #8c6a00; color: #ffffff; }}
QPushButton#AutoButton:hover {{ background-color: #bfa100; color: #000000; }}
QPushButton#ABBtn {{ background-color: {BG2}; padding: 8px 16px; font-size: 10.5pt;
                     min-height: 18px; }}
QPushButton#ABBtn:checked {{ background-color: {ACCENT}; color: #0d1117; }}
QPushButton#CollapseHeader {{ background-color: transparent; color: {ACCENT};
    font-weight: bold; font-size: 10pt; text-align: left; padding: 4px 2px; }}
QPushButton#CollapseHeader:hover {{ color: #93b4ff; }}
QPushButton#CollapseHeader:checked {{ color: #93b4ff; }}

QProgressBar {{ border: none; border-radius: 5px; background: #262b33;
    text-align: center; color: #ffffff; height: 12px; }}
QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 5px; }}

QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{ background: {BG1}; width: 9px; }}
QScrollBar::handle:vertical {{ background: #3a4150; border-radius: 4px; min-height: 30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

/* Disabled-state colors — a stage card's contents get setEnabled(False)
   when its header checkbox is unchecked; without these rules the widgets
   below stayed fully bright even though they were non-interactive. */
QLabel:disabled {{ color: #565c68; }}
QLabel#StageTitle:disabled {{ color: #6b7280; }}
QLabel#StageBadge:disabled {{ background-color: #363c47; color: #6b7280; }}
QLabel#SubHeader:disabled {{ color: #4a505c; }}
QCheckBox:disabled {{ color: #565c68; }}
QCheckBox::indicator:disabled {{ background: #1c1f26; border-color: #333a47; }}
QComboBox:disabled, QDoubleSpinBox:disabled, QSpinBox:disabled {{
    background-color: #1c1f26; color: #565c68; border-color: #2a2f3a; }}
QSlider::groove:horizontal:disabled {{ background: #262b33; }}
QSlider::sub-page:horizontal:disabled {{ background: #4a5160; }}
QSlider::handle:horizontal:disabled {{ background: #5b6270; }}
"""

