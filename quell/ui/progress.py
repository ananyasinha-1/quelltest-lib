"""Progress bars and spinners for Quell UI."""
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn


def make_progress() -> Progress:
    """Create a Rich progress bar with spinner."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
    )
