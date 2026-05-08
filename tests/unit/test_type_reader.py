"""Unit tests for TypeReader."""
from __future__ import annotations

from pathlib import Path

from quell.core.models import ConstraintKind, SpecSource
from quell.spec.type_reader import TypeReader


def test_reads_literal_enum(sample_payments_path: Path) -> None:
    reader = TypeReader()
    reqs = reader.read(sample_payments_path)
    enums = [r for r in reqs if r.constraint_kind == ConstraintKind.ENUM_VALID]
    assert len(enums) >= 1
    assert any("USD" in r.description for r in enums)


def test_reads_field_validators(sample_payments_path: Path) -> None:
    reader = TypeReader()
    reqs = reader.read(sample_payments_path)
    boundaries = [r for r in reqs if r.constraint_kind == ConstraintKind.BOUNDARY]
    assert len(boundaries) >= 1


def test_source_is_type(sample_payments_path: Path) -> None:
    reader = TypeReader()
    reqs = reader.read(sample_payments_path)
    assert all(r.source == SpecSource.TYPE for r in reqs)


def test_returns_empty_on_bad_file() -> None:
    reader = TypeReader()
    assert reader.read(Path("/nonexistent.py")) == []


def test_returns_empty_on_plain_file(tmp_path: Path) -> None:
    f = tmp_path / "plain.py"
    f.write_text("def foo(x: int) -> int: return x\n")
    reader = TypeReader()
    assert reader.read(f) == []


def test_pydantic_model_detection(sample_payments_path: Path) -> None:
    reader = TypeReader()
    reqs = reader.read(sample_payments_path)
    assert any("PaymentRequest" in r.target_function for r in reqs)


def test_source_name() -> None:
    assert TypeReader().source_name == "type"
