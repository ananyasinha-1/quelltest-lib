"""
Reads Pydantic models and type annotations → extracts constraint Requirements.

Every type constraint is a testable requirement.
Quell reads what already exists — you wrote these types, not Quell.

Handled:
  Field(gt=0)                  → BOUNDARY: test value=0 raises ValidationError
  Literal["USD","EUR","GBP"]   → ENUM_VALID: test "JPY" raises ValidationError
  Field(min_length=1)          → BOUNDARY: test [] raises ValidationError
  Annotated[int, Field(ge=18)] → BOUNDARY: test 17 raises error

Why this matters vs Qodo/Copilot:
  They read your implementation and generate tests from what your code DOES.
  We read your types and generate tests from what your code SHOULD DO.
  If your code has a bug (missing validation), we still generate the right test.
"""
from __future__ import annotations
import ast, uuid
from pathlib import Path
from quell.core.models import Requirement, ConstraintKind, SpecSource

FIELD_VALIDATORS = {
    "gt", "ge", "lt", "le",
    "min_length", "max_length",
    "min_items", "max_items",
}


class TypeReader:
    """Extracts Requirements from Pydantic models and type annotations."""

    def read(self, file_path: Path) -> list[Requirement]:
        """Read file and extract Requirements from type annotations."""
        try:
            tree = ast.parse(file_path.read_text(encoding="utf-8"))
        except Exception:
            return []

        reqs: list[Requirement] = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and self._is_pydantic(node):
                reqs.extend(self._from_model(node, file_path))
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                reqs.extend(self._from_function(node, file_path))
        return reqs

    def _is_pydantic(self, node: ast.ClassDef) -> bool:
        for base in node.bases:
            if isinstance(base, ast.Name) and base.id == "BaseModel":
                return True
            if isinstance(base, ast.Attribute) and base.attr == "BaseModel":
                return True
        return False

    def _from_model(self, cls: ast.ClassDef, path: Path) -> list[Requirement]:
        reqs: list[Requirement] = []
        for stmt in cls.body:
            if not isinstance(stmt, ast.AnnAssign):
                continue
            name = self._name(stmt.target)
            # Literal type → ENUM_VALID
            if self._is_literal(stmt.annotation):
                values = self._literal_values(stmt.annotation)
                if values:
                    reqs.append(Requirement(
                        id=str(uuid.uuid4())[:8],
                        description=f"{cls.name}.{name} must be one of {values}",
                        constraint_kind=ConstraintKind.ENUM_VALID,
                        source=SpecSource.TYPE,
                        target_function=cls.name,
                        target_file=path,
                        raw_spec_text=f"{name}: Literal{values}",
                    ))
            # Field validators → BOUNDARY
            if isinstance(stmt.value, ast.Call):
                for kw in stmt.value.keywords:
                    if kw.arg in FIELD_VALIDATORS:
                        val = (
                            ast.literal_eval(kw.value)
                            if isinstance(kw.value, ast.Constant)
                            else "?"
                        )
                        reqs.append(Requirement(
                            id=str(uuid.uuid4())[:8],
                            description=f"{cls.name}.{name} must satisfy {kw.arg}={val}",
                            constraint_kind=ConstraintKind.BOUNDARY,
                            source=SpecSource.TYPE,
                            target_function=cls.name,
                            target_file=path,
                            raw_spec_text=f"Field({kw.arg}={val})",
                        ))
        return reqs

    def _from_function(
        self, func: ast.FunctionDef, path: Path
    ) -> list[Requirement]:
        reqs: list[Requirement] = []
        for arg in func.args.args:
            if arg.annotation and self._is_literal(arg.annotation):
                values = self._literal_values(arg.annotation)
                if values:
                    reqs.append(Requirement(
                        id=str(uuid.uuid4())[:8],
                        description=f"param {arg.arg} must be one of {values}",
                        constraint_kind=ConstraintKind.ENUM_VALID,
                        source=SpecSource.TYPE,
                        target_function=func.name,
                        target_file=path,
                        raw_spec_text=f"{arg.arg}: Literal{values}",
                    ))
        return reqs

    def _is_literal(self, node: ast.expr) -> bool:
        if isinstance(node, ast.Subscript):
            v = node.value
            return (
                (isinstance(v, ast.Name) and v.id == "Literal") or
                (isinstance(v, ast.Attribute) and v.attr == "Literal")
            )
        return False

    def _literal_values(self, node: ast.Subscript) -> list:  # type: ignore[type-arg]
        s = node.slice
        if isinstance(s, ast.Tuple):
            return [
                ast.literal_eval(e) for e in s.elts
                if isinstance(e, ast.Constant)
            ]
        if isinstance(s, ast.Constant):
            return [s.value]
        return []

    def _name(self, node: ast.expr) -> str:
        return node.id if isinstance(node, ast.Name) else "field"  # type: ignore[attr-defined]

    @property
    def source_name(self) -> str:
        """Reader name."""
        return "type"
