# Matn ustaxonasi

Ilovadagi barcha ko‘rinadigan matnlarni bir joydan tahrirlash uchun.

## Qanday ishlaydi

1. **Yig‘ish** — `python3 tools/texts/extract_texts.py`
   Loyihadagi fayllardan matnlarni ajratib, `texts.json` ga yozadi.
   Manbalar: `webapp/app.js`, `webapp/index.html`, `webapp_api.py`,
   `tools/badges/badge_defs.py` (nishon nomi, sharti, xabari).

2. **Panel tuzish** — `python3 tools/texts/build_panel.py`
   `panel.html` — Artifact sifatida chiqariladigan tahrir paneli.
   Chapda hozirgi matn, o‘ngda bo‘sh maydon. «Saqlash» bosilganda
   sahifa o‘zining yangi nusxasini chiqaradi — tahrirlar yo‘qolmaydi.

3. **Qo‘llash** — `python3 tools/texts/apply_texts.py <panel.html> --yoz`
   Artifact'dan o‘qib olingan fayldan tahrirlarni olib, loyiha
   fayllaridagi eski matnlarni almashtiradi.

## Diqqat

- Matn ichidagi `{...}` — o‘zgaruvchi (ism, raqam). Ular o‘z holida
  qolishi shart, aks holda xabar buziladi.
- **Nishon nomini o‘zgartirish xavfli**: nomlar bazada
  (`Users.badges`) saqlanadi. Nom o‘zgarsa, eski nishonlar
  yo‘qoladi — avval migratsiya kerak.
- Matnlar o‘zgargandan keyin `webapp/app.js` dagi `ASSET_V` va
  `webapp/index.html` dagi `?v=` ni oshiring.
