from __future__ import annotations

import abc
from pathlib import Path
from threading import Event
from typing import Dict, List

from app.models import GlobalSettings, ModelInfo


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
    ) -> List[Path]:
        """Generate images for a prompt. Should respect cancel_event when possible."""

    def setup(self) -> None:
        """Optional heavy initialization."""
        return

    def teardown(self) -> None:
        return

    def available_models(self) -> List[ModelInfo]:
        return self.models
