"""GitHub API client.

Wraps the GitHub REST API for:
- Requesting a Copilot code review on a pull request
- Monitoring the Copilot review session
- Requesting Copilot to apply review comments
- Monitoring the comment-resolution session
- Merging a pull request
"""

from __future__ import annotations

from typing import Any

import httpx

GITHUB_BASE_URL = 'https://api.github.com'

# Review states reported by GitHub
REVIEW_PENDING_STATES = {'pending', 'in_progress'}
REVIEW_TERMINAL_STATES = {'approved', 'changes_requested', 'commented', 'dismissed'}

# Check run conclusions
CHECK_SUCCESS_CONCLUSIONS = {'success', 'neutral', 'skipped'}


class GitHubClient:
    """Thin wrapper around the GitHub REST API."""

    def __init__(self, pat: str) -> None:
        self._pat = pat
        self._headers = {
            'Authorization': f'Bearer {pat}',
            'Accept': 'application/vnd.github+json',
            'X-GitHub-Api-Version': '2022-11-28',
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, **kwargs: Any) -> dict[str, Any]:
        with httpx.Client(base_url=GITHUB_BASE_URL, headers=self._headers) as client:
            response = client.get(path, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()

    def _post(self, path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        with httpx.Client(base_url=GITHUB_BASE_URL, headers=self._headers) as client:
            response = client.post(path, json=json, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()

    def _put(self, path: str, json: dict[str, Any] | None = None, **kwargs: Any) -> dict[str, Any]:
        with httpx.Client(base_url=GITHUB_BASE_URL, headers=self._headers) as client:
            response = client.put(path, json=json, timeout=30, **kwargs)
            response.raise_for_status()
            return response.json()

    # ------------------------------------------------------------------
    # Pull request
    # ------------------------------------------------------------------

    def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Fetch metadata for a pull request."""
        return self._get(f'/repos/{owner}/{repo}/pulls/{pr_number}')

    def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        *,
        merge_method: str = 'squash',
    ) -> dict[str, Any]:
        """Merge a pull request.

        Parameters
        ----------
        merge_method:
            One of ``"merge"``, ``"squash"``, or ``"rebase"``.
        """
        return self._put(
            f'/repos/{owner}/{repo}/pulls/{pr_number}/merge',
            json={'merge_method': merge_method},
        )

    # ------------------------------------------------------------------
    # Copilot code review
    # ------------------------------------------------------------------

    def request_copilot_review(self, owner: str, repo: str, pr_number: int) -> dict[str, Any]:
        """Ask GitHub Copilot to review a pull request.

        Uses the ``POST /repos/{owner}/{repo}/pulls/{pull_number}/requested_reviewers``
        endpoint with the ``copilot-pull-request-reviewer[bot]`` reviewer.
        """
        return self._post(
            f'/repos/{owner}/{repo}/pulls/{pr_number}/requested_reviewers',
            json={'reviewers': ['copilot-pull-request-reviewer[bot]']},
        )

    def list_reviews(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Return all reviews submitted on a pull request."""
        result = self._get(f'/repos/{owner}/{repo}/pulls/{pr_number}/reviews')
        # GitHub returns a list here
        return result if isinstance(result, list) else []

    def get_latest_copilot_review(
        self, owner: str, repo: str, pr_number: int
    ) -> dict[str, Any] | None:
        """Return the most recent Copilot review, or ``None`` if not found."""
        reviews = self.list_reviews(owner, repo, pr_number)
        copilot_reviews = [
            r for r in reviews if 'copilot' in (r.get('user', {}) or {}).get('login', '').lower()
        ]
        return copilot_reviews[-1] if copilot_reviews else None

    def list_review_comments(self, owner: str, repo: str, pr_number: int) -> list[dict[str, Any]]:
        """Return all inline review comments on a pull request."""
        result = self._get(f'/repos/{owner}/{repo}/pulls/{pr_number}/comments')
        return result if isinstance(result, list) else []

    # ------------------------------------------------------------------
    # Copilot comment resolution (apply suggestions)
    # ------------------------------------------------------------------

    def request_copilot_apply_comments(
        self, owner: str, repo: str, pr_number: int
    ) -> dict[str, Any]:
        """Ask Copilot to apply any pending review suggestions.

        This is done by posting a review-comment reply that triggers
        Copilot's suggestion-application workflow.  The exact mechanism
        depends on Copilot's integration; here we use the dedicated
        ``autofix`` endpoint when available, falling back to a PR comment.
        """
        try:
            return self._post(
                f'/repos/{owner}/{repo}/pulls/{pr_number}/autofix',
                json={'apply_suggestions': True},
            )
        except httpx.HTTPStatusError:
            # Fall back: post a comment instructing Copilot
            return self._post(
                f'/repos/{owner}/{repo}/issues/{pr_number}/comments',
                json={'body': '@github-copilot apply suggestions'},
            )

    def list_check_runs_for_ref(self, owner: str, repo: str, ref: str) -> list[dict[str, Any]]:
        """Return all check runs for a given commit ref."""
        result = self._get(f'/repos/{owner}/{repo}/commits/{ref}/check-runs')
        return result.get('check_runs', [])
