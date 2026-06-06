from __future__ import annotations

from pathlib import Path
from typing import List

from PySide6 import QtCore, QtGui, QtWidgets

from app.models import ImageResult


class GalleryDialog(QtWidgets.QDialog):
    export_requested = QtCore.Signal(int)
    export_all_requested = QtCore.Signal()

    def __init__(self, images: List[ImageResult], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Image Gallery")
        self.images = images
        self.current_index = 0
        self._build_ui()
        self._refresh()

    def _build_ui(self) -> None:
        layout = QtWidgets.QVBoxLayout(self)
        self.label = QtWidgets.QLabel()
        self.label.setAlignment(QtCore.Qt.AlignCenter)
        self.label.setFixedSize(512, 512)
        layout.addWidget(self.label)

        self.meta_label = QtWidgets.QLabel()
        layout.addWidget(self.meta_label)

        btns = QtWidgets.QHBoxLayout()
        prev_btn = QtWidgets.QPushButton("Prev")
        prev_btn.clicked.connect(self.prev_image)
        next_btn = QtWidgets.QPushButton("Next")
        next_btn.clicked.connect(self.next_image)
        export_btn = QtWidgets.QPushButton("Export current")
        export_btn.clicked.connect(self._emit_export_current)
        export_all = QtWidgets.QPushButton("Export all")
        export_all.clicked.connect(lambda: self.export_all_requested.emit())
        open_btn = QtWidgets.QPushButton("Open in Finder")
        open_btn.clicked.connect(self._open_in_finder)
        copy_btn = QtWidgets.QPushButton("Copy image")
        copy_btn.clicked.connect(self._copy_image)

        btns.addWidget(prev_btn)
        btns.addWidget(next_btn)
        btns.addWidget(export_btn)
        btns.addWidget(export_all)
        btns.addWidget(open_btn)
        btns.addWidget(copy_btn)
        layout.addLayout(btns)

    def prev_image(self) -> None:
        self.current_index = (self.current_index - 1) % len(self.images)
        self._refresh()

    def next_image(self) -> None:
        self.current_index = (self.current_index + 1) % len(self.images)
        self._refresh()

    def _refresh(self) -> None:
        if not self.images:
            self.meta_label.setText("No images")
            return
        img = self.images[self.current_index]
        pixmap = QtGui.QPixmap(str(img.file_path)).scaled(
            self.label.width(),
            self.label.height(),
            QtCore.Qt.KeepAspectRatio,
            QtCore.Qt.SmoothTransformation,
        )
        self.label.setPixmap(pixmap)
        self.meta_label.setText(
            f"{self.current_index + 1}/{len(self.images)} • {Path(img.file_path).name}"
        )

    def _emit_export_current(self) -> None:
        self.export_requested.emit(self.current_index)

    def _open_in_finder(self) -> None:
        img = self.images[self.current_index]
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(str(img.file_path)))

    def _copy_image(self) -> None:
        img = self.images[self.current_index]
        pix = QtGui.QPixmap(str(img.file_path))
        QtGui.QGuiApplication.clipboard().setPixmap(pix)
