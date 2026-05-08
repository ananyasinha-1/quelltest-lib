"""Base protocol for all spec readers."""
from __future__ import annotations
from pathlib import Path
from typing import Protocol
from quell.core.models import Requirement


class SpecReader(Protocol):
    """All spec readers implement this interface."""

    def read(self, file_path: Path) -> list[Requirement]:
        """Read a file and return extracted Requirements. Never raises."""
        ...

    @property
    def source_name(self) -> str:
        """Human-readable name for this reader."""
        ...
