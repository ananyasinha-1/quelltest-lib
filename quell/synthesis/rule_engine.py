"""
Rule-based test generation. Fast, deterministic, no LLM.
Handles the majority of common cases.

Rule per ConstraintKind:
  MUST_RAISE   → pytest.raises() test with violating input
  BOUNDARY     → test with boundary value (0, -1, etc.)
  ENUM_VALID   → test with invalid enum value
  MUST_RETURN  → test with exact value assertion (not just 'is not None')
  BUG_REPRO    → test that should currently FAIL (bug exists)
  MUTATION     → boundary/comparison test

LLM engine handles: CUSTOM, complex MUTATION, anything rule can't generate.
"""
from __future__ import annotations
import re
from pathlib import Path
from quell.core.models import (
    Requirement, GeneratedTest, ConstraintKind
)


class RuleEngine:
    """Deterministic rule-based test generator. No LLM required."""

    def can_handle(self, req: Requirement) -> bool:
        """Returns True if the rule engine can generate a test for this requirement."""
        return req.constraint_kind in {
            ConstraintKind.MUST_RAISE,
            ConstraintKind.BOUNDARY,
            ConstraintKind.ENUM_VALID,
            ConstraintKind.MUST_RETURN,
            ConstraintKind.BUG_REPRO,
        }

    def generate(self, req: Requirement) -> GeneratedTest | None:
        """Generate a test for the given requirement. Returns None if unsupported."""
        if req.constraint_kind == ConstraintKind.MUST_RAISE:
            return self._must_raise(req)
        if req.constraint_kind == ConstraintKind.BOUNDARY:
            return self._boundary(req)
        if req.constraint_kind == ConstraintKind.ENUM_VALID:
            return self._enum(req)
        if req.constraint_kind == ConstraintKind.MUST_RETURN:
            return self._must_return(req)
        if req.constraint_kind == ConstraintKind.BUG_REPRO:
            return self._bug_repro(req)
        return None

    def _test_file(self, req: Requirement) -> Path:
        return (
            req.target_file.parent.parent / "tests" /
            f"test_{req.target_file.stem}.py"
        )

    def _name(self, req: Requirement) -> str:
        func = re.sub(r'[^a-z0-9_]', '_', req.target_function.lower())
        return f"test_quell_{func}_{req.id}"

    def _must_raise(self, req: Requirement) -> GeneratedTest:
        exc = "Exception"
        if req.expected_behavior:
            m = re.search(r'raises (\w+)', req.expected_behavior)
            if m:
                exc = m.group(1)

        name = self._name(req)
        code = f'''def {name}():
    """
    Quell: {req.description}
    Source: {req.source.value} — {req.raw_spec_text or ""}
    """
    import pytest
    # TODO: call {req.target_function} with input that violates: {req.description}
    # Example: with pytest.raises({exc}):
    #     {req.target_function}(<violating_input>)
    raise NotImplementedError(
        "Complete: call {req.target_function} with invalid input, "
        "assert it raises {exc}"
    )
'''
        return GeneratedTest(
            requirement_id=req.id,
            test_function_name=name,
            test_code=code,
            test_file_path=self._test_file(req),
            explanation=f"pytest.raises({exc}) test for: {req.description}",
            generated_by="rule_engine",
        )

    def _boundary(self, req: Requirement) -> GeneratedTest:
        name = self._name(req)
        boundary_val = "0"
        if "positive" in req.description.lower() or "> 0" in req.description:
            boundary_val = "0"
        elif ">= 1" in req.description or "at least 1" in req.description.lower():
            boundary_val = "0"
        elif "between 0 and 100" in req.description.lower():
            boundary_val = "-1"

        code = f'''def {name}():
    """
    Quell: {req.description}
    Source: {req.source.value} — {req.raw_spec_text or ""}

    Boundary test: the violation is passing value={boundary_val}
    """
    import pytest
    # TODO: call {req.target_function} with boundary value {boundary_val}
    # This should raise an error or return a different result than valid input
    raise NotImplementedError(
        "Complete: call {req.target_function}(<input with {boundary_val} "
        "for the constrained param>), assert it's rejected"
    )
'''
        return GeneratedTest(
            requirement_id=req.id,
            test_function_name=name,
            test_code=code,
            test_file_path=self._test_file(req),
            explanation=f"Boundary test at value={boundary_val}: {req.description}",
            generated_by="rule_engine",
        )

    def _enum(self, req: Requirement) -> GeneratedTest:
        name = self._name(req)
        invalid = "INVALID_VALUE"

        code = f'''def {name}():
    """
    Quell: {req.description}
    Source: {req.source.value} — {req.raw_spec_text or ""}

    Enum test: passing a value NOT in the allowed set should be rejected.
    """
    import pytest
    # TODO: call {req.target_function} with an invalid enum value
    # Example: with pytest.raises((ValueError, ValidationError)):
    #     {req.target_function}(<param>="{invalid}")
    raise NotImplementedError(
        "Complete: pass an invalid value for the enum parameter, "
        "assert it's rejected with an error"
    )
'''
        return GeneratedTest(
            requirement_id=req.id,
            test_function_name=name,
            test_code=code,
            test_file_path=self._test_file(req),
            explanation=f"Enum violation test: {req.description}",
            generated_by="rule_engine",
        )

    def _must_return(self, req: Requirement) -> GeneratedTest:
        name = self._name(req)
        code = f'''def {name}():
    """
    Quell: {req.description}
    Source: {req.source.value} — {req.raw_spec_text or ""}

    Return value test: assert EXACT return value, not just "is not None".
    """
    # TODO: call {req.target_function} with valid inputs
    # result = {req.target_function}(...)
    # assert result is not None
    # assert <specific field or value check>  ← be precise here
    raise NotImplementedError(
        "Complete: call {req.target_function}, assert exact return value"
    )
'''
        return GeneratedTest(
            requirement_id=req.id,
            test_function_name=name,
            test_code=code,
            test_file_path=self._test_file(req),
            explanation=f"Return value test: {req.description}",
            generated_by="rule_engine",
        )

    def _bug_repro(self, req: Requirement) -> GeneratedTest:
        name = self._name(req)
        inputs_hint = str(req.violation_input) if req.violation_input else "<triggering_input>"
        expected = req.expected_behavior or "raise an error or return correct value"

        code = f'''def {name}():
    """
    Quell bug reproduction: {req.description}

    This test should FAIL on current code (bug exists).
    After fixing the bug, this test should PASS.
    Inputs that trigger the bug: {inputs_hint}
    Expected behavior: {expected}
    """
    import pytest
    # TODO: call {req.target_function} with: {inputs_hint}
    # Assert the CORRECT behavior (what SHOULD happen, not what currently happens)
    raise NotImplementedError(
        "Complete: reproduce the bug — call {req.target_function} "
        "with {inputs_hint}, assert {expected}"
    )
'''
        return GeneratedTest(
            requirement_id=req.id,
            test_function_name=name,
            test_code=code,
            test_file_path=self._test_file(req),
            explanation=f"Bug reproduction: {req.description}",
            generated_by="rule_engine",
        )
