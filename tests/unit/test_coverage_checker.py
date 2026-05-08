"""Unit tests for CoverageChecker."""
from __future__ import annotations
import pytest
from pathlib import Path
from quell.coverage.checker import CoverageChecker
from quell.core.models import Requirement, ConstraintKind, SpecSource


def test_marks_uncovered_when_no_test_file(
    tmp_path: Path, must_raise_requirement: Requirement
) -> None:
    checker = CoverageChecker(tmp_path)
    reqs = checker.check([must_raise_requirement])
    assert reqs[0].is_covered is False


def test_marks_covered_when_has_raises(
    tmp_path: Path, sample_payments_path: Path
) -> None:
    # Create a test file with pytest.raises
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_payments.py"
    test_file.write_text(
        "import pytest\n"
        "from tests.fixtures.sample_project.src.payments import process_payment, PaymentRequest\n\n"
        "def test_process_payment_raises():\n"
        "    with pytest.raises(ValueError):\n"
        "        pass\n"
    )

    req = Requirement(
        id="test001",
        description="raises ValueError",
        constraint_kind=ConstraintKind.MUST_RAISE,
        source=SpecSource.DOCSTRING,
        target_function="process_payment",
        target_file=sample_payments_path,
    )
    checker = CoverageChecker(tmp_path)
    reqs = checker.check([req])
    assert reqs[0].is_covered is True


def test_bug_repro_never_covered(
    tmp_path: Path, sample_payments_path: Path
) -> None:
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    test_file = tests_dir / "test_payments.py"
    test_file.write_text(
        "def test_process_payment(): pass\n"
    )
    req = Requirement(
        id="bug001",
        description="bug repro",
        constraint_kind=ConstraintKind.BUG_REPRO,
        source=SpecSource.BUG_REPORT,
        target_function="process_payment",
        target_file=sample_payments_path,
    )
    checker = CoverageChecker(tmp_path)
    reqs = checker.check([req])
    assert reqs[0].is_covered is False


def test_returns_same_list(
    tmp_path: Path, must_raise_requirement: Requirement
) -> None:
    checker = CoverageChecker(tmp_path)
    original = [must_raise_requirement]
    result = checker.check(original)
    assert result is original
