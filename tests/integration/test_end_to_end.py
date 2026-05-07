"""
End-to-end integration tests for Quell.

These tests exercise the full pipeline: analyzer → generator → verifier → writer
using the sample calculator project fixture.
"""
from __future__ import annotations
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from quell.core.analyzer import MutationAnalyzer
from quell.core.generator import TestGenerator
from quell.core.verifier import MutantVerifier
from quell.core.writer import TestWriter
from quell.core.models import (
    SurvivedMutant, MutantSource, MutationOperator, QuellConfig, VerificationStatus
)
from quell.llm.client import LLMClient


@pytest.fixture
def e2e_config(tmp_path: Path) -> QuellConfig:
    return QuellConfig(
        backup_dir=tmp_path / ".quell" / "backups",
        audit_log_path=tmp_path / ".quell" / "audit.jsonl",
    )


@pytest.fixture
def mock_llm() -> LLMClient:
    llm = MagicMock(spec=LLMClient)
    llm.generate = AsyncMock(return_value=(
        "```python\n"
        "def test_quell_divide_99():\n"
        '    """Test."""\n'
        "    assert True\n"
        "```"
    ))
    return llm


class TestAnalyzerPipeline:
    def test_analyzer_enriches_boundary_mutant(self, sample_calculator_path: Path) -> None:
        mutant = SurvivedMutant(
            id="1",
            source=MutantSource.MUTMUT,
            file_path=sample_calculator_path,
            line_start=20,
            line_end=20,
            original_code="    return age >= 18",
            mutated_code="    return age > 18",
        )
        analyzer = MutationAnalyzer()
        result = analyzer.analyze(mutant)

        assert result.operator == MutationOperator.BOUNDARY_SHIFT
        assert result.function_name == "is_adult"
        assert result.test_file_path is not None
        assert "test_divide_normal" in result.existing_tests or len(result.existing_tests) > 0


class TestGeneratorPipeline:
    async def test_generator_produces_test_for_boundary_mutant(
        self, mock_llm: LLMClient, sample_calculator_path: Path
    ) -> None:
        config = QuellConfig()
        generator = TestGenerator(mock_llm, config)

        mutant = SurvivedMutant(
            id="1",
            source=MutantSource.MUTMUT,
            file_path=sample_calculator_path,
            line_start=17,
            line_end=17,
            original_code="    return age >= 18",
            mutated_code="    return age > 18",
            operator=MutationOperator.BOUNDARY_SHIFT,
            function_name="is_adult",
        )

        test = await generator.generate(mutant)
        assert test.mutant_id == "1"
        assert test.operator == MutationOperator.BOUNDARY_SHIFT
        assert "18" in test.test_code  # boundary value should be in the test


class TestWriterPipeline:
    def test_writer_injects_test_into_new_file(
        self, e2e_config: QuellConfig, tmp_path: Path, sample_generated_test
    ) -> None:
        writer = TestWriter(e2e_config)
        test_file = tmp_path / "test_new.py"
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})

        success = writer.write(test, "42")

        assert success
        assert test_file.exists()
        content = test_file.read_text()
        assert "test_quell_is_adult_mutant_42" in content


class TestFullPipeline:
    async def test_analyze_generate_write_pipeline(
        self,
        mock_llm: LLMClient,
        e2e_config: QuellConfig,
        sample_calculator_path: Path,
        tmp_path: Path,
    ) -> None:
        """Full pipeline: analyze a raw mutant, generate a test, write it."""
        analyzer = MutationAnalyzer()
        generator = TestGenerator(mock_llm, e2e_config)
        writer = TestWriter(e2e_config)

        raw_mutant = SurvivedMutant(
            id="e2e_1",
            source=MutantSource.MUTMUT,
            file_path=sample_calculator_path,
            line_start=20,
            line_end=20,
            original_code="    return age >= 18",
            mutated_code="    return age > 18",
        )

        enriched = analyzer.analyze(raw_mutant)
        assert enriched.operator == MutationOperator.BOUNDARY_SHIFT

        generated = await generator.generate(enriched)
        assert generated.mutant_id == "e2e_1"

        test_file = tmp_path / "test_output.py"
        test = generated.model_copy(update={"test_file_path": test_file})
        success = writer.write(test, "e2e_1")
        assert success
        assert test_file.exists()
