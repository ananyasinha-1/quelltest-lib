"""Unit tests for MutationAnalyzer."""
from __future__ import annotations
import pytest
from pathlib import Path
from quell.core.analyzer import MutationAnalyzer
from quell.core.models import MutationOperator, SurvivedMutant, MutantSource


@pytest.fixture
def analyzer() -> MutationAnalyzer:
    return MutationAnalyzer()


class TestClassifyOperator:
    def test_boundary_shift_gt_to_gte(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("if x > 0:", "if x >= 0:")
        assert op == MutationOperator.BOUNDARY_SHIFT

    def test_boundary_shift_lt_to_lte(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("if x < 10:", "if x <= 10:")
        assert op == MutationOperator.BOUNDARY_SHIFT

    def test_arithmetic_swap_plus_to_minus(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("return a + b", "return a - b")
        assert op == MutationOperator.ARITHMETIC_SWAP

    def test_arithmetic_swap_multiply(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("result = x * y", "result = x / y")
        assert op == MutationOperator.ARITHMETIC_SWAP

    def test_logical_swap_and_to_or(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("if a and b:", "if a or b:")
        assert op == MutationOperator.LOGICAL_SWAP

    def test_comparison_flip_eq_to_neq(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("if x == 0:", "if x != 0:")
        assert op == MutationOperator.COMPARISON_FLIP

    def test_constant_mutation_digit(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("return 0", "return 1")
        assert op == MutationOperator.CONSTANT_MUTATION

    def test_constant_mutation_bool(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("return True", "return False")
        assert op == MutationOperator.CONSTANT_MUTATION

    def test_string_mutation_empty_string(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator('return "hello"', 'return ""')
        assert op == MutationOperator.STRING_MUTATION

    def test_statement_removal_pass(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("do_something()", "pass")
        assert op == MutationOperator.STATEMENT_REMOVAL

    def test_statement_removal_empty(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("do_something()", "")
        assert op == MutationOperator.STATEMENT_REMOVAL

    def test_return_mutation_to_none(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("return value", "return None")
        assert op == MutationOperator.RETURN_MUTATION

    def test_unknown_fallback(self, analyzer: MutationAnalyzer) -> None:
        op = analyzer._classify_operator("raise ValueError('msg')", "raise ValueError('other')")
        assert op == MutationOperator.UNKNOWN


class TestExtractEnclosingFunction:
    def test_finds_function(self, analyzer: MutationAnalyzer, sample_calculator_path: Path) -> None:
        name, source = analyzer._extract_enclosing_function(sample_calculator_path, 20)
        assert name == "is_adult"
        assert "age >= 18" in source

    def test_returns_none_for_nonexistent_file(self, analyzer: MutationAnalyzer) -> None:
        name, source = analyzer._extract_enclosing_function(Path("/nonexistent/file.py"), 1)
        assert name is None
        assert source is None

    def test_finds_correct_function_by_line(self, analyzer: MutationAnalyzer, sample_calculator_path: Path) -> None:
        name, _ = analyzer._extract_enclosing_function(sample_calculator_path, 5)
        assert name == "divide"


class TestFindTestFile:
    def test_finds_test_file(self, analyzer: MutationAnalyzer, sample_calculator_path: Path) -> None:
        test_file = analyzer._find_test_file(sample_calculator_path)
        assert test_file is not None
        assert test_file.name == "test_calculator.py"

    def test_returns_none_when_no_test_file(self, analyzer: MutationAnalyzer, tmp_path: Path) -> None:
        source = tmp_path / "orphan.py"
        source.write_text("x = 1\n")
        result = analyzer._find_test_file(source)
        assert result is None


class TestExtractTestNames:
    def test_extracts_test_names(self, analyzer: MutationAnalyzer, sample_test_path: Path) -> None:
        names = analyzer._extract_test_names(sample_test_path)
        assert "test_divide_normal" in names
        assert "test_is_adult_true" in names

    def test_returns_empty_for_bad_file(self, analyzer: MutationAnalyzer, tmp_path: Path) -> None:
        bad_file = tmp_path / "bad.py"
        bad_file.write_text("def not a test(): pass")
        names = analyzer._extract_test_names(bad_file)
        assert names == []


class TestAnalyze:
    def test_analyze_enriches_mutant(
        self, analyzer: MutationAnalyzer, boundary_mutant: SurvivedMutant
    ) -> None:
        result = analyzer.analyze(boundary_mutant)
        assert result.operator == MutationOperator.BOUNDARY_SHIFT
        assert result.function_name == "is_adult"
        assert result.function_source is not None
        assert "age >= 18" in result.function_source

    def test_analyze_does_not_mutate_in_place(
        self, analyzer: MutationAnalyzer, boundary_mutant: SurvivedMutant
    ) -> None:
        original_operator = boundary_mutant.operator
        result = analyzer.analyze(boundary_mutant)
        # original should be unchanged
        assert boundary_mutant.operator == original_operator
        # result should have new data
        assert result is not boundary_mutant
