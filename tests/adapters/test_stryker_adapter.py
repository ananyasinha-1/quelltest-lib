"""Unit tests for StrykerAdapter."""
from __future__ import annotations
import pytest
import json
from pathlib import Path
from quell.adapters.stryker_adapter import StrykerAdapter
from quell.core.models import MutantSource


@pytest.fixture
def stryker_adapter(stryker_report_path: Path) -> StrykerAdapter:
    return StrykerAdapter(report_path=stryker_report_path)


class TestReadSurvivors:
    def test_reads_survived_mutants(self, stryker_adapter: StrykerAdapter) -> None:
        mutants = stryker_adapter.read_survivors()
        assert len(mutants) == 2  # only 2 Survived in the fixture

    def test_mutants_have_stryker_source(self, stryker_adapter: StrykerAdapter) -> None:
        mutants = stryker_adapter.read_survivors()
        for m in mutants:
            assert m.source == MutantSource.STRYKER

    def test_mutant_ids_are_strings(self, stryker_adapter: StrykerAdapter) -> None:
        mutants = stryker_adapter.read_survivors()
        for m in mutants:
            assert isinstance(m.id, str)

    def test_skips_killed_mutants(self, stryker_adapter: StrykerAdapter) -> None:
        mutants = stryker_adapter.read_survivors()
        ids = [m.id for m in mutants]
        assert "3" not in ids  # id=3 is "Killed" in fixture

    def test_location_parsed_correctly(self, stryker_adapter: StrykerAdapter) -> None:
        mutants = stryker_adapter.read_survivors()
        mutant = next(m for m in mutants if m.id == "1")
        assert mutant.line_start == 2
        assert mutant.col_start == 7

    def test_raises_if_report_not_found(self, tmp_path: Path) -> None:
        adapter = StrykerAdapter(report_path=tmp_path / "nonexistent.json")
        with pytest.raises(FileNotFoundError):
            adapter.read_survivors()

    def test_replacement_used_as_mutated_code(self, stryker_adapter: StrykerAdapter) -> None:
        mutants = stryker_adapter.read_survivors()
        mutant = next(m for m in mutants if m.id == "1")
        assert "b !== 0" in mutant.mutated_code

    def test_empty_files_section(self, tmp_path: Path) -> None:
        report = tmp_path / "empty_report.json"
        report.write_text(json.dumps({"files": {}}))
        adapter = StrykerAdapter(report_path=report)
        assert adapter.read_survivors() == []

    def test_no_survived_in_mutants(self, tmp_path: Path) -> None:
        report = tmp_path / "no_survived.json"
        data = {
            "files": {
                "src/foo.js": {
                    "source": "x = 1\n",
                    "mutants": [
                        {
                            "id": "1",
                            "location": {"start": {"line": 1, "column": 0}, "end": {"line": 1, "column": 5}},
                            "replacement": "x = 2",
                            "status": "Killed",
                        }
                    ],
                }
            }
        }
        report.write_text(json.dumps(data))
        adapter = StrykerAdapter(report_path=report)
        assert adapter.read_survivors() == []
