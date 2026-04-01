from __future__ import annotations

import html
import math
from pathlib import Path

from utils import as_float, ensure_parent_dir, format_money


def generate_total_floating_pnl_chart(
    chart_file: Path,
    history: list[dict[str, float | str]],
) -> None:
    width = 960
    height = 420
    margin_left = 70
    margin_right = 30
    margin_top = 35
    margin_bottom = 70
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    if not history:
        ensure_parent_dir(chart_file)
        chart_file.write_text(
            (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
                'viewBox="0 0 960 420">'
                '<rect width="100%" height="100%" fill="white"/>'
                '<text x="50%" y="50%" text-anchor="middle" font-size="18" fill="#444">'
                "No data yet"
                "</text></svg>"
            ),
            encoding="utf-8",
        )
        return

    values = [as_float(row.get("current_floating_pnl")) for row in history]
    dates = [str(row.get("date", "")) for row in history]
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        min_value -= 1
        max_value += 1

    def x_pos(index: int) -> float:
        if len(history) == 1:
            return margin_left + plot_width / 2
        return margin_left + (plot_width * index / (len(history) - 1))

    def y_pos(value: float) -> float:
        normalized = (value - min_value) / (max_value - min_value)
        return margin_top + plot_height * (1 - normalized)

    points = " ".join(
        f"{x_pos(index):.2f},{y_pos(value):.2f}" for index, value in enumerate(values)
    )
    y_ticks = []
    for tick_index in range(5):
        tick_value = min_value + (max_value - min_value) * tick_index / 4
        y = y_pos(tick_value)
        y_ticks.append(
            f'<line x1="{margin_left}" y1="{y:.2f}" x2="{width - margin_right}" y2="{y:.2f}" '
            'stroke="#e5e7eb" stroke-width="1"/>'
            f'<text x="{margin_left - 10}" y="{y + 4:.2f}" text-anchor="end" '
            'font-size="12" fill="#555">'
            f"{html.escape(format_money(tick_value))}</text>"
        )

    x_labels = []
    for index, date in enumerate(dates):
        x = x_pos(index)
        y = height - margin_bottom + 20
        x_labels.append(
            f'<text x="{x:.2f}" y="{y}" text-anchor="end" '
            'font-size="11" fill="#555" transform="rotate(-35 '
            f'{x:.2f},{y})">{html.escape(date)}</text>'
        )

    point_marks = []
    for index, value in enumerate(values):
        x = x_pos(index)
        y = y_pos(value)
        point_marks.append(
            f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.5" fill="#2563eb"/>'
            f'<title>{html.escape(dates[index])}: {html.escape(format_money(value))}</title>'
        )

    svg = (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">'
        '<rect width="100%" height="100%" fill="white"/>'
        f'<text x="{width / 2:.2f}" y="22" text-anchor="middle" font-size="18" fill="#111">'
        "Daily Total Floating PnL"
        "</text>"
        f'<line x1="{margin_left}" y1="{margin_top}" x2="{margin_left}" y2="{height - margin_bottom}" '
        'stroke="#111" stroke-width="1.5"/>'
        f'<line x1="{margin_left}" y1="{height - margin_bottom}" x2="{width - margin_right}" y2="{height - margin_bottom}" '
        'stroke="#111" stroke-width="1.5"/>'
        + "".join(y_ticks)
        + f'<polyline fill="none" stroke="#2563eb" stroke-width="2.5" points="{points}"/>'
        + "".join(point_marks)
        + "".join(x_labels)
        + f'<text x="{width / 2:.2f}" y="{height - 10}" text-anchor="middle" font-size="13" fill="#333">Date</text>'
        + (
            f'<text x="20" y="{height / 2:.2f}" text-anchor="middle" font-size="13" fill="#333" '
            'transform="rotate(-90 20,'
            f'{height / 2:.2f})">Current Floating PnL</text>'
        )
        + "</svg>"
    )
    ensure_parent_dir(chart_file)
    chart_file.write_text(svg, encoding="utf-8")
