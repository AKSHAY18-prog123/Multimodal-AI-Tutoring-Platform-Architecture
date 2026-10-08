import os
import json
import re
from typing import Optional, Dict, Any, List
import httpx
from google import genai
from google.genai import types

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.ai.llm.base import BaseLLMProvider

def clean_json_text(text: str) -> str:
    """Strip markdown code fence blocks if present."""
    text = text.strip()
    match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
    if match:
        return match.group(1).strip()
    return text

class GeminiLLMProvider(BaseLLMProvider):
    """Google Gemini LLM provider using the modern google-genai SDK."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.model = model or settings.GEMINI_MODEL or "gemini-2.0-flash"
        if not self.api_key:
            logger.warning("GEMINI_API_KEY not configured. Calls to Gemini may fail or fall back.")
        self.client = genai.Client(api_key=self.api_key) if self.api_key else None

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> str:
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not set. Please provide it in .env or switch to mock/ollama.")
        
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            max_output_tokens=max_tokens
        )
        # google-genai client.aio handles async generation
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=config
        )
        return response.text or ""

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        if not self.client:
            raise ValueError("GEMINI_API_KEY is not set. Please provide it in .env or switch to mock/ollama.")
        
        enhanced_prompt = f"{prompt}\n\nRespond ONLY with a valid JSON object. No Markdown code fences, no extra commentary."
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=temperature,
            response_mime_type="application/json"
        )
        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=enhanced_prompt,
            config=config
        )
        raw = clean_json_text(response.text or "{}")
        try:
            return json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON: {raw[:200]}")
            return {"raw_text": raw, "error": str(e)}

class OllamaLLMProvider(BaseLLMProvider):
    """Local Ollama LLM provider for local offline inference."""

    def __init__(self, base_url: Optional[str] = None, model: Optional[str] = None):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL or "llama3.2"

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> str:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": prompt,
            "system": system_prompt or "",
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/api/generate"
        payload = {
            "model": self.model,
            "prompt": f"{prompt}\n\nReturn strictly valid JSON.",
            "system": system_prompt or "",
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature
            }
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("response", "{}")
            return json.loads(clean_json_text(raw))

class MockLLMProvider(BaseLLMProvider):
    """High-fidelity, subject-agnostic mock LLM for testing, CI, and zero-key development."""

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> str:
        prompt_lower = prompt.lower()

        # Check for out-of-material questions
        if any(w in prompt_lower for w in ["nvidia gpu", "weather", "recipe", "stock price", "celebrity"]):
            return "This topic is not covered in the uploaded course material. Would you like an outside-knowledge explanation?"

        # Extract citation headers from prompt if present
        source_matches = re.findall(r"\[Source:\s*([^\]]+)\]", prompt)
        citation_str = f"[{source_matches[0]}]" if source_matches else "[Source: Course Syllabus • Section 1]"

        # Extract question if present
        q_match = re.search(r"--- STUDENT QUESTION ---\s*(.+?)(?:\n---|\nProvide|\Z)", prompt, re.DOTALL)
        question_text = q_match.group(1).strip() if q_match else ""

        # Extract key subject/topic keywords from prompt
        subject_match = re.search(r"Course Subject:\s*([^\n]+)", prompt)
        subject_str = subject_match.group(1).strip() if subject_match else "this field"

        # Check if retrieved course context exists
        ctx_match = re.search(r"--- RETRIEVED COURSE SOURCES ---\s*(.+?)\s*--- STUDENT QUESTION ---", prompt, re.DOTALL)
        if ctx_match and len(ctx_match.group(1).strip()) > 30:
            snippet = ctx_match.group(1).strip()
            # Clean snippet for summary
            first_lines = [l.strip() for l in snippet.split("\n") if l.strip() and not l.startswith("[Source:")][:3]
            summary_content = " ".join(first_lines)
            return (
                f"### Understanding the Core Concept\n\n"
                f"{summary_content}\n\n"
                f"**Key Analytical Insights:**\n"
                f"- **Foundational Mechanism**: The underlying system behavior is strictly bounded by state invariants and validated pre-conditions.\n"
                f"- **Operational Workflow**: As inputs and resource requests proceed, formal verification ensures no inconsistent or deadlocked states arise.\n"
                f"- **Academic Takeaway**: Mastery of this topic enables predictive reasoning across complex scenarios in {subject_str}.\n\n"
                f"{citation_str}\n\n"
                f"**Next Questions to Explore:**\n"
                f"1. Would you like to walk through a concrete numeric or code example?\n"
                f"2. How does this compare with alternative state management approaches?"
            )

        target = question_text or "this concept"
        return (
            f"### Overview of {target}\n\n"
            f"Based on the course materials provided, **{target}** represents a fundamental framework in {subject_str}.\n\n"
            f"- **Principle**: Establishes standard definitions, governing equations, and transition rules.\n"
            f"- **Significance**: Allows systematic analysis and predictable behavior across complex problem spaces.\n\n"
            f"{citation_str}\n\n"
            f"**Suggested Next Steps:**\n"
            f"1. Can we examine a step-by-step application problem?\n"
            f"2. Would you like a practice assessment to verify your understanding?"
        )

    async def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1
    ) -> Dict[str, Any]:
        prompt_lower = prompt.lower()

        # Dynamic Topic/Taxonomy Extraction from uploaded text
        if "extract a structured hierarchy" in prompt_lower or "course taxonomy" in prompt_lower or "topic" in prompt_lower and "concepts" in prompt_lower:
            # Extract sample text excerpt from prompt
            text_match = re.search(r"Course Material Content Excerpt:\s*(.+)", prompt, re.DOTALL)
            sample = text_match.group(1).strip() if text_match else ""

            # Detect lines or headings in sample text
            headings = [line.strip("#*- \t") for line in sample.split("\n") if len(line.strip("#*- \t")) > 5 and len(line.strip("#*- \t")) < 60]
            t1 = headings[0] if len(headings) > 0 else "Core Foundations"
            t2 = headings[1] if len(headings) > 1 else "Advanced Principles"
            c1 = headings[2] if len(headings) > 2 else "Theoretical Foundations"
            c2 = headings[3] if len(headings) > 3 else "System Architecture & Mechanics"
            c3 = headings[4] if len(headings) > 4 else "Operational Analysis & Methods"
            c4 = headings[5] if len(headings) > 5 else "Practical Applications & Optimization"

            return {
                "topics": [
                    {
                        "title": t1,
                        "description": f"Foundational curriculum principles and primary mechanisms for {t1}.",
                        "concepts": [
                            {"name": c1, "subtopic": "Fundamentals", "definition": f"Core theoretical foundation of {c1}.", "difficulty": "easy"},
                            {"name": c2, "subtopic": "Mechanics", "definition": f"Systematic operational principles of {c2}.", "difficulty": "medium"}
                        ]
                    },
                    {
                        "title": t2,
                        "description": f"Applied concepts, analytical techniques, and performance considerations for {t2}.",
                        "concepts": [
                            {"name": c3, "subtopic": "Analysis", "definition": f"Analytical framework and behavioral rules for {c3}.", "difficulty": "medium"},
                            {"name": c4, "subtopic": "Optimization", "definition": f"Design trade-offs and performance criteria for {c4}.", "difficulty": "hard"}
                        ]
                    }
                ],
                "relationships": [
                    {
                        "source_concept": c1,
                        "target_concept": c2,
                        "relationship_type": "prerequisite",
                        "strength": 1.0
                    },
                    {
                        "source_concept": c2,
                        "target_concept": c3,
                        "relationship_type": "prerequisite",
                        "strength": 0.9
                    },
                    {
                        "source_concept": c3,
                        "target_concept": c4,
                        "relationship_type": "prerequisite",
                        "strength": 0.85
                    }
                ]
            }

        # Dynamic Question Generation
        if "target concept:" in prompt_lower or "generate an educational assessment question" in prompt_lower or "question_type" in prompt_lower:
            concept_match = re.search(r"Target Concept:\s*([^\n]+)", prompt)
            topic_match = re.search(r"Topic:\s*([^\n]+)", prompt)
            diff_match = re.search(r"Difficulty:\s*([^\n]+)", prompt)

            concept = concept_match.group(1).strip() if concept_match else "Fundamental Principles"
            topic = topic_match.group(1).strip() if topic_match else "Curriculum Domain"
            difficulty = diff_match.group(1).strip() if diff_match else "medium"

            return {
                "question": f"In the context of {topic}, which of the following statements regarding {concept} is correct?",
                "question_type": "mcq",
                "difficulty": difficulty,
                "options": [
                    {"id": "A", "text": f"It establishes the verified state boundaries and governing constraints for {concept}."},
                    {"id": "B", "text": f"It eliminates the requirement for prerequisite knowledge in {topic}."},
                    {"id": "C", "text": f"It operates as a completely non-deterministic variable with arbitrary state transitions."},
                    {"id": "D", "text": f"It replaces all downstream analytical methods with unvalidated heuristics."}
                ],
                "correct_answer": "A",
                "explanation": f"In {topic}, {concept} serves as a critical structural component that establishes valid state boundaries, verifying that subsequent operations conform to verified constraints.",
                "concept": concept,
                "topic": topic,
                "verification_status": "verified"
            }

        # Query understanding fallback
        if "query analyzer" in prompt_lower or "intent:" in prompt_lower:
            return {
                "intent": "conceptual_explanation",
                "relevance": "on_topic",
                "keywords": ["Fundamentals", "Principles"],
                "explicit_outside_request": False
            }

        return {
            "status": "success",
            "message": "Mock structured response generated."
        }

def get_llm_provider() -> BaseLLMProvider:
    """Factory to instantiate the configured LLM provider with fallback handling."""
    provider_name = (settings.LLM_PROVIDER or "gemini").lower()
    
    if provider_name == "gemini":
        if settings.GEMINI_API_KEY:
            return GeminiLLMProvider()
        else:
            logger.warning("GEMINI_API_KEY is empty. Falling back to MockLLMProvider for offline execution.")
            return MockLLMProvider()
    elif provider_name == "ollama":
        return OllamaLLMProvider()
    elif provider_name == "mock":
        return MockLLMProvider()
    else:
        logger.warning(f"Unknown LLM_PROVIDER '{provider_name}'. Defaulting to Mock.")
        return MockLLMProvider()
