"""
Quell GitHub App — webhook server deployed at quell.build.

Receives GitHub pull_request events, runs the Quell CI pipeline on the
changed code, and posts a verified-test comment back to the PR.

Environment variables required (set in Render/Railway/Fly.io dashboard):
    GITHUB_APP_ID          — App ID from GitHub App settings
    GITHUB_APP_PRIVATE_KEY — PEM private key (paste full contents)
    GITHUB_WEBHOOK_SECRET  — Webhook secret set in App settings
    QUELL_WORK_DIR         — Temp directory for cloning repos (default: /tmp)

Run locally:
    pip install quell[github]
    uvicorn quell.github.app:app --host 0.0.0.0 --port 8080

Architecture:
    GitHub sends pull_request webhook
        → validate HMAC signature
        → get installation token
        → clone PR branch to tmp dir
        → run: quell ci --diff-only --report json
        → format results as markdown
        → post/update PR comment
"""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import subprocess
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response

from quell.github.auth import generate_app_jwt, get_installation_token
from quell.github.formatter import format_pr_comment
from quell.github.pr_commenter import post_or_update_pr_comment

app = FastAPI(title="Quell GitHub App", version="1.0.0")

_APP_ID = os.getenv("GITHUB_APP_ID", "")
_PRIVATE_KEY = os.getenv("GITHUB_APP_PRIVATE_KEY", "").replace("\\n", "\n")
_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET", "").encode()


@app.get("/")
def health() -> dict:
    """Health check for Render / uptime monitors."""
    return {"status": "ok", "service": "quell-github-app"}


@app.post("/github/webhook")
async def github_webhook(request: Request) -> Response:
    """
    Handle incoming GitHub webhook events.

    Only processes pull_request events with action opened/synchronize.
    All other events return 200 immediately.
    """
    body = await request.body()
    _verify_signature(body, request.headers.get("X-Hub-Signature-256", ""))

    event = request.headers.get("X-GitHub-Event", "")
    if event != "pull_request":
        return Response(content="ignored", status_code=200)

    payload = json.loads(body)
    action = payload.get("action", "")
    if action not in {"opened", "synchronize", "reopened"}:
        return Response(content="ignored", status_code=200)

    # Fire-and-forget so GitHub doesn't time out the webhook
    asyncio.create_task(_handle_pr_event(payload))
    return Response(content="accepted", status_code=202)


def _verify_signature(body: bytes, signature_header: str) -> None:
    """Validate the HMAC-SHA256 webhook signature from GitHub."""
    if not _WEBHOOK_SECRET:
        return  # skip validation if not configured (dev mode)
    if not signature_header.startswith("sha256="):
        raise HTTPException(status_code=403, detail="Missing signature")
    expected = "sha256=" + hmac.new(_WEBHOOK_SECRET, body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=403, detail="Invalid signature")


async def _handle_pr_event(payload: dict) -> None:
    """
    Clone the PR branch, run Quell CI, post the result as a PR comment.

    Runs in a background task so the webhook response is immediate.
    """
    repo_full = payload["repository"]["full_name"]      # "owner/repo"
    clone_url = payload["repository"]["clone_url"]
    branch = payload["pull_request"]["head"]["ref"]
    pr_number = payload["pull_request"]["number"]
    installation_id = payload["installation"]["id"]

    # Get installation token
    app_jwt = generate_app_jwt(_APP_ID, _PRIVATE_KEY)
    token = await get_installation_token(app_jwt, installation_id)

    # Clone into a temp dir and run quell ci
    with tempfile.TemporaryDirectory(dir=os.getenv("QUELL_WORK_DIR", "/tmp")) as tmpdir:
        work_dir = Path(tmpdir)

        # Inject token into clone URL for auth
        auth_url = clone_url.replace("https://", f"https://x-access-token:{token}@")
        subprocess.run(
            ["git", "clone", "--depth=1", "--branch", branch, auth_url, str(work_dir)],
            check=True,
            capture_output=True,
        )

        # Run quell ci --diff-only --report json
        result = subprocess.run(
            ["quell", "ci", "--diff-only", "--report", "json"],
            cwd=work_dir,
            capture_output=True,
            text=True,
        )

        # Load the JSON report written to .quell/ci-report.json
        report_path = work_dir / ".quell" / "ci-report.json"
        if not report_path.exists():
            return  # quell couldn't run (no mutmut cache, etc.)

        report_data = json.loads(report_path.read_text())

    # Build and post the PR comment
    # We use a simplified comment when running from the App
    # (no full ProjectScore object available without re-calculating)
    from quell.ci.threshold import ThresholdResult
    from quell.ci.reporter import CIReport
    from quell.score.calculator import ProjectScore

    threshold_result = ThresholdResult(
        passed=report_data.get("threshold_passed", True),
        score=report_data.get("score_after", 0.0),
        threshold=report_data.get("threshold", 0.0),
        message="",
    )
    ci_report = CIReport(
        score_before=report_data.get("score_before", 0.0),
        score_after=report_data.get("score_after", 0.0),
        fixed_count=report_data.get("fixed", 0),
        skipped_count=report_data.get("skipped", 0),
        total_survivors=report_data.get("total_survivors", 0),
        threshold_result=threshold_result,
    )

    comment_body = format_pr_comment(ci_report, ProjectScore())
    await post_or_update_pr_comment(token, repo_full, pr_number, comment_body)


def main() -> None:
    """Entry point for `quell-github-app` CLI command."""
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", "8080")))


if __name__ == "__main__":
    main()
