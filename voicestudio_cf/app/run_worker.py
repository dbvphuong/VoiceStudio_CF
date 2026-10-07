"""Qt signal bridge for background workers in VoiceStudio_CF."""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Slot

from .processor import ProcessingCallbacks, QueueProcessor, write_wave_file


class RunWorker(QObject):
    model_status = Signal(str)
    file_started = Signal(str)
    chunks_prepared = Signal(str, object)
    chunk_started = Signal(str, int)
    chunk_changed = Signal(str, int, object, object, str)
    file_finished = Signal(str, object, str, str)
    progress_changed = Signal(int, int, int)
    finished = Signal(object)

    def __init__(self, processor: QueueProcessor, tasks: list):
        super().__init__()
        self.processor = processor
        self.tasks = tasks
        self.processor.callbacks = ProcessingCallbacks(
            model_status=self.model_status.emit,
            file_started=self.file_started.emit,
            chunks_prepared=self.chunks_prepared.emit,
            chunk_started=self.chunk_started.emit,
            chunk_changed=self.chunk_changed.emit,
            file_finished=self.file_finished.emit,
            progress_changed=self.progress_changed.emit,
        )

    @Slot()
    def run(self) -> None:
        try:
            result = self.processor.run(self.tasks)
        except Exception as exc:
            result = {
                "success": 0,
                "errors": 1,
                "skipped": 0,
                "elapsed": "0",
                "stopped": 0,
                "fatal": str(exc),
            }
        self.finished.emit(result)

    @Slot(bool)
    def set_paused(self, paused: bool) -> None:
        self.processor.set_paused(paused)

    @Slot()
    def stop(self) -> None:
        self.processor.request_stop()


class PreviewWorker(QObject):
    model_status = Signal(str)
    finished = Signal(str)
    failed = Signal(str)

    def __init__(self, engine, text: str, template, output_path):
        super().__init__()
        self.engine = engine
        self.text = text
        self.template = template
        self.output_path = output_path

    @Slot()
    def run(self) -> None:
        try:
            if hasattr(self.engine, "load"):
                self.engine.load(None, self.model_status.emit)
            self.model_status.emit("Đang sinh audio nghe thử…")
            audio = self.engine.generate(self.text, self.template)
            write_wave_file(
                self.output_path, audio, self.engine.sample_rate
            )
            self.finished.emit(str(self.output_path))
        except Exception as exc:
            self.failed.emit(str(exc).strip() or exc.__class__.__name__)


class ModelLoadWorker(QObject):
    model_status = Signal(str)
    finished = Signal()
    failed = Signal(str)

    def __init__(self, engine, settings):
        super().__init__()
        self.engine = engine
        self.settings = settings

    @Slot()
    def run(self) -> None:
        try:
            self.engine.load(self.settings, self.model_status.emit)
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc).strip() or exc.__class__.__name__)
