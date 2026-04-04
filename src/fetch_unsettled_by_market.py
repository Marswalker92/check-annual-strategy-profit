#!/usr/bin/env python3
"""
Fetch unsettled markets aggregated by market (not by wallet).

For each market with unsettled positions across all wallets:
1. Aggregate total position size
2. Calculate weighted average cost
3. Sum current value and PnL
4. Output a Markdown report grouped by market

Usage:
    python3 fetch_unsettled_by_market.py
    python3 fetch_unsettled_by_market.py --stdout
    python3 fetch_unsettled_by_market.py --wallet 0x123...abc
"""

from __future__ import annotations

import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

from config_loader import load_local_config, require_config, resolve_secret
from constants import (
    API_BASE,
    DEFAULT_CONFIG_FILE,
    DEFAULT_UNSETTLED_BY_MARKET_FILE,
    DEFAULT_UNSETTLED_BY_MARKET_JSON,
)
from telegram_push import send_telegram_split
from wallets import load_wallets_from_config


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
    if position.get("redeemable", False):
        return False

    end_date = position.get("endDate")
    if end_date:
        try:
            end_dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            now = datetime.now(timezone.utc)
            if end_dt > now:
                return True
            return True
        except Exception:
            pass

    return True


def position_has_size(position: dict) -> bool:
    """Check if a position has non-zero size."""
    size = position.get("size", 0)
    try:
        return float(size) > 0
    except (ValueError, TypeError):
        return False


def aggregate_by_market(all_positions: list[dict]) -> list[dict]:
    """
    Aggregate positions by market (condition_id + outcome).

    For each market, calculate:
    - Total size (sum across wallets)
    - Weighted average cost (weighted by size)
    - Total current value
    - Total PnL
    - Wallet count (how many wallets hold this position)
    """
    market_map: dict[str, dict] = {}

    for pos in all_positions:
        condition_id = pos.get("conditionId", "")
        outcome = pos.get("outcome", "")
        key = f"{condition_id}::{outcome}"

        size = float(pos.get("size", 0))
        init_val = float(pos.get("initialValue", 0))
        cur_val = float(pos.get("currentValue", 0))
        pnl = float(pos.get("cashPnl", 0))

        if key not in market_map:
            market_map[key] = {
                "condition_id": condition_id,
                "outcome": outcome,
                "title": pos.get("title", "N/A"),
                "end_date": pos.get("endDate", "N/A"),
                "event_slug": pos.get("eventSlug", ""),
                "total_size": 0.0,
                "total_initial_value": 0.0,
                "total_current_value": 0.0,
                "total_pnl": 0.0,
                "wallet_count": 0,
                "wallets": [],
            }

        market_map[key]["total_size"] += size
        market_map[key]["total_initial_value"] += init_val
        market_map[key]["total_current_value"] += cur_val
        market_map[key]["total_pnl"] += pnl
        market_map[key]["wallet_count"] += 1
        market_map[key]["wallets"].append(pos.get("wallet_name", "Unknown"))

    # Calculate weighted average cost for each market
    result = []
    for key, data in market_map.items():
        total_size = data["total_size"]
        avg_cost = (data["total_initial_value"] / total_size) if total_size > 0 else 0.0

        result.append(
            {
                "condition_id": data["condition_id"],
                "outcome": data["outcome"],
                "title": data["title"],
                "end_date": data["end_date"],
                "event_slug": data["event_slug"],
                "total_size": total_size,
                "avg_cost": avg_cost,
                "total_current_value": data["total_current_value"],
                "total_pnl": data["total_pnl"],
                "wallet_count": data["wallet_count"],
                "wallets": data["wallets"],
            }
        )

    # Sort by total size descending
    result.sort(key=lambda x: x["total_size"], reverse=True)
    return result


def generate_markdown_report(aggregated_markets: list[dict]) -> str:
    """Generate a Markdown report of all unsettled markets."""
    if not aggregated_markets:
        return "# Polymarket 未结算盘口 (按市场汇总)\n\n当前所有钱包均无持仓中的未结算市场。"

    total_size = sum(m["total_size"] for m in aggregated_markets)
    total_value = sum(m["total_current_value"] for m in aggregated_markets)
    total_pnl = sum(m["total_pnl"] for m in aggregated_markets)

    lines = [
        "# Polymarket 未结算盘口 (按市场汇总)",
        "",
        f"**查询时间**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"**未结算市场**: {len(aggregated_markets)} 个",
        f"**总持仓数量**: {total_size:,.2f}",
        f"**总当前价值**: ${total_value:,.2f}",
        f"**总浮动盈亏**: ${total_pnl:,.2f}",
        "",
    ]

    lines.append(
        "| # | 市场描述 | 方向 | 持仓总数量 | 初始平均成本 | 当前价值 | 浮动盈亏 | 截止时间 | 钱包数 |"
    )
    lines.append(
        "|---|---------|------|-----------|-------------|---------|---------|---------|--------|"
    )

    for i, market in enumerate(aggregated_markets, 1):
        question = market["title"]
        if len(question) > 50:
            question = question[:47] + "..."

        outcome = market["outcome"]
        total_size = f"{market['total_size']:,.2f}"
        avg_cost = f"${market['avg_cost']:.4f}"
        cur_val = f"${market['total_current_value']:,.2f}"
        pnl = f"${market['total_pnl']:,.2f}"
        end_date = market["end_date"]
        wallet_count = market["wallet_count"]

        lines.append(
            f"| {i} | {question} | {outcome} | {total_size} | {avg_cost} | {cur_val} | {pnl} | {end_date} | {wallet_count} |"
        )

    lines.append("")
    return "\n".join(lines)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Fetch unsettled Polymarket markets aggregated by market."
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
        f"Checking {len(wallets)} wallet(s) for unsettled markets...\n",
        file=sys.stderr,
    )

    all_unsettled: list[dict] = []

    for wallet in wallets:
        name = wallet["name"]
        poly_wallet = wallet["poly_wallet"]

        print(f"  [{name}] Fetching positions...", file=sys.stderr)
        positions = fetch_positions(poly_wallet)

        active_positions = [p for p in positions if position_has_size(p)]

        for pos in active_positions:
            if is_position_unsettled(pos):
                pos["wallet_name"] = name
                pos["wallet_address"] = poly_wallet
                all_unsettled.append(pos)

        print(
            f"  [{name}] {len([p for p in active_positions if is_position_unsettled(p)])} unsettled position(s)",
            file=sys.stderr,
        )

    # Aggregate by market
    aggregated = aggregate_by_market(all_unsettled)

    # Generate Markdown
    report = generate_markdown_report(aggregated)

    if args.stdout:
        print(report)
    else:
        # Save to file
        output_file = DEFAULT_UNSETTLED_BY_MARKET_FILE
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(report, encoding="utf-8")

        # Also save raw JSON for programmatic use
        json_file = DEFAULT_UNSETTLED_BY_MARKET_JSON
        json_file.write_text(
            json.dumps(aggregated, indent=2, default=str),
            encoding="utf-8",
        )

        print(report)
        print(f"\n---", file=sys.stderr)
        print(f"Markdown report saved to: {output_file}", file=sys.stderr)
        print(f"Raw JSON saved to: {json_file}", file=sys.stderr)

    # Send to Telegram if requested
    if args.send_telegram:
        bot_token = require_config(
            "TELEGRAM_BOT_TOKEN",
            resolve_secret(args.telegram_bot_token, config, "telegram", "bot_token"),
        )
        chat_id = require_config(
            "TELEGRAM_CHAT_ID",
            resolve_secret(args.telegram_chat_id, config, "telegram", "chat_id"),
        )
        send_telegram_split(bot_token, chat_id, report)
        print("Report sent to Telegram", file=sys.stderr)


if __name__ == "__main__":
    main()
