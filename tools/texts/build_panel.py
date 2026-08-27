# -*- coding: utf-8 -*-
"""Matn tahrir panelini (HTML) tuzadi.

Ishlatish (loyiha ildizidan):
    python3 tools/texts/extract_texts.py     # avval matnlarni yig‘ish
    python3 tools/texts/build_panel.py       # keyin panelni tuzish

Natija: tools/texts/panel.html — Artifact sifatida chiqariladi.
Panel o‘z ichida saqlaydi: tahrirlangan matnlar sahifaning o‘ziga
yoziladi, shuning uchun bir necha kun davomida to‘xtab-to‘xtab
ishlash mumkin.
"""
import io
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "tools", "texts", "texts.json")
OUT = os.path.join(ROOT, "tools", "texts", "panel.html")

CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=Nunito:wght@400;600;700;800&display=swap');

:root {
  --paper: #FFFFFF;
  --ground: #F4F7FB;
  --sunk: #EAEFF7;
  --line: #DFE6F0;
  --line-soft: #EDF1F7;
  --ink: #101827;
  --ink-soft: #4A5A70;
  --muted: #7A8BA3;
  --brand: #4E8EF7;
  --brand-deep: #2F63D6;
  --brand-wash: #E9F1FF;
  --done: #10B981;
  --done-wash: #E3F7EF;
  --gold: #D9880B;
  --shadow: 0 1px 2px rgba(16,24,39,.05), 0 8px 24px -14px rgba(16,24,39,.28);
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --paper: #161C26;
    --ground: #0D1219;
    --sunk: #1D2531;
    --line: #29323F;
    --line-soft: #212934;
    --ink: #E7EDF6;
    --ink-soft: #AEBCCE;
    --muted: #7E8EA4;
    --brand: #6FA4FA;
    --brand-deep: #9CC2FD;
    --brand-wash: #1B2739;
    --done: #34D399;
    --done-wash: #14291F;
    --gold: #E8A83C;
    --shadow: 0 1px 2px rgba(0,0,0,.4), 0 10px 26px -16px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"] {
  --paper: #161C26;
  --ground: #0D1219;
  --sunk: #1D2531;
  --line: #29323F;
  --line-soft: #212934;
  --ink: #E7EDF6;
  --ink-soft: #AEBCCE;
  --muted: #7E8EA4;
  --brand: #6FA4FA;
  --brand-deep: #9CC2FD;
  --brand-wash: #1B2739;
  --done: #34D399;
  --done-wash: #14291F;
  --gold: #E8A83C;
  --shadow: 0 1px 2px rgba(0,0,0,.4), 0 10px 26px -16px rgba(0,0,0,.7);
}

* { box-sizing: border-box; }
body {
  margin: 0; background: var(--ground); color: var(--ink);
  font-family: 'IBM Plex Sans', -apple-system, BlinkMacSystemFont, sans-serif;
  font-size: 14px; line-height: 1.5;
}
button { font: inherit; cursor: pointer; }
:focus-visible { outline: 2px solid var(--brand); outline-offset: 2px; border-radius: 4px; }

/* ---------- boshqaruv paneli ---------- */
.bar {
  position: sticky; top: 0; z-index: 20; background: var(--paper);
  border-bottom: 1px solid var(--line); padding: 14px 20px 12px;
}
.bar-in { max-width: 1180px; margin: 0 auto; display: flex; flex-direction: column; gap: 12px; }
.bar-top { display: flex; align-items: baseline; gap: 14px; flex-wrap: wrap; }
h1 { font-size: 17px; font-weight: 700; margin: 0; letter-spacing: -.01em; }
.count {
  font-size: 12.5px; font-weight: 600; color: var(--muted);
  font-variant-numeric: tabular-nums;
}
.count b { color: var(--done); }
.meter { flex: 1; min-width: 120px; height: 5px; border-radius: 99px; background: var(--sunk); overflow: hidden; }
.meter i { display: block; height: 100%; background: var(--done); border-radius: 99px; transition: width .3s; }

.tools { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.tools input[type="search"], .tools select {
  font: inherit; color: var(--ink); background: var(--ground);
  border: 1px solid var(--line); border-radius: 8px; padding: 7px 10px;
}
.tools input[type="search"] { flex: 1; min-width: 150px; }
.chk { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: var(--ink-soft); user-select: none; }
.btn {
  border: 1px solid var(--line); background: var(--paper); color: var(--ink);
  border-radius: 8px; padding: 7px 13px; font-size: 13px; font-weight: 600;
}
.btn:hover { border-color: var(--brand); color: var(--brand-deep); }
.btn-go { background: var(--brand); border-color: var(--brand); color: #fff; }
.btn-go:hover { background: var(--brand-deep); border-color: var(--brand-deep); color: #fff; }
.btn:disabled { opacity: .45; cursor: default; }

/* ---------- ro‘yxat ---------- */
main { max-width: 1180px; margin: 0 auto; padding: 18px 20px 130px; }
.grp { margin-bottom: 26px; }
.grp-head {
  position: sticky; top: 118px; z-index: 10;
  display: flex; align-items: center; gap: 10px;
  background: var(--ground); padding: 8px 0 8px;
  font-size: 11.5px; font-weight: 600; text-transform: uppercase;
  letter-spacing: .09em; color: var(--muted);
}
.grp-head::after { content: ""; flex: 1; height: 1px; background: var(--line); }

.row {
  display: grid; grid-template-columns: 4px 1fr 1fr; gap: 0;
  background: var(--paper); border: 1px solid var(--line);
  border-radius: 10px; overflow: hidden; margin-bottom: 8px;
  box-shadow: var(--shadow);
}
.row + .row { margin-top: 0; }
.stripe { background: var(--line); }
.row.is-draft .stripe { background: var(--brand); }
.row.is-saved .stripe { background: var(--done); }

.was { padding: 13px 16px; border-right: 1px solid var(--line-soft); min-width: 0; }
.was p {
  margin: 0; font-family: Nunito, sans-serif; font-size: 14.5px;
  line-height: 1.45; color: var(--ink); overflow-wrap: anywhere;
}
.where {
  display: flex; align-items: center; gap: 8px; margin-top: 8px;
  font-size: 11px; color: var(--muted);
}
.copy {
  border: 0; background: none; color: var(--brand-deep); padding: 0;
  font-size: 11px; font-weight: 600;
}
.warn {
  background: var(--gold); color: #fff; border-radius: 99px;
  padding: 1px 7px; font-size: 10.5px; font-weight: 600; white-space: nowrap;
}
.copy:hover { text-decoration: underline; }

.now { padding: 9px 12px; display: flex; }
.now textarea {
  flex: 1 1 auto; min-width: 0; width: 100%;
  border: 1px solid transparent; background: var(--ground);
  border-radius: 8px; padding: 9px 11px; resize: vertical; min-height: 62px;
  font-family: Nunito, sans-serif; font-size: 14.5px; line-height: 1.45;
  color: var(--ink);
}
.now textarea::placeholder { color: var(--muted); font-family: 'IBM Plex Sans', sans-serif; font-size: 13px; }
.now textarea:focus { border-color: var(--brand); background: var(--paper); outline: none; }
.row.is-saved .now textarea { background: var(--done-wash); }

.empty { text-align: center; padding: 60px 20px; color: var(--muted); }

/* ---------- saqlash paneli ---------- */
.dock {
  position: fixed; left: 0; right: 0; bottom: 0; z-index: 30;
  background: var(--paper); border-top: 1px solid var(--line);
  padding: 12px 20px; box-shadow: 0 -8px 24px -18px rgba(16,24,39,.5);
}
.dock-in {
  max-width: 1180px; margin: 0 auto; display: flex; align-items: center;
  gap: 14px; flex-wrap: wrap;
}
.dock-msg { font-size: 13px; color: var(--ink-soft); flex: 1; min-width: 160px; }
.dock-msg b { color: var(--ink); font-variant-numeric: tabular-nums; }
.pill {
  display: inline-block; padding: 3px 9px; border-radius: 99px;
  font-size: 11.5px; font-weight: 600; background: var(--brand-wash); color: var(--brand-deep);
}
.pill.ok { background: var(--done-wash); color: var(--done); }

@media (max-width: 720px) {
  .row { grid-template-columns: 4px 1fr; }
  .was { border-right: 0; border-bottom: 1px solid var(--line-soft); }
  .grp-head { top: 150px; }
}
@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; animation: none !important; }
}
"""

CODE = r"""
(function () {
  var DATA = JSON.parse(document.getElementById('pnl-data').textContent);
  var items = DATA.items || [];
  var saved = DATA.edits || {};        // sahifaga yozilgan (tasdiqlangan) tahrirlar
  var draft = {};                      // hali saqlanmagan
  var LSKEY = 'bilig-matn-qoralama';

  try {
    var raw = localStorage.getItem(LSKEY);
    if (raw) draft = JSON.parse(raw) || {};
  } catch (e) { draft = {}; }

  var elApp = document.getElementById('app');
  var filterArea = '', filterQ = '', onlyLeft = false;

  function esc(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c];
    });
  }
  function valueOf(id) {
    if (Object.prototype.hasOwnProperty.call(draft, id)) return draft[id];
    return saved[id] || '';
  }
  function isDone(id) { return (valueOf(id) || '').trim().length > 0; }
  function draftCount() {
    var n = 0;
    for (var k in draft) {
      if ((draft[k] || '').trim() !== (saved[k] || '').trim()) n++;
    }
    return n;
  }

  function areas() {
    var seen = [], has = {};
    items.forEach(function (it) { if (!has[it.area]) { has[it.area] = 1; seen.push(it.area); } });
    return seen.sort();
  }

  function visible() {
    var q = filterQ.trim().toLowerCase();
    return items.filter(function (it) {
      if (filterArea && it.area !== filterArea) return false;
      if (onlyLeft && isDone(it.id)) return false;
      if (q) {
        var hay = (it.text + ' ' + it.area).toLowerCase();
        if (hay.indexOf(q) < 0) return false;
      }
      return true;
    });
  }

  function render() {
    var done = items.filter(function (it) { return isDone(it.id); }).length;
    var pct = items.length ? Math.round(done / items.length * 100) : 0;
    var list = visible();

    var groups = [], byArea = {};
    list.forEach(function (it) {
      if (!byArea[it.area]) { byArea[it.area] = []; groups.push(it.area); }
      byArea[it.area].push(it);
    });

    var html = '' +
      '<div class="bar"><div class="bar-in">' +
        '<div class="bar-top">' +
          '<h1>Bilig — ilova matnlari</h1>' +
          '<span class="count"><b>' + done + '</b> / ' + items.length + ' tahrirlandi</span>' +
          '<span class="meter"><i style="width:' + pct + '%"></i></span>' +
        '</div>' +
        '<div class="tools">' +
          '<input type="search" id="q" placeholder="Matn ichidan qidirish…" value="' + esc(filterQ) + '">' +
          '<select id="area"><option value="">Barcha bo‘limlar</option>' +
            areas().map(function (a) {
              return '<option value="' + esc(a) + '"' + (a === filterArea ? ' selected' : '') + '>' + esc(a) + '</option>';
            }).join('') +
          '</select>' +
          '<label class="chk"><input type="checkbox" id="left"' + (onlyLeft ? ' checked' : '') + '> Faqat tegilmaganlari</label>' +
          '<button class="btn" id="jump">Qolgan joydan davom etish</button>' +
        '</div>' +
      '</div></div>' +
      '<main>';

    if (!list.length) {
      html += '<p class="empty">Bu shartga mos matn topilmadi.</p>';
    }
    groups.forEach(function (area) {
      html += '<section class="grp"><h2 class="grp-head">' + esc(area) + '</h2>';
      byArea[area].forEach(function (it) {
        var v = valueOf(it.id);
        var cls = '';
        if (v.trim()) {
          cls = (Object.prototype.hasOwnProperty.call(draft, it.id) &&
                 draft[it.id].trim() !== (saved[it.id] || '').trim()) ? ' is-draft' : ' is-saved';
        }
        html += '' +
          '<article class="row' + cls + '" data-id="' + esc(it.id) + '">' +
            '<div class="stripe"></div>' +
            '<div class="was">' +
              '<p>' + esc(it.text) + '</p>' +
              '<div class="where"><span>' + esc(it.file) + '</span>' +
                (/\{[^}]+\}/.test(it.text)
                  ? '<span class="warn">{ } — o‘zgaruvchi, o‘z holida qoldiring</span>' : '') +
                '<button class="copy" data-copy="' + esc(it.id) + '">Asl matnni ko‘chirish</button>' +
              '</div>' +
            '</div>' +
            '<div class="now">' +
              '<textarea data-in="' + esc(it.id) + '" placeholder="Yangi matn…" rows="2">' + esc(v) + '</textarea>' +
            '</div>' +
          '</article>';
      });
      html += '</section>';
    });

    html += '</main>' +
      '<div class="dock"><div class="dock-in">' +
        '<span class="dock-msg" id="dockmsg"></span>' +
        '<button class="btn" id="revert">Saqlanmaganini bekor qilish</button>' +
        '<button class="btn btn-go" id="save">Saqlash</button>' +
      '</div></div>';

    elApp.innerHTML = html;
    wire();
    updateDock();
  }

  function updateDock() {
    var n = draftCount();
    var msg = document.getElementById('dockmsg');
    var btn = document.getElementById('save');
    var rev = document.getElementById('revert');
    if (!msg) return;
    if (n) {
      msg.innerHTML = '<span class="pill">' + n + ' ta o‘zgarish saqlanmagan</span>';
    } else if (DATA.savedAt) {
      msg.innerHTML = '<span class="pill ok">Saqlangan</span> <b>' + esc(DATA.savedAt) + '</b>';
    } else {
      msg.textContent = 'Hali hech narsa saqlanmagan.';
    }
    btn.disabled = !n;
    rev.disabled = !n;
  }

  function autosave() {
    try { localStorage.setItem(LSKEY, JSON.stringify(draft)); } catch (e) {}
  }

  function wire() {
    var q = document.getElementById('q');
    q.oninput = function () {
      filterQ = this.value;
      clearTimeout(wire._t);
      var pos = this.selectionStart;
      wire._t = setTimeout(function () {
        render();
        var nq = document.getElementById('q');
        nq.focus(); nq.setSelectionRange(pos, pos);
      }, 220);
    };
    document.getElementById('area').onchange = function () { filterArea = this.value; render(); };
    document.getElementById('left').onchange = function () { onlyLeft = this.checked; render(); };
    document.getElementById('jump').onclick = function () {
      var row = null, all = elApp.querySelectorAll('.row');
      for (var i = 0; i < all.length; i++) {
        if (!all[i].classList.contains('is-saved') && !all[i].classList.contains('is-draft')) { row = all[i]; break; }
      }
      if (!row) { alert('Barcha ko‘rinayotgan matnlar tahrirlangan.'); return; }
      row.scrollIntoView({ block: 'center', behavior: 'smooth' });
      var ta = row.querySelector('textarea');
      if (ta) setTimeout(function () { ta.focus(); }, 350);
    };

    elApp.addEventListener('input', function (e) {
      var id = e.target.getAttribute && e.target.getAttribute('data-in');
      if (!id) return;
      draft[id] = e.target.value;
      autosave();
      var row = e.target.closest('.row');
      var changed = (draft[id] || '').trim() !== (saved[id] || '').trim();
      row.classList.toggle('is-draft', changed && !!draft[id].trim());
      row.classList.toggle('is-saved', !changed && !!(saved[id] || '').trim());
      updateDock();
    });

    elApp.addEventListener('click', function (e) {
      var cid = e.target.getAttribute && e.target.getAttribute('data-copy');
      if (!cid) return;
      var it = items.filter(function (x) { return x.id === cid; })[0];
      var ta = elApp.querySelector('[data-in="' + cid + '"]');
      if (it && ta) { ta.value = it.text; ta.focus(); ta.dispatchEvent(new Event('input', { bubbles: true })); }
    });

    document.getElementById('revert').onclick = function () {
      if (!confirm('Saqlanmagan o‘zgarishlar o‘chiriladi. Davom etamizmi?')) return;
      draft = {}; autosave(); render();
    };
    document.getElementById('save').onclick = save;
  }

  function buildDoc(obj) {
    var css = document.getElementById('pnl-style').textContent;
    var code = document.getElementById('pnl-code').textContent;
    var json = JSON.stringify(obj).replace(/</g, '\\u003c');
    return '<!doctype html>\n<html lang="uz">\n<head>\n<meta charset="utf-8">\n' +
      '<meta name="viewport" content="width=device-width,initial-scale=1">\n' +
      '<title>Bilig matn ustaxonasi</title>\n' +
      '<style id="pnl-style">' + css + '</style>\n</head>\n<body>\n' +
      '<div id="app"></div>\n' +
      '<script type="application/json" id="pnl-data">' + json + '<\/script>\n' +
      '<script id="pnl-code">' + code + '<\/script>\n</body>\n</html>';
  }

  function save() {
    var btn = document.getElementById('save');
    btn.disabled = true; btn.textContent = 'Saqlanmoqda…';
    var next = {};
    for (var k in saved) next[k] = saved[k];
    for (var d in draft) {
      var v = (draft[d] || '').trim();
      if (v) next[d] = v; else delete next[d];
    }
    var stamp = new Date().toLocaleString('uz-UZ', {
      day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
    });
    var payload = { items: items, edits: next, savedAt: stamp };

    var ready = (typeof claude !== 'undefined' && claude && claude.use)
      ? claude.use('artifact')
      : Promise.resolve(null);
    ready.then(function (art) {
      if (!art) throw new Error('yoq');
      return art.publish(buildDoc(payload));
    }).then(function () {
      saved = next; draft = {}; autosave();
      DATA.savedAt = stamp;
      btn.textContent = 'Saqlash';
      render();
    }).catch(function (err) {
      btn.disabled = false; btn.textContent = 'Saqlash';
      var code = (err && err.code) || '';
      if (code === 'conflict') {
        alert('Kimdir sizdan oldin saqlab ulgurdi. Sahifani yangilang — o‘zgarishlaringiz shu qurilmada saqlanib turibdi.');
      } else {
        alert('Saqlab bo‘lmadi. Yozganlaringiz shu qurilmada saqlanib turibdi, keyinroq qayta urinib ko‘ring.');
      }
    });
  }

  window.addEventListener('beforeunload', function (e) {
    if (draftCount()) { e.preventDefault(); e.returnValue = ''; }
  });

  render();
})();
"""


def carry_over(items):
    """Chiqarilgan paneldagi tahrirlarni saqlab qolish.

        python3 tools/texts/build_panel.py --merge <panel.html>

    Loyihaga allaqachon ko‘chirilgan tahrirlar tashlab yuboriladi —
    ular endi «hozirgi matn» bo‘lib qoldi.
    """
    import re
    import sys as _sys
    if "--merge" not in _sys.argv:
        return {}, ""
    path = _sys.argv[_sys.argv.index("--merge") + 1]
    html = io.open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="pnl-data">(.*?)</script>', html, re.S)
    if not m:
        return {}, ""
    old = json.loads(m.group(1))
    alive = {it["id"]: it["text"] for it in items}
    kept, dropped = {}, 0
    for eid, val in (old.get("edits") or {}).items():
        if eid in alive and alive[eid].strip() != (val or "").strip():
            kept[eid] = val
        else:
            dropped += 1
    print("  saqlab qolindi: %d ta tahrir, ko‘chirilgani olib tashlandi: %d ta" % (len(kept), dropped))
    return kept, old.get("savedAt", "")


def main():
    items = json.load(io.open(SRC, encoding="utf-8"))
    edits, stamp = carry_over(items)
    data = {"items": items, "edits": edits, "savedAt": stamp}
    json_text = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    html = (
        '<title>Bilig matn ustaxonasi</title>\n'
        '<style id="pnl-style">%s</style>\n'
        '<div id="app"></div>\n'
        '<script type="application/json" id="pnl-data">%s</script>\n'
        '<script id="pnl-code">%s</script>\n'
    ) % (CSS, json_text, CODE)
    io.open(OUT, "w", encoding="utf-8").write(html)
    print("Panel tayyor: %s  (%d ta matn, %d KB)"
          % (OUT, len(items), os.path.getsize(OUT) // 1024))


if __name__ == "__main__":
    main()
