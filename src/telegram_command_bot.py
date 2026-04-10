#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from config_loader import load_local_config, require_config
from constants import DEFAULT_CONFIG_FILE, PROJECT_DIR, REPORTS_JSON_DIR, TELEGRAM_API_URL
from utils import ensure_parent_dir


DEFAULT_STATE_FILE = REPORTS_JSON_DIR / "telegram_bot_state.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Telegram bot listener for on-demand portfolio checks."
    )
    parser.add_argument(
        "--config",
        default=str(DEFAULT_CONFIG_FILE),
        help=f"Path to the local sensitive config file (default: {DEFAULT_CONFIG_FILE})",
    )
    parser.add_argument(
        "--state-file",
        default=str(DEFAULT_STATE_FILE),
        help=f"Path to the Telegram bot offset state file (default: {DEFAULT_STATE_FILE})",
    )
    parser.add_argument(
        "--poll-timeout",
        type=int,
        default=30,
        help="Telegram getUpdates timeout in seconds (default: 30)",
    )
    return parser.parse_args()


def load_state(state_file: Path) -> dict[str, int]:
    if not state_file.exists():
        return {"last_update_id": 0}
    payload = json.loads(state_file.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Invalid state format in {state_file}")
    return {"last_update_id": int(payload.get("last_update_id", 0) or 0)}


def save_state(state_file: Path, last_update_id: int) -> None:
    ensure_parent_dir(state_file)
    state_file.write_text(
        json.dumps({"last_update_id": last_update_id}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def telegram_api_request(token: str, method: str, params: dict[str, object]) -> dict:
    payload = urllib.parse.urlencode(params).encode("utf-8")
    request = urllib.request.Request(
        TELEGRAM_API_URL.replace("/sendMessage", f"/{method}").format(token=token),
        data=payload,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode("utf-8")
    parsed = json.loads(body)
    if not parsed.get("ok"):
        raise RuntimeError(f"Telegram {method} failed: {parsed!r}")
    return parsed


def send_text(token: str, chat_id: str, text: str) -> None:
    telegram_api_request(
        token,
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
    )


def get_updates(token: str, offset: int, timeout_seconds: int) -> list[dict]:
    result = telegram_api_request(
        token,
        "getUpdates",
        {
            "offset": offset,
            "timeout": timeout_seconds,
            "allowed_updates": json.dumps(["message"]),
        },
    ).get("result", [])
    if not isinstance(result, list):
        raise RuntimeError(f"Unexpected Telegram getUpdates payload: {result!r}")
    return result


def extract_message_text(update: dict) -> tuple[str, str] | None:
    message = update.get("message")
    if not isinstance(message, dict):
        return None
    chat = message.get("chat", {})
    if not isinstance(chat, dict):
        return None
    chat_id = chat.get("id")
    text = message.get("text")
    if chat_id is None or not isinstance(text, str):
        return None
    return str(chat_id), text.strip()


def run_check_command(config_file: Path, chat_id: str) -> tuple[bool, str]:
    command = [
        sys.executable,
        str(PROJECT_DIR / "src" / "query_poly_positions.py"),
        "--config",
        str(config_file),
        "--send-telegram",
        "--telegram-chat-id",
        chat_id,
    ]
    completed = subprocess.run(
        command,
        cwd=PROJECT_DIR,
        capture_output=True,
        text=True,
    )
    if completed.returncode == 0:
        return True, ""
    detail = completed.stderr.strip() or completed.stdout.strip() or "Unknown error"
    return False, detail


def main() -> int:
    args = parse_args()
    config_file = Path(args.config).expanduser().resolve()
    state_file = Path(args.state_file).expanduser().resolve()
    config = load_local_config(config_file)
    telegram_config = config.get("telegram", {})
    if not isinstance(telegram_config, dict):
        raise ValueError(f"Invalid telegram config in {config_file}")

    bot_token = require_config(
        "TELEGRAM_BOT_TOKEN",
        str(telegram_config.get("bot_token", "")).strip(),
    )
    allowed_chat_id = str(telegram_config.get("chat_id", "")).strip()
    if not allowed_chat_id:
        raise ValueError(f"Missing telegram.chat_id in {config_file}")

    state = load_state(state_file)
    next_offset = int(state.get("last_update_id", 0) or 0) + 1

    while True:
        try:
            updates = get_updates(bot_token, next_offset, args.poll_timeout)
            for update in updates:
                update_id = int(update.get("update_id", 0) or 0)
                if update_id >= next_offset:
                    next_offset = update_id + 1
                    save_state(state_file, update_id)

                extracted = extract_message_text(update)
                if not extracted:
                    continue
                chat_id, text = extracted
                if chat_id != allowed_chat_id:
                    continue

                command_token = text.split()[0] if text.split() else ""
                command = command_token.split("@", 1)[0].lower()
                if command == "/check":
                    send_text(
                        bot_token,
                        chat_id,
                        "收到 /check，正在生成最新 portfolio 列表...",
                    )
                    ok, detail = run_check_command(config_file, chat_id)
                    if not ok:
                        send_text(
                            bot_token,
                            chat_id,
                            f"<pre>/check 执行失败\n{detail[:3000]}</pre>",
                        )
                elif command in {"/start", "/help"}:
                    send_text(
                        bot_token,
                        chat_id,
                        "<pre>可用指令:\n/check 立即运行最新 portfolio 查询并返回列表</pre>",
                    )
        except KeyboardInterrupt:
            return 0
        except Exception as exc:
            time.sleep(5)
            try:
                send_text(
                    bot_token,
                    allowed_chat_id,
                    f"<pre>Telegram command bot error\n{str(exc)[:3000]}</pre>",
                )
            except Exception:
                pass


if __name__ == "__main__":
    raise SystemExit(main())
