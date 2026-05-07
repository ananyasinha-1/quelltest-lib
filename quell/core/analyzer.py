"""
Analyzes a SurvivedMutant to:
1. Classify its mutation operator
2. Extract context (enclosing function, existing tests, type hints)
"""
from __future__ import annotations
import ast
import libcst as cst
from pathlib import Path
from quell.core.models import SurvivedMutant, MutationOperator


# Operator classification rules based on diff between original and mutated code
BOUNDARY_OPS = {">", ">=", "<", "<="}
ARITHMETIC_OPS = {"+", "-", "*", "/", "//", "**", "%"}
LOGICAL_OPS = {"and", "or", "not"}
COMPARISON_OPS = {"==", "!=", "is", "is not", "in", "not in"}


class MutationAnalyzer:
    """
    Classifies mutation operator and extracts source context.

    Usage:
        analyzer = MutationAnalyzer()
        mutant = analyzer.analyze(mutant)
    """

    def analyze(self, mutant: SurvivedMutant) -> SurvivedMutant:
        """
        Enrich a SurvivedMutant with:
        - operator classification
        - enclosing function name and source
        - list of existing test names for this file

        Returns enriched mutant (does not mutate in place, returns new).
        """
        operator = self._classify_operator(mutant.original_code, mutant.mutated_code)
        function_name, function_source = self._extract_enclosing_function(
            mutant.file_path, mutant.line_start
        )
        test_file = self._find_test_file(mutant.file_path)
        existing_tests = self._extract_test_names(test_file) if test_file else []

        return mutant.model_copy(update={
            "operator": operator,
            "function_name": function_name,
            "function_source": function_source,
            "test_file_path": test_file,
            "existing_tests": existing_tests,
        })

    def _classify_operator(self, original: str, mutated: str) -> MutationOperator:
        """
        Compare original vs mutated code strings to classify the operator.

        Algorithm:
        1. Strip whitespace from both
        2. Find tokens that differ
        3. Match against known operator sets
        4. Fall back to UNKNOWN if no match
        """
        orig_tokens = set(original.split())
        mut_tokens = set(mutated.split())

        removed = orig_tokens - mut_tokens
        added = mut_tokens - orig_tokens

        # Check boundary shift: > → >= or >= → >
        if removed & BOUNDARY_OPS or added & BOUNDARY_OPS:
            return MutationOperator.BOUNDARY_SHIFT

        # Check arithmetic swap: + → -
        if removed & ARITHMETIC_OPS or added & ARITHMETIC_OPS:
            return MutationOperator.ARITHMETIC_SWAP

        # Check logical: and → or
        if removed & LOGICAL_OPS or added & LOGICAL_OPS:
            return MutationOperator.LOGICAL_SWAP

        # Check comparison flip: == → !=
        if removed & COMPARISON_OPS or added & COMPARISON_OPS:
            return MutationOperator.COMPARISON_FLIP

        # Check return mutation: "return None" added or value removed
        if "None" in added and "return" in mutated:
            return MutationOperator.RETURN_MUTATION

        # Check constant: integer or boolean literals changed
        for token in removed:
            if token.isdigit() or token in ("True", "False"):
                return MutationOperator.CONSTANT_MUTATION

        # Check string mutation: empty string appears
        if '""' in mutated or "''" in mutated:
            return MutationOperator.STRING_MUTATION

        # Check statement removal: mutated is empty or just "pass"
        if mutated.strip() in ("", "pass"):
            return MutationOperator.STATEMENT_REMOVAL

        return MutationOperator.UNKNOWN

    def _extract_enclosing_function(
        self, file_path: Path, line_number: int
    ) -> tuple[str | None, str | None]:
        """
        Use Python's built-in ast module to find which function contains line_number.
        Returns (function_name, full_function_source_code).
        """
        try:
            source = file_path.read_text()
            tree = ast.parse(source)
            lines = source.splitlines()

            best_func = None
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.lineno <= line_number <= node.end_lineno:
                        # Take the innermost matching function
                        if best_func is None or node.lineno > best_func.lineno:
                            best_func = node

            if best_func:
                func_lines = lines[best_func.lineno - 1 : best_func.end_lineno]
                return best_func.name, "\n".join(func_lines)
        except Exception:
            pass
        return None, None

    def _find_test_file(self, source_file: Path) -> Path | None:
        """
        Heuristically find the test file for a given source file.
        Tries multiple patterns:
        - tests/test_{filename}.py
        - test_{filename}.py (same dir)
        - tests/{filename}_test.py
        """
        stem = source_file.stem
        candidates = [
            source_file.parent.parent / "tests" / f"test_{stem}.py",
            source_file.parent / f"test_{stem}.py",
            source_file.parent.parent / "tests" / f"{stem}_test.py",
        ]
        for candidate in candidates:
            if candidate.exists():
                return candidate
        return None

    def _extract_test_names(self, test_file: Path) -> list[str]:
        """Parse test file and return list of all test function names."""
        try:
            tree = ast.parse(test_file.read_text())
            return [
                node.name
                for node in ast.walk(tree)
                if isinstance(node, ast.FunctionDef) and node.name.startswith("test_")
            ]
        except Exception:
            return []
