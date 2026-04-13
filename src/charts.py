from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from utils import as_float, ensure_parent_dir, format_money

CHART_START_DATE = "2026-04-13"


def _save_chart_outputs(image: Image.Image, chart_file: Path) -> None:
    ensure_parent_dir(chart_file)
    png_file = chart_file.with_suffix(".png")
    webp_file = chart_file.with_suffix(".webp")
    image.save(png_file, format="PNG")
    image.save(webp_file, format="WEBP", quality=95, method=6)


def _chart_geometry() -> dict[str, int]:
    width = 960
    height = 420
    margin_left = 70
    margin_right = 30
    margin_top = 35
    margin_bottom = 70
    return {
        "width": width,
        "height": height,
        "margin_left": margin_left,
        "margin_right": margin_right,
        "margin_top": margin_top,
        "margin_bottom": margin_bottom,
        "plot_width": width - margin_left - margin_right,
        "plot_height": height - margin_top - margin_bottom,
    }


def _normalized_chart_data(
    history: list[dict[str, float | str]],
) -> tuple[list[float], list[str], float, float]:
    values = [as_float(row.get("current_floating_pnl")) for row in history]
    dates = [str(row.get("date", "")) for row in history]
    min_value = min(values)
    max_value = max(values)
    if math.isclose(min_value, max_value):
        min_value -= 1
        max_value += 1
    return values, dates, min_value, max_value


def _filter_history_from_start_date(
    history: list[dict[str, float | str]],
) -> list[dict[str, float | str]]:
    return [
        row
        for row in history
        if str(row.get("date", "")) >= CHART_START_DATE
    ]


def _generate_empty_png(chart_file: Path, width: int, height: int) -> None:
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    text = "No data yet"
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    draw.text(
        ((width - text_width) / 2, (height - text_height) / 2),
        text,
        fill="#444444",
        font=font,
    )
    _save_chart_outputs(image, chart_file)


def _generate_png_chart(
    chart_file: Path,
    history: list[dict[str, float | str]],
) -> None:
    geometry = _chart_geometry()
    width = geometry["width"]
    height = geometry["height"]
    margin_left = geometry["margin_left"]
    margin_right = geometry["margin_right"]
    margin_top = geometry["margin_top"]
    margin_bottom = geometry["margin_bottom"]
    plot_width = geometry["plot_width"]
    plot_height = geometry["plot_height"]

    if not history:
        _generate_empty_png(chart_file, width, height)
        return

    values, dates, min_value, max_value = _normalized_chart_data(history)
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    small_font = ImageFont.load_default()

    def x_pos(index: int) -> float:
        if len(history) == 1:
            return margin_left + plot_width / 2
        return margin_left + (plot_width * index / (len(history) - 1))

    def y_pos(value: float) -> float:
        normalized = (value - min_value) / (max_value - min_value)
        return margin_top + plot_height * (1 - normalized)

    draw.text((width / 2 - 70, 12), "Daily Total Floating PnL", fill="#111111", font=font)
    draw.line(
        [(margin_left, margin_top), (margin_left, height - margin_bottom)],
        fill="#111111",
        width=2,
    )
    draw.line(
        [(margin_left, height - margin_bottom), (width - margin_right, height - margin_bottom)],
        fill="#111111",
        width=2,
    )

    for tick_index in range(5):
        tick_value = min_value + (max_value - min_value) * tick_index / 4
        y = y_pos(tick_value)
        draw.line(
            [(margin_left, y), (width - margin_right, y)],
            fill="#e5e7eb",
            width=1,
        )
        label = format_money(tick_value)
        bbox = draw.textbbox((0, 0), label, font=small_font)
        label_width = bbox[2] - bbox[0]
        draw.text(
            (margin_left - label_width - 10, y - 6),
            label,
            fill="#555555",
            font=small_font,
        )

    points = [(x_pos(index), y_pos(value)) for index, value in enumerate(values)]
    if len(points) >= 2:
        draw.line(points, fill="#2563eb", width=3)
    for point in points:
        x, y = point
        draw.ellipse((x - 3.5, y - 3.5, x + 3.5, y + 3.5), fill="#2563eb")

    for index, date in enumerate(dates):
        x = x_pos(index)
        draw.text((x - 18, height - margin_bottom + 18), date, fill="#555555", font=small_font)

    draw.text((width / 2 - 12, height - 18), "Date", fill="#333333", font=font)
    draw.text((12, height / 2 - 10), "PnL", fill="#333333", font=font)

    _save_chart_outputs(image, chart_file)


def generate_total_floating_pnl_chart(
    chart_file: Path,
    history: list[dict[str, float | str]],
) -> None:
    geometry = _chart_geometry()
    width = geometry["width"]
    height = geometry["height"]
    margin_left = geometry["margin_left"]
    margin_right = geometry["margin_right"]
    margin_top = geometry["margin_top"]
    margin_bottom = geometry["margin_bottom"]
    chart_file = chart_file.with_suffix(".png")

    filtered_history = _filter_history_from_start_date(history)

    if not filtered_history:
        _generate_empty_png(chart_file, width, height)
        return

    values, dates, min_value, max_value = _normalized_chart_data(filtered_history)
    _generate_png_chart(chart_file, filtered_history)
