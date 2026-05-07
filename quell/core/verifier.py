"""
Verification Engine — The most important module in Quell.

For every GeneratedTest, we verify:
1. The test PASSES on the original (unmodified) code
2. The test FAILS on the mutated code (i.e., it kills the mutant)

Only tests that satisfy BOTH conditions are accepted.
Auto-restore on any failure. No side effects left on disk.
"""
from __future__ import annotations
import subprocess
import shutil
import time
from pathlib import Path
from quell.core.models import (
    SurvivedMutant, GeneratedTest, VerificationResult, VerificationStatus, QuellConfig
)


class MutantVerifier:
    """
    Verifies that a generated test actually kills a given mutant.

    Algorithm:
    1. Write test to a TEMP file (not the real test file)
    2. Run pytest on original code with temp test → must PASS
    3. Apply mutant to source (patch source file)
    4. Run pytest on mutated code with temp test → must FAIL
    5. Restore source file (always, even on error)
    6. Return VerificationResult

    Usage:
        verifier = MutantVerifier(config)
        result = verifier.verify(mutant, generated_test)
    """

    def __init__(self, config: QuellConfig):
        self.config = config
        self._backup_dir = config.backup_dir
        self._backup_dir.mkdir(parents=True, exist_ok=True)

    def verify(self, mutant: SurvivedMutant, test: GeneratedTest) -> VerificationResult:
        """Main verification entry point."""
        start_time = time.time()
        temp_test_file = self._write_temp_test(test)
        backup_path = self._backup_source(mutant.file_path)

        try:
            # Step 1: Test must PASS on original code
            original_result = self._run_pytest(temp_test_file, mutant.file_path)
            if not original_result["passed"]:
                return VerificationResult(
                    mutant_id=mutant.id,
                    generated_test=test,
                    status=VerificationStatus.FAILS_ON_ORIGINAL,
                    error_message=original_result.get("error"),
                    duration_ms=int((time.time() - start_time) * 1000),
                )

            # Step 2: Apply the mutant
            self._apply_mutant(mutant)

            # Step 3: Test must FAIL on mutated code
            mutant_result = self._run_pytest(temp_test_file, mutant.file_path)

            if mutant_result["passed"]:
                # Test passed even with mutant = doesn't kill it
                status = VerificationStatus.DOESNT_KILL_MUTANT
            else:
                status = VerificationStatus.VERIFIED

            return VerificationResult(
                mutant_id=mutant.id,
                generated_test=test,
                status=status,
                error_message=None if status == VerificationStatus.VERIFIED else mutant_result.get("error"),
                duration_ms=int((time.time() - start_time) * 1000),
            )

        except SyntaxError as e:
            return VerificationResult(
                mutant_id=mutant.id,
                generated_test=test,
                status=VerificationStatus.SYNTAX_ERROR,
                error_message=str(e),
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except TimeoutError:
            return VerificationResult(
                mutant_id=mutant.id,
                generated_test=test,
                status=VerificationStatus.TIMEOUT,
                error_message="Verification timed out",
                duration_ms=self.config.verification_timeout_seconds * 1000,
            )
        finally:
            # ALWAYS restore source file
            self._restore_source(mutant.file_path, backup_path)
            # Clean up temp test file
            temp_test_file.unlink(missing_ok=True)

    def _write_temp_test(self, test: GeneratedTest) -> Path:
        """Write generated test to a temporary file."""
        temp_dir = self._backup_dir / "temp_tests"
        temp_dir.mkdir(parents=True, exist_ok=True)
        temp_file = temp_dir / f"quell_temp_{test.mutant_id}.py"
        temp_file.write_text(test.test_code)
        return temp_file

    def _backup_source(self, source_path: Path) -> Path:
        """Copy source file to backup directory. Returns backup path."""
        backup_path = self._backup_dir / f"{source_path.stem}_{int(time.time())}.py.bak"
        shutil.copy2(source_path, backup_path)
        return backup_path

    def _restore_source(self, source_path: Path, backup_path: Path) -> None:
        """Restore source from backup. Called in finally block."""
        if backup_path.exists():
            shutil.copy2(backup_path, source_path)
            backup_path.unlink()

    def _apply_mutant(self, mutant: SurvivedMutant) -> None:
        """
        Apply the mutant's change to the source file.

        For mutmut: use `mutmut apply <id>` subprocess command.
        For Stryker: directly replace the line in the source file.
        """
        if mutant.source.value == "mutmut":
            result = subprocess.run(
                ["mutmut", "apply", str(mutant.id)],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0:
                raise RuntimeError(f"mutmut apply failed: {result.stderr}")
        else:
            # Direct source replacement for Stryker
            source = mutant.file_path.read_text()
            lines = source.splitlines(keepends=True)
            # Replace the specific line with mutated code
            line_idx = mutant.line_start - 1
            if 0 <= line_idx < len(lines):
                lines[line_idx] = mutant.mutated_code + "\n"
            mutant.file_path.write_text("".join(lines))

    def _run_pytest(self, test_file: Path, source_file: Path) -> dict:
        """
        Run pytest on a specific test file. Returns {"passed": bool, "error": str}.
        Timeout enforced via config.
        """
        try:
            result = subprocess.run(
                ["python", "-m", "pytest", str(test_file), "-v", "--tb=short", "--no-header", "-q"],
                capture_output=True,
                text=True,
                timeout=self.config.verification_timeout_seconds,
                cwd=source_file.parent.parent,  # run from project root
            )
            passed = result.returncode == 0
            return {
                "passed": passed,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "error": result.stdout if not passed else None,
            }
        except subprocess.TimeoutExpired:
            raise TimeoutError("pytest timed out")
