"""
Platform-level image generation service (IMG-001).

Two-step pipeline:
1. Prompt refinement — Gemini 2.5 Flash (text) rewrites the raw prompt using best practices
2. Image generation — Gemini 2.5 Flash Image produces the actual image

Other code (routers, services, MCP tools, agents) calls:
    await image_generation_service.generate_image("a red apple", use_case="thumbnail")
"""

import base64
import logging
from dataclasses import dataclass, field
from typing import Optional

import httpx

from config import GEMINI_API_KEY
from services.image_generation_prompts import (
    USE_CASE_PROMPTS,
    VALID_ASPECT_RATIOS,
    VALID_USE_CASES,
)

logger = logging.getLogger(__name__)

# Gemini API configuration
GEMINI_TEXT_MODEL = "gemini-2.5-flash"
GEMINI_IMAGE_MODEL = "gemini-2.5-flash-image"
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"

# Timeouts
PROMPT_REFINEMENT_TIMEOUT = 30.0  # seconds
IMAGE_GENERATION_TIMEOUT = 120.0  # seconds — image gen can be slow


@dataclass
class ImageGenerationResult:
    """Result of an image generation request."""
    success: bool
    image_data: Optional[bytes] = None
    mime_type: str = "image/png"
    refined_prompt: Optional[str] = None
    original_prompt: Optional[str] = None
    model_used: str = GEMINI_IMAGE_MODEL
    use_case: str = "general"
    aspect_ratio: str = "1:1"
    error: Optional[str] = None


class ImageGenerationService:
    """Platform image generation service using Gemini models."""

    def __init__(self):
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def _http(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(IMAGE_GENERATION_TIMEOUT, connect=10.0),
            )
        return self._client

    @property
    def available(self) -> bool:
        """Whether the service has a configured API key."""
        return bool(GEMINI_API_KEY)

    async def generate_image(
        self,
        prompt: str,
        use_case: str = "general",
        aspect_ratio: str = "1:1",
        refine_prompt: bool = True,
        agent_name: Optional[str] = None,
    ) -> ImageGenerationResult:
        """Generate an image from a text prompt.

        Args:
            prompt: Raw text description of the desired image.
            use_case: One of "general", "thumbnail", "diagram", "social".
            aspect_ratio: One of "1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3".
            refine_prompt: If True, refine the prompt via Gemini text model first.
            agent_name: Optional agent name for logging/tracking.

        Returns:
            ImageGenerationResult with image bytes or error.
        """
        if not self.available:
            return ImageGenerationResult(
                success=False,
                original_prompt=prompt,
                use_case=use_case,
                aspect_ratio=aspect_ratio,
                error="GEMINI_API_KEY not configured",
            )

        if use_case not in VALID_USE_CASES:
            return ImageGenerationResult(
                success=False,
                original_prompt=prompt,
                use_case=use_case,
                aspect_ratio=aspect_ratio,
                error=f"Invalid use_case: {use_case}. Must be one of: {VALID_USE_CASES}",
            )

        if aspect_ratio not in VALID_ASPECT_RATIOS:
            return ImageGenerationResult(
                success=False,
                original_prompt=prompt,
                use_case=use_case,
                aspect_ratio=aspect_ratio,
                error=f"Invalid aspect_ratio: {aspect_ratio}. Must be one of: {VALID_ASPECT_RATIOS}",
            )

        log_prefix = f"[IMG {agent_name or 'platform'}]"

        # Step 1: Prompt refinement (optional)
        refined = prompt
        if refine_prompt:
            try:
                refined = await self.refine_prompt(prompt, use_case, aspect_ratio)
                logger.info(f"{log_prefix} Refined prompt: {refined[:100]}...")
            except Exception as e:
                logger.warning(f"{log_prefix} Prompt refinement failed, using raw prompt: {e}")
                refined = prompt

        # Step 2: Image generation
        try:
            image_bytes, mime_type = await self._call_gemini_image(refined, aspect_ratio)
            logger.info(
                f"{log_prefix} Generated image: {len(image_bytes)} bytes, "
                f"use_case={use_case}, aspect_ratio={aspect_ratio}"
            )
            return ImageGenerationResult(
                success=True,
                image_data=image_bytes,
                mime_type=mime_type,
                refined_prompt=refined,
                original_prompt=prompt,
                model_used=GEMINI_IMAGE_MODEL,
                use_case=use_case,
                aspect_ratio=aspect_ratio,
            )
        except Exception as e:
            logger.error(f"{log_prefix} Image generation failed: {e}")
            return ImageGenerationResult(
                success=False,
                refined_prompt=refined if refined != prompt else None,
                original_prompt=prompt,
                use_case=use_case,
                aspect_ratio=aspect_ratio,
                error=str(e),
            )

    async def refine_prompt(
        self,
        raw_prompt: str,
        use_case: str,
        aspect_ratio: str,
    ) -> str:
        """Refine a raw prompt using Gemini text model with best practices.

        Args:
            raw_prompt: The user's original description.
            use_case: The target use case for best practices selection.
            aspect_ratio: Target aspect ratio (for context in refinement).

        Returns:
            Refined prompt string optimized for image generation.
        """
        system_prompt = USE_CASE_PROMPTS.get(use_case, USE_CASE_PROMPTS["general"])
        user_message = (
            f"Aspect ratio: {aspect_ratio}\n\n"
            f"Raw description to refine:\n{raw_prompt}"
        )

        refined = await self._call_gemini_text(system_prompt, user_message)
        return refined.strip()

    async def _call_gemini_text(self, system_prompt: str, user_message: str) -> str:
        """Call Gemini text model for prompt refinement.

        Args:
            system_prompt: System instruction with best practices.
            user_message: The user's message to refine.

        Returns:
            The model's text response.

        Raises:
            RuntimeError: If the API call fails.
        """
        url = f"{GEMINI_API_BASE}/{GEMINI_TEXT_MODEL}:generateContent"

        payload = {
            "system_instruction": {
                "parts": [{"text": system_prompt}],
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user_message}],
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 512,
            },
        }

        response = await self._http.post(
            url,
            json=payload,
            headers={"x-goog-api-key": GEMINI_API_KEY},
            timeout=PROMPT_REFINEMENT_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini text API error {response.status_code}: {response.text[:500]}"
            )

        data = response.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as e:
            raise RuntimeError(f"Unexpected Gemini text response structure: {e}")

    async def _call_gemini_image(
        self, prompt: str, aspect_ratio: str
    ) -> tuple[bytes, str]:
        """Call Gemini image model to generate an image.

        Args:
            prompt: The refined prompt for image generation.
            aspect_ratio: Target aspect ratio.

        Returns:
            Tuple of (image_bytes, mime_type).

        Raises:
            RuntimeError: If the API call fails or returns no image.
        """
        url = f"{GEMINI_API_BASE}/{GEMINI_IMAGE_MODEL}:generateContent"

        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "responseModalities": ["image", "text"],
                "imageConfig": {
                    "aspectRatio": aspect_ratio,
                },
            },
        }

        response = await self._http.post(
            url,
            json=payload,
            headers={"x-goog-api-key": GEMINI_API_KEY},
            timeout=IMAGE_GENERATION_TIMEOUT,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Gemini image API error {response.status_code}: {response.text[:500]}"
            )

        data = response.json()

        # Find the image part in the response
        try:
            candidates = data["candidates"]
            for candidate in candidates:
                parts = candidate.get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        inline = part["inlineData"]
                        image_b64 = inline["data"]
                        mime_type = inline.get("mimeType", "image/png")
                        return base64.b64decode(image_b64), mime_type
        except (KeyError, IndexError):
            pass

        raise RuntimeError(
            "Gemini image API returned no image data. "
            "The prompt may have been blocked by safety filters."
        )

    async def close(self):
        """Close the HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_image_generation_service: Optional[ImageGenerationService] = None


def get_image_generation_service() -> ImageGenerationService:
    """Get the global ImageGenerationService instance."""
    global _image_generation_service
    if _image_generation_service is None:
        _image_generation_service = ImageGenerationService()
    return _image_generation_service
