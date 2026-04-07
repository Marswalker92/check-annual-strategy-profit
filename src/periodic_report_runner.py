#!/usr/bin/env python3
"""
Periodic report runner.

Runs every 6 hours via cron:
1. Portfolio report (query_poly_positions.py)
2. Unsettled markets by wallet (fetch_unsettled_markets.py)
3. Unsettled markets aggregated (fetch_unsettled_by_market.py)
4. Sends all reports to Telegram
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
SRC_DIR = PROJECT_DIR / "src"
CONFIG_FILE = PROJECT_DIR / "config" / "local_config.json"


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    print(f"[{ts}] {msg}", flush=True)


def run_script(script: str, extra_args: list[str] | None = None) -> bool:
    cmd = [sys.executable, str(SRC_DIR / script), "--config", str(CONFIG_FILE)]
    if extra_args:
        cmd.extend(extra_args)
    log(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    if result.returncode != 0:
        log(f"ERROR: {script} failed (exit {result.returncode})")
        if result.stderr:
            log(f"stderr: {result.stderr[:500]}")
        return False
    log(f"OK: {script} completed")
    return True


def main() -> int:
    log("=== Periodic report run started ===")

    ok = True

    # 1. Portfolio report
    # NOTE: --send-telegram disabled for now, re-enable when needed
    if not run_script("query_poly_positions.py"):
        ok = False

    # 2. Unsettled markets (by wallet)
    # NOTE: --send-telegram disabled for now, re-enable when needed
    if not run_script("fetch_unsettled_markets.py"):
        ok = False

    # 3. Unsettled markets (aggregated by market)
    # NOTE: --send-telegram disabled for now, re-enable when needed
    if not run_script("fetch_unsettled_by_market.py"):
        ok = False

    if ok:
        log("=== All reports completed successfully ===")
    else:
        log("=== Some reports failed, check logs above ===")

    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
