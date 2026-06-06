from pathlib import Path

from app.exporter import ImageExporter
from app.models import ImageResult, RowData


def test_exporter_uses_naming_pattern(tmp_path: Path):
    src = tmp_path / "source.png"
    src.write_bytes(b"fake")
    row = RowData(id="row1", prompt="hello world")
    row.images.append(ImageResult(id="img1", row_id=row.id, file_path=str(src)))
    exporter = ImageExporter("{index}_{slug}.png")
    target = tmp_path / "out"
    count, files = exporter.export_rows([row], target)
    assert count == 1
    assert (target / "1_hello_world.png").exists()
