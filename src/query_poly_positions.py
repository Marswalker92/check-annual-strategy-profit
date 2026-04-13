#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import sys

from constants import (
    DEFAULT_CONFIG_FILE,
    DEFAULT_HISTORY_FILE,
    DEFAULT_MONTHLY_HISTORY_FILE,
    DEFAULT_MONTHLY_OUTPUT_FILE,
    DEFAULT_OUTPUT_FILE,
    DEFAULT_TOTAL_FLOATING_PNL_CHART_FILE,
    DEFAULT_TOTAL_FLOATING_PNL_HISTORY_FILE,
)
from report_pipeline import run_daily_report, run_monthly_report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Query live Polymarket portfolio totals for one or more wallets."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_FILE),
        help=f"Path to the local sensitive config file (default: {DEFAULT_CONFIG_FILE})",
    )
    parser.add_argument(
        "--wallet-file",
        default="",
        help="Optional path to a wallet list file. If omitted, wallets are loaded from the local config file.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_FILE),
        help=f"Path to the markdown report (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--history-file",
        default=str(DEFAULT_HISTORY_FILE),
        help=f"Path to the portfolio history snapshot file (default: {DEFAULT_HISTORY_FILE})",
    )
    parser.add_argument(
        "--total-floating-pnl-history-file",
        default=str(DEFAULT_TOTAL_FLOATING_PNL_HISTORY_FILE),
        help=(
            "Path to the daily total floating PnL history file "
            f"(default: {DEFAULT_TOTAL_FLOATING_PNL_HISTORY_FILE})"
        ),
    )
    parser.add_argument(
        "--total-floating-pnl-chart-file",
        default=str(DEFAULT_TOTAL_FLOATING_PNL_CHART_FILE),
        help=(
            "Path to the generated daily total floating PnL PNG chart "
            f"(default: {DEFAULT_TOTAL_FLOATING_PNL_CHART_FILE})"
        ),
    )
    parser.add_argument(
        "--monthly-output",
        default=str(DEFAULT_MONTHLY_OUTPUT_FILE),
        help=f"Path to the monthly markdown report (default: {DEFAULT_MONTHLY_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--monthly-history-file",
        default=str(DEFAULT_MONTHLY_HISTORY_FILE),
        help=f"Path to the monthly portfolio snapshot file (default: {DEFAULT_MONTHLY_HISTORY_FILE})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the batch summary as JSON to stdout",
    )
    parser.add_argument(
        "--stdout-table",
        action="store_true",
        help="Also print the markdown table to stdout",
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send the rendered report table to Telegram after writing the report",
    )
    parser.add_argument(
        "--monthly-report",
        action="store_true",
        help="Generate the month-over-month portfolio total report instead of the daily report",
    )
    parser.add_argument(
        "--telegram-bot-token",
        default=os.getenv("TELEGRAM_BOT_TOKEN", ""),
        help="Telegram bot token (default: TELEGRAM_BOT_TOKEN env var or local config file)",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default=os.getenv("TELEGRAM_CHAT_ID", ""),
        help="Telegram chat id (default: TELEGRAM_CHAT_ID env var or local config file)",
    )
    parser.add_argument(
        "--opinion-api-key",
        default=os.getenv("OPINION_API_KEY", ""),
        help="Opinion API key (default: OPINION_API_KEY env var or local config file)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.monthly_report:
        return run_monthly_report(args)
    return run_daily_report(args)


if __name__ == "__main__":
    raise SystemExit(main())
