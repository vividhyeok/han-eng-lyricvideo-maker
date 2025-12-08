from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QRadioButton, QButtonGroup, QComboBox, QCheckBox, QMessageBox,
    QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QPixmap, QFont

import os
import re
import sys
import traceback
from datetime import datetime

from app.config.paths import LYRICS_DIR, TEMP_DIR, ensure_data_dirs
from app.pipeline.process_manager import ProcessConfig, ProcessManager
from app.sources.genie_handler import get_genie_lyrics, parse_genie_extra_info, search_genie_songs
from app.sources.youtube_handler import youtube_search
from app.ui.components import YouTubeUploadDialog, load_image_from_url
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
                output_mode=self.main_window.output_mode,
                lrc_path=self.main_window.selected_lrc_path
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
        self.setMinimumSize(1400, 1200)
        
        # Apply modern stylesheet
        self.setStyleSheet(MODERN_STYLESHEET)
        
        # Initialize variables
        self.output_mode = "video"
        self.youtube_upload_enabled = False
        self.selected_youtube_url = ""
        self.selected_lrc_path = None
        self.genie_results = []
        self.youtube_results = []
        self.worker = None
        self.selected_genie_duration = None
        self.is_processing = False
        self.progress_bar = None
        self.progress_log = None
        self.last_progress_message = None
        self.queue_items = []  # Queue for batch processing
        self.current_queue_index = 0
        
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
        
        # Left Panel (Song Details)
        left_panel = self.create_song_details_panel()
        content_layout.addWidget(left_panel, stretch=1)
        
        # Center (Search Results + Settings)
        center_area = self.create_center_area()
        content_layout.addWidget(center_area, stretch=2)
        
        # Right Panel (Queue + Progress)
        right_panel = self.create_queue_panel()
        content_layout.addWidget(right_panel, stretch=1)
        
        main_layout.addLayout(content_layout)
        
    def create_top_bar(self):
        """Create modern top bar with search"""
        top_bar = QFrame()
        top_bar.setObjectName("card")
        top_bar.setFixedHeight(120)  # Increased from 100 to 120
        layout = QHBoxLayout(top_bar)
        layout.setContentsMargins(30, 25, 30, 25)  # Increased margins from 20 to 25
        
        # App Title
        title_label = QLabel("🎵 Lyric Video Maker")
        title_label.setObjectName("title")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Search Bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Search for a song...")
        self.search_input.setFixedWidth(400)
        self.search_input.setMinimumHeight(40)  # Increased from 35 to 40
        self.search_input.returnPressed.connect(self.search_song)
        layout.addWidget(self.search_input)
        
        # Search Button
        search_btn = QPushButton("Search")
        search_btn.setFixedWidth(120)
        search_btn.setMinimumHeight(40)  # Increased from 35 to 40
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
        
        # Cleanup Button
        cleanup_btn = QPushButton("🗑️ Clean Temp Files")
        cleanup_btn.setMinimumHeight(45)
        cleanup_btn.clicked.connect(self.clean_temp_files)
        layout.addWidget(cleanup_btn)
        
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
    
    def create_queue_panel(self):
        """Create queue and progress panel"""
        panel = QFrame()
        panel.setObjectName("card")
        panel.setFixedWidth(350)
        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        
        # Queue Header
        queue_header = QHBoxLayout()
        queue_title = QLabel("📋 Processing Queue")
        queue_title.setObjectName("subtitle")
        queue_header.addWidget(queue_title)
        
        self.queue_count_label = QLabel("(0)")
        self.queue_count_label.setObjectName("hint")
        queue_header.addWidget(self.queue_count_label)
        queue_header.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("secondary")
        clear_btn.setMaximumWidth(60)
        clear_btn.clicked.connect(self.clear_queue)
        queue_header.addWidget(clear_btn)
        layout.addLayout(queue_header)
        
        # Queue List
        from PyQt6.QtWidgets import QListWidget
        self.queue_list = QListWidget()
        self.queue_list.setMinimumHeight(200)
        self.queue_list.setStyleSheet("""
            QListWidget {
                background: rgba(0, 0, 0, 0.3);
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 8px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 8px;
                border-radius: 4px;
                margin: 2px;
            }
            QListWidget::item:selected {
                background: rgba(0, 212, 255, 0.3);
            }
            QListWidget::item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        layout.addWidget(self.queue_list)
        
        # Start Batch Button
        self.start_batch_btn = QPushButton("▶ Start Batch Processing")
        self.start_batch_btn.setMinimumHeight(50)
        self.start_batch_btn.setObjectName("primary")
        self.start_batch_btn.setEnabled(False)
        self.start_batch_btn.clicked.connect(self.start_batch_processing)
        layout.addWidget(self.start_batch_btn)
        
        # Progress Section
        progress_label = QLabel("📈 Live Progress")
        progress_label.setObjectName("hint")
        layout.addWidget(progress_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_log = QTextEdit()
        self.progress_log.setReadOnly(True)
        self.progress_log.setMinimumHeight(200)
        self.progress_log.setStyleSheet("font-size: 12px; background: rgba(0,0,0,0.3);")
        layout.addWidget(self.progress_log)
        
        return panel
    
    def create_song_details_panel(self):
        """Create song details panel"""
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
        
        # Add to Queue Button
        self.add_queue_btn = QPushButton("➕ Add to Queue")
        self.add_queue_btn.setMinimumHeight(45)
        self.add_queue_btn.setEnabled(False)
        self.add_queue_btn.clicked.connect(self.add_to_queue)
        layout.addWidget(self.add_queue_btn)

        layout.addStretch()
        
        return panel
    
    def search_song(self):
        """Search for songs on Genie"""
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
        # Clear previous youtube results
        # This is a bit of a hack to find and remove only youtube results
        for i in reversed(range(self.results_layout.count())):
            item = self.results_layout.itemAt(i)
            if item and item.widget():
                # Heuristic to identify youtube section title
                if isinstance(item.widget(), QLabel) and "YouTube Results" in item.widget().text():
                    item.widget().deleteLater()
                    # We assume youtube results are after this title
                    # A better implementation would be to hold a reference to the widgets
                    for j in reversed(range(i, self.results_layout.count())):
                        item_to_remove = self.results_layout.itemAt(j)
                        if item_to_remove and item_to_remove.widget():
                            item_to_remove.widget().deleteLater()
                    break

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
        
        # If there is only one result (best match), auto-select it
        if len(self.youtube_results) == 1:
            self.youtube_button_group.button(0).click()

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
            thumb_url = result[3]  # album_art_url
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

        if source == "genie":
            title = result[0]
            artist, album = parse_genie_extra_info(result[2])
            duration_sec = result[4]
            duration_str = f"{duration_sec // 60:02d}:{duration_sec % 60:02d}" if duration_sec is not None else "N/A"
        else:
            title = result.get('title', 'Unknown')
            artist = "YouTube" # Simplified for YouTube results
            album = None
            duration_str = result.get('duration', "N/A")

        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        title_label.setWordWrap(True)
        info_layout.addWidget(title_label)

        artist_label = QLabel(f"🎤 {artist}")
        artist_label.setObjectName("hint")
        info_layout.addWidget(artist_label)
        
        duration_label = QLabel(f"⏳ {duration_str}")
        duration_label.setObjectName("hint")
        info_layout.addWidget(duration_label)

        if source == "genie" and album:
            album_label = QLabel(f"💿 {album}")
            album_label.setObjectName("hint")
            info_layout.addWidget(album_label)

        info_layout.addStretch()
        layout.addLayout(info_layout, stretch=1)

        return card
    
    def on_genie_selected(self, idx):
        """Handle Genie result selection and trigger YouTube search"""
        if idx < 0 or idx >= len(self.genie_results):
            return
        
        result = self.genie_results[idx]
        # result: (title, song_id, extra_info, album_art_url, duration)
        title, song_id, extra_info, album_art_url, duration = result
        
        artist, album = parse_genie_extra_info(extra_info)
        self.title_input.setText(title)
        self.artist_input.setText(artist)
        self.album_cover_input.setText(album_art_url)
        self.selected_genie_duration = duration
        self.selected_genie_id = song_id  # Store song_id for queue

        # Automatically search YouTube with details
        try:
            query = f"{artist} {title}"
            print(f"[DEBUG] 자동 YouTube 검색: '{query}', 길이: {duration}초")
            self.youtube_results = youtube_search(query, target_duration=duration)
            self.display_youtube_results()
        except Exception as e:
            print(f"[ERROR] YouTube search failed: {e}")
            self.youtube_results = []
            self.display_youtube_results() # Clear previous results on failure

        # Download lyrics
        try:
            self.selected_lrc_path = None
            if song_id:
                lyrics = get_genie_lyrics(song_id)
                if lyrics:
                    ensure_data_dirs()
                    os.makedirs(LYRICS_DIR, exist_ok=True)
                    lrc_path = os.path.join(LYRICS_DIR, f"{song_id}.lrc")
                    with open(lrc_path, "w", encoding="utf-8") as lrc_file:
                        lrc_file.write(lyrics.strip() + "\n")
                    self.selected_lrc_path = lrc_path
                    print(f"[DEBUG] LRC 파일 저장: {lrc_path}")
                else:
                    print("[WARN] 가사 데이터를 가져오지 못했습니다.")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to download lyrics: {e}")
        
        # Enable Add to Queue button
        self.check_ready_to_add()
    
    def on_youtube_selected(self, idx):
        """Handle YouTube result selection"""
        if idx < 0 or idx >= len(self.youtube_results):
            return
        
        result = self.youtube_results[idx]
        self.selected_youtube_url = result.get('link', '')
        print(f"[DEBUG] 선택된 YouTube URL: {self.selected_youtube_url}")

    
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

    def set_processing_state(self, processing: bool):
        """Enable/disable controls while processing"""
        self.is_processing = processing
        controls = [
            self.generate_btn,
            self.search_input,
            self.model_combo,
            self.output_video_radio,
            self.output_xml_radio,
            self.youtube_upload_checkbox,
        ]
        for control in controls:
            control.setDisabled(processing)

        if self.progress_bar:
            if processing:
                self.progress_bar.setVisible(True)
                self.progress_bar.setValue(0)
            else:
                self.progress_bar.setValue(0)
                self.progress_bar.setVisible(False)

    def append_progress_message(self, message: str):
        """Append a timestamped message to the progress log"""
        if not self.progress_log:
            return
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.progress_log.append(f"[{timestamp}] {message}")
        scrollbar = self.progress_log.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        self.last_progress_message = message

    def update_progress_ui(self, message: str, value: int):
        if self.progress_bar:
            clamped = max(0, min(100, value))
            self.progress_bar.setValue(clamped)
        if message and message != self.last_progress_message:
            self.append_progress_message(message)
    
    def process_selection(self):
        """Process the selected song"""
        if not self.title_input.text() or not self.artist_input.text():
            QMessageBox.warning(self, "Warning", "Please select a song first")
            return
        
        if not self.selected_youtube_url:
            QMessageBox.warning(self, "Warning", "Please select a YouTube audio source")
            return
        
        # Prepare UI for processing
        if self.progress_log:
            self.progress_log.clear()
        self.append_progress_message("🚀 Processing started")
        self.set_processing_state(True)
        
        # Start worker thread
        self.worker = WorkerThread(self)
        self.worker.progress.connect(self.update_progress_ui)
        self.worker.finished.connect(self.on_process_complete)
        self.worker.error.connect(self.on_error)
        self.worker.upload_requested.connect(self.on_upload_requested)
        self.worker.start()
    
    def on_process_complete(self):
        """Handle process completion"""
        self.set_processing_state(False)
        self.append_progress_message("✅ Video generated successfully")
        QMessageBox.information(self, "Success", "Video generated successfully!")
        self.worker = None
    
    def on_error(self, error_message):
        """Handle error"""
        self.set_processing_state(False)
        self.append_progress_message(f"❌ Error: {error_message}")
        QMessageBox.critical(self, "Error", f"An error occurred:\n{error_message}")
        self.worker = None
    
    def on_upload_requested(self, video_path, title, artist):
        """Handle YouTube upload request"""
        self.set_processing_state(False)
        self.append_progress_message("📤 Video ready for upload")
        self.upload_dialog = YouTubeUploadDialog(video_path, title, artist)
        self.upload_dialog.show()
        self.upload_dialog.destroyed.connect(lambda: self.on_upload_complete())
    
    def on_upload_complete(self):
        """Handle upload completion"""
        self.append_progress_message("✅ Upload workflow completed")
        self.worker = None
    
    def clean_temp_files(self):
        """Clean temporary files"""
        import glob
        
        reply = QMessageBox.question(
            self, "확인", 
            "임시 파일을 모두 삭제하시겠습니까?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                files = glob.glob(os.path.join(TEMP_DIR, "*"))
                count = len(files)
                for f in files:
                    try:
                        if os.path.isfile(f):
                            os.remove(f)
                    except Exception as e:
                        print(f"[WARN] Failed to delete {f}: {e}")
                
                self.append_progress_message(f"🗑️ Cleaned {count} temp files")
                QMessageBox.information(self, "완료", f"{count}개의 임시 파일을 삭제했습니다.")
            except Exception as e:
                QMessageBox.critical(self, "오류", f"파일 삭제 중 오류 발생:\n{e}")


# Inject queue methods
from app.ui.queue_methods import inject_queue_methods
inject_queue_methods(ModernMainWindow)

# Alias for compatibility
MainWindow = ModernMainWindow
