# Show HN: Quelltest – pytest generation that proves tests catch violations, not just run

**Title (under 80 chars):**
Show HN: Quelltest – generates verified pytest tests from your docstrings

---

**Body:**

I built Quelltest after getting burned by a 94% coverage badge on a payments codebase that happily accepted zero-amount charges. Every line was "covered". Nothing was proved.

The problem: coverage measures which lines ran, not whether the test checked anything meaningful. You can hit 100% coverage with `assert True`.

Quelltest takes a different approach. It reads the requirements that already exist in your codebase — `Raises:` blocks in docstrings, `Field(gt=0)` in Pydantic models, `nullable=False` in PySpark schemas — and generates a pytest test for each one. But before writing anything to disk, it runs two-phase verification:

1. The test must PASS on your original code
2. The test must FAIL when the relevant code is violated (raise commented out, Field bound weakened, nullable flipped)

If a test passes both phases, it proved the requirement. Only then is it written.

**Install and try:**

```bash
pip install quelltest
quell check src/ --fix --no-llm
```

No LLM needed. No API key. No code leaves your machine. A deterministic rule engine handles ~75% of real requirements — MUST_RAISE, BOUNDARY, ENUM_VALID, NOT_NULL, TYPE_CHECK. LLM fallback is optional for the rest.

**It also works in CI:**

```bash
quell check src/ --ci --threshold 0.80
# fails the pipeline if requirement coverage drops below 80%
```

**What it reads:**
- Python docstrings (Google/NumPy/Sphinx `Raises:`, `Returns:`, `Args:`)
- Pydantic v2 `Field` constraints and `Literal` types
- PySpark `StructType` / `StructField` schemas

**What it does not do:**
- Generate tests for async functions (skipped, planned for 0.7.x)
- Send your source code to any server (rule engine is fully local)
- Require an existing test suite to scan (works from zero)

**The injection is libcst-based** — lossless concrete syntax tree, so comments and formatting are preserved. Source is backed up before every write and always restored in a `finally` block.

GitHub: https://github.com/shashank7109/quelltest_lib
Docs: https://quell.buildsbyshashank.tech/docs
PyPI: https://pypi.org/project/quelltest/

Happy to answer questions about the verification engine design — that's the part I spent the most time on and the part I think is genuinely new.
