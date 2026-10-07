"""Persistent settings, templates, and completed-task history for VoiceStudio_CF."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from .domain import AppSettings, VoiceMode, VoiceTemplate


def _atomic_json_write(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    os.replace(temporary, path)


class SettingsStore:
    def __init__(self, path: Path, defaults: AppSettings):
        self.path = path
        self.defaults = defaults

    def load(self) -> AppSettings:
        if not self.path.exists():
            self.save(self.defaults)
            return self.defaults
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            loaded = AppSettings.from_dict(data)
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            return self.defaults
        return loaded

    def save(self, settings: AppSettings) -> None:
        _atomic_json_write(self.path, asdict(settings))


class TemplateStore:
    def __init__(self, path: Path):
        self.path = path

    def load(self) -> list[VoiceTemplate]:
        if not self.path.exists():
            templates = default_templates()
            self.save(templates)
            return templates
        try:
            items = json.loads(self.path.read_text(encoding="utf-8"))
            templates = [VoiceTemplate.from_dict(item) for item in items]
        except (OSError, TypeError, ValueError, json.JSONDecodeError):
            templates = default_templates()
        return templates or default_templates()

    def save(self, templates: Iterable[VoiceTemplate]) -> None:
        _atomic_json_write(self.path, [asdict(item) for item in templates])

    def restore_defaults(self) -> list[VoiceTemplate]:
        templates = default_templates()
        self.save(templates)
        return templates


class HistoryStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS completed_tasks (
                    task_key TEXT PRIMARY KEY,
                    source_path TEXT NOT NULL,
                    output_path TEXT NOT NULL,
                    completed_at TEXT NOT NULL
                )
                """
            )

    def find_valid_output(self, task_key: str) -> Path | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT output_path FROM completed_tasks WHERE task_key = ?",
                (task_key,),
            ).fetchone()
        if not row:
            return None
        output = Path(row["output_path"])
        if output.is_file():
            return output
        self.remove(task_key)
        return None

    def record(
        self, task_key: str, source_path: Path, output_path: Path
    ) -> None:
        completed_at = datetime.now(timezone.utc).isoformat()
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO completed_tasks(
                    task_key, source_path, output_path, completed_at
                ) VALUES (?, ?, ?, ?)
                ON CONFLICT(task_key) DO UPDATE SET
                    source_path=excluded.source_path,
                    output_path=excluded.output_path,
                    completed_at=excluded.completed_at
                """,
                (task_key, str(source_path), str(output_path), completed_at),
            )

    def remove(self, task_key: str) -> None:
        with self._connect() as connection:
            connection.execute(
                "DELETE FROM completed_tasks WHERE task_key = ?", (task_key,)
            )

    def clear(self) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM completed_tasks")


def default_templates() -> list[VoiceTemplate]:
    # Kiểm tra xem có file audio mẫu trong thư mục template_voice của project không
    project_dir = Path(__file__).resolve().parent.parent.parent
    sample_audio = project_dir / "template_voice" / "Frederick Surrey.mp3"
    sample_text_file = project_dir / "template_voice" / "Frederick Surrey.txt"
    sample_audio_str = str(sample_audio) if sample_audio.exists() else ""
    sample_text_str = sample_text_file.read_text(encoding="utf-8").strip() if sample_text_file.exists() else ""

    templates = [
        VoiceTemplate(
            id="builtin-clone-surrey",
            name="Clone Giọng Surrey (Mẫu)",
            description="Mẫu clone giọng chuẩn tiếng Anh / Đa ngữ trầm ấm, ổn định cao.",
            engine="omnivoice",
            mode=VoiceMode.CLONE.value,
            language="Vietnamese",
            speed=1.0,
            num_step=32,
            ref_audio=sample_audio_str,
            ref_text=sample_text_str,
            builtin=True,
        ),
        VoiceTemplate(
            id="builtin-horror",
            name="Kể chuyện kinh dị",
            description="Giọng thì thầm, âm vực thấp, huyền bí; có thể đổi sang Clone để ổn định hơn.",
            engine="omnivoice",
            mode=VoiceMode.DESIGN.value,
            language="Vietnamese",
            speed=0.92,
            num_step=32,
            gender="male",
            age="middle-aged",
            pitch="low pitch",
            style="whisper",
            builtin=True,
        ),
        VoiceTemplate(
            id="builtin-gentle",
            name="Kể chuyện nhẹ nhàng",
            description="Giọng nữ trẻ, phong cách mềm mại, tốc độ vừa phải.",
            engine="omnivoice",
            mode=VoiceMode.DESIGN.value,
            language="Vietnamese",
            speed=0.95,
            num_step=32,
            gender="female",
            age="young adult",
            pitch="moderate pitch",
            builtin=True,
        ),
        VoiceTemplate(
            id="builtin-normal",
            name="Đọc truyện thông thường",
            description="Cấu hình giọng tự động cân bằng cho nội dung đọc sách, truyện thông thường.",
            engine="omnivoice",
            mode=VoiceMode.AUTO.value,
            language="Vietnamese",
            speed=1.0,
            num_step=32,
            builtin=True,
        ),
        VoiceTemplate(
            id="builtin-news",
            name="Tin tức rõ ràng",
            description="Nhịp rõ ràng, đĩnh đạc, tốc độ nhanh hơn một chút.",
            engine="omnivoice",
            mode=VoiceMode.DESIGN.value,
            language="Vietnamese",
            speed=1.05,
            num_step=32,
            gender="male",
            age="middle-aged",
            pitch="moderate pitch",
            builtin=True,
        ),
        VoiceTemplate(
            id="builtin-draft",
            name="Bản nháp nhanh (16 bước)",
            description="16 bước khuếch tán để nghe thử nghiệm nhanh chóng.",
            engine="omnivoice",
            mode=VoiceMode.AUTO.value,
            language="Vietnamese",
            speed=1.0,
            num_step=16,
            builtin=True,
        ),
        VoiceTemplate(
            id="builtin-mock-test",
            name="Kiểm thử nhanh (Mock)",
            description="Dùng Mock Engine để test nhanh quy trình chia câu & xuất file MP3 tức thì.",
            engine="mock",
            mode=VoiceMode.AUTO.value,
            language="Vietnamese",
            speed=1.0,
            num_step=16,
            builtin=True,
        ),
    ]
    return templates
