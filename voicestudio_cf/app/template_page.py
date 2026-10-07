"""Voice template management page for VoiceStudio_CF."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from .domain import VoiceMode, VoiceTemplate
from .storage import TemplateStore


class TemplatePage(QWidget):
    templates_changed = Signal(object)

    def __init__(
        self, store: TemplateStore, templates: list[VoiceTemplate], parent=None
    ):
        super().__init__(parent)
        self.store = store
        self.templates = templates
        self.editing_id: str | None = None
        self._build_ui()
        self._refresh_list()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 20, 20, 20)
        title = QLabel("Quản lý template giọng")
        title.setObjectName("PageTitle")
        subtitle = QLabel(
            "Tạo cấu hình giọng nói dùng lại cho hàng chờ batch processing. "
            "Hỗ trợ Clone giọng mẫu, Thiết kế giọng theo mô tả, và Giọng tự động từ VoiceStudio."
        )
        subtitle.setProperty("muted", True)
        root.addWidget(title)
        root.addWidget(subtitle)

        body = QHBoxLayout()
        body.setSpacing(14)
        root.addLayout(body, 1)

        left = QFrame()
        left.setProperty("card", True)
        left.setFixedWidth(320)
        left_layout = QVBoxLayout(left)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Tìm template…")
        self.search.textChanged.connect(self._refresh_list)
        self.list_widget = QListWidget()
        self.list_widget.currentItemChanged.connect(self._select_item)

        add_button = QPushButton("+ Thêm template mới")
        add_button.setProperty("primary", True)
        add_button.clicked.connect(self.new_template)
        duplicate_button = QPushButton("Nhân bản template")
        duplicate_button.clicked.connect(self.duplicate_template)
        restore_button = QPushButton("Khôi phục mặc định")
        restore_button.clicked.connect(self.restore_defaults)

        left_layout.addWidget(self.search)
        left_layout.addWidget(self.list_widget, 1)
        left_layout.addWidget(add_button)
        left_layout.addWidget(duplicate_button)
        left_layout.addWidget(restore_button)
        body.addWidget(left)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        form_container = QFrame()
        form_container.setProperty("card", True)
        scroll.setWidget(form_container)
        body.addWidget(scroll, 1)

        form_root = QVBoxLayout(form_container)
        form_root.setContentsMargins(20, 18, 20, 18)
        form_title = QLabel("Cấu hình chi tiết template")
        form_title.setObjectName("CardTitle")
        form_root.addWidget(form_title)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        self.name = QLineEdit()
        self.description = QTextEdit()
        self.description.setMaximumHeight(65)

        self.engine = QComboBox()
        self.engine.addItem("VoiceStudio OmniVoice (Đa ngôn ngữ · Clone & Design)", "omnivoice")
        self.engine.addItem("Sherpa-ONNX (Offline · CPU siêu nhẹ)", "sherpa-onnx")
        self.engine.addItem("Mock Engine (Kiểm thử tức thì không cần GPU)", "mock")

        self.mode = QComboBox()
        self.mode.addItem("Clone giọng mẫu (Voice Cloning)", VoiceMode.CLONE.value)
        self.mode.addItem("Thiết kế giọng (Voice Design)", VoiceMode.DESIGN.value)
        self.mode.addItem("Giọng tự động (Auto Speech)", VoiceMode.AUTO.value)
        self.mode.currentIndexChanged.connect(self._update_mode_visibility)

        self.language = QComboBox()
        self.language.setEditable(True)
        self.language.addItems(
            ["Vietnamese", "English", "Chinese", "Japanese", "Korean", "Auto"]
        )

        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.5, 2.0)
        self.speed.setSingleStep(0.05)
        self.speed.setDecimals(2)
        self.speed.setSuffix("x")

        self.steps = QComboBox()
        for step in (16, 24, 32, 48, 64):
            self.steps.addItem(f"{step} bước", step)

        self.guidance = QDoubleSpinBox()
        self.guidance.setRange(1.0, 5.0)
        self.guidance.setSingleStep(0.1)
        self.guidance.setDecimals(2)

        self.denoise = QCheckBox("Khử nhiễu nền (Denoise)")
        self.postprocess = QCheckBox("Xử lý âm thanh sau khi tạo")
        self.normalize_text = QCheckBox("Chuẩn hóa văn bản số và ký hiệu")

        form.addRow("Tên template", self.name)
        form.addRow("Mô tả", self.description)
        form.addRow("Động cơ TTS", self.engine)
        form.addRow("Chế độ giọng", self.mode)
        form.addRow("Ngôn ngữ", self.language)
        form.addRow("Tốc độ", self.speed)
        form.addRow("Số bước sinh", self.steps)
        form.addRow("Thang hướng dẫn", self.guidance)
        form.addRow("", self.denoise)
        form.addRow("", self.postprocess)
        form.addRow("", self.normalize_text)
        form_root.addLayout(form)

        # Hộp cấu hình Clone giọng
        self.clone_group = QGroupBox("Cấu hình Clone giọng mẫu")
        clone_layout = QFormLayout(self.clone_group)
        ref_row = QHBoxLayout()
        self.ref_audio = QLineEdit()
        self.ref_audio.setPlaceholderText("Đường dẫn file .mp3, .wav mẫu (3-15 giây)…")
        browse_audio = QPushButton("Chọn file…")
        browse_audio.clicked.connect(self._browse_ref_audio)
        play_audio = QPushButton("Nghe thử")
        play_audio.clicked.connect(self._play_ref_audio)
        ref_row.addWidget(self.ref_audio, 1)
        ref_row.addWidget(browse_audio)
        ref_row.addWidget(play_audio)
        clone_layout.addRow("Audio mẫu", ref_row)

        self.ref_text = QTextEdit()
        self.ref_text.setMaximumHeight(70)
        self.ref_text.setPlaceholderText(
            "Lời thoại chính xác trong audio mẫu (giúp clone tự nhiên và chuẩn xác nhất)"
        )
        clone_layout.addRow("Lời thoại mẫu", self.ref_text)
        form_root.addWidget(self.clone_group)

        # Hộp cấu hình Thiết kế giọng
        self.design_group = QGroupBox("Cấu hình Thiết kế giọng (Voice Design)")
        design_layout = QFormLayout(self.design_group)
        self.gender = QComboBox()
        self.gender.addItems(["", "male", "female"])
        self.age = QComboBox()
        self.age.addItems(["", "child", "young adult", "middle-aged", "elderly"])
        self.pitch = QComboBox()
        self.pitch.addItems(["", "low pitch", "moderate pitch", "high pitch"])
        self.style = QComboBox()
        self.style.setEditable(True)
        self.style.addItems(["", "whisper", "calm", "dramatic", "cheerful", "news anchor"])
        self.accent = QLineEdit()
        self.accent.setPlaceholderText("Ví dụ: Northern, Southern, American…")
        self.instruct = QTextEdit()
        self.instruct.setMaximumHeight(65)
        self.instruct.setPlaceholderText("Mô tả bổ sung giọng nói (ví dụ: warm voice, energetic tone…)")
        design_layout.addRow("Giới tính", self.gender)
        design_layout.addRow("Độ tuổi", self.age)
        design_layout.addRow("Cao độ", self.pitch)
        design_layout.addRow("Phong cách", self.style)
        design_layout.addRow("Vùng miền / Accent", self.accent)
        design_layout.addRow("Hướng dẫn thêm", self.instruct)
        form_root.addWidget(self.design_group)

        actions = QHBoxLayout()
        actions.setContentsMargins(0, 10, 0, 0)
        self.save_button = QPushButton("Lưu template")
        self.save_button.setProperty("primary", True)
        self.save_button.clicked.connect(self.save_template)
        self.delete_button = QPushButton("Xóa template")
        self.delete_button.setProperty("danger", True)
        self.delete_button.clicked.connect(self.delete_template)
        actions.addStretch(1)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.save_button)
        form_root.addLayout(actions)
        form_root.addStretch(1)

        self._update_mode_visibility()

    def _update_mode_visibility(self) -> None:
        mode = self.mode.currentData()
        self.clone_group.setVisible(mode == VoiceMode.CLONE.value)
        self.design_group.setVisible(mode == VoiceMode.DESIGN.value)

    def _refresh_list(self) -> None:
        query = self.search.text().strip().lower()
        current_id = self.editing_id
        self.list_widget.clear()
        matching = [
            item
            for item in self.templates
            if not query or query in item.name.lower() or query in item.description.lower()
        ]
        select_row = -1
        for row, item in enumerate(matching):
            label = item.name
            if item.builtin:
                label += " [Mặc định]"
            self.list_widget.addItem(label)
            self.list_widget.item(row).setData(Qt.ItemDataRole.UserRole, item.id)
            if item.id == current_id:
                select_row = row

        if select_row >= 0:
            self.list_widget.setCurrentRow(select_row)
        elif self.list_widget.count() > 0:
            self.list_widget.setCurrentRow(0)

    def _select_item(self, current, _previous) -> None:
        if not current:
            return
        template_id = current.data(Qt.ItemDataRole.UserRole)
        template = next((t for t in self.templates if t.id == template_id), None)
        if not template:
            return
        self.editing_id = template.id
        self.name.setText(template.name)
        self.description.setPlainText(template.description)

        idx = self.engine.findData(template.engine)
        if idx >= 0:
            self.engine.setCurrentIndex(idx)

        idx = self.mode.findData(template.mode)
        if idx >= 0:
            self.mode.setCurrentIndex(idx)

        self.language.setCurrentText(template.language)
        self.speed.setValue(template.speed)

        step_idx = self.steps.findData(template.num_step)
        if step_idx >= 0:
            self.steps.setCurrentIndex(step_idx)
        else:
            self.steps.setCurrentIndex(2)

        self.guidance.setValue(template.guidance_scale)
        self.denoise.setChecked(template.denoise)
        self.postprocess.setChecked(template.postprocess_output)
        self.normalize_text.setChecked(template.normalize_text)

        self.ref_audio.setText(template.ref_audio)
        self.ref_text.setPlainText(template.ref_text)

        self.gender.setCurrentText(template.gender)
        self.age.setCurrentText(template.age)
        self.pitch.setCurrentText(template.pitch)
        self.style.setCurrentText(template.style)
        self.accent.setText(template.accent)
        self.instruct.setPlainText(template.instruct)

        self.delete_button.setEnabled(not template.builtin)
        self._update_mode_visibility()

    def new_template(self) -> None:
        created = VoiceTemplate(
            name="Template mới",
            description="",
            engine=self.engine.currentData() or "omnivoice",
            mode=VoiceMode.CLONE.value,
            language="Vietnamese",
            speed=1.0,
            num_step=32,
        )
        self.templates.append(created)
        self.editing_id = created.id
        self._persist()
        self._refresh_list()

    def duplicate_template(self) -> None:
        template = self._current_template()
        if not template:
            return
        copied = replace(
            template,
            id=VoiceTemplate(name="").id,
            name=f"{template.name} (Bản sao)",
            builtin=False,
        )
        self.templates.append(copied)
        self.editing_id = copied.id
        self._persist()
        self._refresh_list()

    def restore_defaults(self) -> None:
        answer = QMessageBox.question(
            self,
            "Khôi phục mặc định",
            "Bạn có chắc muốn khôi phục danh sách template mặc định?",
        )
        if answer == QMessageBox.StandardButton.Yes:
            self.templates = self.store.restore_defaults()
            self.editing_id = self.templates[0].id if self.templates else None
            self.templates_changed.emit(self.templates)
            self._refresh_list()

    def save_template(self) -> None:
        template = self._current_template()
        if not template:
            return
        name = self.name.text().strip()
        if not name:
            QMessageBox.warning(self, "Lỗi", "Tên template không được để trống.")
            return

        updated = replace(
            template,
            name=name,
            description=self.description.toPlainText().strip(),
            engine=self.engine.currentData(),
            mode=self.mode.currentData(),
            language=self.language.currentText().strip() or "Vietnamese",
            speed=self.speed.value(),
            num_step=self.steps.currentData(),
            guidance_scale=self.guidance.value(),
            denoise=self.denoise.isChecked(),
            postprocess_output=self.postprocess.isChecked(),
            normalize_text=self.normalize_text.isChecked(),
            ref_audio=self.ref_audio.text().strip(),
            ref_text=self.ref_text.toPlainText().strip(),
            gender=self.gender.currentText(),
            age=self.age.currentText(),
            pitch=self.pitch.currentText(),
            style=self.style.currentText().strip(),
            accent=self.accent.text().strip(),
            instruct=self.instruct.toPlainText().strip(),
        )
        self.templates = [
            updated if t.id == updated.id else t for t in self.templates
        ]
        self._persist()
        self._refresh_list()
        QMessageBox.information(self, "Thành công", f"Đã lưu template '{name}'.")

    def delete_template(self) -> None:
        template = self._current_template()
        if not template or template.builtin:
            return
        confirm = QMessageBox.question(
            self,
            "Xác nhận xóa",
            f"Bạn có chắc muốn xóa template '{template.name}'?",
        )
        if confirm == QMessageBox.StandardButton.Yes:
            self.templates = [t for t in self.templates if t.id != template.id]
            self.editing_id = self.templates[0].id if self.templates else None
            self._persist()
            self._refresh_list()

    def _browse_ref_audio(self) -> None:
        selected, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn audio giọng mẫu",
            self.ref_audio.text() or "",
            "Audio (*.wav *.mp3 *.flac *.m4a *.ogg);;Tất cả (*.*)",
        )
        if selected:
            self.ref_audio.setText(selected)

    def _play_ref_audio(self) -> None:
        ref_path = Path(self.ref_audio.text().strip())
        if ref_path.is_file():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(ref_path.resolve())))
        else:
            QMessageBox.warning(self, "Lỗi", "Chưa chọn file audio mẫu hợp lệ.")

    def _current_template(self) -> VoiceTemplate | None:
        return next((t for t in self.templates if t.id == self.editing_id), None)

    def _persist(self) -> None:
        self.store.save(self.templates)
        self.templates_changed.emit(self.templates)
