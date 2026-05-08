"""Unit tests for BugReader."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from quell.core.models import ConstraintKind, SpecSource
from quell.spec.bug_reader import BugReader


@pytest.fixture
def mock_llm() -> MagicMock:
    llm = MagicMock()
    llm.generate = AsyncMock(return_value=(
        '{"function_hint": "process_payment", "triggering_inputs": {"amount": 0},'
        ' "symptom": "no error raised", "expected_behavior": "raise ValueError"}'
    ))
    return llm


def test_read_returns_empty(tmp_path: Path, mock_llm: MagicMock) -> None:
    reader = BugReader(mock_llm, tmp_path)
    assert reader.read(tmp_path / "any.py") == []


def test_read_from_description_returns_bug_repro(
    tmp_path: Path, mock_llm: MagicMock, sample_payments_path: Path
) -> None:
    reader = BugReader(mock_llm, sample_payments_path.parent.parent)
    reqs = reader.read_from_description(
        "payment accepts zero amount silently",
        target_file=sample_payments_path,
    )
    assert len(reqs) == 1
    req = reqs[0]
    assert req.constraint_kind == ConstraintKind.BUG_REPRO
    assert req.source == SpecSource.BUG_REPORT


def test_source_name(mock_llm: MagicMock) -> None:
    reader = BugReader(mock_llm)
    assert reader.source_name == "bug_report"


def test_llm_failure_returns_unknown(
    tmp_path: Path, sample_payments_path: Path
) -> None:
    llm = MagicMock()
    llm.generate = AsyncMock(side_effect=Exception("LLM error"))
    reader = BugReader(llm, sample_payments_path.parent.parent)
    reqs = reader.read_from_description("some bug", target_file=sample_payments_path)
    assert len(reqs) == 1
    assert reqs[0].target_function == "process_payment" or reqs[0].target_function == "unknown"
