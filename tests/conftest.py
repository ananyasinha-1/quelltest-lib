"""Shared pytest fixtures for Quell tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from quell.core.models import (
    ConstraintKind,
    GeneratedTest,
    QuellConfig,
    Requirement,
    SpecSource,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"
SAMPLE_PROJECT = FIXTURES_DIR / "sample_project"


@pytest.fixture
def sample_payments_path() -> Path:
    """Path to the sample payments source file."""
    return SAMPLE_PROJECT / "src" / "payments.py"


@pytest.fixture
def sample_test_path() -> Path:
    """Path to the sample payments test file."""
    return SAMPLE_PROJECT / "tests" / "test_payments.py"


@pytest.fixture
def default_config(tmp_path: Path) -> QuellConfig:
    """A QuellConfig pointing backup and audit paths to tmp_path."""
    return QuellConfig(
        backup_dir=tmp_path / ".quell" / "backups",
        audit_log_path=tmp_path / ".quell" / "audit.jsonl",
    )


@pytest.fixture
def must_raise_requirement(sample_payments_path: Path) -> Requirement:
    """A MUST_RAISE requirement from the payments docstring."""
    return Requirement(
        id="test001",
        description="raises ValueError when amount is zero or negative",
        constraint_kind=ConstraintKind.MUST_RAISE,
        source=SpecSource.DOCSTRING,
        target_function="process_payment",
        target_file=sample_payments_path,
        expected_behavior="raises ValueError",
        raw_spec_text="ValueError: If amount is zero or negative.",
    )


@pytest.fixture
def boundary_requirement(sample_payments_path: Path) -> Requirement:
    """A BOUNDARY requirement from the payments docstring."""
    return Requirement(
        id="test002",
        description="must be positive",
        constraint_kind=ConstraintKind.BOUNDARY,
        source=SpecSource.DOCSTRING,
        target_function="apply_discount",
        target_file=sample_payments_path,
        raw_spec_text="Must be positive.",
    )


@pytest.fixture
def enum_requirement(sample_payments_path: Path) -> Requirement:
    """An ENUM_VALID requirement from the Pydantic model."""
    return Requirement(
        id="test003",
        description="PaymentRequest.currency must be one of ['USD', 'EUR', 'GBP']",
        constraint_kind=ConstraintKind.ENUM_VALID,
        source=SpecSource.TYPE,
        target_function="PaymentRequest",
        target_file=sample_payments_path,
        raw_spec_text="currency: Literal['USD', 'EUR', 'GBP']",
    )


@pytest.fixture
def sample_generated_test(sample_payments_path: Path) -> GeneratedTest:
    """A sample GeneratedTest for testing the writer."""
    return GeneratedTest(
        requirement_id="test001",
        test_function_name="test_quell_process_payment_test001",
        test_code=(
            "def test_quell_process_payment_test001():\n"
            '    """Quell: raises ValueError when amount is zero or negative"""\n'
            "    assert True\n"
        ),
        test_file_path=sample_payments_path.parent.parent / "tests" / "test_payments.py",
        explanation="pytest.raises(ValueError) test",
        generated_by="rule_engine",
    )
