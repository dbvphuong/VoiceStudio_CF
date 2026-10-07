"""GUI integration tests for VoiceStudio_CF."""

from __future__ import annotations

import os
from pathlib import Path
import time

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QMessageBox
import pytest

from voicestudio_cf.app.domain import QueueTask, TaskStatus, TextChunk, VoiceTemplate
from voicestudio_cf.app.main_window import MainWindow
from voicestudio_cf.tts.mock_backend import MockTTSBackend


def test_main_window_components(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VOICESTUDIO_CF_HOME", str(tmp_path / "app-data"))
    app = QApplication.instance() or QApplication([])

    window = MainWindow()
    assert window.windowTitle().startswith("VoiceStudio_CF")
    assert window.table is not None
    assert window.template_page is not None
    assert window.log_page is not None

    # Test phân trang 50 dòng
    task = QueueTask(
        path=tmp_path / "test.txt",
        template=VoiceTemplate(name="Test", engine="mock"),
    )
    task.chunks = [TextChunk(index=i, text=f"Câu {i}") for i in range(1, 105)]
    window.tasks.append(task)
    window.current_task_id = task.id
    window._refresh_table()

    assert window.table.rowCount() == 50
    assert "Trang 1 / 3" in window.page_label.text()

    window._next_page()
    assert window.table.rowCount() == 50
    assert "Trang 2 / 3" in window.page_label.text()

    window._next_page()
    assert window.table.rowCount() == 4
    assert "Trang 3 / 3" in window.page_label.text()

    window.close()
    app.processEvents()


def test_main_window_run_mock(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("VOICESTUDIO_CF_HOME", str(tmp_path / "app-data-run"))
    monkeypatch.setattr(QMessageBox, "information", lambda *args, **kwargs: None)
    monkeypatch.setattr(QMessageBox, "warning", lambda *args, **kwargs: None)

    app = QApplication.instance() or QApplication([])
    window = MainWindow()

    txt_file = tmp_path / "sample.txt"
    txt_file.write_text("Xin chào, đây là đoạn văn bản chạy thử nghiệm GUI.", encoding="utf-8")

    task = QueueTask(
        path=txt_file,
        template=VoiceTemplate(name="TestMock", engine="mock"),
    )
    window.tasks.append(task)
    window._engine_factory = lambda _eng, _settings, _cb: MockTTSBackend()

    window._start_run()
    deadline = time.monotonic() + 10
    while window.run_thread is not None and time.monotonic() < deadline:
        QTest.qWait(50)

    assert window.run_thread is None
    assert task.status == TaskStatus.SUCCESS
    assert Path(task.output_path).is_file()

    window.close()
    app.processEvents()
