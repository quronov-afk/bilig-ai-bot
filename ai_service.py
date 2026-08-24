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
    prompt = "Bu kitob muqovasining rasmi. Menga faqat kitobning nomi va muallifini quyidagi formatda yozib ber: 'Kitob nomi. Muallif'."
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
    DIQQAT: Savollar faqat quruq xotirani emas, balki bolaning fikrlashini, mantiqini va asar mohiyatini tushunganini sinaydigan bo'lsin.
    Har bir savolda 3 ta variant (A, B, C) bo'lsin. 
    Natijani FAQAT VA FAQAT quyidagi JSON formatida qaytar, boshqa hech qanday so'z qo'shma:
    [ {{"question": "Savol matni?", "options": ["A) variant", "B) variant", "C) variant"], "answer": "A) variant"}} ]"""
    
    contents = [prompt]
    for img_bytes in photos_bytes_list:
        contents.append({"mime_type": "image/jpeg", "data": img_bytes})
        
    response = await model.generate_content_async(contents)
    raw_json = clean_json(response.text)
    questions = json.loads(raw_json)
    return questions, raw_json

async def evaluate_voice_summary(audio_bytes, age, book_title):
    prompt = f"""Sen mehribon va talabchan Adabiyotshunos hamda maktab o'qituvchisisan. Bu {age} yoshli bolaning '{book_title}' kitobi bo'yicha yuborgan audio xulosasi.

    Tahlilni ikkita alohida qismga bo'lib, FAQAT quyidagi JSON formatida qaytar:

    {{
        "bonus_bilig": 3,
        "give_badge": false,
        "child_feedback": "Bola uchun sodda xabar matni...",
        "parent_report": {{
            "summary": "Audioning qisqacha matni va mazmuni...",
            "focused_points": "Bola e'tibor qaratgan asosiy masalalar va voqealar...",
            "strengths": "Bolaning yutuqlari (so'z boyligi, his-tuyg'ular, mantiq)...",
            "weaknesses": "Kamchiliklari va rivojlantirish kerak bo'lgan jihatlari..."
        }}
    }}

    TALABLAR:
    1. "bonus_bilig": 1 dan 5 gacha butun raqam (sifatiga qarab).
    2. "child_feedback": Bolaga yuboriladigan matn. Bolaga mos sodda tilda yoz. Agar Bilig kam (1, 2, 3) berilgan bo'lsa, xafa qilmasdan sababini tushuntir. Nutq so'zlash texnikasini o'rgat.
    3. "parent_report": Otaga yuboriladigan HAQQONIY va OBYEKTIV pedagogik tahlil. Audiodagi kamchiliklar va yutuqlarni ro'y-rost ko'rsat.
    4. "give_badge": boolean (juda ajoyib nutq bo'lsa true)."""
    
    response = await model.generate_content_async([prompt, {"mime_type": "audio/ogg", "data": audio_bytes}])
    return json.loads(clean_json(response.text))
