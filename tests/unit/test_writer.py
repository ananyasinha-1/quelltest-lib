"""Unit tests for TestWriter."""
from __future__ import annotations
import pytest
from pathlib import Path
from quell.core.writer import TestWriter
from quell.core.models import GeneratedTest, QuellConfig, MutationOperator


@pytest.fixture
def writer(default_config: QuellConfig) -> TestWriter:
    return TestWriter(default_config)


class TestInjectTest:
    def test_appends_test_to_existing_source(self, writer: TestWriter) -> None:
        existing = "import pytest\n\ndef test_existing():\n    assert True\n"
        new_test = "def test_new():\n    assert 1 == 1\n"
        result = writer._inject_test(existing, new_test)
        assert "test_existing" in result
        assert "test_new" in result

    def test_result_is_valid_python(self, writer: TestWriter) -> None:
        import libcst as cst
        existing = "def test_one():\n    pass\n"
        new_test = "def test_two():\n    pass\n"
        result = writer._inject_test(existing, new_test)
        # Should not raise
        cst.parse_module(result)

    def test_injects_into_empty_file(self, writer: TestWriter) -> None:
        existing = ""
        new_test = "def test_foo():\n    assert True\n"
        result = writer._inject_test(existing, new_test)
        assert "test_foo" in result


class TestWrite:
    def test_creates_file_if_not_exists(
        self, writer: TestWriter, tmp_path: Path, sample_generated_test: GeneratedTest
    ) -> None:
        test_file = tmp_path / "new_tests" / "test_new.py"
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        success = writer.write(test, "42")
        assert success
        assert test_file.exists()

    def test_appends_to_existing_file(
        self, writer: TestWriter, tmp_path: Path, sample_generated_test: GeneratedTest
    ) -> None:
        test_file = tmp_path / "test_existing.py"
        test_file.write_text("def test_existing():\n    assert True\n")
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        success = writer.write(test, "42")
        assert success
        content = test_file.read_text()
        assert "test_existing" in content
        assert "test_quell_is_adult_mutant_42" in content

    def test_backup_removed_on_success(
        self, writer: TestWriter, tmp_path: Path, sample_generated_test: GeneratedTest
    ) -> None:
        test_file = tmp_path / "test_calc.py"
        test_file.write_text("def test_one():\n    pass\n")
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        writer.write(test, "42")
        # No .bak files should remain
        bak_files = list(tmp_path.glob("*.bak"))
        assert len(bak_files) == 0

    def test_returns_false_and_restores_on_invalid_code(
        self, writer: TestWriter, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test_valid.py"
        original_content = "def test_one():\n    pass\n"
        test_file.write_text(original_content)

        bad_test = GeneratedTest(
            mutant_id="bad",
            test_function_name="test_bad",
            test_code="def test_bad(:\n    pass\n",  # syntax error
            test_file_path=test_file,
            explanation="bad test",
            operator=MutationOperator.UNKNOWN,
            generated_by="rule_based",
        )
        success = writer.write(bad_test, "bad")
        assert not success
        # File should be restored to original
        assert test_file.read_text() == original_content

    def test_writes_audit_entry(
        self, writer: TestWriter, tmp_path: Path, sample_generated_test: GeneratedTest, default_config: QuellConfig
    ) -> None:
        test_file = tmp_path / "test_audit.py"
        test_file.write_text("def test_one():\n    pass\n")
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        writer.write(test, "42")

        assert default_config.audit_log_path.exists()
        import json
        lines = default_config.audit_log_path.read_text().strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry["mutant_id"] == "42"
        assert entry["action"] == "test_written"
