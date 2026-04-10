#!/usr/bin/env python3
"""
Fetch unsettled markets for poly_wallet addresses in the config.

For each configured wallet:
1. Fetch all open positions from Polymarket
2. For each position with size > 0, fetch the market details
3. Check if the market is still active/unsettled
4. Output a Markdown report of all unsettled market positions

Usage:
    python3 fetch_unsettled_markets.py
    python3 fetch_unsettled_markets.py --stdout
    python3 fetch_unsettled_markets.py --wallet 0x123...abc
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from config_loader import load_local_config, require_config, resolve_secret
from constants import (
    API_BASE,
    DEFAULT_CONFIG_FILE,
    DEFAULT_UNSETTLED_MARKETS_FILE,
    DEFAULT_UNSETTLED_MARKETS_JSON,
)
from telegram_push import send_telegram_split
from wallets import load_wallets_from_config

BERLIN_TZ = ZoneInfo("Europe/Berlin")


def format_berlin_timestamp(dt: datetime) -> str:
    return dt.astimezone(BERLIN_TZ).strftime("%Y-%m-%d %H:%M:%S %Z (Berlin)")


def fetch_positions(user: str) -> list[dict]:
    """Fetch all positions for a user with pagination."""
    rows: list[dict] = []
    offset = 0
    while True:
        params = {
            "user": user,
            "sizeThreshold": 0,
            "limit": 500,
            "offset": offset,
            "sortDirection": "DESC",
        }
        url = API_BASE + "?" + urllib.parse.urlencode(params)
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            chunk = json.loads(resp.read().decode("utf-8"))
        if not chunk:
            break
        rows.extend(chunk)
        if len(chunk) < 500:
            break
        offset += 500
    return rows


def is_position_unsettled(position: dict) -> bool:
    """
    Determine if a position is unsettled (still active OR ended but not yet redeemable).
    """
    # If redeemable is True, the position can be claimed = settled
    if position.get("redeemable", False):
        return False

    # Check end date
    end_date = position.get("endDate")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            # If end date is in the future, it's unsettled
            if end_dt > now:
                return True
            # If end date passed but not redeemable yet, still unsettled
            return True
        except Exception:
            pass

    # No end date info - assume unsettled if we have a position
    return True


def build_market_description(position: dict) -> str:
    """Build a human-readable description of the market from position data."""
    # Try various fields for the market question/description
    return (
        position.get("title", "")
        or position.get("description", "")
        or position.get("question", "")
        or "N/A"
    )


def position_has_size(position: dict) -> bool:
    """Check if a position has non-zero size."""
    size = position.get("size", 0)
    try:
        return float(size) > 0
    except (ValueError, TypeError):
        return False


def format_position_row(pos: dict) -> dict:
    """Format a single position into a report dict."""
    end_date = pos.get("endDate", "N/A")
    redeemable = pos.get("redeemable", False)
    event_slug = pos.get("eventSlug", "")
    question = build_market_description(pos)

    # Build market URL from event slug
    market_url = f"https://polymarket.com/event/{event_slug}" if event_slug else ""

    return {
        "question": question,
        "condition_id": pos.get("conditionId", "N/A"),
        "position_side": pos.get("outcome", "N/A"),
        "size": pos.get("size", "0"),
        "initial_value": pos.get("initialValue", "0"),
        "current_value": pos.get("currentValue", "0"),
        "cash_pnl": pos.get("cashPnl", "0"),
        "end_date": end_date,
        "redeemable": redeemable,
        "market_url": market_url,
    }


def generate_markdown_report(all_positions: list[dict]) -> str:
    """Generate a Markdown report of all unsettled positions."""
    if not all_positions:
        return "# Polymarket 未结算盘口\n\n当前所有钱包均无持仓中的未结算市场。"

    lines = [
        "# Polymarket 未结算盘口",
        "",
        f"**查询时间**: {format_berlin_timestamp(datetime.now(BERLIN_TZ))}",
        f"**涉及钱包**: {len(set(p['wallet_name'] for p in all_positions))} 个",
        f"**未结算仓位**: {len(all_positions)} 个",
        "",
    ]

    # Group by wallet
    by_wallet: dict[str, list[dict]] = {}
    for p in all_positions:
        by_wallet.setdefault(p["wallet_name"], []).append(p)

    for wallet_name, positions in by_wallet.items():
        lines.append(f"## {wallet_name}")
        lines.append("")
        lines.append(
            "| # | 市场描述 | 方向 | 持仓数量 | 初始成本 | 当前价值 | 浮动盈亏 | 截止时间 | 链接 |"
        )
        lines.append(
            "|---|---------|------|---------|---------|---------|---------|---------|------|"
        )

        for i, pos in enumerate(positions, 1):
            question = pos["question"]
            # Truncate long questions
            if len(question) > 60:
                question = question[:57] + "..."

            side = pos["position_side"]
            size = pos["size"]
            init_val = pos["initial_value"]
            cur_val = pos["current_value"]
            pnl = pos["cash_pnl"]
            end_date = pos["end_date"]
            url = pos["market_url"]

            # Shorten URL
            link_text = "[link]" if url else "-"

            lines.append(
                f"| {i} | {question} | {side} | {size} | {init_val} | {cur_val} | {pnl} | {end_date} | {link_text} |"
            )

        lines.append("")

    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch unsettled Polymarket markets for configured wallets."
    )
    parser.add_argument("--stdout", action="store_true", help="Print report to stdout")
    parser.add_argument(
        "--wallet",
        type=str,
        default="",
        help="Check only this specific poly_wallet address",
    )
    parser.add_argument(
        "--config", type=str, default="", help="Path to local_config.json"
    )
    parser.add_argument(
        "--send-telegram",
        action="store_true",
        help="Send the report to Telegram after generating",
    )
    parser.add_argument(
        "--telegram-bot-token",
        default="",
        help="Telegram bot token (overrides config file)",
    )
    parser.add_argument(
        "--telegram-chat-id",
        default="",
        help="Telegram chat id (overrides config file)",
    )
    args = parser.parse_args()

    # Load config
    config_path = Path(args.config) if args.config else DEFAULT_CONFIG_FILE
    if not config_path.exists():
        print(f"Error: Config file not found: {config_path}")
        print("Please create config based on local_config.example.json")
        sys.exit(1)

    config = load_local_config(config_path)
    wallets = load_wallets_from_config(config, config_path)

    # Filter to specific wallet if requested
    if args.wallet:
        wallets = [
            w for w in wallets if w["poly_wallet"].lower() == args.wallet.lower()
        ]
        if not wallets:
            print(f"No matching wallet found for: {args.wallet}")
            sys.exit(1)

    print(
        f"Checking {len(wallets)} wallet(s) for unsettled markets...\n", file=sys.stderr
    )

    all_unsettled: list[dict] = []

    for wallet in wallets:
        name = wallet["name"]
        poly_wallet = wallet["poly_wallet"]

        print(f"  [{name}] Fetching positions...", file=sys.stderr)
        positions = fetch_positions(poly_wallet)

        # Filter to positions with actual size
        active_positions = [p for p in positions if position_has_size(p)]

        print(
            f"  [{name}] {len(active_positions)} active position(s) found",
            file=sys.stderr,
        )

        for pos in active_positions:
            if is_position_unsettled(pos):
                row = format_position_row(pos)
                row["wallet_name"] = name
                row["wallet_address"] = poly_wallet
                all_unsettled.append(row)

    # Generate Markdown
    report = generate_markdown_report(all_unsettled)

    if args.stdout:
        print(report)
    else:
        # Save to file
        output_file = DEFAULT_UNSETTLED_MARKETS_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report, encoding="utf-8")

        # Also save raw JSON for programmatic use
        json_file = DEFAULT_UNSETTLED_MARKETS_JSON
        json_file.parent.mkdir(parents=True, exist_ok=True)
        json_file.write_text(
            json.dumps(all_unsettled, indent=2, default=str),
            encoding="utf-8",
        )

        print(report)
        print(f"\n---", file=sys.stderr)
        print(f"Markdown report saved to: {output_file}", file=sys.stderr)
        print(f"Raw JSON saved to: {json_file}", file=sys.stderr)


if __name__ == "__main__":
    main()
