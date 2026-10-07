"""System settings dialog for VoiceStudio_CF."""

from __future__ import annotations

import importlib.util
import shutil
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from .domain import AppSettings
from .storage import HistoryStore


class PathPicker(QWidget):
    def __init__(self, value: str = "", parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        self.edit = QLineEdit(value)
        button = QPushButton("Chọn…")
        button.clicked.connect(self._browse)
        layout.addWidget(self.edit, 1)
        layout.addWidget(button)

    def _browse(self) -> None:
        selected = QFileDialog.getExistingDirectory(
            self, "Chọn thư mục", self.edit.text() or str(Path.home())
        )
        if selected:
            self.edit.setText(selected)

    def text(self) -> str:
        return self.edit.text().strip()


class SettingsDialog(QDialog):
    settings_saved = Signal(object)

    def __init__(
        self, settings: AppSettings, history: HistoryStore, parent=None
    ):
        super().__init__(parent)
        self.settings = settings
        self.history = history
        self.setWindowTitle("Cài đặt hệ thống · VoiceStudio_CF")
        self.setMinimumSize(680, 600)

        root = QVBoxLayout(self)
        tabs = QTabWidget()
        tabs.addTab(self._build_model_tab(), "Model & thiết bị")
        tabs.addTab(self._build_performance_tab(), "Hiệu năng")
        tabs.addTab(self._build_storage_tab(), "Đầu ra & log")
        root.addWidget(tabs)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save
            | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.button(QDialogButtonBox.StandardButton.Save).setText("Lưu cài đặt")
        buttons.button(QDialogButtonBox.StandardButton.Cancel).setText("Hủy")
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _build_model_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)

        self.default_engine = QComboBox()
        self.default_engine.addItem("VoiceStudio OmniVoice (Mặc định · 600+ ngôn ngữ)", "omnivoice")
        self.default_engine.addItem("Sherpa-ONNX (Offline · Chạy CPU siêu nhẹ)", "sherpa-onnx")
        self.default_engine.addItem("Chế độ kiểm thử nhanh (Mock Engine)", "mock")
        index = self.default_engine.findData(self.settings.default_engine)
        if index >= 0:
            self.default_engine.setCurrentIndex(index)

        self.model_source = QLineEdit(self.settings.model_source)
        self.device = QComboBox()
        self.device.addItems(["auto", "cuda", "cpu", "mps", "xpu"])
        self.device.setCurrentText(self.settings.device)
        self.load_on_start = QCheckBox("Tải model ngay khi mở ứng dụng")
        self.load_on_start.setChecked(self.settings.load_model_on_start)

        note = QLabel(
            "• Chế độ Tự động (auto) sẽ ưu tiên GPU NVIDIA CUDA nếu khả dụng.\n"
            "• Với card đồ họa 4GB VRAM (GTX 1650), VoiceStudio_CF sẽ tự động kích hoạt "
            "tính năng cân bằng VRAM và offload codec sang CPU để tránh tràn bộ nhớ."
        )
        note.setWordWrap(True)
        note.setProperty("muted", True)

        check_button = QPushButton("Kiểm tra môi trường & Phần cứng")
        check_button.clicked.connect(self._check_environment)
        self.environment_status = QLabel("")
        self.environment_status.setWordWrap(True)
        self.environment_status.setTextFormat(Qt.TextFormat.RichText)

        form.addRow("Engine mặc định", self.default_engine)
        form.addRow("Nguồn model OmniVoice", self.model_source)
        form.addRow("Thiết bị tính toán", self.device)
        form.addRow("", self.load_on_start)
        form.addRow("", note)
        form.addRow("", check_button)
        form.addRow("", self.environment_status)
        return page

    def _build_performance_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.max_chars = QSpinBox()
        self.max_chars.setRange(100, 4000)
        self.max_chars.setSingleStep(50)
        self.max_chars.setValue(self.settings.max_chunk_chars)
        self.max_chars.setSuffix(" ký tự")

        self.prep_workers = QSpinBox()
        self.prep_workers.setRange(1, 16)
        self.prep_workers.setValue(self.settings.preparation_workers)
        self.prep_workers.setSuffix(" luồng")

        self.cpu_threads = QSpinBox()
        self.cpu_threads.setRange(1, 32)
        self.cpu_threads.setValue(self.settings.cpu_threads)
        self.cpu_threads.setSuffix(" luồng")

        self.pause_ms = QSpinBox()
        self.pause_ms.setRange(0, 3000)
        self.pause_ms.setSingleStep(50)
        self.pause_ms.setValue(self.settings.pause_between_chunks_ms)
        self.pause_ms.setSuffix(" ms")

        self.cuda_fraction = QSpinBox()
        self.cuda_fraction.setRange(10, 100)
        self.cuda_fraction.setSingleStep(5)
        self.cuda_fraction.setValue(int(self.settings.cuda_memory_fraction * 100))
        self.cuda_fraction.setSuffix(" %")

        form.addRow("Ký tự tối đa mỗi đoạn", self.max_chars)
        form.addRow("Khoảng lặng giữa các đoạn", self.pause_ms)
        form.addRow("Luồng đọc file đồng thời", self.prep_workers)
        form.addRow("Luồng CPU cho suy luận", self.cpu_threads)
        form.addRow("Giới hạn VRAM GPU", self.cuda_fraction)
        return page

    def _build_storage_tab(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        self.output_picker = PathPicker(self.settings.output_dir)
        self.output_suffix = QLineEdit(self.settings.output_suffix)
        self.output_suffix.setPlaceholderText("Ví dụ: _done hoặc để trống")
        self.log_picker = PathPicker(self.settings.log_dir)
        self.log_days = QSpinBox()
        self.log_days.setRange(1, 90)
        self.log_days.setValue(self.settings.log_retention_days)
        self.log_days.setSuffix(" ngày")

        self.skip_completed = QCheckBox("Bỏ qua nếu file MP3 đích đã tồn tại")
        self.skip_completed.setChecked(self.settings.skip_completed)
        self.auto_open = QCheckBox("Tự động mở thư mục khi xử lý xong tất cả")
        self.auto_open.setChecked(self.settings.auto_open_output)

        clear_history = QPushButton("Xóa bộ nhớ đệm lịch sử đã tạo")
        clear_history.clicked.connect(self._clear_history)

        form.addRow("Thư mục đầu ra mặc định", self.output_picker)
        form.addRow("Hậu tố tên file MP3", self.output_suffix)
        form.addRow("Thư mục lưu log", self.log_picker)
        form.addRow("Thời gian giữ log", self.log_days)
        form.addRow("", self.skip_completed)
        form.addRow("", self.auto_open)
        form.addRow("", clear_history)
        return page

    def _check_environment(self) -> None:
        lines = []
        # Kiểm tra PySide6
        lines.append("• <b>Giao diện:</b> PySide6 đã sẵn sàng")

        # Kiểm tra FFmpeg
        ffmpeg_bin = shutil.which("ffmpeg")
        if ffmpeg_bin:
            lines.append("• <b>Bộ xuất âm thanh:</b> FFmpeg có sẵn trong hệ thống")
        else:
            lines.append("• <b>Bộ xuất âm thanh:</b> <span style='color: #cf2f45;'>Chưa tìm thấy FFmpeg</span>")

        # Kiểm tra PyTorch & CUDA
        torch_spec = importlib.util.find_spec("torch")
        if torch_spec is None:
            lines.append(
                "• <b>Mô hình:</b> <span style='color: #cf2f45;'>Chưa cài PyTorch</span> "
                "(chạy setup_env.bat để cài đặt tự động)"
            )
        else:
            import torch

            lines.append(f"• <b>PyTorch:</b> v{torch.__version__}")
            if torch.cuda.is_available():
                device_name = torch.cuda.get_device_name(0)
                total_mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                lines.append(
                    f"• <b>GPU tăng tốc:</b> <span style='color: #2b7a38;'>{device_name} "
                    f"({total_mem:.1f} GB VRAM, CUDA {torch.version.cuda})</span>"
                )
                if total_mem <= 4.5:
                    lines.append(
                        "  → <i>Đã bật cơ chế VoiceStudio Low-VRAM Guard cho card 4GB!</i>"
                    )
            else:
                lines.append(
                    "• <b>GPU tăng tốc:</b> <span style='color: #a06010;'>Không phát hiện CUDA (đang dùng CPU)</span>"
                )

        # Kiểm tra OmniVoice
        omni_spec = importlib.util.find_spec("omnivoice")
        if omni_spec is not None:
            lines.append("• <b>Động cơ OmniVoice:</b> Đã tích hợp sẵn sàng")
        else:
            lines.append("• <b>Động cơ OmniVoice:</b> Chưa nạp được module")

        # Kiểm tra Sherpa-ONNX
        sherpa_spec = importlib.util.find_spec("sherpa_onnx")
        if sherpa_spec is not None:
            lines.append("• <b>Động cơ Sherpa-ONNX:</b> Sẵn sàng")
        else:
            lines.append("• <b>Động cơ Sherpa-ONNX:</b> Chưa cài đặt (tùy chọn)")

        self.environment_status.setText("<br>".join(lines))

    def _clear_history(self) -> None:
        answer = QMessageBox.question(
            self,
            "Xác nhận",
            "Bạn có chắc chắn muốn xóa toàn bộ bộ nhớ đệm lịch sử đã tạo?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.history.clear()
            QMessageBox.information(self, "Đã xóa", "Đã xóa sạch bộ nhớ đệm lịch sử.")

    def _save(self) -> None:
        suffix = self.output_suffix.text().strip()
        if any(character in suffix for character in '<>:"/\\|?*'):
            QMessageBox.warning(
                self, "Lỗi", "Hậu tố tên file chứa ký tự không hợp lệ."
            )
            return

        updated = replace(
            self.settings,
            default_engine=self.default_engine.currentData(),
            model_source=self.model_source.text().strip() or "k2-fsa/OmniVoice",
            device=self.device.currentText(),
            load_model_on_start=self.load_on_start.isChecked(),
            max_chunk_chars=self.max_chars.value(),
            pause_between_chunks_ms=self.pause_ms.value(),
            preparation_workers=self.prep_workers.value(),
            cpu_threads=self.cpu_threads.value(),
            cuda_memory_fraction=self.cuda_fraction.value() / 100.0,
            output_dir=self.output_picker.text(),
            output_suffix=suffix,
            log_dir=self.log_picker.text(),
            log_retention_days=self.log_days.value(),
            skip_completed=self.skip_completed.isChecked(),
            auto_open_output=self.auto_open.isChecked(),
        )
        self.settings = updated
        self.settings_saved.emit(updated)
        self.accept()
