"""Shared pytest fixtures for Quell tests."""
from __future__ import annotations
import pytest
from pathlib import Path
from quell.core.models import (
    SurvivedMutant, MutantSource, MutationOperator, QuellConfig, GeneratedTest
)


FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


@pytest.fixture
def sample_calculator_path() -> Path:
    """Path to the sample calculator source file."""
    return SAMPLE_PROJECT / "src" / "calculator.py"


@pytest.fixture
def sample_test_path() -> Path:
    """Path to the sample calculator test file."""
    return SAMPLE_PROJECT / "tests" / "test_calculator.py"


@pytest.fixture
def stryker_report_path() -> Path:
    """Path to the sample Stryker JSON report."""
    return FIXTURES_DIR / "stryker_report.json"


@pytest.fixture
def default_config(tmp_path: Path) -> QuellConfig:
    """A QuellConfig pointing backup and audit paths to tmp_path."""
    return QuellConfig(
        backup_dir=tmp_path / ".quell" / "backups",
        audit_log_path=tmp_path / ".quell" / "audit.jsonl",
    )


@pytest.fixture
def boundary_mutant(sample_calculator_path: Path) -> SurvivedMutant:
    """A boundary shift mutant for is_adult (>= → >)."""
    return SurvivedMutant(
        id="42",
        source=MutantSource.MUTMUT,
        file_path=sample_calculator_path,
        line_start=20,
        line_end=20,
        original_code="    return age >= 18",
        mutated_code="    return age > 18",
        operator=MutationOperator.BOUNDARY_SHIFT,
        function_name="is_adult",
    )


@pytest.fixture
def arithmetic_mutant(sample_calculator_path: Path) -> SurvivedMutant:
    """An arithmetic swap mutant for discount (- → +)."""
    return SurvivedMutant(
        id="7",
        source=MutantSource.MUTMUT,
        file_path=sample_calculator_path,
        line_start=14,
        line_end=14,
        original_code="    return price * (1 - pct / 100)",
        mutated_code="    return price * (1 + pct / 100)",
        operator=MutationOperator.ARITHMETIC_SWAP,
        function_name="discount",
    )


@pytest.fixture
def comparison_mutant(sample_calculator_path: Path) -> SurvivedMutant:
    """A comparison flip mutant (== → !=)."""
    return SurvivedMutant(
        id="5",
        source=MutantSource.MUTMUT,
        file_path=sample_calculator_path,
        line_start=5,
        line_end=5,
        original_code="    if b == 0:",
        mutated_code="    if b != 0:",
        operator=MutationOperator.COMPARISON_FLIP,
        function_name="divide",
    )


@pytest.fixture
def unknown_mutant(sample_calculator_path: Path) -> SurvivedMutant:
    """An unknown operator mutant."""
    return SurvivedMutant(
        id="99",
        source=MutantSource.STRYKER,
        file_path=sample_calculator_path,
        line_start=7,
        line_end=7,
        original_code='        raise ValueError("Cannot divide by zero")',
        mutated_code='        raise ValueError("")',
        operator=MutationOperator.UNKNOWN,
        function_name="divide",
    )


@pytest.fixture
def sample_generated_test(sample_calculator_path: Path) -> GeneratedTest:
    """A sample GeneratedTest for testing the writer."""
    return GeneratedTest(
        mutant_id="42",
        test_function_name="test_quell_is_adult_mutant_42",
        test_code=(
            "def test_quell_is_adult_mutant_42():\n"
            '    """Kills boundary mutant."""\n'
            "    assert True\n"
        ),
        test_file_path=sample_calculator_path.parent.parent / "tests" / "test_calculator.py",
        explanation="Boundary test at value 18",
        operator=MutationOperator.BOUNDARY_SHIFT,
        generated_by="rule_based",
    )
