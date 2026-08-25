import json
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(GEMINI_MODEL)

def clean_json(text: str) -> str:
    """Gemini qaytargan matndan JSON blokini xavfsiz ajratib olish"""
    text = text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()

async def analyze_book_cover(image_bytes: bytes):
    """Kitob muqovasidan nomi va muallifini aniqlash"""
    prompt = (
        "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'. "
        "Barcha o‘zbekcha matnlarda faqat va faqat to‘g‘ri O‘, o‘, G‘, g‘ harflaridan foydalan."
    )
    response = await model.generate_content_async([
        prompt,
        {"mime_type": "image/jpeg", "data": image_bytes}
    ])
    ai_result = response.text.strip()
    if "." in ai_result:
        title, author = ai_result.split(".", 1)
    else:
        title, author = ai_result, "Noma'lum muallif"
    return title.strip(), author.strip()

async def verify_page_photo(image_bytes: bytes):
    """Bola o'qigan kitob sahifasi va sahifa raqamini AI Vision orqali tekshirish"""
    prompt = """Bu rasm foydalanuvchi yuborgan kitob sahifasi.
    1. Bu haqiqatan ham kitob sahifasimi? (true/false)
    2. Rasmda ko‘rinib turgan eng katta sahifa raqamini top. Agar sahifa raqami umuman ko‘rinmasa yoki noaniq bo‘lsa, 0 deb ber.
    Javobingni FAQAT quyidagi JSON formatida ber: {"is_book_page": true, "page_number": 155}"""
    
    response = await model.generate_content_async([
        prompt,
        {"mime_type": "image/jpeg", "data": image_bytes}
    ])
    return json.loads(clean_json(response.text))

async def generate_test_bank_from_photos(photos_bytes_list: list):
    """Yuklangan 5–10 ta sahifa rasmi asosida 15–20 talik kengaytirilgan Savollar bankini tuzish"""
    prompt = f"""Sen malakali bolalar pedagogi va adabiyotshunossan. Quyida bolalar kitobining {len(photos_bytes_list)} ta sahifasi rasmlari berilgan.
    Ushbu matnlar asosida bolaning kitobni chuqur tushunishini baholovchi 15 tadan 20 tagacha sifatli mantiqiy savollar bankini tuz.

    SAVOLLARNING PEDAGOGIK QATLAMLARI:
    1. "factual" (Faktik xotira - 30%): Qahramonlar, makon, vaqt va muhim syujet tafsilotlari.
    2. "logic" (Sabab-oqibat mantiqi - 40%): Voqealar sababi, qahramonning niyati va harakatlar oqibati.
    3. "conclusion" (Asar mohiyati va xulosa - 30%): Muallif g‘oyasi, qahramon olgan saboq va asar xulosasi.

    TALABLAR:
    - Har bir savolda 3 ta yoki 4 ta variant (A, B, C, D) bo‘lsin.
    - Faqat va faqat to‘g‘ri o‘zbek lotin alifbosidagi O‘, o‘, G‘, g‘ belgilaridan foydalan (oddiy ' yoki ` qat'iyan taqiqlanadi).
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
        contents.append({"mime_type": "image/jpeg", "data": img_bytes})

    response = await model.generate_content_async(contents)
    raw_json = clean_json(response.text)
    questions = json.loads(raw_json)
    return questions, raw_json

# Eski funksiya bilan moslikni saqlash uchun
async def generate_test_from_photos(photos_bytes_list: list):
    return await generate_test_bank_from_photos(photos_bytes_list)

async def evaluate_voice_summary(audio_bytes: bytes, age: int, book_title: str):
    """Bolaning ovozli xulosasini 4 ta nutqiy mezon bo'yicha tahlil qilish va ota-onaga suhbat mavzusi berish"""
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
    2. "give_badge": agar o‘z yoshiga nisbatan ajoyib notiqlik ko‘rsatgan bo‘lsa true (Notiq nishoni uchun).
    3. Matnda qat'iy ravishda faqat O‘, o‘, G‘, g‘ belgilaridan foydalan."""

    response = await model.generate_content_async([
        prompt,
        {"mime_type": "audio/ogg", "data": audio_bytes}
    ])
    return json.loads(clean_json(response.text))
