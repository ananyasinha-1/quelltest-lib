# Configuration Reference

Quell is configured via `[tool.quell]` in `pyproject.toml` or `quell.toml`.

Run `quell init` to add the default configuration block.

## Options

| Key | Default | Description |
|-----|---------|-------------|
| `llm_provider` | `"anthropic"` | LLM provider: `"anthropic"`, `"openai"`, or `"ollama"` |
| `llm_model` | `"claude-sonnet-4-5"` | Model name for the LLM provider |
| `ollama_base_url` | `"http://localhost:11434"` | Base URL for Ollama server |
| `max_verification_attempts` | `3` | Max attempts to generate a verified killing test |
| `verification_timeout_seconds` | `30` | Timeout for each pytest run |
| `auto_write` | `false` | If `true`, writes without interactive prompt |
| `test_file_pattern` | `"tests/test_{source_file}.py"` | Pattern for test file discovery |
| `audit_log_path` | `".quell/audit.jsonl"` | Path to the audit log |
| `backup_dir` | `".quell/backups"` | Directory for source file backups |

## Example

```toml
[tool.quell]
llm_provider = "anthropic"
llm_model = "claude-sonnet-4-5"
max_verification_attempts = 3
verification_timeout_seconds = 30
auto_write = false
```

## Environment Variables

- `ANTHROPIC_API_KEY` — required for Anthropic provider
- `OPENAI_API_KEY` — required for OpenAI provider
- Ollama requires no API key (runs locally)
