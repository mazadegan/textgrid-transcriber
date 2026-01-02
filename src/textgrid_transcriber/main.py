import logging
import sys
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot, QUrl
from PySide6.QtGui import QFont
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
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
    QComboBox,
    QGroupBox,
    QHeaderView,
    QPlainTextEdit,
    QSlider,
    QTableView,
    QMessageBox,
    QDialog,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from textgrid_transcriber.ffmpeg import get_ffmpeg_path
from textgrid_transcriber.segments_model import (
    STATUS_EMPTY,
    STATUS_UNVERIFIED,
    STATUS_VERIFIED,
    SegmentFilterProxy,
    SegmentTableModel,
    segment_status,
)
from textgrid_transcriber.project import PROJECT_FILENAME, PROJECT_VERSION, Project, Segment, load_project, save_project
from textgrid_transcriber.splitter import split_audio_with_ffmpeg


AUDIO_FILTER = "Audio Files (*.mp3 *.wav *.flac *.mpg *.mpeg *.mp4 *.m4a *.aac *.ogg);;All Files (*)"
TEXTGRID_FILTER = "TextGrid Files (*.TextGrid *.textgrid);;All Files (*)"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TextGrid Transcriber")
        self.current_project_path: Path | None = None
        self.current_output_dir: Path | None = None
        self.current_segments: list[Segment] = []

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

        self.batch_asr_button = QPushButton("Run batch ASR transcription")
        self.batch_asr_button.setEnabled(False)

        self.segments_header = QLabel("Segments (0 total, 0 verified)")
        self.segment_model = SegmentTableModel()
        self.segment_proxy = SegmentFilterProxy()
        self.segment_proxy.setSourceModel(self.segment_model)
        self.segment_proxy.setSortCaseSensitivity(Qt.CaseInsensitive)

        self.filter_tier = QComboBox()
        self.filter_status = QComboBox()
        self.filter_sort = QComboBox()
        self.filter_tier.addItem("All")
        self.filter_status.addItems(["All", STATUS_EMPTY, STATUS_UNVERIFIED, STATUS_VERIFIED])
        self.filter_sort.addItems(["Status", "Duration", "Name"])

        filters_row = QHBoxLayout()
        filters_row.addWidget(QLabel("Tier"))
        filters_row.addWidget(self.filter_tier)
        filters_row.addWidget(QLabel("Status"))
        filters_row.addWidget(self.filter_status)
        filters_row.addWidget(QLabel("Sort"))
        filters_row.addWidget(self.filter_sort)
        filters_row.addStretch(1)
        filters_row.addWidget(self.batch_asr_button)

        self.segments_table = QTableView()
        self.segments_table.setModel(self.segment_proxy)
        self.segments_table.setSelectionBehavior(QTableView.SelectRows)
        self.segments_table.setSelectionMode(QTableView.SingleSelection)
        self.segments_table.setSortingEnabled(True)
        self.segments_table.horizontalHeader().setStretchLastSection(True)
        self.segments_table.horizontalHeader().setSectionResizeMode(
            SegmentTableModel.COLUMN_FILE, QHeaderView.Stretch
        )
        self.segments_table.horizontalHeader().setSectionResizeMode(
            SegmentTableModel.COLUMN_STATUS, QHeaderView.ResizeToContents
        )
        row_height = self.segments_table.verticalHeader().defaultSectionSize()
        header_height = self.segments_table.horizontalHeader().height()
        table_frame = self.segments_table.frameWidth() * 2
        self.segments_table.setMinimumHeight(header_height + (row_height * 3) + table_frame)

        self.segment_details_group = QGroupBox("Selected segment")
        self.segment_details_group.setVisible(False)
        self.segment_file_label = QLabel("No segment selected.")
        self.segment_play_button = QPushButton("Play")
        self.segment_stop_button = QPushButton("Stop")
        self.segment_play_button.setEnabled(False)
        self.segment_stop_button.setEnabled(False)
        self.segment_seek_slider = QSlider(Qt.Horizontal)
        self.segment_seek_slider.setEnabled(False)
        self.segment_seek_slider.setMinimum(0)
        self.segment_seek_slider.setMaximum(0)

        self.transcript_editor = QPlainTextEdit()
        self.transcript_editor.setPlaceholderText("Transcript will appear here.")
        self.transcript_editor.setEnabled(False)
        line_height = self.transcript_editor.fontMetrics().lineSpacing()
        editor_frame = self.transcript_editor.frameWidth() * 2
        self.transcript_editor.setFixedHeight((line_height * 3) + editor_frame + 6)
        self.segment_asr_button = QPushButton("Generate ASR Transcription")
        self.segment_asr_button.setEnabled(False)
        self.segment_verified_checkbox = QCheckBox("Verified")
        self.segment_verified_checkbox.setEnabled(False)

        playback_row = QHBoxLayout()
        playback_row.addWidget(self.segment_file_label, 1)
        playback_row.addWidget(self.segment_play_button)
        playback_row.addWidget(self.segment_stop_button)

        details_layout = QVBoxLayout()
        details_layout.addLayout(playback_row)
        details_layout.addWidget(self.segment_seek_slider)
        details_layout.addWidget(QLabel("Transcript"))
        details_layout.addWidget(self.transcript_editor)
        controls_row = QHBoxLayout()
        controls_row.addWidget(self.segment_asr_button)
        controls_row.addStretch(1)
        controls_row.addWidget(self.segment_verified_checkbox)
        details_layout.addLayout(controls_row)
        self.segment_details_group.setLayout(details_layout)

        segments_group = QGroupBox("Segments")
        segments_layout = QVBoxLayout()
        segments_layout.addWidget(self.segments_header)
        segments_layout.addLayout(filters_row)
        segments_layout.addWidget(self.segments_table)
        segments_layout.addWidget(self.segment_details_group)
        segments_group.setLayout(segments_layout)

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
        root.addLayout(actions)
        root.addWidget(segments_group)
        root.addStretch(1)

        central = QWidget()
        central.setLayout(root)
        self.setCentralWidget(central)

        # Status bar (useful later for progress / ffmpeg messages)
        self.setStatusBar(QStatusBar())
        self._logger = logging.getLogger("textgrid_transcriber")
        if not logging.getLogger().handlers:
            logging.basicConfig(
                filename="textgrid_transcriber.log",
                level=logging.INFO,
                format="%(asctime)s %(levelname)s %(message)s",
            )
        self.log_path = Path("textgrid_transcriber.log").resolve()

        file_menu = self.menuBar().addMenu("File")
        self.open_project_action = file_menu.addAction("Open Project…")
        self.save_project_action = file_menu.addAction("Save Project")
        self.save_project_as_action = file_menu.addAction("Save Project As…")
        self.save_project_action.setEnabled(False)
        help_menu = self.menuBar().addMenu("Help")
        self.view_log_action = help_menu.addAction("View Log…")

        self.check_ffmpeg()

        # --- Connections
        audio_browse.clicked.connect(self.pick_audio_file)
        textgrid_browse.clicked.connect(self.pick_textgrid_file)
        self.audio_path.textChanged.connect(self.update_state)
        self.textgrid_path.textChanged.connect(self.update_state)
        self.split_btn.clicked.connect(self.split_audio)
        self.open_project_action.triggered.connect(self.open_project)
        self.save_project_action.triggered.connect(self.save_project_file)
        self.save_project_as_action.triggered.connect(self.save_project_as)
        self.view_log_action.triggered.connect(self.open_log_window)
        self.filter_tier.currentTextChanged.connect(self.on_filter_tier_changed)
        self.filter_status.currentTextChanged.connect(self.on_filter_status_changed)
        self.filter_sort.currentTextChanged.connect(self.on_sort_changed)
        self.segments_table.selectionModel().selectionChanged.connect(self.on_segment_selection_changed)
        self.segment_play_button.clicked.connect(self.play_selected_segment)
        self.segment_stop_button.clicked.connect(self.stop_selected_segment)
        self.segment_seek_slider.sliderMoved.connect(self.seek_selected_segment)
        self.segment_seek_slider.sliderReleased.connect(self.on_seek_finished)
        self.transcript_editor.textChanged.connect(self.on_transcript_changed)
        self.segment_verified_checkbox.toggled.connect(self.on_verified_toggled)

        self.resize(620, 620)
        self.segment_proxy.sort(0, Qt.AscendingOrder)

        self._updating_transcript = False
        self.current_segment_row: int | None = None
        self.audio_output = QAudioOutput(self)
        self.player = QMediaPlayer(self)
        self.player.setAudioOutput(self.audio_output)
        self.player.positionChanged.connect(self.on_player_position_changed)
        self.player.durationChanged.connect(self.on_player_duration_changed)

    def check_ffmpeg(self):
        self.ffmpeg_ok = False
        try:
            ffmpeg_path = get_ffmpeg_path()
        except Exception:
            self.show_status("ffmpeg not available (missing imageio-ffmpeg binary).")
            self.update_state()
            return
        if not ffmpeg_path.exists():
            self.show_status(f"ffmpeg not found at {ffmpeg_path}")
            self.update_state()
            return
        self.ffmpeg_ok = True
        self.show_status(f"ffmpeg found at {ffmpeg_path}", 5000)
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

    def split_audio(self):
        if not getattr(self, "ffmpeg_ok", False):
            self.show_status("ffmpeg is required to split audio.")
            return

        audio_path = Path(self.audio_path.text().strip())
        textgrid_path = Path(self.textgrid_path.text().strip())

        if not audio_path.is_file() or not textgrid_path.is_file():
            self.show_status("Select valid audio and TextGrid files.")
            return

        output_dir = audio_path.parent / "splits"
        ffmpeg_path = get_ffmpeg_path()

        project_path = output_dir / PROJECT_FILENAME
        if project_path.exists():
            choice = QMessageBox.warning(
                self,
                "Project already exists",
                "A project file already exists for this audio. Resplitting can overwrite "
                "saved transcripts and status. Do you want to continue?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if choice != QMessageBox.Yes:
                self.show_status("Split canceled.")
                return

        self.split_btn.setEnabled(False)
        self.show_status("Splitting audio...")

        self.worker = SplitWorker(ffmpeg_path, audio_path, textgrid_path, output_dir)
        self.worker_thread = QThread(self)
        self.worker.moveToThread(self.worker_thread)

        self.worker.progress.connect(self.on_split_progress)
        self.worker.finished.connect(self.on_split_finished)
        self.worker.failed.connect(self.on_split_failed)
        self.worker_thread.started.connect(self.worker.run)

        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)

        self.worker_thread.start()

    @Slot(int, int, str)
    def on_split_progress(self, done, total, output_name):
        self.show_status(f"Split {done}/{total}: {output_name}")

    @Slot(str)
    def on_split_failed(self, message):
        self.show_status(f"Split failed: {message}")
        self.update_state()

    @Slot(object)
    def on_split_finished(self, result):
        output_dir = Path(result["output_dir"])
        self.current_output_dir = output_dir
        self.current_segments = result["segments"]

        self.current_project_path = output_dir / PROJECT_FILENAME
        self.save_project_file()
        self.batch_asr_button.setEnabled(True)
        self.show_status(f"Split complete. Files saved to {output_dir}")
        self.populate_segments()
        self.update_state()

    def _build_project(self) -> Project:
        audio_path = Path(self.audio_path.text().strip())
        textgrid_path = Path(self.textgrid_path.text().strip())
        output_dir = self.current_output_dir
        if output_dir is None and audio_path:
            output_dir = audio_path.parent / "splits"

        return Project(
            version=PROJECT_VERSION,
            audio_path=str(audio_path),
            textgrid_path=str(textgrid_path),
            output_dir=str(output_dir) if output_dir else "",
            batch_asr=False,
            segments=self.current_segments,
        )

    def save_project_file(self, show_status=True, force_dialog=False):
        if self.current_project_path is None or force_dialog:
            default_path = PROJECT_FILENAME
            if self.current_project_path is not None:
                default_path = str(self.current_project_path)
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Save project",
                default_path,
                "TextGrid Project (*.json);;All Files (*)",
            )
            if not file_path:
                self.show_status("Save canceled.")
                return
            self.current_project_path = Path(file_path)

        project = self._build_project()
        save_project(self.current_project_path, project)
        self.save_project_action.setEnabled(True)
        if show_status:
            self.show_status(f"Project saved to {self.current_project_path}", 3000)

    def save_project_as(self):
        self.save_project_file(force_dialog=True)

    def open_project(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Open project",
            "",
            "TextGrid Project (*.json);;All Files (*)",
        )
        if not file_path:
            self.show_status("Open project canceled.")
            return

        try:
            project = load_project(Path(file_path))
        except Exception as exc:
            self.show_status(f"Failed to load project: {exc}")
            return

        self.current_project_path = Path(file_path)
        self.current_output_dir = Path(project.output_dir)
        self.current_segments = project.segments

        self.audio_path.setText(project.audio_path)
        self.textgrid_path.setText(project.textgrid_path)

        self.save_project_action.setEnabled(True)
        self.batch_asr_button.setEnabled(True)
        self.show_status(f"Project loaded from {self.current_project_path}", 3000)
        self.populate_segments()
        self.update_state()

    def populate_segments(self):
        self.segment_model.set_segments(self.current_segments)
        self.refresh_filters()
        self.update_segments_header()
        self.clear_segment_details()

    def refresh_filters(self):
        tiers = sorted({segment.tier for segment in self.current_segments})
        current_tier = self.filter_tier.currentText()
        self.filter_tier.blockSignals(True)
        self.filter_tier.clear()
        self.filter_tier.addItem("All")
        for tier in tiers:
            self.filter_tier.addItem(tier)
        if current_tier and current_tier in tiers:
            self.filter_tier.setCurrentText(current_tier)
        else:
            self.filter_tier.setCurrentText("All")
        self.filter_tier.blockSignals(False)

        self.segment_proxy.invalidateFilter()

    def update_segments_header(self):
        total = len(self.current_segments)
        verified = sum(1 for segment in self.current_segments if segment_status(segment) == STATUS_VERIFIED)
        self.segments_header.setText(f"Segments ({total} total, {verified} verified)")

    def on_filter_tier_changed(self, text):
        self.segment_proxy.set_filter_tier(text)
        self.update_segments_header()
        self.show_status(f"Filter tier: {text}")

    def on_filter_status_changed(self, text):
        self.segment_proxy.set_filter_status(text)
        self.update_segments_header()
        self.show_status(f"Filter status: {text}")

    def on_sort_changed(self, text):
        if text == "Duration":
            self.segment_proxy.set_sort_mode(SegmentFilterProxy.SORT_DURATION)
        elif text == "Name":
            self.segment_proxy.set_sort_mode(SegmentFilterProxy.SORT_NAME)
        else:
            self.segment_proxy.set_sort_mode(SegmentFilterProxy.SORT_STATUS)
        self.segment_proxy.sort(0, Qt.AscendingOrder)
        self.show_status(f"Sort: {text}")

    def clear_segment_details(self):
        self.current_segment_row = None
        self.segment_details_group.setVisible(False)
        self.segment_file_label.setText("No segment selected.")
        self.segment_play_button.setEnabled(False)
        self.segment_stop_button.setEnabled(False)
        self.segment_seek_slider.setEnabled(False)
        self.segment_seek_slider.setValue(0)
        self.transcript_editor.setEnabled(False)
        self.segment_asr_button.setEnabled(False)
        self.segment_verified_checkbox.setEnabled(False)
        self.segment_verified_checkbox.setChecked(False)
        self._updating_transcript = True
        self.transcript_editor.setPlainText("")
        self._updating_transcript = False

    def on_segment_selection_changed(self, *_):
        selection = self.segments_table.selectionModel().selectedRows()
        if not selection:
            self.clear_segment_details()
            self.show_status("Segment selection cleared.")
            return

        proxy_index = selection[0]
        source_index = self.segment_proxy.mapToSource(proxy_index)
        segment = self.segment_model.segment_at(source_index.row())

        self.current_segment_row = source_index.row()
        self.segment_file_label.setText(Path(segment.path).name)
        self.segment_details_group.setVisible(True)
        self.segment_play_button.setEnabled(True)
        self.segment_stop_button.setEnabled(True)
        self.segment_seek_slider.setEnabled(True)
        self.transcript_editor.setEnabled(True)
        self.segment_asr_button.setEnabled(True)
        self.segment_verified_checkbox.setEnabled(True)

        self._updating_transcript = True
        self.transcript_editor.setPlainText(segment.transcript)
        self.segment_verified_checkbox.setChecked(segment.verified)
        self._updating_transcript = False

        self.player.setSource(QUrl.fromLocalFile(segment.path))
        self.show_status(f"Selected segment: {Path(segment.path).name}")

    def play_selected_segment(self):
        if self.current_segment_row is None:
            return
        self.player.play()
        self.show_status("Playback started.")

    def stop_selected_segment(self):
        self.player.stop()
        self.show_status("Playback stopped.")

    def seek_selected_segment(self, position):
        self.player.setPosition(position)

    def on_seek_finished(self):
        position = self.segment_seek_slider.value()
        self.show_status(f"Seek to {position} ms.")

    def on_player_position_changed(self, position):
        if not self.segment_seek_slider.isSliderDown():
            self.segment_seek_slider.setValue(position)

    def on_player_duration_changed(self, duration):
        self.segment_seek_slider.setMaximum(duration)

    def on_transcript_changed(self):
        if self._updating_transcript or self.current_segment_row is None:
            return
        segment = self.segment_model.segment_at(self.current_segment_row)
        segment.transcript = self.transcript_editor.toPlainText()
        self.segment_model.update_segment(self.current_segment_row)
        self.segment_proxy.invalidate()
        self.segment_proxy.sort(0, Qt.AscendingOrder)
        self.update_segments_header()
        self.show_status("Transcript updated.")
        if self.current_project_path is not None:
            self.save_project_file(show_status=False)
            self.show_status("Transcript saved.")

    def on_verified_toggled(self, checked):
        if self._updating_transcript or self.current_segment_row is None:
            return
        segment = self.segment_model.segment_at(self.current_segment_row)
        segment.verified = checked
        self.segment_model.update_segment(self.current_segment_row)
        self.segment_proxy.invalidate()
        self.segment_proxy.sort(0, Qt.AscendingOrder)
        self.update_segments_header()
        self.show_status(f"Verified set to {checked}.")
        if self.current_project_path is not None:
            self.save_project_file(show_status=False)
            self.show_status("Verification saved.")

    def show_status(self, message: str, timeout: int | None = 3000):
        if timeout is None:
            self.statusBar().showMessage(message)
        else:
            self.statusBar().showMessage(message, timeout)
        self._logger.info(message)

    def open_log_window(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Application Log")
        dialog.resize(720, 420)

        log_view = QPlainTextEdit()
        log_view.setReadOnly(True)
        if self.log_path.exists():
            log_view.setPlainText(self.log_path.read_text(encoding="utf-8"))
        else:
            log_view.setPlainText("Log file not found.")

        layout = QVBoxLayout()
        layout.addWidget(log_view)
        dialog.setLayout(layout)
        dialog.exec()


class SplitWorker(QObject):
    progress = Signal(int, int, str)
    finished = Signal(object)
    failed = Signal(str)

    def __init__(self, ffmpeg_path: Path, audio_path: Path, textgrid_path: Path, output_dir: Path):
        super().__init__()
        self.ffmpeg_path = ffmpeg_path
        self.audio_path = audio_path
        self.textgrid_path = textgrid_path
        self.output_dir = output_dir

    @Slot()
    def run(self):
        try:
            output_dir, segments = split_audio_with_ffmpeg(
                self.ffmpeg_path,
                self.audio_path,
                self.textgrid_path,
                self.output_dir,
                progress_cb=self._on_progress,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            return

        self.finished.emit({"output_dir": str(output_dir), "segments": segments})

    def _on_progress(self, done, total, output_path):
        self.progress.emit(done, total, output_path.name)


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
