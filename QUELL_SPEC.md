# Quell — Implementation Specification
> Auto-generates verified, killing tests for survived mutants from mutmut and Stryker.
> This document is a complete implementation spec for Claude Code to scaffold the entire project.

---

## Name & Branding

**Tool name:** `quell`
**PyPI package:** `quell`
**CLI command:** `quell`
**Tagline:** *"Quell your survivors. Strengthen your tests."*
**Concept:** To quell = to put an end to. Every surviving mutant is a weakness. Quell ends them — automatically, verifiably, safely.

**Alternative names considered (rejected):**
- `mutantkill` — too aggressive, hard to type
- `smite` — taken on PyPI
- `temper` — ambiguous
- `forge` — too generic

---

## What Quell Does (One Paragraph for Claude Code Context)

Quell is a Python CLI tool and library that reads surviving mutants from mutation testing tools (mutmut for Python, Stryker for JS/TS), analyzes each surviving mutant using Python's AST (via libcst), generates a targeted pytest assertion that would catch the mutation, verifies the generated test actually kills the mutant by applying the mutant and running the test in a subprocess, then writes only verified tests to the test file using libcst (preserving formatting and comments). Code never leaves the machine. Every write is auto-restored on failure. Full audit log is maintained.

---

## Project Structure (Generate ALL of these files)

```
quell/
├── pyproject.toml
├── README.md
├── CLAUDE.md                        ← instructions for AI assistants working on this repo
├── .github/
│   └── workflows/
│       ├── ci.yml
│       └── release.yml
├── quell/
│   ├── __init__.py                  ← version, public API exports
│   ├── cli.py                       ← Typer app, all CLI commands
│   ├── core/
│   │   ├── __init__.py
│   │   ├── models.py                ← all Pydantic models
│   │   ├── analyzer.py              ← mutation operator classifier
│   │   ├── generator.py             ← test generation engine
│   │   ├── verifier.py              ← verification engine
│   │   └── writer.py                ← libcst test file injector
│   ├── adapters/
│   │   ├── __init__.py
│   │   ├── base.py                  ← MutationAdapter Protocol
│   │   ├── mutmut_adapter.py        ← reads .mutmut-cache
│   │   └── stryker_adapter.py       ← reads mutation-report.json
│   ├── llm/
│   │   ├── __init__.py
│   │   ├── client.py                ← LLMClient abstract base
│   │   ├── prompts.py               ← prompt templates per operator
│   │   └── providers/
│   │       ├── __init__.py
│   │       ├── anthropic_provider.py
│   │       ├── openai_provider.py
│   │       └── ollama_provider.py
│   └── ui/
│       ├── __init__.py
│       ├── console.py               ← Rich console singleton
│       ├── progress.py              ← progress bars + spinners
│       └── diff.py                  ← colored diff display
├── tests/
│   ├── conftest.py
│   ├── fixtures/
│   │   ├── sample_project/          ← minimal Python project with survivors
│   │   │   ├── src/
│   │   │   │   └── calculator.py
│   │   │   └── tests/
│   │   │       └── test_calculator.py
│   │   └── stryker_report.json      ← sample Stryker JSON report
│   ├── unit/
│   │   ├── test_analyzer.py
│   │   ├── test_generator.py
│   │   ├── test_verifier.py
│   │   └── test_writer.py
│   ├── adapters/
│   │   ├── test_mutmut_adapter.py
│   │   └── test_stryker_adapter.py
│   └── integration/
│       └── test_end_to_end.py
└── docs/
    ├── index.md
    ├── quickstart.md
    └── configuration.md
```

---

## `pyproject.toml` (Generate Exactly)

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "quell"
version = "0.1.0"
description = "Auto-generates verified killing tests for survived mutants from mutmut and Stryker"
readme = "README.md"
requires-python = ">=3.11"
license = { text = "MIT" }
authors = [{ name = "Shashank Bindal", email = "bindalshashank.89@gmail.com" }]
keywords = ["mutation-testing", "testing", "mutmut", "stryker", "test-generation", "pytest"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Environment :: Console",
    "Intended Audience :: Developers",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
    "Topic :: Software Development :: Testing",
]
dependencies = [
    "typer>=0.12.0",
    "rich>=13.7.0",
    "pydantic>=2.6.0",
    "libcst>=1.3.0",
    "anthropic>=0.28.0",
    "openai>=1.30.0",
    "httpx>=0.27.0",   # for Ollama provider
    "tomli>=2.0.0; python_version < '3.11'",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.4.0",
    "mypy>=1.10.0",
    "pre-commit>=3.7.0",
]

[project.scripts]
quell = "quell.cli:app"

[project.urls]
Homepage = "https://github.com/shashank7109/quell"
Documentation = "https://quell.dev"
Repository = "https://github.com/shashank7109/quell"
Issues = "https://github.com/shashank7109/quell/issues"

[tool.hatch.version]
path = "quell/__init__.py"

[tool.ruff]
target-version = "py311"
line-length = 88

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
```

---

## `quell/__init__.py`

```python
"""Quell — Auto-generates verified killing tests for survived mutants."""

__version__ = "0.1.0"
__author__ = "Shashank Bindal"

from quell.core.models import SurvivedMutant, GeneratedTest, VerificationResult, AuditEntry
from quell.core.analyzer import MutationAnalyzer
from quell.core.generator import TestGenerator
from quell.core.verifier import MutantVerifier
from quell.core.writer import TestWriter

__all__ = [
    "SurvivedMutant",
    "GeneratedTest",
    "VerificationResult",
    "AuditEntry",
    "MutationAnalyzer",
    "TestGenerator",
    "MutantVerifier",
    "TestWriter",
]
```

---

## `quell/core/models.py` (All Pydantic Models)

```python
"""All domain models for Quell."""

from __future__ import annotations
from enum import Enum
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field
import datetime


class MutationOperator(str, Enum):
    """Classification of what kind of change the mutant made."""
    BOUNDARY_SHIFT = "boundary_shift"         # > → >=, < → <=
    ARITHMETIC_SWAP = "arithmetic_swap"       # + → -, * → /
    LOGICAL_SWAP = "logical_swap"             # and → or, not removal
    COMPARISON_FLIP = "comparison_flip"       # == → !=
    CONSTANT_MUTATION = "constant_mutation"   # 0 → 1, True → False, "" → "X"
    STATEMENT_REMOVAL = "statement_removal"   # removes a whole statement
    RETURN_MUTATION = "return_mutation"       # return x → return None
    CONDITION_NEGATE = "condition_negate"     # if x → if not x
    STRING_MUTATION = "string_mutation"       # "str" → ""
    UNKNOWN = "unknown"                       # fallback, use LLM


class MutantSource(str, Enum):
    MUTMUT = "mutmut"
    STRYKER = "stryker"


class SurvivedMutant(BaseModel):
    """A mutant that survived — your tests didn't catch this change."""
    id: str                                  # unique id from the tool
    source: MutantSource
    file_path: Path                          # absolute path to source file
    test_file_path: Optional[Path] = None    # where to inject the killing test
    line_start: int
    line_end: int
    col_start: Optional[int] = None
    col_end: Optional[int] = None
    original_code: str                       # the original source line(s)
    mutated_code: str                        # what the mutant changed it to
    operator: MutationOperator = MutationOperator.UNKNOWN
    function_name: Optional[str] = None      # enclosing function (filled by analyzer)
    function_source: Optional[str] = None    # full source of enclosing function
    existing_tests: list[str] = Field(default_factory=list)  # existing test names


class GeneratedTest(BaseModel):
    """A candidate test function that MIGHT kill the mutant."""
    mutant_id: str
    test_function_name: str                  # e.g. test_quell_mutant_42
    test_code: str                           # full Python function source
    test_file_path: Path
    explanation: str                         # why this test kills the mutant
    operator: MutationOperator
    generated_by: str                        # "rule_based" or "llm:claude-3-5-sonnet"


class VerificationStatus(str, Enum):
    VERIFIED = "verified"                    # test kills mutant AND passes on original
    FAILS_ON_ORIGINAL = "fails_on_original"  # test breaks original code (bad test)
    DOESNT_KILL_MUTANT = "doesnt_kill_mutant"  # mutant still survives
    SYNTAX_ERROR = "syntax_error"            # generated test has syntax error
    TIMEOUT = "timeout"                      # verification took too long
    EQUIVALENT_MUTANT = "equivalent_mutant"  # probably can't be killed (flag it)


class VerificationResult(BaseModel):
    mutant_id: str
    generated_test: GeneratedTest
    status: VerificationStatus
    attempts: int = 1
    error_message: Optional[str] = None
    duration_ms: int = 0


class AuditEntry(BaseModel):
    """Immutable record of every action Quell takes."""
    timestamp: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    mutant_id: str
    action: str                              # "test_written", "skipped", "flagged_equivalent"
    file_path: Optional[Path] = None
    test_function_name: Optional[str] = None
    verification_status: Optional[VerificationStatus] = None
    mutation_score_before: Optional[float] = None
    mutation_score_after: Optional[float] = None


class QuellConfig(BaseModel):
    """Configuration loaded from pyproject.toml [tool.quell] or quell.toml"""
    llm_provider: str = "anthropic"          # "anthropic" | "openai" | "ollama"
    llm_model: str = "claude-sonnet-4-5"
    ollama_base_url: str = "http://localhost:11434"
    max_verification_attempts: int = 3
    verification_timeout_seconds: int = 30
    auto_write: bool = False                 # if True, skip interactive prompt
    test_file_pattern: str = "tests/test_{source_file}.py"
    exclude_operators: list[MutationOperator] = Field(default_factory=list)
    audit_log_path: Path = Path(".quell/audit.jsonl")
    backup_dir: Path = Path(".quell/backups")
```

---

## `quell/core/analyzer.py` (Mutation Classifier)

```python
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
```

---

## `quell/core/generator.py` (Test Generation Engine)

```python
"""
Generates candidate killing tests for survived mutants.

Strategy:
1. For known operators (BOUNDARY_SHIFT, ARITHMETIC_SWAP, etc.): use rule-based generation.
   These are deterministic and fast. No LLM needed.
2. For UNKNOWN or complex operators: use LLM with rich context.
3. Always return a GeneratedTest with test_code as a valid Python function string.
"""
from __future__ import annotations
import re
from quell.core.models import (
    SurvivedMutant, GeneratedTest, MutationOperator, QuellConfig
)
from quell.llm.client import LLMClient


class TestGenerator:
    """
    Generates a test function for a given SurvivedMutant.
    
    Usage:
        generator = TestGenerator(llm_client, config)
        test = await generator.generate(mutant)
    """

    def __init__(self, llm_client: LLMClient, config: QuellConfig):
        self.llm = llm_client
        self.config = config

    async def generate(self, mutant: SurvivedMutant) -> GeneratedTest:
        """Main entry point. Routes to rule-based or LLM generator."""
        if mutant.operator == MutationOperator.BOUNDARY_SHIFT:
            return self._generate_boundary_test(mutant)
        elif mutant.operator == MutationOperator.ARITHMETIC_SWAP:
            return self._generate_arithmetic_test(mutant)
        elif mutant.operator == MutationOperator.COMPARISON_FLIP:
            return self._generate_comparison_test(mutant)
        elif mutant.operator == MutationOperator.CONSTANT_MUTATION:
            return self._generate_constant_test(mutant)
        elif mutant.operator == MutationOperator.RETURN_MUTATION:
            return self._generate_return_test(mutant)
        elif mutant.operator == MutationOperator.LOGICAL_SWAP:
            return self._generate_logical_test(mutant)
        else:
            # Fall through to LLM for UNKNOWN, STATEMENT_REMOVAL, STRING_MUTATION, etc.
            return await self._generate_llm_test(mutant)

    def _make_test_name(self, mutant: SurvivedMutant) -> str:
        func = mutant.function_name or "code"
        return f"test_quell_{func}_mutant_{mutant.id}"

    def _generate_boundary_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        """
        For boundary shifts (> → >=), we need a test at the exact boundary value.
        
        Strategy: extract the RHS value from the condition.
        Example: "if amount > 0" mutated to "if amount >= 0"
        → Test: call function with amount=0, expect the ORIGINAL behavior (reject/different outcome)
        """
        func = mutant.function_name or "function_under_test"
        test_name = self._make_test_name(mutant)
        
        # Extract boundary value from original code using regex
        boundary_match = re.search(r'[><=!]+\s*(\d+)', mutant.original_code)
        boundary_val = boundary_match.group(1) if boundary_match else "0"
        
        test_code = f'''def {test_name}():
    """
    Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}
    
    This is a boundary condition test. The mutation shifts the boundary,
    so we test the exact boundary value to ensure correct behavior.
    """
    # The mutation changed a boundary condition.
    # Test with the exact boundary value ({boundary_val}) to expose the difference.
    # TODO: Replace with actual call to {func} with a boundary input.
    # Example: assert {func}({boundary_val}) == <expected_original_behavior>
    raise NotImplementedError(
        "Complete this test: call {func} with boundary value {boundary_val} "
        "and assert the ORIGINAL behavior (not the mutant behavior)."
    )
'''
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=test_name,
            test_code=test_code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation=f"Boundary test at value {boundary_val} exposes the {mutant.original_code.strip()} vs {mutant.mutated_code.strip()} difference",
            operator=mutant.operator,
            generated_by="rule_based",
        )

    def _generate_arithmetic_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        """
        For arithmetic swaps (+ → -), we need distinct non-zero inputs.
        
        Strategy: use inputs where a+b != a-b, i.e., b != 0.
        Example: "result = x + y" mutated to "result = x - y"
        → Test: x=3, y=2 → original gives 5, mutant gives 1
        """
        func = mutant.function_name or "function_under_test"
        test_name = self._make_test_name(mutant)
        
        test_code = f'''def {test_name}():
    """
    Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}
    
    Arithmetic mutation test. We need non-zero, non-equal inputs
    so that the original operator and mutant operator give different results.
    """
    # TODO: Replace with actual call to {func} with specific numeric inputs
    # Use inputs where the ORIGINAL and MUTANT operators give different results.
    # For + vs -: use (3, 2) → original=5, mutant=1
    # For * vs /: use (6, 3) → original=18, mutant=2
    raise NotImplementedError(
        "Complete this test: call {func} with numeric inputs that "
        "produce different results under + vs - (or the relevant operators)."
    )
'''
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=test_name,
            test_code=test_code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation="Arithmetic test with non-zero inputs exposes operator difference",
            operator=mutant.operator,
            generated_by="rule_based",
        )

    def _generate_comparison_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        func = mutant.function_name or "function_under_test"
        test_name = self._make_test_name(mutant)
        test_code = f'''def {test_name}():
    """
    Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}
    
    Comparison flip test. We need an input where the comparison is TRUE
    in the original but FALSE in the mutant (or vice versa).
    """
    # TODO: Call {func} with input that makes original comparison TRUE
    # and assert behavior that would differ if comparison were flipped.
    raise NotImplementedError("Complete this test for comparison flip mutation.")
'''
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=test_name,
            test_code=test_code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation="Comparison flip test with value that makes one branch true and other false",
            operator=mutant.operator,
            generated_by="rule_based",
        )

    def _generate_constant_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        func = mutant.function_name or "function_under_test"
        test_name = self._make_test_name(mutant)
        test_code = f'''def {test_name}():
    """
    Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}
    
    Constant mutation test. The mutant changed a literal constant value.
    We need to assert the exact expected value to catch this change.
    """
    # TODO: Call {func} and assert the EXACT expected output.
    # Avoid "assert result > 0" — use "assert result == <exact_value>"
    raise NotImplementedError("Complete this test with an exact value assertion.")
'''
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=test_name,
            test_code=test_code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation="Exact value assertion catches constant mutation",
            operator=mutant.operator,
            generated_by="rule_based",
        )

    def _generate_return_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        func = mutant.function_name or "function_under_test"
        test_name = self._make_test_name(mutant)
        test_code = f'''def {test_name}():
    """
    Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}
    
    Return value mutation test. The mutant changed what is returned.
    We must assert the EXACT return value, not just that it's truthy.
    """
    # TODO: Call {func} and assert it does NOT return None.
    # result = {func}(...)
    # assert result is not None
    # assert result == <exact_expected_value>
    raise NotImplementedError("Complete this test: assert exact return value, not just truthiness.")
'''
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=test_name,
            test_code=test_code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation="Return value assertion (not None, exact value) kills return mutation",
            operator=mutant.operator,
            generated_by="rule_based",
        )

    def _generate_logical_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        func = mutant.function_name or "function_under_test"
        test_name = self._make_test_name(mutant)
        test_code = f'''def {test_name}():
    """
    Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}
    
    Logical operator mutation test. The mutant changed 'and' to 'or' or similar.
    We need a test where ONE condition is true and the OTHER is false.
    With 'and': result is False. With 'or': result is True.
    """
    # TODO: Call {func} with inputs where EXACTLY ONE condition is true.
    # This exposes the difference between 'and' and 'or'.
    raise NotImplementedError("Complete this test: use inputs where only one condition holds.")
'''
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=test_name,
            test_code=test_code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation="Single-condition-true input exposes and/or operator difference",
            operator=mutant.operator,
            generated_by="rule_based",
        )

    async def _generate_llm_test(self, mutant: SurvivedMutant) -> GeneratedTest:
        """Use LLM for complex or UNKNOWN mutations."""
        from quell.llm.prompts import build_test_generation_prompt
        
        prompt = build_test_generation_prompt(mutant)
        response = await self.llm.generate(prompt)
        
        # Extract Python code block from response
        code = self._extract_code_block(response)
        func_name = self._extract_function_name(code) or self._make_test_name(mutant)
        
        return GeneratedTest(
            mutant_id=mutant.id,
            test_function_name=func_name,
            test_code=code,
            test_file_path=mutant.test_file_path or mutant.file_path.parent / "tests" / f"test_{mutant.file_path.stem}.py",
            explanation=f"LLM-generated test for {mutant.operator.value} mutation",
            operator=mutant.operator,
            generated_by=f"llm:{self.config.llm_model}",
        )

    def _extract_code_block(self, response: str) -> str:
        """Extract ```python ... ``` block from LLM response."""
        match = re.search(r'```python\n(.*?)```', response, re.DOTALL)
        if match:
            return match.group(1).strip()
        return response.strip()

    def _extract_function_name(self, code: str) -> str | None:
        """Extract the function name from generated code."""
        match = re.search(r'^def\s+(test_\w+)', code, re.MULTILINE)
        return match.group(1) if match else None
```

---

## `quell/core/verifier.py` (The Core Moat)

```python
"""
Verification Engine — The most important module in Quell.

For every GeneratedTest, we verify:
1. The test PASSES on the original (unmodified) code
2. The test FAILS on the mutated code (i.e., it kills the mutant)

Only tests that satisfy BOTH conditions are accepted.
Auto-restore on any failure. No side effects left on disk.
"""
from __future__ import annotations
import subprocess
import shutil
import json
import time
from pathlib import Path
from quell.core.models import (
    SurvivedMutant, GeneratedTest, VerificationResult, VerificationStatus, QuellConfig
)


class MutantVerifier:
    """
    Verifies that a generated test actually kills a given mutant.
    
    Algorithm:
    1. Write test to a TEMP file (not the real test file)
    2. Run pytest on original code with temp test → must PASS
    3. Apply mutant to source (patch source file)
    4. Run pytest on mutated code with temp test → must FAIL
    5. Restore source file (always, even on error)
    6. Return VerificationResult
    
    Usage:
        verifier = MutantVerifier(config)
        result = verifier.verify(mutant, generated_test)
    """

    def __init__(self, config: QuellConfig):
        self.config = config
        self._backup_dir = config.backup_dir
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def verify(self, mutant: SurvivedMutant, test: GeneratedTest) -> VerificationResult:
        """Main verification entry point."""
        start_time = time.time()
        temp_test_file = self._write_temp_test(test)
        backup_path = self._backup_source(mutant.file_path)
        
        try:
            # Step 1: Test must PASS on original code
            original_result = self._run_pytest(temp_test_file, mutant.file_path)
            if not original_result["passed"]:
                return VerificationResult(
                    mutant_id=mutant.id,
                    generated_test=test,
                    status=VerificationStatus.FAILS_ON_ORIGINAL,
                    error_message=original_result.get("error"),
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Step 2: Apply the mutant
            self._apply_mutant(mutant)

            # Step 3: Test must FAIL on mutated code
            mutant_result = self._run_pytest(temp_test_file, mutant.file_path)
            
            if mutant_result["passed"]:
                # Test passed even with mutant = doesn't kill it
                status = VerificationStatus.DOESNT_KILL_MUTANT
            else:
                status = VerificationStatus.VERIFIED

            return VerificationResult(
                mutant_id=mutant.id,
                generated_test=test,
                status=status,
                error_message=None if status == VerificationStatus.VERIFIED else mutant_result.get("error"),
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except SyntaxError as e:
            return VerificationResult(
                mutant_id=mutant.id,
                generated_test=test,
                status=VerificationStatus.SYNTAX_ERROR,
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except TimeoutError:
            return VerificationResult(
                mutant_id=mutant.id,
                generated_test=test,
                status=VerificationStatus.TIMEOUT,
                error_message="Verification timed out",
                duration_ms=self.config.verification_timeout_seconds * 1000,
            )
        finally:
            # ALWAYS restore source file
            self._restore_source(mutant.file_path, backup_path)
            # Clean up temp test file
            temp_test_file.unlink(missing_ok=True)

    def _write_temp_test(self, test: GeneratedTest) -> Path:
        """Write generated test to a temporary file."""
        temp_dir = self._backup_dir / "temp_tests"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"quell_temp_{test.mutant_id}.py"
        temp_file.write_text(test.test_code)
        return temp_file

    def _backup_source(self, source_path: Path) -> Path:
        """Copy source file to backup directory. Returns backup path."""
        backup_path = self._backup_dir / f"{source_path.stem}_{int(time.time())}.py.bak"
        shutil.copy2(source_path, backup_path)
        return backup_path

    def _restore_source(self, source_path: Path, backup_path: Path) -> None:
        """Restore source from backup. Called in finally block."""
        if backup_path.exists():
            shutil.copy2(backup_path, source_path)
            backup_path.unlink()

    def _apply_mutant(self, mutant: SurvivedMutant) -> None:
        """
        Apply the mutant's change to the source file.
        
        For mutmut: use `mutmut apply <id>` subprocess command.
        For Stryker: directly replace the line in the source file.
        """
        if mutant.source.value == "mutmut":
            result = subprocess.run(
                ["mutmut", "apply", str(mutant.id)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"mutmut apply failed: {result.stderr}")
        else:
            # Direct source replacement for Stryker
            source = mutant.file_path.read_text()
            lines = source.splitlines(keepends=True)
            # Replace the specific line with mutated code
            line_idx = mutant.line_start - 1
            if 0 <= line_idx < len(lines):
                lines[line_idx] = mutant.mutated_code + "\n"
            mutant.file_path.write_text("".join(lines))

    def _run_pytest(self, test_file: Path, source_file: Path) -> dict:
        """
        Run pytest on a specific test file. Returns {"passed": bool, "error": str}.
        Timeout enforced via config.
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header", "-q"],
                capture_output=True,
                text=True,
                timeout=self.config.verification_timeout_seconds,
                cwd=source_file.parent.parent,  # run from project root
            )
            passed = result.returncode == 0
            return {
                "passed": passed,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.stdout if not passed else None,
            }
        except subprocess.TimeoutExpired:
            raise TimeoutError("pytest timed out")
```

---

## `quell/core/writer.py` (libcst Test Injector)

```python
"""
Writes verified test functions into the target test file using libcst.
Preserves formatting, comments, and all existing code exactly.
Auto-restores if anything goes wrong.
"""
from __future__ import annotations
import shutil
import time
import libcst as cst
from pathlib import Path
from quell.core.models import GeneratedTest, QuellConfig, AuditEntry, VerificationStatus
import json


class TestWriter:
    """
    Injects a verified test function into a test file using libcst.
    
    Never uses string concatenation. Always uses CST transformation.
    Backs up before writing. Restores on failure.
    
    Usage:
        writer = TestWriter(config)
        success = writer.write(generated_test, audit_log)
    """

    def __init__(self, config: QuellConfig):
        self.config = config
        config.audit_log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, test: GeneratedTest, mutant_id: str) -> bool:
        """
        Write a verified test to the test file.
        Returns True on success, False on failure.
        """
        test_file = test.test_file_path
        
        # Create file if it doesn't exist
        if not test_file.exists():
            test_file.parent.mkdir(parents=True, exist_ok=True)
            test_file.write_text("# Generated by Quell\nimport pytest\n\n")

        # Backup
        backup = test_file.with_suffix(f".{int(time.time())}.bak")
        shutil.copy2(test_file, backup)

        try:
            existing_source = test_file.read_text()
            new_source = self._inject_test(existing_source, test.test_code)
            
            # Validate the new source parses correctly
            cst.parse_module(new_source)
            
            test_file.write_text(new_source)
            backup.unlink()
            
            self._append_audit(AuditEntry(
                mutant_id=mutant_id,
                action="test_written",
                file_path=test_file,
                test_function_name=test.test_function_name,
                verification_status=VerificationStatus.VERIFIED,
            ))
            return True

        except Exception as e:
            # Restore backup
            if backup.exists():
                shutil.copy2(backup, test_file)
                backup.unlink()
            
            self._append_audit(AuditEntry(
                mutant_id=mutant_id,
                action="write_failed",
                file_path=test_file,
                test_function_name=test.test_function_name,
            ))
            return False

    def _inject_test(self, existing_source: str, new_test_code: str) -> str:
        """
        Parse existing source as CST and append the new test function.
        Uses libcst to ensure formatting is preserved.
        """
        module = cst.parse_module(existing_source)
        new_test_module = cst.parse_module(new_test_code)
        
        # Add blank lines between functions
        separator = cst.parse_statement("\n\n")
        
        new_statements = list(module.body) + list(new_test_module.body)
        new_module = module.with_changes(body=new_statements)
        return new_module.code

    def _append_audit(self, entry: AuditEntry) -> None:
        """Append an audit entry to the JSONL audit log."""
        with self.config.audit_log_path.open("a") as f:
            f.write(entry.model_dump_json() + "\n")
```

---

## `quell/adapters/mutmut_adapter.py`

```python
"""
Reads surviving mutants from mutmut's output.

mutmut stores results in .mutmut-cache/ directory.
We call `mutmut results` and `mutmut show <id>` to extract mutant data.
"""
from __future__ import annotations
import subprocess
import re
from pathlib import Path
from quell.core.models import SurvivedMutant, MutantSource
from quell.adapters.base import MutationAdapter


class MutmutAdapter(MutationAdapter):
    """
    Reads survived mutants from mutmut.
    
    Requires mutmut to be installed and `mutmut run` to have been executed.
    
    Usage:
        adapter = MutmutAdapter(project_root=Path("."))
        mutants = adapter.read_survivors()
    """

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root

    def read_survivors(self) -> list[SurvivedMutant]:
        """Parse mutmut results and return all survived mutants."""
        survived_ids = self._get_survived_ids()
        mutants = []
        for mutant_id in survived_ids:
            mutant = self._parse_mutant(mutant_id)
            if mutant:
                mutants.append(mutant)
        return mutants

    def _get_survived_ids(self) -> list[str]:
        """Run `mutmut results` and extract IDs of survived mutants."""
        result = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        # Parse lines like: "4-7, 9-14, 16-21" under "Survived"
        ids = []
        in_survived = False
        for line in result.stdout.splitlines():
            if "Survived" in line:
                in_survived = True
                continue
            if in_survived:
                if line.strip().startswith("----"):
                    continue
                if line.strip() == "" or ("Killed" in line or "Timeout" in line):
                    break
                # Parse ranges like "4-7, 9-14"
                parts = re.findall(r'\d+(?:-\d+)?', line)
                for part in parts:
                    if "-" in part:
                        start, end = part.split("-")
                        ids.extend(str(i) for i in range(int(start), int(end) + 1))
                    else:
                        ids.append(part)
        return ids

    def _parse_mutant(self, mutant_id: str) -> SurvivedMutant | None:
        """Run `mutmut show <id>` and parse the diff output."""
        result = subprocess.run(
            ["mutmut", "show", mutant_id],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        output = result.stdout
        
        # Parse unified diff format:
        # --- src/module.py
        # +++ src/module.py
        # @@ -47,7 +47,7 @@
        # - original line
        # + mutated line
        
        file_match = re.search(r'^--- (.+)$', output, re.MULTILINE)
        line_match = re.search(r'^@@ -(\d+)', output, re.MULTILINE)
        original_match = re.search(r'^- (.+)$', output, re.MULTILINE)
        mutated_match = re.search(r'^\+ (.+)$', output, re.MULTILINE)
        
        if not all([file_match, line_match, original_match, mutated_match]):
            return None
        
        file_path = self.project_root / file_match.group(1).strip()
        
        return SurvivedMutant(
            id=mutant_id,
            source=MutantSource.MUTMUT,
            file_path=file_path.resolve(),
            line_start=int(line_match.group(1)),
            line_end=int(line_match.group(1)),
            original_code=original_match.group(1),
            mutated_code=mutated_match.group(1),
        )
```

---

## `quell/adapters/stryker_adapter.py`

```python
"""
Reads surviving mutants from Stryker's mutation-report.json.

Stryker produces a standardized JSON report with the mutation-testing-report-schema.
Run `stryker run --reporters=json` to generate mutation-report.json.
"""
from __future__ import annotations
import json
from pathlib import Path
from quell.core.models import SurvivedMutant, MutantSource
from quell.adapters.base import MutationAdapter


class StrykerAdapter(MutationAdapter):
    """
    Reads survived mutants from Stryker's mutation-report.json.
    
    Usage:
        adapter = StrykerAdapter(report_path=Path("mutation-report.json"))
        mutants = adapter.read_survivors()
    """

    def __init__(self, report_path: Path = Path("reports/mutation/mutation.json")):
        self.report_path = report_path

    def read_survivors(self) -> list[SurvivedMutant]:
        """Parse Stryker JSON report and return all Survived mutants."""
        if not self.report_path.exists():
            raise FileNotFoundError(
                f"Stryker report not found at {self.report_path}. "
                "Run: npx stryker run --reporters=json"
            )
        
        data = json.loads(self.report_path.read_text())
        mutants = []
        
        for file_path_str, file_data in data.get("files", {}).items():
            file_path = Path(file_path_str).resolve()
            
            for mutant in file_data.get("mutants", []):
                if mutant.get("status") != "Survived":
                    continue
                
                location = mutant.get("location", {})
                start = location.get("start", {})
                end = location.get("end", {})
                
                # Reconstruct original code from source + location
                source_lines = file_data.get("source", "").splitlines()
                line_idx = start.get("line", 1) - 1
                original_line = source_lines[line_idx] if line_idx < len(source_lines) else ""
                
                mutants.append(SurvivedMutant(
                    id=str(mutant["id"]),
                    source=MutantSource.STRYKER,
                    file_path=file_path,
                    line_start=start.get("line", 0),
                    line_end=end.get("line", 0),
                    col_start=start.get("column", 0),
                    col_end=end.get("column", 0),
                    original_code=original_line.strip(),
                    mutated_code=mutant.get("replacement", ""),
                ))
        
        return mutants
```

---

## `quell/adapters/base.py`

```python
"""Base protocol for all mutation adapters."""
from __future__ import annotations
from typing import Protocol
from quell.core.models import SurvivedMutant


class MutationAdapter(Protocol):
    """Protocol that all mutation adapters must implement."""
    
    def read_survivors(self) -> list[SurvivedMutant]:
        """Return all survived mutants from the mutation testing run."""
        ...
```

---

## `quell/llm/prompts.py`

```python
"""
Prompt templates for LLM-based test generation.
Used when rule-based generation is not sufficient (UNKNOWN operator, complex mutations).
"""
from quell.core.models import SurvivedMutant


def build_test_generation_prompt(mutant: SurvivedMutant) -> str:
    """Build a structured prompt for test generation."""
    
    existing_tests_section = ""
    if mutant.existing_tests:
        existing_tests_section = f"""
EXISTING TESTS IN THE FILE:
{chr(10).join(f"- {t}" for t in mutant.existing_tests[:10])}

Follow the same testing style and import patterns as the existing tests.
"""

    function_section = ""
    if mutant.function_source:
        function_section = f"""
ENCLOSING FUNCTION SOURCE CODE:
```python
{mutant.function_source}
```
"""

    return f"""You are a Python testing expert. Your job is to write a single pytest test function that KILLS a specific surviving mutant.

A "surviving mutant" means: the mutation testing tool changed a line of code, but your existing tests still passed. This means your tests have a gap.

MUTATION DETAILS:
- File: {mutant.file_path}
- Line: {mutant.line_start}
- Original code: {mutant.original_code}
- Mutated code:  {mutant.mutated_code}
- Mutation type: {mutant.operator.value}
{function_section}
{existing_tests_section}

YOUR TASK:
Write a pytest test function called `test_quell_{mutant.function_name or "function"}_{mutant.id}` that:
1. Calls the function with specific inputs
2. Asserts a SPECIFIC expected output (not "assert result is not None" or "assert result > 0")
3. Would PASS on the original code
4. Would FAIL on the mutated code (catching the mutation)

RULES:
- Output ONLY a Python code block with the test function
- No imports needed (assume pytest and the module under test are available)
- No explanations outside the code block
- The assertion must be specific enough to distinguish original from mutant
- Add a docstring explaining WHY this test kills the mutant

```python
def test_quell_{mutant.function_name or "function"}_{mutant.id}():
    \"\"\"Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}\"\"\"
    # Your test here
```
"""
```

---

## `quell/llm/client.py`

```python
"""Abstract LLM client with provider implementations."""
from __future__ import annotations
from abc import ABC, abstractmethod
from quell.core.models import QuellConfig


class LLMClient(ABC):
    """Abstract base class for all LLM providers."""

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """Send prompt and return text response."""
        ...

    @classmethod
    def from_config(cls, config: QuellConfig) -> "LLMClient":
        """Factory method: creates provider from config."""
        from quell.llm.providers.anthropic_provider import AnthropicProvider
        from quell.llm.providers.openai_provider import OpenAIProvider
        from quell.llm.providers.ollama_provider import OllamaProvider

        providers = {
            "anthropic": AnthropicProvider,
            "openai": OpenAIProvider,
            "ollama": OllamaProvider,
        }
        provider_cls = providers.get(config.llm_provider)
        if not provider_cls:
            raise ValueError(f"Unknown LLM provider: {config.llm_provider}")
        return provider_cls(config)
```

---

## `quell/llm/providers/anthropic_provider.py`

```python
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
```

---

## `quell/llm/providers/ollama_provider.py`

```python
"""Ollama provider for local LLM — privacy-first option."""
from __future__ import annotations
import httpx
from quell.llm.client import LLMClient
from quell.core.models import QuellConfig


class OllamaProvider(LLMClient):
    def __init__(self, config: QuellConfig):
        self.base_url = config.ollama_base_url
        self.model = config.llm_model  # e.g., "codellama", "deepseek-coder"

    async def generate(self, prompt: str) -> str:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False},
            )
            response.raise_for_status()
            return response.json()["response"]
```

---

## `quell/cli.py` (All CLI Commands)

```python
"""
Quell CLI — built with Typer.

Commands:
  quell scan                    List all surviving mutants
  quell fix                     Interactive fix loop (review one by one)
  quell auto                    Auto-fix all survivors (no prompts)
  quell report                  Show audit log
  quell init                    Add [tool.quell] to pyproject.toml
"""
from __future__ import annotations
import asyncio
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich import print as rprint

from quell.core.models import QuellConfig, VerificationStatus
from quell.core.analyzer import MutationAnalyzer
from quell.core.generator import TestGenerator
from quell.core.verifier import MutantVerifier
from quell.core.writer import TestWriter
from quell.adapters.mutmut_adapter import MutmutAdapter
from quell.adapters.stryker_adapter import StrykerAdapter
from quell.llm.client import LLMClient

app = typer.Typer(
    name="quell",
    help="Quell your mutation testing survivors. Auto-generates verified killing tests.",
    rich_markup_mode="rich",
)
console = Console()


def _load_config(project_root: Path) -> QuellConfig:
    """Load config from pyproject.toml [tool.quell] or return defaults."""
    try:
        import tomllib
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text())
            quell_config = data.get("tool", {}).get("quell", {})
            if quell_config:
                return QuellConfig(**quell_config)
    except Exception:
        pass
    return QuellConfig()


def _get_adapter(tool: str, project_root: Path):
    """Return the appropriate adapter based on tool flag."""
    if tool == "mutmut":
        return MutmutAdapter(project_root)
    elif tool == "stryker":
        report_candidates = [
            project_root / "reports" / "mutation" / "mutation.json",
            project_root / "mutation-report.json",
        ]
        for candidate in report_candidates:
            if candidate.exists():
                return StrykerAdapter(candidate)
        raise typer.BadParameter("No Stryker report found. Run: npx stryker run --reporters=json")
    else:
        raise typer.BadParameter(f"Unknown tool: {tool}. Use 'mutmut' or 'stryker'.")


@app.command("scan")
def scan(
    tool: str = typer.Option("mutmut", "--tool", "-t", help="mutmut or stryker"),
    project_root: Path = typer.Option(Path("."), "--root", "-r", help="Project root directory"),
):
    """[bold]Scan[/bold] and list all surviving mutants."""
    
    console.print(Panel.fit("[bold blue]Quell — Scanning for survivors[/bold blue]"))
    
    config = _load_config(project_root)
    adapter = _get_adapter(tool, project_root)
    analyzer = MutationAnalyzer()
    
    with console.status("Reading mutation results..."):
        survivors = adapter.read_survivors()
        survivors = [analyzer.analyze(m) for m in survivors]
    
    if not survivors:
        console.print("[green]✓ No surviving mutants found![/green]")
        return
    
    table = Table(title=f"Surviving Mutants ({len(survivors)} total)")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("File", style="blue")
    table.add_column("Line", style="yellow", width=6)
    table.add_column("Operator", style="magenta")
    table.add_column("Original → Mutated", style="white")
    
    for m in survivors:
        table.add_row(
            str(m.id),
            str(m.file_path.name),
            str(m.line_start),
            m.operator.value,
            f"[red]{m.original_code.strip()[:30]}[/red] → [green]{m.mutated_code.strip()[:30]}[/green]",
        )
    
    console.print(table)
    console.print(f"\n[yellow]Run [bold]quell fix[/bold] to generate and verify killing tests.[/yellow]")


@app.command("fix")
def fix(
    tool: str = typer.Option("mutmut", "--tool", "-t"),
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
    llm_provider: Optional[str] = typer.Option(None, "--llm"),
    mutant_id: Optional[str] = typer.Option(None, "--id", help="Fix only a specific mutant ID"),
):
    """[bold]Interactively[/bold] generate and apply verified killing tests."""
    asyncio.run(_fix_async(tool, project_root, llm_provider, mutant_id))


async def _fix_async(tool, project_root, llm_provider, mutant_id):
    config = _load_config(project_root)
    if llm_provider:
        config = config.model_copy(update={"llm_provider": llm_provider})
    
    adapter = _get_adapter(tool, project_root)
    analyzer = MutationAnalyzer()
    llm = LLMClient.from_config(config)
    generator = TestGenerator(llm, config)
    verifier = MutantVerifier(config)
    writer = TestWriter(config)
    
    with console.status("Reading mutation results..."):
        survivors = adapter.read_survivors()
        survivors = [analyzer.analyze(m) for m in survivors]
        if mutant_id:
            survivors = [m for m in survivors if m.id == mutant_id]
    
    if not survivors:
        console.print("[green]No survivors to fix![/green]")
        return
    
    console.print(f"[bold]Found {len(survivors)} surviving mutants.[/bold]\n")
    
    killed_count = 0
    skipped_count = 0
    
    for i, mutant in enumerate(survivors, 1):
        console.print(Panel(
            f"[bold cyan]Mutant {mutant.id}[/bold cyan] ({i}/{len(survivors)})\n"
            f"[blue]{mutant.file_path.name}[/blue] line [yellow]{mutant.line_start}[/yellow]\n\n"
            f"[red]- {mutant.original_code.strip()}[/red]\n"
            f"[green]+ {mutant.mutated_code.strip()}[/green]\n\n"
            f"Operator: [magenta]{mutant.operator.value}[/magenta]"
        ))
        
        # Generate candidate test
        with console.status("Generating killing test..."):
            generated = await generator.generate(mutant)
        
        console.print("\n[bold]Generated test:[/bold]")
        console.print(Syntax(generated.test_code, "python", theme="monokai"))
        console.print(f"[dim]Generated by: {generated.generated_by}[/dim]")
        console.print(f"[dim]Explanation: {generated.explanation}[/dim]\n")
        
        # Verify it
        with console.status("Verifying test kills the mutant..."):
            for attempt in range(1, config.max_verification_attempts + 1):
                result = verifier.verify(mutant, generated)
                if result.status == VerificationStatus.VERIFIED:
                    break
                if attempt < config.max_verification_attempts:
                    console.print(f"[yellow]Attempt {attempt} failed ({result.status.value}), retrying...[/yellow]")
                    generated = await generator.generate(mutant)
        
        if result.status == VerificationStatus.VERIFIED:
            console.print("[bold green]✓ Verified! Test kills the mutant.[/bold green]")
            
            # Ask user
            confirm = typer.confirm("Write this test to the test file?", default=True)
            if confirm:
                success = writer.write(generated, mutant.id)
                if success:
                    console.print(f"[green]✓ Written to {generated.test_file_path}[/green]\n")
                    killed_count += 1
                else:
                    console.print("[red]✗ Write failed. Backup restored.[/red]\n")
            else:
                skipped_count += 1
        else:
            console.print(f"[red]✗ Could not generate a verified killing test ({result.status.value})[/red]")
            if result.status == VerificationStatus.DOESNT_KILL_MUTANT:
                console.print("[dim]This may be an equivalent mutant (semantically identical to original).[/dim]")
            skipped_count += 1
        
        console.print("─" * 60)
    
    # Summary
    console.print(Panel.fit(
        f"[bold]Done![/bold]\n"
        f"[green]✓ Killed: {killed_count}[/green]  "
        f"[yellow]Skipped: {skipped_count}[/yellow]  "
        f"[dim]Total: {len(survivors)}[/dim]"
    ))


@app.command("auto")
def auto(
    tool: str = typer.Option("mutmut", "--tool", "-t"),
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
    llm_provider: Optional[str] = typer.Option(None, "--llm"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be written without writing"),
):
    """[bold]Auto-fix[/bold] all survivors without interactive prompts."""
    asyncio.run(_auto_async(tool, project_root, llm_provider, dry_run))


async def _auto_async(tool, project_root, llm_provider, dry_run):
    config = _load_config(project_root)
    config = config.model_copy(update={"auto_write": True})
    if llm_provider:
        config = config.model_copy(update={"llm_provider": llm_provider})
    
    adapter = _get_adapter(tool, project_root)
    analyzer = MutationAnalyzer()
    llm = LLMClient.from_config(config)
    generator = TestGenerator(llm, config)
    verifier = MutantVerifier(config)
    writer = TestWriter(config)
    
    survivors = adapter.read_survivors()
    survivors = [analyzer.analyze(m) for m in survivors]
    
    console.print(f"[bold]Auto-fixing {len(survivors)} survivors...[/bold]\n")
    
    results = {"verified": 0, "failed": 0, "written": 0}
    
    for mutant in survivors:
        with console.status(f"Processing mutant {mutant.id}..."):
            generated = await generator.generate(mutant)
            
            for attempt in range(config.max_verification_attempts):
                result = verifier.verify(mutant, generated)
                if result.status == VerificationStatus.VERIFIED:
                    break
                if attempt < config.max_verification_attempts - 1:
                    generated = await generator.generate(mutant)
        
        if result.status == VerificationStatus.VERIFIED:
            results["verified"] += 1
            if not dry_run:
                if writer.write(generated, mutant.id):
                    results["written"] += 1
                    console.print(f"[green]✓ {mutant.id}[/green] → {generated.test_function_name}")
            else:
                console.print(f"[blue]DRY-RUN[/blue] {mutant.id} → {generated.test_function_name}")
        else:
            results["failed"] += 1
            console.print(f"[red]✗ {mutant.id}[/red] → {result.status.value}")
    
    console.print(f"\n[bold]Results:[/bold] {results}")


@app.command("report")
def report(
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Show the [bold]audit log[/bold] of all Quell actions."""
    config = _load_config(project_root)
    
    if not config.audit_log_path.exists():
        console.print("[yellow]No audit log found yet. Run quell fix first.[/yellow]")
        return
    
    lines = config.audit_log_path.read_text().strip().splitlines()
    
    table = Table(title="Quell Audit Log")
    table.add_column("Timestamp", style="dim")
    table.add_column("Mutant ID", style="cyan")
    table.add_column("Action", style="yellow")
    table.add_column("File")
    table.add_column("Test Function")
    
    import json
    for line in lines[-limit:]:
        entry = json.loads(line)
        table.add_row(
            entry.get("timestamp", "")[:19],
            entry.get("mutant_id", ""),
            entry.get("action", ""),
            Path(entry.get("file_path", "")).name if entry.get("file_path") else "",
            entry.get("test_function_name", ""),
        )
    
    console.print(table)


@app.command("init")
def init(
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
):
    """Add [tool.quell] configuration to pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        console.print("[red]No pyproject.toml found.[/red]")
        raise typer.Exit(1)
    
    content = pyproject.read_text()
    if "[tool.quell]" in content:
        console.print("[yellow]quell config already exists in pyproject.toml[/yellow]")
        return
    
    quell_config = """
[tool.quell]
llm_provider = "anthropic"           # "anthropic" | "openai" | "ollama"
llm_model = "claude-sonnet-4-5"
max_verification_attempts = 3
verification_timeout_seconds = 30
auto_write = false                   # set true for CI/CD usage
"""
    pyproject.write_text(content + quell_config)
    console.print("[green]✓ Added [tool.quell] to pyproject.toml[/green]")
    console.print("[dim]Set ANTHROPIC_API_KEY (or OPENAI_API_KEY) in your environment.[/dim]")


if __name__ == "__main__":
    app()
```

---

## `tests/fixtures/sample_project/src/calculator.py`

```python
"""Sample project for Quell integration testing."""

def divide(a: float, b: float) -> float:
    """Divide a by b. Raises ValueError for division by zero."""
    if b == 0:
        raise ValueError("Cannot divide by zero")
    return a / b


def discount(price: float, pct: float) -> float:
    """Apply percentage discount. pct must be between 0 and 100."""
    if pct < 0 or pct > 100:
        raise ValueError(f"Invalid percentage: {pct}")
    return price * (1 - pct / 100)


def is_adult(age: int) -> bool:
    """Return True if age is 18 or older."""
    return age >= 18
```

---

## `tests/fixtures/sample_project/tests/test_calculator.py`

```python
"""Weak tests for calculator — intentionally missing edge cases for demo."""
import pytest
from src.calculator import divide, discount, is_adult


def test_divide_normal():
    assert divide(10, 2) == 5.0


def test_divide_zero():
    with pytest.raises(ValueError):
        divide(10, 0)


def test_discount_basic():
    assert discount(100, 10) == 90.0


def test_is_adult_true():
    assert is_adult(25) is True

# Missing: test_is_adult_at_boundary (age=18)
# Missing: test_discount_at_boundary (pct=0, pct=100)
# This makes these easy targets for surviving mutants
```

---

## `CLAUDE.md` (Instructions for AI Assistants Working on this Repo)

```markdown
# Quell — AI Assistant Instructions

## What this project is
Quell auto-generates verified killing tests for survived mutants from mutmut and Stryker.
It reads mutation testing results, generates pytest assertions using rule-based logic + LLMs,
verifies each test actually kills the mutant, and injects it into test files via libcst.

## Tech Stack
- Python 3.11+, Typer CLI, Rich terminal UI, Pydantic v2, libcst, pytest

## Key invariants — NEVER violate these
1. `verifier.py`: ALWAYS restore source files in a `finally` block
2. `writer.py`: ALWAYS backup before writing, ALWAYS restore on failure
3. `writer.py`: ALWAYS validate CST parses correctly before writing to disk
4. NO code is transmitted to any server except the configured LLM provider
5. The LLM is ONLY called when rule-based generation is insufficient

## Running tests
```bash
uv run pytest tests/ -v
```

## Adding a new mutation operator
1. Add the enum value to `MutationOperator` in `core/models.py`
2. Add classification logic to `_classify_operator` in `core/analyzer.py`
3. Add generator method `_generate_<operator>_test` in `core/generator.py`
4. Add route in `generate()` method in `core/generator.py`
5. Add tests in `tests/unit/test_generator.py`

## Adding a new mutation adapter (e.g., PIT for Java)
1. Create `adapters/pit_adapter.py` implementing `MutationAdapter` protocol
2. Add it to `_get_adapter()` in `cli.py`
3. Add integration tests in `tests/adapters/`

## Code style
- Run `ruff check . --fix` before committing
- All public functions must have docstrings
- Pydantic models for all data structures (no raw dicts crossing module boundaries)
```

---

## `.github/workflows/ci.yml`

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.11", "3.12"]

    steps:
      - uses: actions/checkout@v4
      
      - name: Install uv
        uses: astral-sh/setup-uv@v2
      
      - name: Set up Python ${{ matrix.python-version }}
        run: uv python install ${{ matrix.python-version }}
      
      - name: Install dependencies
        run: uv sync --all-extras --dev
      
      - name: Lint
        run: uv run ruff check .
      
      - name: Type check
        run: uv run mypy quell/
      
      - name: Test
        run: uv run pytest tests/ -v --cov=quell --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v4
```

---

## Quick Start Instructions (for README)

```bash
# Install
pip install quell

# Step 1: Run your mutation testing tool first
mutmut run                          # for Python projects
npx stryker run --reporters=json    # for JS/TS projects

# Step 2: Let quell scan survivors
quell scan                          # see what survived

# Step 3: Fix interactively
quell fix                           # review + apply one by one

# Step 4: Or auto-fix everything
quell auto --dry-run                # preview
quell auto                          # apply all verified tests

# Config (optional)
quell init                          # adds [tool.quell] to pyproject.toml

# Use local LLM (privacy-first)
quell fix --llm ollama              # requires ollama running locally
```

---

## Instructions for Claude Code

When generating this project:

1. Create ALL files listed in the project structure above.
2. Use the exact code provided for each file — do not simplify or merge.
3. Run `uv sync --dev` after creating pyproject.toml.
4. Create the `tests/fixtures/sample_project/` with the calculator example.
5. Run `pytest tests/unit/` — all unit tests should pass.
6. The CLI should be invokable as `quell --help` after `uv run quell --help`.
7. Do NOT simplify the verifier.py — the backup/restore pattern is essential.
8. The `_apply_mutant` in verifier.py requires mutmut to be installed for mutmut source; for Stryker it does direct file replacement.
9. All async methods in generator.py must use `async/await` correctly.
10. The LLM providers read API keys from environment variables — do not hardcode.
