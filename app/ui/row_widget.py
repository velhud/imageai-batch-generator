from __future__ import annotations

from pathlib import Path
from typing import Callable, Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets
import re

from app.models import GlobalSettings, RowData, RowSettings, RowStatus, effective_settings


class ClickableLabel(QtWidgets.QLabel):
    clicked = QtCore.Signal()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # noqa: N802
        self.clicked.emit()
        return super().mousePressEvent(event)


class PromptHighlighter(QtGui.QSyntaxHighlighter):
    """Minimal syntax highlighter for weighting/placeholder syntax."""

    def __init__(self, parent: QtGui.QTextDocument) -> None:
        super().__init__(parent)
        self.patterns = [
            (re.compile(r"\{[^}]+\}"), QtGui.QColor("#3366ff")),
            (re.compile(r"\([^)]+\)"), QtGui.QColor("#cc6600")),
            (re.compile(r"\[[^\]]+\]"), QtGui.QColor("#009966")),
        ]

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, color in self.patterns:
            for match in pattern.finditer(text):
                start, end = match.span()
                fmt = QtGui.QTextCharFormat()
                fmt.setForeground(color)
                self.setFormat(start, end - start, fmt)


class RowWidget(QtWidgets.QWidget):
    generate_requested = QtCore.Signal(str)
    regenerate_requested = QtCore.Signal(str)
    cancel_requested = QtCore.Signal(str)
    duplicate_requested = QtCore.Signal(str)
    delete_requested = QtCore.Signal(str)
    export_requested = QtCore.Signal(str)
    selection_changed = QtCore.Signal(str, bool)
    open_gallery_requested = QtCore.Signal(str)
    settings_changed = QtCore.Signal(str)

    def __init__(
        self,
        row: RowData,
        index: int,
        provider_models: Dict[str, List[str]],
        global_settings: GlobalSettings,
        parent: Optional[QtWidgets.QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.row = row
        self.provider_models = provider_models
        self.global_settings = global_settings
        self._build_ui(index)
        self.refresh(global_settings, index)

    def _build_ui(self, index: int) -> None:
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        # Left column with index and checkbox
        left = QtWidgets.QVBoxLayout()
        idx_label = QtWidgets.QLabel(f"{index}")
        idx_label.setFixedWidth(24)
        idx_label.setAlignment(QtCore.Qt.AlignCenter)
        self.index_label = idx_label
        self.select_box = QtWidgets.QCheckBox()
        self.select_box.stateChanged.connect(self._on_select_changed)
        left.addWidget(idx_label)
        left.addWidget(self.select_box)
        left.addStretch()
        layout.addLayout(left)

        # Middle: prompt and settings
        mid = QtWidgets.QVBoxLayout()
        self.prompt_edit = QtWidgets.QTextEdit()
        self.prompt_edit.setPlaceholderText("Enter prompt...")
        self.prompt_edit.setFixedHeight(90)
        self.prompt_edit.textChanged.connect(self._on_prompt_changed)
        mid.addWidget(self.prompt_edit)

        info_row = QtWidgets.QHBoxLayout()
        self.char_count = QtWidgets.QLabel("0 chars")
        info_row.addWidget(self.char_count)
        copy_prompt_btn = QtWidgets.QPushButton("Copy prompt")
        copy_prompt_btn.clicked.connect(self._copy_prompt)
        info_row.addWidget(copy_prompt_btn)
        info_row.addStretch()
        mid.addLayout(info_row)

        self.status_label = QtWidgets.QLabel("Idle")
        mid.addWidget(self.status_label)

        self.batch_meta_label = QtWidgets.QLabel("")
        mid.addWidget(self.batch_meta_label)

        self.tags_edit = QtWidgets.QLineEdit()
        self.tags_edit.setPlaceholderText("Tags (comma separated)")
        self.tags_edit.editingFinished.connect(self._on_tags_changed)
        mid.addWidget(self.tags_edit)

        self._build_settings_panel(mid)
        self._build_actions(mid)
        layout.addLayout(mid, stretch=4)

        # Right: preview
        right = QtWidgets.QVBoxLayout()
        self.preview = ClickableLabel()
        self.preview.setFixedSize(160, 160)
        self.preview.setFrameShape(QtWidgets.QFrame.Box)
        self.preview.setAlignment(QtCore.Qt.AlignCenter)
        self.preview.setText("No image")
        self.preview.clicked.connect(lambda: self.open_gallery_requested.emit(self.row.id))
        right.addWidget(self.preview)
        self.thumb_meta = QtWidgets.QLabel("")
        right.addWidget(self.thumb_meta)
        btns = QtWidgets.QHBoxLayout()
        copy_img_btn = QtWidgets.QPushButton("Copy image")
        copy_img_btn.clicked.connect(self._copy_image)
        open_btn = QtWidgets.QPushButton("Open in Finder")
        open_btn.clicked.connect(self._open_in_finder)
        btns.addWidget(copy_img_btn)
        btns.addWidget(open_btn)
        right.addLayout(btns)
        layout.addLayout(right, stretch=1)

    def _build_settings_panel(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        self.settings_group = QtWidgets.QGroupBox("Per-row settings")
        self.settings_group.setCheckable(True)
        self.settings_group.setChecked(False)
        form = QtWidgets.QFormLayout()

        self.provider_combo = QtWidgets.QComboBox()
        for pid in self.provider_models.keys():
            self.provider_combo.addItem(pid, pid)
        self.provider_combo.currentTextChanged.connect(self._on_setting_change)
        form.addRow("Provider override", self.provider_combo)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.currentTextChanged.connect(self._on_setting_change)
        form.addRow("Model", self.model_combo)

        self.size_combo = QtWidgets.QComboBox()
        self.size_combo.addItems(["", "Square 1024", "Portrait", "Landscape", "Custom"])
        self.size_combo.currentTextChanged.connect(self._on_setting_change)
        form.addRow("Size", self.size_combo)

        self.num_spin = QtWidgets.QSpinBox()
        self.num_spin.setRange(1, 8)
        self.num_spin.valueChanged.connect(self._on_setting_change)
        form.addRow("Images", self.num_spin)

        self.style_combo = QtWidgets.QComboBox()
        self.style_combo.addItems(["", "None", "Photorealistic", "Illustration", "3D Render"])
        self.style_combo.currentTextChanged.connect(self._on_setting_change)
        form.addRow("Style", self.style_combo)

        self.negative_edit = QtWidgets.QTextEdit()
        self.negative_edit.setFixedHeight(50)
        self.negative_edit.textChanged.connect(self._on_setting_change)
        form.addRow("Negative prompt", self.negative_edit)

        seed_layout = QtWidgets.QHBoxLayout()
        self.seed_spin = QtWidgets.QSpinBox()
        self.seed_spin.setRange(0, 999999999)
        self.seed_spin.valueChanged.connect(self._on_setting_change)
        self.random_seed_box = QtWidgets.QCheckBox("Random")
        self.random_seed_box.setChecked(True)
        self.random_seed_box.stateChanged.connect(self._on_setting_change)
        seed_layout.addWidget(self.seed_spin)
        seed_layout.addWidget(self.random_seed_box)
        form.addRow("Seed", seed_layout)

        self.quality_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.quality_slider.setRange(1, 10)
        self.quality_slider.setValue(5)
        self.quality_slider.valueChanged.connect(self._on_setting_change)
        form.addRow("Quality", self.quality_slider)

        self.safety_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.safety_slider.setRange(0, 3)
        self.safety_slider.setValue(2)
        self.safety_slider.valueChanged.connect(self._on_setting_change)
        form.addRow("Safety", self.safety_slider)

        reset_btn = QtWidgets.QPushButton("Reset to global defaults")
        reset_btn.clicked.connect(self.reset_to_global)
        form.addRow(reset_btn)

        self.settings_group.setLayout(form)
        parent_layout.addWidget(self.settings_group)

    def _build_actions(self, parent_layout: QtWidgets.QVBoxLayout) -> None:
        btn_row = QtWidgets.QHBoxLayout()
        self.generate_btn = QtWidgets.QPushButton("Generate")
        self.generate_btn.setProperty("class", "primary")
        self.generate_btn.clicked.connect(lambda: self.generate_requested.emit(self.row.id))
        btn_row.addWidget(self.generate_btn)

        self.generate_behavior = QtWidgets.QComboBox()
        self.generate_behavior.addItems(["Keep images", "Replace images"])
        self.generate_behavior.currentIndexChanged.connect(self._on_setting_change)
        btn_row.addWidget(self.generate_behavior)

        self.regen_btn = QtWidgets.QPushButton("Regenerate")
        self.regen_btn.clicked.connect(lambda: self.regenerate_requested.emit(self.row.id))
        btn_row.addWidget(self.regen_btn)
        self.regen_btn.setVisible(False)

        self.regen_same_seed = QtWidgets.QCheckBox("Same seed")
        self.regen_same_seed.stateChanged.connect(self._on_setting_change)
        btn_row.addWidget(self.regen_same_seed)

        self.stop_btn = QtWidgets.QPushButton("Stop")
        self.stop_btn.clicked.connect(lambda: self.cancel_requested.emit(self.row.id))
        btn_row.addWidget(self.stop_btn)

        self.duplicate_btn = QtWidgets.QPushButton("Duplicate")
        self.duplicate_btn.clicked.connect(lambda: self.duplicate_requested.emit(self.row.id))
        btn_row.addWidget(self.duplicate_btn)

        self.delete_btn = QtWidgets.QPushButton("Delete")
        self.delete_btn.clicked.connect(lambda: self.delete_requested.emit(self.row.id))
        btn_row.addWidget(self.delete_btn)

        self.export_btn = QtWidgets.QPushButton("Export")
        self.export_btn.clicked.connect(lambda: self.export_requested.emit(self.row.id))
        btn_row.addWidget(self.export_btn)
        parent_layout.addLayout(btn_row)

    def _on_select_changed(self, state: int) -> None:
        self.row.selected = state == QtCore.Qt.Checked
        self.selection_changed.emit(self.row.id, self.row.selected)

    def _on_tags_changed(self) -> None:
        tags = [t.strip() for t in self.tags_edit.text().split(",") if t.strip()]
        self.row.tags = tags
        self.settings_changed.emit(self.row.id)

    def _on_prompt_changed(self) -> None:
        self.row.prompt = self.prompt_edit.toPlainText()
        self.char_count.setText(f"{len(self.row.prompt)} chars")
        self.settings_changed.emit(self.row.id)

    def _on_setting_change(self) -> None:
        settings = RowSettings(
            provider_id=self.provider_combo.currentText() or None,
            model_id=self.model_combo.currentText() or None,
            size_preset=self.size_combo.currentText() or None,
            num_images=self.num_spin.value(),
            style_preset=self.style_combo.currentText() or None,
            negative_prompt=self.negative_edit.toPlainText() or None,
            seed=None if self.random_seed_box.isChecked() else self.seed_spin.value(),
            random_seed=self.random_seed_box.isChecked(),
            quality=self.quality_slider.value(),
            safety=self.safety_slider.value(),
            keep_images=self.generate_behavior.currentText().startswith("Keep"),
            generate_behavior="keep" if self.generate_behavior.currentText().startswith("Keep") else "replace",
            regen_use_same_seed=self.regen_same_seed.isChecked(),
        )
        self.row.settings = settings
        self.settings_changed.emit(self.row.id)

    def reset_to_global(self) -> None:
        self.row.settings = RowSettings()
        self.refresh(self.global_settings, int(self.index_label.text()))
        self.settings_changed.emit(self.row.id)

    def _copy_prompt(self) -> None:
        QtGui.QGuiApplication.clipboard().setText(self.row.prompt or "")

    def _copy_image(self) -> None:
        if not self.row.images:
            return
        img_path = Path(self.row.images[-1].file_path)
        if img_path.exists():
            pix = QtGui.QPixmap(str(img_path))
            QtGui.QGuiApplication.clipboard().setPixmap(pix)

    def _open_in_finder(self) -> None:
        if not self.row.images:
            return
        img_path = Path(self.row.images[-1].file_path)
        if img_path.exists():
            QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(img_path)))

    def refresh(self, global_settings: GlobalSettings, index: int) -> None:
        self.global_settings = global_settings
        self.index_label.setText(str(index))
        self.select_box.setChecked(self.row.selected)
        self.prompt_edit.blockSignals(True)
        self.prompt_edit.setPlainText(self.row.prompt)
        self.prompt_edit.blockSignals(False)
        self.char_count.setText(f"{len(self.row.prompt)} chars")
        self.tags_edit.setText(", ".join(self.row.tags))
        eff = effective_settings(self.row, global_settings)
        self._populate_models(eff.provider_id)
        self.provider_combo.setCurrentText(self.row.settings.provider_id or "")
        self.model_combo.setCurrentText(self.row.settings.model_id or eff.model_id)
        self.size_combo.setCurrentText(self.row.settings.size_preset or eff.size_preset)
        self.num_spin.setValue(self.row.settings.num_images or eff.num_images)
        self.style_combo.setCurrentText(self.row.settings.style_preset or eff.style_preset)
        self.negative_edit.setPlainText(self.row.settings.negative_prompt or eff.negative_prompt)
        if self.row.settings.random_seed is None:
            self.random_seed_box.setChecked(eff.random_seed)
        else:
            self.random_seed_box.setChecked(self.row.settings.random_seed)
        self.seed_spin.setValue(self.row.settings.seed or eff.seed or 0)
        self.quality_slider.setValue(self.row.settings.quality or eff.quality)
        self.safety_slider.setValue(self.row.settings.safety or eff.safety)
        keep = (
            self.row.settings.keep_images
            if self.row.settings.keep_images is not None
            else (
                True
                if (self.row.settings.generate_behavior or eff.generate_behavior) != "replace"
                else False
            )
        )
        self.generate_behavior.setCurrentText("Keep images" if keep else "Replace images")
        self.regen_same_seed.setChecked(self.row.settings.regen_use_same_seed if self.row.settings.regen_use_same_seed is not None else eff.regen_use_same_seed)
        self.update_status(self.row.status, self.row.error_message)
        meta_parts = []
        if self.row.category_id:
            meta_parts.append(f"Category: {self.row.category_id}")
        if self.row.prompt_id:
            meta_parts.append(f"Prompt ID: {self.row.prompt_id}")
        if self.row.images:
            meta_parts.append(f"File: {Path(self.row.images[-1].file_path).name}")
        self.batch_meta_label.setText(" • ".join(meta_parts))
        self._update_preview()
        if self.global_settings.prompt_highlighting:
            PromptHighlighter(self.prompt_edit.document())

    def _populate_models(self, provider_id: str) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for model in self.provider_models.get(provider_id, []):
            self.model_combo.addItem(model, model)
        self.model_combo.blockSignals(False)

    def update_status(self, status: RowStatus, message: str = "") -> None:
        self.row.status = status
        self.row.error_message = message
        text = status.value
        if message:
            text = f"{text}: {message}"
        self.status_label.setText(text)
        self.regen_btn.setVisible(bool(self.row.images))
        self.export_btn.setEnabled(bool(self.row.images))
        self.stop_btn.setVisible(status == RowStatus.GENERATING)
        self.generate_btn.setEnabled(status in {RowStatus.IDLE, RowStatus.ERROR, RowStatus.FILTERED, RowStatus.CANCELLED, RowStatus.COMPLETED})

    def _update_preview(self) -> None:
        if self.row.images:
            img_path = Path(self.row.images[-1].file_path)
            if img_path.exists():
                pixmap = QtGui.QPixmap(str(img_path)).scaled(
                    self.preview.width(),
                    self.preview.height(),
                    QtCore.Qt.KeepAspectRatio,
                    QtCore.Qt.SmoothTransformation,
                )
                self.preview.setPixmap(pixmap)
                self.preview.setText("")
                self.thumb_meta.setText(f"{len(self.row.images)} image(s)")
                return
        self.preview.setPixmap(QtGui.QPixmap())
        self.preview.setText("No image")
        self.thumb_meta.setText("")
