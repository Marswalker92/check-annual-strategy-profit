from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from config_loader import load_local_config, require_config, resolve_secret
from history import (
    get_previous_floating_pnl,
    load_history,
    previous_month_key,
    scheduled_monthly_snapshot,
    update_history,
    update_monthly_history,
    update_total_floating_pnl_history,
)
from platforms.opinion import summarize_opinion_wallet
from platforms.polymarket import summarize_wallet
from reporting import (
    render_markdown,
    render_monthly_markdown,
    render_monthly_telegram_text,
    render_telegram_text,
    total_current_floating_pnl,
)
from telegram_push import send_telegram
from utils import as_float, ensure_parent_dir
from wallets import load_wallets, load_wallets_from_config


BERLIN_TZ = ZoneInfo("Europe/Berlin")
CHART_BASELINE = -2000.0


def resolve_wallets(config: dict, config_file: Path, wallet_file: str):
    return (
        load_wallets(Path(wallet_file).expanduser().resolve())
        if wallet_file
        else load_wallets_from_config(config, config_file)
    )


def build_summaries(wallets: list[dict], opinion_api_key: str) -> list[dict[str, float | str | int]]:
    summaries: list[dict[str, float | str | int]] = []
    for wallet in wallets:
        summaries.append(summarize_wallet(wallet))
        summaries.append(summarize_opinion_wallet(wallet, opinion_api_key))
    return summaries


def run_daily_report(args) -> int:
    config_file = Path(args.config).expanduser().resolve()
    config = load_local_config(config_file)
    output_file = Path(args.output).expanduser().resolve()
    history_file = Path(args.history_file).expanduser().resolve()
    total_floating_pnl_history_file = (
        Path(args.total_floating_pnl_history_file).expanduser().resolve()
    )
    total_floating_pnl_chart_file = (
        Path(args.total_floating_pnl_chart_file).expanduser().resolve()
    )
    generated_at = datetime.now(BERLIN_TZ)
    report_date = generated_at.date().isoformat()

    wallets = resolve_wallets(config, config_file, args.wallet_file)
    history = load_history(history_file)
    opinion_api_key = require_config(
        "OPINION_API_KEY",
        resolve_secret(args.opinion_api_key, config, "opinion", "api_key"),
    )
    summaries = build_summaries(wallets, opinion_api_key)
    for row in summaries:
        previous_floating_pnl = get_previous_floating_pnl(
            history,
            report_date,
            str(row["platform"]),
            str(row["wallet"]),
        )
        row["daily_floating_pnl_change"] = (
            as_float(row["floating_pnl"]) - previous_floating_pnl
        )

    markdown = render_markdown(summaries, generated_at)
    telegram_text = render_telegram_text(summaries, generated_at)
    ensure_parent_dir(output_file)
    output_file.write_text(markdown, encoding="utf-8")
    update_history(history_file, report_date, summaries)
    adjusted_total_floating_pnl = CHART_BASELINE + total_current_floating_pnl(summaries)
    total_floating_pnl_history = update_total_floating_pnl_history(
        total_floating_pnl_history_file,
        report_date,
        generated_at,
        adjusted_total_floating_pnl,
    )
    from charts import generate_total_floating_pnl_chart

    generate_total_floating_pnl_chart(
        total_floating_pnl_chart_file,
        total_floating_pnl_history,
    )

    if args.send_telegram:
        bot_token = require_config(
            "TELEGRAM_BOT_TOKEN",
            resolve_secret(args.telegram_bot_token, config, "telegram", "bot_token"),
        )
        chat_id = require_config(
            "TELEGRAM_CHAT_ID",
            resolve_secret(args.telegram_chat_id, config, "telegram", "chat_id"),
        )
        send_telegram(bot_token, chat_id, telegram_text)

    if args.json:
        json.dump(
            {
                "wallet_file": (
                    str(Path(args.wallet_file).expanduser().resolve())
                    if args.wallet_file
                    else None
                ),
                "config_file": str(config_file),
                "output_file": str(output_file),
                "history_file": str(history_file),
                "wallets": summaries,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    if args.stdout_table:
        sys.stdout.write(markdown)
    else:
        print(f"Report written to: {output_file}")
    return 0


def run_monthly_report(args) -> int:
    config_file = Path(args.config).expanduser().resolve()
    config = load_local_config(config_file)
    monthly_output_file = Path(args.monthly_output).expanduser().resolve()
    monthly_history_file = Path(args.monthly_history_file).expanduser().resolve()
    generated_at = datetime.now(BERLIN_TZ)
    generated_local = generated_at
    current_month_key = f"{generated_local.year:04d}-{generated_local.month:02d}"

    wallets = resolve_wallets(config, config_file, args.wallet_file)
    summaries = build_summaries(
        wallets,
        require_config(
            "OPINION_API_KEY",
            resolve_secret(args.opinion_api_key, config, "opinion", "api_key"),
        ),
    )
    current_total_portfolio = sum(as_float(row["portfolio"]) for row in summaries)
    monthly_history = load_history(monthly_history_file)
    previous_month_snapshot = scheduled_monthly_snapshot(
        monthly_history.get(previous_month_key(generated_local))
    )
    previous_total_portfolio = as_float(
        previous_month_snapshot.get("total_portfolio") if previous_month_snapshot else 0.0
    )
    previous_month_key_value = previous_month_key(generated_local)

    markdown = render_monthly_markdown(
        generated_at,
        current_month_key,
        previous_month_key_value,
        previous_total_portfolio,
        current_total_portfolio,
    )
    telegram_text = render_monthly_telegram_text(
        generated_at,
        current_month_key,
        previous_month_key_value,
        previous_total_portfolio,
        current_total_portfolio,
    )
    ensure_parent_dir(monthly_output_file)
    monthly_output_file.write_text(markdown, encoding="utf-8")
    update_monthly_history(
        monthly_history_file,
        generated_at,
        generated_local,
        current_total_portfolio,
    )

    if args.send_telegram:
        bot_token = require_config(
            "TELEGRAM_BOT_TOKEN",
            resolve_secret(args.telegram_bot_token, config, "telegram", "bot_token"),
        )
        chat_id = require_config(
            "TELEGRAM_CHAT_ID",
            resolve_secret(args.telegram_chat_id, config, "telegram", "chat_id"),
        )
        send_telegram(bot_token, chat_id, telegram_text)

    if args.json:
        json.dump(
            {
                "wallet_file": (
                    str(Path(args.wallet_file).expanduser().resolve())
                    if args.wallet_file
                    else None
                ),
                "config_file": str(config_file),
                "monthly_output_file": str(monthly_output_file),
                "monthly_history_file": str(monthly_history_file),
                "current_month_key": current_month_key,
                "previous_month_key": previous_month_key_value,
                "current_total_portfolio": current_total_portfolio,
                "previous_total_portfolio": previous_total_portfolio,
            },
            sys.stdout,
            ensure_ascii=False,
            indent=2,
        )
        sys.stdout.write("\n")
        return 0

    print(f"Monthly report written to: {monthly_output_file}")
    return 0