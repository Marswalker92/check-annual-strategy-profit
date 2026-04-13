"""
Track realized PnL from settled positions in Polymarket.

Uses daily position snapshots to detect when positions settle/close, 
and accumulates their final PnL into a realized_pnl history.
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path

from constants import (
    POLY_POSITIONS_SNAPSHOT_JSON,
    POLY_REALIZED_PNL_JSON,
    BERLIN_TZ,
)
from utils import as_float


def load_snapshots() -> dict[str, dict[str, list[dict]]]:
    """Load position snapshots from disk."""
    if POLY_POSITIONS_SNAPSHOT_JSON.exists():
        with open(POLY_POSITIONS_SNAPSHOT_JSON) as f:
            return json.load(f)
    return {}


def save_snapshots(snapshots: dict[str, dict[str, list[dict]]]) -> None:
    """Save position snapshots to disk."""
    POLY_POSITIONS_SNAPSHOT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(POLY_POSITIONS_SNAPSHOT_JSON, "w") as f:
        json.dump(snapshots, f, indent=2)


def load_realized_pnl() -> dict[str, dict[str, float | int | str]]:
    """Load cumulative realized PnL tracking from disk."""
    if POLY_REALIZED_PNL_JSON.exists():
        with open(POLY_REALIZED_PNL_JSON) as f:
            return json.load(f)
    return {}


def save_realized_pnl(realized_pnl: dict[str, dict[str, float | int | str]]) -> None:
    """Save realized PnL tracking to disk."""
    POLY_REALIZED_PNL_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(POLY_REALIZED_PNL_JSON, "w") as f:
        json.dump(realized_pnl, f, indent=2)


def get_today_key() -> str:
    """Get today's date key in YYYY-MM-DD format using Berlin timezone."""
    now = datetime.now(BERLIN_TZ)
    return now.strftime("%Y-%m-%d")


def create_position_fingerprint(position: dict) -> str:
    """Create a unique identifier for a position to detect duplicates/matches."""
    # Use market_id as primary key; if not available, use (initialValue, position)
    market_id = position.get("market_id") or position.get("id")
    if market_id:
        return str(market_id)
    # Fallback: deduplicate by (initialValue, position, token) tuple
    iv = round(as_float(position.get("initialValue")), 2)
    pos = position.get("position", 0)
    token = position.get("fpmm", {}).get("token", "unknown")
    return f"{token}:{iv}:{pos}"


def calculate_settled_pnl(
    current_positions: list[dict],
    previous_positions: list[dict],
) -> float:
    """
    Compare current and previous position snapshots.
    Detect positions that existed before but are gone now (settled).
    Calculate realized PnL for settled positions.
    
    Args:
        current_positions: Today's active positions
        previous_positions: Yesterday's active positions
    
    Returns:
        Net PnL from newly settled positions
    """
    # Create fingerprints for quick comparison
    current_fps = {create_position_fingerprint(p): p for p in current_positions}
    previous_fps = {create_position_fingerprint(p): p for p in previous_positions}
    
    settled_pnl = 0.0
    
    # Find positions that settled (were in previous but not in current)
    for fp, prev_pos in previous_fps.items():
        if fp not in current_fps:
            # This position settled; calculate its final PnL
            initial_value = as_float(prev_pos.get("initialValue"))
            current_value = as_float(prev_pos.get("currentValue"))
            pnl = current_value - initial_value
            settled_pnl += pnl
            # Debug: optionally log settled positions
            # print(f"[SETTLED] {fp}: initial={initial_value:.2f}, current={current_value:.2f}, pnl={pnl:.2f}")
    
    return settled_pnl


def update_realized_pnl_for_wallet(
    wallet_key: str,
    orders: list[dict],
) -> tuple[float, int]:
    """
    Update realized PnL for a wallet by comparing today's snapshot with yesterday's.
    
    Args:
        wallet_key: Wallet identifier (e.g., "Poly:0xAbcd...")
        orders: Today's active positions from API
    
    Returns:
        Tuple of (today_settled_pnl, total_settled_count)
    """
    snapshots = load_snapshots()
    realized_pnl_data = load_realized_pnl()
    
    today_key = get_today_key()
    yesterday_key = (
        datetime.fromisoformat(today_key)
        - timedelta(days=1)
    ).strftime("%Y-%m-%d")
    
    # Initialize wallet entry if needed
    if wallet_key not in realized_pnl_data:
        realized_pnl_data[wallet_key] = {
            "total_realized_pnl": 0.0,
            "last_updated": today_key,
            "settled_positions_count": 0,
        }
    
    # Store today's snapshot
    if today_key not in snapshots:
        snapshots[today_key] = {}
    
    # Create snapshot of today's positions (store minimal info for comparison)
    today_snapshot = [
        {
            "market_id": order.get("market_id") or order.get("id"),
            "initial_value": float(order.get("initialValue") or 0),
            "current_value": float(order.get("currentValue") or 0),
            "position": order.get("position") or 0,
        }
        for order in orders
    ]
    snapshots[today_key][wallet_key] = today_snapshot
    
    # Calculate settled PnL (compare with yesterday)
    yesterday_snapshot = snapshots.get(yesterday_key, {}).get(wallet_key, [])
    today_settled_pnl = calculate_settled_pnl(today_snapshot, yesterday_snapshot)
    
    # Update cumulative tracking
    if today_settled_pnl != 0:
        prev_total = as_float(realized_pnl_data[wallet_key]["total_realized_pnl"])
        realized_pnl_data[wallet_key]["total_realized_pnl"] = prev_total + today_settled_pnl
        prev_count = int(realized_pnl_data[wallet_key].get("settled_positions_count", 0))
        settled_count = len(yesterday_snapshot) - len(today_snapshot)
        if settled_count > 0:
            realized_pnl_data[wallet_key]["settled_positions_count"] = (
                prev_count + settled_count
            )
    
    realized_pnl_data[wallet_key]["last_updated"] = today_key
    
    # Persist updates
    save_snapshots(snapshots)
    save_realized_pnl(realized_pnl_data)
    
    return today_settled_pnl, len(today_snapshot)


def get_wallet_realized_pnl(wallet_key: str) -> float:
    """Get cumulative realized PnL for a wallet."""
    realized_pnl_data = load_realized_pnl()
    if wallet_key in realized_pnl_data:
        return as_float(realized_pnl_data[wallet_key].get("total_realized_pnl", 0.0))
    return 0.0
