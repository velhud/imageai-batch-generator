from __future__ import annotations

import json
import time
import uuid
from pathlib import Path
from typing import List

from app.models import (
    GlobalSettings,
    RowData,
    RowStatus,
    SessionData,
    default_session_path,
    session_storage_dir,
)


class SessionManager:
    def __init__(self) -> None:
        self.session: SessionData = SessionData(
            id=str(uuid.uuid4()),
            global_settings=GlobalSettings(),
            rows=[],
        )
        self.last_path: Path = default_session_path()

    def new_session(self) -> SessionData:
        self.session = SessionData(
            id=str(uuid.uuid4()),
            global_settings=GlobalSettings(),
            rows=[],
        )
        return self.session

    def add_rows(self, prompts: List[str]) -> None:
        for prompt in prompts:
            row = RowData(id=str(uuid.uuid4()), prompt=prompt, status=RowStatus.IDLE)
            self.session.rows.append(row)

    def save(self, path: Path | None = None) -> Path:
        path = path or self.last_path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.session.updated_at = time.time()
        with open(path, "w", encoding="utf-8") as f:
            f.write(self.session.to_json())
        self.last_path = path
        return path

    def load(self, path: Path) -> SessionData:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.session = SessionData.from_dict(data)
        self.last_path = path
        return self.session

    def autosave(self) -> Path:
        return self.save(default_session_path())

    def restore_last(self) -> SessionData | None:
        path = default_session_path()
        if path.exists():
            try:
                return self.load(path)
            except Exception:
                return None
        return None

    def session_output_dir(self) -> Path:
        base = session_storage_dir() / self.session.id
        base.mkdir(parents=True, exist_ok=True)
        images_dir = base / "images"
        images_dir.mkdir(exist_ok=True)
        return images_dir
