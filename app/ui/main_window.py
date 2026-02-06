from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QScrollArea, QFrame,
    QRadioButton, QButtonGroup, QComboBox, QCheckBox, QMessageBox,
    QProgressBar, QTextEdit, QListWidget, QListWidgetItem
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
from app.sources.ytmusic_handler import (
    ytmusic_search, ytmusic_get_lyrics, ytmusic_search_albums, ytmusic_get_album_tracks
)
from app.sources.genie_handler import search_genie_songs, get_genie_lyrics
from app.sources.album_art_finder import download_album_art
from app.sources.youtube_handler import download_youtube_audio, youtube_search
from app.ui.components import YouTubeUploadDialog, load_image_from_url, AsyncImageLoader
from app.ui.styles import MODERN_STYLESHEET
from app.ui.lyric_sync_dialog import LyricSyncDialog
from app.ui.manual_entry_dialog import ManualEntryDialog

def sanitize_filename(filename):
    return re.sub(r'[\\/*?:"<>|]', "_", filename)

def _extract_video_id(url):
    if not url:
        return None
    if 'v=' in url:
        return url.split('v=', 1)[1].split('&', 1)[0]
    return None


class QueueItemWidget(QFrame):
    """Custom widget for items in the processing queue"""
    remove_requested = pyqtSignal()
    map_requested = pyqtSignal()

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.init_ui()

    def init_ui(self):
        self.setObjectName("queue_item")
        self.setStyleSheet("""
            #queue_item {
                background: rgba(255, 255, 255, 0.05);
                border-radius: 8px;
                padding: 10px;
                margin: 2px;
            }
            #queue_item:hover {
                background: rgba(255, 255, 255, 0.1);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        
        # Track No
        track_no = self.data.get('track_no')
        if track_no:
            no_label = QLabel(f"{track_no:02d}")
            no_label.setFixedWidth(25)
            no_label.setStyleSheet("font-weight: bold; color: #00d4ff;")
            layout.addWidget(no_label)
            
        # Info
        info_layout = QVBoxLayout()
        title = self.data.get('title', 'Unknown')
        artist = self.data.get('artist', 'Unknown')
        
        title_label = QLabel(title)
        title_label.setStyleSheet("font-weight: bold; font-size: 13px; color: white;")
        info_layout.addWidget(title_label)
        
        artist_label = QLabel(artist)
        artist_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.6);")
        info_layout.addWidget(artist_label)
        layout.addLayout(info_layout, stretch=1)
        
        # Status Icon (LRC)
        self.lrc_status_label = QLabel()
        self.update_lrc_status()
        layout.addWidget(self.lrc_status_label)
        
        # Actions
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(5)
        
        self.map_btn = QPushButton("Sync")
        self.map_btn.setFixedWidth(50)
        self.map_btn.setFixedHeight(25)
        self.map_btn.setStyleSheet("font-size: 10px; background: #2c3e50;")
        self.map_btn.clicked.connect(self.map_requested.emit)
        actions_layout.addWidget(self.map_btn)
        
        remove_btn = QPushButton("✕")
        remove_btn.setFixedWidth(25)
        remove_btn.setFixedHeight(25)
        remove_btn.setStyleSheet("background: #c0392b; border: none; color: white;")
        remove_btn.clicked.connect(self.remove_requested.emit)
        actions_layout.addWidget(remove_btn)
        
        layout.addLayout(actions_layout)

    def update_lrc_status(self):
        has_lrc = bool(self.data.get('lrc_path') and os.path.exists(self.data['lrc_path']))
        if has_lrc:
            self.lrc_status_label.setText("✅ LRC")
            self.lrc_status_label.setStyleSheet("color: #2ecc71; font-size: 10px;")
        else:
            self.lrc_status_label.setText("❌ NO LRC")
            self.lrc_status_label.setStyleSheet("color: #e74c3c; font-size: 10px;")

class WorkerThread(QThread):
    progress = pyqtSignal(str, int)
    finished = pyqtSignal()
    error = pyqtSignal(str)
    upload_requested = pyqtSignal(str, str, str)

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.process_manager = ProcessManager(self.update_progress)

    def run(self):
        try:
            validation_error = self.process_manager.validate_config(self.config)
            if validation_error:
                self.error.emit(validation_error)
                return

            output_path = self.process_manager.process(self.config)

            if output_path and os.path.exists(output_path):
                self.finished.emit()
            else:
                raise Exception("Output file was not generated.")

        except Exception as e:
            print(f"[ERROR] WorkerThread error: {str(e)}")
            traceback.print_exc()
            self.error.emit(str(e))

    def update_progress(self, message, value):
        self.progress.emit(message, value)

class SearchWorker(QThread):
    finished = pyqtSignal(list, list)
    error = pyqtSignal(str)

    def __init__(self, query):
        super().__init__()
        self.query = query

    def run(self):
        try:
            songs = ytmusic_search(self.query)
            albums = ytmusic_search_albums(self.query)
            self.finished.emit(songs, albums)
        except Exception as e:
            self.error.emit(str(e))

class ModernMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("🎵 Lyric Video Maker - Modern Edition")
        self.setMinimumSize(1400, 900)
        
        # Variables
        self.output_mode = "video"
        self.youtube_upload_enabled = False
        self.selected_youtube_url = ""
        self.selected_lrc_path = None
        self.yt_song_results = []
        self.yt_album_results = []
        self.queue_items = []
        self.current_queue_index = 0
        self.is_processing = False
        self.worker = None
        self.is_manual_mode = False
        self.prefer_youtube = False
        self.mapped_queue_index = None
        
        # Apply style
        self.setStyleSheet(MODERN_STYLESHEET)
        
        # Init UI
        self.init_ui()
        
    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Top Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Main Content Area
        content = QWidget()
        content_layout = QHBoxLayout(content)
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # 1. Left Panel (Search results)
        self.search_panel = self.create_search_panel()
        content_layout.addWidget(self.search_panel, stretch=1)
        
        # 2. Middle Panel (Selected song details)
        self.detail_panel = self.create_detail_panel()
        content_layout.addWidget(self.detail_panel, stretch=2)
        
        # 3. Right Panel (Queue & Progress)
        self.queue_panel = self.create_queue_panel()
        content_layout.addWidget(self.queue_panel, stretch=1)
        
        main_layout.addWidget(content)
        
    def create_header(self):
        header = QFrame()
        header.setFixedHeight(100)
        header.setObjectName("sidebar")
        layout = QHBoxLayout(header)
        layout.setContentsMargins(30, 0, 30, 0)
        
        title_label = QLabel("🎵 LYRIC VIDEO MAKER")
        title_label.setObjectName("title")
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Search area
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search for songs or albums...")
        self.search_input.setFixedWidth(400)
        self.search_input.setFixedHeight(40)
        self.search_input.returnPressed.connect(self.search_song)
        layout.addWidget(self.search_input)
        
        self.search_btn = QPushButton("Search")
        self.search_btn.setFixedWidth(120)
        self.search_btn.setFixedHeight(40)
        self.search_btn.clicked.connect(self.search_song)
        layout.addWidget(self.search_btn)
        
        manual_btn = QPushButton("Manual Entry")
        manual_btn.setObjectName("secondary")
        manual_btn.setFixedWidth(130)
        manual_btn.setFixedHeight(40)
        manual_btn.clicked.connect(self.start_manual_entry)
        layout.addWidget(manual_btn)
        
        return header

    def create_search_panel(self):
        panel = QFrame()
        panel.setObjectName("sidebar")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        
        title = QLabel("🔎 Search Results")
        title.setObjectName("subtitle")
        layout.addWidget(title)
        
        self.search_scroll = QScrollArea()
        self.search_scroll.setWidgetResizable(True)
        self.search_content = QWidget()
        self.results_layout = QVBoxLayout(self.search_content)
        self.results_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.results_layout.setSpacing(10)
        self.search_scroll.setWidget(self.search_content)
        
        layout.addWidget(self.search_scroll)
        
        return panel

    def create_detail_panel(self):
        panel = QFrame()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(30)
        
        # Selected Song Header
        header_layout = QHBoxLayout()
        self.detail_title = QLabel("Select a song to start")
        self.detail_title.setObjectName("title")
        self.detail_title.setWordWrap(True)
        header_layout.addWidget(self.detail_title, stretch=1)
        layout.addLayout(header_layout)
        
        # Main Display
        display_layout = QHBoxLayout()
        display_layout.setSpacing(40)
        
        # Album Art
        self.album_art_label = QLabel()
        self.album_art_label.setFixedSize(350, 350)
        self.album_art_label.setStyleSheet("background: rgba(255,255,255,0.05); border-radius: 20px; border: 1px solid rgba(255,255,255,0.1);")
        self.album_art_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.album_art_label.setText("No Art")
        display_layout.addWidget(self.album_art_label)
        
        # Info & Settings
        info_settings = QVBoxLayout()
        info_settings.setSpacing(15)
        
        self.title_input = QLineEdit()
        self.title_input.setPlaceholderText("Title")
        info_settings.addWidget(QLabel("Title"))
        info_settings.addWidget(self.title_input)
        
        self.artist_input = QLineEdit()
        self.artist_input.setPlaceholderText("Artist")
        info_settings.addWidget(QLabel("Artist"))
        info_settings.addWidget(self.artist_input)
        
        self.album_cover_input = QLineEdit()
        self.album_cover_input.setPlaceholderText("Album Art URL")
        self.album_cover_input.textChanged.connect(self.update_album_art)
        info_settings.addWidget(QLabel("Album Art URL"))
        info_settings.addWidget(self.album_cover_input)
        
        # Settings Row
        settings_row = QHBoxLayout()
        
        v_settings = QVBoxLayout()
        v_settings.addWidget(QLabel("AI Model"))
        self.model_combo = QComboBox()
        self.populate_models()
        v_settings.addWidget(self.model_combo)
        settings_row.addLayout(v_settings)
        
        v_output = QVBoxLayout()
        v_output.addWidget(QLabel("Output"))
        self.output_combo = QComboBox()
        self.output_combo.addItems(["Video (.mp4)", "Premiere XML"])
        self.output_combo.currentIndexChanged.connect(self.on_output_changed)
        v_output.addWidget(self.output_combo)
        settings_row.addLayout(v_output)
        
        info_settings.addLayout(settings_row)
        
        self.upload_check = QCheckBox("Auto-upload to YouTube")
        self.upload_check.stateChanged.connect(self.on_upload_toggled)
        info_settings.addWidget(self.upload_check)
        
        info_settings.addStretch()
        display_layout.addLayout(info_settings, stretch=1)
        
        layout.addLayout(display_layout)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(20)
        
        self.sync_btn = QPushButton("🎵 Sync Lyrics")
        self.sync_btn.setMinimumHeight(60)
        self.sync_btn.setObjectName("secondary")
        self.sync_btn.setEnabled(False)
        self.sync_btn.clicked.connect(self.start_manual_sync)
        actions_layout.addWidget(self.sync_btn)
        
        self.add_queue_btn = QPushButton("➕ Add to Queue")
        self.add_queue_btn.setMinimumHeight(60)
        self.add_queue_btn.setObjectName("primary")
        self.add_queue_btn.setEnabled(False)
        self.add_queue_btn.clicked.connect(self.add_to_queue)
        actions_layout.addWidget(self.add_queue_btn)
        
        layout.addLayout(actions_layout)
        layout.addStretch()
        
        return panel

    def create_queue_panel(self):
        panel = QFrame()
        panel.setObjectName("sidebar")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QHBoxLayout()
        header.addWidget(QLabel("📋 Queue"))
        self.queue_count = QLabel("(0)")
        header.addWidget(self.queue_count)
        header.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setFixedHeight(25)
        clear_btn.setObjectName("secondary")
        clear_btn.clicked.connect(self.clear_queue)
        header.addWidget(clear_btn)
        layout.addLayout(header)
        
        self.queue_list_ui = QListWidget()
        layout.addWidget(self.queue_list_ui)
        
        self.start_batch_btn = QPushButton("▶ Start Batch")
        self.start_batch_btn.setObjectName("primary")
        self.start_batch_btn.setMinimumHeight(50)
        self.start_batch_btn.setEnabled(False)
        self.start_batch_btn.clicked.connect(self.start_batch_processing)
        layout.addWidget(self.start_batch_btn)
        
        # Log
        layout.addWidget(QLabel("📈 Log"))
        self.progress_log = QTextEdit()
        self.progress_log.setReadOnly(True)
        layout.addWidget(self.progress_log)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        return panel

    # Logic Methods
    def populate_models(self):
        from app.lyrics.ai_models import get_available_models
        from app.config.config_manager import get_config
        models = get_available_models()
        config = get_config()
        current = config.get_translation_model()
        for mid, name in models.items():
            self.model_combo.addItem(name, mid)
        idx = self.model_combo.findData(current)
        if idx >= 0: self.model_combo.setCurrentIndex(idx)
        self.model_combo.currentIndexChanged.connect(self.on_model_changed)

    def on_model_changed(self, idx):
        mid = self.model_combo.itemData(idx)
        from app.config.config_manager import get_config
        get_config().set_translation_model(mid)

    def on_output_changed(self, idx):
        self.output_mode = "video" if idx == 0 else "premiere_xml"

    def on_upload_toggled(self, state):
        self.youtube_upload_enabled = bool(state == Qt.CheckState.Checked.value)

    def update_album_art(self, url):
        if not url:
            self.album_art_label.setText("No Art")
            return
        pixmap = load_image_from_url(url, size=(350, 350))
        if pixmap:
            self.album_art_label.setPixmap(pixmap)
        else:
            self.album_art_label.setText("Load Failed")

    def search_song(self):
        query = self.search_input.text().strip()
        if not query: return
        
        self.clear_results()
        self.log(f"Searching for '{query}'...")
        self.search_btn.setEnabled(False)
        self.search_input.setEnabled(False)
        
        # Loading indicator
        loading_label = QLabel("🔍 Searching... Please wait.")
        loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        loading_label.setStyleSheet("color: #00d4ff; font-size: 14px; margin-top: 20px;")
        self.results_layout.addWidget(loading_label)
        
        self.search_worker = SearchWorker(query)
        self.search_worker.finished.connect(self.on_search_finished)
        self.search_worker.error.connect(self.on_search_error)
        self.search_worker.start()

    def on_search_finished(self, songs, albums):
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.clear_results()
        
        self.yt_song_results = songs
        self.yt_album_results = albums
        
        self.display_yt_results()
        self.log(f"Search complete. Found {len(songs)} songs, {len(albums)} albums.")

    def on_search_error(self, err):
        self.search_btn.setEnabled(True)
        self.search_input.setEnabled(True)
        self.clear_results()
        self.results_layout.addWidget(QLabel(f"Search failed: {err}"))
        self.log(f"Search error: {err}")

    def clear_results(self):
        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()

    def display_yt_results(self):
        # Albums
        if self.yt_album_results:
            self.results_layout.addWidget(self.create_header_label("💿 Albums"))
            self.album_group = QButtonGroup()
            for i, res in enumerate(self.yt_album_results):
                card = self.create_result_card(res, i, "album")
                self.results_layout.addWidget(card)
        
        # Songs
        if self.yt_song_results:
            self.results_layout.addWidget(self.create_header_label("🎵 Songs"))
            self.song_group = QButtonGroup()
            for i, res in enumerate(self.yt_song_results):
                card = self.create_result_card(res, i, "song")
                self.results_layout.addWidget(card)
        
        if not self.yt_song_results and not self.yt_album_results:
            self.results_layout.addWidget(QLabel("No results found."))
        
        self.results_layout.addStretch()

    def create_header_label(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet("font-weight: bold; margin-top: 10px; color: #00d4ff;")
        return lbl

    def create_result_card(self, res, idx, type):
        card = QFrame()
        card.setObjectName("card")
        card.setFixedHeight(80)
        lay = QHBoxLayout(card)
        
        radio = QRadioButton()
        if type == "album": 
            self.album_group.addButton(radio, idx)
            radio.clicked.connect(lambda: self.on_album_selected(idx))
        else: 
            self.song_group.addButton(radio, idx)
            radio.clicked.connect(lambda: self.on_song_selected(idx))
        lay.addWidget(radio)
        
        # Thumb
        thumb = QLabel()
        thumb.setFixedSize(60, 60)
        thumb.setStyleSheet("background-color: rgba(255,255,255,0.1); border-radius: 4px;")
        
        url = res.get('album_art', '')
        if url:
             loader = AsyncImageLoader(url, size=(60, 60))
             loader.image_loaded.connect(thumb.setPixmap)
             thumb.loader = loader # Keep reference
             loader.start()
        
        lay.addWidget(thumb)
        
        info = QVBoxLayout()
        t_lbl = QLabel(res.get('title'))
        t_lbl.setStyleSheet("font-weight: bold;")
        info.addWidget(t_lbl)
        a_lbl = QLabel(res.get('artist'))
        a_lbl.setStyleSheet("font-size: 11px; color: grey;")
        info.addWidget(a_lbl)
        lay.addLayout(info, stretch=1)
        
        return card

    def on_song_selected(self, idx):
        res = self.yt_song_results[idx]
        self.detail_title.setText(f"🎵 {res['title']}")
        self.title_input.setText(res['title'])
        self.artist_input.setText(res['artist'])
        self.album_cover_input.setText(res['album_art'])
        self.selected_youtube_url = res['youtube_url']
        self.selected_lrc_path = None
        self.prefer_youtube = False
        self.mapped_queue_index = None
        self.check_ready()

    def on_album_selected(self, idx):
        album = self.yt_album_results[idx]
        self.log(f"Loading album: {album['title']}")
        try:
            tracks = ytmusic_get_album_tracks(album['browse_id'])
            self.display_album_view(album, tracks)
        except Exception as e:
            self.log(f"Album error: {e}")

    def display_album_view(self, album, tracks):
        self.clear_results()
        self.results_layout.addWidget(self.create_header_label(f"💿 Album: {album['title']}"))
        
        add_all = QPushButton(f"Add all {len(tracks)} songs to queue")
        add_all.clicked.connect(lambda: self.add_album_to_queue(album, tracks))
        self.results_layout.addWidget(add_all)
        
        for i, t in enumerate(tracks):
            lbl = QLabel(f"{i+1}. {t['title']}")
            lbl.setStyleSheet("padding: 5px; border-bottom: 1px solid rgba(255,255,255,0.05);")
            self.results_layout.addWidget(lbl)
        
        back_btn = QPushButton("← Back to results")
        back_btn.clicked.connect(self.display_yt_results)
        self.results_layout.addWidget(back_btn)
        self.results_layout.addStretch()

    def add_album_to_queue(self, album, tracks):
        for t in tracks:
            item = {
                'title': t['title'],
                'artist': t['artist'],
                'album_art_url': t['album_art'],
                'youtube_url': t['youtube_url'],
                'lrc_path': None,
                'track_no': t.get('track_no'),
                'sub_folder': album['title'],
                'output_mode': self.output_mode,
                'prefer_youtube': False
            }
            self.enqueue(item)
        self.log(f"Added album '{album['title']}' to queue.")

    def check_ready(self):
        has_yt = bool(self.selected_youtube_url)
        has_meta = bool(self.title_input.text() and self.artist_input.text())
        has_lrc = bool(self.selected_lrc_path and os.path.exists(self.selected_lrc_path))
        
        self.sync_btn.setEnabled(has_yt and has_meta)
        self.add_queue_btn.setEnabled(has_yt and has_meta)

    def start_manual_sync(self):
        if not self.selected_youtube_url: return
        
        lyrics_text = self._get_prefill_lyrics(self.title_input.text(), self.artist_input.text(), self.selected_youtube_url)
        
        self.log("Downloading audio for sync...")
        filename = sanitize_filename(f"{self.artist_input.text()} - {self.title_input.text()}")
        audio_path = download_youtube_audio(self.selected_youtube_url, filename)
        
        if not audio_path:
            QMessageBox.warning(self, "Error", "Failed to download audio for sync.")
            return

        dialog = LyricSyncDialog(audio_path, lyrics_text, self)
        if dialog.exec():
            lrc_content = dialog.get_lrc_content()
            if lrc_content:
                ensure_data_dirs()
                lrc_path = os.path.join(LYRICS_DIR, f"{filename}.lrc")
                with open(lrc_path, "w", encoding="utf-8") as f:
                    f.write(lrc_content)
                self.selected_lrc_path = lrc_path
                self.prefer_youtube = True
                self.log(f"LRC saved: {lrc_path}")
                if self.mapped_queue_index is not None:
                    if 0 <= self.mapped_queue_index < len(self.queue_items):
                        self.queue_items[self.mapped_queue_index]['lrc_path'] = lrc_path
                        self.queue_items[self.mapped_queue_index]['prefer_youtube'] = True
                        self.refresh_queue_ui()
                self.check_ready()

    def add_to_queue(self):
        item = {
            'title': self.title_input.text(),
            'artist': self.artist_input.text(),
            'album_art_url': self.album_cover_input.text(),
            'youtube_url': self.selected_youtube_url,
            'lrc_path': self.selected_lrc_path,
            'output_mode': self.output_mode,
            'prefer_youtube': self.prefer_youtube
        }
        self.enqueue(item)

    def enqueue(self, item):
        self.queue_items.append(item)
        idx = len(self.queue_items) - 1
        
        list_item = QListWidgetItem(self.queue_list_ui)
        list_item.setSizeHint(QSize(300, 70))
        widget = QueueItemWidget(item)
        widget.remove_requested.connect(lambda: self.remove_item(idx))
        widget.map_requested.connect(lambda: self.map_item(idx))
        
        self.queue_list_ui.addItem(list_item)
        self.queue_list_ui.setItemWidget(list_item, widget)
        self.update_queue_ui()

    def remove_item(self, idx):
        if 0 <= idx < len(self.queue_items):
            self.queue_items.pop(idx)
            self.refresh_queue_ui()

    def map_item(self, idx):
        item = self.queue_items[idx]
        self.title_input.setText(item['title'])
        self.artist_input.setText(item['artist'])
        self.album_cover_input.setText(item['album_art_url'])
        self.selected_youtube_url = item['youtube_url']
        self.selected_lrc_path = item['lrc_path']
        self.prefer_youtube = item.get('prefer_youtube', False)
        self.mapped_queue_index = idx
        self.check_ready()

    def update_queue_ui(self):
        cnt = len(self.queue_items)
        self.queue_count.setText(f"({cnt})")
        self.start_batch_btn.setEnabled(cnt > 0 and not self.is_processing)

    def refresh_queue_ui(self):
        self.queue_list_ui.clear()
        temp = self.queue_items
        self.queue_items = []
        for i in temp: self.enqueue(i)
        self.update_queue_ui()

    def clear_queue(self):
        self.queue_items = []
        self.queue_list_ui.clear()
        self.update_queue_ui()

    def start_batch_processing(self):
        if not self.queue_items: return
        missing_lrc = [
            i for i, item in enumerate(self.queue_items)
            if not item.get('lrc_path') or not os.path.exists(item.get('lrc_path'))
        ]
        if missing_lrc:
            self.log("Cannot start batch: missing LRC for some items.")
            QMessageBox.warning(self, "Missing LRC", "Some queue items are missing LRC files. Sync lyrics first.")
            return
        self.current_queue_index = 0
        self.is_processing = True
        self.set_ui_processing(True)
        self.process_next()

    def process_next(self):
        if self.current_queue_index >= len(self.queue_items):
            self.is_processing = False
            self.set_ui_processing(False)
            self.log("Batch processing complete.")
            QMessageBox.information(self, "Done", "All items processed!")
            return
            
        item = self.queue_items[self.current_queue_index]
        self.queue_list_ui.setCurrentRow(self.current_queue_index)
        
        config = ProcessConfig(
            title=item['title'],
            artist=item['artist'],
            album_art_url=item['album_art_url'],
            youtube_url=item['youtube_url'],
            output_mode=item['output_mode'],
            lrc_path=item['lrc_path'],
            prefer_youtube=item.get('prefer_youtube', False),
            track_no=item.get('track_no'),
            sub_folder=item.get('sub_folder')
        )
        
        self.worker = WorkerThread(config)
        self.worker.progress.connect(self.on_worker_progress)
        self.worker.finished.connect(self.on_worker_finished)
        self.worker.error.connect(self.on_worker_error)
        self.worker.start()

    def on_worker_progress(self, msg, val):
        self.log(msg)
        self.progress_bar.setValue(val)

    def on_worker_finished(self):
        self.log(f"Finished: {self.queue_items[self.current_queue_index]['title']}")
        self.current_queue_index += 1
        self.process_next()

    def on_worker_error(self, err):
        self.log(f"Error: {err}")
        self.current_queue_index += 1
        self.process_next()

    def set_ui_processing(self, state):
        self.start_batch_btn.setDisabled(state)
        if hasattr(self, 'search_btn'): self.search_btn.setDisabled(state)
        self.progress_bar.setVisible(state)

    def _get_prefill_lyrics(self, title, artist, youtube_url):
        # Try YTMusic lyrics first, then Genie as fallback.
        try:
            vid = _extract_video_id(youtube_url)
            if vid:
                self.log('Fetching lyrics from YTMusic...')
                lyrics = ytmusic_get_lyrics(vid)
                if lyrics and isinstance(lyrics, str):
                    return lyrics.strip()
        except Exception as e:
            self.log(f'YTMusic lyrics fetch failed: {e}')

        try:
            query = f"{artist} {title}".strip()
            if query:
                self.log('Fetching lyrics from Genie...')
                results = search_genie_songs(query, limit=1)
                if results:
                    _, song_id, _, _, _ = results[0]
                    lyrics = get_genie_lyrics(str(song_id))
                    if lyrics and isinstance(lyrics, str):
                        return lyrics.strip()
        except Exception as e:
            self.log(f'Genie lyrics fetch failed: {e}')

        return ''

    def log(self, msg):
        time = datetime.now().strftime("%H:%M:%S")
        self.progress_log.append(f"[{time}] {msg}")

    def start_manual_entry(self):
        dialog = ManualEntryDialog(self)
        if dialog.exec():
            data = dialog.get_data()
            self.detail_title.setText(f"📝 {data['title']} (Manual)")
            self.title_input.setText(data['title'])
            self.artist_input.setText(data['artist'])
            self.album_cover_input.setText(data['album_art'])
            self.selected_youtube_url = data.get('youtube_url', "")
            self.is_manual_mode = True
            self.check_ready()

MainWindow = ModernMainWindow
