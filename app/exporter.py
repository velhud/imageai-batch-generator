from __future__ import annotations

import json
import shutil
import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Tuple

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
                path = target_folder / name
                src = Path(img.file_path)
                if src.exists():
                    shutil.copy(src, path)
                    exported.append(path)
                    metadata.append(
                        {
                            "row_index": idx,
                            "row_id": row.id,
                            "prompt": row.prompt,
                            "file": str(path),
                            "source": str(src),
                            "image_index": img_index,
                        }
                    )
        if export_metadata and metadata:
            meta_path = target_folder / "export_metadata.json"
            meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        return len(exported), exported
