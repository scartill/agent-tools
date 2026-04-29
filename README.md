# agent-tools 🛠️

`agent-tools` is a Python CLI suite designed to orchestrate AI-powered development workflows. It bridges the gap between high-level AI orchestration (like **Jules**) and local development environments, enabling automated coding sessions, performance optimizations, and smart code reviews.

## Features

- **Jules Integration**: Create and manage Jules coding sessions directly from your terminal.
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
```env
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

### Jules Commands

Currently, the primary command is `jules create`, which starts a new automated coding session.

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
- [ ] Add `jules status` to track session progress.
- [ ] Integration with GitHub Copilot Review API.

## License

MIT License - Copyright (c) 2026 Boris Resnick
