# -*- coding: utf-8 -*-
import json, gen2, html as H
CSS = gen2.CSS + """
.kirish{font-family:Literata,Georgia,serif; font-size:16.5px; color:var(--ink-soft); max-width:68ch}
.book{border:1px solid var(--line); background:var(--surface)}
.bhead{padding:22px 24px; border-bottom:1px solid var(--line); display:flex; flex-wrap:wrap; gap:6px 16px; align-items:baseline}
.bhead h3{font-family:Literata,Georgia,serif; font-size:22px; margin:0; font-weight:700}
.bhead .au{color:var(--ink-soft); font-size:14px}
.bhead .band{margin-left:auto; font-size:12px; font-weight:600; color:var(--accent); background:var(--accent-soft); padding:3px 10px; border-radius:2px; white-space:nowrap}
.fields{display:grid; grid-template-columns:repeat(auto-fit,minmax(280px,1fr)); gap:1px; background:var(--line-soft)}
.f{background:var(--surface); padding:18px 24px}
.f.wide{grid-column:1/-1}
.f h4{margin:0 0 8px; font-size:11.5px; letter-spacing:.1em; text-transform:uppercase; color:var(--ink-faint); font-weight:600}
.f p{font-size:14.5px; color:var(--ink); line-height:1.65}
.f .len{float:right; font-size:11px; color:var(--ink-faint); font-variant-numeric:tabular-nums; letter-spacing:0; text-transform:none}
ol.ev{margin:0; padding-left:20px; display:flex; flex-direction:column; gap:6px}
ol.ev li{font-size:14px; color:var(--ink-soft)}
.quote{border-left:2px solid var(--mut); padding:2px 0 2px 14px; margin:0 0 12px; font-family:Literata,Georgia,serif; font-size:14.5px; color:var(--ink-soft)}
.q{background:var(--raised); border:1px solid var(--line); padding:16px 18px; display:flex; flex-direction:column; gap:8px}
.q .qq{font-weight:600; font-size:15px}
.q ul{margin:0; padding-left:18px; display:flex; flex-direction:column; gap:4px}
.q li{font-size:14px; color:var(--ink-soft)}
.q li.ok{color:var(--bor); font-weight:600}
.qs{display:flex; flex-direction:column; gap:12px; padding:18px 24px}
.yangi{color:var(--bor); font-weight:600; font-size:11px; letter-spacing:.06em; margin-left:6px}
"""

def e(s): return H.escape(str(s))

d1 = json.load(open('../book_out2/malika-husnobod-dostoni.json', encoding='utf-8'))
d2 = json.load(open('../book_out2/101-ulug-sahobiy.json', encoding='utf-8'))

def fields(p, extra=""):
    ev = "".join("<li>%s</li>" % e(x) for x in p['events'])
    qt = "".join('<p class="quote">%s</p>' % e(x) for x in p['quotes'])
    return f'''<div class="fields">
 <div class="f"><h4>Yosh toifasi</h4><p>{e(p['age_band'])}</p></div>
 <div class="f"><h4>Mavzular</h4><p>{e(", ".join(p['topics']))}</p></div>
 <div class="f"><h4>Kayfiyati · murakkabligi</h4><p>{e(p['mood'])} · {e(p['difficulty'])}</p></div>
 <div class="f wide"><h4>G‘oyasi<span class="len">{len(p['theme'])} belgi</span></h4><p>{e(p['theme'])}</p></div>
 <div class="f wide"><h4>Qisqacha mazmuni<span class="len">{len(p['summary'])} belgi</span></h4><p>{e(p['summary'])}</p></div>
 <div class="f wide"><h4>Qahramonlar</h4><p>{e(p['characters'])}</p></div>
 <div class="f wide"><h4>Xulosasi</h4><p>{e(p['conclusion'])}</p></div>
 <div class="f wide"><h4>Kimga mos</h4><p>{e(p['for_whom'])}</p></div>
 <div class="f wide"><h4>Voqealar tafsiloti<span class="yangi">YANGI</span><span class="len">{len(p['events'])} band</span></h4><ol class="ev">{ev}</ol></div>
 <div class="f wide"><h4>Muhim parchalar<span class="yangi">YANGI</span><span class="len">{len(p['quotes'])} ta</span></h4>{qt}</div>
 {extra}
</div>'''

def testq(q):
    opts = "".join('<li class="%s">%s</li>' % ("ok" if o == q['answer'] else "", e(o)) for o in q['options'])
    return f'<div class="q"><div class="qq">{e(q["question"])}</div><ul>{opts}</ul></div>'

t1 = "".join(testq(q) for q in d1['questions'][:3])
oq = "".join(f'<div class="q"><p class="quote">{e(q["context"])}</p><div class="qq">{e(q["question"])}</div></div>'
             for q in d2['talk_questions'][:3])

html = f'''<title>Yangi pasport namunasi</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,400;7..72,600;7..72,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">

<header>
  <div class="eyebrow">Bilig AI · kitob bazasi · namuna</div>
  <h1>Yangi pasport qanday chiqdi</h1>
  <p class="lead">Kengaytirilgan pasport va diniy kitob qoidasi ikkita haqiqiy kitobda sinab ko‘rildi. Quyida — AI chiqargan natijaning o‘zi, hech narsa tahrirlanmagan.</p>
  <div class="meta"><span>2026-yil 1-sentabr</span><span>Bittasi 44 soniya, ikkinchisi 37 soniya vaqt oldi · jami 8 sentga tushdi</span></div>
</header>

<section>
  <h2>1. Oddiy kitob — test bilan<span class="sub">Xalq dostoni, 11-13 yosh</span></h2>
  <p class="kirish">Eski pasportda mazmun 1 000 belgi bilan cheklangan edi va voqealar ro‘yxati umuman yo‘q edi. Endi mazmun ikki barobar to‘liq, ustiga 20 bandlik voqealar tafsiloti va asl matndan olingan parchalar qo‘shildi.</p>
  <div class="book">
    <div class="bhead"><h3>{e(d1['title'])}</h3><span class="au">{e(d1['author'])}</span><span class="band">{e(d1['passport']['age_band'])} yosh</span></div>
    {fields(d1['passport'])}
    <div class="qs"><h4 style="margin:0;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint)">Testdan uchta savol ({len(d1['questions'])} tadan)</h4>{t1}</div>
  </div>
</section>

<section>
  <h2>2. Diniy kitob — testsiz<span class="sub">Siz belgilagan qoida amalda</span></h2>
  <p class="kirish">Bu kitobga test tuzilmadi. AI matnni sharhlamadi va hukm chiqarmadi — u kitobdan parchani aynan ko‘chirib oldi va faqat shu parchaga tayangan ochiq savol berdi. Savolning to‘g‘ri javobi yo‘q: bola o‘z fikrini aytadi.</p>
  <div class="book">
    <div class="bhead"><h3>{e(d2['title'])}</h3><span class="au">{e(d2['author'])}</span><span class="band">{e(d2['passport']['age_band'])} yosh · testsiz</span></div>
    {fields(d2['passport'])}
    <div class="qs"><h4 style="margin:0;font-size:11.5px;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-faint)">Ochiq savollardan uchtasi (5 tadan)</h4>{oq}</div>
  </div>
</section>

<section>
  <h2>Ma'qul bo‘lsa — nima bo‘ladi<span class="sub">Keyingi qadam</span></h2>
  <div class="note">
    <p>Papkangizdan <b>141 ta kitob matni</b> ajratib olindi va navbatda turibdi. Siz ma'qullaganingizdan keyin hammasi shu andaza bo‘yicha ishlanadi — taxminan 6-7 dollar va bir necha soat vaqt oladi. Har bir kitob avtomatik tekshiruvdan o‘tadi: chiqmagani chetga suriladi va qo‘lda ko‘riladi.</p>
    <p>Undan keyin ikkita ish qoladi: yangi «17-19» yosh toifasini ilovaga qo‘shish va tayyor kitoblarni bazaga ko‘chirish.</p>
  </div>
</section>

<footer>Bilig AI · pasport namunasi · 2026-yil 1-sentabr. Matnlar AI chiqarganidek, o‘zgartirilmagan holda ko‘rsatilgan.</footer>

</div>'''
open('namuna-pasport.html','w',encoding='utf-8').write(html)
print('OK')
