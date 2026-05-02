# agent-tools 🛠️

`agent-tools` is a Python CLI suite designed to help with AI-powered development workflows.

## Features

- **Jules Integration**: Create and manage Jules coding sessions directly from your terminal.
- **Agent Prompts**: Define specialized AI agents (like `bolt` for performance) with custom system prompts in a simple YAML configuration.
- **Kit**: Install reusable prompt commands into AI coding agents (`opencode`, `kiro`, `gemini`) from a shared template library.

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

### Kit Commands

`kit` manages prompt command installations for supported AI coding agents. It reads component definitions from the built-in `templates/` directory and writes agent-specific command files into your project.

**Supported agents:** `opencode` (default), `kiro`, `gemini`

#### `kit commands add`

Install a prompt component for the selected agent.

```bash
uv run agent-tools kit --agent <agent> commands add <component>
```

**Arguments:**

- `<component>`: Name of the template component to install (e.g. `sc.superb.critique`).

**Options:**

- `--agent`: Target AI agent — one of `opencode`, `kiro`, `gemini` (default: `opencode`).

**Examples:**

```bash
# Install the "superb critique" prompt for opencode (default)
uv run agent-tools kit commands add sc.superb.critique

# Install the same prompt for kiro
uv run agent-tools kit --agent kiro commands add sc.superb.critique

# Install the drift-detection prompt for gemini
uv run agent-tools kit --agent gemini commands add sc.superb.drift.detect
```

The command writes the transformed prompt file to the agent's conventional location:

| Agent | Output path |
|-------|-------------|
| `opencode` | `.opencode/command/<component>.md` |
| `kiro` | `.kiro/prompts/<component>.md` |
| `gemini` | `.gemini/commands/<component>.toml` |

#### Available Components

| Component | Compatible agents | Description |
|-----------|------------------|-------------|
| `sc.superb.critique` | `opencode`, `kiro`, `gemini` | Tailored prompt for `/speckit.superb.critique` |
| `sc.superb.drift.detect` | `opencode`, `gemini` | Detect drift between manually modified code and existing specification |

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

- Add `jules status` to track session progress.
- Integration with GitHub Copilot Review API.

## License

MIT License - Copyright (c) 2026 Boris Resnick
