"""Unit tests for Writer (spec3 architecture)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from quell.core.models import GeneratedTest, QuellConfig
from quell.core.writer import Writer


@pytest.fixture
def writer(default_config: QuellConfig) -> Writer:
    return Writer(default_config)


class TestInject:
    def test_appends_test_to_existing_source(self, writer: Writer) -> None:
        existing = "import pytest\n\ndef test_existing():\n    assert True\n"
        new_test = "def test_new():\n    assert 1 == 1\n"
        result = writer._inject(existing, new_test)
        assert "test_existing" in result
        assert "test_new" in result

    def test_result_is_valid_python(self, writer: Writer) -> None:
        import libcst as cst
        existing = "def test_one():\n    pass\n"
        new_test = "def test_two():\n    pass\n"
        result = writer._inject(existing, new_test)
        cst.parse_module(result)  # must not raise

    def test_injects_into_empty_file(self, writer: Writer) -> None:
        result = writer._inject("", "def test_foo():\n    assert True\n")
        assert "test_foo" in result


class TestWrite:
    def test_creates_file_if_not_exists(
        self, writer: Writer, tmp_path: Path, sample_generated_test: GeneratedTest
    ) -> None:
        test_file = tmp_path / "new_tests" / "test_new.py"
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        success = writer.write(test, "test001")
        assert success
        assert test_file.exists()

    def test_appends_to_existing_file(
        self, writer: Writer, tmp_path: Path, sample_generated_test: GeneratedTest
    ) -> None:
        test_file = tmp_path / "test_existing.py"
        test_file.write_text("def test_existing():\n    assert True\n")
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        success = writer.write(test, "test001")
        assert success
        content = test_file.read_text()
        assert "test_existing" in content
        assert "test_quell_process_payment_test001" in content

    def test_backup_removed_on_success(
        self, writer: Writer, tmp_path: Path, sample_generated_test: GeneratedTest
    ) -> None:
        test_file = tmp_path / "test_calc.py"
        test_file.write_text("def test_one():\n    pass\n")
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        writer.write(test, "test001")
        bak_files = list(tmp_path.glob("*.bak"))
        assert len(bak_files) == 0

    def test_returns_false_and_restores_on_invalid_code(
        self, writer: Writer, tmp_path: Path
    ) -> None:
        test_file = tmp_path / "test_valid.py"
        original = "def test_one():\n    pass\n"
        test_file.write_text(original)

        bad_test = GeneratedTest(
            requirement_id="bad",
            test_function_name="test_bad",
            test_code="def test_bad(:\n    pass\n",  # syntax error
            test_file_path=test_file,
            explanation="bad test",
            generated_by="rule_engine",
        )
        success = writer.write(bad_test, "bad")
        assert not success
        assert test_file.read_text() == original

    def test_writes_audit_entry(
        self,
        writer: Writer,
        tmp_path: Path,
        sample_generated_test: GeneratedTest,
        default_config: QuellConfig,
    ) -> None:
        test_file = tmp_path / "test_audit.py"
        test_file.write_text("def test_one():\n    pass\n")
        test = sample_generated_test.model_copy(update={"test_file_path": test_file})
        writer.write(test, "test001")

        assert default_config.audit_log_path.exists()
        lines = default_config.audit_log_path.read_text().strip().splitlines()
        assert len(lines) >= 1
        entry = json.loads(lines[-1])
        assert entry["requirement_id"] == "test001"
        assert entry["action"] == "test_written"
