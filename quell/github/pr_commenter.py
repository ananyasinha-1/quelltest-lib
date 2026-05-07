"""
Posts and updates Quell PR comments via the GitHub REST API.

Strategy: find the existing Quell comment by its marker, update it in-place.
This avoids spamming new comments on every push to the PR branch.

Usage (from GitHub Actions):
    export GITHUB_TOKEN=${{ secrets.GITHUB_TOKEN }}
    quell github-comment --repo owner/repo --pr 42

Usage (programmatic):
    await post_or_update_pr_comment(token, "owner/repo", 42, comment_body)
"""
from __future__ import annotations

import httpx

from quell.github.formatter import COMMENT_MARKER

GITHUB_API = "https://api.github.com"
_HEADERS_BASE = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
}


async def post_or_update_pr_comment(
    token: str,
    repo: str,
    pr_number: int,
    body: str,
) -> int:
    """
    Post a new PR comment or update the existing Quell comment.

    Identifies the existing Quell comment by COMMENT_MARKER. If found,
    updates it (PATCH). If not found, creates a new one (POST).

    Args:
        token: GitHub token (GITHUB_TOKEN from Actions or a PAT).
        repo: Repository in "owner/repo" format.
        pr_number: Pull request number.
        body: Full comment markdown body (must include COMMENT_MARKER).

    Returns:
        HTTP status code of the final API call.
    """
    headers = {**_HEADERS_BASE, "Authorization": f"Bearer {token}"}

    async with httpx.AsyncClient() as client:
        existing_id = await _find_existing_comment(client, headers, repo, pr_number)

        if existing_id:
            resp = await client.patch(
                f"{GITHUB_API}/repos/{repo}/issues/comments/{existing_id}",
                headers=headers,
                json={"body": body},
            )
        else:
            resp = await client.post(
                f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments",
                headers=headers,
                json={"body": body},
            )

        resp.raise_for_status()
        return resp.status_code


async def _find_existing_comment(
    client: httpx.AsyncClient,
    headers: dict,
    repo: str,
    pr_number: int,
) -> int | None:
    """Return the ID of an existing Quell comment, or None."""
    page = 1
    while True:
        resp = await client.get(
            f"{GITHUB_API}/repos/{repo}/issues/{pr_number}/comments",
            headers=headers,
            params={"per_page": 100, "page": page},
        )
        resp.raise_for_status()
        comments = resp.json()
        if not comments:
            break
        for comment in comments:
            if COMMENT_MARKER in (comment.get("body") or ""):
                return comment["id"]
        if len(comments) < 100:
            break
        page += 1
    return None


async def delete_pr_comment(token: str, repo: str, comment_id: int) -> None:
    """Delete a specific PR comment (used for cleanup)."""
    headers = {**_HEADERS_BASE, "Authorization": f"Bearer {token}"}
    async with httpx.AsyncClient() as client:
        await client.delete(
            f"{GITHUB_API}/repos/{repo}/issues/comments/{comment_id}",
            headers=headers,
        )
