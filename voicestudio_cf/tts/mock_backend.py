"""Mock TTS Backend phục vụ kiểm thử nhanh quy trình hàng chờ và UI."""

from __future__ import annotations

import math
import time
from typing import Any, Callable

import numpy as np

from .base import TTSBackend


class MockTTSBackend(TTSBackend):
    """Engine giả lập để kiểm thử nhanh UI, hàng chờ và xuất MP3 mà không cần GPU."""

    id = "mock"
    display_name = "Chế độ kiểm thử nhanh (Mock Engine · Không cần tải model)"
    supports_voice_clone = True
    supports_voice_design = True

    def __init__(self):
        self._sample_rate = 24000
        self.status_callback: Callable[[str], None] = lambda _msg: None

    @property
    def sample_rate(self) -> int:
        return self._sample_rate

    @property
    def supported_languages(self) -> list[str]:
        return ["Vietnamese", "English", "Auto"]

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        return True, "Sẵn sàng (chế độ kiểm thử)"

    def load(
        self,
        settings: Any,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        if status_callback:
            self.status_callback = status_callback
        self.status_callback("Đang kích hoạt Mock Engine kiểm thử…")
        time.sleep(0.3)
        self.status_callback("Mock Engine sẵn sàng.")

    def generate(self, text: str, template: Any) -> Any:
        # Giả lập thời gian sinh audio thực tế tỷ lệ theo độ dài câu
        duration_sec = max(1.0, min(5.0, len(text.strip()) * 0.04))
        time.sleep(min(1.2, duration_sec * 0.25))

        total_samples = int(self._sample_rate * duration_sec)
        t = np.linspace(0, duration_sec, total_samples, endpoint=False)
        # Sinh âm sắc nhẹ êm tai (tone kết hợp 330Hz và 440Hz)
        audio = (0.2 * np.sin(2 * np.pi * 330 * t) + 0.15 * np.sin(2 * np.pi * 440 * t)).astype(np.float32)
        return audio

    def unload(self) -> None:
        pass
