"""All prompt templates for LLM-based test generation."""
from quell.core.models import Requirement


def build_prompt(req: Requirement) -> str:
    """Build a structured prompt for LLM test generation."""
    return f"""You are an expert Python test engineer. Write a pytest test function that PROVES a specific requirement holds.

REQUIREMENT:
  Description: {req.description}
  Type: {req.constraint_kind.value}
  Function: {req.target_function}
  File: {req.target_file.name}
  Source spec: {req.raw_spec_text or "not available"}
  Violation input: {req.violation_input or "infer from description"}
  Expected behavior: {req.expected_behavior or "infer from description"}

RULES FOR YOUR TEST:
1. Function name MUST start with test_quell_
2. Must PASS on correct code that satisfies the requirement
3. Must FAIL when the requirement is violated
4. Use SPECIFIC assertions — never "assert result is not None" alone
5. For raises requirements: use pytest.raises(ExceptionType)
6. Add a docstring explaining what requirement this proves

Output ONLY a Python code block. No explanation outside the block.

```python
def test_quell_{req.target_function}_{req.id}():
    \"\"\"Proves: {req.description}\"\"\"
    # your test here
```"""
