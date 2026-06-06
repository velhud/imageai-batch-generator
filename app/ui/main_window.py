from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from PySide6 import QtCore, QtGui, QtWidgets
from app.exporter import ImageExporter
from app.models import GlobalSettings, ImageResult, RowData, RowSettings, RowStatus, SessionData, PromptTemplate
from app.providers.registry import ProviderRegistry
from app.queue_manager import GenerationQueue
from app.session_manager import SessionManager
from app.undo_manager import UndoManager
from app.stats import compute_stats
from app.tagging import filter_rows
from app.templates import expand_template, parse_variable_block
from .batch_dialog import BatchInputDialog
from .gallery import GalleryDialog
from .row_widget import RowWidget
from .settings_dialog import AppSettingsDialog
from .styles import BASE_STYLE


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, registry: ProviderRegistry, session_manager: SessionManager) -> None:
        super().__init__()
        self.registry = registry
        self.session_manager = session_manager
        self.session: SessionData = session_manager.session
        self.undo_manager = UndoManager()
        self.undo_manager.push(self.session)
        self.rate_limit_hits = 0
        self.queue = self._create_queue()
        self.row_widgets: Dict[str, RowWidget] = {}
        self.provider_models: Dict[str, List[str]] = self._build_provider_model_map()
        self.setWindowTitle("Imagen Batch Generator")
        self.setMinimumSize(1200, 800)
        self._build_ui()
        self._setup_shortcuts()
        self._start_autosave()
        self.apply_global_settings_to_ui()
        if not self.session.rows:
            self.add_row()
        else:
            self._reload_rows()

    def _build_provider_model_map(self) -> Dict[str, List[str]]:
        mapping: Dict[str, List[str]] = {}
        for info in self.registry.info_list():
            mapping[info.id] = [m.id for m in info.models]
        return mapping

    def _create_queue(self) -> GenerationQueue:
        queue = GenerationQueue(
            self.registry,
            output_root=self.session_manager.session_output_dir(),
            concurrency=self.session.global_settings.concurrency_limit,
            rpm=self.session.global_settings.rate_limit_rpm,
        )
        queue.register_listener(self._handle_queue_event)
        return queue

    def _reset_queue(self) -> None:
        if self.queue:
            self.queue.shutdown()
        self.queue = self._create_queue()

    def _build_ui(self) -> None:
        central = QtWidgets.QWidget()
        main_layout = QtWidgets.QVBoxLayout(central)
        main_layout.setContentsMargins(8, 8, 8, 8)

        self.top_bar = self._build_top_bar()
        main_layout.addLayout(self.top_bar)
        self.banner = QtWidgets.QLabel("")
        self.banner.setStyleSheet("background:#fff3cd;color:#8a6d3b;padding:6px;border:1px solid #f1e1a6;")
        self.banner.setVisible(False)
        main_layout.addWidget(self.banner)
        self.global_panel = self._build_global_panel()
        main_layout.addWidget(self.global_panel)

        self.scroll_area = QtWidgets.QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.rows_container = QtWidgets.QWidget()
        self.rows_layout = QtWidgets.QVBoxLayout(self.rows_container)
        self.rows_layout.setAlignment(QtCore.Qt.AlignTop)
        self.scroll_area.setWidget(self.rows_container)
        main_layout.addWidget(self.scroll_area, stretch=1)

        self.bottom_bar = self._build_bottom_bar()
        main_layout.addLayout(self.bottom_bar)

        self.setCentralWidget(central)
        self.setStyleSheet(BASE_STYLE)

    def _build_top_bar(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        self.provider_combo = QtWidgets.QComboBox()
        for info in self.registry.info_list():
            self.provider_combo.addItem(info.name, userData=info.id)
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        layout.addWidget(QtWidgets.QLabel("Provider"))
        layout.addWidget(self.provider_combo)

        self.model_combo = QtWidgets.QComboBox()
        self.model_combo.currentIndexChanged.connect(self._on_model_changed)
        layout.addWidget(QtWidgets.QLabel("Model"))
        layout.addWidget(self.model_combo)

        self.rate_limit_note = QtWidgets.QLabel("Rate limit: see provider docs")
        layout.addWidget(self.rate_limit_note)

        self.global_toggle = QtWidgets.QPushButton("Global Settings")
        self.global_toggle.setCheckable(True)
        self.global_toggle.setChecked(True)
        self.global_toggle.clicked.connect(self._toggle_global_panel)
        layout.addWidget(self.global_toggle)

        batch_btn = QtWidgets.QPushButton("Batch Input…")
        batch_btn.clicked.connect(self._open_batch_dialog)
        layout.addWidget(batch_btn)

        tpl_btn = QtWidgets.QPushButton("Templates…")
        tpl_btn.clicked.connect(self._open_templates_dialog)
        layout.addWidget(tpl_btn)

        new_btn = QtWidgets.QPushButton("New Session")
        new_btn.clicked.connect(self._new_session)
        layout.addWidget(new_btn)
        open_btn = QtWidgets.QPushButton("Open…")
        open_btn.clicked.connect(self._open_session)
        layout.addWidget(open_btn)
        save_btn = QtWidgets.QPushButton("Save…")
        save_btn.clicked.connect(self._save_session)
        layout.addWidget(save_btn)

        app_settings_btn = QtWidgets.QPushButton("App Settings…")
        app_settings_btn.clicked.connect(self._open_app_settings)
        layout.addWidget(app_settings_btn)

        stats_btn = QtWidgets.QPushButton("Statistics…")
        stats_btn.clicked.connect(self._open_stats)
        layout.addWidget(stats_btn)

        self.tag_filter_edit = QtWidgets.QLineEdit()
        self.tag_filter_edit.setPlaceholderText("Filter by tag…")
        self.tag_filter_edit.textChanged.connect(self._apply_tag_filter)
        layout.addWidget(self.tag_filter_edit)

        layout.addStretch()
        return layout

    def _build_global_panel(self) -> QtWidgets.QGroupBox:
        panel = QtWidgets.QGroupBox("Global Settings (defaults for new rows)")
        form = QtWidgets.QFormLayout(panel)
        self.size_combo = QtWidgets.QComboBox()
        self.size_combo.addItems(["Square 1024", "Portrait", "Landscape", "Custom"])
        self.size_combo.currentTextChanged.connect(self._global_changed)
        form.addRow("Image size", self.size_combo)

        self.num_spin = QtWidgets.QSpinBox()
        self.num_spin.setRange(1, 8)
        self.num_spin.valueChanged.connect(self._global_changed)
        form.addRow("Images per prompt", self.num_spin)

        self.style_combo = QtWidgets.QComboBox()
        self.style_combo.addItems(["None", "Photorealistic", "Illustration", "3D Render"])
        self.style_combo.currentTextChanged.connect(self._global_changed)
        form.addRow("Style preset", self.style_combo)

        self.negative_edit = QtWidgets.QTextEdit()
        self.negative_edit.setFixedHeight(60)
        self.negative_edit.textChanged.connect(self._global_changed)
        form.addRow("Negative prompt", self.negative_edit)

        seed_layout = QtWidgets.QHBoxLayout()
        self.seed_spin = QtWidgets.QSpinBox()
        self.seed_spin.setRange(0, 999999999)
        self.seed_spin.valueChanged.connect(self._global_changed)
        self.random_seed_box = QtWidgets.QCheckBox("Random seed")
        self.random_seed_box.setChecked(True)
        self.random_seed_box.stateChanged.connect(self._global_changed)
        seed_layout.addWidget(self.seed_spin)
        seed_layout.addWidget(self.random_seed_box)
        form.addRow("Seed", seed_layout)

        self.quality_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.quality_slider.setRange(1, 10)
        self.quality_slider.setValue(5)
        self.quality_slider.valueChanged.connect(self._global_changed)
        form.addRow("Quality", self.quality_slider)

        self.safety_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.safety_slider.setRange(0, 3)
        self.safety_slider.setValue(2)
        self.safety_slider.valueChanged.connect(self._global_changed)
        form.addRow("Safety/NSFW", self.safety_slider)

        self.prompt_highlight_box = QtWidgets.QCheckBox("Enable prompt highlighting")
        self.prompt_highlight_box.stateChanged.connect(self._global_changed)
        form.addRow(self.prompt_highlight_box)

        self.generate_behavior_combo = QtWidgets.QComboBox()
        self.generate_behavior_combo.addItems(["keep", "replace"])
        self.generate_behavior_combo.currentTextChanged.connect(self._global_changed)
        form.addRow("Generate behavior", self.generate_behavior_combo)

        self.regen_same_seed_box = QtWidgets.QCheckBox("Regenerate with same seed")
        self.regen_same_seed_box.setChecked(True)
        self.regen_same_seed_box.stateChanged.connect(self._global_changed)
        form.addRow(self.regen_same_seed_box)

        apply_btn = QtWidgets.QPushButton("Apply to selected")
        apply_btn.clicked.connect(self._apply_global_to_selected)
        form.addRow(apply_btn)

        note = QtWidgets.QLabel(
            "These settings are defaults for new rows. Existing rows keep their own settings unless you apply changes to them explicitly."
        )
        note.setWordWrap(True)
        form.addRow(note)
        return panel

    def _build_bottom_bar(self) -> QtWidgets.QHBoxLayout:
        layout = QtWidgets.QHBoxLayout()
        add_btn = QtWidgets.QPushButton("Add Row")
        add_btn.clicked.connect(self.add_row)
        layout.addWidget(add_btn)
        add_many_btn = QtWidgets.QPushButton("Add N Rows…")
        add_many_btn.clicked.connect(self._add_many_rows)
        layout.addWidget(add_many_btn)

        sel_all_btn = QtWidgets.QPushButton("Select All")
        sel_all_btn.clicked.connect(self._select_all)
        layout.addWidget(sel_all_btn)
        clear_sel_btn = QtWidgets.QPushButton("Clear Selection")
        clear_sel_btn.clicked.connect(self._clear_selection)
        layout.addWidget(clear_sel_btn)
        select_no_image_btn = QtWidgets.QPushButton("Select rows with no image")
        select_no_image_btn.clicked.connect(self._select_no_image)
        layout.addWidget(select_no_image_btn)
        select_pending_btn = QtWidgets.QPushButton("Select pending")
        select_pending_btn.clicked.connect(self._select_pending)
        layout.addWidget(select_pending_btn)

        gen_sel_btn = QtWidgets.QPushButton("Generate Selected")
        gen_sel_btn.clicked.connect(self._generate_selected)
        layout.addWidget(gen_sel_btn)
        gen_all_btn = QtWidgets.QPushButton("Generate All")
        gen_all_btn.clicked.connect(self._generate_all)
        layout.addWidget(gen_all_btn)
        stop_all = QtWidgets.QPushButton("Stop All")
        stop_all.clicked.connect(self.queue.cancel_all)
        layout.addWidget(stop_all)

        del_sel_btn = QtWidgets.QPushButton("Delete Selected")
        del_sel_btn.clicked.connect(self._delete_selected)
        layout.addWidget(del_sel_btn)
        del_all_btn = QtWidgets.QPushButton("Delete All")
        del_all_btn.clicked.connect(self._delete_all)
        layout.addWidget(del_all_btn)

        export_sel = QtWidgets.QPushButton("Export Selected")
        export_sel.clicked.connect(self._export_selected)
        layout.addWidget(export_sel)
        export_all = QtWidgets.QPushButton("Export All")
        export_all.clicked.connect(self._export_all)
        layout.addWidget(export_all)

        self.status_bar_label = QtWidgets.QLabel("")
        layout.addWidget(self.status_bar_label)
        layout.addStretch()
        return layout

    def _toggle_global_panel(self) -> None:
        self.global_panel.setVisible(self.global_toggle.isChecked())

    def apply_global_settings_to_ui(self) -> None:
        gs = self.session.global_settings
        self.size_combo.setCurrentText(gs.size_preset)
        self.num_spin.setValue(gs.num_images)
        self.style_combo.setCurrentText(gs.style_preset)
        self.negative_edit.setPlainText(gs.negative_prompt)
        self.random_seed_box.setChecked(gs.random_seed)
        self.seed_spin.setValue(gs.seed or 0)
        self.quality_slider.setValue(gs.quality)
        self.safety_slider.setValue(gs.safety)
        self.prompt_highlight_box.setChecked(gs.prompt_highlighting)
        self.generate_behavior_combo.setCurrentText(gs.generate_behavior)
        self.regen_same_seed_box.setChecked(gs.regen_use_same_seed)

        # top combos
        idx = self.provider_combo.findData(gs.provider_id)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self._populate_models(gs.provider_id)
        midx = self.model_combo.findData(gs.model_id)
        if midx >= 0:
            self.model_combo.setCurrentIndex(midx)

    def _populate_models(self, provider_id: str) -> None:
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        for info in self.registry.info_list():
            if info.id == provider_id:
                for m in info.models:
                    self.model_combo.addItem(m.name, userData=m.id)
                self.rate_limit_note.setText(info.rate_limit_note or "")
                break
        self.model_combo.blockSignals(False)

    def _global_changed(self) -> None:
        self._push_undo()
        gs = self.session.global_settings
        gs.size_preset = self.size_combo.currentText()
        gs.num_images = self.num_spin.value()
        gs.style_preset = self.style_combo.currentText()
        gs.negative_prompt = self.negative_edit.toPlainText()
        gs.random_seed = self.random_seed_box.isChecked()
        gs.seed = None if gs.random_seed else self.seed_spin.value()
        gs.quality = self.quality_slider.value()
        gs.safety = self.safety_slider.value()
        gs.prompt_highlighting = self.prompt_highlight_box.isChecked()
        gs.generate_behavior = self.generate_behavior_combo.currentText()
        gs.regen_use_same_seed = self.regen_same_seed_box.isChecked()
        self.session_manager.autosave()

    def _on_provider_changed(self) -> None:
        pid = self.provider_combo.currentData()
        self.session.global_settings.provider_id = pid
        self._populate_models(pid)
        # update global model id to first
        if self.model_combo.count() > 0:
            self.model_combo.setCurrentIndex(0)
        self._refresh_all_rows()

    def _on_model_changed(self) -> None:
        mid = self.model_combo.currentData()
        self.session.global_settings.model_id = mid
        self._refresh_all_rows()

    def _add_row_widget(self, row: RowData, index: int) -> None:
        widget = RowWidget(row, index, self.provider_models, self.session.global_settings)
        widget.generate_requested.connect(self._generate_row)
        widget.regenerate_requested.connect(self._regenerate_row)
        widget.cancel_requested.connect(lambda rid=row.id: self.queue.cancel(rid))
        widget.duplicate_requested.connect(self._duplicate_row)
        widget.delete_requested.connect(self._delete_row)
        widget.export_requested.connect(self._export_row)
        widget.selection_changed.connect(self._on_row_selection)
        widget.open_gallery_requested.connect(self._open_gallery)
        widget.settings_changed.connect(self._on_row_settings_changed)
        self.row_widgets[row.id] = widget
        self.rows_layout.addWidget(widget)

    def _reload_rows(self) -> None:
        # clear layout
        for i in reversed(range(self.rows_layout.count())):
            item = self.rows_layout.takeAt(i)
            if item and item.widget():
                item.widget().deleteLater()
        self.row_widgets.clear()
        for idx, row in enumerate(self.session.rows, start=1):
            self._add_row_widget(row, idx)
        self._update_status_summary()
        self._apply_tag_filter()

    def add_row(self) -> None:
        self._push_undo()
        row = RowData(id=str(uuid.uuid4()), prompt="")
        self.session.rows.append(row)
        self._add_row_widget(row, len(self.session.rows))
        self.session_manager.autosave()
        self._update_status_summary()

    def _add_many_rows(self) -> None:
        count, ok = QtWidgets.QInputDialog.getInt(self, "Add rows", "How many rows?", 10, 1, 500)
        if ok:
            self._push_undo()
            for _ in range(count):
                self.add_row()
        self._update_status_summary()

    def _select_all(self) -> None:
        for row in self.session.rows:
            row.selected = True
            self.row_widgets[row.id].select_box.setChecked(True)
        self._update_status_summary()

    def _clear_selection(self) -> None:
        for row in self.session.rows:
            row.selected = False
            self.row_widgets[row.id].select_box.setChecked(False)
        self._update_status_summary()

    def _select_no_image(self) -> None:
        for row in self.session.rows:
            has_image = bool(row.images)
            row.selected = not has_image
            self.row_widgets[row.id].select_box.setChecked(row.selected)
        self._update_status_summary()

    def _select_pending(self) -> None:
        for row in self.session.rows:
            row.selected = row.status != RowStatus.COMPLETED
            self.row_widgets[row.id].select_box.setChecked(row.selected)
        self._update_status_summary()

    def _generate_row(self, row_id: str) -> None:
        row = self._row_by_id(row_id)
        if not row:
            return
        row.status = RowStatus.QUEUED
        widget = self.row_widgets[row.id]
        widget.update_status(RowStatus.QUEUED)
        self.queue.enqueue(row, self.session.global_settings)
        self._update_status_summary()

    def _regenerate_row(self, row_id: str) -> None:
        row = self._row_by_id(row_id)
        if not row:
            return
        use_same_seed = (
            row.settings.regen_use_same_seed
            if row.settings.regen_use_same_seed is not None
            else self.session.global_settings.regen_use_same_seed
        )
        if not use_same_seed:
            row.settings.random_seed = True
            row.settings.seed = None
        self._generate_row(row_id)

    def _generate_selected(self) -> None:
        for row in self.session.rows:
            if row.selected and row.status in {RowStatus.IDLE, RowStatus.ERROR, RowStatus.CANCELLED, RowStatus.COMPLETED}:
                self._generate_row(row.id)

    def _generate_all(self) -> None:
        threshold = self.session.global_settings.confirm_generate_threshold or 300
        if len(self.session.rows) >= threshold:
            confirm = QtWidgets.QMessageBox.question(
                self, "Confirm large batch", f"Generate all {len(self.session.rows)} rows?"
            )
            if confirm != QtWidgets.QMessageBox.Yes:
                return
        for row in self.session.rows:
            if row.status in {RowStatus.IDLE, RowStatus.ERROR, RowStatus.CANCELLED, RowStatus.COMPLETED}:
                self._generate_row(row.id)

    def _delete_row(self, row_id: str) -> None:
        row = self._row_by_id(row_id)
        if not row:
            return
        self._push_undo()
        idx = self.session.rows.index(row)
        self.session.rows.remove(row)
        widget = self.row_widgets.pop(row_id)
        widget.deleteLater()
        # reindex
        for i, r in enumerate(self.session.rows, start=1):
            self.row_widgets[r.id].index_label.setText(str(i))
        self.session_manager.autosave()
        self._update_status_summary()

    def _duplicate_row(self, row_id: str) -> None:
        row = self._row_by_id(row_id)
        if not row:
            return
        self._push_undo()
        clone = RowData(
            id=str(uuid.uuid4()),
            prompt=row.prompt,
            status=RowStatus.IDLE,
            settings=RowSettings(**row.settings.to_dict()),
        )
        idx = self.session.rows.index(row) + 1
        self.session.rows.insert(idx, clone)
        self._reload_rows()
        self.session_manager.autosave()
        self._update_status_summary()

    def _delete_selected(self) -> None:
        to_delete = [r for r in self.session.rows if r.selected]
        if not to_delete:
            return
        confirm = QtWidgets.QMessageBox.question(
            self, "Delete selected", f"Delete {len(to_delete)} selected row(s)?"
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            self._push_undo()
            for r in list(to_delete):
                self._delete_row(r.id)
            self._update_status_summary()

    def _delete_all(self) -> None:
        confirm = QtWidgets.QMessageBox.question(
            self,
            "Confirm delete",
            "Delete all rows and their images from this session? This cannot be undone.",
        )
        if confirm == QtWidgets.QMessageBox.Yes:
            self._push_undo()
            self.session.rows.clear()
            self._reload_rows()
            self.session_manager.autosave()
            self._update_status_summary()

    def _on_row_selection(self, row_id: str, selected: bool) -> None:
        row = self._row_by_id(row_id)
        if row:
            row.selected = selected

    def _on_row_settings_changed(self, row_id: str) -> None:
        self._push_undo()
        # row object already mutated by widget; refresh derived data
        widget = self.row_widgets.get(row_id)
        if widget:
            widget.refresh(self.session.global_settings, int(widget.index_label.text()))
        self.session_manager.autosave()
        self._apply_tag_filter()

    def _handle_queue_event(self, event: str, row_id: str, payload: Dict) -> None:
        row = self._row_by_id(row_id)
        if not row:
            return
        widget = self.row_widgets.get(row_id)
        if event == "queued":
            row.status = RowStatus.QUEUED
            if widget:
                widget.update_status(RowStatus.QUEUED, f"Queued (#{payload.get('position','')})")
        elif event == "queue_position":
            if widget:
                widget.update_status(RowStatus.QUEUED, f"Queued (#{payload.get('position','')})")
        elif event == "started":
            row.status = RowStatus.GENERATING
            if widget:
                widget.update_status(RowStatus.GENERATING, "Generating…")
        elif event == "completed":
            row.status = RowStatus.COMPLETED
            row.error_message = ""
            paths = payload.get("paths", [])
            duration = payload.get("duration")
            keep_existing = payload.get("keep_existing", True)
            if not keep_existing:
                row.images = []
            row.last_duration = duration
            for p in paths:
                row.images.append(ImageResult(id=str(uuid.uuid4()), row_id=row.id, file_path=p))
            if widget:
                widget.update_status(RowStatus.COMPLETED, f"Completed: {len(row.images)} images")
                widget.refresh(self.session.global_settings, int(widget.index_label.text()))
        elif event == "error":
            row.status = RowStatus.ERROR
            row.error_message = payload.get("message", "")
            if widget:
                widget.update_status(RowStatus.ERROR, row.error_message)
            if "rate" in row.error_message.lower():
                self.rate_limit_hits += 1
                if self.rate_limit_hits >= 3:
                    self.banner.setText("Multiple rate limit errors detected. Try lowering concurrency or RPM in settings.")
                    self.banner.setVisible(True)
        elif event == "cancelled":
            row.status = RowStatus.CANCELLED
            if widget:
                widget.update_status(RowStatus.CANCELLED, "Cancelled")
        self.session_manager.autosave()
        self._update_status_summary()

    def _refresh_all_rows(self) -> None:
        for idx, row in enumerate(self.session.rows, start=1):
            widget = self.row_widgets.get(row.id)
            if widget:
                widget.refresh(self.session.global_settings, idx)
        self._update_status_summary()

    def _row_by_id(self, row_id: str) -> Optional[RowData]:
        for row in self.session.rows:
            if row.id == row_id:
                return row
        return None

    def _apply_global_to_selected(self) -> None:
        gs = self.session.global_settings
        for row in self.session.rows:
            if row.selected:
                row.settings = RowSettings()
                self.row_widgets[row.id].refresh(gs, int(self.row_widgets[row.id].index_label.text()))
        self.session_manager.autosave()

    def _apply_tag_filter(self) -> None:
        tags = [t.strip() for t in self.tag_filter_edit.text().split(",") if t.strip()]
        for row in self.session.rows:
            widget = self.row_widgets.get(row.id)
            if widget:
                widget.setVisible(not tags or all(t.lower() in [x.lower() for x in row.tags] for t in tags))

    def _open_batch_dialog(self) -> None:
        dlg = BatchInputDialog(self)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            prompts, mode = dlg.get_result()
            if not prompts:
                QtWidgets.QMessageBox.information(self, "No prompts", "No prompts parsed.")
                return
            self._push_undo()
            if mode.startswith("Replace"):
                self.session.rows.clear()
            if mode.startswith("Fill"):
                empty_rows = [r for r in self.session.rows if not r.prompt]
                for row, prompt in zip(empty_rows, prompts):
                    row.prompt = prompt
                prompts = prompts[len(empty_rows) :]
            for prompt in prompts:
                row = RowData(id=str(uuid.uuid4()), prompt=prompt)
                self.session.rows.append(row)
            self._reload_rows()
            self.session_manager.autosave()

    def _open_templates_dialog(self) -> None:
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Prompt Templates")
        layout = QtWidgets.QVBoxLayout(dlg)
        name_edit = QtWidgets.QLineEdit("Template")
        layout.addWidget(QtWidgets.QLabel("Template name"))
        layout.addWidget(name_edit)
        tpl_edit = QtWidgets.QLineEdit("A {style} portrait of {subject}")
        layout.addWidget(QtWidgets.QLabel("Template string"))
        layout.addWidget(tpl_edit)
        var_edit = QtWidgets.QTextEdit("style: photorealistic, illustration\nsubject: cat, dog")
        layout.addWidget(QtWidgets.QLabel("Variables (key: comma separated values)"))
        layout.addWidget(var_edit)
        preview_btn = QtWidgets.QPushButton("Preview")
        preview_list = QtWidgets.QListWidget()
        layout.addWidget(preview_btn)
        layout.addWidget(preview_list)
        result_prompts: List[str] = []

        def do_preview() -> None:
            nonlocal result_prompts
            variables = parse_variable_block(var_edit.toPlainText())
            tpl = PromptTemplate(name=name_edit.text(), template=tpl_edit.text(), variables=variables)
            result_prompts = expand_template(tpl)
            preview_list.clear()
            for p in result_prompts:
                preview_list.addItem(p)

        preview_btn.clicked.connect(do_preview)
        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            if not result_prompts:
                do_preview()
            if result_prompts:
                self._push_undo()
                tpl = PromptTemplate(name=name_edit.text(), template=tpl_edit.text(), variables=parse_variable_block(var_edit.toPlainText()))
                self.session.templates.append(tpl)
                for prompt in result_prompts:
                    self.session.rows.append(RowData(id=str(uuid.uuid4()), prompt=prompt))
                self._reload_rows()
                self.session_manager.autosave()

    def _open_gallery(self, row_id: str) -> None:
        row = self._row_by_id(row_id)
        if not row or not row.images:
            return
        dlg = GalleryDialog(row.images, self)
        dlg.export_requested.connect(lambda idx: self._export_row(row_id, idx))
        dlg.export_all_requested.connect(lambda: self._export_row(row_id))
        dlg.exec()

    def _export_row(self, row_id: str, single_index: Optional[int] = None) -> None:
        row = self._row_by_id(row_id)
        if not row or not row.images:
            return
        folder = self._ask_export_folder()
        if not folder:
            return
        exporter = ImageExporter(self.session.global_settings.naming_pattern)
        rows = [row]
        if single_index is not None:
            # export only specific image
            img = row.images[single_index]
            temp_row = RowData(id=row.id, prompt=row.prompt, images=[img])
            rows = [temp_row]
        count, _ = exporter.export_rows(rows, folder, export_metadata=True)
        QtWidgets.QMessageBox.information(self, "Export", f"Exported {count} image(s) to {folder}")

    def _export_selected(self) -> None:
        rows = [r for r in self.session.rows if r.selected and r.images]
        self._export_rows(rows)

    def _export_all(self) -> None:
        rows = [r for r in self.session.rows if r.images]
        self._export_rows(rows)

    def _export_rows(self, rows: List[RowData]) -> None:
        if not rows:
            QtWidgets.QMessageBox.information(self, "Export", "No images to export.")
            return
        folder = self._ask_export_folder()
        if not folder:
            return
        exporter = ImageExporter(self.session.global_settings.naming_pattern)
        count, _ = exporter.export_rows(rows, folder, export_metadata=True)
        QtWidgets.QMessageBox.information(self, "Export", f"Exported {count} image(s) to {folder}")

    def _ask_export_folder(self) -> Optional[Path]:
        default = self.session.global_settings.export_folder or str(Path.home() / "Pictures")
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose export folder", default)
        if folder:
            self.session.global_settings.export_folder = folder
            return Path(folder)
        return None

    def _open_app_settings(self) -> None:
        dlg = AppSettingsDialog(
            self.session.global_settings.concurrency_limit,
            self.session.global_settings.export_folder,
            self.session.global_settings.theme,
            self.session.global_settings.rate_limit_rpm,
            self.session.global_settings.confirm_generate_threshold,
            self,
        )
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            concurrency, export_folder, theme, api_key, gemini_key, rpm, threshold = dlg.get_values()
            self.session.global_settings.concurrency_limit = concurrency
            if concurrency != self.queue.concurrency:
                self.queue.concurrency = concurrency
                self._reset_queue()
            if export_folder:
                self.session.global_settings.export_folder = export_folder
            self.session.global_settings.theme = theme
            self.session.global_settings.rate_limit_rpm = rpm
            self.session.global_settings.confirm_generate_threshold = threshold
            self.queue.rate_limiter.set_rpm(rpm)
            if api_key:
                os.environ["OPENAI_API_KEY"] = api_key
            if gemini_key:
                os.environ["GEMINI_API_KEY"] = gemini_key
            QtWidgets.QMessageBox.information(self, "Settings", "Settings saved.")

    def _start_autosave(self) -> None:
        timer = QtCore.QTimer(self)
        timer.timeout.connect(self.session_manager.autosave)
        timer.start(20000)

    def _setup_shortcuts(self) -> None:
        shortcuts = [
            (QtGui.QKeySequence("Ctrl+N"), self.add_row, False),
            (QtGui.QKeySequence("Ctrl+Shift+N"), self._add_many_rows, False),
            (QtGui.QKeySequence("Ctrl+Shift+G"), self._generate_selected, True),
            (QtGui.QKeySequence("Ctrl+Shift+A"), self._generate_all, True),
            (QtGui.QKeySequence("Ctrl+E"), self._export_selected, True),
            (QtGui.QKeySequence("Ctrl+Shift+E"), self._export_all, True),
            (QtGui.QKeySequence("Ctrl+A"), self._select_all, True),
            (QtGui.QKeySequence("Ctrl+Z"), self._undo, False),
            (QtGui.QKeySequence("Ctrl+Shift+Z"), self._redo, False),
        ]
        if sys.platform == "darwin":
            shortcuts = [
                (QtGui.QKeySequence("Meta+N"), self.add_row, False),
                (QtGui.QKeySequence("Meta+Shift+N"), self._add_many_rows, False),
                (QtGui.QKeySequence("Meta+Shift+G"), self._generate_selected, True),
                (QtGui.QKeySequence("Meta+Shift+A"), self._generate_all, True),
                (QtGui.QKeySequence("Meta+E"), self._export_selected, True),
                (QtGui.QKeySequence("Meta+Shift+E"), self._export_all, True),
                (QtGui.QKeySequence("Meta+A"), self._select_all, True),
                (QtGui.QKeySequence("Meta+Z"), self._undo, False),
                (QtGui.QKeySequence("Meta+Shift+Z"), self._redo, False),
            ]
        for seq, handler, block_in_text in shortcuts:
            sc = QtGui.QShortcut(seq, self)
            sc.activated.connect(lambda h=handler, b=block_in_text: self._invoke_shortcut(h, b))

    def _invoke_shortcut(self, handler, block_in_text: bool) -> None:
        if block_in_text and self._is_text_focused():
            return
        handler()

    def _is_text_focused(self) -> bool:
        widget = self.focusWidget()
        return isinstance(widget, (QtWidgets.QLineEdit, QtWidgets.QTextEdit, QtWidgets.QPlainTextEdit))

    def closeEvent(self, event: QtGui.QCloseEvent) -> None:  # noqa: N802
        self.queue.shutdown()
        self.session_manager.autosave()
        return super().closeEvent(event)

    def _push_undo(self) -> None:
        self.undo_manager.push(self.session)

    def _open_session(self) -> None:
        path, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open session", str(Path.home()), "JSON files (*.json)")
        if path:
            self.session = self.session_manager.load(Path(path))
            self._reset_queue()
            self._reload_rows()
            self.apply_global_settings_to_ui()
            self._update_status_summary()
            self.undo_manager.push(self.session)

    def _save_session(self) -> None:
        path, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save session", str(Path.home()), "JSON files (*.json)")
        if path:
            self.session_manager.save(Path(path))
            self._update_status_summary()

    def _new_session(self) -> None:
        confirm = QtWidgets.QMessageBox.question(self, "New session", "Clear all rows and start a new session?")
        if confirm == QtWidgets.QMessageBox.Yes:
            self._push_undo()
            self.session = self.session_manager.new_session()
            self._reset_queue()
            self._reload_rows()
            self.apply_global_settings_to_ui()
            self._update_status_summary()

    def _update_status_summary(self) -> None:
        total = len(self.session.rows)
        completed = len([r for r in self.session.rows if r.status == RowStatus.COMPLETED])
        queued = len([r for r in self.session.rows if r.status == RowStatus.QUEUED])
        generating = len([r for r in self.session.rows if r.status == RowStatus.GENERATING])
        self.status_bar_label.setText(f"{total} rows • {completed} done • {queued} queued • {generating} running")
        self.session.stats = compute_stats(self.session.rows)

    def _open_stats(self) -> None:
        stats = compute_stats(self.session.rows)
        msg = QtWidgets.QMessageBox(self)
        msg.setWindowTitle("Statistics")
        msg.setText(
            f"Total: {stats.total}\nCompleted: {stats.completed}\nErrors: {stats.errors}\n"
            f"Average duration: {stats.average_duration:.2f}s"
        )
        msg.exec()

    def _undo(self) -> None:
        restored = self.undo_manager.undo()
        if restored:
            self.session = restored
            self.session_manager.session = restored
            self._reload_rows()
            self.apply_global_settings_to_ui()

    def _redo(self) -> None:
        restored = self.undo_manager.redo()
        if restored:
            self.session = restored
            self.session_manager.session = restored
            self._reload_rows()
            self.apply_global_settings_to_ui()
