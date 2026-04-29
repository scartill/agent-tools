"""CLI entry point for agent-tools.

Usage example:
    agent-tools jules create --repository owner/repo --branch main
"""

import click
from rich.console import Console

from agent_tools.commands.jules import jules_group

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
# Register command groups
# ---------------------------------------------------------------------------


cli.add_command(jules_group)


# ---------------------------------------------------------------------------
# Package entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """Package entry point registered in pyproject.toml."""
    cli()
