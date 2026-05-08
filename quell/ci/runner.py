"""
CI runner for Quell — runs requirement checks in CI pipelines.

Supports targeted mode: only check files changed in the current PR.
This keeps CI runtime under 3 minutes for typical PRs.
"""
from __future__ import annotations
import subprocess
from pathlib import Path

from quell.ci.diff_parser import ChangedLines


def get_changed_python_files(
    base_ref: str = "origin/main",
    project_root: Path = Path("."),
) -> list[Path]:
    """Return Python files changed vs base_ref. Empty list if not in a git repo."""
    from quell.ci.diff_parser import get_changed_lines
    changed = get_changed_lines(base_ref, project_root)
    return [c.file_path for c in changed if c.file_path.exists()]


def run_check_full(project_root: Path = Path(".")) -> int:
    """Run quell check on full project. Returns exit code."""
    result = subprocess.run(
        ["python", "-m", "quell.cli", "check", "."],
        cwd=project_root,
    )
    return result.returncode


def run_check_targeted(
    changed: list[ChangedLines],
    project_root: Path = Path("."),
) -> int:
    """Run quell check only on changed files."""
    files = [str(c.file_path) for c in changed if c.file_path.exists()]
    if not files:
        return 0

    results = []
    for f in files:
        result = subprocess.run(
            ["python", "-m", "quell.cli", "check", f],
            cwd=project_root,
        )
        results.append(result.returncode)

    return max(results) if results else 0
