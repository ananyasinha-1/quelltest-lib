"""
Reads mutation testing results → MUTATION Requirements.

This is OPTIONAL. Quell works without mutmut or Stryker.
Enable with: enable_mutations = true in [tool.quell]

mutmut 3.x IMPORTANT NOTES:
- Version 3.5.0+ (Feb 2026), completely different from 2.x
- Requires Linux/Mac (NOT Windows — WSL only)
- Stores results in .mutmut-cache (SQLite)
- ALWAYS inspect schema at runtime: sqlite3 .mutmut-cache ".schema"
- Do NOT hardcode column names — they vary between versions
- mutmut-mcp (wdm0006/mutmut-mcp) already exists as MCP server for
  running mutation tests. Quell is DOWNSTREAM — we fix what mutmut finds.

Stryker: stable JSON schema, safe to parse directly.
"""
from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path

from quell.core.models import ConstraintKind, Requirement, SpecSource


class MutmutReader:
    """
    Reads mutmut 3.x survivors from .mutmut-cache SQLite.
    Windows users: mutmut requires WSL. Recommend using docstring/type
    readers instead which work natively on all platforms.
    """

    def __init__(self, project_root: Path = Path(".")):
        self.project_root = project_root
        self.db_path = project_root / ".mutmut-cache"

    def read(self, file_path: Path) -> list[Requirement]:
        """Read survivors for a specific file."""
        return [
            r for r in self.read_all()
            if r.target_file == file_path.resolve()
        ]

    def read_all(self) -> list[Requirement]:
        """Read all survived mutants from the cache."""
        if not self.db_path.exists():
            return []
        try:
            conn = sqlite3.connect(self.db_path)

            # Inspect schema at runtime — never hardcode
            tables = [
                t[0] for t in conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            ]
            table = next(
                (t for t in ["MutantStatus", "mutants", "Mutant"] if t in tables),
                None,
            )
            if not table:
                conn.close()
                return []

            cols = [
                c[1] for c in
                conn.execute(f"PRAGMA table_info({table})").fetchall()
            ]
            rows = conn.execute(f"SELECT * FROM {table}").fetchall()
            conn.close()

            reqs = []
            for row in rows:
                d = dict(zip(cols, row))
                if "survived" not in str(d.get("status", "")).lower():
                    continue
                file_str = (
                    d.get("source_path") or d.get("file") or
                    d.get("filename") or "unknown"
                )
                reqs.append(Requirement(
                    id=str(d.get("id", uuid.uuid4()))[:8],
                    description=f"mutation survived: {d.get('mutation', '')}",
                    constraint_kind=ConstraintKind.MUTATION,
                    source=SpecSource.MUTATION,
                    target_function=str(d.get("function", "unknown")),
                    target_file=Path(file_str),
                    raw_spec_text=str(d.get("mutation", "")),
                ))
            return reqs
        except Exception:
            return []

    @property
    def source_name(self) -> str:
        """Reader name."""
        return "mutation"


class StrykerReader:
    """Reads Stryker mutation-report.json. Schema is stable."""

    def __init__(
        self,
        report_path: Path = Path("reports/mutation/mutation.json"),
    ):
        self.report_path = report_path

    def read(self, file_path: Path) -> list[Requirement]:
        """Read Stryker survivors for a specific file."""
        if not self.report_path.exists():
            return []
        try:
            data = json.loads(self.report_path.read_text())
            reqs = []
            for fp_str, fd in data.get("files", {}).items():
                if Path(fp_str).resolve() != file_path.resolve():
                    continue
                for m in fd.get("mutants", []):
                    if m.get("status") != "Survived":
                        continue
                    reqs.append(Requirement(
                        id=str(m["id"])[:8],
                        description=f"mutation survived: {m.get('mutatorName', '')}",
                        constraint_kind=ConstraintKind.MUTATION,
                        source=SpecSource.MUTATION,
                        target_function="unknown",
                        target_file=file_path.resolve(),
                        raw_spec_text=m.get("replacement", ""),
                    ))
            return reqs
        except Exception:
            return []

    @property
    def source_name(self) -> str:
        """Reader name."""
        return "stryker"
