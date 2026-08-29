"""Telegram delivery helper — posts HTML-formatted messages to a channel.

Reads TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID from the environment
(set as GitHub Actions secrets — never hardcode them).
Splits long content into chunks under Telegram's 4096-character limit,
breaking only on section boundaries or newlines so formatting survives.
"""

import html
import os
import time

import requests

API = "https://api.telegram.org/bot{token}/{method}"
LIMIT = 3900  # stay safely under Telegram's 4096-char message limit


def esc(text) -> str:
    """Escape text for Telegram HTML parse mode."""
    return html.escape(str(text), quote=False)


def _split(text: str) -> list[str]:
    """Split on blank lines first, then single newlines, never mid-line."""
    if len(text) <= LIMIT:
        return [text]
    chunks, current = [], ""
    for block in text.split("\n\n"):
        candidate = f"{current}\n\n{block}" if current else block
        if len(candidate) <= LIMIT:
            current = candidate
            continue
        if current:
            chunks.append(current)
            current = ""
        if len(block) <= LIMIT:
            current = block
            continue
        for line in block.split("\n"):  # oversized block: split by lines
            candidate = f"{current}\n{line}" if current else line
            if len(candidate) > LIMIT:
                chunks.append(current)
                current = line
            else:
                current = candidate
    if current:
        chunks.append(current)
    return chunks


def send(text: str, disable_preview: bool = True) -> None:
    """Send `text` (Telegram HTML) to the channel, chunking if needed."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    for chunk in _split(text):
        r = requests.post(
            API.format(token=token, method="sendMessage"),
            json={
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": disable_preview,
            },
            timeout=30,
        )
        if r.status_code == 429:  # rate-limited: wait and retry once
            retry = r.json().get("parameters", {}).get("retry_after", 5)
            time.sleep(retry + 1)
            r = requests.post(
                API.format(token=token, method="sendMessage"),
                json={
                    "chat_id": chat_id,
                    "text": chunk,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": disable_preview,
                },
                timeout=30,
            )
        r.raise_for_status()
        body = r.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram error: {body}")
        time.sleep(1.2)  # respect ~1 msg/sec per chat


def send_document(path: str, caption: str = "") -> None:
    """Send a file (e.g. the dashboard HTML) to the channel as a document."""
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    chat_id = os.environ["TELEGRAM_CHAT_ID"]
    with open(path, "rb") as fh:
        r = requests.post(
            API.format(token=token, method="sendDocument"),
            data={"chat_id": chat_id, "caption": caption},
            files={"document": fh},
            timeout=60,
        )
    r.raise_for_status()
    if not r.json().get("ok"):
        raise RuntimeError(f"Telegram error: {r.json()}")
