"""Jules command group for agent-tools CLI.

Usage example:
    agent-tools jules session create --repository owner/repo --branch main --agent bolt
"""

import sys
from pathlib import Path
from typing import Any

import click
import rich
import yaml

from agent_tools import config
from agent_tools.clients import jules_client
from agent_tools.clients.jules_client import STATE_COMPLETED, STATE_FAILED


@click.group('jules')
def jules_group() -> None:
    """Jules related commands."""
    pass


@jules_group.group('session')
def session_group() -> None:
    """Jules session management commands."""
    pass


@session_group.group('list')
def session_list_group() -> None:
    """List Jules sessions."""
    pass


@session_list_group.command('active')
@click.pass_context
def session_list_active_cmd(ctx: click.Context) -> None:
    """List active (non-archived) Jules sessions."""
    obj: dict[str, Any] = ctx.obj

    try:
        jules_api_key = config.get_jules_api_key(obj.get('jules_api_key'))
    except ValueError as exc:
        rich.print(f'[bold red]Configuration error:[/] {exc}')
        sys.exit(1)

    jules_client_instance = jules_client.JulesClient(api_key=jules_api_key)

    try:
        sessions_resp = jules_client_instance.list_sessions()
        all_sessions = sessions_resp.get('sessions', [])
        inactive_states = {STATE_COMPLETED, STATE_FAILED}
        sessions = [s for s in all_sessions if s.get('state') not in inactive_states]
    except Exception as exc:
        rich.print(f'[bold red]Failed to list sessions:[/] {exc}')
        sys.exit(1)

    if not sessions:
        rich.print('No active sessions found.')
        return

    from rich.table import Table

    table = Table(title='Active Jules Sessions (excluding completed/failed)')
    table.add_column('ID', style='dim')
    table.add_column('Title')
    table.add_column('State')
    table.add_column('PRs')

    for s in sessions:
        s_id = s.get('id', 'N/A')
        title = s.get('title', 'Untitled')
        state = s.get('state', 'UNKNOWN')

        pr_links = []
        for output in s.get('outputs', []):
            pr = output.get('pullRequest')
            if pr and pr.get('url'):
                pr_links.append(pr.get('url'))

        prs = ', '.join(pr_links) if pr_links else '-'

        table.add_row(s_id, title, state, prs)

    rich.print(table)


@session_list_group.command('scheduled')
def session_list_scheduled_cmd() -> None:
    """List scheduled Jules sessions."""
    rich.print('No scheduled sessions found (scheduling API not yet available).')


@session_group.command('create')
@click.option(
    '--repository',
    '-r',
    required=True,
    help='Target GitHub repository in owner/repo format.',
    metavar='OWNER/REPO',
)
@click.option(
    '--branch',
    '-b',
    required=True,
    help='Target branch name for Jules to work against.',
    metavar='BRANCH',
)
@click.option(
    '--agent',
    '-a',
    required=True,
    help='Agent name whose prompt is used (defined in prompts.yaml).',
    metavar='AGENT',
)
@click.option(
    '--title',
    '-t',
    default=None,
    help='Optional title for the session.',
    metavar='TITLE',
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
        jules_api_key = config.get_jules_api_key(obj.get('jules_api_key'))
        # github_pat = config.get_github_pat(obj.get("github_pat"))
    except ValueError as exc:
        rich.print(f'[bold red]Configuration error:[/] {exc}')
        sys.exit(1)

    # Load prompts
    prompts_path: Path = config.get_prompts_path(obj.get('prompts_config'))
    if not prompts_path.exists():
        rich.print(
            f'[bold red]Prompts file not found:[/] {prompts_path}\n'
            'Create prompts.yaml or pass --prompts-config.'
        )
        sys.exit(1)

    prompts_yaml = prompts_path.read_text(encoding='utf-8')
    prompts_data: dict[str, Any] = yaml.safe_load(prompts_yaml)

    agents_cfg: dict[str, Any] = prompts_data.get('agents', {})
    if agent not in agents_cfg:
        available = ', '.join(agents_cfg.keys()) or '(none)'
        rich.print(f'[bold red]Unknown agent {agent!r}.[/] Available agents: {available}')
        sys.exit(1)

    prompt: str = agents_cfg[agent].get('prompt', '')
    if not prompt.strip():
        rich.print(f'[bold red]Agent {agent!r} has an empty prompt.[/]')
        sys.exit(1)

    # Build clients
    jules_client_instance = jules_client.JulesClient(api_key=jules_api_key)
    # github_client_instance = github_client.GitHubClient(pat=github_pat)

    # Parse repository
    parts = repository.split('/', 1)
    if len(parts) != 2 or not all(parts):
        rich.print(f"[bold red]Invalid repository format {repository!r}.[/] Expected 'owner/repo'.")
        sys.exit(1)
    owner, repo = parts

    # Find the source ID for this repository
    source_id = jules_client_instance.find_source_id(owner, repo)
    if not source_id:
        rich.print(f'[bold red]Could not find Jules source for repository {repository}[/]')
        sys.exit(1)

    rich.print(
        f'[bold green]->[/] Creating Jules session for [cyan]{repository}[/] '
        f'on branch [cyan]{branch}[/]'
    )

    try:
        session = jules_client_instance.create_session(
            source=source_id,
            starting_branch=branch,
            prompt=prompt,
            title=title,
        )
    except Exception as exc:
        rich.print(f'[bold red]Failed to create Jules session:[/] {exc}')
        sys.exit(1)

    session_name: str = session.get('name', '')
    session_id: str = session.get('id', '')
    rich.print('[bold green]Session created successfully![/]')
    rich.print(f'  Session ID: [dim]{session_id}[/]')
    rich.print(f'  Session name: [dim]{session_name}[/]')


@jules_group.command('create', deprecated=True)
@click.option(
    '--repository',
    '-r',
    required=True,
    help='Target GitHub repository in owner/repo format.',
    metavar='OWNER/REPO',
)
@click.option(
    '--branch',
    '-b',
    required=True,
    help='Target branch name for Jules to work against.',
    metavar='BRANCH',
)
@click.option(
    '--agent',
    '-a',
    required=True,
    help='Agent name whose prompt is used (defined in prompts.yaml).',
    metavar='AGENT',
)
@click.option(
    '--title',
    '-t',
    default=None,
    help='Optional title for the session.',
    metavar='TITLE',
)
@click.pass_context
def jules_create_legacy_cmd(
    ctx: click.Context,
    repository: str,
    branch: str,
    agent: str,
    title: str | None,
) -> None:
    """Create a new Jules session. Deprecated: use 'jules session create' instead."""
    ctx.invoke(jules_create_cmd, repository=repository, branch=branch, agent=agent, title=title)
