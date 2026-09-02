# -*- coding: utf-8 -*-
import gen
g1, g2, rows = gen.g1, gen.g2, gen.rows
h = gen.hisob
BOR, MUT, YOQ, NOA = gen.BOR, gen.MUT, gen.YOQ, gen.NOA

CSS = """
:root{
  --paper:#F2F4F1; --surface:#FFFFFF; --raised:#FAFBF9;
  --ink:#151F1C; --ink-soft:#4E5C57; --ink-faint:#77837E;
  --line:#DBE0DB; --line-soft:#E9EDE9;
  --accent:#23527C; --accent-soft:#E4ECF3;
  --bor:#2C6A4E; --bor-bg:#E1EEE7;
  --mut:#8A5712; --mut-bg:#F5EAD6;
  --yoq:#982C2C; --yoq-bg:#F6E3E3;
  --noa:#57565F; --noa-bg:#E9E9ED;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --paper:#111715; --surface:#19211F; --raised:#1E2725;
    --ink:#E9EEEB; --ink-soft:#A6B2AD; --ink-faint:#7C8781;
    --line:#2B3532; --line-soft:#232C2A;
    --accent:#89B6DE; --accent-soft:#1C2A36;
    --bor:#7ECBA3; --bor-bg:#1B3128;
    --mut:#E0B461; --mut-bg:#332913;
    --yoq:#E58B8B; --yoq-bg:#341D1D;
    --noa:#B0B0BA; --noa-bg:#26262B;
  }
}
:root[data-theme="dark"]{
    --paper:#111715; --surface:#19211F; --raised:#1E2725;
    --ink:#E9EEEB; --ink-soft:#A6B2AD; --ink-faint:#7C8781;
    --line:#2B3532; --line-soft:#232C2A;
    --accent:#89B6DE; --accent-soft:#1C2A36;
    --bor:#7ECBA3; --bor-bg:#1B3128;
    --mut:#E0B461; --mut-bg:#332913;
    --yoq:#E58B8B; --yoq-bg:#341D1D;
    --noa:#B0B0BA; --noa-bg:#26262B;
}
*{box-sizing:border-box}
body{
  margin:0; background:var(--paper); color:var(--ink);
  font-family:"IBM Plex Sans","Helvetica Neue",Arial,sans-serif;
  font-size:16px; line-height:1.6; -webkit-font-smoothing:antialiased;
}
.wrap{max-width:1040px; margin:0 auto; padding:48px 24px 96px; display:flex; flex-direction:column; gap:56px}
header{display:flex; flex-direction:column; gap:18px; border-bottom:2px solid var(--ink); padding-bottom:32px}
.eyebrow{font-size:12px; letter-spacing:.14em; text-transform:uppercase; color:var(--accent); font-weight:600}
h1{
  font-family:Literata,Georgia,serif; font-weight:700; font-size:clamp(30px,5vw,46px);
  line-height:1.15; margin:0; text-wrap:balance; letter-spacing:-.01em;
}
.lead{font-family:Literata,Georgia,serif; font-size:18px; color:var(--ink-soft); max-width:62ch; margin:0}
.meta{font-size:13px; color:var(--ink-faint); display:flex; flex-wrap:wrap; gap:6px 18px}
.stats{display:grid; grid-template-columns:repeat(auto-fit,minmax(180px,1fr)); gap:2px; background:var(--line); border:1px solid var(--line)}
.stat{background:var(--surface); padding:22px 20px; display:flex; flex-direction:column; gap:6px}
.stat .n{font-family:Literata,Georgia,serif; font-size:38px; font-weight:700; line-height:1; font-variant-numeric:tabular-nums}
.stat .k{font-size:13px; color:var(--ink-soft)}
.stat.s-bor .n{color:var(--bor)} .stat.s-mut .n{color:var(--mut)} .stat.s-yoq .n{color:var(--yoq)}
section{display:flex; flex-direction:column; gap:20px}
h2{font-family:Literata,Georgia,serif; font-size:26px; font-weight:600; margin:0; letter-spacing:-.01em; text-wrap:balance}
h2 .sub{display:block; font-family:"IBM Plex Sans",sans-serif; font-size:13px; font-weight:500; color:var(--ink-faint); letter-spacing:.02em; margin-top:6px}
h3{font-family:Literata,Georgia,serif; font-size:18px; margin:0 0 6px; font-weight:600}
p{margin:0; max-width:70ch}
.note{background:var(--raised); border:1px solid var(--line); border-left:3px solid var(--accent); padding:18px 20px; display:flex; flex-direction:column; gap:8px}
.note p{color:var(--ink-soft); font-size:15px}
.tbox{overflow-x:auto; border:1px solid var(--line); background:var(--surface)}
table{border-collapse:collapse; width:100%; min-width:760px; font-size:14.5px}
thead th{
  text-align:left; font-size:11.5px; letter-spacing:.1em; text-transform:uppercase;
  color:var(--ink-faint); font-weight:600; padding:12px 14px; border-bottom:1px solid var(--line);
  background:var(--raised); position:sticky; top:0;
}
td{padding:11px 14px; border-bottom:1px solid var(--line-soft); vertical-align:top}
tbody tr:last-child td{border-bottom:none}
tbody tr:hover td{background:var(--raised)}
.num{color:var(--ink-faint); font-variant-numeric:tabular-nums; width:38px}
.asar{font-family:Literata,Georgia,serif; font-weight:600; min-width:230px}
.mual{color:var(--ink-soft); white-space:nowrap}
.yosh{font-variant-numeric:tabular-nums; white-space:nowrap; font-weight:600}
.izoh{color:var(--ink-soft); font-size:13.5px; min-width:200px}
.chip{display:inline-block; white-space:nowrap; font-size:12px; font-weight:600; padding:3px 9px; border-radius:2px}
.chip.bor{color:var(--bor); background:var(--bor-bg)}
.chip.mut{color:var(--mut); background:var(--mut-bg)}
.chip.yoq{color:var(--yoq); background:var(--yoq-bg)}
.chip.noaniq{color:var(--noa); background:var(--noa-bg)}
.legend{display:flex; flex-wrap:wrap; gap:10px 22px; font-size:13.5px; color:var(--ink-soft)}
.legend span b{font-weight:600}
.cards{display:grid; grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); gap:16px}
.card{background:var(--surface); border:1px solid var(--line); padding:20px; display:flex; flex-direction:column; gap:8px}
.card p{font-size:14.5px; color:var(--ink-soft)}
.steps{display:flex; flex-direction:column; gap:0; border:1px solid var(--line); background:var(--surface)}
.step{display:grid; grid-template-columns:56px 1fr; gap:18px; padding:20px; border-bottom:1px solid var(--line-soft)}
.step:last-child{border-bottom:none}
.step .no{font-family:Literata,Georgia,serif; font-size:24px; font-weight:700; color:var(--accent); line-height:1.1}
.step p{font-size:14.5px; color:var(--ink-soft)}
footer{border-top:1px solid var(--line); padding-top:24px; font-size:13px; color:var(--ink-faint)}
@media (max-width:600px){ .wrap{padding:32px 16px 64px; gap:44px} .step{grid-template-columns:40px 1fr; gap:12px} }
"""

def sec(nom, sarlavha, sub, data):
    return f'''<section>
<h2>{sarlavha}<span class="sub">{sub}</span></h2>
<div class="tbox"><table>
<thead><tr><th>№</th><th>Asar</th><th>Muallif</th><th>Holat</th><th>Taklif yosh</th><th>Izoh</th></tr></thead>
<tbody>
{rows(data)}
</tbody></table></div>
</section>'''

html = f'''<title>Yosh kitobxon ro‘yxati</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Literata:opsz,wght@7..72,400;7..72,600;7..72,700&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>{CSS}</style>
<div class="wrap">

<header>
  <div class="eyebrow">Davlat tanlovi · 2026-yil mavsumi</div>
  <h1>«Yosh kitobxon» ro‘yxati va Bilig AI bazasi</h1>
  <p class="lead">Tanlovning 10-14 va 15-19 yosh toifalari uchun e'lon qilingan 90 ta asar bazamiz bilan bittalab solishtirildi. Har bir asar uchun: bizda bormi, Mutolaa'da bormi va qaysi yoshga mos.</p>
  <div class="meta"><span>2026-yil 1-sentabr</span><span>Manba: gov.uz e'loni · mutolaa.com katalogi · Bilig AI kitob bazasi (130 ta asar)</span></div>
</header>

<section>
  <div class="stats">
    <div class="stat"><div class="n">90</div><div class="k">Ro‘yxatdagi asar (40 + 50)</div></div>
    <div class="stat s-bor"><div class="n">{h(g1,BOR)+h(g2,BOR)}</div><div class="k">Bazamizda allaqachon bor</div></div>
    <div class="stat s-mut"><div class="n">{h(g1,MUT)+h(g2,MUT)}</div><div class="k">Mutolaa'da bor — darhol olish mumkin</div></div>
    <div class="stat s-yoq"><div class="n">{h(g1,YOQ)+h(g2,YOQ)+h(g1,NOA)+h(g2,NOA)}</div><div class="k">Topilmadi yoki aniqlanmadi</div></div>
  </div>
  <div class="legend">
    <span><b>Bazada bor</b> — ilovada mavjud</span>
    <span><b>Mutolaa'da bor</b> — matni tayyor, bazaga olinadi</span>
    <span><b>Topilmadi</b> — kelajakda to‘ldiriladi</span>
    <span><b>Aniqlanmadi</b> — qaysi nashr ekani noaniq</span>
  </div>
  <div class="note">
    <p><b>Eng muhim raqam:</b> davlat ro‘yxatining 90 ta asaridan bazamizda atigi 10 tasi bor — hammasi 10-14 toifasidan. <b>15-19 yosh toifasidagi 50 ta asardan bittasi ham yo‘q.</b> Buning sababi oddiy: bazamiz shu kungacha 14 yoshgacha bo‘lgan bolaga qurilgan edi.</p>
    <p>Yaxshi xabar: ro‘yxatdagi 62 ta asarning matni Mutolaa'da turibdi — ya'ni ro‘yxatning uchdan ikki qismini qidirmasdan, tayyor manbadan olsa bo‘ladi.</p>
  </div>
</section>

{sec("g1","10-14 yosh toifasi","40 ta asar · bazada 10 ta · Mutolaa'da 23 ta · topilmadi 7 ta", g1)}

{sec("g2","15-19 yosh toifasi","50 ta asar · bazada 0 ta · Mutolaa'da 39 ta · topilmadi yoki noaniq 11 ta", g2)}

<section>
  <h2>Uchta masala — qaror sizniki<span class="sub">Ro‘yxatni ko‘chirishdan oldin hal qilinishi kerak</span></h2>
  <div class="cards">
    <div class="card">
      <h3>She'riy to‘plamlar</h3>
      <p>Ro‘yxatda 8 ta she'riy to‘plam bor (Muhammad Yusuf, Po‘lat Mo‘min, Abdulla Oripov…). She'rga syujet savoli tuzib bo‘lmaydi. Taklifim: ular bazaga kiradi, lekin testsiz — «o‘qildi» belgisi va bitta og‘zaki savol bilan.</p>
    </div>
    <div class="card">
      <h3>Kitob bo‘lmaganlari</h3>
      <p>«Britannika ensiklopediyasi» va «Yoshlik» jurnalining 2026-yil sonlari — boshdan-oxir o‘qiladigan asar emas. Taklifim: bazaga kiritilmasin.</p>
    </div>
    <div class="card">
      <h3>Kattalar mavzusi</h3>
      <p>15-19 toifasida 24 ta asarni 17-19 yoshga surdim: qamoq, qatl, kattalar munosabatlari, diniy-falsafiy iqror kabi mavzular bor. 13 yoshli bola ro‘yxatda ularni ko‘rmasligi kerak.</p>
    </div>
  </div>
</section>

<section>
  <h2>Xalq dostonlari — bazada bitta ham yo‘q<span class="sub">Ro‘yxatdagi 4 ta doston va undan keyingisi</span></h2>
  <p>Bazadagi 130 ta asar orasida bironta xalq dostoni yo‘q. Davlat ro‘yxati to‘rttasini nomma-nom ko‘rsatadi: «Malika Husnobod», «Ravshan», «Yunus va Misqol pari» (10-14) va «Go‘ro‘g‘lining tug‘ilishi» (15-19). Uchtasi Mutolaa'da turibdi.</p>
  <div class="note">
    <p><b>Nozik joyi:</b> dostonning to‘liq matni — she'riy, uzun va o‘smir uchun og‘ir. Bolalar uchun qayta hikoya qilingan nashrini olish kerak. Qaysi nashrni olishimizni siz aytasiz — bu adabiyotshunoslik qarori, men o‘zim hal qilmayman.</p>
  </div>
</section>

<section>
  <h2>Taklif etilayotgan ish tartibi<span class="sub">Nimadan boshlaymiz</span></h2>
  <div class="steps">
    <div class="step"><div class="no">1</div><div>
      <h3>10-14 toifasini yopamiz — 23 ta asar</h3>
      <p>Mutolaa'da matni bor, yoshi bizning bugungi qamrovimizga to‘g‘ri keladi. Har biriga pasport, test va muqova tayyorlanadi. Shundan keyin bu toifada tanlov ro‘yxatining 33 tasi bizda bo‘ladi.</p>
    </div></div>
    <div class="step"><div class="no">2</div><div>
      <h3>Yangi «17-19» toifasi ochiladi</h3>
      <p>Ilovaning eng katta toifasi hozir 14-16. Yangi toifa qo‘shilgach, 15-19 ro‘yxatidagi 39 ta asarni ikkiga ajratib kiritamiz: 15 tasi 14-16 ga, 24 tasi 17-19 ga.</p>
    </div></div>
    <div class="step"><div class="no">3</div><div>
      <h3>Dostonlar alohida to‘lqin</h3>
      <p>Siz nashrni tanlaganingizdan keyin — 4 ta doston, keyin ro‘yxatdan tashqari «Alpomish» va «Kuntug‘mish» ham qaraladi.</p>
    </div></div>
    <div class="step"><div class="no">4</div><div>
      <h3>Topilmagan 14 ta asar — kutish ro‘yxatida</h3>
      <p>Ular na bazamizda, na Mutolaa'da. Matni qo‘lga kirgan sayin qo‘shib boriladi. Bu ro‘yxat yo‘qolmasligi uchun alohida saqlab qo‘yiladi.</p>
    </div></div>
  </div>
</section>

<footer>Bilig AI · kitob bazasi hisoboti · tekshirilgan sana: 2026-yil 1-sentabr. Mutolaa'dagi mavjudlik sayt katalogi va davlat e'lonidagi izohlar bo‘yicha aniqlandi; she'riy to‘plamlarning bir qismi katalogda umumiy nom bilan turgani uchun qo‘lda tasdiqlash kerak bo‘lishi mumkin.</footer>

</div>'''
open('yosh-kitobxon-hisobot.html','w',encoding='utf-8').write(html)
print('OK', len(html))
