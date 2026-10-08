from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List

class BaseLLMProvider(ABC):
    """Abstract interface for Large Language Model providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> str:
        """Generate text response from the model."""
        pass

    @abstractmethod
    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        """Generate structured JSON response parsed into a Python dictionary."""
        pass
