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
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


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

        # Make browse buttons feel consistent
        audio_browse.setFixedWidth(96)
        textgrid_browse.setFixedWidth(96)

        audio_row = QHBoxLayout()
        audio_row.addWidget(self.audio_path)
        audio_row.addWidget(audio_browse)

        textgrid_row = QHBoxLayout()
        textgrid_row.addWidget(self.textgrid_path)
        textgrid_row.addWidget(textgrid_browse)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft)
        form.setFormAlignment(Qt.AlignTop)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(10)
        form.addRow("Audio", audio_row)
        form.addRow("TextGrid", textgrid_row)

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
        root.addStretch(1)
        root.addLayout(actions)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        # Status bar (useful later for progress / ffmpeg messages)
        self.setStatusBar(QStatusBar())

        # --- Connections
        audio_browse.clicked.connect(self.pick_audio_file)
        textgrid_browse.clicked.connect(self.pick_textgrid_file)
        self.audio_path.textChanged.connect(self.update_state)
        self.textgrid_path.textChanged.connect(self.update_state)

        self.resize(620, 240)

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

        ok = a.is_file() and t.is_file()
        self.split_btn.setEnabled(ok)

        if ok:
            self.hint.setText("Ready.")
            self.statusBar().showMessage("Ready to split.", 3000)
        else:
            self.hint.setText("Choose both files to continue.")
            self.statusBar().clearMessage()


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
