"""
Reads natural language bug descriptions → BUG_REPRO Requirements.

This is "quell reproduce" — TDD from a bug report.

Flow:
1. LLM parses description → function hint + triggering inputs + expected behavior
2. Search codebase for matching function
3. Return BUG_REPRO Requirement

Verification engine then:
- Generates failing test (reproduces bug on current broken code)
- Verifies test FAILS now (bug confirmed)
- After dev fixes code: test PASSES (fix confirmed)

This is the ONLY tool that automates the full TDD bug-fixing loop.
"""
from __future__ import annotations
import ast, json, uuid
from pathlib import Path
from quell.core.models import Requirement, ConstraintKind, SpecSource


class BugReader:
    """Converts natural language bug descriptions to BUG_REPRO Requirements."""

    def __init__(self, llm_client: object, project_root: Path = Path(".")):
        self.llm = llm_client
        self.project_root = project_root

    def read_from_description(
        self,
        description: str,
        target_file: Path | None = None,
    ) -> list[Requirement]:
        """
        Parse a bug description and return BUG_REPRO Requirements.
        Called by: quell reproduce "bug description"
        """
        import asyncio
        bug_info = asyncio.run(self._extract(description))
        hint = bug_info.get("function_hint", "")

        if target_file:
            func, path = self._find_in_file(hint, target_file)
        else:
            func, path = self._search_codebase(hint)

        return [Requirement(
            id=str(uuid.uuid4())[:8],
            description=description,
            constraint_kind=ConstraintKind.BUG_REPRO,
            source=SpecSource.BUG_REPORT,
            target_function=func or hint or "unknown",
            target_file=path or target_file or self.project_root / "src" / "unknown.py",
            violation_input=bug_info.get("triggering_inputs"),
            expected_behavior=bug_info.get("expected_behavior"),
            raw_spec_text=description,
        )]

    def read(self, file_path: Path) -> list[Requirement]:
        """Protocol compliance — use read_from_description instead."""
        return []

    async def _extract(self, description: str) -> dict:  # type: ignore[type-arg]
        prompt = f"""Parse this bug report. Return ONLY valid JSON, no other text.

Bug: "{description}"

{{"function_hint": "function name likely involved",
  "triggering_inputs": {{"param": "value_or_null"}},
  "symptom": "what goes wrong",
  "expected_behavior": "what should happen instead"}}"""
        try:
            response = await self.llm.generate(prompt)  # type: ignore[attr-defined]
            return json.loads(response)
        except Exception:
            return {}

    def _find_in_file(
        self, hint: str, path: Path
    ) -> tuple[str | None, Path | None]:
        try:
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if hint.lower() in node.name.lower():
                        return node.name, path
        except Exception:
            pass
        return None, None

    def _search_codebase(
        self, hint: str
    ) -> tuple[str | None, Path | None]:
        for py in self.project_root.rglob("*.py"):
            if "test" in py.name or ".venv" in str(py):
                continue
            n, p = self._find_in_file(hint, py)
            if n:
                return n, p
        return None, None

    @property
    def source_name(self) -> str:
        """Reader name."""
        return "bug_report"
