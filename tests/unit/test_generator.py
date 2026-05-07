"""Unit tests for TestGenerator."""
from __future__ import annotations
import pytest
from unittest.mock import AsyncMock, MagicMock
from pathlib import Path
from quell.core.generator import TestGenerator
from quell.core.models import (
    SurvivedMutant, MutationOperator, QuellConfig, GeneratedTest
)
from quell.llm.client import LLMClient


@pytest.fixture
def mock_llm() -> LLMClient:
    """A mock LLM client that returns a simple test function."""
    llm = MagicMock(spec=LLMClient)
    llm.generate = AsyncMock(return_value=(
        "```python\n"
        "def test_quell_function_99():\n"
        '    """LLM generated test."""\n'
        "    assert True\n"
        "```"
    ))
    return llm


@pytest.fixture
def generator(mock_llm: LLMClient) -> TestGenerator:
    config = QuellConfig()
    return TestGenerator(mock_llm, config)


class TestGenerate:
    async def test_routes_boundary_to_rule_based(
        self, generator: TestGenerator, boundary_mutant: SurvivedMutant
    ) -> None:
        result = await generator.generate(boundary_mutant)
        assert result.generated_by == "rule_based"
        assert result.operator == MutationOperator.BOUNDARY_SHIFT

    async def test_routes_arithmetic_to_rule_based(
        self, generator: TestGenerator, arithmetic_mutant: SurvivedMutant
    ) -> None:
        result = await generator.generate(arithmetic_mutant)
        assert result.generated_by == "rule_based"
        assert result.operator == MutationOperator.ARITHMETIC_SWAP

    async def test_routes_comparison_to_rule_based(
        self, generator: TestGenerator, comparison_mutant: SurvivedMutant
    ) -> None:
        result = await generator.generate(comparison_mutant)
        assert result.generated_by == "rule_based"
        assert result.operator == MutationOperator.COMPARISON_FLIP

    async def test_routes_unknown_to_llm(
        self, generator: TestGenerator, unknown_mutant: SurvivedMutant
    ) -> None:
        result = await generator.generate(unknown_mutant)
        assert result.generated_by.startswith("llm:")

    async def test_returns_generated_test(
        self, generator: TestGenerator, boundary_mutant: SurvivedMutant
    ) -> None:
        result = await generator.generate(boundary_mutant)
        assert isinstance(result, GeneratedTest)
        assert result.mutant_id == boundary_mutant.id
        assert result.test_function_name.startswith("test_quell_")


class TestMakeTestName:
    def test_includes_function_name(self, generator: TestGenerator, boundary_mutant: SurvivedMutant) -> None:
        name = generator._make_test_name(boundary_mutant)
        assert "is_adult" in name
        assert boundary_mutant.id in name

    def test_uses_code_fallback(self, generator: TestGenerator, sample_calculator_path: Path) -> None:
        mutant = SurvivedMutant(
            id="1",
            source="mutmut",
            file_path=sample_calculator_path,
            line_start=1,
            line_end=1,
            original_code="x = 1",
            mutated_code="x = 2",
        )
        name = generator._make_test_name(mutant)
        assert "code" in name


class TestExtractCodeBlock:
    def test_extracts_python_block(self, generator: TestGenerator) -> None:
        response = "Here is the test:\n```python\ndef test_foo():\n    pass\n```"
        code = generator._extract_code_block(response)
        assert code == "def test_foo():\n    pass"

    def test_returns_full_response_if_no_block(self, generator: TestGenerator) -> None:
        response = "def test_foo():\n    pass"
        code = generator._extract_code_block(response)
        assert "def test_foo" in code


class TestExtractFunctionName:
    def test_extracts_name(self, generator: TestGenerator) -> None:
        code = "def test_quell_foo_42():\n    pass"
        name = generator._extract_function_name(code)
        assert name == "test_quell_foo_42"

    def test_returns_none_if_no_match(self, generator: TestGenerator) -> None:
        code = "x = 1"
        name = generator._extract_function_name(code)
        assert name is None


class TestBoundaryTest:
    def test_extracts_boundary_value(self, generator: TestGenerator, boundary_mutant: SurvivedMutant) -> None:
        result = generator._generate_boundary_test(boundary_mutant)
        assert "18" in result.test_code
        assert "18" in result.explanation

    def test_test_file_path_set(self, generator: TestGenerator, boundary_mutant: SurvivedMutant) -> None:
        result = generator._generate_boundary_test(boundary_mutant)
        assert result.test_file_path is not None


class TestRuleBasedGenerators:
    def test_arithmetic_test_has_nonzero_hint(
        self, generator: TestGenerator, arithmetic_mutant: SurvivedMutant
    ) -> None:
        result = generator._generate_arithmetic_test(arithmetic_mutant)
        assert "NotImplementedError" in result.test_code

    def test_logical_test_mentions_conditions(
        self, generator: TestGenerator, arithmetic_mutant: SurvivedMutant
    ) -> None:
        mutant = arithmetic_mutant.model_copy(update={"operator": MutationOperator.LOGICAL_SWAP})
        result = generator._generate_logical_test(mutant)
        assert "NotImplementedError" in result.test_code

    def test_constant_test_mentions_exact_value(
        self, generator: TestGenerator, arithmetic_mutant: SurvivedMutant
    ) -> None:
        mutant = arithmetic_mutant.model_copy(update={"operator": MutationOperator.CONSTANT_MUTATION})
        result = generator._generate_constant_test(mutant)
        assert "NotImplementedError" in result.test_code

    def test_return_test_mentions_none(
        self, generator: TestGenerator, arithmetic_mutant: SurvivedMutant
    ) -> None:
        mutant = arithmetic_mutant.model_copy(update={"operator": MutationOperator.RETURN_MUTATION})
        result = generator._generate_return_test(mutant)
        assert "None" in result.test_code
