"""Colored diff display for Quell UI."""
from rich.console import Console
from rich.text import Text


def print_diff(original: str, mutated: str, console: Console | None = None) -> None:
    """Print a colored diff between original and mutated code."""
    if console is None:
        from quell.ui.console import console as _console
        console = _console

    text = Text()
    text.append("- ", style="red")
    text.append(original.strip(), style="red")
    text.append("\n")
    text.append("+ ", style="green")
    text.append(mutated.strip(), style="green")
    console.print(text)
