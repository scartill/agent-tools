"""CLI entry point for agent-tools.

Usage example:
    agent-tools jules create --repository owner/repo --branch main
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console

from agent_tools.config import get_github_pat, get_jules_api_key, get_prompts_path
from agent_tools.clients.github_client import GitHubClient
from agent_tools.clients.jules_client import JulesClient

console = Console()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------


@click.group()
@click.option(
    "--jules-api-key",
    envvar="JULES_API_KEY",
    default=None,
    help="Jules API key (overrides JULES_API_KEY env var / .env).",
    metavar="KEY",
)
@click.option(
    "--github-pat",
    envvar="GITHUB_PAT",
    default=None,
    help="GitHub Personal Access Token (overrides GITHUB_PAT env var / .env).",
    metavar="TOKEN",
)
@click.option(
    "--prompts-config",
    default=None,
    help="Path to the prompts YAML config (default: prompts.yaml).",
    metavar="PATH",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
)
@click.pass_context
def cli(
    ctx: click.Context,
    jules_api_key: str | None,
    github_pat: str | None,
    prompts_config: str | None,
) -> None:
    """agent-tools – CLI suite for AI-powered development workflows."""
    ctx.ensure_object(dict)
    ctx.obj["jules_api_key"] = jules_api_key
    ctx.obj["github_pat"] = github_pat
    ctx.obj["prompts_config"] = prompts_config


# ---------------------------------------------------------------------------
# Jules command group
# ---------------------------------------------------------------------------


@cli.group("jules")
def jules_group() -> None:
    """Jules session management commands."""
    pass


@jules_group.command("create")
@click.option(
    "--repository",
    "-r",
    required=True,
    help="Target GitHub repository in owner/repo format.",
    metavar="OWNER/REPO",
)
@click.option(
    "--branch",
    "-b",
    required=True,
    help="Target branch name for Jules to work against.",
    metavar="BRANCH",
)
@click.option(
    "--agent",
    "-a",
    required=True,
    help="Agent name whose prompt is used (defined in prompts.yaml).",
    metavar="AGENT",
)
@click.option(
    "--title",
    "-t",
    default=None,
    help="Optional title for the session.",
    metavar="TITLE",
)
@click.pass_context
def jules_create_cmd(
    ctx: click.Context,
    repository: str,
    branch: str,
    agent: str,
    title: str | None,
) -> None:
    """Create a new Jules session."""
    obj: dict[str, Any] = ctx.obj

    # Resolve credentials
    try:
        jules_api_key = get_jules_api_key(obj.get("jules_api_key"))
        github_pat = get_github_pat(obj.get("github_pat"))
    except ValueError as exc:
        console.print(f"[bold red]Configuration error:[/] {exc}")
        sys.exit(1)

    # Load prompts
    prompts_path: Path = get_prompts_path(obj.get("prompts_config"))
    if not prompts_path.exists():
        console.print(
            f"[bold red]Prompts file not found:[/] {prompts_path}\n"
            "Create prompts.yaml or pass --prompts-config."
        )
        sys.exit(1)

    prompts_yaml = prompts_path.read_text(encoding="utf-8")
    prompts_data: dict[str, Any] = yaml.safe_load(prompts_yaml)

    agents_cfg: dict[str, Any] = prompts_data.get("agents", {})
    if agent not in agents_cfg:
        available = ", ".join(agents_cfg.keys()) or "(none)"
        console.print(f"[bold red]Unknown agent {agent!r}.[/] Available agents: {available}")
        sys.exit(1)

    prompt: str = agents_cfg[agent].get("prompt", "")
    if not prompt.strip():
        console.print(f"[bold red]Agent {agent!r} has an empty prompt.[/]")
        sys.exit(1)

    # Build clients
    jules_client = JulesClient(api_key=jules_api_key)
    github_client = GitHubClient(pat=github_pat)

    # Parse repository
    parts = repository.split("/", 1)
    if len(parts) != 2 or not all(parts):
        console.print(
            f"[bold red]Invalid repository format {repository!r}.[/] Expected 'owner/repo'."
        )
        sys.exit(1)
    owner, repo = parts

    # Find the source ID for this repository
    source_id = jules_client.find_source_id(owner, repo)
    if not source_id:
        console.print(f"[bold red]Could not find Jules source for repository {repository}[/]")
        sys.exit(1)

    console.print(
        f"[bold green]->[/] Creating Jules session for [cyan]{repository}[/] "
        f"on branch [cyan]{branch}[/]"
    )

    try:
        session = jules_client.create_session(
            source=source_id,
            starting_branch=branch,
            prompt=prompt,
            title=title,
        )
    except Exception as exc:
        console.print(f"[bold red]Failed to create Jules session:[/] {exc}")
        sys.exit(1)

    session_name: str = session.get("name", "")
    session_id: str = session.get("id", "")
    console.print(f"[bold green]Session created successfully![/]")
    console.print(f"  Session ID: [dim]{session_id}[/]")
    console.print(f"  Session name: [dim]{session_name}[/]")


# ---------------------------------------------------------------------------
# Package entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Package entry point registered in pyproject.toml."""
    cli()
