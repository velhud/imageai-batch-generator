from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, List, Optional

from app.models import GlobalSettings, RowData, RowStatus, effective_settings
from app.providers.registry import ProviderRegistry
from app.scheduler import RateLimiter


@dataclass
class GenerationJob:
    row_id: str
    prompt: str
    settings: GlobalSettings
    provider_id: str
    output_dir: Path
    keep_existing: bool = False
    requested_at: float = 0.0
    attachments: List[Any] = field(default_factory=list)


class GenerationQueue:
    """Simple worker queue controlling concurrent generation jobs."""

    def __init__(
        self,
        providers: ProviderRegistry,
        output_root: Path,
        concurrency: int,
        rpm: int = 60,
    ) -> None:
        self.providers = providers
        self.output_root = output_root
        self.concurrency = max(1, concurrency)
        self.listeners: List[Callable[[str, str, Dict], None]] = []
        self.queue: Queue[GenerationJob] = Queue()
        self.running = True
        self.running_jobs: Dict[str, threading.Event] = {}
        self.lock = threading.Lock()
        self.workers: List[threading.Thread] = []
        self.pending_order: List[str] = []
        self.rate_limiter = RateLimiter(rpm)
        self._start_workers(self.concurrency)

    def _start_workers(self, count: int) -> None:
        for _ in range(count):
            t = threading.Thread(target=self._worker_loop, daemon=True)
            t.start()
            self.workers.append(t)

    def register_listener(self, callback: Callable[[str, str, Dict], None]) -> None:
        """callback signature: (event, row_id, payload)"""
        self.listeners.append(callback)

    def _notify(self, event: str, row_id: str, payload: Optional[Dict] = None) -> None:
        for callback in list(self.listeners):
            try:
                callback(event, row_id, payload or {})
            except Exception:
                # Listeners should never crash queue.
                continue

    def enqueue(self, row: RowData, global_settings: GlobalSettings) -> None:
        eff = effective_settings(row, global_settings)
        provider_id = eff.provider_id
        job = GenerationJob(
            row_id=row.id,
            prompt=row.prompt,
            settings=eff,
            provider_id=provider_id,
            output_dir=self.output_root / row.id,
            keep_existing=eff.generate_behavior != "replace",
            requested_at=time.time(),
            attachments=list(row.attachments),
        )
        self.queue.put(job)
        with self.lock:
            self.pending_order.append(row.id)
            position = len(self.pending_order)
        self._notify("queued", row.id, {"position": position})
        self._broadcast_queue_positions()

    def _worker_loop(self) -> None:
        while self.running:
            job: GenerationJob = self.queue.get()
            if not self.running:
                self.queue.task_done()
                break
            print(f"[Q] Processing Row: {job.row_id}")
            print(f"    Prompt: {job.prompt[:50]}...")
            print(f"    Provider: {job.provider_id}")
            cancel_event = threading.Event()
            with self.lock:
                self.running_jobs[job.row_id] = cancel_event
                if job.row_id in self.pending_order:
                    self.pending_order.remove(job.row_id)
            self._broadcast_queue_positions()
            self._notify("started", job.row_id, {})
            try:
                self.rate_limiter.acquire(job.provider_id)
                start_time = time.time()
                provider = self.providers.get(job.provider_id)
                provider.setup()
                paths = provider.generate_images(
                    prompt=job.prompt,
                    settings=job.settings,
                    output_dir=job.output_dir,
                    cancel_event=cancel_event,
                    attachments=job.attachments,
                )
                duration = time.time() - start_time
                if cancel_event.is_set():
                    self._notify("cancelled", job.row_id, {})
                else:
                    self._notify(
                        "completed",
                        job.row_id,
                        {"paths": [str(p) for p in paths], "duration": duration, "keep_existing": job.keep_existing},
                    )
            except Exception as exc:
                self._notify("error", job.row_id, {"message": str(exc)})
            finally:
                with self.lock:
                    self.running_jobs.pop(job.row_id, None)
                self.queue.task_done()
                self._broadcast_queue_positions()

    def cancel(self, row_id: str) -> None:
        with self.lock:
            ev = self.running_jobs.get(row_id)
            if ev:
                ev.set()

    def cancel_all(self) -> None:
        with self.lock:
            for ev in self.running_jobs.values():
                ev.set()

    def shutdown(self) -> None:
        self.running = False
        self.cancel_all()
        # Drain queue with sentinel None markers
        for _ in self.workers:
            self.queue.put(
                GenerationJob(
                    row_id=str(uuid.uuid4()),
                    prompt="",
                    settings=GlobalSettings(),
                    provider_id="mock",
                    output_dir=self.output_root,
                )
            )
        for t in self.workers:
            t.join(timeout=0.1)

    def _broadcast_queue_positions(self) -> None:
        with self.lock:
            for idx, row_id in enumerate(self.pending_order, start=1):
                self._notify("queue_position", row_id, {"position": idx})


def queue_row_status_update(row: RowData, status: RowStatus, message: str = "") -> None:
    row.status = status
    row.error_message = message
