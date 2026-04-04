from __future__ import annotations

import json
import urllib.parse
import urllib.request

from constants import TELEGRAM_API_URL

# Telegram message text limit
MAX_MESSAGE_LENGTH = 4000


def send_telegram(token: str, chat_id: str, text: str) -> None:
    payload = urllib.parse.urlencode(
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        TELEGRAM_API_URL.format(token=token),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body)
    if not parsed.get("ok"):
        raise RuntimeError(f"Telegram sendMessage failed: {parsed!r}")


def send_telegram_split(token: str, chat_id: str, text: str) -> None:
    """Send a long message, splitting into chunks if needed."""
    if len(text) <= MAX_MESSAGE_LENGTH:
        send_telegram(token, chat_id, text)
        return

    # Split by lines to avoid breaking table rows
    lines = text.split("\n")
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_len = 0

    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if current_len + line_len > MAX_MESSAGE_LENGTH and current_chunk:
            chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_len = line_len
        else:
            current_chunk.append(line)
            current_len += line_len

    if current_chunk:
        chunks.append("\n".join(current_chunk))

    for i, chunk in enumerate(chunks, 1):
        if len(chunks) > 1:
            header = f"({i}/{len(chunks)}) "
            chunk = header + chunk
        send_telegram(token, chat_id, chunk)
