from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from utils import as_float, ensure_parent_dir


def load_history(history_file: Path) -> dict[str, dict[str, dict[str, float | str]]]:
    if not history_file.exists():
        return {}
    payload = json.loads(history_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid history format in {history_file}")
    return payload


def get_previous_floating_pnl(
    history: dict[str, dict[str, dict[str, float | str]]],
    report_date: str,
    platform: str,
    wallet_address: str,
) -> float:
    previous_date = (
        datetime.strptime(report_date, "%Y-%m-%d").date() - timedelta(days=1)
    ).isoformat()
    previous_snapshot = history.get(previous_date, {})
    previous_row = previous_snapshot.get(f"{platform}:{wallet_address.lower()}")
    if not previous_row:
        return 0.0
    return as_float(previous_row.get("floating_pnl"))


def update_history(
    history_file: Path,
    report_date: str,
    rows: list[dict[str, float | str | int]],
) -> None:
    history = load_history(history_file)
    history[report_date] = {
        f"{str(row['platform'])}:{str(row['wallet']).lower()}": {
            "name": str(row["name"]),
            "platform": str(row["platform"]),
            "floating_pnl": as_float(row["floating_pnl"]),
        }
        for row in rows
    }
    ensure_parent_dir(history_file)
    history_file.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def load_total_floating_pnl_history(history_file: Path) -> list[dict[str, float | str]]:
    if not history_file.exists():
        return []
    payload = json.loads(history_file.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Invalid total floating PnL history format in {history_file}")
    return payload


def update_total_floating_pnl_history(
    history_file: Path,
    report_date: str,
    generated_at: datetime,
    total_floating_pnl: float,
) -> list[dict[str, float | str]]:
    history = load_total_floating_pnl_history(history_file)
    entry = {
        "date": report_date,
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "current_floating_pnl": total_floating_pnl,
    }
    updated = False
    for index, row in enumerate(history):
        if row.get("date") == report_date:
            history[index] = entry
            updated = True
            break
    if not updated:
        history.append(entry)
    history.sort(key=lambda row: str(row.get("date", "")))
    ensure_parent_dir(history_file)
    history_file.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return history


def previous_month_key(dt: datetime) -> str:
    year = dt.year
    month = dt.month - 1
    if month == 0:
        year -= 1
        month = 12
    return f"{year:04d}-{month:02d}"


def scheduled_monthly_snapshot(
    snapshot: dict[str, float | str] | None,
) -> dict[str, float | str] | None:
    if not snapshot:
        return None
    if int(snapshot.get("local_day", 0)) != 28:
        return None
    if int(snapshot.get("local_hour", 0)) != 22:
        return None
    return snapshot


def update_monthly_history(
    monthly_history_file: Path,
    generated_at: datetime,
    generated_local: datetime,
    current_total_portfolio: float,
) -> None:
    history = load_history(monthly_history_file)
    current_month_key = f"{generated_local.year:04d}-{generated_local.month:02d}"
    history[current_month_key] = {
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M:%S UTC"),
        "generated_at_local": generated_local.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "local_day": generated_local.day,
        "local_hour": generated_local.hour,
        "total_portfolio": current_total_portfolio,
    }
    ensure_parent_dir(monthly_history_file)
    monthly_history_file.write_text(
        json.dumps(history, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
