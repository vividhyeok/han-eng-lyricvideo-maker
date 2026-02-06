"""
Modern Styles for Lyric Video Maker GUI
Dark theme with glassmorphism and smooth animations
"""

MODERN_STYLESHEET = """
/* Main Window */
QMainWindow {
    background: #0f0f1a;
}

/* Scroll Area */
QScrollArea {
    border: none;
    background: transparent;
}

/* Card Style Frames */
QFrame#card {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

QFrame#card:hover {
    background: rgba(255, 255, 255, 0.06);
    border: 1px solid rgba(255, 255, 255, 0.15);
}

/* Sidebar Panels */
QFrame#sidebar {
    background: rgba(0, 0, 0, 0.2);
    border-right: 1px solid rgba(255, 255, 255, 0.05);
}

/* Input Fields */
QLineEdit {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 10px 15px;
    color: #ffffff;
    font-size: 14px;
}

QLineEdit:focus {
    border: 1px solid #00d4ff;
    background: rgba(255, 255, 255, 0.08);
}

/* Buttons */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00d4ff, stop:1 #0099cc);
    border: none;
    border-radius: 8px;
    padding: 10px 20px;
    color: white;
    font-size: 13px;
    font-weight: bold;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00e5ff, stop:1 #00aadd);
}

QPushButton:pressed {
    background: #008899;
}

QPushButton:disabled {
    background: rgba(255, 255, 255, 0.05);
    color: rgba(255, 255, 255, 0.2);
}

/* Primary Button (Larger) */
QPushButton#primary {
    padding: 15px 30px;
    font-size: 15px;
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                stop:0 #00d4ff, stop:1 #00a8ff);
}

/* Secondary Button */
QPushButton#secondary {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.1);
}

QPushButton#secondary:hover {
    background: rgba(255, 255, 255, 0.12);
}

/* Labels */
QLabel {
    color: #e0e0e0;
}

QLabel#title {
    font-size: 24px;
    font-weight: bold;
    color: #00d4ff;
}

QLabel#subtitle {
    font-size: 16px;
    font-weight: bold;
    color: #ffffff;
}

QLabel#hint {
    font-size: 12px;
    color: rgba(255, 255, 255, 0.5);
}

/* ComboBox */
QComboBox {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 8px;
    padding: 8px 12px;
    color: #ffffff;
}

/* List Widget (Queue) */
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}

QListWidget::item {
    background: rgba(255, 255, 255, 0.03);
    border-radius: 8px;
    margin-bottom: 5px;
    border: 1px solid rgba(255, 255, 255, 0.05);
}

QListWidget::item:selected {
    background: rgba(0, 212, 255, 0.1);
    border: 1px solid rgba(0, 212, 255, 0.3);
}

/* Progress Bar */
QProgressBar {
    background: rgba(255, 255, 255, 0.05);
    border: none;
    border-radius: 4px;
    text-align: center;
    color: #ffffff;
    height: 6px;
}

QProgressBar::chunk {
    background: #00d4ff;
    border-radius: 4px;
}

/* Text Edit (Log) */
QTextEdit {
    background: rgba(0, 0, 0, 0.2);
    border: 1px solid rgba(255, 255, 255, 0.05);
    border-radius: 8px;
    color: #a0a0a0;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 11px;
    padding: 10px;
}
"""
