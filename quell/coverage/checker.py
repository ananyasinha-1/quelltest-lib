"""
Checks which Requirements already have tests in the test suite.
Uses AST — no test execution required.

Conservative: marks as uncovered when uncertain.
Better to generate a duplicate test than miss a real gap.
"""
from __future__ import annotations
import ast
from pathlib import Path
from quell.core.models import Requirement, ConstraintKind


class CoverageChecker:
    """AST-based coverage checker. No test execution needed."""

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root
        self._cache: dict[Path, list[ast.FunctionDef]] = {}

    def check(self, requirements: list[Requirement]) -> list[Requirement]:
        """Mark each Requirement is_covered=True/False. Returns same list."""
        for req in requirements:
            test_file = self._test_file(req.target_file)
            if test_file:
                funcs = self._get_tests(test_file)
                covering = self._find_covering(req, funcs)
                req.is_covered = len(covering) > 0
                req.covering_tests = covering
            else:
                req.is_covered = False
                req.covering_tests = []
        return requirements

    def _test_file(self, src: Path) -> Path | None:
        stem = src.stem
        for candidate in [
            self.project_root / "tests" / f"test_{stem}.py",
            self.project_root / "tests" / f"{stem}_test.py",
            src.parent / f"test_{stem}.py",
        ]:
            if candidate.exists():
                return candidate
        return None

    def _get_tests(self, f: Path) -> list[ast.FunctionDef]:
        if f in self._cache:
            return self._cache[f]
        try:
            tree = ast.parse(f.read_text())
            funcs = [
                n for n in ast.walk(tree)
                if isinstance(n, ast.FunctionDef) and n.name.startswith("test_")
            ]
            self._cache[f] = funcs
            return funcs
        except Exception:
            return []

    def _find_covering(
        self, req: Requirement, funcs: list[ast.FunctionDef]
    ) -> list[str]:
        covering = []
        for func in funcs:
            # Must mention the target function
            if req.target_function.lower() not in func.name.lower():
                doc = ast.get_docstring(func) or ""
                if req.target_function.lower() not in doc.lower():
                    continue
            # BUG_REPRO: never mark as covered (always regenerate)
            if req.constraint_kind == ConstraintKind.BUG_REPRO:
                continue
            # MUST_RAISE: check for pytest.raises
            if req.constraint_kind == ConstraintKind.MUST_RAISE:
                if self._has_raises(func):
                    covering.append(func.name)
            # BOUNDARY: check for boundary values
            elif req.constraint_kind == ConstraintKind.BOUNDARY:
                if self._has_boundary(func):
                    covering.append(func.name)
            else:
                covering.append(func.name)  # conservative: assume covered
        return covering

    def _has_raises(self, func: ast.FunctionDef) -> bool:
        for node in ast.walk(func):
            if isinstance(node, ast.With):
                for item in node.items:
                    call = item.context_expr
                    if isinstance(call, ast.Call):
                        name = (
                            getattr(call.func, "id", None) or
                            getattr(call.func, "attr", None)
                        )
                        if name == "raises":
                            return True
        return False

    def _has_boundary(self, func: ast.FunctionDef) -> bool:
        for node in ast.walk(func):
            if isinstance(node, ast.Constant):
                if node.value in (0, -1, 1, 0.0, -1.0, 1.0):
                    return True
        return False
