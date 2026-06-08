from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from PySide6 import QtWidgets


class AppSettingsDialog(QtWidgets.QDialog):
    def __init__(
        self,
        concurrency: int,
        export_folder: Optional[str],
        theme: str,
        rpm: int,
        confirm_threshold: int,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("App Settings")
        self.concurrency = concurrency
        self.export_folder = export_folder
        self.theme = theme
        self.rpm = rpm
        self.confirm_threshold = confirm_threshold
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QtWidgets.QFormLayout(self)
        self.concurrency_spin = QtWidgets.QSpinBox()
        self.concurrency_spin.setRange(1, 8)
        self.concurrency_spin.setValue(self.concurrency)
        layout.addRow("Concurrency limit", self.concurrency_spin)

        self.rpm_spin = QtWidgets.QSpinBox()
        self.rpm_spin.setRange(1, 500)
        self.rpm_spin.setValue(self.rpm)
        layout.addRow("Requests per minute", self.rpm_spin)

        self.confirm_spin = QtWidgets.QSpinBox()
        self.confirm_spin.setRange(10, 10000)
        self.confirm_spin.setValue(self.confirm_threshold)
        layout.addRow("Generate-all confirm threshold", self.confirm_spin)

        self.export_folder_edit = QtWidgets.QLineEdit(self.export_folder or "")
        browse = QtWidgets.QPushButton("Browse")
        browse.clicked.connect(self._choose_folder)
        folder_layout = QtWidgets.QHBoxLayout()
        folder_layout.addWidget(self.export_folder_edit)
        folder_layout.addWidget(browse)
        layout.addRow("Default export folder", folder_layout)

        self.theme_combo = QtWidgets.QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])
        self.theme_combo.setCurrentText(self.theme)
        layout.addRow("Theme", self.theme_combo)

        self.api_key_edit = QtWidgets.QLineEdit(os.environ.get("OPENAI_API_KEY", ""))
        self.api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("OpenAI API key (env)", self.api_key_edit)

        self.gemini_api_key_edit = QtWidgets.QLineEdit(os.environ.get("GEMINI_API_KEY", ""))
        self.gemini_api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("Gemini API key (env)", self.gemini_api_key_edit)

        self.azure_endpoint_edit = QtWidgets.QLineEdit(os.environ.get("AZURE_OPENAI_ENDPOINT", ""))
        layout.addRow("Azure endpoint (env)", self.azure_endpoint_edit)

        self.azure_deployment_edit = QtWidgets.QLineEdit(os.environ.get("AZURE_GPT_IMAGE_2_DEPLOYMENT", ""))
        layout.addRow("Azure GPT-Image-2 deployment (env)", self.azure_deployment_edit)

        self.azure_api_key_edit = QtWidgets.QLineEdit(os.environ.get("AZURE_OPENAI_API_KEY", ""))
        self.azure_api_key_edit.setEchoMode(QtWidgets.QLineEdit.Password)
        layout.addRow("Azure API key (env)", self.azure_api_key_edit)

        buttons = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def _choose_folder(self) -> None:
        folder = QtWidgets.QFileDialog.getExistingDirectory(self, "Choose export folder")
        if folder:
            self.export_folder_edit.setText(folder)

    def get_values(self) -> Tuple[int, str, str, str, str, int, int, str, str, str]:
        return (
            self.concurrency_spin.value(),
            self.export_folder_edit.text().strip(),
            self.theme_combo.currentText(),
            self.api_key_edit.text().strip(),
            self.gemini_api_key_edit.text().strip(),
            self.rpm_spin.value(),
            self.confirm_spin.value(),
            self.azure_endpoint_edit.text().strip(),
            self.azure_deployment_edit.text().strip(),
            self.azure_api_key_edit.text().strip(),
        )
