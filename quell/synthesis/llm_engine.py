"""
LLM-based test generation. Used when rule engine cannot handle the case.

Called for: CUSTOM constraints, complex mutations, unstructured specs,
and to complete/improve rule-engine scaffolding into real test code.

Key principle: the LLM generates the test code, but the VERIFIER
proves it works before it's accepted. LLM hallucinations are caught
by verification — not a blocker, just a retry trigger.
"""
from __future__ import annotations

import re

from quell.core.models import GeneratedTest, QuellConfig, Requirement
from quell.llm.client import LLMClient
from quell.llm.prompts import build_prompt


class LLMSynthesizer:
    """LLM-powered test synthesizer. Falls back from rule engine."""

    def __init__(self, client: LLMClient, config: QuellConfig):
        self.client = client
        self.config = config

    async def synthesize(self, req: Requirement) -> GeneratedTest:
        """Generate a test for req using the configured LLM."""
        prompt = build_prompt(req)
        response = await self.client.generate(prompt)
        code = self._extract_code(response)
        name = self._extract_name(code) or f"test_quell_{req.target_function}_{req.id}"

        return GeneratedTest(
            requirement_id=req.id,
            test_function_name=name,
            test_code=code,
            test_file_path=(
                req.target_file.parent.parent / "tests" /
                f"test_{req.target_file.stem}.py"
            ),
            explanation=f"LLM-generated test for: {req.description}",
            generated_by=f"llm:{self.config.llm_model}",
        )

    def _extract_code(self, response: str) -> str:
        m = re.search(r'```python\n(.*?)```', response, re.DOTALL)
        return m.group(1).strip() if m else response.strip()

    def _extract_name(self, code: str) -> str | None:
        m = re.search(r'^def\s+(test_\w+)', code, re.MULTILINE)
        return m.group(1) if m else None
