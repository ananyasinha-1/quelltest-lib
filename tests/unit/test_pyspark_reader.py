"""Tests for PySparkReader AST parsing."""
from __future__ import annotations

import tempfile
from pathlib import Path

from quell.core.models import ConstraintKind, SpecSource
from quell.spec.pyspark_reader import PySparkReader

SAMPLE = '''
from pyspark.sql.types import StructType, StructField, FloatType, StringType

payment_schema = StructType([
    StructField("amount",   FloatType(),  nullable=False),
    StructField("currency", StringType(), nullable=True),
])
'''

SAMPLE_IN_FUNC = '''
from pyspark.sql.types import StructType, StructField, LongType, StringType

def get_schema():
    return StructType([
        StructField("user_id",  LongType(),   nullable=False),
        StructField("name",     StringType(), nullable=True),
    ])
'''


def _write_tmp(content: str) -> Path:
    f = tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False)
    f.write(content)
    f.close()
    return Path(f.name)


def test_reads_not_null_requirement() -> None:
    path = _write_tmp(SAMPLE)
    reqs = PySparkReader().read(path)
    not_null = [r for r in reqs if r.constraint_kind == ConstraintKind.NOT_NULL]
    assert len(not_null) == 1
    assert "amount" in not_null[0].description
    assert not_null[0].source == SpecSource.PYSPARK


def test_reads_type_check_for_all_fields() -> None:
    path = _write_tmp(SAMPLE)
    reqs = PySparkReader().read(path)
    type_checks = [r for r in reqs if r.constraint_kind == ConstraintKind.TYPE_CHECK]
    assert len(type_checks) == 2  # both fields


def test_nullable_true_field_has_no_not_null_req() -> None:
    path = _write_tmp(SAMPLE)
    reqs = PySparkReader().read(path)
    not_null = [r for r in reqs if r.constraint_kind == ConstraintKind.NOT_NULL]
    # Only "amount" is nullable=False; "currency" is nullable=True
    assert all("amount" in r.description for r in not_null)


def test_reads_schema_inside_function() -> None:
    path = _write_tmp(SAMPLE_IN_FUNC)
    reqs = PySparkReader().read(path)
    assert len(reqs) > 0
    assert any("user_id" in r.description for r in reqs)


def test_returns_empty_for_non_pyspark_file() -> None:
    path = _write_tmp("def foo(): pass\n")
    assert PySparkReader().read(path) == []


def test_never_raises() -> None:
    assert PySparkReader().read(Path("/nonexistent/file.py")) == []


def test_violation_input_contains_column_and_type() -> None:
    path = _write_tmp(SAMPLE)
    reqs = PySparkReader().read(path)
    not_null = [r for r in reqs if r.constraint_kind == ConstraintKind.NOT_NULL][0]
    assert not_null.violation_input is not None
    assert not_null.violation_input["column"] == "amount"
    assert "FloatType" in not_null.violation_input["type"]
