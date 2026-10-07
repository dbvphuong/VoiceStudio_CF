"""TTS Backend Registry & Factory theo kiến trúc VoiceStudio."""

from __future__ import annotations

from typing import Type

from .base import TTSBackend
from .omnivoice_backend import OmniVoiceBackend
from .sherpa_backend import SherpaOnnxBackend
from .mock_backend import MockTTSBackend

_BACKENDS: dict[str, Type[TTSBackend]] = {
    "omnivoice": OmniVoiceBackend,
    "sherpa-onnx": SherpaOnnxBackend,
    "mock": MockTTSBackend,
}


def register_backend(backend_cls: Type[TTSBackend]) -> None:
    """Đăng ký thêm một TTS backend mới."""
    _BACKENDS[backend_cls.id] = backend_cls


def get_backend_class(backend_id: str) -> Type[TTSBackend]:
    """Lấy class backend theo id. Mặc định fallback về OmniVoiceBackend."""
    if backend_id in _BACKENDS:
        return _BACKENDS[backend_id]
    return OmniVoiceBackend


def create_backend(backend_id: str) -> TTSBackend:
    """Tạo mới một instance của TTS backend."""
    cls = get_backend_class(backend_id)
    return cls()


def list_backends() -> list[dict[str, str | bool]]:
    """Liệt kê danh sách tất cả các backend đã đăng ký kèm trạng thái."""
    results = []
    for bid, cls in _BACKENDS.items():
        available, reason = cls.is_available()
        results.append({
            "id": bid,
            "display_name": cls.display_name,
            "available": available,
            "reason": reason,
            "supports_voice_clone": cls.supports_voice_clone,
            "supports_voice_design": cls.supports_voice_design,
        })
    return results
