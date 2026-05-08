from quell.llm.client import LLMClient
from quell.core.models import QuellConfig
import anthropic


class AnthropicProvider(LLMClient):
    """Anthropic Claude provider. Reads ANTHROPIC_API_KEY from env."""

    def __init__(self, config: QuellConfig):
        self.client = anthropic.Anthropic()
        self.model = config.llm_model

    async def generate(self, prompt: str) -> str:
        """Generate a response from Claude."""
        msg = self.client.messages.create(
            model=self.model, max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text
