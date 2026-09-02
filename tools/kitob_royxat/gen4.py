# -*- coding: utf-8 -*-
import gen2, final_list as FL
CSS = gen2.CSS + """
.chip.tayyor{color:var(--bor); background:var(--bor-bg)}
.chip.kutish{color:var(--mut); background:var(--mut-bg)}
.kirish{font-family:Literata,Georgia,serif; font-size:16.5px; color:var(--ink-soft); max-width:68ch}
.sechead{display:flex; flex-wrap:wrap; align-items:baseline; gap:12px; justify-content:space-between}
.count{font-size:13px; color:var(--ink-faint); font-variant-numeric:tabular-nums; white-space:nowrap}
.jam{display:flex; flex-wrap:wrap; border:1px solid var(--line); background:var(--surface)}
.jam div{flex:1 1 170px; padding:20px; border-right:1px solid var(--line-soft)}
.jam div:last-child{border-right:none}
.jam b{display:block; font-family:Literata,Georgia,serif; font-size:34px; line-height:1.1; font-variant-numeric:tabular-nums}
.jam span{font-size:13px; color:var(--ink-soft)}
.pasport{display:grid; grid-template-columns:repeat(auto-fit,minmax(240px,1fr)); gap:2px; background:var(--line); border:1px solid var(--line)}
.pasport div{background:var(--surface); padding:16px 18px}
.pasport h4{margin:0 0 4px; font-family:Literata,Georgia,serif; font-size:15px; font-weight:600}
.pasport p{font-size:13.5px; color:var(--ink-soft)}
.pasport .eski{color:var(--ink-faint); text-decoration:line-through; margin-right:6px}
.pasport .yangi{color:var(--bor); font-weight:600}
"""

def tbl(rows):
    tr = "\n".join(
      f'<tr><td class="asar">{t}</td><td class="mual">{a}</td><td class="yosh">{y}</td>'
      f'<td><span class="chip {"tayyor" if ok else "kutish"}">{"Matn tayyor" if ok else "Matn yo‘q"}</span></td>'
      f'<td class="izoh">{iz}</td></tr>' for t,a,y,ok,iz in rows)
    return ('<div class="tbox"><table><thead><tr><th>Asar</th><th>Muallif</th><th>Yosh</th>'
            '<th>Matn</th><th>Izoh</th></tr></thead><tbody>'+tr+'</tbody></table></div>')

KIRISH = {
 "Davlat tanlovi · 10-14 yosh":"Davlat ro‘yxatidagi 40 ta asardan bazamizda bo‘lmagan 30 tasi. Yoshi kichik toifa — ilovaning bugungi asosiy foydalanuvchisi shular.",
 "Davlat tanlovi · 15-19 yosh":"Ellikta asarning bittasi ham bazamizda yo‘q edi. Ularni «14-16» va yangi «17-19» toifalariga ajratdim.",
 "Xalq dostonlari va eposlar":"Bazada bironta doston yo‘q edi. To‘liq matni ham, nasriy bayoni ham bo‘lsa — ikkalasi olinadi, nomiga «(nasriy bayoni)» qo‘shib qo‘yiladi.",
 "Navoiy va Sharq dostonlari":"Yozma dostonlar. Navoiyning uch asarining nasriy bayoni papkada tayyor turibdi — o‘smir uchun aynan o‘shalari olinadi.",
 "O‘zbek klassikasi":"Eng katta bo‘shliq shu yerda edi: Qodiriy, Cho‘lpon, Oybek — bittasi ham yo‘q edi.",
 "Jahon klassikasi":"Bazada sarguzasht asarlari ko‘p, jahon adabiyotining tayanch asarlari yo‘q. Tarjima bo‘lgani uchun har biriga bir yosh qo‘shildi.",
 "Shaxsiy rivojlanish":"Yo‘nalish umuman yo‘q edi. Tez boyish va'da qiladigan kitoblarni ataylab tanlamadim — o‘smirga ular emas, mehnat va odat haqidagilari kerak.",
 "Diniy-ma'rifiy":"Yangi yo‘nalish. Qisqa risolalardan boshlanadi — «Keksalarni e'zozlash», «Yolg‘on», «Isrof» kabi bir mavzuga bag‘ishlangan kichik kitoblar o‘smirga oson kiradi. <b>Bu bo‘limdagi kitoblardan test tuzilmaydi</b> — AI diniy matnda xato qilishi mumkin.",
}

jami = sum(len(r) for _, r in FL.SECTIONS)
tay  = sum(1 for _, r in FL.SECTIONS for x in r if x[3])
d1113 = sum(1 for _, r in FL.SECTIONS for x in r if x[2].startswith(('9','11','10','7')))
d1719 = sum(1 for _, r in FL.SECTIONS for x in r if x[2].startswith('17'))

secs = "\n".join(
  f'''<section>
  <div class="sechead"><h2>{nom}</h2><div class="count">{len(rows)} ta asar · matni tayyor {sum(1 for x in rows if x[3])} ta</div></div>
  <p class="kirish">{KIRISH[nom]}</p>
  {tbl(rows)}
</section>''' for nom, rows in FL.SECTIONS)

html = f'''<title>Bilig kutubxonasi ro‘yxati</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,400;7..72,600;7..72,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">

<header>
  <div class="eyebrow">Bilig AI · kitob bazasini kengaytirish · yakuniy ro‘yxat</div>
  <h1>Bazaga qo‘shiladigan kitoblar</h1>
  <p class="lead">Davlat tanlovi ro‘yxati, xalq dostonlari va to‘rt yo‘nalish bir ro‘yxatga jamlandi. Har bir asar kompyuteringizdagi «Mutolaa Word» papkasi bo‘yicha tekshirildi: matni bormi yoki kutish ro‘yxatiga tushadimi.</p>
  <div class="meta"><span>2026-yil 1-sentabr</span><span>Manba: gov.uz ro‘yxati · «Mutolaa Word 28.08.2026» papkasi (3 407 fayl) · Bilig AI bazasi (130 asar)</span></div>
</header>

<section>
  <div class="jam">
    <div><b>{jami}</b><span>Qo‘shiladigan asar</span></div>
    <div><b>{tay}</b><span>Matni papkada tayyor</span></div>
    <div><b>{jami-tay}</b><span>Kutish ro‘yxati</span></div>
    <div><b>{130+jami}</b><span>Bazadagi umumiy son</span></div>
  </div>
  <div class="note">
    <p><b>Eng katta yangilik:</b> matn masalasi hal bo‘ldi. Papkangizda 3 407 ta Word fayli bor va ro‘yxatdagi {tay} ta asarning matni o‘sha yerda turibdi — hech narsani qidirishning hojati yo‘q. Faqat 33 tasi topilmadi.</p>
    <p><b>Papkadagi fayl nomida janr ham yozilgan</b> (doston, diniy-ma'rifiy, shaxsiy rivojlanish…) — shu tufayli tanlash aniq bo‘ldi: papkada 48 ta doston, 63 ta diniy-ma'rifiy va 88 ta shaxsiy rivojlanish kitobi bor ekan.</p>
  </div>
</section>

{secs}

<section>
  <h2>Kitob pasportini kengaytirish<span class="sub">Siz aytgan mulohaza bo‘yicha taklif</span></h2>
  <p class="kirish">Haqsiz: hozirgi chegara bilan kelajakda yangi test kerak bo‘lganda kitobni boshqatdan o‘qishga to‘g‘ri keladi. Yechim — pasportga asarning voqealar tafsilotini yozib qo‘yish. Shunda yangi test uchun kitob emas, pasportning o‘zi yetadi.</p>
  <div class="pasport">
    <div><h4>Qisqacha mazmun</h4><p><span class="eski">1 000 belgi</span><span class="yangi">3 000 belgi</span></p></div>
    <div><h4>Asar g‘oyasi</h4><p><span class="eski">200 belgi</span><span class="yangi">500 belgi</span></p></div>
    <div><h4>Xulosa</h4><p><span class="eski">qisqa</span><span class="yangi">800 belgi</span></p></div>
    <div><h4>Qahramonlar</h4><p><span class="eski">faqat ism</span><span class="yangi">har biriga bir jumla ta'rif</span></p></div>
    <div><h4>Voqealar tafsiloti <span class="yangi">yangi</span></h4><p>Asarning 20-40 ta asosiy epizodi ketma-ketligi bilan. Kelajakdagi barcha yangi testlar shundan tuziladi.</p></div>
    <div><h4>Muhim parchalar <span class="yangi">yangi</span></h4><p>Asl matndan 5-8 ta muhim jumla. Ovozli xulosani baholash va AI ustoz savoli uchun kerak bo‘ladi.</p></div>
  </div>
  <div class="note">
    <p>Xarajat: pasport uch barobar kattalashadi, bu bitta kitobga 250 so‘m o‘rniga 600 so‘m degani. 181 ta kitob — 110 ming so‘m atrofida. Bazadagi eski 130 ta kitobni ham shu andaza bo‘yicha qayta ishlash mumkin, lekin buni keyinga qoldirsak bo‘ladi.</p>
  </div>
</section>

<section>
  <h2>Ish tartibi<span class="sub">To‘rt to‘lqin</span></h2>
  <div class="steps">
    <div class="step"><div class="no">1</div><div>
      <h3>Kichik yosh — 11-13 · taxminan 40 ta kitob</h3>
      <p>Davlat ro‘yxatining 10-14 qismi va yengil kiradigan dostonlar: «Ravshan», «Rustamxon», «Avazxon», «Malika ayyor». Bular ilovaning bugungi foydalanuvchisiga darrov ko‘rinadi.</p>
    </div></div>
    <div class="step"><div class="no">2</div><div>
      <h3>O‘rta yosh — 14-16 · taxminan 70 ta kitob</h3>
      <p>«O‘tkan kunlar», «Alpomish», jahon klassikasi, shaxsiy rivojlanish va diniy-ma'rifiy kitoblarning katta qismi shu bosqichda kiradi.</p>
    </div></div>
    <div class="step"><div class="no">3</div><div>
      <h3>Yangi «17-19» toifasi · taxminan 40 ta kitob</h3>
      <p>Avval ilovada yangi yosh toifasi ochiladi (bu kod ishi, kichik hajmli), keyin unga mos asarlar to‘ldiriladi: «Kecha va kunduz», «Ufq», «Ilohiy komediya», «Baxtiyor oila».</p>
    </div></div>
    <div class="step"><div class="no">4</div><div>
      <h3>Kutish ro‘yxati · 33 ta kitob</h3>
      <p>Matni papkada yo‘q. Ular alohida saqlanadi; matni qo‘lga kirgan sayin qo‘shib boriladi.</p>
    </div></div>
  </div>
</section>

<section>
  <h2>Diniy kitoblar uchun alohida qoida<span class="sub">Siz belgilagan shart</span></h2>
  <div class="note">
    <p><b>Diniy-ma'rifiy bo‘limdagi kitoblardan test tuzilmaydi.</b> Sabab aniq: AI diniy matnni talqin qilishda xato qilishi mumkin, xato savol esa bolaga noto‘g‘ri bilim beradi.</p>
    <p>O‘rniga bola o‘qigan aniq parchadan kelib chiqadigan <b>ochiq savol</b> beriladi. Ota-ona xohlasa, testni o‘zi tuzib qo‘shishi mumkin.</p>
  </div>
</section>

<footer>Bilig AI · yakuniy kitob ro‘yxati · 2026-yil 1-sentabr. Yosh chegaralari taklif tariqasida qo‘yildi — oxirgi so‘z sizniki. Kichik hajmli ertak, hikoya va masallar ro‘yxatga kiritilmadi.</footer>

</div>'''
open('yakuniy-royxat.html','w',encoding='utf-8').write(html)
print('OK', jami, tay)
