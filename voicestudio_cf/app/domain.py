"""Domain models shared by the UI and processing layer in VoiceStudio_CF."""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class TaskStatus(str, Enum):
    WAITING = "Chờ"
    RUNNING = "Đang xử lý"
    SUCCESS = "Thành công"
    ERROR = "Lỗi"


class VoiceMode(str, Enum):
    CLONE = "clone"
    DESIGN = "design"
    AUTO = "auto"


@dataclass
class VoiceTemplate:
    name: str
    description: str = ""
    engine: str = "omnivoice"  # omnivoice, sherpa-onnx, mock
    mode: str = VoiceMode.CLONE.value
    language: str = "Vietnamese"
    speed: float = 1.0
    num_step: int = 32
    ref_audio: str = ""
    ref_text: str = ""
    gender: str = ""
    age: str = ""
    pitch: str = ""
    style: str = ""
    accent: str = ""
    instruct: str = ""
    guidance_scale: float = 2.0
    denoise: bool = True
    postprocess_output: bool = True
    normalize_text: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    builtin: bool = False

    def voice_instruction(self) -> str:
        values = [
            self.gender,
            self.age,
            self.pitch,
            self.style,
            self.accent,
            self.instruct,
        ]
        return ", ".join(value.strip() for value in values if value.strip())

    def generation_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        for key in ("id", "name", "description", "builtin"):
            payload.pop(key, None)
        ref_audio = Path(self.ref_audio) if self.ref_audio else None
        if ref_audio and ref_audio.is_file():
            payload["ref_audio_hash"] = hash_file(ref_audio)
        return payload

    def fingerprint(self) -> str:
        raw = json.dumps(
            self.generation_payload(), ensure_ascii=False, sort_keys=True
        ).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceTemplate":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class AppSettings:
    model_source: str = "k2-fsa/OmniVoice"
    device: str = "auto"
    default_engine: str = "omnivoice"
    output_dir: str = ""
    output_suffix: str = ""
    log_dir: str = ""
    log_retention_days: int = 7
    recursive_folders: bool = False
    skip_completed: bool = True
    max_chunk_chars: int = 700
    pause_between_chunks_ms: int = 350
    preparation_workers: int = 2
    cpu_threads: int = 2
    cuda_memory_fraction: float = 0.75
    existing_output: str = "suffix"
    auto_open_output: bool = False
    load_model_on_start: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppSettings":
        allowed = set(cls.__dataclass_fields__)
        return cls(**{key: value for key, value in data.items() if key in allowed})


@dataclass
class TextChunk:
    index: int
    text: str
    status: TaskStatus = TaskStatus.WAITING
    elapsed_seconds: float | None = None
    message: str = ""


@dataclass
class QueueTask:
    path: Path
    template: VoiceTemplate
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: TaskStatus = TaskStatus.WAITING
    message: str = ""
    output_path: str = ""
    chunks: list[TextChunk] = field(default_factory=list)


def hash_file(path: Path, block_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(block_size):
            digest.update(block)
    return digest.hexdigest()
