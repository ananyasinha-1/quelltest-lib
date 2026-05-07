"""
Reads surviving mutants from Stryker's mutation-report.json.

Stryker produces a standardized JSON report with the mutation-testing-report-schema.
Run `stryker run --reporters=json` to generate mutation-report.json.
"""
from __future__ import annotations
import json
from pathlib import Path
from quell.core.models import SurvivedMutant, MutantSource
from quell.adapters.base import MutationAdapter


class StrykerAdapter(MutationAdapter):
    """
    Reads survived mutants from Stryker's mutation-report.json.

    Usage:
        adapter = StrykerAdapter(report_path=Path("mutation-report.json"))
        mutants = adapter.read_survivors()
    """

    def __init__(self, report_path: Path = Path("reports/mutation/mutation.json")):
        self.report_path = report_path

    def read_survivors(self) -> list[SurvivedMutant]:
        """Parse Stryker JSON report and return all Survived mutants."""
        if not self.report_path.exists():
            raise FileNotFoundError(
                f"Stryker report not found at {self.report_path}. "
                "Run: npx stryker run --reporters=json"
            )

        data = json.loads(self.report_path.read_text())
        mutants = []

        for file_path_str, file_data in data.get("files", {}).items():
            file_path = Path(file_path_str).resolve()

            for mutant in file_data.get("mutants", []):
                if mutant.get("status") != "Survived":
                    continue

                location = mutant.get("location", {})
                start = location.get("start", {})
                end = location.get("end", {})

                # Reconstruct original code from source + location
                source_lines = file_data.get("source", "").splitlines()
                line_idx = start.get("line", 1) - 1
                original_line = source_lines[line_idx] if line_idx < len(source_lines) else ""

                mutants.append(SurvivedMutant(
                    id=str(mutant["id"]),
                    source=MutantSource.STRYKER,
                    file_path=file_path,
                    line_start=start.get("line", 0),
                    line_end=end.get("line", 0),
                    col_start=start.get("column", 0),
                    col_end=end.get("column", 0),
                    original_code=original_line.strip(),
                    mutated_code=mutant.get("replacement", ""),
                ))

        return mutants
