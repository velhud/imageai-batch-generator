from __future__ import annotations

import base64
import mimetypes
import os
from math import gcd
from pathlib import Path
from threading import Event
from typing import Any, Dict, List, Tuple

from app.models import DEFAULT_SIZE_PRESETS, GeneratedImage, GenerationContext, GlobalSettings, ModelInfo, ProviderCapabilities
from .base import BaseProvider

NANO_MODEL_ID = "gemini-2.5-flash-image"
PRO_MODEL_ID = "gemini-3-pro-image-preview"


class GoogleGeminiProvider(BaseProvider):
    id = "google"
    name = "Google Gemini"

    def __init__(self) -> None:
        base_capabilities = ProviderCapabilities(
            max_images=4,
            supports_style=False,
            supports_negative_prompt=True,
            supports_seed=False,
            supports_quality=False,
            supports_safety=True,
        )
        nano_caps = ProviderCapabilities(**base_capabilities.__dict__)
        pro_caps = ProviderCapabilities(**base_capabilities.__dict__)
        models = [
            ModelInfo(
                id=NANO_MODEL_ID,
                name="Nano Banana (Gemini 2.5 Flash Image)",
                provider_id=self.id,
                capabilities=nano_caps,
            ),
            ModelInfo(
                id=PRO_MODEL_ID,
                name="Nano Banana Pro (Gemini 3 Pro Image Preview)",
                provider_id=self.id,
                capabilities=pro_caps,
            ),
        ]
        super().__init__(models, rate_limit_note="Gemini API via GEMINI_API_KEY (.env)")

    def generate_images(
        self,
        prompt: str,
        settings: GlobalSettings,
        output_dir: Path,
        cancel_event: Event,
        attachments: List[Any] = [],
        context: GenerationContext | None = None,
    ) -> List[GeneratedImage]:
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            raise RuntimeError("Missing GEMINI_API_KEY. Add it to the project .env.")
        try:
            import requests  # type: ignore
        except Exception as exc:  # pragma: no cover - import-time guard
            raise RuntimeError(f"requests package not available: {exc}") from exc

        known_models = {m.id for m in self.models}
        model_id = settings.model_id or NANO_MODEL_ID
        if model_id not in known_models:
            model_id = NANO_MODEL_ID
        url = self._endpoint_for_model(model_id)
        output_dir.mkdir(parents=True, exist_ok=True)

        count = max(1, min(settings.num_images or 1, 4))
        paths: List[GeneratedImage] = []
        for idx in range(count):
            if cancel_event.is_set():
                break
            body = self._build_request_body(prompt, settings, model_id, attachments)
            self._log_request(model_id, body, attachments)
            try:
                response = requests.post(
                    url,
                    headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                    json=body,
                    timeout=120,
                )
            except Exception as exc:  # pragma: no cover - network runtime
                raise RuntimeError(f"Gemini request failed: {exc}") from exc
            if cancel_event.is_set():
                break
            if not response.ok:
                self._log_response_error(response)
                raise RuntimeError(f"Gemini error {response.status_code}: {response.text}")

            data = response.json()
            images = self._extract_inline_images(data)
            if not images:
                raise RuntimeError("No inline image data in Gemini response.")

            for part_idx, (b64_data, mime_type) in enumerate(images):
                if cancel_event.is_set():
                    break
                ext = self._extension_from_mime(mime_type)
                file_name = f"{model_id.replace('-', '_')}_{idx}_{part_idx}.{ext}"
                raw = base64.b64decode(b64_data)
                path = output_dir / file_name
                with open(path, "wb") as f:
                    f.write(raw)
                paths.append(
                    GeneratedImage(
                        file_path=path,
                        metadata={
                            "provider": self.id,
                            "model": model_id,
                            "mime_type": mime_type,
                            "output_format": ext,
                        },
                    )
                )

        if cancel_event.is_set() and not paths:
            raise RuntimeError("Cancelled")
        if not paths:
            raise RuntimeError("Gemini did not return any images.")
        return paths

    def _build_request_body(
        self,
        prompt: str,
        settings: GlobalSettings,
        model_id: str,
        attachments: List[Any] = [],
    ) -> Dict[str, Any]:
        attachments = attachments or []
        parts: List[Dict[str, Any]] = []
        parts.append({"text": prompt})

        for att in attachments:
            try:
                with open(att.file_path, "rb") as f:
                    file_data = f.read()
                b64_data = base64.b64encode(file_data).decode("utf-8")
                mime = att.mime_type or mimetypes.guess_type(att.file_path)[0] or "image/png"
                parts.append({"inlineData": {"mimeType": mime, "data": b64_data}})
            except Exception as exc:
                print(f"Error loading attachment {getattr(att, 'file_path', '')}: {exc}")

        if settings.negative_prompt:
            parts.append({"text": f"Negative prompt: {settings.negative_prompt}"})

        body: Dict[str, Any] = {"contents": [{"role": "user", "parts": parts}]}

        generation_config: Dict[str, Any] = {}
        image_config: Dict[str, Any] = {}
        thinking_config: Dict[str, Any] = {}

        aspect_ratio = self._aspect_ratio_from_settings(settings)
        if aspect_ratio:
            image_config["aspectRatio"] = aspect_ratio

        is_nano = "flash" in model_id
        is_pro = "pro" in model_id
        is_image_preview = "image-preview" in model_id
        thinking_supported = False

        if is_pro:
            generation_config["responseModalities"] = ["TEXT", "IMAGE"]
            image_size = self._image_size_from_settings(settings)
            if image_size:
                image_config["imageSize"] = image_size
            thinking_supported = not is_image_preview
            if thinking_supported and settings.thinking_level:
                thinking_config["thinkingLevel"] = settings.thinking_level
        elif is_nano:
            budget = settings.thinking_budget if settings.thinking_budget is not None else 0
            if budget != 0:
                thinking_config["thinkingBudget"] = budget

        if image_config:
            generation_config["imageConfig"] = image_config
        if thinking_config:
            generation_config["thinkingConfig"] = thinking_config
        if generation_config:
            body["generationConfig"] = generation_config

        if self._search_grounding_enabled() and is_pro:
            body["tools"] = [{"google_search": {}}]

        return body

    def _log_response_error(self, response: Any) -> None:
        try:
            payload = response.json()
        except Exception:
            payload = response.text
        try:
            print("[Gemini] Error", response.status_code, payload)
        except Exception:
            pass

    def _log_request(self, model_id: str, body: Dict[str, Any], attachments: List[Any]) -> None:
        try:
            parts = body.get("contents", [{}])[0].get("parts", [])
            generation = body.get("generationConfig", {})
            print(
                "[Gemini] Request",
                f"model={model_id}",
                f"parts={len(parts)}",
                f"attachments={len(attachments)}",
                f"imageConfig={generation.get('imageConfig')}",
                f"thinkingConfig={generation.get('thinkingConfig')}",
            )
        except Exception:
            # Logging should never break generation.
            pass

    def _extract_inline_images(self, response: Dict[str, Any]) -> List[Tuple[str, str]]:
        candidates = response.get("candidates") or []
        if not candidates:
            return []
        parts = candidates[0].get("content", {}).get("parts", [])
        images: List[Tuple[str, str]] = []
        for part in parts:
            inline = part.get("inlineData")
            if inline and inline.get("data"):
                images.append((inline["data"], inline.get("mimeType", "image/png")))
        return images

    def _endpoint_for_model(self, model_id: str) -> str:
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent"

    def _aspect_ratio_from_settings(self, settings: GlobalSettings) -> str | None:
        width, height = self._resolve_dimensions(settings)
        if not width or not height:
            return None
        divisor = gcd(width, height)
        if divisor == 0:
            return None
        return f"{width // divisor}:{height // divisor}"

    def _image_size_from_settings(self, settings: GlobalSettings) -> str:
        width, height = self._resolve_dimensions(settings)
        longest = max(width, height)
        if longest >= 3500:
            return "4K"
        if longest >= 2000:
            return "2K"
        return "1K"

    def _resolve_dimensions(self, settings: GlobalSettings) -> Tuple[int, int]:
        if settings.custom_size:
            width = int(settings.custom_size.get("width", 0) or 0)
            height = int(settings.custom_size.get("height", 0) or 0)
            if width > 0 and height > 0:
                return width, height

        preset = DEFAULT_SIZE_PRESETS.get(settings.size_preset or "", DEFAULT_SIZE_PRESETS["Square 1024"])
        return int(preset.get("width", 1024)), int(preset.get("height", 1024))

    def _extension_from_mime(self, mime_type: str | None) -> str:
        if not mime_type:
            return "png"
        if "jpeg" in mime_type or "jpg" in mime_type:
            return "jpg"
        if "webp" in mime_type:
            return "webp"
        return "png"

    def _search_grounding_enabled(self) -> bool:
        flag = os.environ.get("GEMINI_ENABLE_SEARCH", "")
        return flag.lower() in {"1", "true", "yes", "on"}
