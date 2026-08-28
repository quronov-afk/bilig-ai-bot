import json
import os
import re
import sqlite3
import asyncio
import threading
import traceback
from datetime import datetime
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)


# ==========================================================
# NOSOZLIK JURNALI
# ----------------------------------------------------------
# Xatolar Render jurnaliga yoziladi, lekin uni faqat loyiha egasi
# ko‘ra oladi. Shuning uchun so‘nggi yozuvlar shu yerda ham saqlanadi
# va himoyalangan manzil orqali o‘qiladi. Bu ma'lumot faqat texnik:
# format, hajm, xato matni. Bolalarning ismi yoki matnlari yozilmaydi.
# ==========================================================
from collections import deque
LOG_RING = deque(maxlen=400)


def log_line(msg):
    line = datetime.now().strftime("%m-%d %H:%M:%S") + "  " + str(msg)
    LOG_RING.append(line)
    print(line, flush=True)


# ==========================================================
# AI SARFINI O‘LCHASH
# ==========================================================
# Har bir chaqiruvdan keyin sarflangan token soni bazaga yoziladi.
# Shundan keyin "pul qayerga ketyapti" degan savolga taxmin emas,
# aniq raqam bilan javob beramiz.
_usage_db_path = "/var/data/bot_base.db" if os.path.exists("/var/data") else "bot_base.db"
_usage_lock = threading.Lock()
_usage_conn = None


def _usage_log(task: str, response):
    """Bitta AI chaqiruvining token sarfini AI_Usage jadvaliga yozadi."""
    global _usage_conn
    try:
        u = getattr(response, "usage_metadata", None)
        if u is None:
            return
        with _usage_lock:
            if _usage_conn is None:
                _usage_conn = sqlite3.connect(_usage_db_path, check_same_thread=False, timeout=10)
                _usage_conn.execute("""CREATE TABLE IF NOT EXISTS AI_Usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT,
                    model TEXT,
                    prompt_tokens INTEGER,
                    output_tokens INTEGER,
                    total_tokens INTEGER,
                    created_at TEXT
                )""")
                _usage_conn.commit()
            _usage_conn.execute(
                "INSERT INTO AI_Usage (task, model, prompt_tokens, output_tokens, total_tokens, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (task, GEMINI_MODEL,
                 getattr(u, "prompt_token_count", 0) or 0,
                 getattr(u, "candidates_token_count", 0) or 0,
                 getattr(u, "total_token_count", 0) or 0,
                 datetime.now().isoformat(timespec="seconds"))
            )
            _usage_conn.commit()
    except Exception:
        # O‘lchov hech qachon asosiy ishni to‘xtatmasligi kerak
        pass


class UserFacingError(RuntimeError):
    """Matni foydalanuvchiga ko‘rsatish uchun YOZILGAN xato.

    Boshqa hamma xatolar texnik hisoblanadi: ular jurnalga yoziladi,
    foydalanuvchiga esa sodda, tushunarli xabar ko‘rsatiladi.
    """


class AiEmptyResponse(UserFacingError):
    """AI javob berdi, lekin matn bo‘sh — sababi xabar matnida."""


def human_error(e):
    """Texnik xatoni foydalanuvchi tushunadigan jumlaga aylantiradi.

    Ekranda «400 INVALID_ARGUMENT» yoki «'NoneType' object has no
    attribute» kabi yozuvlar chiqmasligi kerak — ular faqat jurnalda
    qoladi.
    """
    if isinstance(e, UserFacingError):
        return str(e)
    t = (str(e) or "").lower()
    if "429" in t or "resource_exhausted" in t or "quota" in t:
        return "AI hozir juda band. Bir-ikki daqiqadan so‘ng qayta urinib ko‘ring."
    if "timeout" in t or "timed out" in t or "deadline" in t:
        return "Javob kutish vaqti tugadi. Internet tezlashganda qayta urinib ko‘ring."
    if "invalid_argument" in t or "unsupported" in t:
        return "Yuborilgan fayl AI ga to‘g‘ri kelmadi. Qaytadan yozib ko‘ring."
    if "permission" in t or "api key" in t or "unauthenticated" in t:
        return "AI xizmatiga ulanib bo‘lmadi. Administratorga xabar bering."
    return "Hozir bo‘lmadi. Biroz kutib, qaytadan urinib ko‘ring."


def _text_or_reason(task, response):
    """Javob matnini olamiz. Bo‘sh bo‘lsa — SABABINI aniq aytamiz.

    Ilgari bu yerda hech qanday tekshiruv yo‘q edi: model bo‘sh javob
    qaytarsa, `clean_json(None)` ichida "'NoneType' object has no attribute
    'strip'" degan tushunarsiz xato chiqardi. Na foydalanuvchi, na biz nima
    bo‘lganini bilardik. Endi sabab aniq nomlanadi.
    """
    text = getattr(response, "text", None)
    if text and text.strip():
        return text

    reason = ""
    try:
        cands = getattr(response, "candidates", None) or []
        if cands:
            reason = str(getattr(cands[0], "finish_reason", "") or "")
    except Exception:
        pass
    blocked = ""
    try:
        fb = getattr(response, "prompt_feedback", None)
        blocked = str(getattr(fb, "block_reason", "") or "")
    except Exception:
        pass

    up = (reason + " " + blocked).upper()
    log_line("[ai] BO‘SH JAVOB [%s] finish_reason=%r block_reason=%r" % (task, reason, blocked))
    if "MAX_TOKEN" in up:
        raise AiEmptyResponse(
            "AI javobi juda uzun bo‘lib ketdi va oxirigacha yetmadi. "
            "Sahifalar sonini kamaytirib ko‘ring."
        )
    if "SAFETY" in up or "BLOCK" in up or "PROHIBITED" in up:
        raise AiEmptyResponse(
            "AI yuborilgan rasmlarni qabul qilmadi (xavfsizlik filtri). "
            "Boshqa sahifalarni suratga olib ko‘ring."
        )
    if "RECITATION" in up:
        raise AiEmptyResponse("AI matnni ko‘chirma deb hisobladi. Boshqa sahifalarni tanlang.")
    raise AiEmptyResponse("AI bo‘sh javob qaytardi (sabab: %s)" % (reason or blocked or "noma'lum"))


# Model "o‘ylash"ni o‘chirishni qo‘llab-quvvatlaydimi — birinchi xatodan keyin aniqlanadi
_thinking_off_supported = True


# ==========================================================
# MADANIY MEZON — barcha AI ko‘rsatmalariga qo‘shiladi
# ----------------------------------------------------------
# Ega talabi (2026-08-28): ilova O‘zbekistondagi oilalar uchun. Savol,
# mazmun va baholar musulmon Sharqi an'analari, madaniyati va mentaliteti
# doirasida bo‘lishi SHART.
# ==========================================================
MADANIY_MEZON = """
MADANIY MEZON — MAJBURIY:
· Ota-ona va kattalarga hurmat eng yuqori qadriyat. Kattalarga qarshi
  chiqish «jasorat» deb maqtalmasin — oqibati muhokama qilinsin.
· Halollik, sabr, shukr, hayo, kamtarlik, mehmondo‘stlik, saxovat,
  mehnatsevarlik, va'daga vafo — ijobiy o‘lchov shular.
· Oila va qarindoshlik rishtalari, opa-uka inoqligi qadrli holat sifatida
  ko‘rsatilsin. Ustoz-shogird munosabati va ilm qadri e'zozlansin.
· Mahalliy madaniyatga yot lavhalarga (ichkilik, qiz-yigit munosabatlari,
  e'tiqodni masxaralash) urg‘u berilmasin; asarning umuminsoniy
  saboqlariga e'tibor qaratilsin.
· Asarda YO‘Q narsani qo‘shma va sun'iy diniy tus BERMA — bor matnni shu
  qadriyatlar nuqtai nazaridan ko‘r, xolos.
"""


async def _ask(task: str, contents, json_mode=False, max_tokens=None, fast=False, attempts=2):
    """Barcha Gemini chaqiruvlari shu yagona joydan o‘tadi.

    fast=True     — sodda vazifa (bet raqamini o‘qish kabi): model ortiqcha
                    "o‘ylamaydi", ya'ni ortiqcha token sarflanmaydi.
    json_mode     — javob rasman JSON formatida so‘raladi. Shunda format
                    buzilib, ikkinchi marta to‘lash holati deyarli yo‘qoladi.
    max_tokens    — javob uzunligi chegarasi (faqat fast rejimda xavfsiz).
    """
    global _thinking_off_supported
    if client is None:
        # Ilgari bu holatda «'NoneType' object has no attribute 'aio'» degan
        # tushunarsiz xato chiqardi.
        raise RuntimeError("AI kaliti sozlanmagan (GEMINI_API_KEY yo‘q)")
    tries = 0
    while True:
        tries += 1
        cfg = {}
        if json_mode:
            cfg["response_mime_type"] = "application/json"
        use_fast = bool(fast) and _thinking_off_supported
        if use_fast:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            if max_tokens:
                cfg["max_output_tokens"] = max_tokens
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents,
                config=types.GenerateContentConfig(**cfg) if cfg else None,
            )
            _usage_log(task, response)
            # Bo‘sh javob ham xato — shu yerda ushlaymiz. Shunda quyidagi
            # `except` ishlaydi va yana bir marta urinib ko‘riladi.
            _text_or_reason(task, response)
            return response
        except Exception as e:
            # Tejash sozlamasi ("o‘ylashni o‘chirish" va javob uzunligi chegarasi)
            # modelga yoqmasligi mumkin. Ilgari xato MATNIDAN bilishga urinardik,
            # lekin Gemini shunchaki "Request contains an invalid argument" deb
            # javob berardi — natijada sahifa rasmi umuman tekshirilmay qolgan edi.
            # Endi tejash rejimida HAR QANDAY xatodan keyin bir marta oddiy
            # rejimda qayta urinamiz. Bir marta ishlamasa, boshqa urinilmaydi.
            if use_fast and not isinstance(e, AiEmptyResponse):
                _thinking_off_supported = False
                log_line(f"[ai] tejash rejimi bu modelga to‘g‘ri kelmadi, oddiy rejimga o‘tildi ({task}): {e}")
                tries -= 1
                continue
            log_line(f"[ai] XATO [{task} - urinish {tries}]: {e}")
            if tries >= attempts:
                raise
            await asyncio.sleep(1)

def image_part(image_bytes: bytes):
    """Rasmni AI ga uzatish uchun tayyorlaydi.

    Rasm turi baytlarning o‘zidan aniqlanadi. Ilgari hamma rasm «jpeg» deb
    yuborilardi — telefon boshqa turda (png yoki webp) yuborsa, AI so‘rovni
    rad etardi.
    """
    head = image_bytes[:12]
    if head.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        mime = "image/webp"
    elif head[:3] == b"GIF":
        mime = "image/gif"
    else:
        mime = "image/jpeg"
    return types.Part.from_bytes(data=image_bytes, mime_type=mime)


def audio_kind(audio_bytes: bytes):
    """Audio formatini baytlaridan aniqlaydi (nosozlik izlashda ham kerak)."""
    head = audio_bytes[:16]
    if head[:4] == b"RIFF" and head[8:12] == b"WAVE":
        return "audio/wav"
    if head[:4] == b"OggS":
        return "audio/ogg"
    if head[:4] == b"fLaC":
        return "audio/flac"
    if head[:3] == b"ID3" or (len(head) > 1 and head[0] == 0xFF and (head[1] & 0xE0) == 0xE0):
        return "audio/mp3"
    if head[4:8] == b"ftyp":
        return "audio/mp4"
    if head[:4] == b"\x1aE\xdf\xa3":
        return "audio/webm"
    if head[:4] == b"FORM":
        return "audio/aiff"
    return "noma'lum"


def audio_part(audio_bytes: bytes):
    """Audioni AI ga uzatish uchun tayyorlaydi.

    Ilgari hamma audio «audio/ogg» deb yuborilardi. Lekin brauzer odatda
    WEBM (Chrome/Android) yoki MP4 (iPhone) formatida yozadi — natijada
    AI faylni ocholmay, so‘rovni bir zumda rad etardi. Endi format
    baytlarning o‘zidan aniqlanadi.
    """
    kind = audio_kind(audio_bytes)
    if kind == "noma'lum":
        kind = "audio/mp3"
    return types.Part.from_bytes(data=audio_bytes, mime_type=kind)


def clean_json(text: str) -> str:
    """Gemini qaytargan matndan JSON blokini xavfsiz ajratib olish (RegEx orqali)"""
    text = text.strip()
    json_block = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if json_block:
        return json_block.group(1).strip()
    json_obj = re.search(r'(\{.*\}|\[.*\])', text, re.DOTALL)
    if json_obj:
        return json_obj.group(1).strip()
    return text

def split_title_author(user_text: str):
    """Matnni AI'siz "Nom. Muallif" ko‘rinishida ajratish (zaxira va tezkor yo‘l)."""
    text = (user_text or "").strip()
    if "." in text:
        title, author = text.split(".", 1)
        title, author = title.strip(), author.strip().rstrip(".")
        if title and author:
            return title, author
    return text, "Noma'lum muallif"


def looks_clean(user_text: str) -> bool:
    """Matn allaqachon toza "Nom. Muallif" ko‘rinishidami?

    Katalogdan yoki tavsiya ro‘yxatidan tanlangan kitoblar shunday keladi —
    ularni AI'ga yuborish bekorga pul sarflash va bekorga kutish demakdir.
    """
    text = (user_text or "").strip()
    if "." not in text or len(text) > 120:
        return False
    title, author = text.split(".", 1)
    title, author = title.strip(), author.strip().rstrip(".")
    if not title or not author:
        return False
    # Muallif qismi 1-4 so‘zdan iborat ism bo‘lishi kutiladi
    return 1 <= len(author.split()) <= 4


async def normalize_book_input(user_text: str):
    """Erkin yozilgan matndan kitob nomi va muallifini aniqlab, tozalash.

    Matn allaqachon toza bo‘lsa — AI umuman chaqirilmaydi.
    """
    if looks_clean(user_text):
        return split_title_author(user_text)

    prompt = f"""Foydalanuvchi quyidagi matnni kiritdi: "{user_text}".
Ushbu matndan kitob nomi va muallifini aniqlab ber.
Agar muallif yozilmagan bo‘lsa, ushbu mashhur bolalar asarining muallifini o‘zing to‘ldir. Agar asar muallifi noma'lum yoki topilmasa "Noma'lum muallif" deb yoz.

TALAB:
- Faqat va faqat to‘g‘ri O‘, o‘, G‘, g‘ harflaridan foydalan.
- Natijani FAQAT quyidagi JSON formatida ber:
{{"title": "Kitob nomi", "author": "Muallif ismi"}}"""

    try:
        response = await _ask("normalize_book_input", [prompt],
                              json_mode=True, max_tokens=120, fast=True)
        data = json.loads(clean_json(response.text))
        title = data.get("title", user_text).strip()
        author = data.get("author", "Noma'lum muallif").strip()
        return title, author
    except Exception:
        # AI ishlamasa — matnni o‘zimiz ajratamiz
        return split_title_author(user_text)

async def analyze_book_cover(image_bytes: bytes):
    """Kitob muqovasidan nomi va muallifini aniqlash"""
    prompt = (
        "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'. "
        "Barcha o‘zbekcha matnlarda faqat va faqat to‘g‘ri O‘, o‘, G‘, g‘ harflaridan foydalan."
    )
    try:
        response = await _ask("analyze_book_cover", [prompt, image_part(image_bytes)])
        return split_title_author(response.text.strip())
    except Exception as e:
        traceback.print_exc()
        raise e

async def verify_page_photo(image_bytes: bytes):
    """Bola o‘qigan kitob sahifasi va sahifa raqamini AI Vision orqali tekshirish.

    AYYORLIK: model sahifani baribir o‘qib chiqadi — eng qimmat qismi
    (rasmning o‘zi) allaqachon to‘langan. Shuning uchun undan sahifa
    MAZMUNINI ham so‘raymiz va saqlab qo‘yamiz. Bola kitob davomida
    3-4 marta sahifa rasmini yuborsa, shu yozuvlardan test o‘z-o‘zidan
    tuziladi — na bola, na ota-ona qo‘shimcha ish qiladi.
    Qo‘shimcha xarajat: javobga ~100 token (rasm qayta yuborilmaydi).
    """
    prompt = """Bu rasm foydalanuvchi yuborgan kitob sahifasi.
    1. Bu haqiqatan ham kitob sahifasimi? (true/false)
    2. Rasmda ko‘rinib turgan eng katta sahifa raqamini top. Agar sahifa raqami umuman ko‘rinmasa yoki noaniq bo‘lsa, 0 deb ber.
    3. Agar kitob sahifasi bo‘lsa, shu sahifada nima sodir bo‘layotganini 2-4 gapda yoz.
       ANIQ FAKTLARNI yoz: qahramonlar ismi, joy nomi, ular nima qildi, nima dedi,
       qanday narsalar tilga olindi. Bu keyinchalik savol tuzish uchun ishlatiladi,
       shuning uchun umumiy gaplar («qiziqarli voqea») emas, tafsilot kerak.
       Matn o‘qilmasa yoki sahifa bo‘sh bo‘lsa, "" (bo‘sh satr) ber.
    Javobingni FAQAT quyidagi JSON formatida ber:
    {"is_book_page": true, "page_number": 155, "note": "Hoshimjon bozorda cholni uchratdi va undan sehrli qovoq sotib oldi..."}"""

    try:
        response = await _ask("verify_page_photo", [prompt, image_part(image_bytes)],
                              json_mode=True, max_tokens=600, fast=True)
        data = json.loads(clean_json(response.text))

        is_page = bool(data.get("is_book_page", False))
        raw_page = data.get("page_number", 0)
        note = data.get("note") or ""
        if not isinstance(note, str):
            note = ""
        note = note.strip()[:900]

        if isinstance(raw_page, str):
            nums = re.findall(r'\d+', raw_page)
            page_number = int(nums[0]) if nums else 0
        elif isinstance(raw_page, (int, float)):
            page_number = int(raw_page)
        else:
            page_number = 0

        return {"is_book_page": is_page, "page_number": page_number, "note": note}
    except Exception as e:
        traceback.print_exc()
        raise e


async def generate_test_from_notes(title: str, author: str, notes: list, total_pages: int = 0):
    """O‘qish davomida yig‘ilgan sahifa yozuvlaridan test tuzish.

    Bu yerda RASM YUBORILMAYDI — faqat qisqa matnlar. Shuning uchun
    rasmlardan test tuzishga qaraganda ancha arzon va tez.
    `notes` — [(sahifa_raqami, matn), ...] ko‘rinishida.
    """
    parts = []
    for page, text in notes:
        parts.append("%s-sahifa: %s" % (page, text))
    body = "\n".join(parts)
    count = max(6, min(30, len(notes) * 3))
    # Kitob nechta betligi ma'lum bo‘lsa, AI savollarni kitob qismlariga
    # to‘g‘ri taqsimlay oladi. Bo‘lmasa — sahifa raqamiga qarab o‘zi bo‘ladi.
    if total_pages:
        part_hint = ("Kitob jami %d betdan iborat. 1-qism: 1-%d betlar, "
                     "2-qism: %d-%d betlar, 3-qism: %d-%d betlar."
                     % (total_pages, total_pages // 3,
                        total_pages // 3 + 1, total_pages * 2 // 3,
                        total_pages * 2 // 3 + 1, total_pages))
    else:
        part_hint = ("Kitob necha betligi noma'lum — savol qaysi sahifadan "
                     "olinganiga qarab qismni o‘zing belgila.")

    prompt = f"""Sen malakali bolalar pedagogi va adabiyotshunossan.
Quyida «{title}» kitobidan ({author or "muallif noma'lum"}) bola o‘qish
davomida qayd etilgan sahifalar mazmuni berilgan:

{body}

Shu mazmun asosida bolaning kitobni tushunganini tekshiradigan {count} ta
savol tuz. FAQAT yuqoridagi matnda bor narsalar haqida so‘ra — o‘zingdan
voqea yoki qahramon to‘qib chiqarma.

SAVOLLARNING PEDAGOGIK QATLAMLARI:
1. "factual" (Faktik xotira): qahramonlar, joy, tafsilotlar.
2. "logic" (Sabab-oqibat): nima uchun shunday bo‘ldi, qahramon nega shunday qildi.
3. "conclusion" (Xulosa): qahramon olgan saboq, voqeaning ma'nosi.

TALABLAR:
- Har bir savolda 3 yoki 4 ta variant bo‘lsin.
- Faqat to‘g‘ri o‘zbek lotin alifbosidagi O‘, o‘, G‘, g‘ belgilaridan foydalan.

KITOB QISMLARI: har bir savolga "part" maydonini qo‘y — savol kitobning
boshlanishiga tegishli bo‘lsa 1, o‘rtasiga 2, oxiriga 3.
{part_hint}

{MADANIY_MEZON}

Natijani FAQAT quyidagi JSON ro‘yxat formatida qaytar:
[
  {{"id": 1, "part": 1, "category": "factual", "question": "Savol matni?",
    "options": ["A) Variant 1", "B) Variant 2", "C) Variant 3"], "answer": "A) Variant 1"}}
]"""

    # Uch marta urinamiz: bu ish fon rejimida bajariladi, hech kim kutmaydi.
    response = await _ask("generate_test_from_notes", [prompt], json_mode=True, attempts=3)
    raw_json = clean_json(response.text)
    questions = json.loads(raw_json)
    return questions, raw_json


async def summarize_book_from_notes(title: str, author: str, notes: list):
    """O‘qish davomida yig‘ilgan sahifa yozuvlaridan kitob mazmunini tuzadi.

    Rasm yuborilmaydi — faqat qisqa matnlar, ya'ni juda arzon. Natija
    umumiy kitob bazasiga tushadi va boshqa oilalarga tayyor holda beriladi.
    """
    body = "\n".join("%s-sahifa: %s" % (page, text) for page, text in notes)
    prompt = f"""Sen bolalar adabiyoti bo‘yicha mutaxassissan. Quyida
«{title}» kitobidan ({author or "muallif noma'lum"}) o‘qish davomida qayd
etilgan sahifalar mazmuni berilgan:

{body}

Shu yozuvlar asosida kitob haqida qisqa ma'lumot tuz. FAQAT yuqoridagi
matnda bor narsalarga tayan — o‘zingdan voqea yoki qahramon to‘qima.
Yozuvlar kitobning hammasini qamramagan bo‘lishi mumkin; bunda bor
qismini tasvirla, yetishmagan joyni to‘qib to‘ldirma.

Faqat to‘g‘ri o‘zbek lotin alifbosidagi O‘, o‘, G‘, g‘ belgilaridan foydalan.

{MADANIY_MEZON}

Natijani FAQAT quyidagi JSON formatida qaytar:
{{
  "summary": "Kitobning qisqacha mazmuni — 5-8 jumla.",
  "characters": "Asosiy qahramonlar va ular kim ekani.",
  "theme": "Asarning g‘oyasi va bola oladigan saboq.",
  "age_hint": "8-12"
}}"""
    response = await _ask("summarize_book", [prompt], json_mode=True, attempts=2)
    return json.loads(clean_json(response.text))


async def generate_talk_question(title: str, author: str, base: dict, stage: str, age: int = 10):
    """«AI ustoz savoli» — bola ovozda javob beradigan ochiq savol.

    Faktik emas: «nechta ukasi bor edi?» kabi xotira savoli EMAS. Bolaning
    o‘qiganini o‘z so‘zi bilan gapira olishini, tushunganini va munosabatini
    ochadigan savol bo‘lishi kerak.

    `stage`: 'start' — kitobning boshlanish qismi haqida;
             'end'   — butun kitob va undan olingan saboq haqida.
    """
    if stage == "start":
        qism = ("Bola kitobning BOSHLANISH qismini o‘qib bo‘ldi (taxminan "
                "uchdan birini). Savol faqat SHU qismga tegishli bo‘lsin — "
                "kitobning oxiri haqida so‘rama, u hali o‘qimagan.")
    else:
        qism = ("Bola kitobni OXIRIGACHA o‘qib bo‘ldi. Savol butun asarga, "
                "undagi o‘zgarishga va bola olgan saboqqa tegishli bo‘lsin.")

    prompt = f"""Sen mehribon «AI ustoz»san. {age} yoshli bolaga «{title}»
kitobi ({author or "muallif noma'lum"}) bo‘yicha OG‘ZAKI javob beriladigan
BITTA savol tuz.

Kitob haqida bilganlaring:
Mazmuni: {base.get("summary", "")}
Qahramonlar: {base.get("characters", "")}
G‘oyasi: {base.get("theme", "")}

{qism}

SAVOL QANDAY BO‘LISHI KERAK:
- Faktik BO‘LMASIN. «Qahramonning ismi nima edi?», «Nechta edi?» kabi
  bir so‘z bilan javob beriladigan savollar TAQIQLANADI.
- Bola kamida 30-60 soniya gapira oladigan, o‘z fikrini aytishga
  undaydigan ochiq savol bo‘lsin.
- Javobidan bolaning kitobni haqiqatan o‘qigani va tushungani bilinsin —
  ya'ni kitobni o‘qimagan bola bunga javob bera olmasin.
- Bolaning o‘z munosabati, o‘rniga qo‘yib ko‘rishi so‘ralsin.
- Til sodda, iliq va do‘stona bo‘lsin; savol bitta jumla, ko‘pi bilan ikkita.
- Faqat to‘g‘ri o‘zbek lotin alifbosidagi O‘, o‘, G‘, g‘ belgilaridan foydalan.

{MADANIY_MEZON}

Natijani FAQAT quyidagi JSON formatida qaytar:
{{"question": "Savol matni?"}}"""

    response = await _ask("generate_talk_question", [prompt], json_mode=True, attempts=2)
    data = json.loads(clean_json(response.text))
    return (data.get("question") or "").strip()


async def generate_test_bank_from_photos(photos_bytes_list: list):
    """Sahifa rasmlaridan: savollar banki + kitobning qisqacha mazmuni.

    AI bu rasmlarni baribir o‘qiydi — shuning uchun O‘SHA chaqiruvning
    o‘zida kitob haqidagi ma'lumotni ham so‘raymiz. Qo‘shimcha xarajat
    deyarli yo‘q, lekin ilova o‘z kitob bazasini yig‘ib boradi.

    Qaytaradi: (savollar, savollar_json, kitob_haqida)
    """
    prompt = f"""Sen malakali bolalar pedagogi va adabiyotshunossan. Quyida bolalar kitobining {len(photos_bytes_list)} ta sahifasi rasmlari berilgan.
    Ushbu matnlar asosida bolaning kitobni chuqur tushunishini baholovchi 30 ta sifatli mantiqiy savollar bankini tuz.

    SAVOLLARNING PEDAGOGIK QATLAMLARI:
    1. "factual" (Faktik xotira - 30%): Qahramonlar, makon, vaqt va muhim syujet tafsilotlari.
    2. "logic" (Sabab-oqibat mantiqi - 40%): Voqealar sababi, qahramonning niyati va harakatlar oqibati.
    3. "conclusion" (Asar mohiyati va xulosa - 30%): Muallif g‘oyasi, qahramon olgan saboq va asar xulosasi.

    KITOB QISMLARI — JUDA MUHIM:
    Kitobni uchga bo‘l va har bir savolga "part" maydonini qo‘y:
      "part": 1 — kitobning BOSHLANISHI (birinchi uchdan bir qismi)
      "part": 2 — kitobning O‘RTASI
      "part": 3 — kitobning OXIRI
    Har bir qism uchun 10 tadan savol bo‘lsin va savollar shu tartibda,
    kitob voqealari ketma-ketligida joylashsin. Bu shart uchun sabab:
    kitobning yarmini o‘qigan bolaga oxiri haqida savol berilmasligi kerak.

    TALABLAR:
    - Har bir savolda 3 ta yoki 4 ta variant (A, B, C, D) bo‘lsin.
    - Faqat va faqat to‘g‘ri o‘zbek lotin alifbosidagi O‘, o‘, G‘, g‘ belgilaridan foydalan.
    - Savollar bolaning yoshiga mos, qiziqarli va tushunarli bo‘lsin.

    {MADANIY_MEZON}

    Natijani FAQAT VA FAQAT quyidagi JSON obyekt formatida qaytar:
    {{
      "kitob": {{
        "summary": "Kitobning qisqacha mazmuni — 5-8 jumla, voqealar ketma-ketligi bilan.",
        "characters": "Asosiy qahramonlar va ular kim ekani.",
        "theme": "Asarning g‘oyasi va bola oladigan saboq.",
        "age_hint": "8-12"
      }},
      "savollar": [
        {{
          "id": 1,
          "part": 1,
          "category": "factual",
          "question": "Savol matni?",
          "options": ["A) Variant 1", "B) Variant 2", "C) Variant 3"],
          "answer": "A) Variant 1"
        }}
      ]
    }}"""

    contents = [prompt]
    for img_bytes in photos_bytes_list:
        contents.append(image_part(img_bytes))

    try:
        # Fon rejimida bajariladi — qayta urinish foydalanuvchini kuttirmaydi.
        response = await _ask("generate_test_bank", contents, json_mode=True, attempts=3)
        parsed = json.loads(clean_json(response.text))
        # AI ba'zan eski ko‘nikma bo‘yicha to‘g‘ridan-to‘g‘ri ro‘yxat qaytaradi —
        # ikkala shaklni ham qabul qilamiz, aks holda ish behuda ketardi.
        if isinstance(parsed, list):
            questions, info = parsed, {}
        else:
            questions = parsed.get("savollar") or parsed.get("questions") or []
            info = parsed.get("kitob") or parsed.get("book") or {}
        raw_json = json.dumps(questions, ensure_ascii=False)
        return questions, raw_json, info
    except Exception as e:
        traceback.print_exc()
        raise e

async def evaluate_voice_summary(audio_bytes: bytes, age: int, book_title: str,
                                 question: str = ""):
    """Bolaning ovozli xulosasini tahlil qilish va ota-onaga pedagogik hisobot berish.

    `question` berilgan bo‘lsa — bu erkin xulosa emas, AI ustoz bergan aniq
    savolga javob. Bunda javobning savolga mos kelishi ham baholanadi.
    """
    if question:
        savol_bloki = f"""
    MUHIM: bu erkin xulosa EMAS. Bolaga quyidagi savol berilgan:
    «{question}»

    Shuning uchun avvalo javobning SHU SAVOLGA mos kelishini baho:
    - Bola savolga javob berdimi yoki chetlab o‘tdimi?
    - Javobidan kitobni haqiqatan o‘qigani bilinadimi?
    Savolga umuman aloqasiz javob bo‘lsa, baholarni past qo‘y.
"""
    else:
        savol_bloki = ""

    prompt = f"""Sen mehribon va talabchan pedagog hamda bolalarning qadrdoni bo‘lgan «AI ustoz»san. Bu {age} yoshli bolaning '{book_title}' kitobi bo‘yicha yuborgan audio xulosasi.
{savol_bloki}
    Audioni 4 ta nutqiy mezon bo‘yicha sinchiklab tahlil qil:
    1. Leksik boylik (yangi so‘zlardan foydalanishi, yoshiga mos lug‘at zaxirasi).
    2. Nutq ravonligi (to‘xtashlarsiz, ifodali va silliq gapirishi).
    3. Syujet izchilligi (fikrni chalkashtirmay, voqealar ketma-ketligini bayon qilishi).
    4. Shaxsiy munosabat (o‘z his-tuyg‘ulari va mustaqil xulosalarini qo‘shishi).

    {MADANIY_MEZON}

    Natijani FAQAT quyidagi JSON formatida qaytar:
    {{
        "bonus_bilig": 4,
        "give_badge": false,
        "badge_ezgulik": false,
        "child_feedback": "Bola uchun AI ustoz nomidan samimiy, rag‘batlantiruvchi va o‘sishga undovchi xabar...",
        "parent_report": {{
            "summary": "Audioning qisqacha mazmuni...",
            "strengths": "✅ Qahramon asar voqealarini juda chiroyli va o‘z his-tuyg‘ularini qo‘shib gapirib berdi...",
            "weaknesses": "🌱 Ayrim o‘rinlarda qahramonning nima uchun bunday qarorga kelganini tushuntirishda biroz to‘xtaldi...",
            "conversation_topic": "☕️ Kechki suhbat uchun savol: 'Hoshimjon sehrli qalpoqchani topganda qanday hisda edi? Odam mehnat qilmasa nima bo‘ladi?'"
        }},
        "diagnostic_scores": {{
            "factual_score": 85,
            "logic_score": 75,
            "conclusion_score": 80,
            "fluency_score": 85,
            "vocabulary_score": 80
        }}
    }}

    BAHOLASH QOIDALARI:
    1. "bonus_bilig": 1 dan 5 gacha butun son. Nutqi ravon, teran va mazmunli bo‘lsa 4 yoki 5 Bilig ber. Agar fikri sayoz yoki tutilgan bo‘lsa 1, 2 yoki 3 Bilig ber.
    2. "give_badge": agar o‘z yoshiga nisbatan ajoyib notiqlik ko‘rsatgan bo‘lsa true.
    3. "badge_ezgulik": agar bola qahramonning ezgu fazilatlari (mehr, halollik, do‘stlik, mardlik) haqida chiroyli va samimiy xulosa aytgan bo‘lsa true.
    4. Matnda qat'iy ravishda faqat O‘, o‘, G‘, g‘ belgilaridan foydalan."""

    try:
        response = await _ask("evaluate_voice_summary", [
            prompt,
            audio_part(audio_bytes)
        ], json_mode=True)
        return json.loads(clean_json(response.text))
    except Exception as e:
        traceback.print_exc()
        raise e
