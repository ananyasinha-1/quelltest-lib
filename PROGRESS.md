# Quell — Implementation Progress

> This file is kept up-to-date after each work session so any AI tool or
> developer can pick up exactly where work left off.

---

## Completed Phases

### P1 — Core (done)

| Feature | Files | Status |
|---------|-------|--------|
| mutmut 3.x adapter | `quell/adapters/mutmut_adapter.py` | ✅ |
| `quell ci` command | `quell/ci/`, `quell/cli.py` | ✅ |
| `quell score` command | `quell/score/`, `quell/cli.py` | ✅ |
| Badge generation | `quell/score/badge.py` | ✅ |
| Score history tracker | `quell/score/tracker.py` | ✅ |
| pyproject.toml v0.2.0 | `pyproject.toml` | ✅ |

### P2 — Extensions (done)

| Feature | Files | Status |
|---------|-------|--------|
| `quell repair` command | `quell/repair/`, `quell/cli.py` | ✅ |
| `quell-mcp` MCP server | `quell/mcp_server.py` | ✅ |
| `quell.sdk.Quell` SDK class | `quell/sdk.py` | ✅ |
| Tests for ci/ and score/ | `tests/ci/`, `tests/score/` | ✅ |

### P3 — Integrations (done)

| Feature | Files | Status |
|---------|-------|--------|
| GitHub PR comment formatter | `quell/github/formatter.py` | ✅ |
| GitHub PR commenter (API) | `quell/github/pr_commenter.py` | ✅ |
| GitHub App auth (JWT) | `quell/github/auth.py` | ✅ |
| GitHub App webhook server | `quell/github/app.py` | ✅ |
| `quell github-comment` CLI | `quell/cli.py` | ✅ |
| GitHub Actions template | `docs/github-actions.yml` | ✅ |
| VS Code extension scaffold | `vscode-quell/` | ✅ |
| PyPI publish (v0.3.0) | `dist/quelltest-0.3.0*` | ✅ |

---

## Current Test Coverage

```
105 tests — 0 failures
tests/adapters/   10 tests   mutmut v2+v3 adapter, Stryker adapter
tests/ci/          8 tests   diff_parser (line ranges, multi-hunk, edge cases)
tests/score/      20 tests   calculator (SQLite schema), badge (SVG/color/threshold)
tests/unit/       67 tests   analyzer, generator, verifier, writer
```

Run: `uv run pytest tests/ -v`

---

## PyPI

Package: `quelltest` — `pip install quelltest`
Published: v0.1.0 → v0.2.0 → v0.3.0

Install extras:
```bash
pip install quelltest[mcp]     # MCP server for AI agents
pip install quelltest[github]  # GitHub App + PR commenter
```

---

## VS Code Extension

Location: `vscode-quell/`
Status: Scaffolded — TypeScript source complete, NOT yet published to Marketplace.

To publish (requires `vsce` and a Marketplace publisher account):
```bash
cd vscode-quell
npm install
npm run compile
npx vsce package        # produces vscode-quell-0.1.0.vsix
npx vsce publish        # needs VSCE_PAT env var
```

To test locally:
```bash
code --install-extension vscode-quell-0.1.0.vsix
```

---

## GitHub App (quell.build)

Location: `quell/github/app.py`
Status: Code complete — NOT yet deployed.

To deploy on Render:
1. Create a new Web Service pointing to the library repo
2. Start command: `quell-github-app`
3. Set env vars: `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`
4. Point GitHub App webhook URL to: `https://quell.build/github/webhook`

GitHub App setup (https://github.com/settings/apps/new):
- Name: Quell
- Homepage: https://quell.build
- Webhook URL: https://quell.build/github/webhook
- Permissions: Pull requests (read/write), Contents (read)
- Events: Pull request

---

## Pending Phases

### P4 — Cloud (not started)

- [ ] Badge hosting at `https://quell.build/badge/{user}/{repo}`
- [ ] Team dashboard — mutation score trends over time
- [ ] Enterprise: SSO, audit logs, air-gapped mode

### P5 — Autonomous (not started)

- [ ] Auto-detect when code changes break mutation score, auto-fix
- [ ] PIT adapter (Java via XML report)
- [ ] IDE-native real-time mutation feedback (LSP or extension)

---

## Known Limitations / TODOs

- VS Code extension needs to be compiled (`npm run compile`) and published to Marketplace
- GitHub App webhook server needs deployment to quell.build (Render/Fly.io)
- `quell repair` re-runs mutmut from scratch if no cache; slow on large projects
- mutmut 3.x does NOT run on Windows without WSL; adapter handles gracefully
- `quell/sdk.py` `_fix_all_async` has a redundant `MutmutAdapter` import — harmless

---

## Architecture Invariants (never change these)

1. `verifier.py` — ALWAYS restore source files in a `finally` block
2. `writer.py` — ALWAYS backup before writing, ALWAYS restore on failure
3. `writer.py` — ALWAYS validate CST parse before writing to disk
4. No source code sent to any server unless LLM provider configured
5. LLM only called for `UNKNOWN` operators — rule engine handles everything else
6. Verification runs in subprocess (never in-process) so mutations load fresh
