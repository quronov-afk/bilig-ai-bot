import json
import google.generativeai as genai
from config import GEMINI_API_KEY, GEMINI_MODEL

if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel(GEMINI_MODEL)

def clean_json(text):
    text = text.strip()
    if text.startswith("```json"): text = text[7:]
    elif text.startswith("```"): text = text[3:]
    if text.endswith("```"): text = text[:-3]
    return text.strip()

async def analyze_book_cover(image_bytes):
    prompt = (
        "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'. "
        "Matnda faqat to‘g‘ri o‘zbek lotin harflaridan (O‘, o‘, G‘, g‘) foydalan."
    )
    response = await model.generate_content_async([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
    ai_result = response.text.strip()
    title, author = ai_result.split(".", 1) if "." in ai_result else (ai_result, "Noma'lum muallif")
    return title.strip(), author.strip()

async def verify_page_photo(image_bytes):
    prompt = """Bu rasm foydalanuvchi yuborgan kitob sahifasi.
    1. Bu haqiqatan ham kitob sahifasimi? (true/false)
    2. Rasmda ko'rinib turgan eng katta sahifa raqamini top. Agar sahifa raqami umuman ko'rinmasa, 0 deb ber.
    Javobingni FAQAT JSON formatida ber: {"is_book_page": true, "page_number": 155}"""
    response = await model.generate_content_async([prompt, {"mime_type": "image/jpeg", "data": image_bytes}])
    return json.loads(clean_json(response.text))

async def generate_test_from_photos(photos_bytes_list):
    prompt = f"""Bu bolalar kitobining {len(photos_bytes_list)} ta sahifasi rasmlari. Shu matnlar va sahifalar mazmuni asosida bolalar uchun 5 ta sifatli test savoli tuz. 
    DIQQAT: 
    1. Savollar faqat quruq xotirani emas, balki bolaning fikrlashini, mantiqini va asar mohiyatini tushunganini sinaydigan bo‘lsin.
    2. Har bir savolda 3 ta variant (A, B, C) bo‘lsin.
    3. Barcha o‘zbekcha matnlarda qat'iy ravishda O‘, o‘, G‘, g‘ belgilaridan foydalan (apostrof yoki qiya belgilar taqiqlanadi).
    Natijani FAQAT VA FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday so‘z qo‘shma:
    [ {{"question": "Savol matni?", "options": ["A) variant", "B) variant", "C) variant"], "answer": "A) variant"}} ]"""
    
    contents = [prompt]
    for img_bytes in photos_bytes_list:
        contents.append({"mime_type": "image/jpeg", "data": img_bytes})
        
    response = await model.generate_content_async(contents)
    raw_json = clean_json(response.text)
    questions = json.loads(raw_json)
    return questions, raw_json

async def evaluate_voice_summary(audio_bytes, age, book_title):
    prompt = f"""Sen mehribon va talabchan pedagog hamda bolalarning qadrdoni bo‘lgan «AI ustoz»san. Bu {age} yoshli bolaning '{book_title}' kitobi bo‘yicha yuborgan audio xulosasi.

    Tahlilni ikkita alohida qismga bo‘lib, FAQAT quyidagi JSON formatida qaytar:

    {{
        "bonus_bilig": 3,
        "give_badge": false,
        "child_feedback": "Bola uchun sodda va rag‘batlantiruvchi xabar matni...",
        "parent_report": {{
            "summary": "Audioning qisqacha mazmuni...",
            "focused_points": "Bola e'tibor qaratgan asosiy voqealar...",
            "strengths": "Bolaning yutuqlari (ravon nutq, so‘z boyligi, his-tuyg‘ular, mantiq)...",
            "weaknesses": "Kamchiliklari va rivojlantirish kerak bo‘lgan jihatlari..."
        }}
    }}

    BAHOLASH VA PEDAGOGIK MEZONLAR:
    1. "bonus_bilig": 1 dan 5 gacha butun raqam. Agar bola nutqi ravon, fikrlari teran va asar mohiyatini anglagan bo‘lsa — 4 yoki 5 Bilig ber. Agar fikri sayoz, shunchaki o‘qib bergan yoki tutilib qolgan bo‘lsa — 1, 2 yoki 3 Bilig ber.
    2. "child_feedback": AI ustoz nomidan bolaga yoziladigan xabar. Samimiy, bolaning yoshiga mos bo‘lsin. Agar kam Bilig berilsa, sababini chiroyli tushuntir va nutqini qanday yaxshilash bo‘yicha maslahat ber.
    3. "parent_report": Ota-onaga yuboriladigan haqqoniy va xolis pedagogik xulosa.
    4. "give_badge": boolean (o‘z yoshiga nisbatan ajoyib notiqlik ko‘rsatsa true).
    5. DIQQAT: Barcha matnlarda O‘, o‘, G‘, g‘ belgilaridan to‘g‘ri foydalan."""
    
    response = await model.generate_content_async([prompt, {"mime_type": "audio/ogg", "data": audio_bytes}])
    return json.loads(clean_json(response.text))
