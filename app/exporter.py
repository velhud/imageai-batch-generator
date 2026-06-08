from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import List, Tuple

from app.generation_log import LOG_FILENAME, verify_rows
from app.models import ImageResult, RowData


def slugify(text: str, limit: int = 32) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in ("-", "_") else "_" for ch in text)
    return cleaned[:limit] or "prompt"


class ImageExporter:
    def __init__(self, naming_pattern: str) -> None:
        self.naming_pattern = naming_pattern

    def export_rows(
        self,
        rows: List[RowData],
        target_folder: Path,
        export_metadata: bool = True,
    ) -> Tuple[int, List[Path]]:
        target_folder.mkdir(parents=True, exist_ok=True)
        exported: List[Path] = []
        metadata: List[dict] = []
        for idx, row in enumerate(rows, start=1):
            if not row.images:
                continue
            for img_index, img in enumerate(row.images):
                name = self.naming_pattern.format(
                    index=idx,
                    image_index=img_index,
                    slug=slugify(row.prompt),
                    row_id=row.id[:8],
                )
                src = Path(img.file_path)
                if img.metadata.get("provider") == "azure-openai":
                    name = src.name
                path = target_folder / name
                if src.exists():
                    shutil.copy(src, path)
                    exported.append(path)
                    metadata.append(
                        {
                            "row_index": idx,
                            "row_id": row.id,
                            "prompt_id": row.prompt_id,
                            "category_id": row.category_id,
                            "prompt": row.prompt,
                            "file": str(path),
                            "source": str(src),
                            "image_index": img_index,
                            "metadata": img.metadata,
                        }
                    )
        if export_metadata and metadata:
            meta_path = target_folder / "export_metadata.json"
            meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
            summary_path = target_folder / "export_summary.json"
            summary_path.write_text(json.dumps(verify_rows(rows), indent=2), encoding="utf-8")
            log_path = _find_generation_log(rows)
            if log_path and log_path.exists():
                shutil.copy(log_path, target_folder / LOG_FILENAME)
        return len(exported), exported


def _find_generation_log(rows: List[RowData]) -> Path | None:
    for row in rows:
        for img in row.images:
            path = Path(img.file_path)
            if len(path.parents) >= 3:
                candidate = path.parents[2] / LOG_FILENAME
                if candidate.exists():
                    return candidate
    return None
