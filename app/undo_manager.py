from __future__ import annotations

import copy
from typing import List, Optional

from app.models import SessionData


class UndoManager:
    """Simple undo/redo stack storing SessionData snapshots."""

    def __init__(self, max_depth: int = 30) -> None:
        self.max_depth = max_depth
        self.stack: List[dict] = []
        self.redo_stack: List[dict] = []

    def push(self, session: SessionData) -> None:
        snapshot = copy.deepcopy(session.to_dict())
        if self.stack and self.stack[-1] == snapshot:
            return
        self.stack.append(snapshot)
        if len(self.stack) > self.max_depth:
            self.stack.pop(0)
        self.redo_stack.clear()

    def undo(self) -> Optional[SessionData]:
        if not self.stack:
            return None
        current = self.stack.pop()
        self.redo_stack.append(current)
        if not self.stack:
            return SessionData.from_dict(current)
        return SessionData.from_dict(self.stack[-1])

    def redo(self) -> Optional[SessionData]:
        if not self.redo_stack:
            return None
        snapshot = self.redo_stack.pop()
        self.stack.append(snapshot)
        return SessionData.from_dict(snapshot)
