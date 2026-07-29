# Detsu Motivation Bot — 2 цаг тутмын AI урмын бот

Энэ хувилбар таны компьютер унтарсан байсан ч GitHub Actions дээр ажиллана.

## Автомат хуваарь

Монголын цагаар өдөр бүр:

- 08:07
- 10:07
- 12:07
- 14:07
- 16:07
- 18:07
- 20:07
- 22:07

**00:00–08:00 хооронд автомат мессеж огт илгээхгүй.**

GitHub Actions цагийн яг эхэнд ачаалал ихтэй байж болдог тул `:07` минут сонгосон.
Ингэснээр 2 цагийн давтамж хэвээр мөртлөө хэт хоцрох эрсдэл багасна.

Код workflow хоцорч шөнийн quiet hours руу орвол дахин цаг шалгаж,
автомат мессежийг цуцална.

## Цагаас хамаарах агуулга

| Цаг | Мессежийн зорилго |
|---|---|
| 08:00 | Өглөөг тайван, эрч хүчтэй эхлүүлэх |
| 10:00 | Төвлөрөх, хойшлуулалтыг зогсоох |
| 12:00 | Өдрийн дунд дахин цэнэглэх |
| 14:00 | Үдээс хойших сулралыг давах |
| 16:00 | Гол ажлаа тууштай дуусгах |
| 18:00 | Ажил, хичээлээс тайван шилжих |
| 20:00 | Гуниг, эргэлзээг зөөллөж сэтгэл өргөх |
| 22:00 | Өдрөө тайван хааж, маргаашийг хөнгөлөх |

Мессеж бүр:

- Gemini-ээр шинээр зохиогдоно;
- 700–1400 орчим тэмдэгттэй;
- өмнөх 16 мессежийг харж давталтыг багасгана;
- тухайн цагийн сэтгэлзүйн хэрэгцээнд таарна;
- эцэстээ яг одоо хийх нэг жижиг алхам өгнө;
- Gemini түр ажиллахгүй бол тухайн цагийн нөөц мессеж илгээнэ.

## 1. Telegram bot үүсгэх

Telegram дээр `@BotFather` руу орж:

```text
/newbot
```

гэж илгээнэ. Өгсөн token-оо нууц хадгална.

Bot руугаа нэг удаа:

```text
/start
```

гэж илгээнэ.

## 2. Telegram Chat ID авах

ZIP файлыг задлаад терминал нээнэ.

### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
notepad .env
```

`.env` файлд:

```env
TELEGRAM_BOT_TOKEN=BOTFATHER_AAS_AVSAN_TOKEN
```

гэж оруулсны дараа:

```powershell
python get_chat_id.py
```

### Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python get_chat_id.py
```

Гарч ирсэн тоон утга нь `TELEGRAM_CHAT_ID`.

## 3. GitHub private repository үүсгэх

Шинэ private repository үүсгээд төслөө push хийнэ:

```bash
git init
git add .
git commit -m "Add Detsu motivation bot"
git branch -M main
git remote add origin YOUR_REPOSITORY_URL
git push -u origin main
```

## 4. GitHub Secrets нэмэх

Repository дотроос:

```text
Settings
→ Secrets and variables
→ Actions
→ New repository secret
```

Дараах гурван secret нэмнэ:

| Secret | Утга |
|---|---|
| `TELEGRAM_BOT_TOKEN` | BotFather-аас авсан token |
| `TELEGRAM_CHAT_ID` | `get_chat_id.py`-ийн гаргасан тоо |
| `GEMINI_API_KEY` | Google AI Studio API key |

Token болон API key-г workflow, Python файл эсвэл README дотор шууд бичихгүй.

## 5. Гараар турших

Repository:

```text
Actions
→ Detsu Motivation Bot
→ Run workflow
```

Гараар ажиллуулах үед quiet hours байсан ч зөвхөн туршилтын нэг мессеж илгээнэ.
Автомат schedule quiet hours-д илгээхгүй.

## Ашиглаж буй model

```text
gemini-3.6-flash
```

## Memory

`motivation_state.json` файл:

- өмнөх 16 мессеж;
- аль цагийн мессеж илгээгдсэн түүх

хадгална. Ингэснээр мессеж давтагдах болон нэг slot давхар илгээгдэх эрсдэл багасна.

## Хувийн мэдээллийг өөрчлөх

`.github/workflows/motivation.yml` файл дахь:

```yaml
USER_NAME: Дээгий
USER_CONTEXT: ...
```

хэсгийг өөрчилж болно. Bot руу өдөр бүр юм бичих шаардлагагүй.

## Алдаа шалгах

GitHub repository:

```text
Actions → Detsu Motivation Bot → хамгийн сүүлийн run
```

Log дотор:

```text
Telegram руу амжилттай илгээлээ
```

гарвал зөв ажилласан.

## Мессежийн шинэ өнгө аяс

- Танд `Дээгий` гэж байгалийн байдлаар хандана.
- Хэт сүржин motivational poster маягийн өгүүлбэрээс зайлсхийнэ.
- Яг дотны хүн Telegram-аар бичсэн мэт богино, амьд хэмнэлтэй байна.
- Тухайн цагийн мэдрэмжид таарсан 2–4 emoji хэрэглэнэ.
- Гунигийг үгүйсгэхгүй, харин ойлгож, дарамтгүй жижиг алхам санал болгоно.
