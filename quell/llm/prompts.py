"""
Prompt templates for LLM-based test generation.
Used when rule-based generation is not sufficient (UNKNOWN operator, complex mutations).
"""
from quell.core.models import SurvivedMutant


def build_test_generation_prompt(mutant: SurvivedMutant) -> str:
    """Build a structured prompt for test generation."""

    existing_tests_section = ""
    if mutant.existing_tests:
        existing_tests_section = f"""
EXISTING TESTS IN THE FILE:
{chr(10).join(f"- {t}" for t in mutant.existing_tests[:10])}

Follow the same testing style and import patterns as the existing tests.
"""

    function_section = ""
    if mutant.function_source:
        function_section = f"""
ENCLOSING FUNCTION SOURCE CODE:
```python
{mutant.function_source}
```
"""

    return f"""You are a Python testing expert. Your job is to write a single pytest test function that KILLS a specific surviving mutant.

A "surviving mutant" means: the mutation testing tool changed a line of code, but your existing tests still passed. This means your tests have a gap.

MUTATION DETAILS:
- File: {mutant.file_path}
- Line: {mutant.line_start}
- Original code: {mutant.original_code}
- Mutated code:  {mutant.mutated_code}
- Mutation type: {mutant.operator.value}
{function_section}
{existing_tests_section}

YOUR TASK:
Write a pytest test function called `test_quell_{mutant.function_name or "function"}_{mutant.id}` that:
1. Calls the function with specific inputs
2. Asserts a SPECIFIC expected output (not "assert result is not None" or "assert result > 0")
3. Would PASS on the original code
4. Would FAIL on the mutated code (catching the mutation)

RULES:
- Output ONLY a Python code block with the test function
- No imports needed (assume pytest and the module under test are available)
- No explanations outside the code block
- The assertion must be specific enough to distinguish original from mutant
- Add a docstring explaining WHY this test kills the mutant

```python
def test_quell_{mutant.function_name or "function"}_{mutant.id}():
    \"\"\"Kills mutant {mutant.id}: {mutant.original_code.strip()} → {mutant.mutated_code.strip()}\"\"\"
    # Your test here
```
"""
