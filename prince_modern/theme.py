"""Prince Modern stylesheet — dusty lavender palette matched to the mockup photo."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QFontDatabase

# Sampled / matched from the original PRINCE Modern mockup:
#   window ~#19202A, cards ~#1F2130, headers/progress ~#8870A3 (dusty lavender)
_FONT_DIR = Path(__file__).resolve().parent / "fonts"


def load_fonts() -> list[str]:
    """Register bundled Inter faces; returns family names that loaded."""
    loaded: list[str] = []
    if not _FONT_DIR.is_dir():
        return loaded
    for path in sorted(_FONT_DIR.glob("Inter-*.ttf")):
        font_id = QFontDatabase.addApplicationFont(str(path))
        if font_id < 0:
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            if family not in loaded:
                loaded.append(family)
    return loaded


QSS = """
QMainWindow, QWidget#modernRoot {
    background-color: #19202A;
    color: #F2F2F5;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 13px;
}
QFrame#card {
    background-color: #1F2130;
    border: 1px solid #3A4152;
    border-radius: 10px;
}
QFrame#headerBar, QFrame#footerBar {
    background-color: #1F2130;
    border: 1px solid #3A4152;
    border-radius: 10px;
}
QFrame#accentBar {
    background-color: #8870A3;
    border: none;
    border-radius: 2px;
    min-height: 3px;
    max-height: 3px;
}
QFrame#cardHeader {
    background-color: #8870A3;
    border: none;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    border-bottom-left-radius: 0px;
    border-bottom-right-radius: 0px;
    min-height: 28px;
}
QLabel {
    color: #F2F2F5;
    background: transparent;
    border: none;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
}
QLabel#muted {
    color: #A8AAB8;
}
QLabel#title {
    font-size: 16px;
    font-weight: 600;
    letter-spacing: 0.4px;
}
QLabel#cardTitle {
    font-size: 12px;
    font-weight: 600;
    letter-spacing: 0.85px;
    color: #FFFFFF;
    padding: 5px 12px;
}
QLabel#chip {
    background-color: #151A24;
    color: #C4B5DC;
    border: 1px solid #3A4152;
    border-radius: 8px;
    padding: 4px 10px;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 12px;
}
QLabel#chipActive {
    background-color: #151A24;
    color: #D7CBEA;
    border: 1px solid #8870A3;
    border-radius: 8px;
    padding: 4px 10px;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
    font-size: 12px;
    font-weight: 600;
}
QLabel#warning {
    color: #E8C547;
    background-color: rgba(232, 197, 71, 28);
    border: 1px solid #E8C547;
    border-radius: 8px;
    padding: 6px 10px;
}
QLabel#feed {
    background-color: #151A24;
    border: 1px solid #3A4152;
    border-radius: 8px;
}
QLineEdit, QComboBox, QPushButton, QSpinBox, QDoubleSpinBox {
    background-color: #2A303C;
    color: #F2F2F5;
    border: 1px solid #4A5160;
    border-radius: 8px;
    padding: 6px 10px;
    min-height: 18px;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
}
QComboBox QAbstractItemView {
    background-color: #1F2130;
    color: #F2F2F5;
    selection-background-color: #8870A3;
    border-radius: 6px;
}
QPushButton:hover {
    border-color: #A892C0;
    background-color: #323846;
}
QPushButton:disabled {
    color: #7E8190;
}
QPushButton#danger {
    background-color: #3A1A22;
    border-color: #C05060;
}
QPushButton#danger:hover {
    border-color: #E07080;
    background-color: #4A222C;
}
QPushButton#primary {
    background-color: #2E2940;
    border-color: #8870A3;
}
QPushButton#primary:hover {
    border-color: #A892C0;
    background-color: #3A3450;
}
QTextEdit#systemLog {
    background-color: #151A24;
    color: #C8CAD4;
    border: 1px solid #3A4152;
    border-radius: 8px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 12px;
    padding: 8px;
}
QCheckBox {
    color: #F2F2F5;
    spacing: 8px;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #4A5160;
    border-radius: 4px;
    background: #2A303C;
}
QCheckBox::indicator:checked {
    background: #8870A3;
    border-color: #A892C0;
}
QProgressBar {
    background-color: #151A24;
    border: 1px solid #3A4152;
    border-radius: 8px;
    text-align: center;
    color: #F2F2F5;
    font-family: "Inter", "Bahnschrift", "Segoe UI", sans-serif;
    min-height: 32px;
    max-height: 32px;
}
QProgressBar::chunk {
    background-color: #8870A3;
    border-radius: 7px;
}
QScrollArea {
    background: transparent;
    border: none;
}
"""
