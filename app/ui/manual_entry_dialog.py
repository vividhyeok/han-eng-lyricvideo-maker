from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QTextEdit, QPushButton, QFileDialog, QMessageBox
)

class ManualEntryDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Manual Song Info Entry")
        self.resize(500, 600)
        self.result_data = None
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)

        # Title
        layout.addWidget(QLabel("Song Title:"))
        self.title_input = QLineEdit()
        layout.addWidget(self.title_input)

        # Artist
        layout.addWidget(QLabel("Artist:"))
        self.artist_input = QLineEdit()
        layout.addWidget(self.artist_input)

        # Album Art
        layout.addWidget(QLabel("Album Art URL or Path:"))
        art_layout = QHBoxLayout()
        self.art_input = QLineEdit()
        art_layout.addWidget(self.art_input)
        self.browse_art_btn = QPushButton("Browse...")
        self.browse_art_btn.clicked.connect(self.browse_art)
        art_layout.addWidget(self.browse_art_btn)
        layout.addLayout(art_layout)

        # YouTube URL
        layout.addWidget(QLabel("YouTube URL (Optional):"))
        self.youtube_input = QLineEdit()
        self.youtube_input.setPlaceholderText("https://www.youtube.com/watch?v=...")
        layout.addWidget(self.youtube_input)

        # Lyrics
        layout.addWidget(QLabel("Lyrics (Paste here):"))
        self.lyrics_input = QTextEdit()
        layout.addWidget(self.lyrics_input)

        # Buttons
        btn_layout = QHBoxLayout()
        self.ok_btn = QPushButton("Next (Sync Lyrics)")
        self.ok_btn.clicked.connect(self.validate_and_accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.ok_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def browse_art(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Album Art", "", "Images (*.png *.jpg *.jpeg)")
        if path:
            self.art_input.setText(path)

    def validate_and_accept(self):
        title = self.title_input.text().strip()
        artist = self.artist_input.text().strip()
        lyrics = self.lyrics_input.toPlainText().strip()

        if not title or not artist:
            QMessageBox.warning(self, "Missing Info", "Please enter Title and Artist.")
            return
        
        if not lyrics:
            QMessageBox.warning(self, "Missing Info", "Please enter Lyrics.")
            return

        self.result_data = {
            "title": title,
            "artist": artist,
            "album_art": self.art_input.text().strip(),
            "youtube_url": self.youtube_input.text().strip(),
            "lyrics": lyrics
        }
        self.accept()

    def get_data(self):
        return self.result_data
