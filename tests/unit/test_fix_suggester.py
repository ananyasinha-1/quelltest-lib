"""Unit tests for FixSuggester."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from quell.core.models import ConstraintKind, GeneratedTest, QuellConfig, Requirement, SpecSource
from quell.fix.suggester import FixSuggester


@pytest.fixture()
def sample_req(tmp_path: Path) -> Requirement:
    src = tmp_path / "payments.py"
    src.write_text(
        "def process_payment(amount):\n    return amount\n"
    )
    return Requirement(
        id="abc12345",
        description="boundary condition — if amount <= 0:",
        constraint_kind=ConstraintKind.BOUNDARY,
        source=SpecSource.CODE_GUARD,
        target_function="process_payment",
        target_file=src,
        raw_spec_text="if amount <= 0:",
    )


@pytest.fixture()
def sample_test(tmp_path: Path) -> GeneratedTest:
    return GeneratedTest(
        requirement_id="abc12345",
        test_function_name="test_quell_process_payment_boundary_abc12345",
        test_code=(
            "import pytest\n"
            "def test_quell_process_payment_boundary_abc12345():\n"
            "    with pytest.raises(ValueError):\n"
            "        process_payment(0)\n"
        ),
        test_file_path=tmp_path / "test_quell_payments.py",
        explanation="boundary check",
        generated_by="rule_engine",
    )


def test_extract_explanation() -> None:
    suggester = FixSuggester(MagicMock(), QuellConfig())
    response = "Adds a boundary check before processing.\n```python\ndef foo(): pass\n```"
    assert suggester._extract_explanation(response) == "Adds a boundary check before processing."


def test_extract_code_block() -> None:
    suggester = FixSuggester(MagicMock(), QuellConfig())
    response = "Fix:\n```python\ndef foo():\n    return 1\n```"
    result = suggester._extract_code_block(response)
    assert result == "def foo():\n    return 1"


def test_extract_code_block_none_when_missing() -> None:
    suggester = FixSuggester(MagicMock(), QuellConfig())
    assert suggester._extract_code_block("no code here") is None


def test_generate_diff() -> None:
    suggester = FixSuggester(MagicMock(), QuellConfig())
    original = "def foo():\n    return 1\n"
    suggested = "def foo():\n    if x <= 0:\n        raise ValueError\n    return 1\n"
    diff = suggester._generate_diff(original, suggested)
    assert "---" in diff
    assert "+++" in diff
    assert "raise ValueError" in diff


def test_extract_function(tmp_path: Path) -> None:
    src = tmp_path / "mod.py"
    src.write_text(
        "def helper():\n    pass\n\ndef main():\n    return 42\n"
    )
    suggester = FixSuggester(MagicMock(), QuellConfig())
    result = suggester._extract_function(src.read_text(), "main")
    assert "def main" in result
    assert "helper" not in result


@pytest.mark.asyncio
async def test_suggest_returns_none_when_no_code_block(
    sample_req: Requirement, sample_test: GeneratedTest
) -> None:
    llm = AsyncMock()
    llm.generate = AsyncMock(return_value="No code block in this response.")
    suggester = FixSuggester(llm, QuellConfig())
    result = await suggester.suggest(sample_req, sample_test)
    assert result is None
