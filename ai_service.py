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


class AiEmptyResponse(RuntimeError):
    """AI javob berdi, lekin matn bo‘sh — sababi xabar matnida."""


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
    print("[ai] BO‘SH JAVOB [%s] finish_reason=%r block_reason=%r" % (task, reason, blocked))
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


async def _ask(task: str, contents, json_mode=False, max_tokens=None, fast=False, attempts=2):
    """Barcha Gemini chaqiruvlari shu yagona joydan o‘tadi.

    fast=True     — sodda vazifa (bet raqamini o‘qish kabi): model ortiqcha
                    "o‘ylamaydi", ya'ni ortiqcha token sarflanmaydi.
    json_mode     — javob rasman JSON formatida so‘raladi. Shunda format
                    buzilib, ikkinchi marta to‘lash holati deyarli yo‘qoladi.
    max_tokens    — javob uzunligi chegarasi (faqat fast rejimda xavfsiz).
    """
    global _thinking_off_supported
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
                print(f"[ai] tejash rejimi bu modelga to‘g‘ri kelmadi, oddiy rejimga o‘tildi ({task}): {e}")
                tries -= 1
                continue
            print(f"XATOLIK [{task} - Urinish {tries}]: {e}")
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
    """Bola o‘qigan kitob sahifasi va sahifa raqamini AI Vision orqali tekshirish"""
    prompt = """Bu rasm foydalanuvchi yuborgan kitob sahifasi.
    1. Bu haqiqatan ham kitob sahifasimi? (true/false)
    2. Rasmda ko‘rinib turgan eng katta sahifa raqamini top. Agar sahifa raqami umuman ko‘rinmasa yoki noaniq bo‘lsa, 0 deb ber.
    Javobingni FAQAT quyidagi JSON formatida ber: {"is_book_page": true, "page_number": 155}"""
    
    try:
        response = await _ask("verify_page_photo", [prompt, image_part(image_bytes)],
                              json_mode=True, max_tokens=200, fast=True)
        data = json.loads(clean_json(response.text))

        is_page = bool(data.get("is_book_page", False))
        raw_page = data.get("page_number", 0)

        if isinstance(raw_page, str):
            nums = re.findall(r'\d+', raw_page)
            page_number = int(nums[0]) if nums else 0
        elif isinstance(raw_page, (int, float)):
            page_number = int(raw_page)
        else:
            page_number = 0

        return {"is_book_page": is_page, "page_number": page_number}
    except Exception as e:
        traceback.print_exc()
        raise e

async def generate_test_bank_from_photos(photos_bytes_list: list):
    """Yuklangan sahifa rasmlari asosida kengaytirilgan Savollar bankini tuzish"""
    prompt = f"""Sen malakali bolalar pedagogi va adabiyotshunossan. Quyida bolalar kitobining {len(photos_bytes_list)} ta sahifasi rasmlari berilgan.
    Ushbu matnlar asosida bolaning kitobni chuqur tushunishini baholovchi 15 tadan 20 tagacha sifatli mantiqiy savollar bankini tuz.

    SAVOLLARNING PEDAGOGIK QATLAMLARI:
    1. "factual" (Faktik xotira - 30%): Qahramonlar, makon, vaqt va muhim syujet tafsilotlari.
    2. "logic" (Sabab-oqibat mantiqi - 40%): Voqealar sababi, qahramonning niyati va harakatlar oqibati.
    3. "conclusion" (Asar mohiyati va xulosa - 30%): Muallif g‘oyasi, qahramon olgan saboq va asar xulosasi.

    TALABLAR:
    - Har bir savolda 3 ta yoki 4 ta variant (A, B, C, D) bo‘lsin.
    - Faqat va faqat to‘g‘ri o‘zbek lotin alifbosidagi O‘, o‘, G‘, g‘ belgilaridan foydalan.
    - Savollar bolaning yoshiga mos, qiziqarli va tushunarli bo‘lsin.

    Natijani FAQAT VA FAQAT quyidagi JSON ro‘yxat formatida qaytar:
    [
      {{
        "id": 1,
        "category": "factual",
        "question": "Savol matni?",
        "options": ["A) Variant 1", "B) Variant 2", "C) Variant 3"],
        "answer": "A) Variant 1"
      }}
    ]"""

    contents = [prompt]
    for img_bytes in photos_bytes_list:
        contents.append(image_part(img_bytes))

    try:
        response = await _ask("generate_test_bank", contents, json_mode=True)
        raw_json = clean_json(response.text)
        questions = json.loads(raw_json)
        return questions, raw_json
    except Exception as e:
        traceback.print_exc()
        raise e

async def evaluate_voice_summary(audio_bytes: bytes, age: int, book_title: str):
    """Bolaning ovozli xulosasini tahlil qilish va ota-onaga pedagogik hisobot berish"""
    prompt = f"""Sen mehribon va talabchan pedagog hamda bolalarning qadrdoni bo‘lgan «AI ustoz»san. Bu {age} yoshli bolaning '{book_title}' kitobi bo‘yicha yuborgan audio xulosasi.

    Audioni 4 ta nutqiy mezon bo‘yicha sinchiklab tahlil qil:
    1. Leksik boylik (yangi so‘zlardan foydalanishi, yoshiga mos lug‘at zaxirasi).
    2. Nutq ravonligi (to‘xtashlarsiz, ifodali va silliq gapirishi).
    3. Syujet izchilligi (fikrni chalkashtirmay, voqealar ketma-ketligini bayon qilishi).
    4. Shaxsiy munosabat (o‘z his-tuyg‘ulari va mustaqil xulosalarini qo‘shishi).

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
            types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
        ], json_mode=True)
        return json.loads(clean_json(response.text))
    except Exception as e:
        traceback.print_exc()
        raise e
