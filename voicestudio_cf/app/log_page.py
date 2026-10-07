"""Realtime session log viewer for VoiceStudio_CF."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class LogPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.entries: list[tuple[str, int]] = []
        self.current_path: Path | None = None
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Log realtime")
        title.setObjectName("PageTitle")
        root.addWidget(title)

        toolbar = QHBoxLayout()
        self.path_label = QLabel("Chưa có phiên chạy")
        self.path_label.setProperty("muted", True)
        self.filter = QComboBox()
        self.filter.addItem("Tất cả", 0)
        self.filter.addItem("Thông tin", 20)
        self.filter.addItem("Cảnh báo", 30)
        self.filter.addItem("Lỗi", 40)
        self.filter.currentIndexChanged.connect(self._render)
        copy_button = QPushButton("Sao chép")
        copy_button.clicked.connect(self._copy)
        open_button = QPushButton("Mở file log")
        open_button.clicked.connect(self._open_file)
        clear_button = QPushButton("Xóa màn hình")
        clear_button.clicked.connect(self._clear_view)
        toolbar.addWidget(self.path_label, 1)
        toolbar.addWidget(self.filter)
        toolbar.addWidget(copy_button)
        toolbar.addWidget(open_button)
        toolbar.addWidget(clear_button)
        root.addLayout(toolbar)

        self.viewer = QPlainTextEdit()
        self.viewer.setReadOnly(True)
        self.viewer.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.viewer.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; background: #201b30; "
            "color: #eeeaf8; border-radius: 10px; padding: 12px; selection-background-color: #554488;"
        )
        root.addWidget(self.viewer, 1)

    def begin_session(self, path: Path) -> None:
        self.entries.clear()
        self.viewer.clear()
        self.current_path = path
        self.path_label.setText(str(path))

    def append_line(self, line: str, level: int) -> None:
        self.entries.append((line, level))
        threshold = self.filter.currentData()
        if not threshold or level >= threshold:
            self.viewer.appendPlainText(line)
            bar = self.viewer.verticalScrollBar()
            bar.setValue(bar.maximum())

    def _render(self, *_args) -> None:
        threshold = self.filter.currentData()
        lines = [
            line for line, level in self.entries if not threshold or level >= threshold
        ]
        self.viewer.setPlainText("\n".join(lines))
        bar = self.viewer.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _copy(self) -> None:
        QApplication.clipboard().setText(self.viewer.toPlainText())

    def _open_file(self) -> None:
        if self.current_path and self.current_path.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.current_path)))

    def _clear_view(self) -> None:
        self.entries.clear()
        self.viewer.clear()
