"""Queue processor independent from the Qt user interface for VoiceStudio_CF."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import subprocess
import threading
import time
import wave
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .domain import AppSettings, QueueTask, TaskStatus, TextChunk
from .storage import HistoryStore
from .text_processing import read_text_file, split_text
from ..tts.base import TTSBackend


def _noop(*_args, **_kwargs) -> None:
    return None


@dataclass
class ProcessingCallbacks:
    model_status: Callable[[str], None] = _noop
    file_started: Callable[[str], None] = _noop
    chunks_prepared: Callable[[str, list[TextChunk]], None] = _noop
    chunk_started: Callable[[str, int], None] = _noop
    chunk_changed: Callable[[str, int, TaskStatus, float | None, str], None] = _noop
    file_finished: Callable[[str, TaskStatus, str, str], None] = _noop
    progress_changed: Callable[[int, int, int], None] = _noop


@dataclass
class PreparedTask:
    task: QueueTask
    content: str = ""
    content_hash: str = ""
    error: str = ""


class QueueProcessor:
    def __init__(
        self,
        settings: AppSettings,
        history: HistoryStore,
        logger: logging.Logger,
        engine_factory: Callable[[str, AppSettings, Callable[[str], None]], TTSBackend],
        callbacks: ProcessingCallbacks | None = None,
    ):
        self.settings = settings
        self.history = history
        self.logger = logger
        self.engine_factory = engine_factory
        self.callbacks = callbacks or ProcessingCallbacks()
        self.stop_event = threading.Event()
        self.pause_event = threading.Event()
        self._engines: dict[str, TTSBackend] = {}

    def request_stop(self) -> None:
        self.stop_event.set()
        self.pause_event.clear()

    def set_paused(self, paused: bool) -> None:
        if paused:
            self.pause_event.set()
        else:
            self.pause_event.clear()

    def _get_engine(self, engine_id: str) -> TTSBackend:
        if engine_id not in self._engines:
            self._engines[engine_id] = self.engine_factory(
                engine_id, self.settings, self.callbacks.model_status
            )
        return self._engines[engine_id]

    def run(self, tasks: list[QueueTask]) -> dict[str, int | str]:
        started_at = time.monotonic()
        prepared = self._prepare_all(tasks)
        total_chunks = sum(len(item.task.chunks) for item in prepared)
        completed_chunks = 0
        success = 0
        errors = 0
        skipped = 0

        self.logger.info("Bắt đầu phiên VoiceStudio_CF với %d file (tổng %d đoạn)", len(tasks), total_chunks)
        for item in prepared:
            if self.stop_event.is_set():
                break
            task = item.task
            self.callbacks.file_started(task.id)
            self.callbacks.chunks_prepared(task.id, task.chunks)

            if item.error:
                errors += 1
                task.status = TaskStatus.ERROR
                task.message = item.error
                self.logger.error("[%s] Lỗi: %s", task.path.name, item.error)
                self.callbacks.file_finished(
                    task.id, task.status, task.message, ""
                )
                continue

            task_key = self._task_key(item)
            output = self._output_path(task.path)
            if self.settings.skip_completed and output.is_file():
                skipped += 1
                task.status = TaskStatus.SUCCESS
                task.output_path = str(output)
                task.message = "MP3 đã tồn tại - bỏ qua"
                for chunk in task.chunks:
                    chunk.status = TaskStatus.SUCCESS
                    chunk.message = "MP3 đã tồn tại"
                completed_chunks += len(task.chunks)
                self.logger.info("[%s] Bỏ qua: đã có %s", task.path.name, output.name)
                self.callbacks.file_finished(
                    task.id, task.status, task.message, task.output_path
                )
                self.callbacks.progress_changed(
                    completed_chunks, total_chunks, len(tasks)
                )
                continue

            engine_id = getattr(task.template, "engine", "omnivoice") or "omnivoice"
            try:
                engine = self._get_engine(engine_id)
            except Exception as e:
                errors += 1
                task.status = TaskStatus.ERROR
                task.message = f"Lỗi khởi tạo engine {engine_id}: {e}"
                self.logger.error("[%s] %s", task.path.name, task.message)
                self.callbacks.file_finished(task.id, task.status, task.message, "")
                continue

            wave_part = output.with_name(
                f".{output.stem}.{task.id[:8]}.wav.part"
            )
            mp3_part = output.with_name(f".{output.name}.{task.id[:8]}.part")
            self.logger.info(
                "[%s] Bắt đầu tạo audio (%d đoạn) bằng engine '%s'",
                task.path.name,
                len(task.chunks),
                engine.display_name,
            )

            file_ok = True
            writer = None
            try:
                for chunk in task.chunks:
                    if not self._wait_until_runnable():
                        file_ok = False
                        task.message = "Đã dừng an toàn"
                        break
                    chunk_started = time.monotonic()
                    self.callbacks.chunk_started(task.id, chunk.index)
                    try:
                        audio = engine.generate(chunk.text, task.template)
                        if writer is None:
                            writer = wave.open(str(wave_part), mode="wb")
                            writer.setnchannels(1)
                            writer.setsampwidth(2)
                            writer.setframerate(engine.sample_rate)
                        
                        writer.writeframes(_pcm16_bytes(audio))

                        pause_samples = int(
                            engine.sample_rate
                            * self.settings.pause_between_chunks_ms
                            / 1000
                        )
                        if pause_samples and chunk.index < len(task.chunks):
                            writer.writeframes(b"\x00\x00" * pause_samples)

                        chunk.status = TaskStatus.SUCCESS
                        chunk.elapsed_seconds = time.monotonic() - chunk_started
                        chunk.message = "Đã tạo audio"

                        audio_len = len(np.asarray(audio).reshape(-1))
                        audio_seconds = audio_len / engine.sample_rate if engine.sample_rate else 0.0
                        rtf = (
                            chunk.elapsed_seconds / audio_seconds
                            if audio_seconds > 0
                            else 0.0
                        )
                        self.logger.info(
                            "[%s] Đoạn %d/%d xong: %.1fs xử lý, %.1fs audio (RTF: %.2f)",
                            task.path.name,
                            chunk.index,
                            len(task.chunks),
                            chunk.elapsed_seconds,
                            audio_seconds,
                            rtf,
                        )
                        completed_chunks += 1
                        self.callbacks.chunk_changed(
                            task.id,
                            chunk.index,
                            chunk.status,
                            chunk.elapsed_seconds,
                            chunk.message,
                        )
                        self.callbacks.progress_changed(
                            completed_chunks, total_chunks, len(tasks)
                        )
                    except Exception as exc:
                        file_ok = False
                        errors += 1
                        chunk.status = TaskStatus.ERROR
                        chunk.elapsed_seconds = time.monotonic() - chunk_started
                        chunk.message = _friendly_error(exc)
                        task.message = f"Đoạn {chunk.index}: {chunk.message}"
                        self.logger.error(
                            "[%s] Đoạn %d gặp lỗi: %s",
                            task.path.name,
                            chunk.index,
                            chunk.message,
                        )
                        self.callbacks.chunk_changed(
                            task.id,
                            chunk.index,
                            chunk.status,
                            chunk.elapsed_seconds,
                            chunk.message,
                        )
                        break
            except Exception as exc:
                if file_ok:
                    errors += 1
                file_ok = False
                task.message = _friendly_error(exc)
                self.logger.error("[%s] %s", task.path.name, task.message)
            finally:
                if writer is not None:
                    writer.close()

            if file_ok and not self.stop_event.is_set():
                try:
                    convert_wave_to_mp3(wave_part, mp3_part)
                    output.parent.mkdir(parents=True, exist_ok=True)
                    os.replace(mp3_part, output)
                    task.status = TaskStatus.SUCCESS
                    task.output_path = str(output)
                    task.message = "Hoàn thành"
                    success += 1
                    self.history.record(task_key, task.path, output)
                    self.logger.info("[%s] Hoàn thành xuất sắc: %s", task.path.name, output)
                except Exception as exc:
                    errors += 1
                    file_ok = False
                    task.status = TaskStatus.ERROR
                    task.message = _friendly_error(exc)
                    self.logger.error("[%s] %s", task.path.name, task.message)
            else:
                task.status = TaskStatus.ERROR
                if not task.message:
                    task.message = "Tác vụ chưa hoàn thành"
            wave_part.unlink(missing_ok=True)
            mp3_part.unlink(missing_ok=True)
            self.callbacks.file_finished(
                task.id, task.status, task.message, task.output_path
            )

        elapsed = time.monotonic() - started_at
        result = {
            "success": success,
            "errors": errors,
            "skipped": skipped,
            "elapsed": f"{elapsed:.1f}",
            "stopped": int(self.stop_event.is_set()),
        }
        self.logger.info(
            "Kết thúc phiên: %d thành công, %d bỏ qua, %d lỗi (Tổng thời gian: %.1fs)",
            success,
            skipped,
            errors,
            elapsed,
        )
        return result

    def _prepare_all(self, tasks: list[QueueTask]) -> list[PreparedTask]:
        workers = max(1, min(16, self.settings.preparation_workers))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            return list(pool.map(self._prepare_one, tasks))

    def _prepare_one(self, task: QueueTask) -> PreparedTask:
        try:
            content = read_text_file(task.path)
            chunks = split_text(content, self.settings.max_chunk_chars)
            if not chunks:
                return PreparedTask(task=task, error="File rỗng, không có nội dung văn bản")
            task.chunks = [
                TextChunk(index=index, text=text)
                for index, text in enumerate(chunks, start=1)
            ]
            digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
            return PreparedTask(task=task, content=content, content_hash=digest)
        except Exception as exc:
            return PreparedTask(task=task, error=_friendly_error(exc))

    def _task_key(self, item: PreparedTask) -> str:
        payload = {
            "content": item.content_hash,
            "template": item.task.template.fingerprint(),
            "model": self.settings.model_source,
            "max_chunk_chars": self.settings.max_chunk_chars,
            "pause_ms": self.settings.pause_between_chunks_ms,
        }
        raw = json.dumps(payload, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _wait_until_runnable(self) -> bool:
        while self.pause_event.is_set() and not self.stop_event.is_set():
            time.sleep(0.1)
        return not self.stop_event.is_set()

    def _output_path(self, source: Path) -> Path:
        suffix = self.settings.output_suffix.strip()
        if any(character in suffix for character in '<>:"/\\|?*'):
            raise ValueError("Hậu tố tên MP3 chứa ký tự không hợp lệ")

        if self.settings.output_dir and Path(self.settings.output_dir).is_dir():
            target_dir = Path(self.settings.output_dir)
            return target_dir / f"{source.stem}{suffix}.mp3"
        return source.with_name(f"{source.stem}{suffix}.mp3")


def _friendly_error(exc: Exception) -> str:
    message = str(exc).strip() or exc.__class__.__name__
    lowered = message.lower()
    if "out of memory" in lowered or "cuda out of memory" in lowered:
        return (
            "Tràn bộ nhớ GPU (VRAM). Hãy giảm 'Ký tự tối đa mỗi đoạn' "
            "hoặc chuyển sang chế độ CPU / Sherpa-ONNX trong Cài đặt."
        )
    return message


def convert_wave_to_mp3(wave_path: Path, mp3_path: Path) -> None:
    """Chuyển đổi file PCM WAV sang MP3 chất lượng cao bằng FFmpeg."""
    try:
        result = subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                str(wave_path),
                "-codec:a",
                "libmp3lame",
                "-q:a",
                "2",
                "-f",
                "mp3",
                str(mp3_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Không tìm thấy FFmpeg để xuất MP3. Hãy cài FFmpeg và thêm vào PATH."
        ) from exc
    if result.returncode != 0:
        detail = result.stderr.strip() or f"mã lỗi {result.returncode}"
        raise RuntimeError(f"Không thể xuất MP3: {detail}")


def _pcm16_bytes(audio) -> bytes:
    samples = np.asarray(audio).reshape(-1)
    if np.issubdtype(samples.dtype, np.floating):
        samples = np.clip(samples, -1.0, 1.0) * 32767.0
    return samples.astype("<i2", copy=False).tobytes()


def write_wave_file(path: Path, audio, sampling_rate: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), mode="wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sampling_rate)
        writer.writeframes(_pcm16_bytes(audio))
