from __future__ import annotations

import random
import time
import uuid
from pathlib import Path
from threading import Event
from typing import List

from PIL import Image, ImageDraw, ImageFont

from app.models import GeneratedImage, GenerationContext, GlobalSettings, ModelInfo, ProviderCapabilities
from .base import BaseProvider


def _ensure_font() -> ImageFont.ImageFont:
    try:
        return ImageFont.load_default()
    except Exception:
        return ImageFont.load_default()


class MockProvider(BaseProvider):
    id = "mock"
    name = "Mock Provider"

    def __init__(self) -> None:
        capabilities = ProviderCapabilities()
        model = ModelInfo(
            id="mock-standard",
            name="Mock Standard",
            provider_id=self.id,
            capabilities=capabilities,
        )
        super().__init__([model], rate_limit_note="Instant offline mock images.")

    def generate_images(
        self,
        prompt: str,
        settings: GlobalSettings,
        output_dir: Path,
        cancel_event: Event,
        attachments: List[object] = [],
        context: GenerationContext | None = None,
    ) -> List[GeneratedImage]:
        paths: List[GeneratedImage] = []
        count = max(1, min(settings.num_images, 8))
        size = settings.custom_size or {"width": 1024, "height": 1024}
        font = _ensure_font()

        for idx in range(count):
            if cancel_event.is_set():
                break
            img = Image.new(
                "RGB",
                (size.get("width", 1024), size.get("height", 1024)),
                color=_random_color(prompt, idx),
            )
            draw = ImageDraw.Draw(img)
            text = f"{prompt[:40] or 'Empty prompt'}\nStyle: {settings.style_preset}\nSeed: {settings.seed or 'auto'}"
            draw.text((20, 20), text, fill=(255, 255, 255), font=font)
            file_name = f"{int(time.time()*1000)}_{idx}.png"
            output_dir.mkdir(parents=True, exist_ok=True)
            path = output_dir / file_name
            img.save(path)
            paths.append(GeneratedImage(file_path=path, metadata={"provider": self.id, "model": settings.model_id}))
            time.sleep(0.2)
        return paths


def _random_color(prompt: str, idx: int) -> tuple:
    random.seed(hash(prompt) + idx)
    return (
        random.randint(32, 200),
        random.randint(32, 200),
        random.randint(32, 200),
    )
