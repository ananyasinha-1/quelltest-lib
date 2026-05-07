from __future__ import annotations
import openai
from quell.llm.client import LLMClient
from quell.core.models import QuellConfig


class OpenAIProvider(LLMClient):
    def __init__(self, config: QuellConfig):
        self.client = openai.AsyncOpenAI()  # reads OPENAI_API_KEY from env
        self.model = config.llm_model

    async def generate(self, prompt: str) -> str:
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        )
        return response.choices[0].message.content or ""
