"""Jules API client.

Wraps the Jules REST API for creating and polling coding sessions.
Session states observed in practice:
  - "queued"      : session is waiting to be picked up
  - "running"     : Jules is actively working
  - "paused"      : Jules stopped without opening a PR (needs user input)
  - "pr_open"     : a pull-request has been created
  - "completed"   : session finished (PR merged or closed)
  - "error"       : session encountered an unrecoverable error

Base URL: https://api.jules.google.com/v1   (subject to change)
"""

from __future__ import annotations

from typing import Any

import httpx

JULES_BASE_URL = "https://api.jules.google.com/v1"

# States that indicate Jules stopped without producing a PR
PAUSED_STATES = {"paused", "error"}

# State that means a PR has been opened
PR_OPEN_STATE = "pr_open"

# Terminal states (no more polling needed)
TERMINAL_STATES = {"pr_open", "completed", "error"}


class JulesClient:
    """Thin async wrapper around the Jules REST API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        *,
        repository: str,
        branch: str,
        prompt: str,
    ) -> dict[str, Any]:
        """Create a new Jules session that will open a PR.

        Parameters
        ----------
        repository:
            Full repository name in ``owner/repo`` format.
        branch:
            Target branch for the PR.
        prompt:
            Natural-language task description sent to Jules.

        Returns
        -------
        dict
            The parsed JSON response from the Jules API containing at
            minimum ``id`` (the session identifier) and ``state``.
        """
        payload = {
            "repository": repository,
            "branch": branch,
            "prompt": prompt,
            "mode": "open_pr",
        }
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.post("/sessions", json=payload, timeout=30)
            response.raise_for_status()
            return response.json()

    def get_session(self, session_id: str) -> dict[str, Any]:
        """Fetch the current state of a Jules session.

        Parameters
        ----------
        session_id:
            The identifier returned by :meth:`create_session`.

        Returns
        -------
        dict
            Parsed JSON with at minimum ``id``, ``state``, and (when a PR
            exists) ``pr_url`` / ``pr_number``.
        """
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.get(f"/sessions/{session_id}", timeout=30)
            response.raise_for_status()
            return response.json()
