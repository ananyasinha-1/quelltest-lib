# quelltest

> Auto-generate verified killing tests for survived mutants from mutmut and Stryker.

[![PyPI](https://img.shields.io/pypi/v/quelltest)](https://pypi.org/project/quelltest/)
[![Python](https://img.shields.io/pypi/pyversions/quelltest)](https://pypi.org/project/quelltest/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Quell reads your mutation testing results, generates pytest assertions that kill each surviving mutant, verifies them, and injects them directly into your test files — without touching your formatting.

## How it works

1. **Scan** — reads `.mutmut-cache` or Stryker JSON. Finds all survived mutants.
2. **Generate** — deterministic rule-based generators handle 9 operator types. No LLM call needed for the common cases.
3. **Verify** — every generated test runs against the live mutant in isolation. Tests that don't kill are discarded.
4. **Inject** — verified tests are written using libcst, a lossless concrete syntax tree parser. Comments, spacing, and formatting are preserved exactly. Source files are backed up first.

## Installation

```bash
pip install quelltest
```

Requires Python 3.11+.

## Quick start

```bash
# Run your mutation tool first
mutmut run
# or
npx stryker run --reporters=json

# Scan survived mutants
quell scan --source mutmut

# Generate and inject killing tests
quell fix

# Preview without writing
quell fix --dry-run

# Auto-fix all without prompts
quell auto
```

## Supported mutation operators

Nine operators have deterministic rule-based generators — no network call required:

| Operator | Example |
|----------|---------|
| `BOUNDARY_SHIFT` | `>` → `>=` |
| `ARITHMETIC_OP` | `+` → `-` |
| `LOGICAL_OP` | `and` → `or` |
| `COMPARISON_OP` | `==` → `!=` |
| `RETURN_VALUE` | `return x` → `return None` |
| `STATEMENT_DEL` | statement removed |
| `CONSTANT_MUTATION` | `0` → `1` |
| `DECORATOR_REMOVAL` | decorator stripped |
| `COLLECTION_OP` | `append` → `remove` |

`UNKNOWN` operators fall back to an LLM if a provider is configured.

## Configuration

```bash
quell init   # adds [tool.quell] to pyproject.toml
```

```toml
[tool.quell]
llm_provider = "anthropic"         # "anthropic" | "openai" | "ollama"
llm_model    = "claude-sonnet-4-6"
max_verification_attempts   = 3
verification_timeout_seconds = 30
auto_write = false
```

Set your LLM API key (only needed for UNKNOWN operators):

```bash
export ANTHROPIC_API_KEY=sk-ant-...
# or
export OPENAI_API_KEY=sk-...
```

For a fully local/offline setup, use Ollama:

```bash
quell fix --llm ollama   # requires ollama running locally
```

## Privacy

- Your code is never sent to any server unless you configure an LLM provider.
- LLM is called only for `UNKNOWN` operators — the rule engine handles everything else.
- All source file mutations are done locally in a subprocess and reverted afterwards.

## Adapters

| Tool | Format | Status |
|------|--------|--------|
| mutmut | `.mutmut-cache` (SQLite) | ✅ Supported |
| Stryker (JS/TS) | `reports/mutation/mutation.json` | ✅ Supported |
| PIT (Java) | XML | 🔜 Planned |

## Project structure

```
quell/
├── cli.py              # Typer CLI entry point
├── adapters/           # mutmut + Stryker result parsers
├── core/
│   ├── analyzer.py     # classifies mutation operators from AST diffs
│   ├── generator.py    # rule-based test generators for 9 operators
│   ├── verifier.py     # runs tests against live mutants in subprocess
│   └── writer.py       # libcst-based test file injection
├── llm/                # LLM client + Anthropic / OpenAI / Ollama providers
└── ui/                 # Rich terminal UI (progress, diffs, console)
```

## Development

```bash
# Clone and install
git clone https://github.com/shashank7109/quelltest_lib.git
cd quelltest_lib
uv sync

# Run tests
uv run pytest tests/ -v

# Lint
uv run ruff check . --fix
```

## Related

- [quell_frontend](https://github.com/shashank7109/quell_frontend) — Next.js dashboard
- [quell_backend](https://github.com/shashank7109/quell_backend) — FastAPI backend

## License

MIT — see [LICENSE](LICENSE)
