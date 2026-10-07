"""TTS package for VoiceStudio_CF."""

from .base import TTSBackend
from .omnivoice_backend import OmniVoiceBackend
from .sherpa_backend import SherpaOnnxBackend
from .mock_backend import MockTTSBackend
from .registry import (
    create_backend,
    get_backend_class,
    list_backends,
    register_backend,
)

__all__ = [
    "TTSBackend",
    "OmniVoiceBackend",
    "SherpaOnnxBackend",
    "MockTTSBackend",
    "create_backend",
    "get_backend_class",
    "list_backends",
    "register_backend",
]
