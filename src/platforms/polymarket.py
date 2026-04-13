from __future__ import annotations

import json
import urllib.request

from constants import POLYGON_RPC_URL, POLY_USDCE_TOKEN_CONTRACT
from polymarket_api import fetch_positions
from poly_realized_pnl import update_realized_pnl_for_wallet, get_wallet_realized_pnl
from utils import as_float


def erc20_balance_of(
    rpc_url: str, token_contract: str, wallet_address: str, decimals: int
) -> float:
    normalized = wallet_address.lower().removeprefix("0x")
    data = "0x70a08231" + ("0" * 24) + normalized
    payload = json.dumps(
        {
            "jsonrpc": "2.0",
            "method": "eth_call",
            "params": [{"to": token_contract, "data": data}, "latest"],
            "id": 1,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        rpc_url,
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        result = json.loads(resp.read().decode("utf-8"))
    raw_balance = result.get("result")
    if not isinstance(raw_balance, str) or not raw_balance.startswith("0x"):
        raise RuntimeError(f"Unexpected BSC RPC balance payload: {result!r}")
    return int(raw_balance, 16) / (10**decimals)


def summarize_wallet(wallet_entry: dict[str, str]) -> dict[str, float | str | int]:
    user = wallet_entry["poly_wallet"]
    rows = fetch_positions(user)
    positions_initial_value = sum(as_float(row.get("initialValue")) for row in rows)
    positions_current_value = sum(as_float(row.get("currentValue")) for row in rows)
    
    # Calculate unrealized PnL (active positions only)
    unrealized_pnl = positions_current_value - positions_initial_value
    
    # Update realized PnL tracking and get cumulative realized PnL from settled positions
    wallet_key = f"Poly:{user}"
    today_settled, position_count = update_realized_pnl_for_wallet(wallet_key, rows)
    realized_pnl = get_wallet_realized_pnl(wallet_key)
    
    # Total floating PnL = unrealized + realized
    total_floating_pnl = unrealized_pnl + realized_pnl
    
    usdce_balance = erc20_balance_of(
        POLYGON_RPC_URL,
        POLY_USDCE_TOKEN_CONTRACT,
        user,
        6,
    )
    total_initial_value = positions_initial_value + usdce_balance
    total_current_value = positions_current_value + usdce_balance
    return {
        "platform": "Poly",
        "name": wallet_entry["name"],
        "wallet": user,
        "position_count": len(rows),
        "portfolio": total_current_value,
        "initial_cost": total_initial_value,
        "unrealized_pnl": unrealized_pnl,
        "realized_pnl": realized_pnl,
        "floating_pnl": total_floating_pnl,
    }
