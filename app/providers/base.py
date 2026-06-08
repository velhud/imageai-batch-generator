from __future__ import annotations

import abc
from pathlib import Path
from threading import Event
from typing import Any, Dict, List, Optional

from app.models import GeneratedImage, GenerationContext, GlobalSettings, ModelInfo


class ProviderGenerationError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status: str = "failed",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.status = status
        self.metadata = metadata or {}


class ProviderFilteredError(ProviderGenerationError):
    def __init__(self, message: str, *, metadata: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, status="filtered", metadata=metadata)


class ProviderRetryExhaustedError(ProviderGenerationError):
    def __init__(self, message: str, *, metadata: Optional[Dict[str, Any]] = None) -> None:
        super().__init__(message, status="retry_exhausted", metadata=metadata)


class BaseProvider(abc.ABC):
    id: str = "base"
    name: str = "Base Provider"

    def __init__(self, models: List[ModelInfo], rate_limit_note: str = "") -> None:
        self.models = models
        self.rate_limit_note = rate_limit_note

    @abc.abstractmethod
    def generate_images(
        self,
        prompt: str,
        settings: GlobalSettings,
        output_dir: Path,
        cancel_event: Event,
        attachments: List[object] = [],
        context: GenerationContext | None = None,
    ) -> List[GeneratedImage]:
        """Generate images for a prompt. Should respect cancel_event when possible."""

    def quota_cost(self, settings: GlobalSettings) -> int:
        return 1

    def setup(self) -> None:
        """Optional heavy initialization."""
        return

    def teardown(self) -> None:
        return

    def available_models(self) -> List[ModelInfo]:
        return self.models
