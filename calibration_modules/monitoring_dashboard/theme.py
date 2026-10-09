"""Dark research-dashboard stylesheet for the monitoring suite."""

QSS = """
QMainWindow, QWidget#dashboardRoot {
    background-color: #0E0F12;
    color: #FFFFFF;
    font-family: "Segoe UI", "Arial", sans-serif;
    font-size: 13px;
}
QFrame#card {
    background-color: #18191E;
    border: 1px solid #2B2D35;
    border-radius: 8px;
}
QFrame#headerBar {
    background-color: #18191E;
    border: 1px solid #2B2D35;
    border-radius: 8px;
}
QFrame#accentBar {
    background-color: #4E2A84;
    border: none;
    border-radius: 2px;
    min-height: 4px;
    max-height: 4px;
}
QLabel {
    color: #FFFFFF;
    background: transparent;
    border: none;
}
QLabel#muted {
    color: #9E9EA8;
}
QLabel#title {
    font-size: 18px;
    font-weight: 650;
    letter-spacing: 0.6px;
}
QLabel#metricValue {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 28px;
    font-weight: 650;
    color: #FFFFFF;
}
QLabel#metricUnit {
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 13px;
    color: #9E9EA8;
}
QLabel#badge {
    background-color: #0E0F12;
    color: #FFFFFF;
    border: 1px solid #4E2A84;
    border-radius: 6px;
    padding: 6px 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
    font-size: 14px;
}
QLabel#chip {
    background-color: #0E0F12;
    color: #B084F4;
    border: 1px solid #2B2D35;
    border-radius: 10px;
    padding: 4px 10px;
    font-family: "Cascadia Mono", "Consolas", monospace;
}
QLabel#overlay {
    background-color: rgba(14, 15, 18, 210);
    color: #FFFFFF;
    border: 1px solid #4E2A84;
    border-radius: 4px;
    padding: 3px 8px;
    font-family: "Cascadia Mono", "Consolas", monospace;
}
QLabel#feed {
    background-color: #0E0F12;
    border: 1px solid #2B2D35;
    border-radius: 4px;
}
QProgressBar {
    background-color: #0E0F12;
    border: 1px solid #2B2D35;
    border-radius: 4px;
    text-align: center;
    color: #FFFFFF;
    font-family: "Cascadia Mono", "Consolas", monospace;
    min-height: 42px;
    max-height: 42px;
}
QComboBox, QPushButton, QLineEdit {
    background-color: #0E0F12;
    color: #FFFFFF;
    border: 1px solid #2B2D35;
    border-radius: 4px;
    padding: 6px 8px;
}
QComboBox QAbstractItemView {
    background-color: #18191E;
    color: #FFFFFF;
    selection-background-color: #4E2A84;
}
QPushButton:hover {
    border-color: #B084F4;
}
QPushButton:disabled {
    color: #9E9EA8;
}
QFrame#unavailablePanel, QWidget#unavailableCover {
    background-color: rgba(92, 94, 102, 140);
    border: none;
    border-radius: 6px;
}
QLabel#unavailableBanner {
    background-color: #FFFFFF;
    color: #1A1A1A;
    font-size: 22px;
    font-weight: 650;
    padding: 12px 18px;
    border-radius: 2px;
}
QProgressBar::chunk {
    background-color: #4E2A84;
    border-radius: 3px;
}
"""
