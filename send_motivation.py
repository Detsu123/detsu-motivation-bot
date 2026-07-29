from __future__ import annotations

import json
import logging
import os
import random
import re
import sys
import uuid
from difflib import SequenceMatcher
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import requests
from google import genai


TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"].strip()
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"].strip()
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"].strip()

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash").strip()
USER_NAME = os.getenv("USER_NAME", "Дээгий").strip()
USER_CONTEXT = os.getenv(
    "USER_CONTEXT",
    (
        "Монголд ажиллаж, суралцдаг оюутан. Программчлал, хиймэл оюун, "
        "сүлжээний инженерчлэл, англи хэл болон хувийн хөгжилдөө ахихыг хүсдэг. "
        "Олон зорилготой учраас заримдаа ядарч, эргэлзэж, эхлүүлсэн ажлаа "
        "хойшлуулах үе гардаг."
    ),
).strip()

LOCAL_TIMEZONE = ZoneInfo(os.getenv("TIMEZONE", "Asia/Ulaanbaatar"))
STATE_FILE = Path(os.getenv("STATE_FILE", "motivation_state.json"))
HISTORY_LIMIT = int(os.getenv("HISTORY_LIMIT", "16"))
MIN_MESSAGE_CHARS = int(os.getenv("MIN_MESSAGE_CHARS", "700"))
MAX_MESSAGE_CHARS = int(os.getenv("MAX_MESSAGE_CHARS", "1400"))
ALLOW_OUTSIDE_WINDOW = os.getenv("ALLOW_OUTSIDE_WINDOW", "false").lower() == "true"

ALLOWED_HOURS = (8, 10, 12, 14, 16, 18, 20, 22)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class TimeProfile:
    title: str
    emotional_need: str
    desired_effect: str
    action_style: str
    avoid: str


TIME_PROFILES: dict[int, TimeProfile] = {
    8: TimeProfile(
        "Өглөөг тайван бөгөөд эрч хүчтэй эхлүүлэх",
        "Сэрээд шууд дарамт мэдрүүлэхгүйгээр итгэл төрүүлж, шинэ өдөр бол дахин эхлэх боломж гэдгийг мэдрүүлэх.",
        "Нойрмог, хүнд мэдрэмжийг багасгаж, өнөөдрийн хамгийн чухал нэг зүйлдээ төвлөрөх хүсэл төрүүлэх.",
        "5-10 минутын дотор эхлүүлж болох маш жижиг өглөөний алхам.",
        "Өглөөнөөс хэт шахах, бүх зорилгыг нэг дор сануулах, гэмшил төрүүлэх хэллэг.",
    ),
    10: TimeProfile(
        "Анхаарлаа төвлөрүүлж, хойшлуулалтыг зогсоох",
        "Өдрийн эхний эрчийг алдалгүй, өөрийгөө дайчлах боловч буруутгалгүйгээр хөдөлгөөнд оруулах.",
        "Сошиал, эргэлзээ, төгс хийх хүсэлд гацалгүй бодит ажил эхлүүлэх.",
        "20-25 минутын төвлөрсөн нэг блок эхлүүлэх тодорхой санал.",
        "Хэт сүржин үг, айлгах, бусадтай харьцуулах, амрах эрхгүй мэт мэдрүүлэх.",
    ),
    12: TimeProfile(
        "Өдрийн дунд өөрийгөө дахин цэнэглэх",
        "Өглөөнөөс хойш хийсэн жижиг ахицыг анзаарах, амжаагүй зүйлээс болж өдрийг бүтэлгүй болсон мэт бодохоос сэргийлэх.",
        "Сэтгэлээ шинээр цэгцэлж, үлдсэн өдрийг дахин эхлүүлэх мэдрэмж авах.",
        "Ус уух, богино завсарлага авах эсвэл үлдсэн ажлаас нэгийг сонгох зэрэг энгийн reset алхам.",
        "Өглөөг дүгнэн шүүмжлэх, бүтээмжийг хүний үнэ цэнтэй холбох.",
    ),
    14: TimeProfile(
        "Үдээс хойших сулралыг даван туулах",
        "Нойрмог, залхуу, хийх хүсэлгүй мэдрэмж хэвийн гэдгийг зөвшөөрөөд бага хүчээр дахин хөдөлгөх.",
        "Том даалгавраас айх айдсыг багасгаж, хамгийн жижиг хэсгийг эхлүүлэх.",
        "Хоёр минутын эхлэл эсвэл хамгийн амархан дэд ажлыг дуусгах.",
        "Залхуу гэж нэрлэх, хэт ачааллаар хүчлэхийг шаардах.",
    ),
    16: TimeProfile(
        "Өдрийн чухал ажлыг тууштай дуусгах",
        "Өдөр дуусах дөхөхөд сандралгүйгээр өнөөдрийн гол ажлын нэг хэсгийг бодитоор хаах зориг өгөх.",
        "Олон жижиг зүйл рүү үсчихгүй, хамгийн үнэ цэнтэй нэг үр дүн гаргах.",
        "Дууссан гэж тооцох тодорхой шалгууртай 25-40 минутын алхам.",
        "Бүх ажлыг өнөөдөр заавал дуусгах шахалт, орой хүртэл амралтгүй ажиллуулах.",
    ),
    18: TimeProfile(
        "Ажил, хичээлээс хувийн амьдрал руу тайван шилжих",
        "Өдрийн ачааллыг өөртэйгөө хамт чирэхгүйгээр тайвшрах, хийсэн зүйлээ үнэлэх.",
        "Өөрийгөө хоосон эсвэл хангалтгүй мэт бодохоос хамгаалж, оройн цагаа ухаалгаар сонгох.",
        "10-20 минут амрах эсвэл оройн ганц зорилгоо сонгох.",
        "Амралтыг залхуурал мэт харагдуулах, ажлын дараа том хөтөлбөр тулгах.",
    ),
    20: TimeProfile(
        "Гуниг, ганцаардал, өөрийгөө голох мэдрэмжийг зөөллөх",
        "Орой бодол ихсэж, бусадтай өөрийгөө харьцуулах үед хүний үнэ цэнэ өнөөдрийн үр дүнгээр хэмжигдэхгүй гэдгийг дулаанаар сануулах.",
        "Сэтгэлийг хөнгөлж, өөрийнхөө талд зогсох, маргааш руу итгэлтэй харах мэдрэмж төрүүлэх.",
        "Өөртөө анхаарах нэг энгийн үйлдэл эсвэл итгэдэг хүнтэйгээ богино холбоо барих зэрэг дарамтгүй алхам.",
        "Хуурамч өөдрөг байдал, гунигийг үгүйсгэх, сэтгэл хөдлөлийг оношлох, бүх зүйл шууд сайхан болно гэж амлах.",
    ),
    22: TimeProfile(
        "Өдрөө тайван хааж, маргаашийн ачааг багасгах",
        "Амжаагүй зүйлээс болж өөрийгөө зэмлэхгүйгээр өнөөдрийн хөдөлмөрийг хааж, амрах зөвшөөрөл өгөх.",
        "Толгой доторх ажлуудыг суллаж, маргаашийн эхний алхмаа тодорхой болгоод тайван амрахад бэлтгэх.",
        "Маргаашийн хамгийн эхний нэг ажлыг бичээд төхөөрөмжөөс холдох.",
        "Шөнө үргэлжлүүлэн ажиллахыг уриалах, хоцорсон зүйлээр айлгах.",
    ),
}


FALLBACK_MESSAGES: dict[int, str] = {
    8: (
        "Өглөөний мэнд, {name}. Өнөөдөр бүхнийг төгс хийх өдөр биш; өөрийнхөө "
        "талд зогсоод нэг зөв алхам хийх өдөр. Өчигдрийн эргэлзээ өнөөдрийн "
        "боломжийг шийдэх албагүй.\n\nОдоо том зорилгуудаа зэрэг бодох хэрэггүй. "
        "Хамгийн чухал нэг зүйлээ сонгоод ердөө арван минут эхлүүл. Эхэлсний "
        "дараа хөдөлгөөн өөрөө дараагийн хүчийг бий болгодог."
    ),
    10: (
        "{name}, яг одоо төгс төлөвлөгөө хүлээх тусам эхлэл улам хүнд санагдана. "
        "Чи бүх ажлыг дуусгах шаардлагагүй, харин нэг ажлынхаа эхний бодит хэсгийг "
        "хийхэд хангалттай.\n\nУтсаа хол тавиад 25 минутын таймер асаа. Энэ "
        "хугацаанд зөвхөн нэг файл, нэг даалгавар эсвэл нэг асуудал дээр ажилла."
    ),
    12: (
        "{name}, өдрийн тал өнгөрсөн нь боломж дууссан гэсэн үг биш. Өглөө "
        "хүссэнээр болоогүй байсан ч үлдсэн өдрийг энэ мөчөөс шинээр эхлүүлж "
        "болно.\n\nТүр амьсгаа аваад, ус уугаад, үлдсэн ажлуудаас хамгийн үнэ "
        "цэнтэй нэгийг сонго. Нэг утгатай ахиц хангалттай."
    ),
    14: (
        "{name}, үдээс хойш хүч сулрах нь чамайг залхуу гэсэн үг биш. Оюун ухаан "
        "том ажлыг хараад хамгаалах гэж хойшлуулах үе байдаг. Тиймээс ажлаа жижиг "
        "болго.\n\nФайл нээ, гарчиг бич, эхний мөрийг зас. Эхлэл жижиг байж болно."
    ),
    16: (
        "{name}, өдөр дуусах дөхөхөд бүх дутуу зүйл зэрэг чанга сонсогддог. "
        "Гэхдээ чиний үүрэг бүгдийг амжуулах биш, хамгийн үнэ цэнтэй нэг үр дүнг "
        "хаах юм.\n\nНэг ажлыг сонгоод дууссан гэж үзэх шалгуураа тодорхойл. "
        "Дараагийн 30 минут зөвхөн тэр шалгуур руу ажилла."
    ),
    18: (
        "{name}, өнөөдрийн ажлыг толгойдоо дахин дахин үргэлжлүүлэх шаардлагагүй. "
        "Чи хийж чадсан зүйлээ үнэлээд, одоо эрч хүчээ буцаан авах эрхтэй.\n\n"
        "Арван минут ямар ч ажилгүй тайван бай. Дараа нь оройн цагаас зөвхөн нэг "
        "зүйлийг сонго: амрах эсвэл өөрт чухал жижиг зорилгоо урагшлуулах."
    ),
    20: (
        "{name}, оройн нам гүмд эргэлзээ бодитоосоо том сонсогдож болно. Өнөөдөр "
        "хүссэнээр болоогүй зүйл байсан ч тэр нь чиний бүх үнэ цэнийг тодорхойлохгүй.\n\n"
        "Одоо өөрийнхөө талд нэг жижиг үйлдэл хий: дуртай дуугаа сонс, богино алх, "
        "эсвэл итгэдэг хүндээ мэнд хүргэ."
    ),
    22: (
        "{name}, өнөөдөр амжаагүй зүйлс маргаашийн чамайг буруутгах шалтгаан биш. "
        "Өнөөдрийн хөдөлмөрийг энд хааж, амрах боломж өгөх нь бас сахилга бат.\n\n"
        "Маргааш хамгийн түрүүнд хийх ганц ажлаа бич. Дараа нь дэлгэцээс холдоод "
        "өдрөө дуусга."
    ),
}


def load_state() -> dict[str, Any]:
    default = {"history": [], "sent_slots": []}
    if not STATE_FILE.exists():
        return default
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        logger.exception("State файл уншихад алдаа гарлаа.")
        return default
    if not isinstance(data, dict):
        return default
    history = data.get("history", [])
    slots = data.get("sent_slots", [])
    return {
        "history": [str(x).strip() for x in history if str(x).strip()][-HISTORY_LIMIT:]
        if isinstance(history, list) else [],
        "sent_slots": [str(x) for x in slots if str(x)][-60:]
        if isinstance(slots, list) else [],
    }


def save_state(state: dict[str, Any]) -> None:
    state["history"] = state.get("history", [])[-HISTORY_LIMIT:]
    state["sent_slots"] = state.get("sent_slots", [])[-60:]
    temp = STATE_FILE.with_suffix(STATE_FILE.suffix + ".tmp")
    temp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(STATE_FILE)


def nearest_scheduled_hour(now: datetime) -> int:
    return min(ALLOWED_HOURS, key=lambda hour: abs(hour - now.hour))


def resolve_profile_hour(now: datetime) -> int | None:
    if now.hour in ALLOWED_HOURS:
        return now.hour
    previous = [hour for hour in ALLOWED_HOURS if hour <= now.hour]
    if previous:
        latest = max(previous)
        if now.hour - latest <= 1:
            return latest
    if ALLOW_OUTSIDE_WINDOW:
        return nearest_scheduled_hour(now)
    return None


def clean_text(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:text|markdown)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"^(Мессеж|Хариулт)\s*:\s*", "", text, flags=re.IGNORECASE)
    return (text[:3897].rstrip() + "...") if len(text) > 3900 else text



def build_prompt(
    now: datetime,
    hour: int,
    history: list[str],
    attempt: int,
    request_nonce: str,
) -> str:
    profile = TIME_PROFILES[hour]
    previous = "Өмнөх мессеж байхгүй."
    if history:
        previous = "\n\n--- ӨМНӨХ МЕССЕЖ ---\n\n".join(history)

    weekdays = ["Даваа", "Мягмар", "Лхагва", "Пүрэв", "Баасан", "Бямба", "Ням"]

    styles = [
        "дотно найз нь яг хэрэгтэй үед нь мессеж бичиж буй мэт",
        "Дээгийг сайн мэддэг, тайван сонсож чаддаг хүн ярьж буй мэт",
        "хиймэл сүржин үггүй, бодит амьдралыг нь ойлгосон дулаахан чат мэт",
        "бага зэрэг хөгжилтэй мөртлөө сэтгэлд хүрэх найзын мессеж мэт",
        "хэт зааварласан биш, мөрөн дээр нь зөөлөн алгадаад зоригжуулж буй мэт",
        "урт лекц биш, чин сэтгэлээсээ санаа тавьсан хүн бичсэн мэт",
    ]

    openings = [
        "өнөөдрийн яг энэ мөчийг анзаарсан мэт эхэл",
        "өмнөх мессежүүдэд байгаагүй шинэ дүр зураг эсвэл ажиглалтаар эхэл",
        "маш энгийн, хүний амьд ярианы нэг өгүүлбэрээр эхэл",
        "зөөлөн хошигнолтой боловч эвгүй биш байдлаар эхэл",
        "тухайн цагийн ядрал эсвэл бодлыг нэрлэж эхэл",
        "гэнэт ирсэн дотны мессеж шиг шууд эхэл",
    ]

    emotional_angles = [
        "өөрийгөө голохоо багасгах",
        "гацсан газраасаа жижиг хөдөлгөөн хийх",
        "хийсэн ахицаа анзаарах",
        "толгой доторх дарамтыг багасгах",
        "эрч хүчгүй үед өөртөө зөөлөн хандах",
        "төгс хийх хүсэлд гацахгүй эхлэх",
        "бусадтай харьцуулах бодлыг сулруулах",
        "өнөөдрийн үлдсэн цагийг шинээр эхлүүлэх",
    ]

    return f"""
Чи Дээгийг сайн мэддэг дотны, дулаахан найз шиг Монгол хэлээр бич.
Хариулт AI-ийн текст, илтгэл, motivational poster шиг биш,
яг Telegram-аар чин сэтгэлээсээ бичсэн бодит хүний мессеж мэт сонсогдох ёстой.

Одоогийн цаг: {now:%Y-%m-%d %H:%M:%S}
Гараг: {weekdays[now.weekday()]}
Хуваарийн цаг: {hour:02d}:00
Хэрэглэгч: {USER_NAME or "нэр дурдахгүй"}
Нөхцөл: {USER_CONTEXT}

Энэ цагийн зорилго: {profile.title}
Одоогийн хэрэгцээ: {profile.emotional_need}
Уншсаны дараах нөлөө: {profile.desired_effect}
Эцсийн жижиг алхам: {profile.action_style}
Зайлсхийх зүйл: {profile.avoid}

Энэ удаагийн бүтээлч чиглэл:
- Өнгө аяс: {random.choice(styles)}
- Эхлэл: {random.choice(openings)}
- Гол сэтгэлзүйн өнцөг: {random.choice(emotional_angles)}
- Давтагдашгүй request ID: {request_nonce}
- Дахин зохиох оролдлого: {attempt}

Шаардлага:
- {MIN_MESSAGE_CHARS}-{MAX_MESSAGE_CHARS} орчим тэмдэгт, 4-6 богино догол мөр.
- Эхний 1-2 өгүүлбэрээр тухайн цагийн бодит мэдрэмжийг онож хэл.
- Дээгийд дотны хүн нь бичиж байгаа мэт дулаан, энгийн, чин сэтгэлтэй бай.
- Хэт төгс найруулга, номын хэллэг, AI-ийн хэвшмэл өгүүлбэр бүү ашигла.
- Тайвшруулалт, бодит эргэцүүлэл, өөрийгөө дайчлах түлхэц гурвыг тэнцвэржүүл.
- Гунигийг үгүйсгэхгүй, оношлохгүй, хуурамч амлалт өгөхгүй.
- Өмнөх мессежийн өгүүлбэр, зүйрлэл, эхлэл, санааны дараалал,
  emoji-ийн дараалал болон төгсгөлийг хуулбарлахгүй.
- Өмнөх мессежтэй зөвхөн хэдэн үг солиод адил бүтэц гаргахыг хориглоно.
- Нэрийг хамгийн ихдээ нэг удаа хэрэглэ.
- 2-4 emoji-г нэг дор бөөгнөрүүлэхгүй, байгалийн байдлаар тарааж хэрэглэ.
- Эцэст нь яг одоо хийх нэг жижиг, дарамтгүй, тодорхой алхам өг.
- Зөвхөн Telegram-д илгээх бэлэн мессеж гарга.
- Тайлбар, сонголт, жагсаалтын дугаар, markdown code fence бүү гарга.

Сүүлийн мессежүүд:
{previous}
""".strip()


def similarity_ratio(first: str, second: str) -> float:
    return SequenceMatcher(
        None,
        first.casefold().strip(),
        second.casefold().strip(),
    ).ratio()


def is_too_similar(message: str, history: list[str]) -> bool:
    if not history:
        return False

    # Сүүлийн мессежүүдийн аль нэгтэй 62%-иас дээш төстэй бол дахин зохиолгоно.
    return any(
        similarity_ratio(message, old_message) >= 0.62
        for old_message in history[-HISTORY_LIMIT:]
    )


def generate_message(now: datetime, hour: int, state: dict[str, Any]) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY)
    request_nonce = str(uuid.uuid4())

    last_message = ""
    for attempt in range(1, 4):
        prompt = build_prompt(
            now=now,
            hour=hour,
            history=state["history"],
            attempt=attempt,
            request_nonce=request_nonce,
        )

        # Gemini 3.6 Flash нь шинэ Interactions API-аар дуудагдана.
        interaction = client.interactions.create(
            model=GEMINI_MODEL,
            input=prompt,
        )

        message = clean_text(interaction.output_text or "")
        last_message = message

        if len(message) < 300:
            logger.warning(
                "Gemini хэт богино хариу өглөө. attempt=%s",
                attempt,
            )
            continue

        if is_too_similar(message, state["history"]):
            logger.warning(
                "Gemini өмнөх зурвастай хэт төстэй байна. Дахин зохиолгож байна. "
                "attempt=%s",
                attempt,
            )
            continue

        return message

    if len(last_message) >= 300:
        return last_message

    raise ValueError("Gemini 3 оролдлогын дараа хүчинтэй шинэ мессеж өгсөнгүй.")


def send_to_telegram(message: str) -> None:
    response = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "disable_web_page_preview": True,
        },
        timeout=30,
    )
    response.raise_for_status()
    payload = response.json()
    if not payload.get("ok"):
        raise RuntimeError(f"Telegram API error: {payload}")


def main() -> int:
    now = datetime.now(LOCAL_TIMEZONE)
    hour = resolve_profile_hour(now)
    if hour is None:
        logger.info("Quiet hours эсвэл зөвшөөрөгдсөн цагаас гадуур: %s", now.isoformat())
        return 0

    state = load_state()
    slot = f"{now:%Y-%m-%d}-{hour:02d}"
    if slot in state["sent_slots"] and not ALLOW_OUTSIDE_WINDOW:
        logger.info("Энэ slot өмнө илгээгдсэн: %s", slot)
        return 0

    try:
        message = generate_message(now, hour, state)
        logger.info("Gemini мессеж үүсгэлээ. model=%s hour=%s", GEMINI_MODEL, hour)
    except Exception:
        logger.exception("Gemini алдаа өглөө. Нөөц мессеж ашиглана.")
        message = (
            FALLBACK_MESSAGES[hour].format(name=USER_NAME or "найз минь")
            + "\n\n"
            + random.choice(
                [
                    "Өнөөдрийн энэ мөч өмнөхөөсөө өөр. Одоо өөртөө багахан зай гаргаарай 🌿",
                    "Яг одоо бүхнийг засах хэрэггүй ээ. Нэг жижиг алхам л хангалттай ✨",
                    "Өөрийгөө яаруулахын оронд түр амьсгаа аваад дараагийн ганц зүйлээ сонгоё 🤍",
                    "Өнөөдрийн Дээгийд хэрэгтэй зүйл нь төгс байдал биш, багахан хөдөлгөөн шүү 🌱",
                ]
            )
        )

    send_to_telegram(message)
    state["history"].append(message)
    state["sent_slots"].append(slot)
    save_state(state)
    logger.info("Telegram руу амжилттай илгээлээ. slot=%s", slot)
    return 0


if __name__ == "__main__":
    sys.exit(main())
