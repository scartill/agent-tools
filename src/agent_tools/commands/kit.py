from pathlib import Path

import click
import rich
import yaml


@click.group(name="kit")
@click.pass_obj
@click.option("--agent", type=click.Choice(["opencode", "kiro", "gemini"]), default="opencode")
def kit_group(obj, agent) -> None:
    """Prompt kit commands"""
    obj["agent"] = agent


@kit_group.group(name="commands")
def commands_group() -> None:
    """Commands for managing agent commands"""
    pass


@commands_group.command(name="add")
@click.pass_obj
@click.argument("component")
def add_command(obj, component):
    templates_dir = Path(__file__).parents[1] / "templates"
    agent = obj["agent"]
    rich.print(f"Installing {component} for {agent}")
    template_def_file = templates_dir / f"{component}.yaml"
    template_def = yaml.safe_load(template_def_file.read_text(encoding="utf-8"))
    command = template_def.get("command")

    if not command:
        rich.print("[red]No command definition found[/red]")
        raise click.Abort()

    if agent not in command.get("compatible", []):
        rich.print("[red]Agent not compatible with this command[/red]")
        raise click.Abort()

    description = command.get("description")

    if not description:
        rich.print("[red]No description found[/red]")
        raise click.Abort()

    prompt_file = command.get("prompt-file")

    if not prompt_file:
        rich.print("[red]No prompt file found[/red]")
        raise click.Abort()

    prompt_file_path = templates_dir / prompt_file

    if not prompt_file_path.exists():
        rich.print("[red]Prompt file not found[/red]")
        raise click.Abort()

    prompt_content = prompt_file_path.read_text(encoding="utf-8")

    command_path, command_content = _transform(agent, component, description, prompt_content)
    command_path.parent.mkdir(exist_ok=True, parents=True)
    command_path.write_text(command_content, encoding="utf-8")
    rich.print(f"[green]Command {component} installed successfully[/green]")


def _transform(agent, name, description, prompt):
    match agent:
        case "kiro":
            return _transform_to_kiro(name, description, prompt)
        case "gemini":
            return _transform_to_gemini(name, description, prompt)
        case "opencode":
            return _transform_to_opencode(name, description, prompt)
        case _:
            raise ValueError(f"Unknown agent: {agent}")


OPENCODE_ARGUMENTS = """\
```text
$ARGUMENTS
```
"""

OPENCODE_MD = """
---
descriptions: {description}
---

{prompt}
"""


def _transform_to_opencode(name, description, prompt):
    path = Path(f".opencode/command/{name}.md")
    agent_prompt = prompt.replace("[<arguments>]", OPENCODE_ARGUMENTS)
    md = OPENCODE_MD.format(description=description, prompt=agent_prompt)
    return path, md


def _transform_to_kiro(name, description, prompt):
    raise NotImplementedError("Kiro not implemented yet")
    # path = Path(f".kiro/command/{name}.md")
    # agent_prompt = prompt.replace("[<arguments>]", KIRO_ARGUMENTS)
    # md = KIRO_MD.format(description=description, prompt=agent_prompt)
    # return path, md


def _transform_to_gemini(name, description, prompt):
    raise NotImplementedError("Gemini not implemented yet")
    # path = Path(f".gemini/command/{name}.md")
    # agent_prompt = prompt.replace("[<arguments>]", GEMINI_ARGUMENTS)
    # md = GEMINI_MD.format(description=description, prompt=agent_prompt)
    # return path, md
