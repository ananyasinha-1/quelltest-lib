"""
Formats CI run results for different output targets.

Supported formats:
  console   — Rich-formatted human-readable output (default)
  json      — Machine-readable JSON for dashboards and external tooling
  github    — GitHub Actions annotations (::notice/::warning/::error)
"""
from __future__ import annotations
import json
from dataclasses import dataclass, field
from pathlib import Path

from quell.core.models import ProjectScore


@dataclass
class CIReport:
    """Full CI run summary."""
    score: float
    total_requirements: int
    covered_requirements: int
    threshold: float
    passed: bool
    dry_run: bool = False
    files_checked: list[str] = field(default_factory=list)


def report_console(report: CIReport, project_score: ProjectScore) -> None:
    """Print a Rich-formatted CI summary to stdout."""
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel

    console = Console()
    status_icon = "✓" if report.passed else "✗"
    status_color = "green" if report.passed else "red"

    summary = (
        f"[{status_color}]{status_icon} Quell Score: {report.score:.0%}[/{status_color}]\n\n"
        f"Requirements: [bold]{report.covered_requirements}/{report.total_requirements}[/bold] covered  "
        f"Threshold: {report.threshold:.0%}"
    )

    if report.dry_run:
        summary = "[yellow](dry-run)[/yellow] " + summary

    console.print(Panel(summary, title="Quell CI", border_style=status_color))

    if project_score.files:
        table = Table(title="File Scores", show_header=True)
        table.add_column("File", style="blue")
        table.add_column("Requirements", justify="right")
        table.add_column("Covered", justify="right")
        table.add_column("Score", justify="right")
        table.add_column("Grade", justify="center")

        for fs in sorted(project_score.files, key=lambda f: f.quell_score):
            grade_color = {"A": "green", "B": "yellow", "C": "yellow", "F": "red"}.get(
                fs.grade, "white"
            )
            table.add_row(
                str(fs.file_path.name),
                str(fs.total_requirements),
                str(fs.covered_requirements),
                f"{fs.percentage}%",
                f"[{grade_color}]{fs.grade}[/{grade_color}]",
            )

        console.print(table)


def report_json(report: CIReport, output_path: Path | None = None) -> str:
    """Serialize CI report to JSON. Returns JSON string."""
    payload = {
        "score": report.score,
        "total_requirements": report.total_requirements,
        "covered_requirements": report.covered_requirements,
        "threshold": report.threshold,
        "passed": report.passed,
        "dry_run": report.dry_run,
    }
    out = json.dumps(payload, indent=2)

    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(out, encoding="utf-8")

    return out


def report_github_actions(report: CIReport) -> None:
    """Emit GitHub Actions workflow commands for step outputs and annotations."""
    pct = int(report.score * 100)
    level = "notice" if report.passed else "error"
    print(f"::set-output name=score::{pct}")
    print(f"::set-output name=threshold_passed::{str(report.passed).lower()}")
    print(
        f"::{level}::Quell Score: {pct}% | "
        f"{report.covered_requirements}/{report.total_requirements} requirements covered | "
        f"{'PASS' if report.passed else 'FAIL'}"
    )
