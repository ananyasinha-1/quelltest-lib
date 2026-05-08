# quelltest

> Your docstrings say what your code should do. Quell proves it.

[![PyPI](https://img.shields.io/pypi/v/quelltest)](https://pypi.org/project/quelltest/)
[![Python](https://img.shields.io/pypi/pyversions/quelltest)](https://pypi.org/project/quelltest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Quell reads specifications that already exist in your codebase — docstrings, Pydantic models, bug reports — extracts every testable requirement, checks which ones have no test, generates a test for each gap, **proves** the test actually catches violations, then writes it to disk. Every test is verified before it touches your files.

## Why Quell is different

| Tool | Spec source | Verified? |
|------|------------|-----------|
| Qodo Gen | reads implementation | ❌ |
| GitHub Copilot | chat prompt | ❌ |
| Hypothesis | you write it manually | ❌ |
| **Quell** | reads existing specs | ✅ |

**The critical insight:** Qodo reads your implementation and generates tests for what your code *does*. If your code has a bug, Qodo generates tests that bless it. Quell reads your specification (docstring says "must raise ValueError") and generates a test that proves the requirement — catching the bug.

## How it works

```
docstrings + Pydantic models + bug reports
         ↓
   list[Requirement]
         ↓
   Coverage checker (AST scan — no execution)
         ↓
   Rule engine → verified test
         ↓
   Verification: PASS on correct code + FAIL on violated code
         ↓
   libcst injection into test file
```

## Installation

```bash
pip install quelltest
```

Requires Python 3.11+. The CLI command is `quell`.

## Quick start

```bash
# Scan your specs, find gaps
quell check src/

# Generate + verify + write tests for all gaps
quell check src/ --fix

# Reproduce a bug from a description
quell reproduce "payment accepts zero amount"

# Show confidence score for a file
quell prove src/payments.py

# Project-wide Quell Score
quell score --badge
```

## Example

Given this existing code:

```python
def process_payment(request: PaymentRequest) -> dict:
    """
    Process a payment transaction.

    Args:
        request: Amount must be greater than 0. Currency must be one of: USD, EUR, GBP.

    Returns:
        dict with transaction_id, status, amount.

    Raises:
        ValueError: If amount is zero or negative.
    """
```

And this Pydantic model:

```python
class PaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    currency: Literal["USD", "EUR", "GBP"]
```

Running `quell check src/payments.py` finds **5 requirements** with no tests and generates a verified test for each one — before touching your files.

## Configuration

```bash
quell init   # adds [tool.quell] to pyproject.toml
```

```toml
[tool.quell]
llm_provider = "anthropic"          # "anthropic" | "openai" | "ollama"
llm_model    = "claude-sonnet-4-5"
enable_docstring = true
enable_types     = true
enable_mutations = false            # mutmut optional
auto_write       = false
```

Set your LLM API key (only needed for complex/unstructured specs):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

For fully local/offline setup, use Ollama:

```bash
# In pyproject.toml: llm_provider = "ollama"
# ollama pull codellama
```

## Python SDK

```python
from quell import Quell

q = Quell()

# Find requirement gaps
result = q.check("src/")
print(f"Score: {result.score:.0%} | Gaps: {len(result.uncovered)}")

# Reproduce a bug
q.reproduce("payment accepts zero amount silently")

# Project score
score = q.score()
print(f"Project: {score.percentage}%")
```

## Project structure

```
quell/
├── cli.py              # Typer CLI: check, reproduce, prove, score, ci, init
├── sdk.py              # Python API: Quell class
├── spec/               # Spec readers (docstring, type, bug, mutation)
├── core/
│   ├── models.py       # Requirement, ConstraintKind, VerificationResult
│   ├── verifier.py     # THE MOAT — proves every test catches violations
│   └── writer.py       # libcst injection, backup/restore
├── coverage/           # AST-based coverage checker
├── synthesis/          # rule_engine.py + llm_engine.py
├── score/              # Quell Score calculator + SVG badge
└── llm/                # Anthropic / OpenAI / Ollama providers
```

## Development

```bash
git clone https://github.com/shashank7109/quelltest_lib.git
cd quelltest_lib
uv sync --dev

uv run pytest tests/ -v
uv run ruff check . --fix
uv run mypy quell/
```

## Related

- [Docs](https://quell.buildsbyshashank.tech/docs)
- [quell_frontend](https://github.com/shashank7109/quell_frontend) — Next.js website

## License

MIT — see [LICENSE](LICENSE)
