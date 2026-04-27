"""Checkpoint management for agent-tools.

Provides functionality to save and restore the state of long-running operations,
allowing them to be resumed if interrupted.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

# Step identifiers for tracking progress within a cycle
STEP_INIT = "init"
STEP_JULES_SESSION_CREATED = "jules_session_created"
STEP_JULES_SESSION_COMPLETED = "jules_session_completed"
STEP_PR_CREATED = "pr_created"
STEP_COPILOT_REVIEW_REQUESTED = "copilot_review_requested"
STEP_COPILOT_REVIEW_COMPLETED = "copilot_review_completed"
STEP_COPILOT_APPLY_REQUESTED = "copilot_apply_requested"
STEP_COPILOT_APPLY_COMPLETED = "copilot_apply_completed"
STEP_MERGED = "merged"
STEP_COMPLETED = "completed"

# All steps in order
ALL_STEPS = [
    STEP_INIT,
    STEP_JULES_SESSION_CREATED,
    STEP_JULES_SESSION_COMPLETED,
    STEP_PR_CREATED,
    STEP_COPILOT_REVIEW_REQUESTED,
    STEP_COPILOT_REVIEW_COMPLETED,
    STEP_COPILOT_APPLY_REQUESTED,
    STEP_COPILOT_APPLY_COMPLETED,
    STEP_MERGED,
    STEP_COMPLETED,
]


@dataclass
class Checkpoint:
    """Represents the checkpoint state for a refine-loop operation."""

    repository: str
    branch: str
    agent: str
    prompt: str
    max_cycles: int
    current_cycle: int = 0
    completed_cycles: int = 0
    current_step: str = STEP_INIT
    last_session_name: str | None = None
    last_pr_url: str | None = None
    last_pr_number: int | None = None
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    version: int = 1

    def to_dict(self) -> dict[str, Any]:
        """Convert checkpoint to a dictionary for serialization."""
        return {
            "repository": self.repository,
            "branch": self.branch,
            "agent": self.agent,
            "prompt": self.prompt,
            "max_cycles": self.max_cycles,
            "current_cycle": self.current_cycle,
            "completed_cycles": self.completed_cycles,
            "current_step": self.current_step,
            "last_session_name": self.last_session_name,
            "last_pr_url": self.last_pr_url,
            "last_pr_number": self.last_pr_number,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Checkpoint":
        """Create a Checkpoint from a dictionary."""
        return cls(
            repository=data.get("repository", ""),
            branch=data.get("branch", ""),
            agent=data.get("agent", ""),
            prompt=data.get("prompt", ""),
            max_cycles=data.get("max_cycles", 1),
            current_cycle=data.get("current_cycle", 0),
            completed_cycles=data.get("completed_cycles", 0),
            current_step=data.get("current_step", STEP_INIT),
            last_session_name=data.get("last_session_name"),
            last_pr_url=data.get("last_pr_url"),
            last_pr_number=data.get("last_pr_number"),
            created_at=data.get("created_at", datetime.utcnow().isoformat()),
            updated_at=data.get("updated_at", datetime.utcnow().isoformat()),
            version=data.get("version", 1),
        )

    def step_index(self) -> int:
        """Get the index of the current step in ALL_STEPS."""
        try:
            return ALL_STEPS.index(self.current_step)
        except ValueError:
            return 0

    def can_resume_at_step(self, step: str) -> bool:
        """Check if we can resume at the given step (i.e., we haven't completed it yet)."""
        try:
            our_idx = self.step_index()
            their_idx = ALL_STEPS.index(step)
            return their_idx > our_idx
        except ValueError:
            return False

    def set_step(self, step: str) -> None:
        """Set the current step and update the timestamp."""
        if step in ALL_STEPS:
            self.current_step = step
            self.updated_at = datetime.utcnow().isoformat()

    def is_compatible(self, params: dict[str, Any]) -> bool:
        """Check if this checkpoint is compatible with the given parameters.

        A checkpoint is compatible if the repository, branch, agent, prompt,
        and max_cycles match. This allows resuming an interrupted operation
        with the same configuration.
        """
        return (
            self.repository == params.get("repository")
            and self.branch == params.get("branch")
            and self.agent == params.get("agent")
            and self.prompt == params.get("prompt")
            and self.max_cycles == params.get("max_cycles")
        )

    def save(self, path: Path) -> None:
        """Save checkpoint to a JSON file."""
        self.updated_at = datetime.utcnow().isoformat()
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "Checkpoint | None":
        """Load checkpoint from a JSON file.

        Returns None if the file doesn't exist or is invalid.
        """
        if not path.exists():
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return cls.from_dict(data)
        except (json.JSONDecodeError, KeyError, TypeError):
            return None


def get_checkpoint_path(cwd: Path | None = None) -> Path:
    """Get the default checkpoint file path (.checkpoint.json in current directory)."""
    if cwd is None:
        cwd = Path.cwd()
    return cwd / ".checkpoint.json"


def save_checkpoint(
    checkpoint: Checkpoint,
    path: Path | None = None,
) -> None:
    """Save a checkpoint to the default location."""
    if path is None:
        path = get_checkpoint_path()
    checkpoint.save(path)


def load_checkpoint(path: Path | None = None) -> Checkpoint | None:
    """Load a checkpoint from the default location."""
    if path is None:
        path = get_checkpoint_path()
    return Checkpoint.load(path)


def remove_checkpoint(path: Path | None = None) -> bool:
    """Remove the checkpoint file.

    Returns True if the file was removed, False if it didn't exist.
    """
    if path is None:
        path = get_checkpoint_path()
    if path.exists():
        path.unlink()
        return True
    return False
