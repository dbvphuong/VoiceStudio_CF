"""Test suite for VoiceStudio_CF."""

from __future__ import annotations

import logging
from pathlib import Path

import pytest

from voicestudio_cf.app.domain import AppSettings, QueueTask, VoiceMode, VoiceTemplate
from voicestudio_cf.app.paths import AppPaths
from voicestudio_cf.app.processor import QueueProcessor
from voicestudio_cf.app.storage import HistoryStore, SettingsStore, TemplateStore
from voicestudio_cf.app.text_processing import read_text_file, split_text
from voicestudio_cf.tts import MockTTSBackend, list_backends


def test_list_backends():
    backends = list_backends()
    assert len(backends) >= 2
    ids = [b["id"] for b in backends]
    assert "omnivoice" in ids
    assert "mock" in ids


def test_text_split():
    text = "Câu thứ nhất. Câu thứ hai! Câu thứ ba? Đây là một đoạn văn dài hơn một chút để kiểm tra chia câu và ngữ nghĩa hoàn chỉnh của bộ chia văn bản."
    chunks = split_text(text, max_chars=120)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 130


def test_storage(tmp_path: Path):
    settings_file = tmp_path / "settings.json"
    tpl_file = tmp_path / "templates.json"
    db_file = tmp_path / "history.db"

    # Settings
    s_store = SettingsStore(settings_file, AppSettings())
    s = s_store.load()
    assert s.model_source == "k2-fsa/OmniVoice"
    s.max_chunk_chars = 500
    s_store.save(s)
    s2 = s_store.load()
    assert s2.max_chunk_chars == 500

    # Templates
    t_store = TemplateStore(tpl_file)
    templates = t_store.load()
    assert len(templates) > 0

    # History
    h_store = HistoryStore(db_file)
    src = tmp_path / "sample.txt"
    out = tmp_path / "sample.mp3"
    src.write_text("Hello", encoding="utf-8")
    out.write_text("dummy", encoding="utf-8")
    h_store.record("task_123", src, out)
    assert h_store.find_valid_output("task_123") == out


def test_queue_processor_end_to_end(tmp_path: Path):
    txt_file = tmp_path / "test_story.txt"
    txt_file.write_text(
        "Ngày xửa ngày xưa, tại một vùng đất xa xôi có một vương quốc thanh bình.\n\n"
        "Mọi người ở đó sống vô cùng hạnh phúc và ấm no.",
        encoding="utf-8",
    )

    settings = AppSettings(
        output_dir=str(tmp_path),
        skip_completed=False,
        max_chunk_chars=500,
        pause_between_chunks_ms=100,
    )
    history = HistoryStore(tmp_path / "history.db")
    logger = logging.getLogger("test_voicestudio")

    def factory(engine_id, _settings, _cb):
        return MockTTSBackend()

    processor = QueueProcessor(
        settings=settings,
        history=history,
        logger=logger,
        engine_factory=factory,
    )

    template = VoiceTemplate(
        name="Test Template",
        engine="mock",
        mode=VoiceMode.AUTO.value,
    )
    task = QueueTask(path=txt_file, template=template)

    result = processor.run([task])
    assert result["success"] == 1
    assert result["errors"] == 0

    expected_mp3 = tmp_path / "test_story.mp3"
    assert expected_mp3.is_file()
    assert expected_mp3.stat().st_size > 1000
