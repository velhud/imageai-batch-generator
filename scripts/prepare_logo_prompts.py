from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import time
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.models import GlobalSettings, RowData, RowStatus, SessionData  # noqa: E402


DEFAULT_OUTPUT_FOLDER_NAME = "logos_prepared"

CATEGORY_RE = re.compile(r"^#\s+Category\s+(?P<number>\d{1,2})\s*(?:[:\-—]\s*(?P<title>.*))?$", re.IGNORECASE)
HEADING_RE = re.compile(r"^(?P<marks>#{2,3})\s+(?P<text>.+?)\s*$")
PREFIXED_RE = re.compile(
    r"^(?P<label>(?:C(?P<c_cat>\d{1,2})-(?P<c_num>\d{1,2}))|(?:(?P<n_cat>\d{1,2})\.(?P<n_num>\d{1,2}))|(?:(?P<letters>[A-Z]+)(?P<l_num>\d{2})))\b"
    r"(?:\s*[—-]\s*(?P<title>.*)|\s*$)"
)
NUMBER_ONLY_RE = re.compile(r"^(?P<label>(?P<num>\d{1,3})\.)\s+(?P<title>.+)$")
PROMPT_LABEL_RE = re.compile(r"^\s*(?:\*\*)?Prompt:?(?:\*\*)?\s*", re.IGNORECASE)


@dataclass(frozen=True)
class PreparedPrompt:
    generation_id: str
    category_id: str
    prompt_id: str
    category_number: int
    category_title: str
    source_file: str
    source_path: str
    source_line: int
    source_label: str
    title: str
    prompt: str


@dataclass(frozen=True)
class PromptStart:
    line_index: int
    line_number: int
    category_number: int
    category_title: str
    source_label: str
    title: str


def natural_key(path: Path) -> list[int | str]:
    parts: list[int | str] = []
    for chunk in re.split(r"(\d+)", path.stem):
        if chunk.isdigit():
            parts.append(int(chunk))
        elif chunk:
            parts.append(chunk)
    return parts


def clean_title(value: str) -> str:
    return value.strip(" \t-—")


def clean_category_title(value: str) -> str:
    value = clean_title(value)
    return re.sub(r"\s+", " ", value)


def normalize_prompt(lines: Iterable[str]) -> str:
    body = list(lines)
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    while body and body[0].strip() in {"---", "***"}:
        body.pop(0)
    while body and body[-1].strip() in {"---", "***"}:
        body.pop()
    if body:
        body[0] = PROMPT_LABEL_RE.sub("", body[0]).strip()
    text = "\n".join(line.rstrip() for line in body).strip()
    return re.sub(r"\s+", " ", text)


def parse_prompt_heading(
    text: str,
    current_category: int | None,
    current_category_title: str,
    category_counts: dict[int, int],
) -> tuple[int, str, str, str] | None:
    prefixed = PREFIXED_RE.match(text)
    if prefixed:
        if prefixed.group("c_cat"):
            category_number = int(prefixed.group("c_cat"))
        elif prefixed.group("n_cat"):
            category_number = int(prefixed.group("n_cat"))
        elif current_category is not None:
            category_number = current_category
        else:
            return None
        source_label = prefixed.group("label")
        title = clean_title(prefixed.group("title") or text[prefixed.end() :])
        return category_number, current_category_title, source_label, title

    number_only = NUMBER_ONLY_RE.match(text)
    if number_only and current_category is not None:
        source_label = number_only.group("label")
        title = clean_title(number_only.group("title"))
        return current_category, current_category_title, source_label, title

    return None


def find_prompt_starts(path: Path) -> list[PromptStart]:
    lines = path.read_text(encoding="utf-8").splitlines()
    current_category: int | None = None
    current_category_title = ""
    category_counts: dict[int, int] = {}
    starts: list[PromptStart] = []

    for idx, line in enumerate(lines):
        category_match = CATEGORY_RE.match(line.strip())
        if category_match:
            current_category = int(category_match.group("number"))
            current_category_title = clean_category_title(category_match.group("title") or "")
            category_counts.setdefault(current_category, 0)
            continue

        heading_match = HEADING_RE.match(line)
        if not heading_match:
            continue

        parsed = parse_prompt_heading(
            heading_match.group("text").strip(),
            current_category,
            current_category_title,
            category_counts,
        )
        if not parsed:
            continue
        category_number, category_title, source_label, title = parsed
        category_counts[category_number] = category_counts.get(category_number, 0) + 1
        starts.append(
            PromptStart(
                line_index=idx,
                line_number=idx + 1,
                category_number=category_number,
                category_title=category_title,
                source_label=source_label,
                title=title,
            )
        )

    return starts


def parse_markdown_file(path: Path, category_seen_counts: dict[int, int], source_dir: Path) -> list[PreparedPrompt]:
    lines = path.read_text(encoding="utf-8").splitlines()
    starts = find_prompt_starts(path)
    prompts: list[PreparedPrompt] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].line_index if index + 1 < len(starts) else len(lines)
        for candidate_end in range(start.line_index + 1, end):
            if CATEGORY_RE.match(lines[candidate_end].strip()):
                end = candidate_end
                break
        prompt_text = normalize_prompt(lines[start.line_index + 1 : end])
        if not prompt_text:
            continue
        category_seen_counts[start.category_number] = category_seen_counts.get(start.category_number, 0) + 1
        local_number = category_seen_counts[start.category_number]
        category_id = f"cat{start.category_number:02d}"
        prompt_id = f"p{local_number:03d}"
        prompts.append(
            PreparedPrompt(
                generation_id=f"{category_id}_{prompt_id}",
                category_id=category_id,
                prompt_id=prompt_id,
                category_number=start.category_number,
                category_title=start.category_title,
                source_file=path.name,
                source_path=str(path.relative_to(source_dir)),
                source_line=start.line_number,
                source_label=start.source_label,
                title=start.title,
                prompt=prompt_text,
            )
        )
    return prompts


def parse_source_folder(source_dir: Path) -> list[PreparedPrompt]:
    source_dir = source_dir.resolve()
    files = sorted(source_dir.glob("*.md"), key=natural_key)
    if not files:
        raise FileNotFoundError(f"No Markdown files found in {source_dir}")

    category_seen_counts: dict[int, int] = {}
    prompts: list[PreparedPrompt] = []
    for path in files:
        prompts.extend(parse_markdown_file(path.resolve(), category_seen_counts, source_dir))
    return prompts


def write_csv(path: Path, prompts: list[PreparedPrompt]) -> None:
    fields = [
        "generation_id",
        "category_id",
        "prompt_id",
        "category_number",
        "category_title",
        "source_file",
        "source_line",
        "source_label",
        "title",
        "prompt",
    ]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for prompt in prompts:
            row = asdict(prompt)
            writer.writerow({field: row[field] for field in fields})


def write_json_outputs(output_dir: Path, prompts: list[PreparedPrompt], source_dir: Path) -> None:
    payload = [asdict(prompt) for prompt in prompts]
    (output_dir / "logos_prompts.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    with (output_dir / "logos_prompts.jsonl").open("w", encoding="utf-8") as handle:
        for prompt in payload:
            handle.write(json.dumps(prompt, ensure_ascii=False) + "\n")

    summary = build_summary(prompts, source_dir)
    (output_dir / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (output_dir / "preparation_report.md").write_text(build_report(summary), encoding="utf-8")


def build_session(prompts: list[PreparedPrompt]) -> SessionData:
    now = time.time()
    rows: list[RowData] = []
    namespace = uuid.UUID("7d880b8f-34f6-4767-9d2e-35e27d1ab8c1")
    for prompt in prompts:
        row_id = str(uuid.uuid5(namespace, prompt.generation_id))
        rows.append(
            RowData(
                id=row_id,
                prompt=prompt.prompt,
                prompt_id=prompt.prompt_id,
                category_id=prompt.category_id,
                source_metadata={
                    "generation_id": prompt.generation_id,
                    "category_number": prompt.category_number,
                    "category_title": prompt.category_title,
                    "source_file": prompt.source_file,
                    "source_path": prompt.source_path,
                    "source_line": prompt.source_line,
                    "source_label": prompt.source_label,
                    "title": prompt.title,
                },
                status=RowStatus.IDLE,
                tags=[prompt.category_id],
                created_at=now,
                updated_at=now,
            )
        )
    return SessionData(
        id=str(uuid.uuid5(namespace, "inai-logo-prompts-session")),
        global_settings=GlobalSettings(),
        rows=rows,
        created_at=now,
        updated_at=now,
    )


def write_session(path: Path, prompts: list[PreparedPrompt]) -> None:
    session = build_session(prompts)
    path.write_text(session.to_json() + "\n", encoding="utf-8")


def write_per_category_csv(output_dir: Path, prompts: list[PreparedPrompt]) -> None:
    per_category_dir = output_dir / "per_category"
    per_category_dir.mkdir(exist_ok=True)
    category_ids = sorted({prompt.category_id for prompt in prompts})
    for category_id in category_ids:
        write_csv(per_category_dir / f"{category_id}.csv", [p for p in prompts if p.category_id == category_id])


def build_summary(prompts: list[PreparedPrompt], source_dir: Path) -> dict:
    by_category: dict[str, dict] = {}
    by_file: dict[str, int] = {}
    for prompt in prompts:
        entry = by_category.setdefault(
            prompt.category_id,
            {
                "category_number": prompt.category_number,
                "category_title": prompt.category_title,
                "count": 0,
                "first_generation_id": prompt.generation_id,
                "last_generation_id": prompt.generation_id,
            },
        )
        entry["count"] += 1
        entry["last_generation_id"] = prompt.generation_id
        by_file[prompt.source_file] = by_file.get(prompt.source_file, 0) + 1

    return {
        "source_dir": str(source_dir),
        "total_prompts": len(prompts),
        "total_categories": len(by_category),
        "total_files": len(by_file),
        "by_category": dict(sorted(by_category.items())),
        "by_file": dict(sorted(by_file.items(), key=lambda item: natural_key(Path(item[0])))),
    }


def build_report(summary: dict) -> str:
    lines = [
        "# Logos Prompt Preparation Report",
        "",
        f"Source folder: `{summary['source_dir']}`",
        f"Total Markdown files: {summary['total_files']}",
        f"Total categories: {summary['total_categories']}",
        f"Total prompts: {summary['total_prompts']}",
        "",
        "## Outputs",
        "",
        "- `logos_prompts.csv`: import-ready CSV; use CSV mode and the `prompt` column in ImageAI.",
        "- `logos_prompts.json`: full structured prompt manifest.",
        "- `logos_prompts.jsonl`: one prompt object per line for batch tooling.",
        "- `imageai_session.json`: ImageAI session with prompt IDs, category IDs, and source metadata preserved.",
        "- `per_category/*.csv`: category-specific CSV files.",
        "",
        "## Categories",
        "",
        "| Category | Title | Count | ID range |",
        "| --- | --- | ---: | --- |",
    ]
    for category_id, data in summary["by_category"].items():
        title = data["category_title"] or ""
        lines.append(
            f"| `{category_id}` | {title} | {data['count']} | `{data['first_generation_id']}` to `{data['last_generation_id']}` |"
        )
    lines.extend(["", "## Source Files", "", "| File | Prompt count |", "| --- | ---: |"])
    for source_file, count in summary["by_file"].items():
        lines.append(f"| `{source_file}` | {count} |")
    lines.append("")
    return "\n".join(lines)


def prepare(source_dir: Path, output_dir: Path) -> list[PreparedPrompt]:
    prompts = parse_source_folder(source_dir)
    if not prompts:
        raise RuntimeError("No prompts were extracted.")
    output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(output_dir / "logos_prompts.csv", prompts)
    write_json_outputs(output_dir, prompts, source_dir)
    write_session(output_dir / "imageai_session.json", prompts)
    write_per_category_csv(output_dir, prompts)
    return prompts


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare inAi logo-generation prompts for ImageAI batches.")
    parser.add_argument(
        "--source",
        type=Path,
        required=True,
        help="Folder containing source Markdown files.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help=f"Output folder. Defaults to SOURCE/{DEFAULT_OUTPUT_FOLDER_NAME}.",
    )
    args = parser.parse_args()

    source_dir = args.source.expanduser().resolve()
    output_dir = args.output.expanduser().resolve() if args.output else source_dir / DEFAULT_OUTPUT_FOLDER_NAME
    prompts = prepare(source_dir, output_dir)
    summary = build_summary(prompts, source_dir)
    print(f"Prepared {summary['total_prompts']} prompts from {summary['total_files']} files.")
    print(f"Categories: {summary['total_categories']}")
    print(f"Output: {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
