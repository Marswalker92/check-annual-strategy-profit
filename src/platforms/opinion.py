from __future__ import annotations

import json
import urllib.parse
import urllib.request

from constants import BSC_RPC_URL, OPINION_API_BASE, USDT_TOKEN_CONTRACT
from platforms.polymarket import erc20_balance_of
from utils import as_float


def fetch_opinion_positions(user: str, api_key: str) -> list[dict]:
    rows: list[dict] = []
    page = 1
    limit = 20
    while True:
        url = (
            f"{OPINION_API_BASE}/{user}?"
            + urllib.parse.urlencode({"limit": limit, "page": page})
        )
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept": "application/json",
                "apikey": api_key,
            },
        )
        with urllib.request.urlopen(req, timeout=20) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
        result = payload.get("result", {})
        chunk = result.get("list", [])
        if not isinstance(chunk, list):
            raise RuntimeError(f"Unexpected Opinion response payload: {payload!r}")
        rows.extend(chunk)
        total = int(result.get("total", 0) or 0)
        if len(rows) >= total or not chunk:
            break
        page += 1
    return rows


def summarize_opinion_wallet(
    wallet_entry: dict[str, str], api_key: str
) -> dict[str, float | str | int]:
    user = wallet_entry["owner_wallet"]
    rows = fetch_opinion_positions(user, api_key)
    positions_current_value = sum(
        as_float(row.get("currentValueInQuoteToken")) for row in rows
    )
    total_cash_pnl = sum(as_float(row.get("unrealizedPnl")) for row in rows)
    op_wallet = wallet_entry["op_wallet"]
    usdt_balance = (
        erc20_balance_of(BSC_RPC_URL, USDT_TOKEN_CONTRACT, op_wallet, 18)
        if op_wallet
        else 0.0
    )
    total_current_value = positions_current_value + usdt_balance
    total_initial_value = (positions_current_value - total_cash_pnl) + usdt_balance
    return {
        "platform": "OP",
        "name": wallet_entry["name"],
        "wallet": op_wallet or user,
        "position_count": len(rows),
        "portfolio": total_current_value,
        "initial_cost": total_initial_value,
        "floating_pnl": total_cash_pnl,
    }
