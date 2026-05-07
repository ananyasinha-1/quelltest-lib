# Quell

> *Quell your survivors. Strengthen your tests.*

Quell auto-generates verified, killing tests for survived mutants from mutmut and Stryker.

## What it does

Quell reads surviving mutants from mutation testing tools (mutmut for Python, Stryker for JS/TS), analyzes each surviving mutant using Python's AST (via libcst), generates a targeted pytest assertion that would catch the mutation, verifies the generated test actually kills the mutant by applying the mutant and running the test in a subprocess, then writes only verified tests to the test file using libcst (preserving formatting and comments).

- Code never leaves the machine (unless you configure an LLM provider)
- Every write is auto-restored on failure
- Full audit log is maintained

## Installation

```bash
pip install quell
```

## Quick Start

```bash
# Step 1: Run your mutation testing tool first
mutmut run                          # for Python projects
npx stryker run --reporters=json    # for JS/TS projects

# Step 2: Let quell scan survivors
quell scan                          # see what survived

# Step 3: Fix interactively
quell fix                           # review + apply one by one

# Step 4: Or auto-fix everything
quell auto --dry-run                # preview
quell auto                          # apply all verified tests

# Config (optional)
quell init                          # adds [tool.quell] to pyproject.toml

# Use local LLM (privacy-first)
quell fix --llm ollama              # requires ollama running locally
```

## Configuration

Add `[tool.quell]` to your `pyproject.toml`:

```toml
[tool.quell]
llm_provider = "anthropic"           # "anthropic" | "openai" | "ollama"
llm_model = "claude-sonnet-4-5"
max_verification_attempts = 3
verification_timeout_seconds = 30
auto_write = false
```

Set your API key:

```bash
export ANTHROPIC_API_KEY=sk-...
# or
export OPENAI_API_KEY=sk-...
```

## License

MIT
