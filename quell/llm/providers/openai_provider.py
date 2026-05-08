from openai import AsyncOpenAI

from quell.core.models import QuellConfig
from quell.llm.client import LLMClient


class OpenAIProvider(LLMClient):
    """OpenAI provider. Reads OPENAI_API_KEY from env."""

    def __init__(self, config: QuellConfig):
        self.client = AsyncOpenAI()
        self.model = config.llm_model

    async def generate(self, prompt: str) -> str:
        """Generate a response from OpenAI."""
        r = await self.client.chat.completions.create(
            model=self.model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return r.choices[0].message.content or ""
