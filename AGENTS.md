# Project Instructions

This document provides context and instructions for AI agents working on the `agent-tools` project.

## Project Overview

`agent-tools` is a Python CLI suite that orchestrates AI-powered development workflows. It integrates with **Jules** (for automated coding sessions) and **GitHub Copilot** (for code reviews and automated fixes).

### Main Technologies

- **Python:** 3.12+
- **Project Manager:** [uv](https://docs.astral.sh/uv/)
- **CLI Framework:** [Click](https://click.palletsproject.com/)
- **API Clients:** `httpx` for REST API interactions.
- **Terminal UI:** `rich` for formatted output and progress indicators.
- **Linting/Formatting:** `ruff`.

### Architecture

The project follows a modular structure:

- `src/agent_tools/cli.py`: Main entry point and CLI group definitions.
- `src/agent_tools/config.py`: Handles configuration loading from environment variables and `.env` files.
- `src/agent_tools/clients/`: contains thin wrappers around external APIs.
  - `jules_client.py`: Jules REST API interactions.
  - `github_client.py`: GitHub REST API interactions (including Copilot features).
- `src/agent_tools/commands/`: Logic for specific CLI commands.
  - `jules.py`: Commands related to Jules session management (e.g., `agent-tools jules create`).

## Building and Running

### Development Setup

```bash
# Install dependencies and create virtual environment
uv sync

# Run the CLI
uv run agent-tools --help
```

### Configuration

The tool requires two main credentials, which can be provided via environment variables, a `.env` file, or CLI flags:

- `JULES_API_KEY`: For Jules API access.
- `GITHUB_PAT`: GitHub Personal Access Token.

A `prompts.yaml` file is used to define agent prompts:

```yaml
agents:
  bolt:
    prompt: |
      Your task description here.
```


## Development Conventions

### Coding Style

- Follow PEP 8 standards.
- Use type hints for all function signatures.
- Use `ruff` for linting and formatting:

### External API Interactions

- All external API calls should be encapsulated within the `clients/` directory.
- Use `httpx` for synchronous/asynchronous HTTP requests.

### CLI Structure

- Commands are grouped using Click groups.
- Prefer `rich` for any user-facing outpud in the `README.md` (currently only `jules cr of GitHub Copilot review and apply logic in the orchestration commands.


<!-- pin mcp start -->
Before staring the first task, fetch all global and project factoids via Pin MCP and use them as **important** instructions.
<!-- pin mcp stop -->
