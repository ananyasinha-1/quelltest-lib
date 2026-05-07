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
