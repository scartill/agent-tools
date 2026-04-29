# agent-tools 🛠️

`agent-tools` is a Python CLI suite designed to orchestrate AI-powered development workflows. It bridges the gap between high-level AI orchestration (like **Jules**) and local development environments, enabling automated coding sessions, performance optimizations, and persistent memory for AI agents.

## Features

- **Jules Integration**: Create and manage Jules coding sessions directly from your terminal.
- **Persistent Memory (MCP)**: A Model Context Protocol (MCP) server for agents to "pin" and "recall" factoids across different scopes (Global, Workspace, Project).
- **Agent Prompts**: Define specialized AI agents (like `bolt` for performance) with custom system prompts in a simple YAML configuration.

## Installation

This project uses [uv](https://docs.astral.sh/uv/) for fast, reliable dependency management.

```bash
# Clone the repository
git clone https://github.com/scartill/agent-tools.git
cd agent-tools

# Install dependencies and create a virtual environment
uv sync
```

## Configuration

The tool requires API credentials to interact with external services. You can provide these via environment variables, a `.env` file, or CLI flags.

### Credentials

- `JULES_API_KEY`: Required for interacting with the Jules API.
- `GITHUB_PAT`: GitHub Personal Access Token for repository interactions.

Example `.env` file:

```javascript
JULES_API_KEY=your_jules_key
GITHUB_PAT=your_github_token
```

### Agent Prompts (`prompts.yaml`)

Define your AI agents in `prompts.yaml` in the project root:

```yaml
agents:
  bolt:
    prompt: |
      You are "Bolt" ⚡ - a performance-obsessed agent...
      (Full prompt text here)
```

## Usage

### Memory Management

Manage and inspect your persistent factoids.

```bash
# List all factoids grouped by location
uv run agent-tools memory show

# Launch the MCP server
uv run agent-tools memory mcp
```

#### `memory show`

Displays all stored factoids in a formatted view, grouped by:

- **Global**: `~/.scartill/pin/`
- **Workspaces**: `~/.scartill/pin/workspaces/<name>/`
- **Local**: `./.pin/`

#### `memory mcp` (Server)

Launches the Model Context Protocol (MCP) server that provides agents with tools to store and retrieve information.

### MCP Configuration Example

To use `agent-tools` as an MCP server in applications like Claude Desktop or other MCP-compatible clients, it is recommended to install it globally using `uv`.

#### 1. Install the tool

````bash
uv tool install --editable .  # For local development
# OR
uv tool install agent-tools   # Once publ2. Configure your client

Add this (or similar) to your MCP config JSON:

```json
{
  "mcpServers": {
    "agent-tools-memory": {
      "command": "uvx",
      "args": ["path/to/gent-tools", "memory", "mcp"],
    }
  }
}
````

*Note: If installed via uv tool install, you can simply use "command": "agent-tools".*

#### MCP Tools:

1. **pin**: Store a factoid.
   - `factoid_name`: A unique name for the factoid.
   - `factoid`: The content to store.
   - `location`: Scoped storage location:
     - `global`: Stored in `~/.pin/` (available everywhere).
     - `workspace/<name>`: Stored in `~/.pin/workspaces/<name>/`.
     - `project`: Stored in `./.pin/` (local to the current directory).
2. **recall**: Retrieve stored factoids.
   - `workspace`: (Optional) Name of the workspace to include.
   - **Returns**: A concatenation of Global factoids, Workspace factoids (if specified), and Project factoids (if present).

### Jules Commands

Create an automated coding session.

```bash
uv run agent-tools jules create \
  --repository owner/repo \
  --branch feature-branch \
  --agent bolt \
  --title "Performance optimization for API"
```

**Options:**

- `--repository`, `-r`: Target GitHub repository (owner/repo).
- `--branch`, `-b`: Branch for Jules to work on.
- `--agent`, `-a`: Name of the agent defined in `prompts.yaml`.
- `--title`, `-t`: (Optional) Title for the session.

## Project Structure

- `src/agent_tools/cli.py`: CLI entry point and command registration.
- `src/agent_tools/config.py`: Configuration and environment management.
- `src/agent_tools/clients/`: API clients for Jules and GitHub.
- `src/agent_tools/commands/`: Implementation logic for CLI commands.
  - `memory.py`: Implementation of the Memory MCP server.
- `kit/`: Reusable tool definitions and prompts for agent-led workflows.

## Development

### Running Tests & Linting

```bash
# Lint with ruff
uv run ruff check .

# Fix linting issues
uv run ruff check --fix .
```

### Roadmap

- Add `jules status` to track session progress.
- Integration with GitHub Copilot Review API.

## License

MIT License - Copyright (c) 2026 Boris Resnick
