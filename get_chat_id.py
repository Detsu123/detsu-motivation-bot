from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv


load_dotenv()
token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

if not token:
    print("TELEGRAM_BOT_TOKEN олдсонгүй. .env файлдаа token оруулна уу.")
    sys.exit(1)

response = requests.get(
    f"https://api.telegram.org/bot{token}/getUpdates",
    timeout=30,
)
response.raise_for_status()
updates = response.json().get("result", [])

if not updates:
    print("Bot руугаа эхлээд /start илгээгээд дахин ажиллуулна уу.")
    sys.exit(0)

found: dict[str, str] = {}
for update in updates:
    message = update.get("message") or update.get("edited_message")
    if not message:
        continue
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    if chat_id is None:
        continue
    label = (
        chat.get("username")
        or " ".join(x for x in [chat.get("first_name"), chat.get("last_name")] if x)
        or chat.get("title")
        or "Unknown chat"
    )
    found[str(chat_id)] = label

if not found:
    print("Chat ID олдсонгүй.")
else:
    print("Олдсон chat ID:")
    for chat_id, label in found.items():
        print(f"- {label}: {chat_id}")
