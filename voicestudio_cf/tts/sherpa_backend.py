"""Sherpa-ONNX engine adapter kế thừa từ VoiceStudio."""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Callable

import numpy as np

from .base import TTSBackend

logger = logging.getLogger("voicestudio_cf.tts.sherpa")


class SherpaOnnxBackend(TTSBackend):
    """Engine TTS offline siêu nhẹ từ VoiceStudio (k2-fsa/sherpa-onnx).
    
    Chạy trực tiếp qua ONNX Runtime trên CPU, không cần GPU rời hoặc CUDA phức tạp.
    """

    id = "sherpa-onnx"
    display_name = "Sherpa-ONNX (Siêu nhẹ · Chạy CPU Offline mượt mà)"
    supports_voice_clone = False
    supports_voice_design = False

    def __init__(self):
        self.tts = None
        self._sample_rate = 22050
        self.status_callback: Callable[[str], None] = lambda _msg: None

    @property
    def sample_rate(self) -> int:
        if self.tts is not None and hasattr(self.tts, "sample_rate"):
            return int(self.tts.sample_rate)
        return self._sample_rate

    @property
    def supported_languages(self) -> list[str]:
        return ["Vietnamese", "English", "Chinese", "Auto"]

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        try:
            import sherpa_onnx  # noqa: F401
            return True, "Sẵn sàng"
        except ImportError:
            return False, "Chưa cài đặt gói sherpa-onnx (cài bằng: pip install sherpa-onnx)"

    def load(
        self,
        settings: Any,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        if status_callback:
            self.status_callback = status_callback

        if self.tts is not None:
            return

        self.status_callback("Đang nạp mô hình Sherpa-ONNX…")
        import sherpa_onnx

        # Tìm model dir từ cấu hình hoặc biến môi trường
        model_dir = os.environ.get("SHERPA_ONNX_MODEL_DIR", "")
        if not model_dir or not Path(model_dir).is_dir():
            raise FileNotFoundError(
                "Chưa thiết lập đường dẫn mô hình Sherpa-ONNX (SHERPA_ONNX_MODEL_DIR). "
                "Hãy tải model VITS ONNX từ https://github.com/k2-fsa/sherpa-onnx/releases"
            )

        vits_model = Path(model_dir) / "model.onnx"
        tokens = Path(model_dir) / "tokens.txt"
        lexicon = Path(model_dir) / "lexicon.txt"
        data_dir = Path(model_dir) / "espeak-ng-data"

        config = sherpa_onnx.OfflineTtsConfig(
            model=sherpa_onnx.OfflineTtsModelConfig(
                vits=sherpa_onnx.OfflineTtsVitsModelConfig(
                    model=str(vits_model),
                    lexicon=str(lexicon) if lexicon.exists() else "",
                    tokens=str(tokens),
                    data_dir=str(data_dir) if data_dir.exists() else "",
                ),
                provider="cpu",
                num_threads=getattr(settings, "cpu_threads", 4),
            )
        )
        self.tts = sherpa_onnx.OfflineTts(config)
        self._sample_rate = self.tts.sample_rate
        self.status_callback("Mô hình Sherpa-ONNX đã sẵn sàng.")

    def generate(self, text: str, template: Any) -> Any:
        if self.tts is None:
            raise RuntimeError("Mô hình Sherpa-ONNX chưa được nạp.")
        
        speed = getattr(template, "speed", 1.0)
        audio = self.tts.generate(text, sid=0, speed=speed)
        return np.array(audio.samples, dtype=np.float32)

    def unload(self) -> None:
        self.tts = None
        self.status_callback("Đã giải phóng Sherpa-ONNX.")
