"""Abstract LLM client with provider implementations."""
from __future__ import annotations
from abc import ABC, abstractmethod
from quell.core.models import QuellConfig


class LLMClient(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Send prompt and return text response."""
        ...

    @classmethod
    def from_config(cls, config: QuellConfig) -> "LLMClient":
        """Factory method: creates provider from config."""
        from quell.llm.providers.anthropic_provider import AnthropicProvider
        from quell.llm.providers.openai_provider import OpenAIProvider
        from quell.llm.providers.ollama_provider import OllamaProvider

        providers = {
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
        }
        provider_cls = providers.get(config.llm_provider)
        if not provider_cls:
            raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
        return provider_cls(config)
