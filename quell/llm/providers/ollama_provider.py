"""Local LLM — zero API key, privacy-first. Works offline."""
import httpx
from quell.llm.client import LLMClient
from quell.core.models import QuellConfig


class OllamaProvider(LLMClient):
    """Ollama local LLM provider. Works with any model (codellama, deepseek-coder, etc.)."""

    def __init__(self, config: QuellConfig):
        self.base_url = config.ollama_base_url
        self.model = config.llm_model

    async def generate(self, prompt: str) -> str:
        """Generate a response from local Ollama instance."""
        async with httpx.AsyncClient(timeout=60.0) as c:
            r = await c.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            r.raise_for_status()
            return r.json()["response"]
