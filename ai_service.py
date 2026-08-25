import json
import re
import asyncio
import traceback
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL

client = None
if GEMINI_API_KEY:
    client = genai.Client(api_key=GEMINI_API_KEY)

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

async def normalize_book_input(user_text: str):
    """Erkin yozilgan matndan kitob nomi va muallifini Gemini orqali aniqlab, tozalash"""
    prompt = f"""Foydalanuvchi quyidagi matnni kiritdi: "{user_text}".
Ushbu matndan kitob nomi va muallifini aniqlab ber.
Agar muallif yozilmagan bo‘lsa, ushbu mashhur bolalar asarining muallifini o‘zing to‘ldir. Agar asar muallifi noma'lum yoki topilmasa "Noma'lum muallif" deb yoz.

TALAB:
- Faqat va faqat to‘g‘ri O‘, o‘, G‘, g‘ harflaridan foydalan.
- Natijani FAQAT quyidagi JSON formatida ber:
{{"title": "Kitob nomi", "author": "Muallif ismi"}}"""

    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[prompt]
            )
            data = json.loads(clean_json(response.text))
            title = data.get("title", user_text).strip()
            author = data.get("author", "Noma'lum muallif").strip()
            return title, author
        except Exception as e:
            if attempt == 1:
                # Fallback agar AI ishlamasa
                if "." in user_text:
                    parts = user_text.split(".", 1)
                    return parts[0].strip(), parts[1].strip()
                return user_text.strip(), "Noma'lum muallif"
            await asyncio.sleep(1)

async def analyze_book_cover(image_bytes: bytes):
    """Kitob muqovasidan nomi va muallifini aniqlash"""
    prompt = (
        "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'. "
        "Barcha o‘zbekcha matnlarda faqat va faqat to‘g‘ri O‘, o‘, G‘, g‘ harflaridan foydalan."
    )
    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                ]
            )
            ai_result = response.text.strip()
            if "." in ai_result:
                title, author = ai_result.split(".", 1)
            else:
                title, author = ai_result, "Noma'lum muallif"
            return title.strip(), author.strip()
        except Exception as e:
            print(f"XATOLIK [analyze_book_cover - Urinish {attempt + 1}]: {e}")
            if attempt == 1:
                traceback.print_exc()
                raise e
            await asyncio.sleep(1)

async def verify_page_photo(image_bytes: bytes):
    """Bola o‘qigan kitob sahifasi va sahifa raqamini AI Vision orqali tekshirish"""
    prompt = """Bu rasm foydalanuvchi yuborgan kitob sahifasi.
    1. Bu haqiqatan ham kitob sahifasimi? (true/false)
    2. Rasmda ko‘rinib turgan eng katta sahifa raqamini top. Agar sahifa raqami umuman ko‘rinmasa yoki noaniq bo‘lsa, 0 deb ber.
    Javobingni FAQAT quyidagi JSON formatida ber: {"is_book_page": true, "page_number": 155}"""
    
    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg")
                ]
            )
            raw_text = clean_json(response.text)
            data = json.loads(raw_text)
            
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
            print(f"XATOLIK [verify_page_photo - Urinish {attempt + 1}]: {e}")
            if attempt == 1:
                traceback.print_exc()
                raise e
            await asyncio.sleep(1)

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
        contents.append(types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"))

    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=contents
            )
            raw_json = clean_json(response.text)
            questions = json.loads(raw_json)
            return questions, raw_json
        except Exception as e:
            print(f"XATOLIK [generate_test_bank_from_photos - Urinish {attempt + 1}]: {e}")
            if attempt == 1:
                traceback.print_exc()
                raise e
            await asyncio.sleep(1)

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
    3. Matnda qat'iy ravishda faqat O‘, o‘, G‘, g‘ belgilaridan foydalan."""

    for attempt in range(2):
        try:
            response = await client.aio.models.generate_content(
                model=GEMINI_MODEL,
                contents=[
                    prompt,
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/ogg")
                ]
            )
            return json.loads(clean_json(response.text))
        except Exception as e:
            print(f"XATOLIK [evaluate_voice_summary - Urinish {attempt + 1}]: {e}")
            if attempt == 1:
                traceback.print_exc()
                raise e
            await asyncio.sleep(1)
