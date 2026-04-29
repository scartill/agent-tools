"""Configuration management for agent-tools.

Loads settings from .env file and environment variables.
All values can be overridden via CLI options.
"""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

PROMPTS_CONFIG_NAME = Path(__file__).parent / 'prompts.yaml'


def get_jules_api_key(override: str | None = None) -> str:
    """Return the Jules API key, preferring the CLI override."""
    if override:
        return override
    value = os.environ.get('JULES_API_KEY', '')
    if not value:
        raise ValueError(
            'JULES_API_KEY is not set. '
            'Set it in your environment, .env file, or pass --jules-api-key.'
        )
    return value


def get_github_pat(override: str | None = None) -> str:
    """Return the GitHub Personal Access Token, preferring the CLI override."""
    if override:
        return override
    value = os.environ.get('GITHUB_PAT', '')
    if not value:
        raise ValueError(
            'GITHUB_PAT is not set. Set it in your environment, .env file, or pass --github-pat.'
        )
    return value


def get_prompts_path(override: str | None = None) -> Path:
    """Return path to the prompts YAML file."""
    name = override or PROMPTS_CONFIG_NAME
    return Path(name)
