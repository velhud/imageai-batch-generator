from __future__ import annotations

import json
import mimetypes
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Dict, Any, List
from urllib.parse import parse_qs, urlparse, unquote

from app.models import InputAttachment, RowData, RowStatus, SessionData, ImageResult, RowSettings, session_storage_dir
from app.env import load_dotenv_if_available
from app.providers.registry import ProviderRegistry
from app.queue_manager import GenerationQueue
from app.session_manager import SessionManager
from app.stats import compute_stats
from app.exporter import ImageExporter
from app.undo_manager import UndoManager

class BackendState:
    def __init__(self) -> None:
        load_dotenv_if_available()
        self.registry = ProviderRegistry()
        self.session_manager = SessionManager()
        self.session: SessionData = self.session_manager.session
        self.undo_manager = UndoManager()
        self.undo_manager.push(self.session)
        
        self.queue = GenerationQueue(
            self.registry,
            output_root=self.session_manager.session_output_dir(),
            concurrency=self.session.global_settings.concurrency_limit,
            rpm=self.session.global_settings.rate_limit_rpm,
        )
        self.queue.register_listener(self._handle_event)
        self._lock = threading.Lock()

    def _handle_event(self, event: str, row_id: str, payload: Dict) -> None:
        with self._lock:
            row = self._row_by_id(row_id)
            if not row:
                return
            if event in {"queued", "queue_position"}:
                row.status = RowStatus.QUEUED
                row.error_message = payload.get("message", "")
            elif event == "started":
                row.status = RowStatus.GENERATING
            elif event == "completed":
                row.status = RowStatus.COMPLETED
                row.error_message = ""
                # Handle images
                paths = payload.get("paths", [])
                keep = payload.get("keep_existing", True)
                if not keep:
                    row.images = []
                for p in paths:
                    row.images.append(ImageResult(id=f"img-{len(row.images)+1}", row_id=row.id, file_path=p))
            elif event == "error":
                row.status = RowStatus.ERROR
                row.error_message = payload.get("message", "")
            elif event == "cancelled":
                row.status = RowStatus.CANCELLED
            self.session_manager.autosave()

    def _row_by_id(self, row_id: str) -> RowData | None:
        for row in self.session.rows:
            if row.id == row_id:
                return row
        return None

    def push_state(self):
        with self._lock:
            self.undo_manager.push(self.session)
            self.session_manager.autosave()

    def to_dict(self) -> Dict[str, Any]:
        with self._lock:
            return {
                "session": self.session.to_dict(),
                "providers": [p.to_dict() for p in self.registry.info_list()],
                "stats": compute_stats(self.session.rows).to_dict(),
            }

STATE = BackendState()

def _json_response(handler: BaseHTTPRequestHandler, body: Dict, status: int = 200) -> None:
    data = json.dumps(body).encode("utf-8")
    handler.send_response(status)
    _set_cors_headers(handler)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(data)))
    handler.end_headers()
    handler.wfile.write(data)

def _set_cors_headers(handler: BaseHTTPRequestHandler) -> None:
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type")
    handler.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")

class Handler(BaseHTTPRequestHandler):
    def do_OPTIONS(self) -> None:
        self.send_response(200)
        _set_cors_headers(self)
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path != "/images":
            self.send_error(404)
            return

        query = parse_qs(parsed.query or "")
        raw_path = query.get("path", [None])[0]
        if not raw_path:
            self.send_error(400, "missing path")
            return

        file_path = Path(unquote(raw_path))
        images_root = session_storage_dir().resolve()
        try:
            file_path.resolve().relative_to(images_root)
        except Exception:
            self.send_error(403)
            return

        if not file_path.exists() or not file_path.is_file():
            self.send_error(404)
            return

        data = file_path.read_bytes()
        mime, _ = mimetypes.guess_type(file_path.name)
        self.send_response(200)
        _set_cors_headers(self)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        try:
            self.wfile.write(data)
        except BrokenPipeError:
            # Client disconnected
            pass

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            _json_response(self, {"error": "invalid json"}, 400)
            return
        action = payload.get("action")
        data = payload.get("data", {})

        # Request logging for key actions
        print(f"[-] ACTION: {action}")
        if action == "update_row":
            try:
                print(f"    Data: {json.dumps(data)}")
            except Exception:
                pass
        elif action == "generate_rows":
            print(f"    Rows: {data.get('row_ids')}")
        
        try:
            result = self._dispatch(action, data)
            _json_response(self, {"ok": True, "data": result})
        except Exception as exc:
            import traceback
            traceback.print_exc()
            print(f"[!] ERROR in {action}: {exc}")
            _json_response(self, {"ok": False, "error": str(exc)}, 500)

    def _dispatch(self, action: str, data: Dict[str, Any]) -> Any:
        if action == "state":
            return STATE.to_dict()
            
        # --- Session Management ---
        if action == "new_session":
            STATE.push_state()
            STATE.session = STATE.session_manager.new_session()
            STATE.push_state()
            return STATE.to_dict()
            
        if action == "save_session":
            path = data.get("path")
            if path:
                STATE.session_manager.save(Path(path))
            else:
                STATE.session_manager.autosave()
            return {"saved": True}

        if action == "load_session":
            path = data.get("path")
            if path and Path(path).exists():
                STATE.push_state()
                STATE.session = STATE.session_manager.load(Path(path))
                STATE.undo_manager.push(STATE.session)
            return STATE.to_dict()

        if action == "undo":
            prev = STATE.undo_manager.undo()
            if prev:
                STATE.session = prev
                STATE.session_manager.session = prev
            return STATE.to_dict()

        if action == "redo":
            next_s = STATE.undo_manager.redo()
            if next_s:
                STATE.session = next_s
                STATE.session_manager.session = next_s
            return STATE.to_dict()

        # --- Row Operations ---
        if action == "add_rows":
            import uuid
            STATE.push_state()
            prompts: List[str] = data.get("prompts", [])
            for prompt in prompts:
                row = RowData(id=str(uuid.uuid4()), prompt=prompt)
                STATE.session.rows.append(row)
            STATE.push_state()
            return {"rows": [r.to_dict() for r in STATE.session.rows]}

        if action == "update_row":
            # Don't push undo for every keystroke, handle debounce in frontend or specific commit action
            # For simplicity, we push state if 'final' flag is sent or specific fields change
            rid = data["row_id"]
            row = STATE._row_by_id(rid)
            if not row:
                return {}
            
            if "prompt" in data:
                row.prompt = data["prompt"]
            if "selected" in data:
                row.selected = bool(data["selected"])
            if "tags" in data:
                row.tags = data["tags"]
            if "attachments" in data:
                row.attachments = [InputAttachment.from_dict(a) for a in data.get("attachments", [])]
            
            # Row Settings
            if "settings" in data:
                # Merge logic
                new_settings = data["settings"]
                current = row.settings.to_dict()
                current.update(new_settings)
                # Remove nulls if strictly merging? Or replace? 
                # Model handles None as "inherit global".
                row.settings = RowSettings(**current)

            STATE.session_manager.autosave()
            return row.to_dict()

        if action == "delete_rows":
            STATE.push_state()
            ids = set(data.get("row_ids", []))
            STATE.session.rows = [r for r in STATE.session.rows if r.id not in ids]
            STATE.push_state()
            return {"rows": [r.to_dict() for r in STATE.session.rows]}

        if action == "duplicate_row":
            STATE.push_state()
            rid = data.get("row_id")
            row = STATE._row_by_id(rid)
            if row:
                import uuid
                clone = RowData.from_dict(row.to_dict())
                clone.id = str(uuid.uuid4())
                clone.images = [] # Don't clone images
                clone.status = RowStatus.IDLE
                idx = STATE.session.rows.index(row) + 1
                STATE.session.rows.insert(idx, clone)
            STATE.push_state()
            return STATE.to_dict()

        # --- Generation ---
        if action == "generate_rows":
            ids = data.get("row_ids", [])
            for rid in ids:
                row = STATE._row_by_id(rid)
                if not row:
                    continue
                row.status = RowStatus.QUEUED
                STATE.queue.enqueue(row, STATE.session.global_settings)
            return {"queued": ids}

        if action == "stop_all":
            STATE.queue.cancel_all()
            return {"stopped": True}

        # --- Global Settings ---
        if action == "global_settings":
            STATE.push_state()
            gs = STATE.session.global_settings
            for key, val in data.items():
                if hasattr(gs, key):
                    setattr(gs, key, val)
            STATE.queue.rate_limiter.set_rpm(gs.rate_limit_rpm)
            if gs.concurrency_limit != STATE.queue.concurrency:
                # Restart queue if concurrency changed
                STATE.queue.shutdown()
                STATE.queue = GenerationQueue(
                    STATE.registry,
                    STATE.session_manager.session_output_dir(),
                    gs.concurrency_limit,
                    gs.rate_limit_rpm
                )
                STATE.queue.register_listener(STATE._handle_event)
            STATE.push_state()
            return gs.to_dict()

        if action == "select_image_file":
            from PySide6.QtWidgets import QApplication, QFileDialog
            if not QApplication.instance():
                _ = QApplication([])
            file_path, _ = QFileDialog.getOpenFileName(None, "Select Image", "", "Images (*.png *.jpg *.jpeg *.webp)")
            if file_path:
                mime, _ = mimetypes.guess_type(file_path)
                return {"path": file_path, "mime": mime or "image/png"}
            return None

        if action == "select_folder":
            from PySide6.QtWidgets import QApplication, QFileDialog

            if not QApplication.instance():
                _ = QApplication([])
            folder = QFileDialog.getExistingDirectory(None, "Select Folder")
            return {"path": folder}
            
        if action == "export":
            folder = Path(data.get("folder", str(Path.home() / "Pictures")))
            rows = [STATE._row_by_id(rid) for rid in data.get("row_ids", [])]
            rows = [r for r in rows if r]
            exporter = ImageExporter(STATE.session.global_settings.naming_pattern)
            count, _ = exporter.export_rows(rows, folder, export_metadata=True)
            return {"exported": count}

        if action == "copy_image_to_clipboard":
            from PySide6 import QtGui, QtWidgets
            if not QtWidgets.QApplication.instance():
                _ = QtWidgets.QApplication([])
            path = data.get("path")
            if path and Path(path).exists():
                img = QtGui.QImage(path)
                if not img.isNull():
                    QtWidgets.QApplication.clipboard().setImage(img)
                    return {"copied": True}
            return {"copied": False}

        if action == "open_path":
            from PySide6 import QtGui, QtCore
            path = data.get("path")
            if path:
                url = QtCore.QUrl.fromLocalFile(path)
                QtGui.QDesktopServices.openUrl(url)
            return {"opened": True}

        # --- Templates ---
        if action == "save_template":
            from app.models import PromptTemplate
            tpl = PromptTemplate.from_dict(data)
            STATE.session.templates.append(tpl)
            STATE.session_manager.autosave()
            return {"templates": [t.to_dict() for t in STATE.session.templates]}
            
        if action == "expand_template":
            from app.templates import expand_template, parse_variable_block
            from app.models import PromptTemplate
            tpl = PromptTemplate(
                name=data.get("name", ""),
                template=data.get("template", ""),
                variables=data.get("variables", {})
            )
            prompts = expand_template(tpl)
            return {"prompts": prompts}

        return {}

def run_server(port: int = 8765) -> None:
    server = HTTPServer(("127.0.0.1", port), Handler)
    print(f"[backend_server] listening on http://127.0.0.1:{port}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
