import click
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
    templates_dir = Path(__file__).parent
    agent = obj["agent"]
    rich.print(f"Selected agent {agent}")
    rich.print(f"Templates dir {templates_dir}")
    rich.print(f"Component {component}")
