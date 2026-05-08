"""
Programmatic API. Use in CI scripts, MCP servers, other tools.

from quell import Quell
q = Quell()
q.check("src/")                    # find gaps
q.check("src/", fix=True)          # find + fix
q.reproduce("zero amount accepted") # bug → test
q.prove("src/payments.py")         # confidence score
q.score()                           # project score
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass
from pathlib import Path
from quell.core.models import Requirement, ProjectScore, QuellConfig


@dataclass
class CheckResult:
    """Result of quell.check()."""
    requirements: list[Requirement]
    score: float

    @property
    def uncovered(self) -> list[Requirement]:
        """Requirements with no covering tests."""
        return [r for r in self.requirements if not r.is_covered]

    @property
    def covered(self) -> list[Requirement]:
        """Requirements that already have tests."""
        return [r for r in self.requirements if r.is_covered]


class Quell:
    """Main entry point for the Quell SDK."""

    def __init__(
        self,
        llm: str = "anthropic",
        model: str | None = None,
        project_root: str | Path = ".",
    ):
        self.config = QuellConfig(llm_provider=llm)
        if model:
            self.config = self.config.model_copy(update={"llm_model": model})
        self.root = Path(project_root)

    def check(
        self,
        target: str | Path,
        sources: list[str] | None = None,
        fix: bool = False,
    ) -> CheckResult:
        """Scan target for requirement gaps. Optionally generate tests (fix=True)."""
        return asyncio.run(
            self._check(Path(target), sources or ["docstring", "type"], fix)
        )

    def reproduce(self, description: str, file: str | Path | None = None) -> bool:
        """Convert a bug description to a verified failing test. Returns True if written."""
        return asyncio.run(
            self._reproduce(description, Path(file) if file else None)
        )

    def prove(self, file: str | Path, function: str | None = None) -> float:
        """Return requirement coverage score (0.0–1.0) for a file/function."""
        result = self.check(file)
        reqs = (
            [r for r in result.requirements if r.target_function == function]
            if function else result.requirements
        )
        total = len(reqs)
        return sum(1 for r in reqs if r.is_covered) / total if total else 0.0

    def score(self) -> ProjectScore:
        """Calculate project-wide Quell Score."""
        from quell.score.calculator import calculate_score
        return calculate_score(self.root)

    async def _check(
        self, target: Path, sources: list[str], fix: bool
    ) -> CheckResult:
        from quell.spec.docstring_reader import DocstringReader
        from quell.spec.type_reader import TypeReader
        from quell.coverage.checker import CoverageChecker
        from quell.llm.client import LLMClient

        llm = LLMClient.from_config(self.config)
        files = (
            [
                f for f in target.rglob("*.py")
                if "test" not in f.name and ".venv" not in str(f)
            ]
            if target.is_dir() else [target]
        )
        reqs: list[Requirement] = []
        for f in files:
            if "docstring" in sources:
                reqs.extend(DocstringReader(llm).read(f))
            if "type" in sources:
                reqs.extend(TypeReader().read(f))

        reqs = CoverageChecker(self.root).check(reqs)
        total = len(reqs)
        covered = sum(1 for r in reqs if r.is_covered)
        return CheckResult(
            requirements=reqs,
            score=covered / total if total else 0.0,
        )

    async def _reproduce(
        self, description: str, target_file: Path | None
    ) -> bool:
        from quell.spec.bug_reader import BugReader
        from quell.synthesis.llm_engine import LLMSynthesizer
        from quell.core.verifier import Verifier
        from quell.core.writer import Writer
        from quell.core.models import VerificationStatus
        from quell.llm.client import LLMClient

        llm = LLMClient.from_config(self.config)
        reqs = BugReader(llm, self.root).read_from_description(
            description, target_file
        )
        if not reqs:
            return False
        req = reqs[0]
        test = await LLMSynthesizer(llm, self.config).synthesize(req)
        result = Verifier(self.config).verify(req, test)
        if result.status == VerificationStatus.VERIFIED:
            Writer(self.config).write(test, req.id)
            return True
        return False
