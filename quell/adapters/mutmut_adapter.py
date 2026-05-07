"""
Reads surviving mutants from mutmut's output.

mutmut stores results in .mutmut-cache/ directory.
We call `mutmut results` and `mutmut show <id>` to extract mutant data.
"""
from __future__ import annotations
import subprocess
import re
from pathlib import Path
from quell.core.models import SurvivedMutant, MutantSource
from quell.adapters.base import MutationAdapter


class MutmutAdapter(MutationAdapter):
    """
    Reads survived mutants from mutmut.

    Requires mutmut to be installed and `mutmut run` to have been executed.

    Usage:
        adapter = MutmutAdapter(project_root=Path("."))
        mutants = adapter.read_survivors()
    """

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root

    def read_survivors(self) -> list[SurvivedMutant]:
        """Parse mutmut results and return all survived mutants."""
        survived_ids = self._get_survived_ids()
        mutants = []
        for mutant_id in survived_ids:
            mutant = self._parse_mutant(mutant_id)
            if mutant:
                mutants.append(mutant)
        return mutants

    def _get_survived_ids(self) -> list[str]:
        """Run `mutmut results` and extract IDs of survived mutants."""
        result = subprocess.run(
            ["mutmut", "results"],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        # Parse lines like: "4-7, 9-14, 16-21" under "Survived"
        ids = []
        in_survived = False
        for line in result.stdout.splitlines():
            if "Survived" in line:
                in_survived = True
                continue
            if in_survived:
                if line.strip().startswith("----"):
                    continue
                if line.strip() == "" or ("Killed" in line or "Timeout" in line):
                    break
                # Parse ranges like "4-7, 9-14"
                parts = re.findall(r'\d+(?:-\d+)?', line)
                for part in parts:
                    if "-" in part:
                        start, end = part.split("-")
                        ids.extend(str(i) for i in range(int(start), int(end) + 1))
                    else:
                        ids.append(part)
        return ids

    def _parse_mutant(self, mutant_id: str) -> SurvivedMutant | None:
        """Run `mutmut show <id>` and parse the diff output."""
        result = subprocess.run(
            ["mutmut", "show", mutant_id],
            capture_output=True,
            text=True,
            cwd=self.project_root,
        )
        output = result.stdout

        # Parse unified diff format:
        # --- src/module.py
        # +++ src/module.py
        # @@ -47,7 +47,7 @@
        # - original line
        # + mutated line

        file_match = re.search(r'^--- (.+)$', output, re.MULTILINE)
        line_match = re.search(r'^@@ -(\d+)', output, re.MULTILINE)
        original_match = re.search(r'^- (.+)$', output, re.MULTILINE)
        mutated_match = re.search(r'^\+ (.+)$', output, re.MULTILINE)

        if not all([file_match, line_match, original_match, mutated_match]):
            return None

        file_path = self.project_root / file_match.group(1).strip()

        return SurvivedMutant(
            id=mutant_id,
            source=MutantSource.MUTMUT,
            file_path=file_path.resolve(),
            line_start=int(line_match.group(1)),
            line_end=int(line_match.group(1)),
            original_code=original_match.group(1),
            mutated_code=mutated_match.group(1),
        )
