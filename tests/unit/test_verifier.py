"""Unit tests for MutantVerifier."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from quell.core.verifier import MutantVerifier
from quell.core.models import (
    SurvivedMutant, GeneratedTest, VerificationStatus, QuellConfig,
    MutationOperator, MutantSource
)


@pytest.fixture
def verifier(default_config: QuellConfig) -> MutantVerifier:
    return MutantVerifier(default_config)


class TestWriteTempTest:
    def test_creates_temp_file(
        self, verifier: MutantVerifier, sample_generated_test: GeneratedTest
    ) -> None:
        temp_file = verifier._write_temp_test(sample_generated_test)
        assert temp_file.exists()
        assert "quell_temp_" in temp_file.name
        temp_file.unlink(missing_ok=True)

    def test_temp_file_has_test_code(
        self, verifier: MutantVerifier, sample_generated_test: GeneratedTest
    ) -> None:
        temp_file = verifier._write_temp_test(sample_generated_test)
        content = temp_file.read_text()
        assert "test_quell_is_adult_mutant_42" in content
        temp_file.unlink(missing_ok=True)


class TestBackupRestore:
    def test_backup_creates_file(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        source = tmp_path / "source.py"
        source.write_text("x = 1\n")
        backup = verifier._backup_source(source)
        assert backup.exists()
        assert backup.read_text() == "x = 1\n"

    def test_restore_overwrites_source(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        source = tmp_path / "source.py"
        source.write_text("x = 1\n")
        backup = verifier._backup_source(source)

        # Simulate mutation
        source.write_text("x = 999\n")

        verifier._restore_source(source, backup)
        assert source.read_text() == "x = 1\n"
        assert not backup.exists()

    def test_restore_removes_backup(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        source = tmp_path / "source.py"
        source.write_text("x = 1\n")
        backup = verifier._backup_source(source)
        verifier._restore_source(source, backup)
        assert not backup.exists()


class TestApplyMutant:
    def test_stryker_replaces_line(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        source = tmp_path / "code.py"
        source.write_text("line1\noriginal line\nline3\n")
        mutant = SurvivedMutant(
            id="1",
            source=MutantSource.STRYKER,
            file_path=source,
            line_start=2,
            line_end=2,
            original_code="original line",
            mutated_code="mutated line",
        )
        verifier._apply_mutant(mutant)
        lines = source.read_text().splitlines()
        assert lines[1] == "mutated line"

    def test_mutmut_calls_subprocess(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        source = tmp_path / "code.py"
        source.write_text("x = 1\n")
        mutant = SurvivedMutant(
            id="5",
            source=MutantSource.MUTMUT,
            file_path=source,
            line_start=1,
            line_end=1,
            original_code="x = 1",
            mutated_code="x = 2",
        )
        mock_result = MagicMock()
        mock_result.returncode = 0
        with patch("quell.core.verifier.subprocess.run", return_value=mock_result) as mock_run:
            verifier._apply_mutant(mutant)
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert "mutmut" in args
            assert "apply" in args


class TestRunPytest:
    def test_passing_test_returns_passed_true(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test_pass.py"
        test_file.write_text("def test_always_passes():\n    assert True\n")
        source_file = tmp_path / "source.py"
        source_file.write_text("x = 1\n")

        result = verifier._run_pytest(test_file, source_file)
        assert result["passed"] is True

    def test_failing_test_returns_passed_false(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test_fail.py"
        test_file.write_text("def test_always_fails():\n    assert False\n")
        source_file = tmp_path / "source.py"
        source_file.write_text("x = 1\n")

        result = verifier._run_pytest(test_file, source_file)
        assert result["passed"] is False


class TestVerify:
    def test_verify_restores_source_on_success(
        self, verifier: MutantVerifier, tmp_path: Path, default_config: QuellConfig
    ) -> None:
        source = tmp_path / "calculator.py"
        source.write_text("def add(a, b):\n    return a + b\n")

        mutant = SurvivedMutant(
            id="1",
            source=MutantSource.STRYKER,
            file_path=source,
            line_start=2,
            line_end=2,
            original_code="    return a + b",
            mutated_code="    return a - b",
        )
        test = GeneratedTest(
            mutant_id="1",
            test_function_name="test_quell_add_mutant_1",
            test_code="def test_quell_add_mutant_1():\n    assert True\n",
            test_file_path=tmp_path / "test_calc.py",
            explanation="test",
            operator=MutationOperator.ARITHMETIC_SWAP,
            generated_by="rule_based",
        )

        verifier.verify(mutant, test)

        # Source should be restored to original
        assert source.read_text() == "def add(a, b):\n    return a + b\n"

    def test_verify_restores_source_on_failure(
        self, verifier: MutantVerifier, tmp_path: Path
    ) -> None:
        source = tmp_path / "code.py"
        original_content = "def foo():\n    return 1\n"
        source.write_text(original_content)

        mutant = SurvivedMutant(
            id="2",
            source=MutantSource.STRYKER,
            file_path=source,
            line_start=2,
            line_end=2,
            original_code="    return 1",
            mutated_code="    return 2",
        )
        test = GeneratedTest(
            mutant_id="2",
            test_function_name="test_fails_on_original",
            test_code="def test_fails_on_original():\n    assert False\n",
            test_file_path=tmp_path / "test_code.py",
            explanation="test",
            operator=MutationOperator.CONSTANT_MUTATION,
            generated_by="rule_based",
        )

        result = verifier.verify(mutant, test)

        assert result.status == VerificationStatus.FAILS_ON_ORIGINAL
        # Source should be restored
        assert source.read_text() == original_content
