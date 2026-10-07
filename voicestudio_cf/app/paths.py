"""Application data path helpers for VoiceStudio_CF."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AppPaths:
    root: Path
    config: Path
    templates: Path
    history: Path
    logs: Path
    outputs: Path

    @classmethod
    def discover(cls) -> "AppPaths":
        override = os.environ.get("VOICESTUDIO_CF_HOME") or os.environ.get("VOICE_OMNI_CF_HOME")
        if override:
            root = Path(override).expanduser().resolve()
        elif os.name == "nt" and os.environ.get("LOCALAPPDATA"):
            root = Path(os.environ["LOCALAPPDATA"]) / "VoiceStudio_CF"
        else:
            root = Path.home() / ".voicestudio-cf"
        return cls(
            root=root,
            config=root / "settings.json",
            templates=root / "templates.json",
            history=root / "history.db",
            logs=root / "logs",
            outputs=root / "outputs",
        )

    def ensure(self) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        self.logs.mkdir(parents=True, exist_ok=True)
        self.outputs.mkdir(parents=True, exist_ok=True)
