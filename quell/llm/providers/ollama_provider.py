"""Ollama provider for local LLM — privacy-first option."""
from __future__ import annotations
import httpx
from quell.llm.client import LLMClient
from quell.core.models import QuellConfig


class OllamaProvider(LLMClient):
    def __init__(self, config: QuellConfig):
        self.base_url = config.ollama_base_url
        self.model = config.llm_model  # e.g., "codellama", "deepseek-coder"

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]
