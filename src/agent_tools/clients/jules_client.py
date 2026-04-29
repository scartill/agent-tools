"""Jules API client.

Wraps the Jules REST API for creating and polling coding sessions.

Session states from the API:
  - "STATE_UNSPECIFIED" : unknown state
  - "QUEUED"           : session is waiting to be picked up
  - "PLANNING"         : the agent is planning
  - "AWAITING_PLAN_APPROVAL" : waiting for plan approval
  - "AWAITING_USER_FEEDBACK" : waiting for user feedback
  - "IN_PROGRESS"      : session is actively working
  - "PAUSED"           : session is paused
  - "FAILED"           : session has failed
  - "COMPLETED"        : session has completed

Automation modes:
  - "AUTOMATION_MODE_UNSPECIFIED" : default (no automation)
  - "AUTO_CREATE_PR" : automatically create PR when code is ready

Base URL: https://jules.googleapis.com/v1alpha/
"""

from __future__ import annotations

from typing import Any

import httpx

JULES_BASE_URL = 'https://jules.googleapis.com/v1alpha/'

# Session states from the Jules API
STATE_QUEUED = 'QUEUED'
STATE_PLANNING = 'PLANNING'
STATE_AWAITING_PLAN_APPROVAL = 'AWAITING_PLAN_APPROVAL'
STATE_AWAITING_USER_FEEDBACK = 'AWAITING_USER_FEEDBACK'
STATE_IN_PROGRESS = 'IN_PROGRESS'
STATE_PAUSED = 'PAUSED'
STATE_FAILED = 'FAILED'
STATE_COMPLETED = 'COMPLETED'

# Terminal states (no more polling needed)
TERMINAL_STATES = {
    STATE_COMPLETED,
    STATE_FAILED,
    STATE_PAUSED,
    STATE_AWAITING_PLAN_APPROVAL,
    STATE_AWAITING_USER_FEEDBACK,
}

# States that indicate a PR might have been created
PR_STATES = {STATE_COMPLETED, STATE_IN_PROGRESS, STATE_AWAITING_USER_FEEDBACK}

# Automation mode for auto-creating PRs
AUTOMATION_MODE_AUTO_CREATE_PR = 'AUTO_CREATE_PR'


class JulesClient:
    """Thin async wrapper around the Jules REST API."""

    def __init__(self, api_key: str) -> None:
        self._api_key = api_key
        self._headers = {
            'X-Goog-Api-Key': api_key,
            'Content-Type': 'application/json',
        }

    # ------------------------------------------------------------------
    # Sources
    # ------------------------------------------------------------------

    def list_sources(self) -> dict[str, Any]:
        """List all available sources.

        Returns
        -------
        dict
            The parsed JSON response containing a list of sources.
        """
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.get('/sources', timeout=30)
            response.raise_for_status()
            return response.json()

    def get_source(self, source_name: str) -> dict[str, Any]:
        """Get a single source by name.

        Parameters
        ----------
        source_name:
            The full resource name of the source (e.g., "sources/github/owner/repo").

        Returns
        -------
        dict
            The parsed JSON response containing the source details.
        """
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.get(f'/{source_name}', timeout=30)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def create_session(
        self,
        *,
        source: str,
        starting_branch: str,
        prompt: str,
        title: str | None = None,
        automation_mode: str = AUTOMATION_MODE_AUTO_CREATE_PR,
        require_plan_approval: bool = False,
    ) -> dict[str, Any]:
        """Create a new Jules session.

        Parameters
        ----------
        source:
            The full source resource name in format ``sources/github/owner/repo``.
        starting_branch:
            The branch name to start the session from.
        prompt:
            Natural-language task description sent to Jules.
        title:
            Optional title for the session. If not provided, system generates one.
        automation_mode:
            Automation mode. Use ``AUTOMATION_MODE_AUTO_CREATE_PR`` to automatically
            create a PR. Default is ``AUTOMATION_MODE_AUTO_CREATE_PR``.
        require_plan_approval:
            If True, plans require explicit approval before agent starts working.
            Default is False (plans are auto-approved).

        Returns
        -------
        dict
            The parsed JSON response containing the session with ``name``,
            ``id``, ``state``, and other fields.
        """
        payload: dict[str, Any] = {
            'prompt': prompt,
            'sourceContext': {
                'source': source,
                'githubRepoContext': {
                    'startingBranch': starting_branch,
                },
            },
            'automationMode': automation_mode,
        }

        if title:
            payload['title'] = title

        if require_plan_approval:
            payload['requirePlanApproval'] = True

        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.post('/sessions', json=payload, timeout=30)
            response.raise_for_status()
            return response.json()

    def get_session(self, session_name: str) -> dict[str, Any]:
        """Fetch the current state of a Jules session.

        Parameters
        ----------
        session_name:
            The full resource name of the session (e.g., "sessions/123456").

        Returns
        -------
        dict
            Parsed JSON with ``name``, ``id``, ``state``, ``outputs``, and other fields.
            PR information (if any) is in ``outputs`` array with ``pullRequest`` field.
        """
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.get(f'/{session_name}', timeout=30)
            response.raise_for_status()
            return response.json()

    def list_sessions(self, page_size: int | None = None) -> dict[str, Any]:
        """List all sessions.

        Parameters
        ----------
        page_size:
            Optional maximum number of sessions to return.

        Returns
        -------
        dict
            The parsed JSON response containing a list of sessions.
        """
        params = {}
        if page_size:
            params['pageSize'] = page_size

        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.get('/sessions', params=params, timeout=30)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Session interactions
    # ------------------------------------------------------------------

    def approve_plan(self, session_name: str) -> dict[str, Any]:
        """Approve the latest plan in a session.

        Parameters
        ----------
        session_name:
            The full resource name of the session (e.g., "sessions/123456").

        Returns
        -------
        dict
            The parsed JSON response (typically empty on success).
        """
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.post(f'/{session_name}:approvePlan', timeout=30)
            response.raise_for_status()
            return response.json()

    def send_message(self, session_name: str, prompt: str) -> dict[str, Any]:
        """Send a message to a session.

        Parameters
        ----------
        session_name:
            The full resource name of the session (e.g., "sessions/123456").
        prompt:
            The message text to send to the agent.

        Returns
        -------
        dict
            The parsed JSON response (typically empty on success).
        """
        payload = {'prompt': prompt}
        with httpx.Client(base_url=JULES_BASE_URL, headers=self._headers) as client:
            response = client.post(f'/{session_name}:sendMessage', json=payload, timeout=30)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------

    def find_source_id(self, owner: str, repo: str) -> str | None:
        """Find the source ID for a GitHub repository.

        Parameters
        ----------
        owner:
            GitHub repository owner.
        repo:
            GitHub repository name.

        Returns
        -------
        str or None
            The source resource name (e.g., "sources/github/owner/repo") or None.
        """
        sources = self.list_sources()
        for source in sources.get('sources', []):
            source_name = source.get('name', '')
            github_repo = source.get('githubRepo', {})
            if github_repo.get('owner') == owner and github_repo.get('repo') == repo:
                return source_name
        return None

    def extract_pr_info(self, session: dict[str, Any]) -> tuple[str | None, int | None]:
        """Extract PR URL and number from a session response.

        Parameters
        ----------
        session:
            The session dictionary returned by get_session().

        Returns
        -------
        tuple
            A tuple of (pr_url, pr_number) or (None, None) if no PR exists.
        """
        outputs = session.get('outputs', [])
        for output in outputs:
            pull_request = output.get('pullRequest', {})
            if pull_request:
                url = pull_request.get('url', '')
                # Extract PR number from URL like https://github.com/owner/repo/pull/123
                try:
                    pr_number = int(url.split('/')[-1])
                    return url, pr_number
                except (ValueError, IndexError):
                    return url, None
        return None, None
