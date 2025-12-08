"""Queue management methods for MainWindow"""

import os
from PyQt6.QtWidgets import QMessageBox


def check_ready_to_add(self):
    """Check if ready to add to queue"""
    has_genie = hasattr(self, 'selected_genie_id') and self.selected_genie_id
    has_youtube = self.selected_youtube_url
    has_lrc = self.selected_lrc_path and os.path.exists(self.selected_lrc_path)
    
    self.add_queue_btn.setEnabled(has_genie and has_youtube and has_lrc)


def add_to_queue(self):
    """Add current song to queue"""
    if not hasattr(self, 'selected_genie_id') or not self.selected_youtube_url or not self.selected_lrc_path:
        return
    
    queue_item = {
        'title': self.title_input.text(),
        'artist': self.artist_input.text(),
        'album_art_url': self.album_cover_input.text(),
        'youtube_url': self.selected_youtube_url,
        'lrc_path': self.selected_lrc_path,
        'genie_id': self.selected_genie_id
    }
    
    self.queue_items.append(queue_item)
    self.queue_list.addItem(f"🎵 {queue_item['artist']} - {queue_item['title']}")
    self.update_queue_count()
    self.append_progress_message(f"✅ Added to queue: {queue_item['artist']} - {queue_item['title']}")
    
    # Reset selection
    self.selected_youtube_url = ""
    self.selected_lrc_path = None
    if hasattr(self, 'selected_genie_id'):
        delattr(self, 'selected_genie_id')
    self.add_queue_btn.setEnabled(False)


def update_queue_count(self):
    """Update queue count label"""
    count = len(self.queue_items)
    self.queue_count_label.setText(f"({count})")
    self.start_batch_btn.setEnabled(count > 0)


def clear_queue(self):
    """Clear all items from queue"""
    self.queue_items.clear()
    self.queue_list.clear()
    self.update_queue_count()
    self.append_progress_message("🗑️ Queue cleared")


def start_batch_processing(self):
    """Start batch processing of queue"""
    if not self.queue_items or self.is_processing:
        return
    
    self.current_queue_index = 0
    self.append_progress_message(f"▶ Starting batch processing ({len(self.queue_items)} songs)...")
    self.set_processing_state(True)
    self.process_next_in_queue()


def process_next_in_queue(self):
    """Process next item in queue"""
    if self.current_queue_index >= len(self.queue_items):
        self.on_batch_complete()
        return
    
    item = self.queue_items[self.current_queue_index]
    self.append_progress_message(f"🎬 Processing {self.current_queue_index + 1}/{len(self.queue_items)}: {item['artist']} - {item['title']}")
    
    # Update UI with current item
    self.title_input.setText(item['title'])
    self.artist_input.setText(item['artist'])
    self.album_cover_input.setText(item['album_art_url'])
    self.selected_youtube_url = item['youtube_url']
    self.selected_lrc_path = item['lrc_path']
    
    # Start worker
    from app.ui.main_window import WorkerThread
    self.worker = WorkerThread(self)
    self.worker.progress.connect(self.update_progress_ui)
    self.worker.finished.connect(self.on_queue_item_complete)
    self.worker.error.connect(self.on_queue_item_error)
    self.worker.start()


def on_queue_item_complete(self):
    """Handle completion of one queue item"""
    self.worker = None
    self.current_queue_index += 1
    self.process_next_in_queue()


def on_queue_item_error(self, error_message):
    """Handle error in queue item"""
    self.append_progress_message(f"❌ Error processing item {self.current_queue_index + 1}: {error_message}")
    self.worker = None
    
    reply = QMessageBox.question(
        self, "Error", 
        f"Error processing song:\n{error_message}\n\nContinue with next song?",
        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
    )
    
    if reply == QMessageBox.StandardButton.Yes:
        self.current_queue_index += 1
        self.process_next_in_queue()
    else:
        self.on_batch_complete()


def on_batch_complete(self):
    """Handle completion of batch processing"""
    self.set_processing_state(False)
    self.append_progress_message(f"✅ Batch processing complete! Processed {self.current_queue_index}/{len(self.queue_items)} songs")
    QMessageBox.information(self, "Complete", f"Batch processing finished!\nProcessed {self.current_queue_index} out of {len(self.queue_items)} songs.")
    
    # Clear queue
    self.clear_queue()
    self.current_queue_index = 0


# Inject methods into ModernMainWindow class
def inject_queue_methods(cls):
    """Inject queue methods into class"""
    cls.check_ready_to_add = check_ready_to_add
    cls.add_to_queue = add_to_queue
    cls.update_queue_count = update_queue_count
    cls.clear_queue = clear_queue
    cls.start_batch_processing = start_batch_processing
    cls.process_next_in_queue = process_next_in_queue
    cls.on_queue_item_complete = on_queue_item_complete
    cls.on_queue_item_error = on_queue_item_error
    cls.on_batch_complete = on_batch_complete
    return cls
