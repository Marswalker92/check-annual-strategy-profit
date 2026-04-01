from __future__ import annotations

import json
from pathlib import Path


def load_local_config(config_file: Path) -> dict:
    if not config_file.exists():
        return {}
    payload = json.loads(config_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid local config format in {config_file}")
    return payload


def resolve_secret(cli_value: str, config: dict, section: str, key: str) -> str:
    if cli_value.strip():
        return cli_value.strip()
    section_data = config.get(section, {})
    if isinstance(section_data, dict):
        value = section_data.get(key, "")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def require_config(name: str, value: str) -> str:
    if value.strip():
        return value.strip()
    raise ValueError(f"Missing required config: {name}")
