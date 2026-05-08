"""
Calculates Quell Score — requirement coverage per file/project.

Quell Score = covered_requirements / total_requirements

Stronger than coverage% because it measures whether your tests
prove the code meets its specification, not just that lines ran.
"""
from __future__ import annotations

from pathlib import Path

from quell.core.models import FileScore, ProjectScore
from quell.coverage.checker import CoverageChecker
from quell.spec.docstring_reader import DocstringReader
from quell.spec.type_reader import TypeReader


def calculate_score(project_root: Path = Path(".")) -> ProjectScore:
    """Scan all source files and calculate requirement coverage."""
    src_dirs = [
        project_root / "src",
        project_root / "app",
        project_root,
    ]
    py_files = []
    for d in src_dirs:
        if d.exists():
            py_files.extend([
                f for f in d.rglob("*.py")
                if "test" not in f.name and ".venv" not in str(f)
                and "CLAUDE" not in f.name
            ])
    if not py_files:
        return ProjectScore()

    checker = CoverageChecker(project_root)
    file_scores = []

    for f in py_files:
        reqs = []
        reqs.extend(DocstringReader().read(f))
        reqs.extend(TypeReader().read(f))
        if not reqs:
            continue
        reqs = checker.check(reqs)
        total = len(reqs)
        covered = sum(1 for r in reqs if r.is_covered)
        file_scores.append(FileScore(
            file_path=f,
            total_requirements=total,
            covered_requirements=covered,
            quell_score=covered / total if total else 0.0,
        ))

    return ProjectScore(files=sorted(file_scores, key=lambda x: x.quell_score))
