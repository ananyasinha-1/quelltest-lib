"""
LLM-powered code fix suggester.

ONLY runs after a verified failing test exists.
Never suggests a fix without first proving the bug with a test.

Flow:
  1. CodeGuardReader finds a gap (no test for this guard)
  2. Verifier generates + proves a failing test
  3. Suggester asks LLM for a code fix
  4. Suggester verifies: apply fix → test must now PASS
  5. Show diff to developer — never auto-apply

Different from Refactron:
  Refactron: linter output → safe style fix (syntax level)
  Suggester: logic gap + failing test → logic/security fix (semantic level)

Different from Corgea:
  Corgea: finds bug → auto-generates fix PR (no test proof)
  Suggester: finds bug → PROVES it with failing test → suggests fix
             → VERIFIES fix makes test pass → shows diff

You never apply a fix that isn't proven to work.
"""
from __future__ import annotations

import ast
import difflib
import re
import subprocess

from quell.core.models import GeneratedTest, QuellConfig, Requirement
from quell.llm.client import LLMClient


class FixSuggestion:
    """Result of a fix suggestion attempt."""

    def __init__(
        self,
        requirement: Requirement,
        failing_test: GeneratedTest,
        original_code: str,
        suggested_code: str,
        diff: str,
        verified: bool,
        explanation: str,
    ) -> None:
        self.requirement = requirement
        self.failing_test = failing_test
        self.original_code = original_code
        self.suggested_code = suggested_code
        self.diff = diff
        self.verified = verified
        self.explanation = explanation


class FixSuggester:
    """
    Suggests code fixes after a failing test is proven to exist.

    The test MUST be verified as failing before this is called.
    This ensures every suggestion has proven value.
    """

    def __init__(self, llm: LLMClient, config: QuellConfig) -> None:
        self.llm = llm
        self.config = config

    async def suggest(
        self,
        req: Requirement,
        failing_test: GeneratedTest,
    ) -> FixSuggestion | None:
        """
        Given a requirement with a failing test, suggest a code fix.
        Returns None if no good fix can be generated.
        """
        original_source = req.target_file.read_text(encoding="utf-8")
        function_source = self._extract_function(original_source, req.target_function)

        prompt = self._build_prompt(req, failing_test, function_source)
        response = await self.llm.generate(prompt)
        suggested_function = self._extract_code_block(response)
        explanation = self._extract_explanation(response)

        if not suggested_function:
            return None

        suggested_source = original_source.replace(function_source, suggested_function, 1)
        verified = self._verify_fix_makes_test_pass(req, failing_test, suggested_source)
        diff = self._generate_diff(function_source, suggested_function)

        return FixSuggestion(
            requirement=req,
            failing_test=failing_test,
            original_code=function_source,
            suggested_code=suggested_function,
            diff=diff,
            verified=verified,
            explanation=explanation,
        )

    def _build_prompt(
        self, req: Requirement, test: GeneratedTest, function_source: str
    ) -> str:
        return f"""You are a Python security and correctness expert.

A test has PROVEN that this code has a logic gap:

FAILING TEST (proves the bug exists):
```python
{test.test_code}
```

CURRENT FUNCTION WITH THE GAP:
```python
{function_source}
```

GAP DESCRIPTION: {req.description}
GAP TYPE: {req.constraint_kind.value}
RAW GUARD: {req.raw_spec_text}

YOUR TASK:
Suggest a fix for the function that makes the failing test pass.

RULES:
- Fix ONLY the specific logic gap, nothing else
- Do NOT change function signature
- Do NOT add imports that don't exist in the file
- Do NOT change behavior for valid inputs
- For security gaps: add the missing validation/check
- For null gaps: add None check with appropriate raise
- For boundary gaps: add the missing boundary check
- Keep the fix minimal — smallest change that fixes the gap

RESPONSE FORMAT:
First, one sentence explaining what the fix does.
Then the fixed function in a Python code block.

```python
# fixed function here
```"""

    def _verify_fix_makes_test_pass(
        self,
        req: Requirement,
        test: GeneratedTest,
        suggested_source: str,
    ) -> bool:
        """Apply fix to a temp copy and run the failing test — must now PASS."""
        backup_dir = self.config.backup_dir
        backup_dir.mkdir(parents=True, exist_ok=True)

        temp_test = backup_dir / f"quell_fix_test_{req.id}.py"
        original = req.target_file.read_text(encoding="utf-8")
        try:
            req.target_file.write_text(suggested_source, encoding="utf-8")
            temp_test.write_text(test.test_code, encoding="utf-8")

            result = subprocess.run(
                ["python", "-m", "pytest", str(temp_test), "-v", "-q"],
                capture_output=True,
                text=True,
                timeout=self.config.verification_timeout_seconds,
                cwd=req.target_file.parent.parent,
            )
            return result.returncode == 0

        except Exception:
            return False
        finally:
            req.target_file.write_text(original, encoding="utf-8")
            temp_test.unlink(missing_ok=True)

    def _extract_function(self, source: str, function_name: str) -> str:
        """Extract just the named function's source lines from a file."""
        try:
            tree = ast.parse(source)
            lines = source.splitlines(keepends=True)
            for node in ast.walk(tree):
                if (
                    isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and node.name == function_name
                    and node.end_lineno is not None
                ):
                    return "".join(lines[node.lineno - 1 : node.end_lineno])
        except Exception:
            pass
        return source

    def _generate_diff(self, original: str, suggested: str) -> str:
        """Return a unified diff string between original and suggested code."""
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            suggested.splitlines(keepends=True),
            fromfile="original",
            tofile="suggested",
            lineterm="",
        )
        return "".join(diff)

    def _extract_code_block(self, response: str) -> str | None:
        match = re.search(r"```python\n(.*?)```", response, re.DOTALL)
        return match.group(1).strip() if match else None

    def _extract_explanation(self, response: str) -> str:
        for line in response.strip().splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("```"):
                return stripped
        return "Fix suggested by Quell"
