from __future__ import annotations
import anthropic
from quell.llm.client import LLMClient
from quell.core.models import QuellConfig


class AnthropicProvider(LLMClient):
    def __init__(self, config: QuellConfig):
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
        self.model = config.llm_model

    async def generate(self, prompt: str) -> str:
        message = self.client.messages.create(
            model=self.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return message.content[0].text
