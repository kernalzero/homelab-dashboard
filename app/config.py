"""Load config.yaml, expanding ${ENV_VAR} references so secrets can live in .env."""
import os
import re
from pathlib import Path

import yaml

_ENV_RE = re.compile(r"\$\{([A-Z0-9_]+)(?::-([^}]*))?\}")


def _expand(value):
    if isinstance(value, str):
        return _ENV_RE.sub(lambda m: os.environ.get(m.group(1), m.group(2) or ""), value)
    if isinstance(value, dict):
        return {k: _expand(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand(v) for v in value]
    return value


def load_config(path: str | None = None) -> dict:
    path = Path(path or os.environ.get("DASHBOARD_CONFIG", "config/config.yaml"))
    if not path.exists():
        return {}
    with path.open() as f:
        return _expand(yaml.safe_load(f) or {})
