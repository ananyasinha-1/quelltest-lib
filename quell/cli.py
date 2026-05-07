"""
Quell CLI — built with Typer.

Commands:
  quell scan                    List all surviving mutants
  quell fix                     Interactive fix loop (review one by one)
  quell auto                    Auto-fix all survivors (no prompts)
  quell report                  Show audit log
  quell init                    Add [tool.quell] to pyproject.toml
"""
from __future__ import annotations
import asyncio
import json
from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from quell.core.models import QuellConfig, VerificationStatus
from quell.core.analyzer import MutationAnalyzer
from quell.core.generator import TestGenerator
from quell.core.verifier import MutantVerifier
from quell.core.writer import TestWriter
from quell.adapters.mutmut_adapter import MutmutAdapter
from quell.adapters.stryker_adapter import StrykerAdapter
from quell.llm.client import LLMClient

app = typer.Typer(
    name="quell",
    help="Quell your mutation testing survivors. Auto-generates verified killing tests.",
    rich_markup_mode="rich",
)
console = Console()


def _load_config(project_root: Path) -> QuellConfig:
    """Load config from pyproject.toml [tool.quell] or return defaults."""
    try:
        import tomllib
        pyproject = project_root / "pyproject.toml"
        if pyproject.exists():
            data = tomllib.loads(pyproject.read_text())
            quell_config = data.get("tool", {}).get("quell", {})
            if quell_config:
                return QuellConfig(**quell_config)
    except Exception:
        pass
    return QuellConfig()


def _get_adapter(tool: str, project_root: Path):
    """Return the appropriate adapter based on tool flag."""
    if tool == "mutmut":
        return MutmutAdapter(project_root)
    elif tool == "stryker":
        report_candidates = [
            project_root / "reports" / "mutation" / "mutation.json",
            project_root / "mutation-report.json",
        ]
        for candidate in report_candidates:
            if candidate.exists():
                return StrykerAdapter(candidate)
        raise typer.BadParameter("No Stryker report found. Run: npx stryker run --reporters=json")
    else:
        raise typer.BadParameter(f"Unknown tool: {tool}. Use 'mutmut' or 'stryker'.")


@app.command("scan")
def scan(
    tool: str = typer.Option("mutmut", "--tool", "-t", help="mutmut or stryker"),
    project_root: Path = typer.Option(Path("."), "--root", "-r", help="Project root directory"),
):
    """[bold]Scan[/bold] and list all surviving mutants."""

    console.print(Panel.fit("[bold blue]Quell — Scanning for survivors[/bold blue]"))

    config = _load_config(project_root)
    adapter = _get_adapter(tool, project_root)
    analyzer = MutationAnalyzer()

    with console.status("Reading mutation results..."):
        survivors = adapter.read_survivors()
        survivors = [analyzer.analyze(m) for m in survivors]

    if not survivors:
        console.print("[green]✓ No surviving mutants found![/green]")
        return

    table = Table(title=f"Surviving Mutants ({len(survivors)} total)")
    table.add_column("ID", style="cyan", width=6)
    table.add_column("File", style="blue")
    table.add_column("Line", style="yellow", width=6)
    table.add_column("Operator", style="magenta")
    table.add_column("Original → Mutated", style="white")

    for m in survivors:
        table.add_row(
            str(m.id),
            str(m.file_path.name),
            str(m.line_start),
            m.operator.value,
            f"[red]{m.original_code.strip()[:30]}[/red] → [green]{m.mutated_code.strip()[:30]}[/green]",
        )

    console.print(table)
    console.print(f"\n[yellow]Run [bold]quell fix[/bold] to generate and verify killing tests.[/yellow]")


@app.command("fix")
def fix(
    tool: str = typer.Option("mutmut", "--tool", "-t"),
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
    llm_provider: Optional[str] = typer.Option(None, "--llm"),
    mutant_id: Optional[str] = typer.Option(None, "--id", help="Fix only a specific mutant ID"),
):
    """[bold]Interactively[/bold] generate and apply verified killing tests."""
    asyncio.run(_fix_async(tool, project_root, llm_provider, mutant_id))


async def _fix_async(tool: str, project_root: Path, llm_provider: Optional[str], mutant_id: Optional[str]) -> None:
    config = _load_config(project_root)
    if llm_provider:
        config = config.model_copy(update={"llm_provider": llm_provider})

    adapter = _get_adapter(tool, project_root)
    analyzer = MutationAnalyzer()
    llm = LLMClient.from_config(config)
    generator = TestGenerator(llm, config)
    verifier = MutantVerifier(config)
    writer = TestWriter(config)

    with console.status("Reading mutation results..."):
        survivors = adapter.read_survivors()
        survivors = [analyzer.analyze(m) for m in survivors]
        if mutant_id:
            survivors = [m for m in survivors if m.id == mutant_id]

    if not survivors:
        console.print("[green]No survivors to fix![/green]")
        return

    console.print(f"[bold]Found {len(survivors)} surviving mutants.[/bold]\n")

    killed_count = 0
    skipped_count = 0

    for i, mutant in enumerate(survivors, 1):
        console.print(Panel(
            f"[bold cyan]Mutant {mutant.id}[/bold cyan] ({i}/{len(survivors)})\n"
            f"[blue]{mutant.file_path.name}[/blue] line [yellow]{mutant.line_start}[/yellow]\n\n"
            f"[red]- {mutant.original_code.strip()}[/red]\n"
            f"[green]+ {mutant.mutated_code.strip()}[/green]\n\n"
            f"Operator: [magenta]{mutant.operator.value}[/magenta]"
        ))

        # Generate candidate test
        with console.status("Generating killing test..."):
            generated = await generator.generate(mutant)

        console.print("\n[bold]Generated test:[/bold]")
        console.print(Syntax(generated.test_code, "python", theme="monokai"))
        console.print(f"[dim]Generated by: {generated.generated_by}[/dim]")
        console.print(f"[dim]Explanation: {generated.explanation}[/dim]\n")

        # Verify it
        result = None
        with console.status("Verifying test kills the mutant..."):
            for attempt in range(1, config.max_verification_attempts + 1):
                result = verifier.verify(mutant, generated)
                if result.status == VerificationStatus.VERIFIED:
                    break
                if attempt < config.max_verification_attempts:
                    console.print(f"[yellow]Attempt {attempt} failed ({result.status.value}), retrying...[/yellow]")
                    generated = await generator.generate(mutant)

        if result and result.status == VerificationStatus.VERIFIED:
            console.print("[bold green]✓ Verified! Test kills the mutant.[/bold green]")

            # Ask user
            confirm = typer.confirm("Write this test to the test file?", default=True)
            if confirm:
                success = writer.write(generated, mutant.id)
                if success:
                    console.print(f"[green]✓ Written to {generated.test_file_path}[/green]\n")
                    killed_count += 1
                else:
                    console.print("[red]✗ Write failed. Backup restored.[/red]\n")
            else:
                skipped_count += 1
        else:
            status_val = result.status.value if result else "unknown"
            console.print(f"[red]✗ Could not generate a verified killing test ({status_val})[/red]")
            if result and result.status == VerificationStatus.DOESNT_KILL_MUTANT:
                console.print("[dim]This may be an equivalent mutant (semantically identical to original).[/dim]")
            skipped_count += 1

        console.print("─" * 60)

    # Summary
    console.print(Panel.fit(
        f"[bold]Done![/bold]\n"
        f"[green]✓ Killed: {killed_count}[/green]  "
        f"[yellow]Skipped: {skipped_count}[/yellow]  "
        f"[dim]Total: {len(survivors)}[/dim]"
    ))


@app.command("auto")
def auto(
    tool: str = typer.Option("mutmut", "--tool", "-t"),
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
    llm_provider: Optional[str] = typer.Option(None, "--llm"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be written without writing"),
):
    """[bold]Auto-fix[/bold] all survivors without interactive prompts."""
    asyncio.run(_auto_async(tool, project_root, llm_provider, dry_run))


async def _auto_async(tool: str, project_root: Path, llm_provider: Optional[str], dry_run: bool) -> None:
    config = _load_config(project_root)
    config = config.model_copy(update={"auto_write": True})
    if llm_provider:
        config = config.model_copy(update={"llm_provider": llm_provider})

    adapter = _get_adapter(tool, project_root)
    analyzer = MutationAnalyzer()
    llm = LLMClient.from_config(config)
    generator = TestGenerator(llm, config)
    verifier = MutantVerifier(config)
    writer = TestWriter(config)

    survivors = adapter.read_survivors()
    survivors = [analyzer.analyze(m) for m in survivors]

    console.print(f"[bold]Auto-fixing {len(survivors)} survivors...[/bold]\n")

    results: dict[str, int] = {"verified": 0, "failed": 0, "written": 0}

    for mutant in survivors:
        result = None
        with console.status(f"Processing mutant {mutant.id}..."):
            generated = await generator.generate(mutant)

            for attempt in range(config.max_verification_attempts):
                result = verifier.verify(mutant, generated)
                if result.status == VerificationStatus.VERIFIED:
                    break
                if attempt < config.max_verification_attempts - 1:
                    generated = await generator.generate(mutant)

        if result and result.status == VerificationStatus.VERIFIED:
            results["verified"] += 1
            if not dry_run:
                if writer.write(generated, mutant.id):
                    results["written"] += 1
                    console.print(f"[green]✓ {mutant.id}[/green] → {generated.test_function_name}")
            else:
                console.print(f"[blue]DRY-RUN[/blue] {mutant.id} → {generated.test_function_name}")
        else:
            results["failed"] += 1
            status_val = result.status.value if result else "unknown"
            console.print(f"[red]✗ {mutant.id}[/red] → {status_val}")

    console.print(f"\n[bold]Results:[/bold] {results}")


@app.command("report")
def report(
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
    limit: int = typer.Option(20, "--limit", "-n"),
):
    """Show the [bold]audit log[/bold] of all Quell actions."""
    config = _load_config(project_root)

    if not config.audit_log_path.exists():
        console.print("[yellow]No audit log found yet. Run quell fix first.[/yellow]")
        return

    lines = config.audit_log_path.read_text().strip().splitlines()

    table = Table(title="Quell Audit Log")
    table.add_column("Timestamp", style="dim")
    table.add_column("Mutant ID", style="cyan")
    table.add_column("Action", style="yellow")
    table.add_column("File")
    table.add_column("Test Function")

    for line in lines[-limit:]:
        entry = json.loads(line)
        table.add_row(
            entry.get("timestamp", "")[:19],
            entry.get("mutant_id", ""),
            entry.get("action", ""),
            Path(entry.get("file_path", "")).name if entry.get("file_path") else "",
            entry.get("test_function_name", ""),
        )

    console.print(table)


@app.command("init")
def init(
    project_root: Path = typer.Option(Path("."), "--root", "-r"),
):
    """Add [tool.quell] configuration to pyproject.toml."""
    pyproject = project_root / "pyproject.toml"
    if not pyproject.exists():
        console.print("[red]No pyproject.toml found.[/red]")
        raise typer.Exit(1)

    content = pyproject.read_text()
    if "[tool.quell]" in content:
        console.print("[yellow]quell config already exists in pyproject.toml[/yellow]")
        return

    quell_config = """
[tool.quell]
llm_provider = "anthropic"           # "anthropic" | "openai" | "ollama"
llm_model = "claude-sonnet-4-5"
max_verification_attempts = 3
verification_timeout_seconds = 30
auto_write = false                   # set true for CI/CD usage
"""
    pyproject.write_text(content + quell_config)
    console.print("[green]✓ Added [tool.quell] to pyproject.toml[/green]")
    console.print("[dim]Set ANTHROPIC_API_KEY (or OPENAI_API_KEY) in your environment.[/dim]")


if __name__ == "__main__":
    app()
