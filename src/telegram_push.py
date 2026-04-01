from __future__ import annotations

import json
import urllib.parse
import urllib.request

from constants import TELEGRAM_API_URL


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
