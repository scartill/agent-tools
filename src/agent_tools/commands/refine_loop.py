"""refine-loop command implementation.

Each cycle:
1. Create a Jules session (open-PR mode) for the configured repo/branch/prompt.
2. Poll until a PR is open (or Jules pauses).
3. Ask Copilot to review the PR.
4. Monitor Copilot's review session until it finishes.
5. Ask Copilot to apply any review comments.
6. Monitor Copilot's comment-resolution session until it finishes.
7. Prompt the user for merge confirmation; merge and continue.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import httpx
from rich.console import Console
from rich.prompt import Confirm
from rich.status import Status

from agent_tools.checkpoint import (
    Checkpoint,
    get_checkpoint_path,
    load_checkpoint,
    remove_checkpoint,
    save_checkpoint,
)
from agent_tools.github_client import GitHubClient
from agent_tools.jules_client import (
    PR_STATES,
    TERMINAL_STATES,
    JulesClient,
)

console = Console()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_owner_repo(repository: str) -> tuple[str, str]:
    """Split ``owner/repo`` into a ``(owner, repo)`` tuple."""
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(parts):
        raise ValueError(f"Invalid repository format {repository!r}. Expected 'owner/repo'.")
    return parts[0], parts[1]


def _poll_jules_session(
    jules: JulesClient,
    session_name: str,
    polling_rate: int,
) -> dict[str, Any]:
    """Poll a Jules session until it reaches a terminal state.

    Returns the final session dict.
    """
    with Status("[bold cyan]Waiting for Jules to open a PR…", console=console) as status:
        while True:
            session = jules.get_session(session_name)
            state: str = session.get("state", "unknown")
            status.update(f"[bold cyan]Jules session state: [yellow]{state}")

            if state in TERMINAL_STATES:
                return session

            time.sleep(polling_rate)


def _poll_copilot_review(
    github: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    polling_rate: int,
) -> dict[str, Any] | None:
    """Poll until Copilot has submitted a review.

    Returns the review dict, or ``None`` if no review was found.
    """
    with Status("[bold cyan]Waiting for Copilot review…", console=console) as status:
        while True:
            review = github.get_latest_copilot_review(owner, repo, pr_number)
            if review and review.get("state", "") not in ("PENDING",):
                return review
            status.update("[bold cyan]Copilot review still pending…")
            time.sleep(polling_rate)


def _poll_copilot_apply(
    github: GitHubClient,
    owner: str,
    repo: str,
    pr_number: int,
    head_sha: str,
    polling_rate: int,
) -> None:
    """Poll check runs until Copilot's apply-suggestions run completes."""
    with Status("[bold cyan]Waiting for Copilot to apply comments…", console=console) as status:
        while True:
            runs = github.list_check_runs_for_ref(owner, repo, head_sha)
            copilot_runs = [
                r
                for r in runs
                if "copilot" in (r.get("app", {}) or {}).get("slug", "").lower()
                or "copilot" in (r.get("name", "") or "").lower()
            ]
            if copilot_runs:
                all_done = all(r.get("status") == "completed" for r in copilot_runs)
                if all_done:
                    return
            status.update(
                f"[bold cyan]Copilot apply-comments: "
                f"{len([r for r in copilot_runs if r.get('status') == 'completed'])}/"
                f"{len(copilot_runs)} runs completed"
            )
            time.sleep(polling_rate)


# ---------------------------------------------------------------------------
# Checkpoint management
# ---------------------------------------------------------------------------


def _load_or_create_checkpoint(
    repository: str,
    branch: str,
    agent: str,
    prompt: str,
    max_cycles: int,
    checkpoint_path: Path | None,
    restart: bool,
) -> tuple[Checkpoint, bool]:
    """Load existing checkpoint or create a new one.

    Returns a tuple of (checkpoint, is_resuming).
    - checkpoint: The loaded or newly created checkpoint
    - is_resuming: True if resuming from an existing checkpoint, False if starting fresh
    """
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()

    # If restart flag is set, remove any existing checkpoint
    if restart and checkpoint_path.exists():
        remove_checkpoint(checkpoint_path)
        is_resuming = False
    else:
        # Try to load existing checkpoint
        checkpoint = load_checkpoint(checkpoint_path)
        if checkpoint is not None:
            # Check if checkpoint is compatible with current parameters
            current_params = {
                "repository": repository,
                "branch": branch,
                "agent": agent,
                "prompt": prompt,
                "max_cycles": max_cycles,
            }
            if checkpoint.is_compatible(current_params):
                console.print(
                    f"[bold yellow]⏎ Resuming from checkpoint at cycle {checkpoint.current_cycle + 1}/{checkpoint.max_cycles}[/]"
                )
                return checkpoint, True
            else:
                console.print(
                    "[bold yellow]⚠ Existing checkpoint is not compatible with current parameters. "
                    "Starting fresh.[/]"
                )

        is_resuming = False

    # Create a new checkpoint
    checkpoint = Checkpoint(
        repository=repository,
        branch=branch,
        agent=agent,
        prompt=prompt,
        max_cycles=max_cycles,
        current_cycle=0,
        completed_cycles=0,
    )
    return checkpoint, False


def _save_checkpoint(
    checkpoint: Checkpoint,
    checkpoint_path: Path | None,
) -> None:
    """Save checkpoint state."""
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()
    save_checkpoint(checkpoint, checkpoint_path)


def _cleanup_checkpoint(
    checkpoint: Checkpoint,
    checkpoint_path: Path | None,
) -> None:
    """Remove checkpoint file after successful completion."""
    if checkpoint_path is None:
        checkpoint_path = get_checkpoint_path()
    # Only remove if we completed all cycles
    if checkpoint.completed_cycles >= checkpoint.max_cycles:
        remove_checkpoint(checkpoint_path)


# ---------------------------------------------------------------------------
# Single cycle
# ---------------------------------------------------------------------------


def run_single_cycle(
    *,
    jules: JulesClient,
    github: GitHubClient,
    repository: str,
    branch: str,
    prompt: str,
    polling_rate: int,
    automerge: bool,
    cycle_number: int,
    checkpoint: Checkpoint,
    checkpoint_path: Path | None,
) -> bool:
    """Execute a single refine-loop cycle.

    Returns ``True`` if the cycle completed successfully (PR was merged),
    ``False`` if it should be skipped or the user declined to merge.
    """
    owner, repo = _parse_owner_repo(repository)
    console.rule(f"[bold blue]Cycle {cycle_number}")

    # ------------------------------------------------------------------
    # Step 1: Create Jules session
    # ------------------------------------------------------------------
    console.print(
        f"[bold green]→[/] Creating Jules session for "
        f"[cyan]{repository}[/] on branch [cyan]{branch}[/]"
    )

    # Find the source ID for this repository
    source_id = jules.find_source_id(owner, repo)
    if not source_id:
        console.print(
            f"[bold red]✗ Could not find Jules source for repository {repository}[/]"
        )
        return False

    try:
        session = jules.create_session(
            source=source_id,
            starting_branch=branch,
            prompt=prompt,
        )
    except httpx.HTTPError as exc:
        console.print(f"[bold red]✗ Failed to create Jules session:[/] {exc}")
        return False

    # The session name is in format "sessions/{id}"
    session_name: str = session.get("name", "")
    session_id: str = session.get("id", "")
    console.print(f"  Session ID: [dim]{session_id}[/]")

    # ------------------------------------------------------------------
    # Step 2: Poll until PR opens (or session pauses)
    # ------------------------------------------------------------------
    try:
        final_session = _poll_jules_session(jules, session_name, polling_rate)
    except httpx.HTTPError as exc:
        console.print(f"[bold red]✗ Error polling Jules session:[/] {exc}")
        return False

    final_state: str = final_session.get("state", "unknown")

    # Check if we're in a terminal state without a PR
    if final_state not in PR_STATES:
        console.print(
            f"[bold yellow]⚠ Jules session reached terminal state {final_state!r} "
            f"without opening a PR. Skipping cycle.[/]"
        )
        return False

    # Extract PR information from session outputs
    pr_url, pr_number = jules.extract_pr_info(final_session)

    if pr_number is None:
        console.print(
            f"[bold red]✗ Jules did not return a PR number (state={final_state!r}). "
            f"Skipping cycle.[/]"
        )
        return False

    console.print(f"[bold green]✓ PR opened:[/] {pr_url}")

    # ------------------------------------------------------------------
    # Step 3: Ask Copilot to review
    # ------------------------------------------------------------------
    console.print("[bold green]→[/] Requesting Copilot code review…")
    try:
        github.request_copilot_review(owner, repo, pr_number)
    except httpx.HTTPError as exc:
        console.print(f"[bold yellow]⚠ Could not request Copilot review:[/] {exc}")
        # Non-fatal – continue without automated review

    # ------------------------------------------------------------------
    # Step 4: Monitor Copilot review session
    # ------------------------------------------------------------------
    review: dict[str, Any] | None = None
    try:
        review = _poll_copilot_review(github, owner, repo, pr_number, polling_rate)
    except httpx.HTTPError as exc:
        console.print(f"[bold yellow]⚠ Error monitoring Copilot review:[/] {exc}")

    if review:
        review_state = review.get("state", "unknown")
        console.print(f"[bold green]✓ Copilot review complete:[/] state={review_state!r}")
    else:
        console.print("[bold yellow]⚠ No Copilot review found; proceeding.[/]")

    # ------------------------------------------------------------------
    # Step 5: Ask Copilot to apply comments (if any)
    # ------------------------------------------------------------------
    try:
        comments = github.list_review_comments(owner, repo, pr_number)
    except httpx.HTTPError as exc:
        console.print(f"[bold yellow]⚠ Could not list review comments:[/] {exc}")
        comments = []

    if comments:
        console.print(f"[bold green]→[/] Asking Copilot to apply {len(comments)} comment(s)…")
        try:
            github.request_copilot_apply_comments(owner, repo, pr_number)
        except httpx.HTTPError as exc:
            console.print(f"[bold yellow]⚠ Could not trigger Copilot apply:[/] {exc}")

        # Step 6: Monitor comment resolution
        pr_meta = github.get_pull_request(owner, repo, pr_number)
        head_sha: str = pr_meta.get("head", {}).get("sha", "")
        if head_sha:
            try:
                _poll_copilot_apply(github, owner, repo, pr_number, head_sha, polling_rate)
                console.print("[bold green]✓ Copilot comment resolution done.[/]")
            except httpx.HTTPError as exc:
                console.print(f"[bold yellow]⚠ Error monitoring Copilot apply:[/] {exc}")
    else:
        console.print("[dim]No review comments to apply.[/]")

    # ------------------------------------------------------------------
    # Step 7: Merge confirmation & merge
    # ------------------------------------------------------------------
    console.print(f"\n[bold]PR ready:[/] {pr_url}")

    if automerge:
        do_merge = True
        console.print("[dim](automerge enabled – merging automatically)[/]")
    else:
        do_merge = Confirm.ask("Merge this PR?", default=True)

    if not do_merge:
        console.print("[bold yellow]⚠ Merge declined. Moving to next cycle.[/]")
        return False

    try:
        github.merge_pull_request(owner, repo, pr_number)
        console.print("[bold green]✓ PR merged successfully.[/]")
    except httpx.HTTPError as exc:
        console.print(f"[bold red]✗ Failed to merge PR:[/] {exc}")
        return False

    # Update checkpoint state
    checkpoint.last_session_name = session_name
    checkpoint.last_pr_url = pr_url
    checkpoint.last_pr_number = pr_number

    return True


# ---------------------------------------------------------------------------
# Main loop entry point
# ---------------------------------------------------------------------------


def refine_loop(
    *,
    jules: JulesClient,
    github: GitHubClient,
    repository: str,
    branch: str,
    prompt: str,
    max_cycles: int,
    polling_rate: int,
    automerge: bool,
    restart: bool = False,
    checkpoint_path: Path | None = None,
) -> None:
    """Run the refine loop for up to *max_cycles* iterations.

    Parameters
    ----------
    jules:
        Jules REST API client.
    github:
        GitHub REST API client.
    repository:
        Target GitHub repository in owner/repo format.
    branch:
        Target branch for Jules to work against.
    prompt:
        The prompt to send to Jules.
    max_cycles:
        Maximum number of cycles to run.
    polling_rate:
        Seconds between poll requests.
    automerge:
        Whether to automatically merge without confirmation.
    restart:
        Whether to restart from scratch (ignore checkpoint).
    checkpoint_path:
        Optional path to the checkpoint file.
    """
    # Load or create checkpoint
    checkpoint, is_resuming = _load_or_create_checkpoint(
        repository=repository,
        branch=branch,
        agent="",  # Agent is not stored in checkpoint but used for compatibility check
        prompt=prompt,
        max_cycles=max_cycles,
        checkpoint_path=checkpoint_path,
        restart=restart,
    )

    # Update checkpoint with agent info (for future compatibility checks)
    # Note: We set agent here because it might have been loaded from checkpoint
    if checkpoint.agent == "" and is_resuming:
        checkpoint.agent = "unknown"

    console.print(
        f"[bold]Starting refine-loop[/] for [cyan]{repository}[/] "
        f"branch=[cyan]{branch}[/] max_cycles={max_cycles}"
    )

    if is_resuming:
        completed = checkpoint.completed_cycles
        start_cycle = checkpoint.current_cycle + 1
        console.print(
            f"[dim]Resuming from cycle {start_cycle} (completed {completed}/{max_cycles})[/]"
        )
    else:
        completed = 0
        start_cycle = 1

    # Run cycles from start_cycle to max_cycles
    for cycle_number in range(start_cycle, max_cycles + 1):
        success = run_single_cycle(
            jules=jules,
            github=github,
            repository=repository,
            branch=branch,
            prompt=prompt,
            polling_rate=polling_rate,
            automerge=automerge,
            cycle_number=cycle_number,
            checkpoint=checkpoint,
            checkpoint_path=checkpoint_path,
        )

        # Update checkpoint after each cycle
        checkpoint.current_cycle = cycle_number
        if success:
            checkpoint.completed_cycles += 1

        _save_checkpoint(checkpoint, checkpoint_path)

        if success:
            completed += 1

    # Clean up checkpoint if we completed all cycles
    _cleanup_checkpoint(checkpoint, checkpoint_path)

    console.rule("[bold blue]Done")
    console.print(
        f"[bold green]Refine-loop finished.[/] "
        f"Completed {completed}/{max_cycles} cycle(s) successfully."
    )
