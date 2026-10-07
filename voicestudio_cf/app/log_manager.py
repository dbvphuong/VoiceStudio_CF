"""Concise per-session logging with retention cleanup for VoiceStudio_CF."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable


LOG_NAME_PATTERN = re.compile(
    r"^voicestudio_\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}(?:_\d{2})?\.log$"
)


class CallbackHandler(logging.Handler):
    def __init__(self, callback: Callable[[str, int], None]):
        super().__init__()
        self.callback = callback

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.callback(self.format(record), record.levelno)
        except Exception:
            self.handleError(record)


def cleanup_old_logs(
    log_dir: Path, retention_days: int = 7, now: datetime | None = None
) -> list[Path]:
    if retention_days < 1 or not log_dir.exists():
        return []
    current = now or datetime.now()
    cutoff = current - timedelta(days=retention_days)
    removed: list[Path] = []
    for path in log_dir.iterdir():
        if not path.is_file() or not LOG_NAME_PATTERN.fullmatch(path.name):
            continue
        modified = datetime.fromtimestamp(path.stat().st_mtime)
        if modified < cutoff:
            path.unlink(missing_ok=True)
            removed.append(path)
    return removed


class SessionLog:
    def __init__(
        self,
        log_dir: Path,
        retention_days: int = 7,
        callback: Callable[[str, int], None] | None = None,
    ):
        log_dir.mkdir(parents=True, exist_ok=True)
        cleanup_old_logs(log_dir, retention_days)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.path = log_dir / f"voicestudio_{timestamp}.log"
        counter = 2
        while self.path.exists():
            self.path = log_dir / f"voicestudio_{timestamp}_{counter:02d}.log"
            counter += 1
        self.logger = logging.getLogger(f"voicestudio_cf.session.{timestamp}")
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False
        self.logger.handlers.clear()

        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)-7s] %(message)s", datefmt="%H:%M:%S"
        )
        file_handler = logging.FileHandler(self.path, encoding="utf-8")
        file_handler.setFormatter(formatter)
        self.logger.addHandler(file_handler)
        if callback:
            callback_handler = CallbackHandler(callback)
            callback_handler.setFormatter(formatter)
            self.logger.addHandler(callback_handler)

    def close(self) -> None:
        for handler in list(self.logger.handlers):
            handler.flush()
            handler.close()
            self.logger.removeHandler(handler)
