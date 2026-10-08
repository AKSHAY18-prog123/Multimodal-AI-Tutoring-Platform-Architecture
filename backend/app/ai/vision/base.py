from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

class BaseVisionProvider(ABC):
    """Abstract interface for Multimodal Vision models."""

    @abstractmethod
    async def analyze_image(
        self,
        image_path: str,
        context_prompt: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze an extracted image/diagram and produce structured pedagogical understanding."""
        pass
