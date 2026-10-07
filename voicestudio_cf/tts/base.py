"""Base protocol and abstractions for VoiceStudio TTS engines."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Callable


class TTSBackend(ABC):
    """Giao diện chuẩn cho tất cả các engine TTS trong VoiceStudio_CF."""

    id: str = "base"
    display_name: str = "Base TTS Engine"
    supports_voice_clone: bool = False
    supports_voice_design: bool = False

    @property
    @abstractmethod
    def sample_rate(self) -> int:
        """Tần số lấy mẫu đầu ra (Hz) của audio sinh ra."""
        ...

    @property
    @abstractmethod
    def supported_languages(self) -> list[str]:
        """Danh sách các ngôn ngữ được hỗ trợ."""
        ...

    @classmethod
    @abstractmethod
    def is_available(cls) -> tuple[bool, str]:
        """Kiểm tra engine có khả dụng trong môi trường hiện tại không.
        
        Trả về (True, 'ready') hoặc (False, 'nguyên nhân thiếu dependency/model...').
        """
        ...

    @abstractmethod
    def load(
        self,
        settings: Any,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        """Nạp model vào RAM/VRAM khi cần thiết."""
        ...

    @abstractmethod
    def generate(self, text: str, template: Any) -> Any:
        """Sinh mảng âm thanh (1D audio tensor hoặc numpy array) từ văn bản."""
        ...

    def unload(self) -> None:
        """Giải phóng tài nguyên và VRAM."""
        pass
