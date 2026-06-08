from __future__ import annotations

import time
import threading
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from queue import Queue
from typing import Any, Callable, Dict, List, Optional

from app.generation_log import LOG_FILENAME, append_generation_log
from app.models import GeneratedImage, GenerationContext, GlobalSettings, RowData, RowStatus, effective_settings
from app.providers.base import ProviderFilteredError, ProviderGenerationError, ProviderRetryExhaustedError
from app.providers.registry import ProviderRegistry
from app.scheduler import RateLimiter


@dataclass
class GenerationJob:
    row_id: str
    prompt: str
    settings: GlobalSettings
    provider_id: str
    output_dir: Path
    row_index: int = 1
    prompt_id: str = ""
    category_id: str = ""
    source_metadata: Dict[str, Any] = field(default_factory=dict)
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

    def enqueue(
        self,
        row: RowData,
        global_settings: GlobalSettings,
        *,
        row_index: int = 1,
        missing_only: bool = False,
    ) -> None:
        if missing_only and self._row_has_success(row):
            self._notify("skipped", row.id, {"message": "Existing successful image found; skipped."})
            self._log_generation(
                row=row,
                context=self._context_for(row, global_settings, row_index),
                settings=effective_settings(row, global_settings),
                status="skipped",
                output_file="",
                metadata={"message": "Existing successful image found; skipped."},
            )
            return

        eff = effective_settings(row, global_settings)
        provider_id = eff.provider_id
        job = GenerationJob(
            row_id=row.id,
            prompt=row.prompt,
            settings=eff,
            provider_id=provider_id,
            output_dir=self.output_root / row.id,
            row_index=row_index,
            prompt_id=row.prompt_id,
            category_id=row.category_id,
            source_metadata=dict(row.source_metadata),
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
                provider = self.providers.get(job.provider_id)
                self.rate_limiter.acquire(job.provider_id, provider.quota_cost(job.settings))
                start_time = time.time()
                provider.setup()
                context = self._context_for_job(job)
                images = provider.generate_images(
                    prompt=context.full_prompt,
                    settings=job.settings,
                    output_dir=job.output_dir,
                    cancel_event=cancel_event,
                    attachments=job.attachments,
                    context=context,
                )
                duration = time.time() - start_time
                if cancel_event.is_set():
                    self._notify("cancelled", job.row_id, {})
                else:
                    image_payloads = [
                        {
                            "path": str(img.file_path),
                            "metadata": {
                                **context.to_metadata(),
                                **img.metadata,
                                "source_metadata": job.source_metadata,
                            },
                        }
                        for img in images
                    ]
                    for img in image_payloads:
                        self._log_generation(
                            row=None,
                            context=context,
                            settings=job.settings,
                            status="success",
                            output_file=img["path"],
                            metadata=img["metadata"],
                        )
                    self._notify(
                        "completed",
                        job.row_id,
                        {
                            "paths": [img["path"] for img in image_payloads],
                            "images": image_payloads,
                            "duration": duration,
                            "keep_existing": job.keep_existing,
                        },
                    )
            except ProviderFilteredError as exc:
                context = self._context_for_job(job)
                self._log_generation(
                    row=None,
                    context=context,
                    settings=job.settings,
                    status="filtered",
                    output_file="",
                    metadata=exc.metadata,
                    error=str(exc),
                )
                self._notify("filtered", job.row_id, {"message": str(exc), "metadata": exc.metadata})
            except ProviderRetryExhaustedError as exc:
                context = self._context_for_job(job)
                self._log_generation(
                    row=None,
                    context=context,
                    settings=job.settings,
                    status="retry_exhausted",
                    output_file="",
                    metadata=exc.metadata,
                    error=str(exc),
                )
                self._notify("error", job.row_id, {"message": str(exc), "metadata": exc.metadata})
            except ProviderGenerationError as exc:
                context = self._context_for_job(job)
                self._log_generation(
                    row=None,
                    context=context,
                    settings=job.settings,
                    status=exc.status or "failed",
                    output_file="",
                    metadata=exc.metadata,
                    error=str(exc),
                )
                self._notify("error", job.row_id, {"message": str(exc), "metadata": exc.metadata})
            except Exception as exc:
                context = self._context_for_job(job)
                self._log_generation(
                    row=None,
                    context=context,
                    settings=job.settings,
                    status="failed",
                    output_file="",
                    metadata={},
                    error=str(exc),
                )
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

    def stop_after_current(self) -> None:
        drained: List[GenerationJob] = []
        while True:
            try:
                drained.append(self.queue.get_nowait())
                self.queue.task_done()
            except Exception:
                break
        with self.lock:
            for job in drained:
                if job.row_id in self.pending_order:
                    self.pending_order.remove(job.row_id)
                self._notify("cancelled", job.row_id, {"message": "Stopped before generation."})
        self._broadcast_queue_positions()

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

    def _context_for(self, row: RowData, global_settings: GlobalSettings, row_index: int) -> GenerationContext:
        settings = effective_settings(row, global_settings)
        original_prompt = row.prompt or ""
        wrapper = (settings.prompt_wrapper or "").strip()
        full_prompt = original_prompt.strip()
        if wrapper:
            full_prompt = f"{full_prompt}\n\n{wrapper}" if full_prompt else wrapper
        return GenerationContext(
            row_id=row.id,
            row_index=row_index,
            prompt_id=row.prompt_id or f"prompt{row_index:04d}",
            category_id=row.category_id or "cat00",
            original_prompt=original_prompt,
            full_prompt=full_prompt,
            run_index=1,
            log_path=str(self.log_path),
        )

    def _context_for_job(self, job: GenerationJob) -> GenerationContext:
        wrapper = (job.settings.prompt_wrapper or "").strip()
        full_prompt = job.prompt.strip()
        if wrapper:
            full_prompt = f"{full_prompt}\n\n{wrapper}" if full_prompt else wrapper
        return GenerationContext(
            row_id=job.row_id,
            row_index=job.row_index,
            prompt_id=job.prompt_id or f"prompt{job.row_index:04d}",
            category_id=job.category_id or "cat00",
            original_prompt=job.prompt,
            full_prompt=full_prompt,
            run_index=1,
            log_path=str(self.log_path),
        )

    @property
    def log_path(self) -> Path:
        return self.output_root.parent / LOG_FILENAME

    def _row_has_success(self, row: RowData) -> bool:
        return any(Path(img.file_path).exists() for img in row.images)

    def _log_generation(
        self,
        *,
        row: RowData | None,
        context: GenerationContext,
        settings: GlobalSettings,
        status: str,
        output_file: str,
        metadata: Dict[str, Any],
        error: str = "",
    ) -> None:
        append_generation_log(
            self.log_path,
            {
                "prompt_id": context.prompt_id,
                "category_id": context.category_id,
                "row_id": context.row_id,
                "original_prompt": context.original_prompt,
                "full_prompt": context.full_prompt,
                "provider": settings.provider_id,
                "model": settings.model_id,
                "size": metadata.get("size") or _size_string(settings),
                "quality": metadata.get("quality") or settings.quality,
                "n": metadata.get("n") or settings.num_images,
                "output_format": metadata.get("output_format") or "png",
                "output_file": output_file,
                "status": status,
                "attempt": metadata.get("attempt"),
                "azure_request_id": metadata.get("azure_request_id", ""),
                "error": error,
            },
        )


def _size_string(settings: GlobalSettings) -> str:
    if settings.custom_size:
        return f"{settings.custom_size.get('width', 1024)}x{settings.custom_size.get('height', 1024)}"
    from app.models import DEFAULT_SIZE_PRESETS

    preset = DEFAULT_SIZE_PRESETS.get(settings.size_preset or "", DEFAULT_SIZE_PRESETS["Square 1024"])
    return f"{preset.get('width', 1024)}x{preset.get('height', 1024)}"


def queue_row_status_update(row: RowData, status: RowStatus, message: str = "") -> None:
    row.status = status
    row.error_message = message
