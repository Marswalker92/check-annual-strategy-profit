from __future__ import annotations

from pathlib import Path

from constants import ADDRESS_RE


def parse_wallet_record(
    name: str, owner_wallet: str, poly_wallet: str, op_wallet: str
) -> dict[str, str]:
    if not name or not owner_wallet or not poly_wallet:
        raise ValueError("Wallet entry contains an empty required field.")
    for label, address in (
        ("owner wallet", owner_wallet),
        ("poly wallet", poly_wallet),
    ):
        if not ADDRESS_RE.fullmatch(address):
            raise ValueError(f"Invalid {label} address: {address}")
    if op_wallet and not ADDRESS_RE.fullmatch(op_wallet):
        raise ValueError(f"Invalid op wallet address: {op_wallet}")
    return {
        "name": name,
        "owner_wallet": owner_wallet,
        "poly_wallet": poly_wallet,
        "op_wallet": op_wallet,
    }


def load_wallets(wallet_file: Path) -> list[dict[str, str]]:
    wallets: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for raw_line in wallet_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) == 2:
            name, address = parts
            owner_wallet = address
            poly_wallet = address
            op_wallet = address
        elif len(parts) == 3:
            name, owner_wallet, poly_wallet = parts
            op_wallet = ""
        elif len(parts) == 4:
            name, owner_wallet, poly_wallet, op_wallet = parts
        else:
            raise ValueError(
                f"Invalid wallet entry in {wallet_file}: {line}. Expected format: "
                "wallet_name, wallet_address or wallet_name, owner_wallet, poly_wallet "
                "or wallet_name, owner_wallet, poly_wallet, op_wallet"
            )
        wallet = parse_wallet_record(name, owner_wallet, poly_wallet, op_wallet)
        normalized = (
            wallet["owner_wallet"].lower(),
            wallet["poly_wallet"].lower(),
            wallet["op_wallet"].lower() if wallet["op_wallet"] else "",
        )
        if normalized in seen:
            continue
        seen.add(normalized)
        wallets.append(wallet)
    if not wallets:
        raise ValueError(f"No wallet entries found in {wallet_file}")
    return wallets


def load_wallets_from_config(config: dict, config_file: Path) -> list[dict[str, str]]:
    wallet_entries = config.get("wallets", [])
    if not isinstance(wallet_entries, list):
        raise ValueError(f"Invalid wallets list in {config_file}")
    wallets: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for entry in wallet_entries:
        if not isinstance(entry, dict):
            raise ValueError(f"Invalid wallet object in {config_file}: {entry!r}")
        wallet = parse_wallet_record(
            str(entry.get("name", "")).strip(),
            str(entry.get("owner_wallet", "")).strip(),
            str(entry.get("poly_wallet", "")).strip(),
            str(entry.get("op_wallet", "")).strip(),
        )
        normalized = (
            wallet["owner_wallet"].lower(),
            wallet["poly_wallet"].lower(),
            wallet["op_wallet"].lower() if wallet["op_wallet"] else "",
        )
        if normalized in seen:
            continue
        seen.add(normalized)
        wallets.append(wallet)
    if not wallets:
        raise ValueError(f"No wallet entries found in {config_file}")
    return wallets
