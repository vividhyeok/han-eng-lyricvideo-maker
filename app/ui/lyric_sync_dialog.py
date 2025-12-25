import os
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QListWidget, QPushButton, QSlider, QMessageBox, QListWidgetItem,
    QTextEdit, QStackedWidget, QWidget, QInputDialog
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QUrl, QTime, QTimer

class LyricSyncDialog(QDialog):
    def __init__(self, audio_path, lyrics_text, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Lyric Sync Tool")
        self.resize(600, 800)
        
        self.audio_path = audio_path
        self.initial_text = lyrics_text
        self.timestamps = []
        self.current_line_index = 0
        
        self.init_ui()
        self.init_player()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Header
        self.header_label = QLabel("<h2>🎵 Manual Lyric Sync</h2>")
        layout.addWidget(self.header_label)
        
        # Stacked Widget for Edit vs Sync mode
        self.stack = QStackedWidget()
        layout.addWidget(self.stack)
        
        # Page 1: Edit Lyrics
        self.edit_page = QWidget()
        edit_layout = QVBoxLayout(self.edit_page)
        edit_layout.addWidget(QLabel("<b>Step 1: Edit Lyrics</b><br>Paste or edit your lyrics below. Each line will be a subtitle."))
        self.text_edit = QTextEdit()
        self.text_edit.setText(self.initial_text)
        edit_layout.addWidget(self.text_edit)
        
        self.start_sync_btn = QPushButton("Start Syncing →")
        self.start_sync_btn.clicked.connect(self.start_sync_mode)
        self.start_sync_btn.setStyleSheet("font-size: 16px; padding: 10px; background-color: #0078D7; color: white;")
        edit_layout.addWidget(self.start_sync_btn)
        
        self.stack.addWidget(self.edit_page)
        
        # Page 2: Sync Lyrics
        self.sync_page = QWidget()
        sync_layout = QVBoxLayout(self.sync_page)
        sync_layout.addWidget(QLabel("<b>Step 2: Sync Lyrics</b><br>1. Press <b>Enter</b> to Play/Pause.<br>2. Press <b>Spacebar</b> to mark the start of the highlighted line.<br>3. Click a line to rewind and re-sync from there."))
        
        self.list_widget = QListWidget()
        self.list_widget.setStyleSheet("""
            QListWidget { font-size: 16px; }
            QListWidget::item { padding: 10px; border-bottom: 1px solid #eee; }
            QListWidget::item:selected { background-color: #0078D7; color: white; }
        """)
        self.list_widget.itemClicked.connect(self.on_item_clicked)
        self.list_widget.currentRowChanged.connect(self.on_row_changed) # Sync selection changes
        self.list_widget.installEventFilter(self) # Install event filter
        sync_layout.addWidget(self.list_widget)
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.seek_back_btn = QPushButton("⏪ -5s")
        self.seek_back_btn.clicked.connect(lambda: self.seek_relative(-5000))
        controls_layout.addWidget(self.seek_back_btn)

        self.play_btn = QPushButton("▶ Play (Enter)")
        self.play_btn.clicked.connect(self.toggle_playback)
        controls_layout.addWidget(self.play_btn)
        
        self.seek_fwd_btn = QPushButton("⏩ +5s")
        self.seek_fwd_btn.clicked.connect(lambda: self.seek_relative(5000))
        controls_layout.addWidget(self.seek_fwd_btn)

        self.time_label = QLabel("00:00.00")
        self.time_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        controls_layout.addWidget(self.time_label)
        
        sync_layout.addLayout(controls_layout)

        # Edit Controls
        edit_controls_layout = QHBoxLayout()
        
        self.edit_ts_btn = QPushButton("✏️ Edit Time")
        self.edit_ts_btn.clicked.connect(self.edit_timestamp)
        edit_controls_layout.addWidget(self.edit_ts_btn)

        self.delete_ts_btn = QPushButton("❌ Clear Time (Del)")
        self.delete_ts_btn.clicked.connect(self.clear_timestamp)
        edit_controls_layout.addWidget(self.delete_ts_btn)

        sync_layout.addLayout(edit_controls_layout)
        
        # Save Button
        self.save_btn = QPushButton("💾 Save LRC")
        self.save_btn.clicked.connect(self.save_lrc)
        self.save_btn.setEnabled(False)
        sync_layout.addWidget(self.save_btn)
        
        self.stack.addWidget(self.sync_page)
        
    def init_player(self):
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.player.setSource(QUrl.fromLocalFile(self.audio_path))
        
        self.timer = QTimer(self)
        self.timer.setInterval(100) # Reduced frequency to improve performance
        self.timer.timeout.connect(self.update_time)
        self.timer.start()
        
    def start_sync_mode(self):
        text = self.text_edit.toPlainText()
        if not text.strip():
            QMessageBox.warning(self, "Warning", "Please enter some lyrics.")
            return
            
        self.raw_lyrics = [line.strip() for line in text.split('\n') if line.strip()]
        self.timestamps = [None] * len(self.raw_lyrics) # Initialize timestamps
        
        self.list_widget.clear()
        for line in self.raw_lyrics:
            self.list_widget.addItem(line)
            
        self.current_line_index = 0
        self.list_widget.setCurrentRow(0)
        self.stack.setCurrentWidget(self.sync_page)
        self.list_widget.setFocus()
        
    def toggle_playback(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.play_btn.setText("▶ Play (Enter)")
        else:
            self.player.play()
            self.play_btn.setText("⏸ Pause (Enter)")
            self.list_widget.setFocus()
            
    def update_time(self):
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            ms = self.player.position()
            self.time_label.setText(self.format_time(ms))
            
            # Auto-scroll if playing past marked lines (optional visual feedback)
            
    def format_time(self, ms):
        seconds = (ms // 1000) % 60
        minutes = (ms // 60000)
        hundredths = (ms // 10) % 100
        return f"{minutes:02d}:{seconds:02d}.{hundredths:02d}"
        
    def eventFilter(self, source, event):
        if source == self.list_widget and event.type() == event.Type.KeyPress:
            if event.key() == Qt.Key.Key_Space:
                self.mark_timestamp()
                return True
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.toggle_playback()
                return True
            elif event.key() == Qt.Key.Key_Left:
                self.seek_relative(-5000)
                return True
            elif event.key() == Qt.Key.Key_Right:
                self.seek_relative(5000)
                return True
            elif event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
                self.clear_timestamp()
                return True
        return super().eventFilter(source, event)

    def keyPressEvent(self, event):
        # Fallback for when list widget doesn't have focus
        if self.stack.currentWidget() == self.sync_page:
            if event.key() == Qt.Key.Key_Space:
                self.mark_timestamp()
            elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                self.toggle_playback()
            elif event.key() == Qt.Key.Key_Left:
                self.seek_relative(-5000)
            elif event.key() == Qt.Key.Key_Right:
                self.seek_relative(5000)
            elif event.key() == Qt.Key.Key_Delete or event.key() == Qt.Key.Key_Backspace:
                self.clear_timestamp()
            else:
                super().keyPressEvent(event)
        else:
            super().keyPressEvent(event)
            
    def seek_relative(self, ms):
        new_pos = max(0, self.player.position() + ms)
        self.player.setPosition(new_pos)
        self.time_label.setText(self.format_time(new_pos))

    def on_item_clicked(self, item):
        # Just ensure row is selected, on_row_changed will handle logic
        pass

    def on_row_changed(self, row):
        if row < 0: return
        self.current_line_index = row
        
        # If this line already has a timestamp, seek to it
        if self.timestamps[row]:
            # Parse timestamp back to ms
            ts = self.timestamps[row]
            try:
                parts = ts.split(':')
                minutes = int(parts[0])
                seconds_parts = parts[1].split('.')
                seconds = int(seconds_parts[0])
                hundredths = int(seconds_parts[1])
                ms = (minutes * 60000) + (seconds * 1000) + (hundredths * 10)
                self.player.setPosition(ms)
                self.time_label.setText(self.format_time(ms))
            except:
                pass
        
        # Ensure focus stays on list for keyboard nav
        self.list_widget.setFocus()

    def edit_timestamp(self):
        """Manually edit timestamp for the current line"""
        if self.current_line_index >= len(self.raw_lyrics):
            return

        current_ts = self.timestamps[self.current_line_index] or "00:00.00"
        text, ok = QInputDialog.getText(self, "Edit Timestamp", "Enter timestamp (MM:SS.mm):", text=current_ts)
        
        if ok and text:
            # Validate format (simple check)
            try:
                # Update UI and data
                item = self.list_widget.item(self.current_line_index)
                original_text = self.raw_lyrics[self.current_line_index]
                item.setText(f"[{text}] {original_text}")
                self.timestamps[self.current_line_index] = text
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Invalid format: {e}")

    def clear_timestamp(self):
        """Clear timestamp for the current line"""
        if self.current_line_index < len(self.raw_lyrics):
            self.timestamps[self.current_line_index] = None
            item = self.list_widget.item(self.current_line_index)
            original_text = self.raw_lyrics[self.current_line_index]
            item.setText(original_text) # Revert to original text
            
            # Optional: Move to next line? No, stay here to allow re-syncing.
            # But maybe user wants to clear and move back? 
            # For now, just clear.

    def mark_timestamp(self):
        if self.current_line_index >= len(self.raw_lyrics):
            return
            
        ms = self.player.position()
        timestamp = self.format_time(ms)
        
        # Update current item text
        item = self.list_widget.item(self.current_line_index)
        original_text = self.raw_lyrics[self.current_line_index]
        item.setText(f"[{timestamp}] {original_text}")
        
        self.timestamps[self.current_line_index] = timestamp
        self.current_line_index += 1
        
        # Move selection
        if self.current_line_index < len(self.raw_lyrics):
            self.list_widget.setCurrentRow(self.current_line_index)
            self.list_widget.scrollToItem(self.list_widget.item(self.current_line_index))
        else:
            self.save_btn.setEnabled(True)
            self.save_btn.setFocus()
            
    def save_lrc(self):
        # Check if all lines have timestamps
        if not any(self.timestamps):
            return
            
        lrc_content = ""
        for i, text in enumerate(self.raw_lyrics):
            ts = self.timestamps[i]
            if ts:
                lrc_content += f"[{ts}]{text}\n"
            
        self.lrc_content = lrc_content
        self.accept()
        
    def get_lrc_content(self):
        return getattr(self, 'lrc_content', None)
