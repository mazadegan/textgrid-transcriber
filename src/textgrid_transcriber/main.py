import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QCheckBox,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from textgrid_transcriber.ffmpeg import get_ffmpeg_path


AUDIO_FILTER = "Audio Files (*.mp3 *.wav *.flac *.mpg *.mpeg *.mp4 *.m4a *.aac *.ogg);;All Files (*)"
TEXTGRID_FILTER = "TextGrid Files (*.TextGrid *.textgrid);;All Files (*)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TextGrid Transcriber")

        # --- Header
        title = QLabel("TextGrid Transcriber")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)

        subtitle = QLabel("Select an audio file and its TextGrid to split and transcribe.")
        subtitle.setStyleSheet("color: rgba(0,0,0,0.65);")  # subtle; works OK on light themes
        subtitle.setWordWrap(True)

        # --- Inputs
        self.audio_path = QLineEdit()
        self.audio_path.setPlaceholderText("Audio file (mp3/wav/flac/...)")

        self.textgrid_path = QLineEdit()
        self.textgrid_path.setPlaceholderText("TextGrid file (.TextGrid)")

        audio_browse = QPushButton("Browse…")
        textgrid_browse = QPushButton("Browse…")
        audio_browse.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        textgrid_browse.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

        # Make browse buttons feel consistent
        audio_browse.setFixedWidth(96)
        textgrid_browse.setFixedWidth(96)

        self.audio_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.textgrid_path.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        audio_row = QHBoxLayout()
        audio_row.addWidget(self.audio_path, 1)
        audio_row.addWidget(audio_browse, 0)

        textgrid_row = QHBoxLayout()
        textgrid_row.addWidget(self.textgrid_path, 1)
        textgrid_row.addWidget(textgrid_browse, 0)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.addRow("Audio", audio_row)
        form.addRow("TextGrid", textgrid_row)

        self.batch_asr_checkbox = QCheckBox("Enable batch ASR transcription")
        self.batch_asr_checkbox.setStatusTip(
            "Run speech recognition on all segments after splitting. Takes longer for large files."
        )

        # --- Primary action
        self.split_btn = QPushButton("Split")
        self.split_btn.setEnabled(False)
        self.split_btn.setDefault(True)  # Enter triggers it

        self.hint = QLabel("Choose both files to continue.")
        self.hint.setStyleSheet("color: rgba(0,0,0,0.65);")

        actions = QHBoxLayout()
        actions.addWidget(self.hint)
        actions.addStretch(1)
        actions.addWidget(self.split_btn)

        # --- Layout root
        root = QVBoxLayout()
        root.setContentsMargins(20, 18, 20, 18)
        root.setSpacing(14)
        root.addWidget(title)
        root.addWidget(subtitle)
        root.addSpacing(6)
        root.addLayout(form)
        root.addWidget(self.batch_asr_checkbox)
        root.addStretch(1)
        root.addLayout(actions)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        # Status bar (useful later for progress / ffmpeg messages)
        self.setStatusBar(QStatusBar())

        self.check_ffmpeg()

        # --- Connections
        audio_browse.clicked.connect(self.pick_audio_file)
        textgrid_browse.clicked.connect(self.pick_textgrid_file)
        self.audio_path.textChanged.connect(self.update_state)
        self.textgrid_path.textChanged.connect(self.update_state)

        self.resize(620, 240)

    def check_ffmpeg(self):
        self.ffmpeg_ok = False
        try:
            ffmpeg_path = get_ffmpeg_path()
        except Exception:
            self.statusBar().showMessage("ffmpeg not available (missing imageio-ffmpeg binary).")
            self.update_state()
            return
        if not ffmpeg_path.exists():
            self.statusBar().showMessage(f"ffmpeg not found at {ffmpeg_path}")
            self.update_state()
            return
        self.ffmpeg_ok = True
        self.statusBar().showMessage(f"ffmpeg found at {ffmpeg_path}", 5000)
        self.update_state()

    def pick_audio_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select audio file", "", AUDIO_FILTER)
        if file_path:
            self.audio_path.setText(file_path)

    def pick_textgrid_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Select TextGrid file", "", TEXTGRID_FILTER)
        if file_path:
            self.textgrid_path.setText(file_path)

    def update_state(self):
        a = Path(self.audio_path.text().strip())
        t = Path(self.textgrid_path.text().strip())

        ok = a.is_file() and t.is_file() and getattr(self, "ffmpeg_ok", False)
        self.split_btn.setEnabled(ok)

        if ok:
            self.hint.setText("Ready.")
        else:
            if not getattr(self, "ffmpeg_ok", False):
                self.hint.setText("ffmpeg is required to split audio.")
            else:
                self.hint.setText("Choose both files to continue.")


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
