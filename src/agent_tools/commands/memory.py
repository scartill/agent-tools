"""Memory command group for agent-tools CLI.

Provides tools for pinning and recalling factoids via an MCP server.
"""

from pathlib import Path
from typing import List, Literal, Optional

import click
from mcp.server.fastmcp import FastMCP
from rich.console import Console
from rich.table import Table


class MemoryManager:
    """Manages factoids stored in various scopes."""

    def __init__(self):
        self.global_dir = Path.home() / ".scartill" / "pin"
        self.workspaces_root = self.global_dir / "workspaces"
        self.project_dir = Path(".pin")

    def _get_dir(self, location: str) -> Path:
        """Resolve the directory for a given location string."""
        if location == "global":
            return self.global_dir
        if location == "project":
            return self.project_dir
        if location.startswith("workspace/"):
            workspace_name = location.split("/", 1)[1]
            if not workspace_name:
                raise ValueError("Workspace name cannot be empty")
            return self.workspaces_root / workspace_name
        raise ValueError(f"Invalid location: {location}")

    def pin(self, factoid_name: str, factoid: str, location: str = "global") -> str:
        """Store a factoid in memory at the specified location."""
        try:
            target_dir = self._get_dir(location)
        except ValueError as e:
            return f"Error: {e}"

        # Ensure name is safe for filesystem
        safe_name = "".join(c for c in factoid_name if c.isalnum() or c in ("-", "_")).strip()
        if not safe_name:
            return "Error: factoid_name must contain alphanumeric, dashes, or underscores."

        target_dir.mkdir(parents=True, exist_ok=True)
        file_path = target_dir / f"{safe_name}.md"
        try:
            file_path.write_text(factoid, encoding="utf-8")
            return f"Factoid '{factoid_name}' pinned to '{location}' successfully."
        except Exception as e:
            return f"Error writing factoid: {e}"

    def _read_factoids(self, target_dir: Path) -> List[str]:
        """Read all factoids from a specific directory."""
        factoids = []
        if target_dir.exists() and target_dir.is_dir():
            for file in sorted(target_dir.glob("*.md")):
                try:
                    factoids.append(file.read_text(encoding="utf-8"))
                except Exception:
                    continue
        return factoids

    def _get_factoids(self, target_dir: Path) -> List[dict]:
        """Get all factoids from a specific directory as list of dicts {name, content}."""
        results = []
        if target_dir.exists() and target_dir.is_dir():
            for file in sorted(target_dir.glob("*.md")):
                content = None
                # Try common encodings
                for enc in ["utf-8-sig", "utf-16", "latin-1"]:
                    try:
                        content = file.read_text(encoding=enc).strip()
                        break
                    except (UnicodeDecodeError, Exception):
                        continue

                if content is not None:
                    results.append({
                        "name": file.stem,
                        "content": content
                    })
                else:
                    # If we really can't read it, add a placeholder so user knows something is there
                    results.append({
                        "name": file.stem,
                        "content": "[ERROR: Could not decode file content]"
                    })
        return results

    def recall(self, workspace: Optional[str] = None) -> str:
        """Recall pinned factoids from global, optional workspace, and local project scopes."""
        all_factoids: List[str] = []

        # 1. Global factoids - always
        all_factoids.extend(self._read_factoids(self.global_dir))

        # 2. Workspace factoids - if workspace is provided
        if workspace:
            workspace_dir = self.workspaces_root / workspace
            all_factoids.extend(self._read_factoids(workspace_dir))

        # 3. Project factoids - if present
        all_factoids.extend(self._read_factoids(self.project_dir))

        if not all_factoids:
            return "No factoids found in memory."

        return "\n\n".join(all_factoids)

    def list_all(self) -> dict:
        """List all factoids grouped by location."""
        results = {
            "global": self._get_factoids(self.global_dir),
            "workspaces": {},
            "local": self._get_factoids(self.project_dir)
        }

        if self.workspaces_root.exists() and self.workspaces_root.is_dir():
            for workspace_dir in sorted(self.workspaces_root.iterdir()):
                if workspace_dir.is_dir():
                    workspace_factoids = self._get_factoids(workspace_dir)
                    if workspace_factoids:
                        results["workspaces"][workspace_dir.name] = workspace_factoids

        return results


@click.group("memory")
def memory_group() -> None:
    """Memory management commands."""
    pass


@memory_group.command("show")
def memory_show_cmd() -> None:
    """List all factoids grouped by location (global, workspaces, and local)."""
    manager = MemoryManager()
    all_factoids = manager.list_all()
    console = Console()

    def print_section(title: str, factoids: List[dict]):
        if not factoids:
            return
        table = Table(title=title, show_header=True, header_style="bold magenta", box=None)
        table.add_column("Name", style="cyan", no_wrap=True)
        table.add_column("Content", style="green")
        for f in factoids:
            table.add_row(f["name"], f["content"])
        console.print(table)
        console.print()

    # 1. Global
    print_section("Global Factoids", all_factoids["global"])

    # 2. Workspaces
    for ws_name, ws_factoids in sorted(all_factoids["workspaces"].items()):
        print_section(f"Workspace: {ws_name}", ws_factoids)

    # 3. Local
    print_section("Local Project Factoids", all_factoids["local"])

    if not all_factoids["global"] and not all_factoids["workspaces"] and not all_factoids["local"]:
        console.print("[yellow]No factoids found in memory.[/yellow]")


@memory_group.command("install")
@click.option("--workspace", "-w", help="Optional workspace name to include in the instructions.")
def memory_install_cmd(workspace: Optional[str]) -> None:
    """Add agent instructions fragment to AGENTS.md."""
    console = Console()
    agents_file = Path("AGENTS.md")

    start_marker = "<!-- pin mcp start -->"
    stop_marker = "<!-- pin mcp stop -->"

    instruction = (
        "Before staring the first task, fetch all global and project factoids via Pin MCP "
        "and use them as **important** instructions."
    )
    if workspace:
        instruction += f" The Pin workspace for this project is `{workspace}`."

    fragment = f"{start_marker}\n{instruction}\n{stop_marker}\n"

    if agents_file.exists():
        content = agents_file.read_text(encoding="utf-8")
        if start_marker in content:
            console.print("[yellow]AGENTS.md already contains the Pin MCP fragment. Skipping.[/yellow]")
            return
        # Append to existing file
        try:
            with agents_file.open("a", encoding="utf-8") as f:
                # Ensure we start on a new line if the file doesn't end with one
                if content and not content.endswith("\n"):
                    f.write("\n")
                f.write(f"\n{fragment}")
            console.print("[green]Pin MCP fragment added to AGENTS.md.[/green]")
        except Exception as e:
            console.print(f"[red]Error updating AGENTS.md: {e}[/red]")
    else:
        # Create new file
        try:
            agents_file.write_text(fragment, encoding="utf-8")
            console.print("[green]Created AGENTS.md with Pin MCP fragment.[/green]")
        except Exception as e:
            console.print(f"[red]Error creating AGENTS.md: {e}[/red]")


@memory_group.command("mcp")
def memory_mcp_cmd() -> None:
    """Launch the Memory MCP server (stdio)."""
    mcp = FastMCP("Memory")
    manager = MemoryManager()

    @mcp.tool()
    def pin(factoid_name: str, factoid: str, location: Literal["global", "project"] | str) -> str:
        """Store a factoid in memory.

        If asked to pin to a workspace, use "workspace/<name>" for location. Example: "workspace/my-workspace".

        If asked to pin locally or for the current projects, use "project" for location.

        Args:
            factoid_name: The name of the factoid.
            factoid: The fact content.
            location: Where to store it ("global", "workspace/<name>", or "project").
        """  # noqa
        return manager.pin(factoid_name, factoid, location)

    @mcp.tool()
    def recall(workspace: Optional[str] = None) -> str:
        """Recall pinned factoids.

        Returns global, requested workspace, and local project factoids.

        Args:
            workspace: Optional name of the workspace to include.
        """
        return manager.recall(workspace)

    mcp.run()
