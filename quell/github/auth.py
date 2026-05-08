"""
GitHub App JWT authentication.

GitHub Apps authenticate in two steps:
  1. Generate a short-lived JWT signed with the App's RSA private key
  2. Exchange the JWT for an installation access token (valid 1 hour)

Requires:
    pip install quell[github]   # installs PyJWT + cryptography
"""
from __future__ import annotations

import time


def generate_app_jwt(app_id: str, private_key_pem: str) -> str:
    """
    Generate a GitHub App JWT valid for 10 minutes.

    Args:
        app_id: GitHub App ID (found in App settings).
        private_key_pem: PEM-encoded RSA private key (contents of the .pem file).

    Returns:
        Signed JWT string.
    """
    try:
        import jwt as pyjwt
    except ImportError:
        raise ImportError(
            "PyJWT is required for GitHub App auth.\n"
            "Install it with: pip install quell[github]"
        )

    now = int(time.time())
    payload = {
        "iat": now - 60,    # 60s leeway for clock drift
        "exp": now + 600,   # 10-minute validity
        "iss": app_id,
    }
    return pyjwt.encode(payload, private_key_pem, algorithm="RS256")


async def get_installation_token(app_jwt: str, installation_id: int) -> str:
    """
    Exchange a GitHub App JWT for an installation access token.

    The installation token is valid for 1 hour and scoped to the
    repositories the App is installed on.

    Args:
        app_jwt: Signed JWT from generate_app_jwt().
        installation_id: Installation ID from the webhook event payload.

    Returns:
        Installation access token string.
    """
    import httpx

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"https://api.github.com/app/installations/{installation_id}/access_tokens",
            headers={
                "Authorization": f"Bearer {app_jwt}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        resp.raise_for_status()
        return resp.json()["token"]
