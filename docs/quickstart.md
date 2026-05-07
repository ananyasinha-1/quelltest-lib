# Quick Start

## Prerequisites

- Python 3.11+
- mutmut or Stryker installed and run on your project

## Installation

```bash
pip install quell
```

## Step 1: Run mutation testing

```bash
# Python
mutmut run

# JavaScript/TypeScript
npx stryker run --reporters=json
```

## Step 2: Scan survivors

```bash
quell scan
```

## Step 3: Fix interactively

```bash
quell fix
```

## Step 4: Auto-fix

```bash
quell auto --dry-run  # preview first
quell auto            # apply all
```

## Configuration

```bash
quell init  # adds [tool.quell] to pyproject.toml
```
