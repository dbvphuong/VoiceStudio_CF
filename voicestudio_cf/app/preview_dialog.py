"""Preview dialog to test voice templates quickly."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from .domain import AppSettings, VoiceTemplate
from .run_worker import PreviewWorker


class PreviewDialog(QDialog):
    def __init__(
        self,
        engine_factory,
        settings: AppSettings,
        templates: list[VoiceTemplate],
        current_template_id: str | None = None,
        preview_dir: Path | None = None,
        parent=None,
    ):
        super().__init__(parent)
        self.engine_factory = engine_factory
        self.settings = settings
        self.templates = templates
        self.preview_dir = preview_dir or (Path.home() / ".voicestudio-cf" / "preview")
        self.preview_dir.mkdir(parents=True, exist_ok=True)
        self.output_audio: Path | None = None

        self.preview_thread: QThread | None = None
        self.preview_worker: PreviewWorker | None = None

        self.setWindowTitle("Nghe thử giọng · VoiceStudio_CF")
        self.setMinimumSize(540, 420)
        self._build_ui(current_template_id)

    def _build_ui(self, current_template_id: str | None) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        header = QLabel("Nghe thử chất giọng của Template")
        header.setObjectName("CardTitle")
        layout.addWidget(header)

        # Chọn template
        tpl_layout = QHBoxLayout()
        tpl_layout.addWidget(QLabel("Chọn Template:"))
        self.template_combo = QComboBox()
        selected_idx = 0
        for i, t in enumerate(self.templates):
            self.template_combo.addItem(t.name, t.id)
            if t.id == current_template_id:
                selected_idx = i
        self.template_combo.setCurrentIndex(selected_idx)
        tpl_layout.addWidget(self.template_combo, 1)
        layout.addLayout(tpl_layout)

        # Nhập văn bản thử nghiệm
        layout.addWidget(QLabel("Nội dung đọc thử:"))
        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("Nhập câu ngắn bạn muốn nghe thử (khoảng 1-3 câu)…")
        self.text_edit.setPlainText("Xin chào, đây là giọng đọc thử nghiệm chất lượng cao từ VoiceStudio CF.")
        layout.addWidget(self.text_edit, 1)

        # Trạng thái & thanh tiến trình
        self.status_label = QLabel("Sẵn sàng nghe thử.")
        self.status_label.setProperty("muted", True)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)

        # Nút bấm
        btn_layout = QHBoxLayout()
        self.play_button = QPushButton("▶ Phát lại audio")
        self.play_button.setEnabled(False)
        self.play_button.clicked.connect(self._play_audio)

        self.generate_button = QPushButton("Tạo audio nghe thử")
        self.generate_button.setProperty("primary", True)
        self.generate_button.clicked.connect(self._generate_preview)

        close_button = QPushButton("Đóng")
        close_button.clicked.connect(self.close)

        btn_layout.addWidget(self.play_button)
        btn_layout.addStretch(1)
        btn_layout.addWidget(self.generate_button)
        btn_layout.addWidget(close_button)
        layout.addLayout(btn_layout)

    def _generate_preview(self) -> None:
        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Lỗi", "Vui lòng nhập nội dung muốn nghe thử.")
            return

        template_id = self.template_combo.currentData()
        template = next((t for t in self.templates if t.id == template_id), None)
        if not template:
            return

        self.generate_button.setEnabled(False)
        self.play_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Đang khởi tạo…")

        output_path = self.preview_dir / "preview_sample.wav"
        output_path.unlink(missing_ok=True)

        engine = self.engine_factory(template.engine, self.settings, lambda msg: self.status_label.setText(msg))

        self.preview_thread = QThread(self)
        self.preview_worker = PreviewWorker(engine, text, template, output_path)
        self.preview_worker.moveToThread(self.preview_thread)

        self.preview_thread.started.connect(self.preview_worker.run)
        self.preview_worker.model_status.connect(self.status_label.setText)
        self.preview_worker.finished.connect(self._on_preview_finished)
        self.preview_worker.failed.connect(self._on_preview_failed)
        self.preview_thread.start()

    def _on_preview_finished(self, out_path_str: str) -> None:
        self.output_audio = Path(out_path_str)
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.play_button.setEnabled(True)
        self.status_label.setText("Đã tạo thành công! Đang phát âm thanh…")
        self._clean_thread()
        self._play_audio()

    def _on_preview_failed(self, error_msg: str) -> None:
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.status_label.setText(f"Lỗi: {error_msg}")
        self._clean_thread()
        QMessageBox.critical(self, "Lỗi tạo audio", f"Không thể tạo audio: {error_msg}")

    def _play_audio(self) -> None:
        if self.output_audio and self.output_audio.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.output_audio.resolve())))

    def _clean_thread(self) -> None:
        if self.preview_thread is not None:
            self.preview_thread.quit()
            self.preview_thread.wait(2000)
            self.preview_thread = None
            self.preview_worker = None
