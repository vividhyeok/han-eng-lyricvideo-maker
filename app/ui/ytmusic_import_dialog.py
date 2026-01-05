from __future__ import annotations

from typing import List

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QHBoxLayout,
)

from app.sources.ytmusic_export_handler import TrackItem


class YTMusicImportDialog(QDialog):
    """Preview dialog for imported YouTube Music tracks."""

    def __init__(self, tracks: List[TrackItem], parent=None):
        super().__init__(parent)
        self.setWindowTitle("YouTube Music Import Preview")
        self.resize(700, 400)
        self.tracks = tracks
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(f"Found {len(self.tracks)} tracks. Sort columns to verify before enqueueing."))

        table = QTableWidget(len(self.tracks), 4)
        table.setHorizontalHeaderLabels(["Title", "Artist", "Album", "Video ID"])
        table.setSortingEnabled(True)
        for row, track in enumerate(self.tracks):
            table.setItem(row, 0, QTableWidgetItem(track.title))
            table.setItem(row, 1, QTableWidgetItem(track.artist))
            table.setItem(row, 2, QTableWidgetItem(track.album or ""))
            table.setItem(row, 3, QTableWidgetItem(track.video_id))
        table.resizeColumnsToContents()
        layout.addWidget(table)

        buttons = QHBoxLayout()
        ok_btn = QPushButton("Enqueue All")
        ok_btn.clicked.connect(self.accept)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        buttons.addWidget(ok_btn)
        buttons.addWidget(cancel_btn)
        layout.addLayout(buttons)
