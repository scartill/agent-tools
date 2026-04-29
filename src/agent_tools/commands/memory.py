"""Memory command group for agent-tools CLI.

Provides tools for pinning and recalling factoids via an MCP server.
"""

from pathlib import Path
from typing import List, Literal, Optional

import click
from mcp.server.fastmcp import FastMCP


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


@click.group("memory")
def memory_group() -> None:
    """Memory management commands."""
    pass


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
