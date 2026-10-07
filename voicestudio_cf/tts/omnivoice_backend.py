"""OmniVoice backend adapter kế thừa các tối ưu từ VoiceStudio."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Callable

from .base import TTSBackend

logger = logging.getLogger("voicestudio_cf.tts.omnivoice")


class OmniVoiceBackend(TTSBackend):
    """Engine TTS cốt lõi mặc định của VoiceStudio (k2-fsa/OmniVoice, 600+ ngôn ngữ).
    
    Tích hợp các tối ưu hóa của VoiceStudio:
    - Prompt caching: Tái sử dụng prompt clone cho toàn bộ hàng chờ mà không encode lại.
    - Low-VRAM guard: Giữ an toàn cho GPU 4-6GB (như GTX 1650) không bị Out of Memory.
    - CPU/CUDA balance: Offload nhẹ codec khi cần thiết.
    """

    id = "omnivoice"
    display_name = "VoiceStudio OmniVoice (k2-fsa/OmniVoice · 600+ ngôn ngữ)"
    supports_voice_clone = True
    supports_voice_design = True

    def __init__(self):
        self.model = None
        self.device = ""
        self.low_vram = False
        self._clone_prompts: dict[tuple[str, str, int], Any] = {}
        self.status_callback: Callable[[str], None] = lambda _msg: None
        self._sample_rate = 24000

    @property
    def sample_rate(self) -> int:
        if self.model is not None and hasattr(self.model, "sampling_rate"):
            return int(self.model.sampling_rate)
        return self._sample_rate

    @property
    def supported_languages(self) -> list[str]:
        return [
            "Vietnamese",
            "English",
            "Chinese",
            "Japanese",
            "Korean",
            "French",
            "German",
            "Spanish",
            "Russian",
            "Auto",
        ]

    @classmethod
    def is_available(cls) -> tuple[bool, str]:
        try:
            import torch  # noqa: F401
            import omnivoice  # noqa: F401
            return True, "Sẵn sàng"
        except ImportError as exc:
            return False, f"Thiếu thư viện omnivoice hoặc torch: {exc}"

    def load(
        self,
        settings: Any,
        status_callback: Callable[[str], None] | None = None,
    ) -> None:
        if status_callback:
            self.status_callback = status_callback

        if self.model is not None:
            return

        self.status_callback("Đang nạp mô hình OmniVoice từ VoiceStudio…")
        import torch
        from omnivoice import OmniVoice
        from omnivoice.utils.common import get_best_device

        # Cấu hình luồng CPU
        cpu_threads = getattr(settings, "cpu_threads", 2)
        torch.set_num_threads(max(1, int(cpu_threads)))

        req_device = getattr(settings, "device", "auto")
        self.device = get_best_device() if req_device in ("", "auto") else req_device

        dtype = torch.float16 if str(self.device) != "cpu" else torch.float32

        if str(self.device).startswith("cuda") and torch.cuda.is_available():
            mem_frac = float(getattr(settings, "cuda_memory_fraction", 0.75))
            fraction = min(1.0, max(0.1, mem_frac))
            cuda_device = torch.device(self.device)
            cuda_index = (
                cuda_device.index
                if cuda_device.index is not None
                else torch.cuda.current_device()
            )
            try:
                torch.cuda.set_per_process_memory_fraction(fraction, device=cuda_index)
            except Exception as e:
                logger.warning("Không thể set VRAM fraction: %s", e)

            total_vram = torch.cuda.get_device_properties(cuda_index).total_memory
            # Card <= 6GB VRAM (ví dụ GTX 1650 4GB) được bật chế độ low_vram tự động
            self.low_vram = total_vram <= 6 * 1024**3
            logger.info(
                "Phát hiện GPU: %s (VRAM: %.1f GB) - Low VRAM mode: %s",
                torch.cuda.get_device_name(cuda_index),
                total_vram / (1024**3),
                self.low_vram,
            )

        model_source = getattr(settings, "model_source", "k2-fsa/OmniVoice")
        self.status_callback(f"Đang tải trọng số từ {model_source} ({self.device})…")
        
        self.model = OmniVoice.from_pretrained(
            model_source,
            device_map=self.device,
            dtype=dtype,
        )

        if self.low_vram and hasattr(self.model, "audio_tokenizer"):
            self.status_callback("Đang tối ưu VRAM: chuyển bộ codec sang CPU…")
            try:
                self.model.audio_tokenizer.to("cpu")
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception as e:
                logger.debug("Không thể offload audio_tokenizer sang CPU: %s", e)

        self._sample_rate = getattr(self.model, "sampling_rate", 24000)
        self.status_callback(f"Mô hình OmniVoice sẵn sàng · {str(self.device).upper()}")

    def generate(self, text: str, template: Any) -> Any:
        if self.model is None:
            raise RuntimeError("Mô hình chưa được nạp.")

        kwargs: dict[str, Any] = {
            "text": text,
            "language": template.language if getattr(template, "language", None) != "Auto" else None,
            "speed": getattr(template, "speed", 1.0),
            "num_step": getattr(template, "num_step", 32),
            "guidance_scale": getattr(template, "guidance_scale", 2.0),
            "denoise": getattr(template, "denoise", True),
            "postprocess_output": getattr(template, "postprocess_output", True),
            "normalize_text": getattr(template, "normalize_text", True),
        }

        if self.low_vram:
            kwargs["audio_chunk_duration"] = 10.0
            kwargs["audio_chunk_threshold"] = 12.0

        mode = getattr(template, "mode", "clone")

        if mode == "clone":
            ref_audio = getattr(template, "ref_audio", "")
            if not ref_audio:
                raise ValueError(f"Template '{template.name}' chưa có file audio mẫu")
            ref_path = Path(ref_audio)
            if not ref_path.is_file():
                raise FileNotFoundError(f"Không tìm thấy file audio mẫu: {ref_audio}")

            ref_text = getattr(template, "ref_text", "").strip()
            # Tối ưu hóa của VoiceStudio: Caching voice prompt theo file mtime + text
            cache_key = (
                str(ref_path.resolve()),
                ref_text,
                ref_path.stat().st_mtime_ns,
            )
            prompt = self._clone_prompts.get(cache_key)
            if prompt is None:
                self.status_callback("Đang tạo prompt cho giọng mẫu (chỉ tạo 1 lần)…")
                prompt = self.model.create_voice_clone_prompt(
                    str(ref_path), ref_text or None
                )
                self._clone_prompts[cache_key] = prompt
            kwargs["voice_clone_prompt"] = prompt

        elif mode == "design":
            instruction = ""
            if hasattr(template, "voice_instruction"):
                instruction = template.voice_instruction()
            else:
                values = [
                    getattr(template, "gender", ""),
                    getattr(template, "age", ""),
                    getattr(template, "pitch", ""),
                    getattr(template, "style", ""),
                    getattr(template, "accent", ""),
                    getattr(template, "instruct", ""),
                ]
                instruction = ", ".join(v.strip() for v in values if v.strip())
            
            if not instruction:
                raise ValueError(f"Template '{template.name}' chưa có mô tả thiết kế giọng")
            kwargs["instruct"] = instruction

        try:
            try:
                result = self.model.generate(**kwargs)
                return result[0]
            except ImportError as exc:
                if kwargs.get("normalize_text") and "WeTextProcessing" in str(exc):
                    self.status_callback("Bỏ qua WeTextProcessing (tính năng tuỳ chọn trên Windows)…")
                    kwargs["normalize_text"] = False
                    result = self.model.generate(**kwargs)
                    return result[0]
                raise
        finally:
            if str(self.device).startswith("cuda"):
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()

    def unload(self) -> None:
        self._clone_prompts.clear()
        if self.model is not None:
            del self.model
            self.model = None
            if str(self.device).startswith("cuda"):
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            self.status_callback("Đã giải phóng mô hình khỏi bộ nhớ.")
