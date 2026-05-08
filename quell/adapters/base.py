"""Base protocol for all mutation adapters."""
from __future__ import annotations

from typing import Protocol

from quell.core.models import SurvivedMutant


class MutationAdapter(Protocol):
    """Protocol that all mutation adapters must implement."""

    def read_survivors(self) -> list[SurvivedMutant]:
        """Return all survived mutants from the mutation testing run."""
        ...
