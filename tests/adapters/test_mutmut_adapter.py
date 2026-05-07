"""Unit tests for MutmutAdapter."""
from __future__ import annotations
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
from quell.adapters.mutmut_adapter import MutmutAdapter
from quell.core.models import MutantSource


SAMPLE_MUTMUT_RESULTS = """\
--- Survived ---
4, 5, 7-9
"""

SAMPLE_MUTMUT_SHOW = """\
--- src/calculator.py
+++ src/calculator.py
@@ -17,1 +17,1 @@
-    return age >= 18
+    return age > 18
"""


@pytest.fixture
def adapter(tmp_path: Path) -> MutmutAdapter:
    return MutmutAdapter(project_root=tmp_path)


class TestGetSurvivedIds:
    def test_parses_single_ids(self, adapter: MutmutAdapter) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "--- Survived ---\n4, 5\n"
        with patch("quell.adapters.mutmut_adapter.subprocess.run", return_value=mock_result):
            ids = adapter._get_survived_ids()
        assert "4" in ids
        assert "5" in ids

    def test_parses_ranges(self, adapter: MutmutAdapter) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "--- Survived ---\n7-9\n"
        with patch("quell.adapters.mutmut_adapter.subprocess.run", return_value=mock_result):
            ids = adapter._get_survived_ids()
        assert "7" in ids
        assert "8" in ids
        assert "9" in ids

    def test_returns_empty_when_no_survivors(self, adapter: MutmutAdapter) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "--- Killed ---\n1, 2, 3\n"
        with patch("quell.adapters.mutmut_adapter.subprocess.run", return_value=mock_result):
            ids = adapter._get_survived_ids()
        assert ids == []

    def test_stops_at_killed_section(self, adapter: MutmutAdapter) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "--- Survived ---\n4, 5\n--- Killed ---\n6, 7\n"
        with patch("quell.adapters.mutmut_adapter.subprocess.run", return_value=mock_result):
            ids = adapter._get_survived_ids()
        assert "4" in ids
        assert "5" in ids
        assert "6" not in ids


class TestParseMutant:
    def test_parses_valid_diff(self, adapter: MutmutAdapter, tmp_path: Path) -> None:
        # Create the source file so the path resolves
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        calc = src_dir / "calculator.py"
        calc.write_text("x = 1\n")

        mock_result = MagicMock()
        mock_result.stdout = (
            "--- src/calculator.py\n"
            "+++ src/calculator.py\n"
            "@@ -17,1 +17,1 @@\n"
            "-    return age >= 18\n"
            "+    return age > 18\n"
        )
        with patch("quell.adapters.mutmut_adapter.subprocess.run", return_value=mock_result):
            mutant = adapter._parse_mutant("42")

        assert mutant is not None
        assert mutant.id == "42"
        assert mutant.source == MutantSource.MUTMUT
        assert mutant.line_start == 17
        assert "age >= 18" in mutant.original_code
        assert "age > 18" in mutant.mutated_code

    def test_returns_none_for_unparseable_diff(self, adapter: MutmutAdapter) -> None:
        mock_result = MagicMock()
        mock_result.stdout = "some garbage output"
        with patch("quell.adapters.mutmut_adapter.subprocess.run", return_value=mock_result):
            mutant = adapter._parse_mutant("1")
        assert mutant is None


class TestReadSurvivors:
    def test_returns_list_of_mutants(self, adapter: MutmutAdapter, tmp_path: Path) -> None:
        src_dir = tmp_path / "src"
        src_dir.mkdir()
        calc = src_dir / "calculator.py"
        calc.write_text("x = 1\n")

        results_result = MagicMock()
        results_result.stdout = "--- Survived ---\n42\n"

        show_result = MagicMock()
        show_result.stdout = (
            "--- src/calculator.py\n"
            "+++ src/calculator.py\n"
            "@@ -17,1 +17,1 @@\n"
            "-    return age >= 18\n"
            "+    return age > 18\n"
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return results_result
            return show_result

        with patch("quell.adapters.mutmut_adapter.subprocess.run", side_effect=side_effect):
            mutants = adapter.read_survivors()

        assert len(mutants) == 1
        assert mutants[0].id == "42"
