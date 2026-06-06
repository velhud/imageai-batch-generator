import time
from pathlib import Path

from app.models import GlobalSettings, RowData, RowStatus
from app.providers.registry import ProviderRegistry
from app.queue_manager import GenerationQueue


def test_generation_queue_creates_images(tmp_path: Path):
    registry = ProviderRegistry()
    queue = GenerationQueue(registry, output_root=tmp_path, concurrency=1)
    row = RowData(id="row1", prompt="test prompt")
    events = {}

    def listener(event: str, row_id: str, payload: dict) -> None:
        events.setdefault(event, 0)
        events[event] += 1

    queue.register_listener(listener)
    queue.enqueue(row, GlobalSettings())

    # wait for completion
    deadline = time.time() + 5
    while time.time() < deadline and row.status != RowStatus.COMPLETED:
        time.sleep(0.1)
        # We don't directly set status in queue for tests; rely on file creation
        if any(tmp_path.rglob("*.png")):
            row.status = RowStatus.COMPLETED
            break

    queue.shutdown()
    assert any(tmp_path.rglob("*.png"))
    assert events.get("queued")
