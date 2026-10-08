import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Optional
import httpx
from PIL import Image
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ai.vision.base import BaseVisionProvider
from backend.app.ai.llm.provider import clean_json_text

VISION_EXTRACTION_PROMPT = """
You are an expert educational diagram and figure analyst.
Analyze the provided image from an educational course and extract structured knowledge.
Return ONLY a valid JSON object matching this schema:
{
  "visual_type": "diagram | chart | graph | table | figure | screenshot | flowchart",
  "title": "Short title of what is shown",
  "description": "Comprehensive explanation of the visual concepts, workflow, or data displayed",
  "concept": "Primary educational concept (e.g., Resource Allocation Graph, Safe State Matrix)",
  "entities": ["Entity 1", "Entity 2"],
  "relationships": ["Entity 1 points to / connects with Entity 2"],
  "key_takeaways": ["Main educational insight 1", "Main insight 2"]
}
"""

class GeminiVisionProvider(BaseVisionProvider):
    """Gemini Vision provider using google-genai."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-2.0-flash"
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def analyze_image(
        self,
        image_path: str,
        context_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not set.")
        
        path = Path(image_path)
        if not path.exists():
            return {"error": f"Image path {image_path} does not exist."}

        with open(path, "rb") as f:
            image_bytes = f.read()

        mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
        image_part = types.Part.from_bytes(data=image_bytes, mime_type=mime)

        prompt = context_prompt or VISION_EXTRACTION_PROMPT
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.1
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=[prompt, image_part],
            config=config
        )
        raw = clean_json_text(response.text or "{}")
        try:
            return json.loads(raw)
        except Exception as e:
            logger.error(f"Failed to parse Gemini Vision JSON: {e}")
            return {
                "visual_type": "figure",
                "description": response.text or "Visual element extracted",
                "concept": "Extracted Figure",
                "entities": [],
                "relationships": []
            }

class OllamaVisionProvider(BaseVisionProvider):
    """Local Ollama Vision provider (e.g., llama3.2-vision)."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_VISION_MODEL or "llama3.2-vision"

    async def analyze_image(
        self,
        image_path: str,
        context_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        path = Path(image_path)
        if not path.exists():
            return {"error": f"Image file not found: {image_path}"}

        with open(path, "rb") as f:
            img_b64 = base64.b64encode(f.read()).decode("utf-8")

        prompt = context_prompt or VISION_EXTRACTION_PROMPT
        payload = {
            "model": self.model,
            "prompt": prompt,
            "images": [img_b64],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0.1}
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = clean_json_text(data.get("response", "{}"))
            return json.loads(raw)

class MockVisionProvider(BaseVisionProvider):
    """Mock vision provider for offline testing."""

    async def analyze_image(
        self,
        image_path: str,
        context_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        filename = Path(image_path).stem
        clean_title = filename.replace("_", " ").replace("-", " ").title()

        return {
            "visual_type": "diagram" if any(w in filename.lower() for w in ["chart", "graph", "diagram", "figure", "map"]) else "figure",
            "title": f"Educational Figure: {clean_title}",
            "description": f"Visual conceptual diagram illustrating structural relationships, state transitions, and component behavior for {clean_title}.",
            "concept": clean_title,
            "entities": [f"{clean_title} Primary Component", f"{clean_title} Dependent Module"],
            "relationships": [f"{clean_title} Primary Component feeds data and state to {clean_title} Dependent Module"],
            "key_takeaways": [
                f"Visual verification of boundary conditions for {clean_title}.",
                "State integrity is maintained across all observed visual transitions."
            ]
        }

def get_vision_provider() -> BaseVisionProvider:
    provider_name = (settings.VISION_PROVIDER or "gemini").lower()
    if provider_name == "gemini":
        if settings.GEMINI_API_KEY:
            return GeminiVisionProvider()
        else:
            logger.warning("GEMINI_API_KEY not configured. Falling back to MockVisionProvider.")
            return MockVisionProvider()
    elif provider_name == "ollama":
        return OllamaVisionProvider()
    return MockVisionProvider()
