"""Unit tests for CodeGuardReader."""
from __future__ import annotations

from pathlib import Path

import pytest

from quell.core.models import ConstraintKind, SpecSource
from quell.spec.code_guard_reader import CodeGuardReader


@pytest.fixture()
def guard_file(tmp_path: Path) -> Path:
    """A Python file containing various guard clause patterns."""
    f = tmp_path / "guards.py"
    f.write_text(
        """
def process_payment(amount, currency, user):
    if amount <= 0:
        raise ValueError("Amount must be positive")
    if user is None:
        raise ValueError("User must not be None")
    if currency not in ["USD", "EUR", "GBP"]:
        raise ValueError("Invalid currency")
    if not isinstance(amount, (int, float)):
        raise TypeError("Amount must be numeric")
    return amount

def validate_token(token, request):
    if not token:
        raise PermissionError("Missing token")
    if not request.user.is_authenticated:
        raise PermissionError("Not authenticated")
    return True

def risky_function(x):
    try:
        return int(x)
    except:
        pass

def silent_fail(result):
    if not result:
        return None
    return result

def assert_boundary(n):
    assert n > 0, "must be positive"
    return n
"""
    )
    return f


def test_reads_boundary(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    boundary = [r for r in reqs if r.constraint_kind == ConstraintKind.BOUNDARY]
    assert len(boundary) >= 1


def test_reads_not_null(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    not_null = [r for r in reqs if r.constraint_kind == ConstraintKind.NOT_NULL]
    assert len(not_null) >= 1


def test_reads_enum_valid(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    enums = [r for r in reqs if r.constraint_kind == ConstraintKind.ENUM_VALID]
    assert len(enums) >= 1


def test_reads_type_check(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    type_checks = [r for r in reqs if r.constraint_kind == ConstraintKind.TYPE_CHECK]
    assert len(type_checks) >= 1


def test_reads_auth_check(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    auth = [r for r in reqs if r.constraint_kind == ConstraintKind.AUTH_CHECK]
    assert len(auth) >= 1


def test_reads_bare_except(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    bare = [r for r in reqs if r.constraint_kind == ConstraintKind.BARE_EXCEPT]
    assert len(bare) >= 1


def test_reads_silent_fail(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    silent = [r for r in reqs if r.constraint_kind == ConstraintKind.SILENT_FAIL]
    assert len(silent) >= 1


def test_reads_assert(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    asserts = [r for r in reqs if r.constraint_kind == ConstraintKind.BOUNDARY]
    assert len(asserts) >= 1


def test_source_is_code_guard(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    assert all(r.source == SpecSource.CODE_GUARD for r in reqs)


def test_returns_empty_on_bad_file() -> None:
    reader = CodeGuardReader()
    assert reader.read(Path("/nonexistent/file.py")) == []


def test_returns_empty_on_plain_file(tmp_path: Path) -> None:
    f = tmp_path / "plain.py"
    f.write_text("def foo(x):\n    return x\n")
    reader = CodeGuardReader()
    assert reader.read(f) == []


def test_target_function_set(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    funcs = {r.target_function for r in reqs}
    assert "process_payment" in funcs


def test_raw_spec_text_set(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    assert all(r.raw_spec_text is not None for r in reqs)


def test_source_name() -> None:
    assert CodeGuardReader().source_name == "code_guard"


def test_violation_input_boundary(guard_file: Path) -> None:
    reader = CodeGuardReader()
    reqs = reader.read(guard_file)
    boundary = [r for r in reqs if r.constraint_kind == ConstraintKind.BOUNDARY
                and r.violation_input is not None]
    assert len(boundary) >= 1
    assert "boundary_value" in boundary[0].violation_input  # type: ignore[index]


def test_no_requirements_from_file_with_no_guards(tmp_path: Path) -> None:
    f = tmp_path / "clean.py"
    f.write_text(
        "def add(a, b):\n    return a + b\n\ndef greet(name):\n    return f'Hello {name}'\n"
    )
    reader = CodeGuardReader()
    assert reader.read(f) == []
