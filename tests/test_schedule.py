import os
import sys
import types as py_types
from datetime import datetime
from zoneinfo import ZoneInfo

# This test file validates schedule logic only. Stub google-genai so the
# tests remain offline and do not require an API client installation.
google_module = py_types.ModuleType("google")
genai_module = py_types.ModuleType("google.genai")
genai_module.types = py_types.SimpleNamespace(GenerateContentConfig=object)
google_module.genai = genai_module
sys.modules.setdefault("google", google_module)
sys.modules.setdefault("google.genai", genai_module)

os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("TELEGRAM_CHAT_ID", "123")
os.environ.setdefault("GEMINI_API_KEY", "test-key")

import send_motivation


TZ = ZoneInfo("Asia/Ulaanbaatar")


def local_time(hour: int, minute: int = 7) -> datetime:
    return datetime(2026, 7, 29, hour, minute, tzinfo=TZ)


def test_allowed_schedule_hours() -> None:
    for hour in (8, 10, 12, 14, 16, 18, 20, 22):
        assert send_motivation.resolve_profile_hour(local_time(hour)) == hour


def test_quiet_hours_do_not_send() -> None:
    old_value = send_motivation.ALLOW_OUTSIDE_WINDOW
    send_motivation.ALLOW_OUTSIDE_WINDOW = False
    try:
        for hour in range(0, 8):
            assert send_motivation.resolve_profile_hour(local_time(hour)) is None
    finally:
        send_motivation.ALLOW_OUTSIDE_WINDOW = old_value


def test_one_hour_delay_uses_previous_profile() -> None:
    assert send_motivation.resolve_profile_hour(local_time(11, 5)) == 10
    assert send_motivation.resolve_profile_hour(local_time(23, 5)) == 22
