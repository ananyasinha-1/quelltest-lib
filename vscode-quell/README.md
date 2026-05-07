# Quell — Mutation Score (VS Code Extension)

Inline mutation score warnings and verified test fixes powered by [Quell](https://quell.build).

## What it does

- **Status bar** — shows the current file's mutation score (e.g. `✓ Quell 87% (A)`)
- **Inline decorations** — annotates every `def` and `class` with its score
- **Warning highlight** — turns red when score drops below your threshold (default 60%)
- **Commands** — repair weak tests, fix survivors, scan for mutants — all from the command palette

## Requirements

- Python 3.11+
- `quelltest` installed: `pip install quelltest`
- `mutmut` run at least once: `mutmut run`

## Setup

1. Install the extension from the VS Code Marketplace
2. Install Quell in your project's Python environment:
   ```bash
   pip install quelltest
   ```
3. Run mutation testing once to build the cache:
   ```bash
   mutmut run
   ```
4. Open a Python file — the score appears in the status bar automatically.

## Commands

| Command | Description |
|---------|-------------|
| `Quell: Show Mutation Score` | Refresh and show score for current file |
| `Quell: Repair Current File` | Run `quell repair` in the integrated terminal |
| `Quell: Fix All Survivors` | Run `quell auto` to batch-fix all survivors |
| `Quell: Scan for Survivors` | Run `quell scan` to list surviving mutants |

## Settings

| Setting | Default | Description |
|---------|---------|-------------|
| `quell.pythonPath` | `""` | Path to Python interpreter. Leave empty to auto-detect. |
| `quell.autoRefresh` | `true` | Refresh score on file save. |
| `quell.showInlineDecorations` | `true` | Show score annotations on `def`/`class` lines. |
| `quell.threshold` | `0.6` | Score below this value triggers a warning (0–1). |

## Score colours

| Grade | Score | Colour |
|-------|-------|--------|
| A | ≥ 80% | Green |
| B | 60–79% | Yellow |
| C | 40–59% | Orange |
| F | < 40% | Red |

## Links

- [Quell docs](https://quell.build/docs)
- [GitHub Actions setup](https://quell.build/docs/github-actions)
- [PyPI](https://pypi.org/project/quelltest/)
