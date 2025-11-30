from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QRadioButton, QButtonGroup, QComboBox, QCheckBox, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont

import os
import re
import sys
import traceback

from app.pipeline.process_manager import ProcessConfig, ProcessManager
from app.sources.genie_handler import get_genie_lyrics, parse_genie_extra_info, search_genie_songs
from app.sources.youtube_handler import youtube_search
from app.ui.components import ProgressWindow, YouTubeUploadDialog, load_image_from_url
from app.ui.styles import MODERN_STYLESHEET


def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)


class WorkerThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    upload_requested = pyqtSignal(str, str, str)

    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.process_manager = ProcessManager(self.update_progress)

    def run(self):
        try:
            config = ProcessConfig(
                title=self.main_window.title_input.text(),
                artist=self.main_window.artist_input.text(),
                album_art_url=self.main_window.album_cover_input.text(),
                youtube_url=self.main_window.selected_youtube_url,
                output_mode=self.main_window.output_mode
            )

            validation_error = self.process_manager.validate_config(config)
            if validation_error:
                self.error.emit(validation_error)
                return

            output_path = self.process_manager.process(config)

            if output_path and os.path.exists(output_path):
                print(f"[DEBUG] 처리 완료. 출력 파일: {output_path}")
                
                if self.main_window.youtube_upload_enabled and output_path.endswith('.mp4'):
                    self.upload_requested.emit(output_path, config.title, config.artist)
                else:
                    self.finished.emit()
            else:
                raise Exception("출력 파일이 생성되지 않았습니다.")

        except Exception as e:
            print(f"[ERROR] WorkerThread 오류: {str(e)}")
            traceback.print_exc()
            self.error.emit(str(e))

    def update_progress(self, message, value):
        self.progress.emit(message, value)


class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Lyric Video Maker - Modern Edition")
        self.setMinimumSize(1400, 900)
        
        # Apply modern stylesheet
        self.setStyleSheet(MODERN_STYLESHEET)
        
        # Initialize variables
        self.output_mode = "video"
        self.youtube_upload_enabled = False
        self.selected_youtube_url = ""
        self.genie_results = []
        self.youtube_results = []
        self.worker = None
        
        # Create UI
        self.init_ui()
        
    def init_ui(self):
        """Initialize the modern UI"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top Bar
        top_bar = self.create_top_bar()
        main_layout.addWidget(top_bar)
        
        # Content Area (3-column layout)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)
        content_layout.setContentsMargins(20, 20, 20, 20)
        
        # Left Sidebar (Settings)
        left_sidebar = self.create_left_sidebar()
        content_layout.addWidget(left_sidebar, stretch=1)
        
        # Center Area (Search Results)
        center_area = self.create_center_area()
        content_layout.addWidget(center_area, stretch=3)
        
        # Right Panel (Details & Actions)
        right_panel = self.create_right_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        main_layout.addLayout(content_layout)
        
    def create_top_bar(self):
        """Create modern top bar with search"""
        top_bar = QFrame()
        top_bar.setObjectName("card")
        top_bar.setFixedHeight(80)
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(30, 15, 30, 15)
        
        # App Title
        title_label = QLabel("🎵 Lyric Video Maker")
        title_label.setObjectName("title")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search for a song...")
        self.search_input.setFixedWidth(400)
        self.search_input.returnPressed.connect(self.search_song)
        layout.addWidget(self.search_input)
        
        # Search Button
        search_btn = QPushButton("Search")
        search_btn.setFixedWidth(120)
        search_btn.clicked.connect(self.search_song)
        layout.addWidget(search_btn)
        
        return top_bar
    
    def create_left_sidebar(self):
        """Create left sidebar with settings"""
        sidebar = QFrame()
        sidebar.setObjectName("card")
        sidebar.setFixedWidth(300)
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(20)
        
        # Settings Title
        settings_title = QLabel("⚙️ Settings")
        settings_title.setObjectName("subtitle")
        layout.addWidget(settings_title)
        
        # AI Model Selection
        model_label = QLabel("AI Translation Model")
        layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        from app.lyrics.ai_models import get_available_models
        from app.config.config_manager import get_config
        
        available_models = get_available_models()
        config = get_config()
        current_model = config.get_translation_model()
        
        if not available_models:
            self.model_combo.addItem("No models available")
            self.model_combo.setEnabled(False)
        else:
            for model_id, model_name in available_models.items():
                self.model_combo.addItem(model_name, model_id)
            index = self.model_combo.findData(current_model)
            if index >= 0:
                self.model_combo.setCurrentIndex(index)
        
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)
        layout.addWidget(self.model_combo)
        
        # Output Mode
        output_label = QLabel("Output Mode")
        layout.addWidget(output_label)
        
        self.output_video_radio = QRadioButton("🎬 Video (.mp4)")
        self.output_xml_radio = QRadioButton("📄 Premiere XML")
        self.output_video_radio.setChecked(True)
        self.output_video_radio.toggled.connect(lambda: self.set_output_mode("video"))
        self.output_xml_radio.toggled.connect(lambda: self.set_output_mode("premiere_xml"))
        layout.addWidget(self.output_video_radio)
        layout.addWidget(self.output_xml_radio)
        
        # YouTube Upload
        self.youtube_upload_checkbox = QCheckBox("📤 Auto-upload to YouTube")
        self.youtube_upload_checkbox.stateChanged.connect(self.on_youtube_upload_toggled)
        layout.addWidget(self.youtube_upload_checkbox)
        
        layout.addStretch()
        
        return sidebar
    
    def create_center_area(self):
        """Create center area for search results"""
        center = QFrame()
        center.setObjectName("card")
        layout = QVBoxLayout(center)
        
        # Results Title
        results_title = QLabel("🔎 Search Results")
        results_title.setObjectName("subtitle")
        layout.addWidget(results_title)
        
        # Scroll Area for Results
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        self.results_layout = QVBoxLayout(scroll_content)
        self.results_layout.setSpacing(15)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        return center
    
    def create_right_panel(self):
        """Create right panel for song details and actions"""
        panel = QFrame()
        panel.setObjectName("card")
        panel.setFixedWidth(350)
        layout = QVBoxLayout(panel)
        layout.setSpacing(20)
        
        # Details Title
        details_title = QLabel("📝 Song Details")
        details_title.setObjectName("subtitle")
        layout.addWidget(details_title)
        
        # Album Art Preview
        self.album_art_label = QLabel()
        self.album_art_label.setFixedSize(300, 300)
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setStyleSheet("""
            QLabel {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 12px;
                border: 2px dashed rgba(255, 255, 255, 0.2);
            }
        """)
        self.album_art_label.setText("No album art")
        layout.addWidget(self.album_art_label)
        
        # Song Info
        info_frame = QFrame()
        info_layout = QVBoxLayout(info_frame)
        info_layout.setSpacing(10)
        
        # Title
        title_label = QLabel("Title:")
        title_label.setObjectName("hint")
        info_layout.addWidget(title_label)
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Song title...")
        info_layout.addWidget(self.title_input)
        
        # Artist
        artist_label = QLabel("Artist:")
        artist_label.setObjectName("hint")
        info_layout.addWidget(artist_label)
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Artist name...")
        info_layout.addWidget(self.artist_input)
        
        # Album Cover URL
        cover_label = QLabel("Album Cover URL:")
        cover_label.setObjectName("hint")
        info_layout.addWidget(cover_label)
        self.album_cover_input = QLineEdit()
        self.album_cover_input.setPlaceholderText("https://...")
        self.album_cover_input.textChanged.connect(self.update_album_art)
        info_layout.addWidget(self.album_cover_input)
        
        layout.addWidget(info_frame)
        
        layout.addStretch()
        
        # Action Buttons
        self.generate_btn = QPushButton("🎬 Generate Video")
        self.generate_btn.setFixedHeight(50)
        self.generate_btn.clicked.connect(self.process_selection)
        layout.addWidget(self.generate_btn)
        
        return panel
    
    def search_song(self):
        """Search for songs"""
        query = self.search_input.text().strip()
        if not query:
            QMessageBox.warning(self, "Warning", "Please enter a search query")
            return
        
        # Clear previous results
        self.clear_results()
        
        # Search Genie
        try:
            self.genie_results = search_genie_songs(query)
            self.display_genie_results()
        except Exception as e:
            print(f"[ERROR] Genie search failed: {e}")
        
        # Search YouTube
        try:
            self.youtube_results = youtube_search(query)
            self.display_youtube_results()
        except Exception as e:
            print(f"[ERROR] YouTube search failed: {e}")
    
    def clear_results(self):
        """Clear search results"""
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
    
    def display_genie_results(self):
        """Display Genie search results as cards"""
        if not self.genie_results:
            return
        
        # Section Title
        genie_title = QLabel("🎵 Genie Music Results")
        genie_title.setObjectName("subtitle")
        genie_title.setStyleSheet("font-size: 16px; margin-top: 10px;")
        self.results_layout.addWidget(genie_title)
        
        # Button Group
        self.genie_button_group = QButtonGroup()
        
        for idx, result in enumerate(self.genie_results):
            card = self.create_result_card(result, idx, "genie")
            self.results_layout.addWidget(card)
    
    def display_youtube_results(self):
        """Display YouTube search results as cards"""
        if not self.youtube_results:
            return
        
        # Section Title
        youtube_title = QLabel("🎥 YouTube Results")
        youtube_title.setObjectName("subtitle")
        youtube_title.setStyleSheet("font-size: 16px; margin-top: 20px;")
        self.results_layout.addWidget(youtube_title)
        
        # Button Group
        self.youtube_button_group = QButtonGroup()
        
        for idx, result in enumerate(self.youtube_results):
            card = self.create_result_card(result, idx, "youtube")
            self.results_layout.addWidget(card)
    
    def create_result_card(self, result, idx, source):
        """Create a modern result card"""
        card = QFrame()
        card.setObjectName("card")
        card.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QHBoxLayout(card)
        layout.setSpacing(15)
        
        # Radio Button
        radio = QRadioButton()
        if source == "genie":
            self.genie_button_group.addButton(radio, idx)
            radio.clicked.connect(lambda: self.on_genie_selected(idx))
        else:
            self.youtube_button_group.addButton(radio, idx)
            radio.clicked.connect(lambda: self.on_youtube_selected(idx))
        layout.addWidget(radio)
        
        # Thumbnail
        thumb_label = QLabel()
        thumb_label.setFixedSize(80, 80)
        thumb_label.setStyleSheet("border-radius: 8px;")
        
        if source == "genie":
            thumb_url = result.get('albumArt', '')
        else:
            thumb_url = result.get('thumbnail', '')
        
        if thumb_url:
            pixmap = load_image_from_url(thumb_url)
            if pixmap:
                thumb_label.setPixmap(pixmap.scaled(80, 80, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation))
        
        layout.addWidget(thumb_label)
        
        # Info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        
        title = result.get('title', 'Unknown')
        artist = result.get('artist', 'Unknown')
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)
        
        artist_label = QLabel(f"🎤 {artist}")
        artist_label.setObjectName("hint")
        info_layout.addWidget(artist_label)
        
        if source == "genie" and result.get('album'):
            album_label = QLabel(f"💿 {result['album']}")
            album_label.setObjectName("hint")
            info_layout.addWidget(album_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, stretch=1)
        
        return card
    
    def on_genie_selected(self, idx):
        """Handle Genie result selection"""
        if idx < 0 or idx >= len(self.genie_results):
            return
        
        result = self.genie_results[idx]
        self.title_input.setText(result.get('title', ''))
        self.artist_input.setText(result.get('artist', ''))
        self.album_cover_input.setText(result.get('albumArt', ''))
        
        # Download lyrics
        try:
            song_id = result.get('songId')
            if song_id:
                get_genie_lyrics(song_id, "result")
                QMessageBox.information(self, "Success", "Lyrics downloaded successfully!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to download lyrics: {e}")
    
    def on_youtube_selected(self, idx):
        """Handle YouTube result selection"""
        if idx < 0 or idx >= len(self.youtube_results):
            return
        
        result = self.youtube_results[idx]
        self.selected_youtube_url = result.get('link', '')
    
    def update_album_art(self, url):
        """Update album art preview"""
        if not url:
            self.album_art_label.clear()
            self.album_art_label.setText("No album art")
            return
        
        pixmap = load_image_from_url(url)
        if pixmap:
            self.album_art_label.setPixmap(pixmap.scaled(300, 300, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
        else:
            self.album_art_label.setText("Failed to load")
    
    def on_model_changed(self, index):
        """Handle AI model selection change"""
        if index < 0:
            return
        model_id = self.model_combo.itemData(index)
        if model_id:
            from app.config.config_manager import get_config
            config = get_config()
            config.set_translation_model(model_id)
    
    def set_output_mode(self, mode):
        """Set output mode"""
        self.output_mode = mode
    
    def on_youtube_upload_toggled(self, state):
        """Handle YouTube upload toggle"""
        self.youtube_upload_enabled = (state == Qt.CheckState.Checked.value)
    
    def process_selection(self):
        """Process the selected song"""
        if not self.title_input.text() or not self.artist_input.text():
            QMessageBox.warning(self, "Warning", "Please select a song first")
            return
        
        if not self.selected_youtube_url:
            QMessageBox.warning(self, "Warning", "Please select a YouTube audio source")
            return
        
        # Show progress window
        self.progress_window = ProgressWindow()
        self.progress_window.show()
        self.hide()
        
        # Start worker thread
        self.worker = WorkerThread(self)
        self.worker.progress.connect(self.progress_window.update_progress)
        self.worker.finished.connect(self.on_process_complete)
        self.worker.error.connect(self.on_error)
        self.worker.upload_requested.connect(self.on_upload_requested)
        self.worker.start()
    
    def on_process_complete(self):
        """Handle process completion"""
        self.progress_window.close()
        QMessageBox.information(self, "Success", "Video generated successfully!")
        self.worker = None
        self.show()
    
    def on_error(self, error_message):
        """Handle error"""
        self.progress_window.close()
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_message}")
        self.worker = None
        self.show()
    
    def on_upload_requested(self, video_path, title, artist):
        """Handle YouTube upload request"""
        self.progress_window.close()
        self.upload_dialog = YouTubeUploadDialog(video_path, title, artist)
        self.upload_dialog.show()
        self.upload_dialog.destroyed.connect(lambda: self.on_upload_complete())
    
    def on_upload_complete(self):
        """Handle upload completion"""
        self.worker = None
        self.show()


# Alias for compatibility
MainWindow = ModernMainWindow
