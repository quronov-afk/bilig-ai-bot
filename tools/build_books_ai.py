#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Kitob pasporti va 30 ta testni Gemini orqali tayyorlash.

Ilovaning O‘Z Gemini sozlamasidan foydalanadi (yangi kalit kerak emas —
`.env` faylidagi GEMINI_API_KEY olinadi).

Xususiyatlari:
  · Har kitob tugagan zahoti faylga yoziladi — uzilsa, o‘sha joydan davom etadi
  · Natija darrov tekshiriladi (check_book.py), o‘tmasa AI'ga xatolar
    aytilib, qayta yozdiriladi (2 marta urinadi)
  · Sarflangan pul hisoblanib, ekranda ko‘rsatib boriladi

Ishlatish:
    python3 tools/build_books_ai.py --kun 1 --limit 5    # sinov
    python3 tools/build_books_ai.py --kun 1              # 1-kunning hammasi
    python3 tools/build_books_ai.py --kun 1 --narx       # faqat narxni chamalash
    python3 tools/build_books_ai.py --hammasi            # qolgan hamma kitob
"""

import asyncio
import json
import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

WORK = os.path.join(ROOT, "tools", "book_work")
OUT = os.path.join(ROOT, "tools", "book_out")
INDEX = os.path.join(WORK, "index.json")
LOG = os.path.join(OUT, "_log.txt")

# gemini-3.6-flash tarifi, $ / 1 mln token (2026-yil, 31-dekabrgacha)
PRICE_IN, PRICE_OUT = 0.75, 3.75


def load_env():
    """`.env` faylidagi sozlamalarni muhitga qo‘yadi (kutubxonasiz)."""
    path = os.path.join(ROOT, ".env")
    if not os.path.exists(path):
        return False
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            os.environ.setdefault(key.strip(), val.strip().strip("'\""))
    return True


load_env()
import ai_service                                    # noqa: E402
from tools.check_book import check, profile_for, PROFILES   # noqa: E402


MADANIY_MEZON = """MADANIY MEZON — MAJBURIY, HAMMA JAVOBGA TAALLUQLI:
Bu ilova O‘zbekistondagi oilalar uchun. Mazmun, savol va baholarni musulmon
Sharqi an'analari, madaniyati va mentaliteti doirasida yoz:

· Ota-ona va kattalarga hurmat, ularning maslahatiga quloq solish — eng
  yuqori qadriyat. Qahramonning kattalarga qarshi chiqishi «jasorat» deb
  maqtalmasin; asarda shunday holat bo‘lsa, uning OQIBATI muhokama qilinsin.
· Halollik, sabr, shukr, hayo, kamtarlik, mehmondo‘stlik, saxovat,
  qo‘shniga va yetimga g‘amxo‘rlik, mehnatsevarlik, va'daga vafo —
  ijobiy o‘lchov shular.
· Oila va qarindoshlik rishtalari, kattalar bilan birga yashash, opa-uka
  inoqligi — tabiiy va qadrli holat sifatida ko‘rsatilsin.
· Ustoz-shogird munosabati va ilm olishning qadri alohida e'zozlansin.
· Chet el asarlarida mahalliy madaniyatga yot lavhalar (ichkilik, qiz-yigit
  munosabatlari, e'tiqodni masxaralash) uchrasa — ularga savol tuzilmasin
  va qisqacha mazmunda ularga urg‘u berilmasin. Asarning umuminsoniy
  saboqlariga (do‘stlik, mardlik, halollik, mehr) e'tibor qaratilsin.
· Bolaga o‘rnak bo‘ladigan xulq ko‘rsatilsin: salomlashish, kattaga joy
  berish, ota-onaning roziligini olish, mehmonni kutish kabi.

DIQQAT: asarda YO‘Q narsani qo‘shma va matnga sun'iy diniy tus BERMA.
Vazifa — bor matnni shu qadriyatlar nuqtai nazaridan ko‘rish va baholash,
asarni o‘zgartirish emas."""


QISQA_NAMUNA = """NAMUNA og‘zaki savol (shu darajada bo‘lsin):
  «Olmaxon qish bo‘yi qorda ko‘milgan yong‘oqlarini adashmay topdi. Sen 
  o‘zingga kerakli narsani unutmaslik uchun nima qilasan? Olmaxonning
  qaysi fazilati senga eng ko‘p yoqdi va nega?»
Savol bolani gapirishga undasin, «ha/yo‘q» bilan javob berib bo‘lmasin."""


# ----------------------------------------------------------------------
# Ko‘rsatma — sifat shu yerda hal bo‘ladi
# ----------------------------------------------------------------------
NAMUNA = """NAMUNA (shu darajada va shu uslubda yozilsin):

Pasport:
  "summary": "Teddi — sirkda o‘sgan bahaybat qo‘ng‘ir ayiq. U velosiped
  haydashni biladi-yu, o‘z tabiatini butunlay unutgan. Sirk safarga
  chiqqanda xizmatchi qafas eshigini yopishni unutadi va Teddi tasodifan
  ozod bo‘lib qoladi. Lekin erkinlik unga bayram emas, imtihon bo‘lib
  tushadi... (voqealar ketma-ketligi oxirigacha aytiladi)"
  "for_whom": "Hayvonlar va tabiat haqida o‘qishni yaxshi ko‘radigan,
  qahramonga achinib, uning taqdiri haqida o‘ylaydigan bolaga."

Xotira savoli (literal):
  {"question": "Teddi sirk sahnasida asosan nima qilardi?",
   "options": ["A) Sakrab olov halqasidan o‘tardi",
               "B) Velosiped haydab, sahna bo‘ylab aylanardi",
               "C) Qo‘shiq aytardi",
               "D) Bolalarni yelkasida ko‘tarib yurardi"],
   "answer": "B) Velosiped haydab, sahna bo‘ylab aylanardi"}

Baholash savoli (evaluation):
  {"question": "Teddining kuchliroq ayiqqa bo‘ysunib, jangsiz ketishi —
                qo‘rqoqlikmi yoki aqlmi?",
   "options": ["A) Qo‘rqoqlik — u kurashib ko‘rishi kerak edi",
               "B) Aql — kuchini to‘g‘ri baholab, hayotini saqlab qoldi",
               "C) Loqaydlik — unga baribir edi",
               "D) Xato — shundan keyin hayoti buzildi"],
   "answer": "B) Aql — kuchini to‘g‘ri baholab, hayotini saqlab qoldi"}

His-tuyg‘u savoli (appreciation) — muallifning AYNAN o‘z jumlasiga tayanadi:
  {"question": "Muallif o‘q tekkan lahzani «Teddi og‘riqdan emas, alam va
                talvasaga tushganidan bo‘kirardi» deb tasvirlaydi. Bu jumla
                bilan nimani ko‘rsatmoqchi?",
   "options": ["A) O‘q unga umuman og‘riq bermaganini",
               "B) Ayiqlar og‘riqni sezmasligini",
               "C) Ishonchining sinishi jismoniy og‘riqdan ham og‘irroq
                   bo‘lganini",
               "D) Teddi juda baland ovozda bo‘kira olishini"],
   "answer": "C) Ishonchining sinishi jismoniy og‘riqdan ham og‘irroq bo‘lganini"}
"""


def build_short_prompt(book, text, errors=None):
    """Qisqa asar uchun: pasport + BITTA og‘zaki savol, test yo‘q.

    Ega qarori: bola bir o‘tirishda o‘qib chiqadigan asardan test emas,
    ovozli xulosa so‘raladi.
    """
    fix = ""
    if errors:
        fix = ("\n\nDIQQAT: oldingi javobingda quyidagi xatolar bor edi, tuzat:\n" +
               "\n".join("· " + e for e in errors[:8]))
    return f"""Sen bolalar adabiyoti bo‘yicha mutaxassis va tajribali pedagogsan.
Quyida «{book['title']}» kitobi ({book['author'] or "muallif noma'lum"},
janri: {book['genre']}) matni TO‘LIQ berilgan. Bu — qisqa asar.

Vazifang ikkita:

═══ 1) PASPORT ═══
Bu pasport ERTAGA ota-onaga kerak bo‘ladi: u AI ustozdan «bu kitob nima
haqida?» deb so‘raganda, javob shu yerdan olinadi. Shuning uchun har bir
maydon o‘zicha to‘liq va tushunarli bo‘lsin.

  age_band    — YOSH TOIFASI. FAQAT shu oltitadan bittasini tanla:
                "4-6" | "7-8" | "9-10" | "11-13" | "14-16" | "17-19"
                Bu asar ENG KAM qaysi yoshdan boshlab tushunarli bo‘lishini
                bildiradi. Kattaroq bolalar ham o‘qiyveradi.
  age_hint    — batafsilroq izoh, masalan "9-13" yoki "12+" shaklida.
                YOSHNI BELGILASHDA IKKI QOIDA:
                (a) Yoshni asarning SO‘Z BOYLIGI emas, G‘OYASINING
                    murakkabligi belgilaydi. Bola so‘zlarni o‘qiy olsa-yu,
                    ma'nosini tushunmasa — yosh yuqori bo‘lishi kerak.
                    Falsafiy, ramziy, majoziy asarlarda so‘z sodda bo‘lsa
                    ham, yosh chegarasi baland bo‘ladi.
                (b) Asar chet tilidan tarjima bo‘lsa, quyi chegarani
                    KAMIDA 1 YOSH oshir. Sabab: o‘zbek bolasi uchun begona
                    madaniyat tafsilotlari (turmush tarzi, urf-odat,
                    tarixiy sharoit) qo‘shimcha yuk bo‘ladi, tarjima tili
                    esa ona tilidagi matndan og‘irroq o‘qiladi.
                ANDAZA: «Kichkina shahzoda» — so‘zlari juda sodda, 9 yoshli
                bola bemalol o‘qiy oladi. LEKIN uning g‘oyasi (yolg‘izlik,
                mas'uliyat, kattalar dunyosining bo‘shligi, yo‘qotish)
                falsafiy va ramziy. Shuning uchun uning to‘g‘ri yoshi —
                12+. So‘zga emas, MA'NOGA qarab baho ber. Shubhalansang,
                past emas, YUQORI yoshni tanla: kitobni erta o‘qigan bola
                undan hech narsa olmaydi va kitobdan sovib qoladi.
  topics      — MAVZULAR: 4-6 ta teg (do‘stlik, jasorat, oila, tabiat,
                halollik, mehnat, vatan, ilm...)
  theme       — G‘OYASI: muallif nima demoqchi, asarning bosh fikri.
                ENG KO‘PI 500 BELGI. Ikki-uch jumla, aniq va lo‘nda.
  summary     — QISQACHA SYUJETI: asar voqealarining bayoni, boshidan
                OXIRIGACHA, yechimi bilan. ENG KO‘PI 1500 BELGI (asar qisqa).
                Umumiy gap emas — aniq voqealar ketma-ketligi.
  characters  — ASOSIY QAHRAMONLAR: har biriga bir-ikki jumla — kim, qanday
                odam va asarda nima qiladi. Ikkinchi darajali qahramonlar ham
                kirsin, agar voqeaga ta'sir qilgan bo‘lsa.
  conclusion  — XULOSASI: asar nima bilan tugaydi va bola undan nima oladi.
                Ota-onaga «bu kitob farzandimga nima beradi?» degan savolga
                javob bo‘ladigan 3-6 jumla, ENG KO‘PI 800 BELGI.
  difficulty  — "oson" | "o‘rta" | "qiyin"
  mood        — kayfiyati (masalan: "kulgili, yengil" yoki "hazin, o‘ylantiruvchi")
  for_whom    — QANDAY bolaga mos kelishi, uning qiziqishi tilida. AI ustoz
                shu qatorga qarab kitob tavsiya qiladi.
  events      — VOQEALAR TAFSILOTI: asar epizodlarining RO‘YXATI, ketma-ket.
                Har band — bitta to‘liq jumla, aniq voqea (kim nima qildi,
                nima bo‘ldi). Uzun asarda KAMIDA 20 band, qisqa asarda 6-10.
                Bu ro‘yxat kelajakda yangi test tuzish uchun ishlatiladi:
                shuning uchun kitobning boshidan oxirigacha bo‘lgan barcha
                muhim burilishlar shu yerda bo‘lishi SHART.
  quotes      — MUHIM PARCHALAR: asl matndan 5-8 ta jumla, AYNAN ko‘chirilsin
                (o‘zgartirmasdan). Asarning eng kuchli, eng ma'noli joylari
                tanlansin — keyinchalik savol va suhbat uchun asos bo‘ladi.

═══ 2) OG‘ZAKI SAVOL ═══
Asar qisqa — bola uni bir o‘tirishda o‘qiydi. Shuning uchun test tuzilmaydi.
Uning o‘rniga BITTA savol tuz: bola unga OVOZLI javob beradi.

Savol qanday bo‘lsin:
· Faktik BO‘LMASIN. «Qahramonning ismi nima edi?» kabi bir so‘zli javob
  beriladigan savol TAQIQLANADI.
· Bola kamida 30-60 soniya gapira oladigan, ochiq savol bo‘lsin.
· Javobidan bolaning asarni O‘QIGANI va TUSHUNGANI bilinsin — o‘qimagan
  bola bunga javob bera olmasin.
· Bolaning o‘z fikri, munosabati yoki hayotidan misol so‘ralsin.
· Til sodda va iliq bo‘lsin; bitta-ikkita jumla.
· IMLO: faqat O‘, o‘, G‘, g‘ belgilaridan foydalan. Hech qachon O', o', G', g'.
· TIL: toza o‘zbek tilida, lotin yozuvida. Inglizcha/ruscha so‘z qoldirma.

{QISQA_NAMUNA}

{MADANIY_MEZON}

Natijani FAQAT quyidagi JSON formatida qaytar:
{{
 "passport": {{"age_band": "9-10", "age_hint": "...", "topics": ["..."], "theme": "...",
   "summary": "...", "characters": "...", "conclusion": "...",
   "difficulty": "...", "mood": "...", "for_whom": "...",
   "events": ["1-voqea...", "2-voqea...", "..."],
   "quotes": ["asl matndan jumla", "..."]}},
 "talk_question": "Savol matni?"
}}
{fix}

═══ ASAR MATNI ═══
{text}"""


def build_prompt(book, text, errors=None):
    # Savollar soni kitob uzunligiga qarab: bir sahifalik hikoyadan 30 ta
    # savol chiqarib bo‘lmaydi — AI matndan so‘z terishga majbur bo‘ladi.
    total = profile_for(book["chars"], book.get("pages", 0), book.get("age_group"))
    prof = PROFILES[total]
    pr = prof["parts"]
    ba = prof["barrett"]
    if total == 10:
        qism_izoh = (
            "Bu QISQA asar — bola uni bir o‘tirishda o‘qib chiqadi. Shuning "
            "uchun savollar kam va ular oraliq testlarga bo‘linmaydi: bola "
            "kitobni tugatgach, bittagina yakuniy test topshiradi. Shunga "
            "qaramay har savolga \"part\" qo‘yiladi (asarning boshi, o‘rtasi, "
            "oxiri): %d + %d + %d ta." % (pr[1], pr[2], pr[3]))
    else:
        qism_izoh = (
            "Kitobni uchga bo‘l: \"part\" 1 — boshlanishi, 2 — o‘rtasi, "
            "3 — oxiri. Har qismdan AYNAN %d, %d va %d ta savol. Sabab: "
            "kitobning yarmini o‘qigan bolaga oxiri haqida savol berilmasligi "
            "kerak." % (pr[1], pr[2], pr[3]))

    # Yosh guruhi kichik bo‘lsa variant kam bo‘ladi — bola uchun yengilroq.
    age_group = str(book.get("age_group", "8"))
    opt_count = 4 if age_group == "12" else 3
    opt_letters = ", ".join('"%s) ..."' % c for c in "ABCD"[:opt_count])

    coverage_note = (
        "Matn kitobning KESMASI: boshi to‘liq, o‘rtasidan oynalar, oxiri "
        "to‘liq va (agar bo‘lsa) bob sarlavhalari ro‘yxati. «[...]» belgisi "
        "tushirib qoldirilgan joyni bildiradi. Bob sarlavhalari kitobning "
        "butun yo‘lini ko‘rsatadi — undan foydalan. Ko‘rmagan joying haqida "
        "savol TO‘QIMA."
    )
    fix = ""
    if errors:
        fix = ("\n\nDIQQAT: oldingi javobing quyidagi xatolar bilan qaytdi. "
               "Ularni tuzatib, TO‘LIQ javobni qaytadan yoz:\n" +
               "\n".join("· " + e for e in errors[:10]))

    return f"""Sen bolalar adabiyoti bo‘yicha mutaxassis va tajribali pedagogsan.
Quyida «{book['title']}» kitobi ({book['author'] or "muallif noma'lum"},
janri: {book['genre']}) matni berilgan. {coverage_note}

Vazifang: kitob PASPORTI va 30 ta TEST savolini tuzish.

═══ 1) PASPORT ═══
Bu pasport ERTAGA ota-onaga kerak bo‘ladi: u AI ustozdan «bu kitob nima
haqida?» deb so‘raganda, javob shu yerdan olinadi. Shuning uchun har bir
maydon o‘zicha to‘liq va tushunarli bo‘lsin.

  age_band    — YOSH TOIFASI. FAQAT shu oltitadan bittasini tanla:
                "4-6" | "7-8" | "9-10" | "11-13" | "14-16" | "17-19"
                Bu asar ENG KAM qaysi yoshdan boshlab tushunarli bo‘lishini
                bildiradi. Kattaroq bolalar ham o‘qiyveradi.
  age_hint    — batafsilroq izoh, masalan "9-13" yoki "12+" shaklida.
                YOSHNI BELGILASHDA IKKI QOIDA:
                (a) Yoshni asarning SO‘Z BOYLIGI emas, G‘OYASINING
                    murakkabligi belgilaydi. Bola so‘zlarni o‘qiy olsa-yu,
                    ma'nosini tushunmasa — yosh yuqori bo‘lishi kerak.
                    Falsafiy, ramziy, majoziy asarlarda so‘z sodda bo‘lsa
                    ham, yosh chegarasi baland bo‘ladi.
                (b) Asar chet tilidan tarjima bo‘lsa, quyi chegarani
                    KAMIDA 1 YOSH oshir. Sabab: o‘zbek bolasi uchun begona
                    madaniyat tafsilotlari (turmush tarzi, urf-odat,
                    tarixiy sharoit) qo‘shimcha yuk bo‘ladi, tarjima tili
                    esa ona tilidagi matndan og‘irroq o‘qiladi.
                ANDAZA: «Kichkina shahzoda» — so‘zlari juda sodda, 9 yoshli
                bola bemalol o‘qiy oladi. LEKIN uning g‘oyasi (yolg‘izlik,
                mas'uliyat, kattalar dunyosining bo‘shligi, yo‘qotish)
                falsafiy va ramziy. Shuning uchun uning to‘g‘ri yoshi —
                12+. So‘zga emas, MA'NOGA qarab baho ber. Shubhalansang,
                past emas, YUQORI yoshni tanla: kitobni erta o‘qigan bola
                undan hech narsa olmaydi va kitobdan sovib qoladi.
  topics      — MAVZULAR: 4-6 ta teg (do‘stlik, jasorat, oila, tabiat,
                halollik, mehnat, vatan, ilm...)
  theme       — G‘OYASI: muallif nima demoqchi, asarning bosh fikri.
                ENG KO‘PI 500 BELGI. Ikki-uch jumla, aniq va lo‘nda.
  summary     — QISQACHA SYUJETI: asar voqealarining bayoni, boshidan
                OXIRIGACHA, yechimi bilan. 1500-3000 BELGI — batafsil yoz,
                hech bir muhim voqeani tushirib qoldirma. Umumiy gap emas —
                aniq voqealar ketma-ketligi, sabab-oqibati bilan.
  characters  — ASOSIY QAHRAMONLAR: har biriga bir-ikki jumla — kim, qanday
                odam va asarda nima qiladi. Ikkinchi darajali qahramonlar ham
                kirsin, agar voqeaga ta'sir qilgan bo‘lsa.
  conclusion  — XULOSASI: asar nima bilan tugaydi va bola undan nima oladi.
                Ota-onaga «bu kitob farzandimga nima beradi?» degan savolga
                javob bo‘ladigan 3-6 jumla, ENG KO‘PI 800 BELGI.
  difficulty  — "oson" | "o‘rta" | "qiyin"
  mood        — kayfiyati (masalan: "kulgili, yengil" yoki "hazin, o‘ylantiruvchi")
  for_whom    — QANDAY bolaga mos kelishi, uning qiziqishi tilida. AI ustoz
                shu qatorga qarab kitob tavsiya qiladi.
  events      — VOQEALAR TAFSILOTI: asar epizodlarining RO‘YXATI, ketma-ket.
                Har band — bitta to‘liq jumla, aniq voqea (kim nima qildi,
                nima bo‘ldi). Uzun asarda KAMIDA 20 band, qisqa asarda 6-10.
                Bu ro‘yxat kelajakda yangi test tuzish uchun ishlatiladi:
                shuning uchun kitobning boshidan oxirigacha bo‘lgan barcha
                muhim burilishlar shu yerda bo‘lishi SHART.
  quotes      — MUHIM PARCHALAR: asl matndan 5-8 ta jumla, AYNAN ko‘chirilsin
                (o‘zgartirmasdan). Asarning eng kuchli, eng ma'noli joylari
                tanlansin — keyinchalik savol va suhbat uchun asos bo‘ladi.

═══ 2) {total} TA SAVOL ═══
{qism_izoh}

Savollar Barrett taksonomiyasi bo‘yicha taqsimlanadi. JAMI SONI AYNAN shunday
bo‘lsin (buzilsa javob rad etiladi):
  "literal"        — {ba["literal"]} ta  (xotira: kim, nima, qayerda, qanday tartibda)
  "reorganization" — {ba["reorganization"]} ta  (voqealarni tartibga solish, guruhlash, ajratish)
  "inferential"    — {ba["inferential"]} ta  (nega shunday bo‘ldi, qahramon nega shunday qildi)
  "evaluation"     — {ba["evaluation"]} ta  (to‘g‘ri qildimi? qanday baholaysan?)
  "appreciation"   — {ba["appreciation"]} ta  (muallifning tili, tasviri, uyg‘otgan tuyg‘usi)
Bu {ba["literal"]} ta xotira (40%) va {total - ba["literal"]} ta tushunish (60%) degani.

MUHIM: savol soni matnga mos. Matnda yo‘q narsani TO‘QIMA va bitta faktni
ikki xil so‘z bilan qayta so‘rama — har savol boshqa narsani tekshirsin.

Har savolga "category" ham qo‘yiladi (ilova uchun):
  literal, reorganization → "factual"
  inferential             → "logic"
  evaluation, appreciation → "conclusion"

DIQQAT — TESTSIZ HOLAT:
Agar sen bu asarni "4-6" yosh toifasiga kiritsang, unga TEST TUZILMAYDI.
7 yoshgacha bola uchun kitob o‘yin va suhbat, imtihon emas. Bunday holda
"questions" ro‘yxatini BO‘SH qoldir va uning o‘rniga "talk_question"
maydonini to‘ldir: bola ovozda javob beradigan bitta ochiq savol.
Boshqa barcha toifalarda test tuziladi.

ENG MUHIM TALAB — SODDALIK:
Bu IMTIHON EMAS. Maqsad — kitobni o‘qigan bolani rag‘batlantirish, uni
sinash emas. Kitobni diqqat bilan o‘qigan bola savollarning deyarli
hammasiga qiynalmasdan javob bera olishi SHART. Aks holda u «o‘qimagan»
bo‘lib chiqadi, bu esa uyda janjalga va bolada stressga sabab bo‘ladi.

· SAVOL QISQA bo‘lsin — 12 so‘zdan oshmasin. Bitta jumla, bitta fikr.
  Savol ichiga uzun iqtibos yoki ikkita fikrni tiqishtirma.
· VARIANTLAR QISQA — har biri 6 so‘zdan oshmasin.
· Savol asarning ASOSIY voqealari va qahramonlari haqida bo‘lsin.
  Mayda tafsilot so‘ralmasin: «necha yoshda edi», «nechta edi»,
  «qaysi kuni» kabi savollar TAQIQLANADI — kitobni o‘qigan bola ham
  bunday mayda narsani eslamaydi.
· Noto‘g‘ri variantlar kitobni o‘qigan bolaga DARROV noto‘g‘ri ko‘rinsin.
  «Deyarli to‘g‘ri», chalg‘ituvchi variant yozma — bu tuzoq bo‘ladi.
· Tushunish savollari ham sodda tilda bo‘lsin: «Qahramon nega shunday
  qildi?», «Nima uchun ... deb o‘ylaysan?» kabi.
· Yosh guruhi {age_group} — savollar aynan shu yoshdagi bolaning
  so‘z boyligiga mos bo‘lsin.

MAJBURIY TALABLAR:
· Har savolda {opt_count} ta variant: {opt_letters}
· "answer" variantlardan birining AYNAN nusxasi bo‘lsin (harfi-harfiga)
· id: 1 dan {total} gacha
· Savol kitobni O‘QIGAN bola javob bera oladigan, o‘qimagani esa
  TOPA OLMAYDIGAN bo‘lsin. «Qahramon yaxshimi?» kabi umumiy savol yaramaydi.
· "appreciation" savollari muallifning AYNIQSA aniq jumlasi yoki tasviriga
  tayansin — shunda javobi bir xil bo‘ladi, taxmin bo‘lmaydi.
· Noto‘g‘ri variantlar ham ishonarli bo‘lsin, kulgili emas.
· Noto‘g‘ri variantlar VOQEA jihatidan xato bo‘lsin, QADRIYAT jihatidan
  emas. Ya'ni «qizlar faqat uy ishini qilgani ma'qul» yoki «kattalarni
  eshitmasa ham bo‘ladi» kabi zararli fikrni GAP sifatida yozma — bola
  uni baribir o‘qiydi va xotirasida qolishi mumkin. Tuzoq asar voqeasida
  bo‘lsin: boshqa qahramon, boshqa joy, boshqa sabab.
· IMLO: faqat va faqat O‘, o‘, G‘, g‘ belgilaridan foydalan (chapga qaragan
  jingalak belgi). Hech qachon O', o', G', g' yozma.
· TIL: hamma narsa TOZA O‘ZBEK TILIDA, lotin yozuvida bo‘lsin. Inglizcha
  yoki ruscha so‘zni tarjima qilmay qoldirma («astronomers» emas —
  «astronomlar»). Kirill harfi umuman ishlatilmasin.

{NAMUNA}

{MADANIY_MEZON}

Natijani FAQAT quyidagi JSON formatida qaytar:
{{
 "passport": {{"age_band": "9-10", "age_hint": "...", "topics": ["..."], "theme": "...",
   "summary": "...", "characters": "...", "conclusion": "...",
   "difficulty": "...", "mood": "...", "for_whom": "...",
   "events": ["1-voqea...", "2-voqea...", "..."],
   "quotes": ["asl matndan jumla", "..."]}},
 "talk_question": "(faqat 4-6 toifasi uchun; aks holda bo‘sh satr)",
 "questions": [
   {{"id": 1, "part": 1, "category": "factual", "barrett": "literal",
     "question": "...", "options": ["A) ...","B) ...","C) ...","D) ..."],
     "answer": "A) ..."}}
 ]
}}
{fix}

═══ KITOB MATNI ═══
{text}"""


# ----------------------------------------------------------------------

def build_diniy_prompt(book, text, errors=None):
    """Diniy-ma'rifiy kitob: pasport + 5 ta ochiq savol, TEST YO‘Q.

    Ega qarori (2026-09-01): diniy kitobdan test tuzilmaydi — AI diniy
    matnni talqin qilishda xato qilishi mumkin, xato savol esa bolaga
    noto‘g‘ri bilim beradi. O‘rniga bola o‘qigan ANIQ PARCHAGA tayangan
    ochiq savol beriladi; ota-ona xohlasa testni o‘zi tuzadi.
    """
    fix = ""
    if errors:
        fix = ("\n\nDIQQAT: oldingi javobingda quyidagi xatolar bor edi, tuzat:\n" +
               "\n".join("· " + e for e in errors[:8]))
    return f"""Sen o‘zbek oilalari uchun mo‘ljallangan bolalar ilovasida ishlaydigan
muharrirsan. Quyida «{book['title']}» kitobi ({book['author']}) matni berilgan.
Bu — DINIY-MA'RIFIY kitob.

ENG MUHIM QOIDA: sen bu kitobga TEST TUZMAYSAN va diniy hukm chiqarmaysan.
Matnni o‘zingdan sharhlama, unga yangi ma'no qo‘shma. Vazifang — kitobning
pasportini yozish va matndagi ANIQ parchalarga tayangan ochiq savollar tuzish.

═══ 1) PASPORT ═══
  age_band    — "14-16" yoki "17-19" (kitobning og‘irligiga qarab)
  age_hint    — qisqa izoh, masalan "14+"
  topics      — 4-6 ta teg (odob, oila, halollik, sabr, ilm...)
  theme       — kitob nima haqida, bosh maqsadi. ENG KO‘PI 500 BELGI.
  summary     — kitob MAZMUNI: qaysi mavzular, qaysi tartibda yoritilgan.
                1500-3000 BELGI. O‘zingdan hukm qo‘shma, faqat bayon qil.
  characters  — kitobda tilga olingan asosiy shaxslar (bo‘lmasa: "yo‘q").
  conclusion  — o‘quvchi bu kitobdan nima oladi. 3-6 jumla, 800 belgigacha.
  difficulty  — "oson" | "o‘rta" | "qiyin"
  mood        — ohangi (masalan: "vazmin, nasihatomuz")
  for_whom    — qanday o‘quvchiga mos
  events      — KITOB TUZILISHI: boblar yoki mavzular ro‘yxati, ketma-ket.
                Har band bitta jumla. KAMIDA 15 band.
  quotes      — matndan AYNAN ko‘chirilgan 5-8 ta jumla, o‘zgartirmasdan.

═══ 2) 5 TA OCHIQ SAVOL ═══
Har savol shunday tuziladi:
  · "context" — kitobdan AYNAN ko‘chirilgan parcha (2-5 jumla). Savol
    faqat shu parchaga tayanadi. Parchani o‘zgartirma, qisqartirma.
  · "question" — shu parchani o‘qigan o‘smirga beriladigan ochiq savol.
    Javobi "ha/yo‘q" bo‘lmasin; o‘quvchi o‘z fikrini aytsin yoki hayotidan
    misol keltirsin. Savolda diniy hukm so‘ralmasin («bu savobmi?» kabi).
    MUROJAAT: bolaga «SEN» deb murojaat qilinadi («sizningcha» emas —
    «sencha», «hayotingdan misol keltir»). Ilovaning hamma joyida
    shunday, savol ham shu ohangda bo‘lsin.
    To‘g‘ri-noto‘g‘ri javob yo‘q — savol o‘ylantirish uchun.
  · "part" — 1, 2 yoki 3 (kitobning boshi, o‘rtasi, oxiri).

IMLO: faqat O‘, o‘, G‘, g‘ belgilaridan foydalan. Hech qachon O', o', G', g'.
TIL: toza o‘zbek tilida, lotin yozuvida. Kirill harfi ishlatilmasin.

Natijani FAQAT quyidagi JSON formatida qaytar:
{{
 "passport": {{"age_band": "14-16", "age_hint": "...", "topics": ["..."],
   "theme": "...", "summary": "...", "characters": "...", "conclusion": "...",
   "difficulty": "...", "mood": "...", "for_whom": "...",
   "events": ["..."], "quotes": ["..."]}},
 "talk_questions": [
   {{"part": 1, "context": "kitobdan aynan ko‘chirilgan parcha",
     "question": "Ochiq savol?"}}
 ]
}}
{fix}

═══ KITOB MATNI ═══
{text}"""


# ----------------------------------------------------------------------
def read_work(book):
    with open(os.path.join(WORK, book["work_file"]), encoding="utf-8") as fh:
        raw = fh.read()
    # Sarlavha blokidan keyingi qismi — matnning o‘zi
    marker = "=" * 60
    return raw.split(marker, 1)[1].strip() if marker in raw else raw


def money(usage):
    return (usage["in"] / 1e6 * PRICE_IN) + (usage["out"] / 1e6 * PRICE_OUT)


def log(msg):
    line = time.strftime("%m-%d %H:%M:%S  ") + msg
    # flush — natija faylga yozilganda ham darrov ko‘rinsin
    print(line, flush=True)
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")


async def one_book(book, usage):
    """Bitta kitobni ishlaydi. True — muvaffaqiyat."""
    text = read_work(book)
    out_path = os.path.join(OUT, book["work_file"][:-4] + ".json")
    errors = None

    diniy = book.get("mode") == "diniy"
    short = (not diniy and
             profile_for(book["chars"], book.get("pages", 0), book.get("age_group")) == 0)
    for attempt in (1, 2, 3):
        if diniy:
            prompt = build_diniy_prompt(book, text, errors)
        else:
            prompt = (build_short_prompt(book, text, errors) if short
                      else build_prompt(book, text, errors))
        try:
            resp = await ai_service._ask("kitob_pasporti", [prompt],
                                         json_mode=True, attempts=1)
        except Exception as e:
            log("   ✗ %d-urinish: AI xatosi: %r" % (attempt, e))
            errors = None
            continue

        um = getattr(resp, "usage_metadata", None)
        if um:
            usage["in"] += getattr(um, "prompt_token_count", 0) or 0
            usage["out"] += getattr(um, "candidates_token_count", 0) or 0

        try:
            data = json.loads(ai_service.clean_json(resp.text))
        except Exception as e:
            log("   ✗ %d-urinish: JSON buzuq: %r" % (attempt, e))
            errors = ["Javob JSON formatida emas edi"]
            continue

        full = {
            "title": book["title"], "author": book["author"],
            "genre": book["genre"], "age_group": book["age_group"],
            "coverage": book["coverage"],
            "passport": data.get("passport", {}),
            "questions": [] if (short or diniy) else data.get("questions", []),
        }
        band = (full["passport"] or {}).get("age_band")
        if diniy:
            full["no_test"] = True
            full["questions"] = []
            full["talk_questions"] = data.get("talk_questions") or []
        elif short or band == "4-6":
            full["short_form"] = True
            full["questions"] = []
            full["talk_question"] = (data.get("talk_question") or "").strip()
        with open(out_path, "w", encoding="utf-8") as fh:
            json.dump(full, fh, ensure_ascii=False, indent=1)

        errors = check(out_path)
        if not errors:
            return True
        log("   · %d-urinish: %d ta kamchilik (%s...)"
            % (attempt, len(errors), errors[0][:60]))

    # Uch urinish ham chiqmadi. Yozilgan bo‘lsa — chetga surib qo‘yamiz,
    # aks holda keyingi safar «tayyor» deb o‘tkazib yuborilardi.
    if os.path.exists(out_path):
        os.replace(out_path, out_path + ".xato")
    return False


async def run(day, limit, dry):
    """`day = 0` — kunlarga bo‘lmasdan, qolgan HAMMA kitobni ketma-ket qiladi."""
    with open(INDEX, encoding="utf-8") as fh:
        books = json.load(fh)
    only = None
    if "--kitob" in sys.argv:
        only = sys.argv[sys.argv.index("--kitob") + 1]
    band = None
    if "--toifa" in sys.argv:
        band = sys.argv[sys.argv.index("--toifa") + 1]
    todo = [b for b in books
            if (only is None or b["work_file"].startswith(only))
            and (band is None or b.get("band") == band)
            and (day == 0 or b.get("day") == day)
            and not os.path.exists(os.path.join(OUT, b["work_file"][:-4] + ".json"))]
    if limit:
        todo = todo[:limit]
    if not todo:
        print("Qiladigan ish qolmagan." if day == 0 else "%d-kunda qiladigan ish qolmagan." % day)
        return 0

    chars = sum(b["sent_chars"] for b in todo)
    out_tok = sum(700 if profile_for(b["chars"], b.get("pages", 0), b.get("age_group")) == 0
                  else (5000 if profile_for(b["chars"], b.get("pages", 0), b.get("age_group")) == 20 else 6900)
                  for b in todo)
    est = (chars / 4.0 + 2000 * len(todo)) / 1e6 * PRICE_IN + \
          out_tok / 1e6 * PRICE_OUT
    print(("HAMMASI: %d ta kitob, taxminiy narx ~$%.2f\n" % (len(todo), est))
          if day == 0 else
          ("%d-kun: %d ta kitob, taxminiy narx ~$%.2f\n" % (day, len(todo), est)))
    if dry:
        return 0
    if not os.getenv("GEMINI_API_KEY"):
        print("XATO: GEMINI_API_KEY topilmadi. `.env` fayliga qo‘ying.")
        return 1

    usage = {"in": 0, "out": 0}
    ok = bad = 0
    for i, book in enumerate(todo, 1):
        log("[%d/%d] %s (%s, %s belgi)"
            % (i, len(todo), book["title"], book["coverage"],
               f"{book['sent_chars']:,}"))
        t0 = time.time()
        if await one_book(book, usage):
            ok += 1
            log("   ✓ tayyor (%.0f soniya, jami $%.2f)" % (time.time() - t0, money(usage)))
        else:
            bad += 1
            log("   ✗ 3 urinishda ham chiqmadi — qo‘lda ko‘riladi")

    print()
    log("YAKUN: %d ta tayyor, %d ta chiqmadi. Sarflandi: $%.2f "
        "(kirish %s, chiqish %s token)"
        % (ok, bad, money(usage), f"{usage['in']:,}", f"{usage['out']:,}"))
    return 0


def main():
    global WORK, OUT, INDEX, LOG
    args = sys.argv[1:]
    # `--yangi` — 2026-09-01 dagi yangi ro‘yxat (book_work2 / book_out2)
    if "--yangi" in args:
        WORK = os.path.join(ROOT, "tools", "book_work2")
        OUT = os.path.join(ROOT, "tools", "book_out2")
        INDEX = os.path.join(WORK, "index.json")
        LOG = os.path.join(OUT, "_log.txt")
    # `--hammasi` — kunlarga bo‘lmay, qolgan barcha kitoblarni bir yo‘la
    day = 0 if "--hammasi" in args else \
        (int(args[args.index("--kun") + 1]) if "--kun" in args else 1)
    limit = int(args[args.index("--limit") + 1]) if "--limit" in args else 0
    dry = "--narx" in args
    os.makedirs(OUT, exist_ok=True)
    return asyncio.run(run(day, limit, dry))


if __name__ == "__main__":
    sys.exit(main())
