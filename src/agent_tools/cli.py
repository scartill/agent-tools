"""CLI entry point for agent-tools.

Usage example:
    agent-tools refine-loop \\
        --repository owner/repo \\
        --branch main \\
        --agent bolt \\
        --max-cycles 5 \\
        --polling-rate 30
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import click
import yaml
from rich.console import Console

from agent_tools.config import get_github_pat, get_jules_api_key, get_prompts_path
from agent_tools.github_client import GitHubClient
from agent_tools.jules_client import JulesClient

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
# refine-loop command
# ---------------------------------------------------------------------------


@cli.command("refine-loop")
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
    "--max-cycles",
    "-n",
    default=1,
    show_default=True,
    help="Maximum number of refine cycles to execute.",
    type=click.IntRange(min=1),
    metavar="N",
)
@click.option(
    "--polling-rate",
    default=30,
    show_default=True,
    help="Seconds to wait between status poll requests.",
    type=click.IntRange(min=1),
    metavar="SECONDS",
)
@click.option(
    "--automerge/--no-automerge",
    default=False,
    show_default=True,
    help="Automatically merge each PR without asking for confirmation.",
)
@click.option(
    "--restart",
    is_flag=True,
    default=False,
    show_default=True,
    help="Restart from scratch, ignoring any existing checkpoint file.",
)
@click.option(
    "--checkpoint-path",
    default=None,
    help="Path to the checkpoint file (default: .checkpoint.json in current directory).",
    metavar="PATH",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
)
@click.pass_context
def refine_loop_cmd(
    ctx: click.Context,
    repository: str,
    branch: str,
    agent: str,
    max_cycles: int,
    polling_rate: int,
    automerge: bool,
    restart: bool,
    checkpoint_path: str | None,
) -> None:
    """Run the refine loop: Jules session → Copilot review → apply → merge."""
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

    # Pass checkpoint configuration
    restart_flag = restart
    checkpoint_file = Path(checkpoint_path) if checkpoint_path else None

    # Run the loop
    from agent_tools.commands.refine_loop import refine_loop

    refine_loop(
        jules=jules_client,
        github=github_client,
        repository=repository,
        branch=branch,
        prompt=prompt,
        max_cycles=max_cycles,
        polling_rate=polling_rate,
        automerge=automerge,
        restart=restart_flag,
        checkpoint_path=checkpoint_file,
    )


# ---------------------------------------------------------------------------
# Package entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Package entry point registered in pyproject.toml."""
    cli()
