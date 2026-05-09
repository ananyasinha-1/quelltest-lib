"""
PySpark schema reader.
Reads StructType definitions via AST — no PySpark imports, no SparkSession.
Returns [] on any error — never raises.

Detects:
  schema = StructType([StructField("col", FloatType(), nullable=False)])
  return StructType([...])  inside a function
  self.schema = StructType([...])

Produces two Requirement kinds per field:
  NOT_NULL   → when nullable=False
  TYPE_CHECK → always (column must match declared type)
"""
from __future__ import annotations

import ast
import uuid
from pathlib import Path

from quell.core.models import ConstraintKind, Requirement, SpecSource


class PySparkReader:
    """Extracts Requirements from PySpark StructType schema definitions."""

    def read(self, file_path: Path) -> list[Requirement]:
        """Read file and extract Requirements from PySpark schemas."""
        try:
            source = file_path.read_text(encoding="utf-8")
            if "StructType" not in source:
                return []  # fast exit — no PySpark in this file
            tree = ast.parse(source)
        except Exception:
            return []

        reqs: list[Requirement] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Assign):
                if self._is_struct_type(node.value):
                    fields = self._parse_fields(node.value)  # type: ignore[arg-type]
                    ctx = self._enclosing_function(node, tree) or "module_schema"
                    reqs.extend(self._to_requirements(fields, ctx, file_path))

            if isinstance(node, ast.Return) and node.value:
                if self._is_struct_type(node.value):
                    fields = self._parse_fields(node.value)  # type: ignore[arg-type]
                    ctx = self._enclosing_function(node, tree) or "schema"
                    reqs.extend(self._to_requirements(fields, ctx, file_path))

        return reqs

    def _is_struct_type(self, node: ast.expr) -> bool:
        if not isinstance(node, ast.Call):
            return False
        f = node.func
        return (
            (isinstance(f, ast.Name) and f.id == "StructType") or
            (isinstance(f, ast.Attribute) and f.attr == "StructType")
        )

    def _parse_fields(self, struct_node: ast.Call) -> list[dict]:  # type: ignore[type-arg]
        fields: list[dict] = []  # type: ignore[type-arg]
        if not struct_node.args:
            return fields
        first = struct_node.args[0]
        if not isinstance(first, ast.List):
            return fields

        for elt in first.elts:
            if not isinstance(elt, ast.Call):
                continue
            f = elt.func
            is_sf = (
                (isinstance(f, ast.Name) and f.id == "StructField") or
                (isinstance(f, ast.Attribute) and f.attr == "StructField")
            )
            if not is_sf or len(elt.args) < 2:
                continue
            name_node = elt.args[0]
            if not isinstance(name_node, ast.Constant) or not isinstance(name_node.value, str):
                continue

            name = name_node.value
            type_name = self._type_name(elt.args[1])
            nullable = True

            if len(elt.args) >= 3 and isinstance(elt.args[2], ast.Constant):
                nullable = bool(elt.args[2].value)
            for kw in elt.keywords:
                if kw.arg == "nullable" and isinstance(kw.value, ast.Constant):
                    nullable = bool(kw.value.value)

            fields.append({"name": name, "type": type_name, "nullable": nullable})

        return fields

    def _type_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                return f.id
            if isinstance(f, ast.Attribute):
                return f.attr
        if isinstance(node, ast.Name):
            return node.id
        return "UnknownType"

    def _to_requirements(
        self, fields: list[dict], context: str, file_path: Path  # type: ignore[type-arg]
    ) -> list[Requirement]:
        reqs: list[Requirement] = []
        for f in fields:
            name, type_name, nullable = f["name"], f["type"], f["nullable"]
            if not nullable:
                reqs.append(Requirement(
                    id=str(uuid.uuid4())[:8],
                    description=f"column '{name}' must not be null (nullable=False)",
                    constraint_kind=ConstraintKind.NOT_NULL,
                    source=SpecSource.PYSPARK,
                    target_function=context,
                    target_file=file_path,
                    raw_spec_text=f"StructField('{name}', {type_name}(), nullable=False)",
                    violation_input={"column": name, "type": type_name},
                ))
            reqs.append(Requirement(
                id=str(uuid.uuid4())[:8],
                description=f"column '{name}' must be {type_name}",
                constraint_kind=ConstraintKind.TYPE_CHECK,
                source=SpecSource.PYSPARK,
                target_function=context,
                target_file=file_path,
                raw_spec_text=f"StructField('{name}', {type_name}())",
                violation_input={"column": name, "type": type_name},
            ))
        return reqs

    def _enclosing_function(self, target: ast.AST, tree: ast.AST) -> str | None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for child in ast.walk(node):
                    if child is target:
                        return node.name
        return None

    @property
    def source_name(self) -> str:
        """Reader name."""
        return "pyspark"
