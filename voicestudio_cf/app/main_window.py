"""Main window for VoiceStudio_CF."""

from __future__ import annotations

import copy
import time
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QThread, QTimer, Qt, QUrl, Signal
from PySide6.QtGui import QCloseEvent, QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QButtonGroup,
    QComboBox,
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from . import APP_NAME, APP_VERSION
from .domain import AppSettings, QueueTask, TaskStatus, VoiceMode, VoiceTemplate
from .log_manager import SessionLog, cleanup_old_logs
from .log_page import LogPage
from .paths import AppPaths
from .preview_dialog import PreviewDialog
from .processor import QueueProcessor
from .run_worker import ModelLoadWorker, RunWorker
from .settings_dialog import SettingsDialog
from .storage import HistoryStore, SettingsStore, TemplateStore
from .template_page import TemplatePage
from ..tts import create_backend, TTSBackend


class MainWindow(QMainWindow):
    log_received = Signal(str, int)
    PAGE_SIZE = 50

    def __init__(self):
        super().__init__()
        self.paths = AppPaths.discover()
        self.paths.ensure()

        default_settings = AppSettings(
            output_dir=str(self.paths.outputs), log_dir=str(self.paths.logs)
        )
        self.settings_store = SettingsStore(self.paths.config, default_settings)
        self.settings = self.settings_store.load()
        if not self.settings.output_dir or not self.settings.log_dir:
            self.settings = replace(
                self.settings,
                output_dir=self.settings.output_dir or str(self.paths.outputs),
                log_dir=self.settings.log_dir or str(self.paths.logs),
            )
            self.settings_store.save(self.settings)

        cleanup_old_logs(
            Path(self.settings.log_dir).expanduser(),
            self.settings.log_retention_days,
        )

        self.template_store = TemplateStore(self.paths.templates)
        self.templates = self.template_store.load()
        self.history = HistoryStore(self.paths.history)

        self.tasks: list[QueueTask] = []
        self.current_task_id: str | None = None
        self.current_page = 0
        self.active_chunk_index: int | None = None

        self.run_thread: QThread | None = None
        self.run_worker: RunWorker | None = None
        self.processor: QueueProcessor | None = None
        self.session_log: SessionLog | None = None
        self._shared_engines: dict[str, TTSBackend] = {}

        self.run_started_at = 0.0
        self.is_paused = False

        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} · Bộ tạo giọng nói Local chuyên nghiệp")
        self.resize(1540, 900)
        self.setMinimumSize(1120, 700)

        self._build_ui()
        self._refresh_template_combo()
        self._refresh_summary()
        self._update_device_badge()
        self.log_received.connect(self.log_page.append_line)

        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._update_elapsed)

    def _engine_factory(self, engine_id: str, settings: AppSettings, status_cb) -> TTSBackend:
        if engine_id not in self._shared_engines:
            backend = create_backend(engine_id)
            backend.load(settings, status_cb)
            self._shared_engines[engine_id] = backend
        return self._shared_engines[engine_id]

    def _build_ui(self) -> None:
        root_widget = QWidget()
        root_widget.setObjectName("AppRoot")
        self.setCentralWidget(root_widget)
        root = QVBoxLayout(root_widget)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_topbar())

        body = QHBoxLayout()
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(8)
        root.addLayout(body, 1)

        body.addWidget(self._build_sidebar())

        self.pages = QStackedWidget()
        self.pages.setObjectName("Pages")
        self.process_page = self._build_process_page()
        self.template_page = TemplatePage(
            self.template_store, self.templates
        )
        self.template_page.templates_changed.connect(self._templates_changed)
        self.log_page = LogPage()

        self.pages.addWidget(self.process_page)
        self.pages.addWidget(self.template_page)
        self.pages.addWidget(self.log_page)
        body.addWidget(self.pages, 1)

    def _build_topbar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("TopBar")
        bar.setFixedHeight(66)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 8, 18, 8)

        logo = QLabel("🎙")
        logo.setStyleSheet("font-size: 26px; color: #7143dc;")
        title = QLabel(APP_NAME)
        title.setObjectName("AppTitle")
        ver = QLabel(f"v{APP_VERSION}")
        ver.setProperty("muted", True)

        self.device_badge = QLabel("Thiết bị: Đang kiểm tra…")
        self.device_badge.setObjectName("DeviceBadge")

        settings_btn = QPushButton("⚙ Cài đặt hệ thống")
        settings_btn.clicked.connect(self._open_settings)

        layout.addWidget(logo)
        layout.addWidget(title)
        layout.addWidget(ver)
        layout.addSpacing(14)
        layout.addWidget(self.device_badge)
        layout.addStretch(1)
        layout.addWidget(settings_btn)
        return bar

    def _build_sidebar(self) -> QFrame:
        bar = QFrame()
        bar.setObjectName("Sidebar")
        bar.setFixedWidth(240)
        layout = QVBoxLayout(bar)
        layout.setContentsMargins(10, 14, 10, 14)
        layout.setSpacing(6)

        self.nav_buttons = QButtonGroup(self)
        self.nav_buttons.setExclusive(True)

        self.nav_process = QPushButton("  📋  Xử lý hàng chờ")
        self.nav_process.setProperty("nav", True)
        self.nav_process.setCheckable(True)
        self.nav_process.setChecked(True)
        self.nav_process.clicked.connect(lambda: self.pages.setCurrentIndex(0))

        self.nav_templates = QPushButton("  🎭  Quản lý template")
        self.nav_templates.setProperty("nav", True)
        self.nav_templates.setCheckable(True)
        self.nav_templates.clicked.connect(lambda: self.pages.setCurrentIndex(1))

        self.nav_logs = QPushButton("  📝  Log realtime")
        self.nav_logs.setProperty("nav", True)
        self.nav_logs.setCheckable(True)
        self.nav_logs.clicked.connect(lambda: self.pages.setCurrentIndex(2))

        self.nav_buttons.addButton(self.nav_process, 0)
        self.nav_buttons.addButton(self.nav_templates, 1)
        self.nav_buttons.addButton(self.nav_logs, 2)

        layout.addWidget(self.nav_process)
        layout.addWidget(self.nav_templates)
        layout.addWidget(self.nav_logs)
        layout.addStretch(1)

        tip_card = QFrame()
        tip_card.setStyleSheet("background: #fbfaff; border: 1px solid #ebe5f8; border-radius: 8px; padding: 10px;")
        tip_layout = QVBoxLayout(tip_card)
        tip_title = QLabel("💡 Mẹo tối ưu")
        tip_title.setStyleSheet("font-weight: 700; color: #43239a;")
        tip_text = QLabel("Chia văn bản 500-700 ký tự mỗi đoạn giúp sinh giọng tự nhiên và không bị tràn VRAM.")
        tip_text.setWordWrap(True)
        tip_text.setProperty("muted", True)
        tip_layout.addWidget(tip_title)
        tip_layout.addWidget(tip_text)
        layout.addWidget(tip_card)

        return bar

    def _build_process_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(12)

        # Toolbar trên
        toolbar_card = QFrame()
        toolbar_card.setProperty("card", True)
        tb_layout = QHBoxLayout(toolbar_card)
        tb_layout.setContentsMargins(14, 12, 14, 12)
        tb_layout.setSpacing(8)

        add_folder_btn = QPushButton("📁 Thêm folder")
        add_folder_btn.clicked.connect(self._add_folder)
        add_file_btn = QPushButton("📄 Thêm file TXT")
        add_file_btn.clicked.connect(self._add_files)

        tb_layout.addWidget(add_folder_btn)
        tb_layout.addWidget(add_file_btn)
        tb_layout.addSpacing(10)

        tb_layout.addWidget(QLabel("Giọng:"))
        self.template_combo = QComboBox()
        self.template_combo.setMinimumWidth(220)
        tb_layout.addWidget(self.template_combo)

        preview_btn = QPushButton("🎧 Nghe thử")
        preview_btn.clicked.connect(self._open_preview)
        tb_layout.addWidget(preview_btn)

        tb_layout.addStretch(1)

        self.start_btn = QPushButton("▶ Bắt đầu chạy")
        self.start_btn.setProperty("primary", True)
        self.start_btn.clicked.connect(self._start_run)

        self.pause_btn = QPushButton("⏸ Tạm dừng")
        self.pause_btn.setEnabled(False)
        self.pause_btn.clicked.connect(self._toggle_pause)

        self.stop_btn = QPushButton("⏹ Dừng")
        self.stop_btn.setProperty("danger", True)
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self._stop_run)

        clear_btn = QPushButton("Xóa hàng chờ")
        clear_btn.clicked.connect(self._clear_queue)

        open_out_btn = QPushButton("Mở thư mục")
        open_out_btn.clicked.connect(self._open_output_dir)

        tb_layout.addWidget(self.start_btn)
        tb_layout.addWidget(self.pause_btn)
        tb_layout.addWidget(self.stop_btn)
        tb_layout.addWidget(clear_btn)
        tb_layout.addWidget(open_out_btn)
        layout.addWidget(toolbar_card)

        # Main Table Card (Bảng phân trang 50 dòng)
        table_card = QFrame()
        table_card.setProperty("card", True)
        tc_layout = QVBoxLayout(table_card)
        tc_layout.setContentsMargins(14, 14, 14, 14)

        table_header = QHBoxLayout()
        self.table_title = QLabel("Chi tiết phân đoạn (50 đoạn mỗi trang)")
        self.table_title.setObjectName("CardTitle")
        table_header.addWidget(self.table_title)
        table_header.addStretch(1)

        self.prev_page_btn = QPushButton("◀ Trang trước")
        self.prev_page_btn.clicked.connect(self._prev_page)
        self.page_label = QLabel("Trang 1 / 1")
        self.page_label.setStyleSheet("font-weight: 600; padding: 0 8px;")
        self.next_page_btn = QPushButton("Trang sau ▶")
        self.next_page_btn.clicked.connect(self._next_page)

        table_header.addWidget(self.prev_page_btn)
        table_header.addWidget(self.page_label)
        table_header.addWidget(self.next_page_btn)
        tc_layout.addLayout(table_header)

        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([
            "Đoạn", "Nội dung văn bản", "Thời gian", "Trạng thái", "Chi tiết / Lỗi"
        ])
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tc_layout.addWidget(self.table, 1)

        layout.addWidget(table_card, 1)

        # Thanh tiến trình & Trạng thái đáy
        status_card = QFrame()
        status_card.setProperty("card", True)
        sc_layout = QVBoxLayout(status_card)
        sc_layout.setContentsMargins(14, 10, 14, 10)

        info_row = QHBoxLayout()
        self.status_text = QLabel("Sẵn sàng.")
        self.summary_text = QLabel("0 file trong hàng chờ")
        self.summary_text.setProperty("muted", True)
        self.elapsed_text = QLabel("Thời gian: 00:00")
        self.elapsed_text.setStyleSheet("font-weight: 600; color: #43239a;")

        info_row.addWidget(self.status_text, 1)
        info_row.addWidget(self.summary_text)
        info_row.addSpacing(16)
        info_row.addWidget(self.elapsed_text)
        sc_layout.addLayout(info_row)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        sc_layout.addWidget(self.progress_bar)

        layout.addWidget(status_card)
        return page

    def _update_device_badge(self) -> None:
        try:
            import torch
            if torch.cuda.is_available():
                name = torch.cuda.get_device_name(0)
                mem = torch.cuda.get_device_properties(0).total_memory / (1024**3)
                self.device_badge.setText(f"GPU: {name} ({mem:.1f} GB) · CUDA")
            else:
                self.device_badge.setText("Thiết bị: CPU (Không có CUDA)")
        except Exception:
            self.device_badge.setText("Thiết bị: CPU / Standard")

    def _refresh_template_combo(self) -> None:
        self.template_combo.clear()
        for item in self.templates:
            self.template_combo.addItem(item.name, item.id)

    def _templates_changed(self, templates: list[VoiceTemplate]) -> None:
        self.templates = templates
        self._refresh_template_combo()

    def _open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.history, self)
        dialog.settings_saved.connect(self._settings_saved)
        dialog.exec()

    def _settings_saved(self, updated: AppSettings) -> None:
        self.settings = updated
        self.settings_store.save(updated)
        self._update_device_badge()

    def _open_preview(self) -> None:
        current_tpl_id = self.template_combo.currentData()
        dialog = PreviewDialog(
            engine_factory=self._engine_factory,
            settings=self.settings,
            templates=self.templates,
            current_template_id=current_tpl_id,
            preview_dir=self.paths.root / "preview",
            parent=self,
        )
        dialog.exec()

    def _add_files(self) -> None:
        files, _ = QFileDialog.getOpenFileNames(
            self, "Chọn file TXT", "", "Text files (*.txt);;Tất cả (*.*)"
        )
        if not files:
            return
        selected_tpl = self._get_selected_template()
        for f in files:
            path = Path(f)
            if not any(t.path == path for t in self.tasks):
                self.tasks.append(QueueTask(path=path, template=selected_tpl))
        self._refresh_summary()
        self._refresh_table()

    def _add_folder(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Chọn thư mục chứa file TXT")
        if not folder:
            return
        folder_path = Path(folder)
        pattern = "**/*.txt" if self.settings.recursive_folders else "*.txt"
        files = sorted(folder_path.glob(pattern))
        if not files:
            QMessageBox.information(
                self, "Thông báo", "Không tìm thấy file .txt nào trong thư mục này."
            )
            return
        selected_tpl = self._get_selected_template()
        added = 0
        for f in files:
            if not any(t.path == f for t in self.tasks):
                self.tasks.append(QueueTask(path=f, template=selected_tpl))
                added += 1
        self._refresh_summary()
        self._refresh_table()
        QMessageBox.information(self, "Đã thêm", f"Đã thêm {added} file TXT vào hàng chờ.")

    def _get_selected_template(self) -> VoiceTemplate:
        tid = self.template_combo.currentData()
        for t in self.templates:
            if t.id == tid:
                return t
        return self.templates[0] if self.templates else VoiceTemplate(name="Mặc định")

    def _clear_queue(self) -> None:
        if self.run_thread is not None and self.run_thread.isRunning():
            QMessageBox.warning(self, "Cảnh báo", "Không thể xóa hàng chờ khi đang chạy.")
            return
        self.tasks.clear()
        self.current_task_id = None
        self.current_page = 0
        self.table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.status_text.setText("Đã xóa hàng chờ.")
        self._refresh_summary()

    def _open_output_dir(self) -> None:
        out_dir = Path(self.settings.output_dir) if self.settings.output_dir else self.paths.outputs
        out_dir.mkdir(parents=True, exist_ok=True)
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(out_dir.resolve())))

    def _refresh_summary(self) -> None:
        total_tasks = len(self.tasks)
        total_chunks = sum(len(t.chunks) for t in self.tasks)
        self.summary_text.setText(f"{total_tasks} file · {total_chunks} đoạn")

    def _current_active_task(self) -> QueueTask | None:
        if self.current_task_id:
            for t in self.tasks:
                if t.id == self.current_task_id:
                    return t
        return self.tasks[0] if self.tasks else None

    def _refresh_table(self) -> None:
        task = self._current_active_task()
        if not task or not task.chunks:
            self.table.setRowCount(0)
            self.page_label.setText("Trang 1 / 1")
            self.table_title.setText("Chi tiết phân đoạn (50 đoạn mỗi trang)")
            return

        chunks = task.chunks
        total_pages = max(1, (len(chunks) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
        self.current_page = min(self.current_page, total_pages - 1)

        start = self.current_page * self.PAGE_SIZE
        end = min(start + self.PAGE_SIZE, len(chunks))
        page_chunks = chunks[start:end]

        self.table.setRowCount(len(page_chunks))
        for row, chunk in enumerate(page_chunks):
            # Cột 0: Đoạn
            it_idx = QTableWidgetItem(f"#{chunk.index}")
            it_idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 0, it_idx)

            # Cột 1: Nội dung
            it_txt = QTableWidgetItem(chunk.text)
            self.table.setItem(row, 1, it_txt)

            # Cột 2: Thời gian
            dur_str = f"{chunk.elapsed_seconds:.1f}s" if chunk.elapsed_seconds is not None else "--"
            it_dur = QTableWidgetItem(dur_str)
            it_dur.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 2, it_dur)

            # Cột 3: Trạng thái
            st_text = chunk.status.value
            if chunk.index == self.active_chunk_index:
                st_text = "Đang chạy…"
            it_st = QTableWidgetItem(st_text)
            it_st.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if chunk.status == TaskStatus.SUCCESS:
                it_st.setForeground(Qt.GlobalColor.darkGreen)
            elif chunk.status == TaskStatus.ERROR:
                it_st.setForeground(Qt.GlobalColor.red)
            self.table.setItem(row, 3, it_st)

            # Cột 4: Chi tiết
            it_msg = QTableWidgetItem(chunk.message)
            self.table.setItem(row, 4, it_msg)

        self.page_label.setText(f"Trang {self.current_page + 1} / {total_pages}")
        self.table_title.setText(f"Chi tiết: [{task.path.name}] ({len(chunks)} đoạn)")

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.current_page -= 1
            self._refresh_table()

    def _next_page(self) -> None:
        task = self._current_active_task()
        if task:
            total_pages = max(1, (len(task.chunks) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)
            if self.current_page < total_pages - 1:
                self.current_page += 1
                self._refresh_table()

    # ── Điều khiển xử lý ────────────────────────────────────────────────────────

    def _start_run(self) -> None:
        if not self.tasks:
            QMessageBox.warning(self, "Thông báo", "Hàng chờ rỗng. Hãy thêm file TXT hoặc folder trước.")
            return

        self.session_log = SessionLog(
            Path(self.settings.log_dir).expanduser(),
            self.settings.log_retention_days,
            lambda msg, lvl: self.log_received.emit(msg, lvl),
        )
        self.log_page.begin_session(self.session_log.path)

        self.processor = QueueProcessor(
            settings=self.settings,
            history=self.history,
            logger=self.session_log.logger,
            engine_factory=self._engine_factory,
        )

        self.run_thread = QThread(self)
        self.run_worker = RunWorker(self.processor, self.tasks)
        self.run_worker.moveToThread(self.run_thread)

        self.run_thread.started.connect(self.run_worker.run)
        self.run_worker.model_status.connect(self.status_text.setText)
        self.run_worker.file_started.connect(self._on_file_started)
        self.run_worker.chunks_prepared.connect(self._on_chunks_prepared)
        self.run_worker.chunk_started.connect(self._on_chunk_started)
        self.run_worker.chunk_changed.connect(self._on_chunk_changed)
        self.run_worker.file_finished.connect(self._on_file_finished)
        self.run_worker.progress_changed.connect(self._on_progress_changed)
        self.run_worker.finished.connect(self._on_run_finished)

        self.start_btn.setEnabled(False)
        self.pause_btn.setEnabled(True)
        self.stop_btn.setEnabled(True)
        self.is_paused = False
        self.pause_btn.setText("⏸ Tạm dừng")

        self.run_started_at = time.monotonic()
        self.elapsed_timer.start()

        self.run_thread.start()

    def _toggle_pause(self) -> None:
        if not self.run_worker:
            return
        self.is_paused = not self.is_paused
        self.run_worker.set_paused(self.is_paused)
        if self.is_paused:
            self.pause_btn.setText("▶ Tiếp tục")
            self.status_text.setText("Tạm dừng an toàn sau đoạn hiện tại…")
        else:
            self.pause_btn.setText("⏸ Tạm dừng")
            self.status_text.setText("Đang tiếp tục xử lý…")

    def _stop_run(self) -> None:
        if not self.run_worker:
            return
        self.stop_btn.setEnabled(False)
        self.status_text.setText("Đang dừng an toàn sau đoạn hiện tại…")
        self.run_worker.stop()

    def _on_file_started(self, task_id: str) -> None:
        self.current_task_id = task_id
        self.active_chunk_index = None
        self._refresh_table()

    def _on_chunks_prepared(self, task_id: str, chunks: list) -> None:
        for t in self.tasks:
            if t.id == task_id:
                t.chunks = chunks
                break
        self._refresh_summary()
        self._refresh_table()

    def _on_chunk_started(self, task_id: str, chunk_index: int) -> None:
        self.current_task_id = task_id
        self.active_chunk_index = chunk_index
        self._refresh_table()

    def _on_chunk_changed(self, task_id: str, index: int, status, elapsed, msg) -> None:
        for t in self.tasks:
            if t.id == task_id:
                for c in t.chunks:
                    if c.index == index:
                        c.status = status
                        c.elapsed_seconds = elapsed
                        c.message = msg
                        break
                break
        if self.active_chunk_index == index:
            self.active_chunk_index = None
        self._refresh_table()

    def _on_file_finished(self, task_id: str, status, msg, out_path) -> None:
        for t in self.tasks:
            if t.id == task_id:
                t.status = status
                t.message = msg
                t.output_path = out_path
                break
        self._refresh_table()

    def _on_progress_changed(self, done_chunks: int, total_chunks: int, total_files: int) -> None:
        if total_chunks > 0:
            pct = int((done_chunks / total_chunks) * 100)
            self.progress_bar.setValue(pct)
            self.summary_text.setText(f"{done_chunks}/{total_chunks} đoạn · {total_files} file")

    def _on_run_finished(self, result: dict) -> None:
        self.elapsed_timer.stop()
        self.start_btn.setEnabled(True)
        self.pause_btn.setEnabled(False)
        self.stop_btn.setEnabled(False)
        self.active_chunk_index = None

        if self.session_log:
            self.session_log.close()
            self.session_log = None

        if self.run_thread:
            self.run_thread.quit()
            self.run_thread.wait(2000)
            self.run_thread = None
            self.run_worker = None

        success = result.get("success", 0)
        skipped = result.get("skipped", 0)
        errors = result.get("errors", 0)
        self.status_text.setText(
            f"Hoàn thành: {success} thành công, {skipped} bỏ qua, {errors} lỗi."
        )
        self._refresh_table()

        if self.settings.auto_open_output and success > 0:
            self._open_output_dir()

        QMessageBox.information(
            self,
            "Kết thúc phiên chạy",
            f"Xử lý hoàn tất!\n• Thành công: {success}\n• Bỏ qua: {skipped}\n• Lỗi: {errors}\n"
            f"Thời gian: {result.get('elapsed', '0')}s",
        )

    def _update_elapsed(self) -> None:
        if self.run_started_at > 0:
            secs = int(time.monotonic() - self.run_started_at)
            mins = secs // 60
            s = secs % 60
            self.elapsed_text.setText(f"Thời gian: {mins:02d}:{s:02d}")

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.run_thread is not None and self.run_thread.isRunning():
            confirm = QMessageBox.question(
                self,
                "Đang xử lý",
                "Quá trình tạo audio đang diễn ra. Bạn có chắc muốn dừng và thoát ứng dụng?",
            )
            if confirm != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            if self.run_worker:
                self.run_worker.stop()
            self.run_thread.quit()
            self.run_thread.wait(2000)
        event.accept()
