"""Abstract LLM client + factory."""
from __future__ import annotations

from abc import ABC, abstractmethod

from quell.core.models import QuellConfig


class LLMClient(ABC):
    """Abstract base for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Send prompt, return text response."""
        ...

    @classmethod
    def from_config(cls, config: QuellConfig) -> LLMClient:
        """Factory: create provider from config."""
        from quell.llm.providers.anthropic_provider import AnthropicProvider
        from quell.llm.providers.ollama_provider import OllamaProvider
        from quell.llm.providers.openai_provider import OpenAIProvider
        return {
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
        }[config.llm_provider](config)
