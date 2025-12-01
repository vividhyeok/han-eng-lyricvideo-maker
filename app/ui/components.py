from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QLabel,
                           QRadioButton, QDialog, QLineEdit, QTextEdit, 
                           QPushButton, QComboBox, QCheckBox, QMessageBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage
import requests
import threading
from app.upload.youtube_uploader import upload_video

def load_image_from_url(url, size=(120, 90)):
    """URL에서 이미지를 로드하여 QPixmap으로 반환"""
    try:
        response = requests.get(url)
        image = QImage.fromData(response.content)
        pixmap = QPixmap.fromImage(image)
        return pixmap.scaled(size[0], size[1], Qt.AspectRatioMode.KeepAspectRatio)
    except Exception as e:
        print("이미지 로드 실패:", e)
        return None

def create_album_art_preview():
    """앨범 아트 미리보기 레이블 생성"""
    label = QLabel()
    label.setFixedSize(120, 90)
    label.setStyleSheet("background-color: lightgrey;")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label

def update_album_art_preview(label, url):
    """앨범 아트 미리보기 업데이트"""
    if not url:
        label.clear()
        return
        
    pixmap = load_image_from_url(url)
    if pixmap:
        label.setPixmap(pixmap)
    else:
        label.clear()

def create_youtube_result_item(parent, result, idx, main_window):
    item = QWidget()
    layout = QHBoxLayout(item)
    
    # 라디오 버튼 생성
    radio = QRadioButton()
    main_window.youtube_button_group.addButton(radio, idx)
    layout.addWidget(radio)
    
    # 썸네일과 정보 표시
    thumb_label = QLabel()
    thumb_url = result.get('thumbnail', '')
    if (thumb_url):
        pixmap = load_image_from_url(thumb_url)
        if pixmap:
            thumb_label.setPixmap(pixmap.scaled(120, 90, Qt.AspectRatioMode.KeepAspectRatio))
    thumb_label.setFixedSize(120, 90)
    layout.addWidget(thumb_label)
    
    # 곡 정보 표시
    info_widget = QWidget()
    info_layout = QVBoxLayout(info_widget)
    title_label = QLabel(result.get('title', ''))
    title_label.setWordWrap(True)
    info_layout.addWidget(title_label)
    
    duration_label = QLabel(f"길이: {result.get('duration', 'N/A')}")
    info_layout.addWidget(duration_label)
    layout.addWidget(info_widget)
    
    # 라디오 버튼 클릭 이벤트 연결
    radio.clicked.connect(lambda _, selected_idx=idx: main_window.on_youtube_selection(selected_idx))
    
    return item

def create_genie_result_item(parent, idx, title, artist, album, window, album_art_url=None):
    """지니뮤직 검색 결과 아이템 위젯 생성"""
    item_widget = QWidget()
    layout = QHBoxLayout(item_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    
    # 라디오 버튼
    radio = QRadioButton()
    window.genie_button_group.addButton(radio)
    window.genie_button_group.setId(radio, idx)
    layout.addWidget(radio)
    
    # 앨범 아트 미리보기 (60x60)
    if album_art_url:
        art_label = QLabel()
        art_label.setFixedSize(60, 60)
        pixmap = load_image_from_url(album_art_url)
        if pixmap:
            art_label.setPixmap(pixmap.scaled(60, 60, Qt.AspectRatioMode.KeepAspectRatio))
        art_label.setStyleSheet("background-color: lightgrey;")
        layout.addWidget(art_label)
    
    # 정보 표시
    info_widget = QWidget()
    info_layout = QVBoxLayout(info_widget)
    title_label = QLabel(f"제목: {title}")
    artist_label = QLabel(f"아티스트: {artist}")
    title_label.setStyleSheet("font-weight: bold;")
    info_layout.addWidget(title_label)
    info_layout.addWidget(artist_label)
    if album:
        info_layout.addWidget(QLabel(f"앨범: {album}"))
    layout.addWidget(info_widget, stretch=1)
    
    return item_widget

def create_album_art_preview(parent, url, idx, window):
    """앨범 아트 미리보기 아이템 생성"""
    item_widget = QWidget()
    layout = QHBoxLayout(item_widget)
    layout.setContentsMargins(5, 5, 5, 5)
    
    # 라디오 버튼
    radio = QRadioButton()
    window.album_art_button_group.addButton(radio)
    window.album_art_button_group.setId(radio, idx)
    layout.addWidget(radio)
    
    # 앨범 아트 미리보기
    art_label = QLabel()
    art_label.setFixedSize(100, 100)
    pixmap = load_image_from_url(url)
    if pixmap:
        art_label.setPixmap(pixmap.scaled(100, 100, Qt.AspectRatioMode.KeepAspectRatio))
    layout.addWidget(art_label)
    
    # 선택 시 이벤트 연결
    radio.clicked.connect(lambda _, selected_idx=idx: window.on_album_art_selected(selected_idx))
    
    return item_widget

class ProgressWindow(QWidget):
    """작업 진행 상황을 보여주는 창"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle("작업 진행 상황")
        self.setFixedSize(500, 200)
        
        layout = QVBoxLayout(self)
        
        # 진행 상황 메시지
        self.progress_label = QLabel("진행 상황: 준비 중...")
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.progress_label)
        
        # 진행 상태 바를 추가할 수 있습니다 (선택사항)
        # self.progress_bar = QProgressBar()
        # layout.addWidget(self.progress_bar)
        
        # 창을 화면 중앙에 위치
        self.center_window()
        
    def center_window(self):
        """창을 화면 중앙에 위치시킴"""
        frame = self.frameGeometry()
        center = self.screen().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())
        
    def update_progress(self, message, value=None):
        """진행 상황 업데이트"""
        self.progress_label.setText(f"진행 상황: {message}")
        # if value is not None:
        #     self.progress_bar.setValue(value)


class YouTubeUploadDialog(QDialog):
    """YouTube 업로드 대화상자"""
    def __init__(self, video_path, title, artist):
        super().__init__()
        self.video_path = video_path
        self.setWindowTitle("YouTube 업로드")
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # 제목 입력
        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("제목:"))
        self.title_input = QLineEdit(f"{title} - {artist}")
        title_layout.addWidget(self.title_input)
        layout.addLayout(title_layout)
        
        # 설명 입력
        layout.addWidget(QLabel("설명:"))
        self.description_input = QTextEdit()
        self.description_input.setPlainText(f"{artist}의 {title} 뮤직비디오")
        self.description_input.setMaximumHeight(100)
        layout.addWidget(self.description_input)
        
        # 태그 입력
        layout.addWidget(QLabel("태그 (쉼표로 구분):"))
        self.tags_input = QLineEdit(f"{artist},{title},뮤직비디오")
        layout.addWidget(self.tags_input)
        
        # 공개 설정
        privacy_layout = QHBoxLayout()
        privacy_layout.addWidget(QLabel("공개 설정:"))
        self.privacy_combo = QComboBox()
        self.privacy_combo.addItems(["private", "unlisted", "public"])
        self.privacy_combo.setCurrentText("private")
        privacy_layout.addWidget(self.privacy_combo)
        layout.addLayout(privacy_layout)
        
        # 버튼들
        button_layout = QHBoxLayout()
        self.upload_button = QPushButton("업로드")
        self.upload_button.clicked.connect(self.upload_video)
        button_layout.addWidget(self.upload_button)
        
        self.cancel_button = QPushButton("취소")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # 진행 상황 레이블
        self.status_label = QLabel("")
        layout.addWidget(self.status_label)
        
        self.center_window()
    
    def center_window(self):
        """창을 화면 중앙에 위치시킴"""
        frame = self.frameGeometry()
        center = self.screen().availableGeometry().center()
        frame.moveCenter(center)
        self.move(frame.topLeft())
    
    def upload_video(self):
        """비디오 업로드"""
        self.upload_button.setEnabled(False)
        self.status_label.setText("업로드 준비 중...")
        
        # UI에서 값 가져오기
        title = self.title_input.text()
        description = self.description_input.toPlainText()
        tags = [tag.strip() for tag in self.tags_input.text().split(',') if tag.strip()]
        privacy = self.privacy_combo.currentText()
        
        # 백그라운드에서 업로드
        def upload_thread():
            try:
                self.status_label.setText("YouTube에 업로드 중...")
                video_id = upload_video(
                    video_path=self.video_path,
                    title=title,
                    description=description,
                    tags=tags,
                    privacy_status=privacy
                )
                self.status_label.setText(f"업로드 완료! https://www.youtube.com/watch?v={video_id}")
                QMessageBox.information(self, "성공", f"YouTube 업로드가 완료되었습니다!\nhttps://www.youtube.com/watch?v={video_id}")
                self.accept()
            except Exception as e:
                self.status_label.setText(f"업로드 실패: {str(e)}")
                QMessageBox.critical(self, "오류", f"업로드 실패: {str(e)}")
                self.upload_button.setEnabled(True)
        
        thread = threading.Thread(target=upload_thread)
        thread.daemon = True
        thread.start()
