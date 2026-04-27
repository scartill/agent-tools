# agent-tools

**agent-tools** is a UV-managed Python CLI suite that orchestrates AI-powered
development workflows.  It combines [Jules](https://jules.google.com) coding
sessions with [GitHub Copilot](https://github.com/features/copilot) code
reviews to run fully automated refine-and-merge loops on your repositories.

---

## Table of Contents

- [Features](#features)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment variables / `.env`](#environment-variables--env)
  - [Prompts configuration (`prompts.yaml`)](#prompts-configuration-promptsyaml)
- [Usage](#usage)
  - [Global options](#global-options)
  - [`refine-loop` command](#refine-loop-command)
    - [Options](#options)
    - [Examples](#examples)
- [How `refine-loop` works](#how-refine-loop-works)
- [Project structure](#project-structure)
- [Development](#development)
  - [Setup](#setup)
  - [Linting](#linting)
- [License](#license)

---

## Features

- 🤖 **Jules integration** – creates coding sessions in *open-PR* mode and
  polls them until a pull request is ready.
- 🔍 **Copilot code review** – automatically requests a GitHub Copilot review
  on every new PR and waits for it to complete.
- 🛠️ **Copilot suggestion apply** – asks Copilot to apply its own review
  comments and monitors the resulting check runs.
- 🔀 **Merge gate** – prompts you for confirmation before merging, or merges
  automatically with `--automerge`.
- 🔄 **Multi-cycle loops** – run the full Jules → review → apply → merge
  pipeline up to *N* times in sequence.
- 🎨 **Rich output** – colour-coded status messages, live spinners, and clear
  progress rules via [Rich](https://github.com/Textualize/rich).
- ⚙️ **Flexible configuration** – credentials and settings can be supplied via
  `.env`, environment variables, or CLI flags (CLI takes precedence).

---

## Requirements

- Python ≥ 3.12
- [uv](https://docs.astral.sh/uv/) (package and project manager)
- A [Jules API key](https://jules.google.com)
- A [GitHub Personal Access Token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens)
  with `repo` and `pull_requests: write` scopes

---

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/scartill/agent-tools.git
cd agent-tools

# 2. Install with uv (creates a .venv automatically)
uv sync

# 3. Verify
uv run agent-tools --help
```

To install into your active Python environment instead:

```bash
uv pip install -e .
agent-tools --help
```

---

## Configuration

### Environment variables / `.env`

Create a `.env` file in the working directory (it is git-ignored by default):

```dotenv
# Required
JULES_API_KEY=your-jules-api-key
GITHUB_PAT=ghp_yourPersonalAccessToken
```

Both values can also be set as regular shell environment variables, or passed
directly on the command line via `--jules-api-key` and `--github-pat` (see
[Global options](#global-options)).

| Variable | Description |
|---|---|
| `JULES_API_KEY` | API key for authenticating with the Jules REST API |
| `GITHUB_PAT` | GitHub Personal Access Token used for all GitHub API calls |

### Prompts configuration (`prompts.yaml`)

By default, **agent-tools** looks for a `prompts.yaml` file in the current
working directory.  A different path can be specified with `--prompts-config`.

The file defines named agents and the natural-language prompt each one sends to
Jules:

```yaml
agents:
  bolt:
    prompt: |
      <Your task description for the Bolt agent goes here.
       Jules will use this to implement changes and open a PR.>

  another-agent:
    prompt: |
      <A different prompt for a different workflow.>
```

The agent name passed to `--agent` must match a key under `agents`.

---

## Usage

```
agent-tools [GLOBAL OPTIONS] COMMAND [COMMAND OPTIONS]
```

### Global options

These options apply to every command and can also be set via environment
variables or `.env`.

| Option | Env var | Description |
|---|---|---|
| `--jules-api-key KEY` | `JULES_API_KEY` | Jules API key |
| `--github-pat TOKEN` | `GITHUB_PAT` | GitHub Personal Access Token |
| `--prompts-config PATH` | – | Path to the prompts YAML file (default: `prompts.yaml`) |
| `--help` | – | Show help and exit |

### `refine-loop` command

```
agent-tools refine-loop [OPTIONS]
```

Runs the full Jules → Copilot review → apply → merge pipeline for the
specified repository and branch, repeating up to `--max-cycles` times.

#### Options

| Option | Short | Default | Description |
|---|---|---|---|
| `--repository OWNER/REPO` | `-r` | *(required)* | Target GitHub repository |
| `--branch BRANCH` | `-b` | *(required)* | Branch Jules works against |
| `--agent AGENT` | `-a` | *(required)* | Agent name from `prompts.yaml` |
| `--max-cycles N` | `-n` | `1` | Maximum number of refine cycles |
| `--polling-rate SECONDS` | – | `30` | Seconds between each poll request |
| `--automerge` / `--no-automerge` | – | `--no-automerge` | Merge PRs automatically without confirmation |
| `--help` | – | – | Show help and exit |

#### Examples

**Single cycle, interactive merge confirmation:**

```bash
agent-tools refine-loop \
  --repository myorg/myrepo \
  --branch feature/my-feature \
  --agent bolt
```

**Five cycles, 60-second polling, automerge enabled:**

```bash
agent-tools refine-loop \
  --repository myorg/myrepo \
  --branch main \
  --agent bolt \
  --max-cycles 5 \
  --polling-rate 60 \
  --automerge
```

**Pass credentials inline (useful in CI):**

```bash
agent-tools \
  --jules-api-key "$JULES_API_KEY" \
  --github-pat "$GITHUB_PAT" \
  refine-loop \
  --repository myorg/myrepo \
  --branch main \
  --agent bolt \
  --automerge
```

**Use a custom prompts file:**

```bash
agent-tools \
  --prompts-config /etc/agent-tools/prompts.yaml \
  refine-loop \
  --repository myorg/myrepo \
  --branch dev \
  --agent bolt
```

---

## How `refine-loop` works

Each iteration of the loop executes the following steps:

```
┌─────────────────────────────────────────────────────────────┐
│  Cycle N                                                    │
│                                                             │
│  1. Create Jules session (open-PR mode)                     │
│     └─ repository, branch, prompt from prompts.yaml         │
│                                                             │
│  2. Poll Jules session                                      │
│     ├─ running / queued  → keep polling                     │
│     ├─ paused / error    → warn user, skip cycle            │
│     └─ pr_open           → continue ↓                       │
│                                                             │
│  3. Request GitHub Copilot code review on the new PR        │
│                                                             │
│  4. Poll for Copilot review completion                      │
│     └─ review submitted  → continue ↓                       │
│                                                             │
│  5. If review comments exist:                               │
│     a. Ask Copilot to apply suggestions                     │
│     b. Poll check runs until apply completes                │
│                                                             │
│  6. Merge gate                                              │
│     ├─ --automerge       → merge immediately                │
│     └─ interactive       → prompt user for confirmation     │
│                                                             │
│  7. Merge PR (squash by default)                            │
└─────────────────────────────────────────────────────────────┘
```

Steps 3–5 are non-fatal: if the Copilot review or apply step fails, the tool
prints a warning and proceeds to the merge gate.

---

## Project structure

```
agent-tools/
├── prompts.yaml                        # Agent prompt definitions
├── pyproject.toml                      # UV project manifest + ruff config
├── uv.lock                             # Locked dependency versions
└── src/
    └── agent_tools/
        ├── __init__.py
        ├── cli.py                      # Click CLI entry point
        ├── config.py                   # Credential & path resolution
        ├── jules_client.py             # Jules REST API client
        ├── github_client.py            # GitHub REST API client
        └── commands/
            └── refine_loop.py          # refine-loop cycle implementation
```

---

## Development

### Setup

```bash
# Install runtime + dev dependencies
uv sync

# Activate the virtual environment (optional)
source .venv/bin/activate
```

### Linting

[Ruff](https://docs.astral.sh/ruff/) is used for linting and import sorting.

```bash
# Check
uv run ruff check src/

# Auto-fix
uv run ruff check --fix src/
```

---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file
included in the repository.
