from __future__ import annotations

import dataclasses
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
import mimetypes
from typing import Any, Dict, List, Optional


class RowStatus(str, Enum):
    IDLE = "Idle"
    QUEUED = "Queued"
    GENERATING = "Generating"
    COMPLETED = "Completed"
    ERROR = "Error"
    FILTERED = "Filtered"
    CANCELLED = "Cancelled"


SizePreset = Dict[str, int]


DEFAULT_SIZE_PRESETS: Dict[str, SizePreset] = {
    "Square 1024": {"width": 1024, "height": 1024},
    "Portrait": {"width": 1024, "height": 1536},
    "Landscape": {"width": 1536, "height": 1024},
}


@dataclass
class InputAttachment:
    id: str
    file_path: str
    mime_type: str = "image/png"

    def to_dict(self) -> Dict:
        return asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "InputAttachment":
        mime_type = data.get("mime_type") or mimetypes.guess_type(data.get("file_path", ""))[0] or "image/png"
        return InputAttachment(
            id=data.get("id", str(uuid.uuid4())),
            file_path=data.get("file_path", ""),
            mime_type=mime_type,
        )


@dataclass
class ProviderCapabilities:
    max_images: int = 4
    supports_style: bool = True
    supports_negative_prompt: bool = True
    supports_seed: bool = True
    supports_quality: bool = True
    supports_safety: bool = True
    size_presets: Dict[str, SizePreset] = field(
        default_factory=lambda: dict(DEFAULT_SIZE_PRESETS)
    )


@dataclass
class ModelInfo:
    id: str
    name: str
    provider_id: str
    capabilities: ProviderCapabilities = field(default_factory=ProviderCapabilities)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "provider_id": self.provider_id,
            "capabilities": dataclasses.asdict(self.capabilities),
        }

    @staticmethod
    def from_dict(data: Dict) -> "ModelInfo":
        return ModelInfo(
            id=data["id"],
            name=data["name"],
            provider_id=data["provider_id"],
            capabilities=ProviderCapabilities(**data.get("capabilities", {})),
        )


@dataclass
class ProviderInfo:
    id: str
    name: str
    models: List[ModelInfo]
    rate_limit_note: str = ""

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "rate_limit_note": self.rate_limit_note,
            "models": [m.to_dict() for m in self.models],
        }

    @staticmethod
    def from_dict(data: Dict) -> "ProviderInfo":
        return ProviderInfo(
            id=data["id"],
            name=data["name"],
            rate_limit_note=data.get("rate_limit_note", ""),
            models=[ModelInfo.from_dict(m) for m in data.get("models", [])],
        )


@dataclass
class PromptTemplate:
    name: str
    template: str
    variables: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "template": self.template,
            "variables": self.variables,
        }

    @staticmethod
    def from_dict(data: Dict) -> "PromptTemplate":
        return PromptTemplate(
            name=data.get("name", "Template"),
            template=data.get("template", ""),
            variables=data.get("variables", {}),
        )


@dataclass
class StatsSnapshot:
    total: int = 0
    completed: int = 0
    errors: int = 0
    average_duration: float = 0.0
    per_provider: Dict[str, int] = field(default_factory=dict)
    per_model: Dict[str, int] = field(default_factory=dict)
    per_style: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "StatsSnapshot":
        return StatsSnapshot(
            total=data.get("total", 0),
            completed=data.get("completed", 0),
            errors=data.get("errors", 0),
            average_duration=data.get("average_duration", 0.0),
            per_provider=data.get("per_provider", {}),
            per_model=data.get("per_model", {}),
            per_style=data.get("per_style", {}),
        )


@dataclass
class GlobalSettings:
    provider_id: str = "mock"
    model_id: str = "mock-standard"
    size_preset: str = "Square 1024"
    custom_size: Optional[SizePreset] = None
    num_images: int = 1
    style_preset: str = "None"
    negative_prompt: str = ""
    seed: Optional[int] = None
    random_seed: bool = True
    quality: int = 5  # 1-10
    safety: int = 2  # 0-3
    export_folder: Optional[str] = None
    naming_pattern: str = "{index}_{slug}.png"
    concurrency_limit: int = 2
    theme: str = "system"
    prompt_highlighting: bool = False
    generate_behavior: str = "keep"  # keep or replace previous images
    regen_use_same_seed: bool = True
    confirm_generate_threshold: int = 300
    rate_limit_rpm: int = 60
    thinking_budget: int = 0  # For Nano Banana (2.5), 0=off, -1=dynamic
    thinking_level: str = "high"  # For Nano Banana Pro (3.0), "low" or "high"
    prompt_wrapper: str = ""

    def to_dict(self) -> Dict:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "GlobalSettings":
        return GlobalSettings(**data)


@dataclass
class RowSettings:
    provider_id: Optional[str] = None
    model_id: Optional[str] = None
    size_preset: Optional[str] = None
    custom_size: Optional[SizePreset] = None
    num_images: Optional[int] = None
    style_preset: Optional[str] = None
    negative_prompt: Optional[str] = None
    seed: Optional[int] = None
    random_seed: Optional[bool] = None
    quality: Optional[int] = None
    safety: Optional[int] = None
    keep_images: Optional[bool] = None
    generate_behavior: Optional[str] = None
    regen_use_same_seed: Optional[bool] = None
    thinking_budget: Optional[int] = None
    thinking_level: Optional[str] = None

    def to_dict(self) -> Dict:
        return dataclasses.asdict(self)

    @staticmethod
    def from_dict(data: Dict) -> "RowSettings":
        return RowSettings(**data)

    def is_override(self, field_name: str) -> bool:
        return getattr(self, field_name) is not None


@dataclass
class ImageResult:
    id: str
    row_id: str
    file_path: str
    metadata: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "row_id": self.row_id,
            "file_path": self.file_path,
            "metadata": self.metadata,
        }

    @staticmethod
    def from_dict(data: Dict) -> "ImageResult":
        return ImageResult(
            id=data["id"],
            row_id=data["row_id"],
            file_path=data["file_path"],
            metadata=data.get("metadata", {}),
        )


@dataclass
class GeneratedImage:
    file_path: Path
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GenerationContext:
    row_id: str
    row_index: int
    prompt_id: str
    category_id: str
    original_prompt: str
    full_prompt: str
    run_index: int = 1
    log_path: Optional[str] = None

    def to_metadata(self) -> Dict[str, Any]:
        return {
            "row_id": self.row_id,
            "row_index": self.row_index,
            "prompt_id": self.prompt_id,
            "category_id": self.category_id,
            "original_prompt": self.original_prompt,
            "full_prompt": self.full_prompt,
            "run_index": self.run_index,
        }


@dataclass
class RowData:
    id: str
    prompt: str = ""
    prompt_id: str = ""
    category_id: str = ""
    source_metadata: Dict[str, Any] = field(default_factory=dict)
    status: RowStatus = RowStatus.IDLE
    error_message: str = ""
    selected: bool = False
    settings: RowSettings = field(default_factory=RowSettings)
    attachments: List[InputAttachment] = field(default_factory=list)
    images: List[ImageResult] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    tags: List[str] = field(default_factory=list)
    last_duration: Optional[float] = None

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "prompt": self.prompt,
            "prompt_id": self.prompt_id,
            "category_id": self.category_id,
            "source_metadata": self.source_metadata,
            "status": self.status.value,
            "error_message": self.error_message,
            "selected": self.selected,
            "settings": self.settings.to_dict(),
            "attachments": [a.to_dict() for a in self.attachments],
            "images": [img.to_dict() for img in self.images],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "tags": self.tags,
            "last_duration": self.last_duration,
        }

    @staticmethod
    def from_dict(data: Dict) -> "RowData":
        return RowData(
            id=data["id"],
            prompt=data.get("prompt", ""),
            prompt_id=data.get("prompt_id", ""),
            category_id=data.get("category_id", ""),
            source_metadata=data.get("source_metadata", {}),
            status=RowStatus(data.get("status", RowStatus.IDLE.value)),
            error_message=data.get("error_message", ""),
            selected=data.get("selected", False),
            settings=RowSettings.from_dict(data.get("settings", {})),
            attachments=[InputAttachment.from_dict(a) for a in data.get("attachments", [])],
            images=[ImageResult.from_dict(img) for img in data.get("images", [])],
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            tags=data.get("tags", []),
            last_duration=data.get("last_duration"),
        )


@dataclass
class SessionData:
    id: str
    global_settings: GlobalSettings
    rows: List[RowData]
    version: str = "1.0"
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    templates: List[PromptTemplate] = field(default_factory=list)
    stats: StatsSnapshot = field(default_factory=StatsSnapshot)

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "version": self.version,
            "global_settings": self.global_settings.to_dict(),
            "rows": [row.to_dict() for row in self.rows],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "templates": [tpl.to_dict() for tpl in self.templates],
            "stats": self.stats.to_dict(),
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)

    @staticmethod
    def from_dict(data: Dict) -> "SessionData":
        return SessionData(
            id=data.get("id", str(uuid.uuid4())),
            global_settings=GlobalSettings.from_dict(data.get("global_settings", {})),
            rows=[RowData.from_dict(row) for row in data.get("rows", [])],
            version=data.get("version", "1.0"),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            templates=[PromptTemplate.from_dict(t) for t in data.get("templates", [])],
            stats=StatsSnapshot.from_dict(data.get("stats", {})),
        )


def effective_settings(row: RowData, global_settings: GlobalSettings) -> GlobalSettings:
    merged = dataclasses.asdict(global_settings)
    row_settings = dataclasses.asdict(row.settings)
    # Map keep_images into generate_behavior if provided.
    if row_settings.get("keep_images") is not None:
        merged["generate_behavior"] = "keep" if row_settings["keep_images"] else "replace"
    if row_settings.get("generate_behavior"):
        merged["generate_behavior"] = row_settings["generate_behavior"]
    for key, value in row_settings.items():
        if key in merged and value is not None:
            merged[key] = value
    # Map merged dict back into GlobalSettings-like object for consumption.
    return GlobalSettings(**merged)


def session_storage_dir() -> Path:
    base = Path.home() / ".imagen"
    base.mkdir(parents=True, exist_ok=True)
    return base


def default_session_path() -> Path:
    return session_storage_dir() / "last_session.json"
