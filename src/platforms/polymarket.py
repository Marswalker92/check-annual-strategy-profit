from __future__ import annotations

import json
import urllib.parse
import urllib.request

from constants import API_BASE, POLYGON_RPC_URL, POLY_USDCE_TOKEN_CONTRACT
from utils import as_float


def fetch_positions(user: str) -> list[dict]:
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
    total_cash_pnl = sum(as_float(row.get("cashPnl")) for row in rows)
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
        "floating_pnl": total_cash_pnl,
    }
