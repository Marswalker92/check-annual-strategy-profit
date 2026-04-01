from __future__ import annotations

import math
import unicodedata
from pathlib import Path


def as_float(value: object) -> float:
    if value is None:
        return 0.0
    try:
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return 0.0
        number = float(value)
        if not math.isfinite(number):
            return 0.0
        return number
    except (TypeError, ValueError):
        return 0.0


def format_money(value: float) -> str:
    return f"{value:.2f}"


def display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in {"F", "W"} else 1
    return width


def pad_cell(text: str, width: int, align: str = "left") -> str:
    padding = max(0, width - display_width(text))
    if align == "right":
        return (" " * padding) + text
    return text + (" " * padding)


def ensure_parent_dir(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
