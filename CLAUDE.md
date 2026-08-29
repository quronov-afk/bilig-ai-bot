# Bilig AI — loyiha qo‘llanmasi (Claude Code uchun)

Bu fayl har bir yangi Code sessiyasida avtomatik o‘qiladi. Shu yerdagi qoidalarga
**har doim**, so‘ralmasa ham, amal qil.

## MUHIM: Loyiha egasi bilan muloqot uslubi

Loyiha egasi **dasturchi emas**. U kod yozishni, terminalni, git nima ekanini
bilmaydi. Shuning uchun:

- Har bir amalni **"qo‘limdan ushlab" darajada sodda va aniq** tushuntir —
  qadam-baqadam, oddiy so‘zlar bilan.
- Texnik atama ishlatishdan oldin (masalan "commit", "push", "endpoint",
  "deploy", "migratsiya") — bir jumlada, oddiy tilda nima ekanini tushuntir.
  Masalan: *"push qilamiz (ya'ni o‘zgarishlarni GitHub'ga yuboramiz)"*.
- Terminal buyrug‘ini ishlatishdan oldin, **nima uchun** shu buyruq
  kerakligini va u **nima qilishini** oddiy tilda ayt — keyin buyruqni ber.
- Hech qachon "albatta bilasiz" deb taxmin qilma — har doim eng boshidan
  boshlab tushuntir, hatto oldin bir marta aytilgan bo‘lsa ham.
- Xavfli yoki qaytarib bo‘lmaydigan amaldan oldin (masalan: fayllarni
  o‘chirish, `git push --force`, bazani tozalash) — avval **aniq va tushunarli
  tilda ogohlantir**, tasdiq so‘ra, keyin bajar.
- Javoblarni qisqa va tartibli qatorlarga bo‘lib yoz (1-qadam, 2-qadam...) —
  uzun, uzluksiz paragraflardan qoch.
- Muvaffaqiyatli bajarilgan amaldan keyin, oddiy tilda **nima o‘zgarganini**
  va **keyingi qadam nima ekanini** ayt.
- Faqat o‘zbek tilida javob ber (agar boshqacha so‘ralmasa).

## Loyiha haqida

"Bilig AI" — bolalar uchun kitob o‘qish odatini shakllantiruvchi Telegram bot va
unga qo‘shimcha Mini App. Ikki foydalanuvchi turi bor: **ota-ona** va **bola**.
AI (Gemini) orqali: kitob sahifasini tekshirish, ovozli xulosani baholash, test
savollari tuzish, kitob muqovasini aniqlash.

## Fayl tuzilishi

```
main.py, config.py, database.py, keyboards.py, states.py, ai_service.py   ← ASOSIY BOT (aiogram), tegilmaydi
handlers/                                                                  ← bot handlerlari, tegilmaydi
server.py                                                                  ← webapp_api.py'ni fon rejimida ishga tushiradi
webapp_api.py                                                              ← Mini App BACKEND (Flask). Bot bilan bir xil SQLite bazadan foydalanadi
webapp/
  index.html, style.css, app.js                                           ← Mini App FRONTEND (vanilla JS, freymvorksiz)
```

`database.py`, `ai_service.py`, `handlers/*.py` — bularga faqat aniq so‘ralganda
tegiladi. Ular botning o‘zagi.

## QAT'IY IMLO QOIDASI (eng muhim qoida)

O‘zbek lotin alifbosidagi **O‘, o‘, G‘, g‘** harflari FAQAT chapga qaragan
jingalak belgi bilan yoziladi: **‘** (Unicode U+2018).

**Taqiqlangan variantlar** (hech qachon ishlatilmasin):
- Oddiy vertikal apostrof: `O'`, `o'`, `G'`, `g'`
- Orqaga qiyshiq belgi: `` O` ``, `` o` ``, `` G` ``, `` g` ``
- O‘ngga qaragan belgi: `O’`, `o’`, `G’`, `g’`

To‘g‘ri: **O‘qish, O‘quvchi, Qo‘shish, Bog‘, Ko‘rish, Yo‘q, To‘g‘ri**

Tutuq belgili so‘zlar (ma'lumot, e'tibor, a'lo, san'at) boshqa masala — ularga
tegilmaydi, ular oddiy apostrof bilan qoladi.

**Har bir kod o‘zgarishidan keyin** quyidagi tekshiruvni bajar (buni avtomatik,
so‘ralmasa ham qil):

```bash
python3 -c "
import re
bad = 0
for fname in ['webapp/app.js','webapp/style.css','webapp/index.html','webapp_api.py']:
    s = open(fname, encoding='utf-8').read()
    for m in re.finditer(r\"[oOgG](\\\\)?['\u0060\u2019]\", s):
        print(fname, repr(s[max(0,m.start()-25):m.end()+25]))
        bad += 1
print('JAMI shubhali:', bad)
"
```

Diqqat: bu tekshiruv kod ichidagi haqiqiy holatlarni ham (masalan CSS
`font-family:'Nunito'` yoki JS satr ichidagi tirnoqlar) belgilab chiqishi mumkin
— shularni farqlab, faqat haqiqiy imlo xatolarini tuzat.

## "Matnlarga tegma" qoidasi

Foydalanuvchi bir necha marta alohida ta'kidlagan: **e'tiroz bildirilmagan
matnlarga tegilmasin**. Bu degani:

- Kichik tuzatish so‘ralganda, faqat aynan shu joyni o‘zgartir — butun faylni
  qayta yozib, boshqa matnlarni ham "yaxshilab qo‘yish" kerak emas.
- Katta arxitektura o‘zgarishi (masalan, yangi tab qo‘shish) so‘ralgandagina
  fayl strukturasini keng qamrovda o‘zgartirish mumkin.
- Har doim aniq nima o‘zgarganini o‘zingga hisobot ber (diff shaklida), shunda
  foydalanuvchi keraksiz o‘zgarishlarni darrov ko‘radi.

## Dizayn tizimi (UI/UX)

- **Uslub**: zamonaviy, vazmin minimalizm. Hech qanday emoji — faqat qo‘lda
  chizilgan chiziqli SVG ikonalar (`app.js` ichidagi `ICON_PATHS` va `icon()`
  funksiyasidan foydalanilsin).
- **Ranglar** (`style.css` dagi `:root` o‘zgaruvchilari):
  - `--brand: #4E8EF7` — ochroq, yorqin ko‘k (asosiy brend rangi)
  - `--gold: #F59E0B` — Bilig tangasi
  - `--success: #10B981`, `--danger: #EF4444`
  - Fon: `--bg: #F8FAFC`, kartalar: `--surface: #FFFFFF`
- **Shrift**: Nunito (Google Fonts) — kattalar va bolalar uchun bir xil
  darajada iliq va o‘qilishi oson bo‘lgani uchun tanlangan.
- **Bo‘rtma effekt**: barcha tugma/karta/chiplarda `--shadow-raised` yordamida
  yumshoq "bosilib turgan" ko‘rinish beriladi.
- **Burchaklar**: `--radius-lg/md/sm` (16-20px), keskin burchak yo‘q.

## Ilova arxitekturasi

- **4 ta doimiy tab** (pastki navigatsiya): Bosh sahifa, **Kitobxona**, Do‘kon +
  to‘rtinchisi rolga qarab farq qiladi: ota-onada **Bolaxona**, bolada
  **Reyting**. Diqqat: «Kitobxona» — ko‘rinadigan nom; koddagi ichki nomi
  avvalgidek `plans` bo‘lib qoladi (2026-08-29 da qayta nomlandi).
  Kitobxona ichida: kitob qo‘shish, rejalar, «Oila kitobxonligi» pasporti
  va yoshga mos tavsiyalar javoni.
- **Do‘kon ichida Hamyon** — alohida tab emas, `State.storeView` bilan
  almashadigan ikkinchi ko‘rinish. Ota-onada Reyting'ga header'dagi belgi orqali kirilyapti
  (yuqorida, doim ko‘rinadi).
- **Bolaxona rejimi**: ota-ona farzand nomidan kirib, uning to‘liq (child)
  interfeysida ishlaydi. `State.activeChildId` shu holatni belgilaydi;
  `isChildView()` funksiyasi butun ilova bo‘ylab shu asosda qaror qabul qiladi.
- **10 ta bolalar avatari** (cho‘chqa YO‘Q): tulki, ayiqcha, pingvin, quyoncha,
  mushukcha, boyo‘g‘li, panda, sherbola, fil, kuchukcha — `app.js` dagi
  `AVATARS` obyektida, o‘z-o‘zidan yetarli SVG (rang+shakl birga).
- Bola ro‘yxatdan o‘tishda: ota-ona kodi bilan bog‘langandan so‘ng, avatar +
  ism + yosh so‘raladigan alohida ekran chiqadi (`screen-child-profile`).

## Backend haqida muhim faktlar

- `webapp_api.py` — Flask ilovasi, `database.py`dagi **bir xil** `conn`/`cursor`
  obyektlaridan foydalanadi (bot bilan bitta SQLite fayl).
- Auth: har bir so‘rov `X-Telegram-Init-Data` header orqali Telegram HMAC
  imzosini tekshiradi (`validate_init_data`). `DEV_MODE=1` bo‘lsa, `?dev_id=`
  orqali tekshiruvsiz sinash mumkin (faqat local test uchun).
- `ai_service.py` dagi funksiyalar `async def` — Flask ichida `run_async()`
  yordamchisi orqali (`asyncio.run`) chaqiriladi.
- Yozish amallari `db_lock` (threading.Lock) bilan himoyalangan — ko‘p bo‘limli
  yozuvda shu naqshni buzmaslik kerak.
- Yangi ustun qo‘shish kerak bo‘lsa, `database.py`ni qayta yozmang — xavfsiz
  `ALTER TABLE ... ADD COLUMN` migratsiyasini `webapp_api.py` boshida,
  `try/except` bilan o‘rab qo‘shing (mavjud namunaga qarang: `avatar_id`,
  `profile_done`).

## Kod uslubi (`webapp/app.js`)

- Vanilla JavaScript, hech qanday freymvork yo‘q.
- Funksiyalar `function` kalit so‘zi bilan (arrow function emas) — mavjud
  uslubga mos yozing.
- Barcha HTML `data-action="..."` atributi orqali, markazlashgan bitta
  `document.addEventListener("click", ...)` dispatcherida boshqariladi.
  Yangi interaktiv element qo‘shsangiz, shu naqshga qo‘shiling.
- `api(path, opts)` — barcha backend so‘rovlari shu yordamchi orqali.

## Har bir o‘zgarishdan keyin tekshir

1. `node --check webapp/app.js` — JS sintaksisi.
2. `python3 -c "import ast; ast.parse(open('webapp_api.py').read())"` — Python
   sintaksisi.
3. Yuqoridagi imlo tekshiruv skripti.
4. O‘zgargan endpoint bo‘lsa, frontend chaqiruvi bilan yo‘l (`/api/...`) va
   metod (`GET`/`POST`) mosligini qo‘lda solishtiring.

## Deploy

O‘zgarishlar tayyor bo‘lgach, foydalanuvchi odatda GitHub'ga push qilib,
Render.com'da qayta deploy qiladi. Agar Git ulangan bo‘lsa, commit xabarini
o‘zbek tilida, qisqa va aniq yozing (masalan: `"Do‘kon dizaynini yangilash"`).
