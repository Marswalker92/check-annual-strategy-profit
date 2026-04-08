from __future__ import annotations

import html
from datetime import datetime

from utils import as_float, display_width, format_money, pad_cell


def should_render_row(row: dict[str, float | str | int]) -> bool:
    return any(
        round(as_float(row[field]), 2) != 0
        for field in (
            "portfolio",
            "initial_cost",
            "floating_pnl",
            "daily_floating_pnl_change",
        )
    )


def total_current_floating_pnl(rows: list[dict[str, float | str | int]]) -> float:
    visible_rows = [row for row in rows if should_render_row(row)]
    return sum(as_float(row["floating_pnl"]) for row in visible_rows)


def render_markdown(
    rows: list[dict[str, float | str | int]],
    generated_at: datetime,
) -> str:
    visible_rows = [row for row in rows if should_render_row(row)]
    total_initial_cost = sum(as_float(row["initial_cost"]) for row in visible_rows)
    total_floating_pnl = sum(as_float(row["floating_pnl"]) for row in visible_rows)
    total_daily_floating_pnl_change = sum(
        as_float(row["daily_floating_pnl_change"]) for row in visible_rows
    )
    generated_at_str = generated_at.strftime("%Y-%m-%d %H:%M:%S UTC")

    lines = [
        "# Polymarket Portfolio Report",
        "",
        f"Generated at: {generated_at_str}",
        "",
        "| 钱包名称 | 平台 | portfolio | 初始成本 | 当前浮动盈亏 | 当天较前一天浮动盈亏变化 | 钱包地址 |",
        "| --- | --- | ---: | ---: | ---: | ---: | --- |",
    ]
    # Add Total row first
    lines.append(
        "| **总计** |  |  | **{initial_cost}** | **{floating_pnl}** | **{daily_floating_pnl_change}** |  |".format(
            initial_cost=format_money(total_initial_cost),
            floating_pnl=format_money(total_floating_pnl),
            daily_floating_pnl_change=format_money(total_daily_floating_pnl_change),
        )
    )
    for row in visible_rows:
        lines.append(
            "| {name} | {platform} | {portfolio} | {initial_cost} | {floating_pnl} | {daily_floating_pnl_change} | {wallet} |".format(
                name=row["name"],
                platform=row["platform"],
                portfolio=format_money(as_float(row["portfolio"])),
                initial_cost=format_money(as_float(row["initial_cost"])),
                floating_pnl=format_money(as_float(row["floating_pnl"])),
                daily_floating_pnl_change=format_money(
                    as_float(row["daily_floating_pnl_change"])
                ),
                wallet=row["wallet"],
            )
        )
    lines.append("")
    return "\n".join(lines)


def render_telegram_text(
    rows: list[dict[str, float | str | int]],
    generated_at: datetime,
) -> str:
    visible_rows = [row for row in rows if should_render_row(row)]
    total_initial_cost = sum(as_float(row["initial_cost"]) for row in visible_rows)
    total_floating_pnl = sum(as_float(row["floating_pnl"]) for row in visible_rows)
    total_daily_floating_pnl_change = sum(
        as_float(row["daily_floating_pnl_change"]) for row in visible_rows
    )
    table_rows = [
        [
            "钱包名称",
            "平台",
            "portfolio",
            "初始成本",
            "当前盈亏",
            "当天变化",
            "钱包地址",
        ]
    ]
    table_rows.extend(
        [
            str(row["name"]),
            str(row["platform"]),
            format_money(as_float(row["portfolio"])),
            format_money(as_float(row["initial_cost"])),
            format_money(as_float(row["floating_pnl"])),
            format_money(as_float(row["daily_floating_pnl_change"])),
            str(row["wallet"]),
        ]
        for row in visible_rows
    )
    table_rows.append(
        [
            "总计",
            "",
            "",
            format_money(total_initial_cost),
            format_money(total_floating_pnl),
            format_money(total_daily_floating_pnl_change),
            "",
        ]
    )

    col_widths = [
        max(display_width(str(row[col_index])) for row in table_rows)
        for col_index in range(len(table_rows[0]))
    ]
    alignments = ["left", "left", "left", "right", "right", "right", "right"]

    def format_table_row(row: list[str]) -> str:
        return " | ".join(
            pad_cell(str(cell), col_widths[index], alignments[index])
            for index, cell in enumerate(row)
        )

    divider = "-+-".join("-" * width for width in col_widths)
    lines = [
        "Polymarket Portfolio Report",
        f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        format_table_row(table_rows[0]),
        divider,
    ]
    lines.extend(format_table_row(row) for row in table_rows[1:-1])
    lines.append(divider)
    lines.append(format_table_row(table_rows[-1]))
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"


def render_monthly_markdown(
    generated_at: datetime,
    current_month_key: str,
    previous_month_key_value: str,
    previous_total_portfolio: float,
    current_total_portfolio: float,
) -> str:
    portfolio_change = current_total_portfolio - previous_total_portfolio
    direction = "正" if portfolio_change > 0 else "负" if portfolio_change < 0 else "持平"

    lines = [
        "# Monthly Portfolio Report",
        "",
        f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"Current month key: {current_month_key}",
        f"Previous month key: {previous_month_key_value}",
        "",
        "| 指标 | 数值 |",
        "| --- | ---: |",
        f"| 本月所有钱包 portfolio 总和 | {format_money(current_total_portfolio)} |",
        f"| 上个月截止同一时间 portfolio 总和 | {format_money(previous_total_portfolio)} |",
        f"| 环比变化 | {format_money(portfolio_change)} |",
        f"| 本月结果 | {direction} |",
        "",
    ]
    return "\n".join(lines)


def render_monthly_telegram_text(
    generated_at: datetime,
    current_month_key: str,
    previous_month_key_value: str,
    previous_total_portfolio: float,
    current_total_portfolio: float,
) -> str:
    portfolio_change = current_total_portfolio - previous_total_portfolio
    direction = "正" if portfolio_change > 0 else "负" if portfolio_change < 0 else "持平"
    lines = [
        "Monthly Portfolio Report",
        f"Generated at: {generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
        "",
        f"本月: {current_month_key}",
        f"上月: {previous_month_key_value}",
        f"本月所有钱包 portfolio 总和: {format_money(current_total_portfolio)}",
        f"上个月截止同一时间 portfolio 总和: {format_money(previous_total_portfolio)}",
        f"环比变化: {format_money(portfolio_change)}",
        f"本月结果: {direction}",
    ]
    return "<pre>" + html.escape("\n".join(lines)) + "</pre>"
