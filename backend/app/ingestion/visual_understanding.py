from typing import Dict, Any, List
from backend.app.ai.vision.provider import get_vision_provider
from backend.app.core.logging import logger

class VisualUnderstandingService:
    """Orchestrates Multimodal Vision analysis on extracted diagrams, charts, and figures."""

    def __init__(self):
        self.vision_provider = get_vision_provider()

    async def analyze_visual(self, image_path: str, context_hint: str = "") -> Dict[str, Any]:
        """Runs multimodal vision model and returns structured visual entity analysis."""
        try:
            logger.info(f"Analyzing visual element: {image_path}")
            result = await self.vision_provider.analyze_image(
                image_path=image_path,
                context_prompt=f"Educational document context: {context_hint}" if context_hint else None
            )
            return result
        except Exception as e:
            logger.error(f"Visual understanding failed for {image_path}: {e}")
            return {
                "visual_type": "figure",
                "title": "Extracted Diagram",
                "description": "Visual diagram extracted from course material.",
                "concept": "Diagram",
                "entities": [],
                "relationships": [],
                "key_takeaways": []
            }

visual_understander = VisualUnderstandingService()
