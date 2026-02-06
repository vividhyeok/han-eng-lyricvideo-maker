"""애플리케이션 진입점."""

import app.config.paths  # Configure FFmpeg/Pydub as early as possible
from app.ui.main_window import MainWindow
from PyQt6.QtWidgets import QApplication
import sys


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
