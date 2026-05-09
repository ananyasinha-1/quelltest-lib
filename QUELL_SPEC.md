# Quell — Agent Spec (v0.4.4)

> Accurate description of what Quell currently does. Read before editing code.
> For aspirational architecture and positioning, see CLAUDE.md.

---

## What Quell Is

**Package:** `pip install quelltest` | **CLI command:** `quell` | **Version:** 0.4.4

**Tagline:** "Your docstrings say what your code should do. Quell proves it."

Quell reads specifications already in your codebase (docstrings, Pydantic models, bug reports), extracts every testable requirement, checks which have no test, generates a real callable test for each gap, **proves the test actually catches violations** (two-phase verification), then writes it to disk. Every written test is guaranteed to both pass on correct code and fail when the requirement is violated.

---

## The Full Pipeline

```
1. SPEC READERS  (quell/spec/)
   ├── DocstringReader   → parses Google-style docstrings → Requirement list
   ├── TypeReader        → parses Pydantic Field/Literal annotations → Requirement list
   └── BugReader         → LLM parses natural language bug description → BUG_REPRO Requirement

2. COVERAGE CHECKER  (quell/coverage/checker.py)
   └── AST-scans test files; marks each Requirement is_covered=True/False
       Conservative: prefers false positive (duplicate) over false negative (missed gap)

3. TEST SYNTHESIZER  (quell/synthesis/)
   ├── RuleEngine        → deterministic, no LLM, handles 5 ConstraintKinds
   │   └── sig_inspector → inspects target function AST to build valid call stubs
   └── LLMSynthesizer    → LLM fallback for BUG_REPRO and CUSTOM kinds

4. VERIFICATION ENGINE  (quell/core/verifier.py)  ← THE MOAT
   ├── Phase 1: run test on ORIGINAL source → MUST PASS (bad test → reject)
   ├── Phase 2: inject violation into source → run test → MUST FAIL (weak test → reject)
   └── finally: ALWAYS restore source (even on exception)

5. WRITER  (quell/core/writer.py)
   └── libcst injection into test file (never string concatenation)
       Backs up, validates CST, restores on failure

6. REPORT  (quell/report/generator.py)
   └── .quell/report.json — privacy-safe diagnostic (no source code, no full paths)
```

---

## ConstraintKind Enum

Defined in `quell/core/models.py`. Each kind drives a different generation + violation strategy.

| Kind | Source | Rule Engine? | Violation Injection |
|------|--------|-------------|---------------------|
| `MUST_RAISE` | docstring Raises: block | YES | comment out `raise` in function body |
| `MUST_RETURN` | docstring Returns: block | YES (skipped if Optional return) | replace ALL non-None returns with `return None` |
| `BOUNDARY` | docstring "must be positive", Pydantic `Field(gt=0)` | YES | weaken threshold: `> 0` → `> -9999` |
| `ENUM_VALID` | Pydantic `Literal["USD","EUR"]`, function param Literal | YES | remove enum validation guard |
| `BUG_REPRO` | `quell reproduce` bug description | YES (skeleton) | no injection needed — source already broken |
| `CUSTOM` | LLM fallback when nothing structured found | NO | LLM handles |
| `MUTATION` | mutmut/Stryker results (disabled by default) | NO | mutmut apply |

---

## Spec Readers

### DocstringReader (`quell/spec/docstring_reader.py`)

Reads Python docstrings via `ast.get_docstring`. Extracts:

- **MUST_RAISE**: Google-style `Raises:\n    ExceptionType: condition` blocks
- **BOUNDARY**: regex patterns — "must be positive", "must be > 0", "must be >= N", "must be between X and Y"
- **ENUM_VALID**: patterns — "must be one of", "one of", "valid values" followed by uppercase words
- **MUST_RETURN**: `Returns:\n    description` blocks

LLM fallback (`llm_client` must be configured) fires only when none of the above match.

Returns `[]` on any error — never raises.

### TypeReader (`quell/spec/type_reader.py`)

Reads Python AST — no execution required.

- **Pydantic models** (`class X(BaseModel)`):
  - `Literal["A","B"]` fields → `ENUM_VALID`
  - `Field(gt=0)`, `Field(ge=1)`, `Field(lt=N)`, `Field(min_length=1)`, etc. → `BOUNDARY`
  - Supported validators: `gt, ge, lt, le, min_length, max_length, min_items, max_items`
- **Function parameters** with `Literal[...]` annotation → `ENUM_VALID`

`target_function` for Pydantic models is the **class name** (not a method).

### BugReader (`quell/spec/bug_reader.py`)

Used only by `quell reproduce`. Calls LLM to parse bug description into:
- `function_hint`, `triggering_inputs`, `symptom`, `expected_behavior`

Then searches codebase (or given `--file`) for matching function. Returns a `BUG_REPRO` Requirement.

---

## Coverage Checker (`quell/coverage/checker.py`)

Looks for test files at:
1. `{project_root}/tests/test_{stem}.py`
2. `{project_root}/tests/{stem}_test.py`
3. `{src_dir}/test_{stem}.py`

For each test function found, checks coverage heuristics:
- Function name or docstring must mention `target_function` (case-insensitive)
- `MUST_RAISE`: looks for `pytest.raises` context manager in the test
- `BOUNDARY`: looks for numeric constants `{0, -1, 1, 0.0, -1.0, 1.0}` in the test
- `BUG_REPRO`: never marked covered — always regenerated
- Other kinds: conservatively assumed covered if function name matches

---

## Rule Engine (`quell/synthesis/rule_engine.py`)

Generates **real callable tests** — not TODO scaffolds. Uses `sig_inspector` to build valid call arguments from the target function's type annotations.

### Test name format
`test_quell_{function_name}_{constraint_kind}_{req_id[:8]}`

### Test file path
`{target_file.parent.parent}/tests/test_{target_file.stem}.py`

### Per-kind generation

**MUST_RAISE**:
```python
def test_quell_func_must_raise_abc12345(tmp_path):
    """Quell: raises ValueError when amount is zero"""
    import pytest
    from mymodule import func
    with pytest.raises(ValueError):
        func(amount=0)  # real stub, no file creation (Path stubs → FileNotFoundError)
```
- Exception name extracted from `req.description` + `req.expected_behavior` via regex `r"\braises?\s+(\w+Error|\w+Exception)"`
- Intentionally skips `_setup_lines` — Path stubs point to non-existent files so functions that open files raise naturally

**BOUNDARY**:
```python
with pytest.raises(Exception):
    func(amount=0)  # boundary value injected via _inject_boundary_value()
```
- `_inject_boundary_value()` replaces first numeric stub with violating value
- "positive" / "> 0" → 0; ">= 1" / "at least 1" → 0; "between 0 and 1" → -1

**ENUM_VALID**:
```python
with pytest.raises(Exception):
    func(currency="INVALID_VALUE")  # or replaces first string stub
```
- Replaces first `"test_value"` stub with `"INVALID_VALUE"`
- Fallback: appends `, currency="INVALID_VALUE"` if no string stub found

**MUST_RETURN**:
```python
result = func(arg1=val1)
assert result is not None
```
- Skipped (returns `None`) if return annotation is `Optional[X]`, `X | None`, or `None`

**BUG_REPRO**:
```python
with pytest.raises(Exception):
    func(arg1=val1)  # "Fix the code to make it pass"
```

---

## Signature Inspector (`quell/synthesis/sig_inspector.py`)

Pure AST analysis — no code execution, no imports.

### Type → stub value mapping

| Annotation | Stub |
|-----------|------|
| `str` | `"test_value"` |
| `int` | `1` |
| `float` | `1.0` |
| `bool` | `True` |
| `bytes` | `b"test"` |
| `list`, `List[...]`, `Sequence[...]` | `[]` |
| `dict`, `Dict[...]`, `Mapping[...]` | `{}` |
| `tuple`, `Tuple[...]` | `()` |
| `set`, `Set[...]` | `set()` |
| `Path`, `*Path*` | `tmp_path / 'test_file.py'` (needs `tmp_path` fixture) |
| `Optional[X]`, `X \| None` | `None` |
| `Callable[...]` | `lambda: None` |
| `logging.LogRecord` | `__import__('logging').LogRecord('test', 20, '', 0, 'msg', [], None)` |
| `datetime.datetime` | `__import__('datetime').datetime(2024, 1, 1)` |
| `re.Pattern`, `re.Pattern[str]` | `__import__('re').compile('.*')` |
| unknown annotation | falls back to param name heuristics, then `None  # unknown` |

### Param name heuristics (when no annotation)
`path`/`file` → `tmp_path / 'test_file.py'`, `source`/`code` → `"def foo(): pass"`, `name` → `"test_name"`, `count`/`num`/`size` → `1`, etc.

### Class method handling
If function is a class method, inspects `__init__` to build `ClassName(init_args).method(args)`.

---

## Verification Engine (`quell/core/verifier.py`)

### Two-phase verify algorithm
1. Write test to temp file (`.quell/backups/temp/quell_{req_id}.py`)
2. Back up source file
3. **Phase 1**: `pytest tempfile` on original source → returncode 0 required
   - Fail → `FAILS_ON_CORRECT` (test is wrong)
4. **Phase 2**: inject violation into source, run pytest again
   - Pass → `DOESNT_CATCH_VIOLATION` (test is weak)
   - Fail → `VERIFIED`
5. `finally`: restore source from backup, delete temp file

### Working directory for pytest subprocess
`_resolve_cwd()` walks up from source file to find `pyproject.toml`/`setup.py`/`setup.cfg`. Falls back to `src.parent.parent`. `project_root` parameter overrides when set.

### Targeted violation injection
Violations are scoped to the specific function's line range (via AST `end_lineno`), not the entire file:

| Kind | What changes |
|------|-------------|
| `MUST_RAISE` | Comments out `raise ExcType(...)` inside the function |
| `BOUNDARY` | Weakens first numeric comparison: `> 0` → `> -9999` |
| `MUST_RETURN` | Replaces **all** `return <non-None>` with `return None` (`count=0`) |
| `BUG_REPRO` | No change — source is already broken |
| `MUTATION` | `mutmut apply {req_id}` subprocess |

---

## Writer (`quell/core/writer.py`)

1. Creates test file if it doesn't exist (writes `# Generated by Quell\nimport pytest\n\n`)
2. Backs up test file to `.{timestamp}.bak`
3. Appends new test via libcst (lossless CST — preserves comments and formatting)
4. Validates CST parses before writing
5. Deletes backup on success; restores on failure
6. Appends to `.quell/audit.jsonl`

---

## CLI Commands

| Command | What it does |
|---------|-------------|
| `quell check <target>` | Scan specs, show requirement table and score |
| `quell check <target> --fix` | Same + generate/verify/write tests + write report |
| `quell check <target> --sources docstring,type` | Specify which readers to use |
| `quell reproduce "bug description"` | LLM → BUG_REPRO requirement → LLMSynthesizer → verify → write |
| `quell prove <file>` | Show requirement coverage % for file |
| `quell prove <file> --function func_name` | Same, scoped to one function |
| `quell score` | Project-wide score across all source files |
| `quell score --badge` | Also write `.quell/badge.svg` |
| `quell ci <target> --threshold 0.8` | Exit 1 if score < threshold (for CI gates) |
| `quell init` | Add `[tool.quell]` block to `pyproject.toml` |
| `quell --version` / `quell -V` | Print `quelltest {version}` |

---

## Diagnostic Report (`.quell/report.json`)

Written by `quell check --fix`. Privacy-safe: no source code, no full file paths.

```json
{
  "quell_version": "0.4.4",
  "generated_at": "2026-05-09T12:00:00",
  "target_name": "payments.py",
  "total_requirements": 20,
  "already_covered": 5,
  "written": 8,
  "fails_on_correct": 4,
  "doesnt_catch_violation": 2,
  "timeout": 0,
  "error": 1,
  "skipped": 0,
  "outcomes": [
    {
      "constraint_kind": "must_raise",
      "function_name": "process_payment",
      "file_basename": "payments.py",
      "outcome": "verified",
      "unknown_types": [],
      "failure_reason": null
    }
  ]
}
```

**Outcome values**: `verified`, `fails_on_correct`, `doesnt_catch_violation`, `timeout`, `error`, `skipped`

---

## Config (`pyproject.toml`)

```toml
[tool.quell]
llm_provider = "anthropic"          # "anthropic" | "openai" | "ollama"
llm_model = "claude-sonnet-4-5"
ollama_base_url = "http://localhost:11434"
max_verification_attempts = 3
verification_timeout_seconds = 30
auto_write = false
enable_docstring = true
enable_types = true
enable_mutations = false            # mutmut not required; off by default (Windows compat)
score_threshold = 0.0
```

---

## Programmatic API (`quell/sdk.py`)

```python
from quell import Quell

q = Quell(llm="anthropic", project_root=".")

result = q.check("src/")                    # CheckResult: .requirements, .score, .uncovered
result = q.check("src/", fix=True)          # also generates/verifies/writes tests
written = q.reproduce("zero amount accepted")  # bool
score = q.prove("src/payments.py")          # float 0.0-1.0
project = q.score()                         # ProjectScore: .files, .total_score, .percentage
```

---

## Key File Map

```
quell/__init__.py              version string + public exports
quell/cli.py                   Typer CLI commands
quell/sdk.py                   Quell class, CheckResult dataclass
quell/core/models.py           ConstraintKind, Requirement, GeneratedTest, VerificationResult, ...
quell/core/verifier.py         Two-phase verification engine + violation injectors
quell/core/writer.py           libcst test injection
quell/spec/docstring_reader.py Docstring -> Requirements
quell/spec/type_reader.py      Pydantic/Literal -> Requirements
quell/spec/bug_reader.py       Bug description (LLM) -> BUG_REPRO Requirement
quell/spec/mutation_reader.py  mutmut/Stryker -> MUTATION Requirements (optional)
quell/coverage/checker.py      AST-based coverage heuristics
quell/synthesis/rule_engine.py Deterministic test code generation
quell/synthesis/sig_inspector.py AST signature inspection + stub generation
quell/synthesis/llm_engine.py  LLM test generation fallback
quell/report/generator.py      Diagnostic report model + writer
quell/score/calculator.py      ProjectScore calculation
quell/score/badge.py           SVG badge generation
quell/llm/client.py            Abstract LLM client + factory
quell/llm/providers/           anthropic, openai, ollama providers
quell/llm/prompts.py           LLM prompt templates
```

---

## Known Limitations (v0.4.4)

**fails_on_correct for class-method MUST_RAISE (~15 cases on Refactron core/)**
- Problem: Functions like `from_file()` / `load_with_profile()` raise based on config content, not file existence. The rule engine stubs Path args to non-existent files, but the function fails *before* reaching the validation raise (wrong exception, or fails at open() not at validation).
- Workaround: None yet. Counted as `fails_on_correct` in the report.

**CUSTOM ConstraintKind**
- `can_handle()` returns `False` — skipped by rule engine. Counted as `skipped`.
- Would need LLM engine wired into `_fix_gaps()` to handle.

**must_return skipped for Optional returns**
- Functions annotated `Optional[X]`, `X | None`, or `None` are always skipped. Intentional — `assert result is not None` would fail legitimately on empty inputs.

**ENUM_VALID for Pydantic class-level validation**
- TypeReader generates the requirement with `target_function = ClassName`.
- The generated test calls `ClassName(currency="INVALID_VALUE")` which works for Pydantic (raises `ValidationError`), but violation injector scope targets the class constructor.

**mutmut requires Linux/Mac (WSL on Windows)**
- `enable_mutations = false` by default. `MutmutReader` returns `[]` if `.mutmut-cache` doesn't exist.

---

## Verification Status Outcomes

| Status | Meaning |
|--------|---------|
| `VERIFIED` | Test passes on original, fails after violation — written to disk |
| `FAILS_ON_CORRECT` | Test fails even on correct code — test is wrong, not written |
| `DOESNT_CATCH_VIOLATION` | Test passes after violation — too weak to detect the bug, not written |
| `TIMEOUT` | pytest subprocess exceeded `verification_timeout_seconds` |
| `ERROR` | Exception during verification (file not found, import error, etc.) |
| `skipped` | Rule engine `can_handle()` returned False, or `generate()` returned None |

---

## Score Progression (Refactron core/ benchmark)

| Version | Score |
|---------|-------|
| 0.4.0 | 11% |
| 0.4.2 | 23% |
| 0.4.3 | 65% |
| 0.4.4 | 75% |

Key improvements: sig_inspector stubs (Callable, LogRecord), targeted violation injection by function scope, replace ALL returns in must_return violation (not just first).
