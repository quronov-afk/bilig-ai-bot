# -*- coding: utf-8 -*-
"""Nishon nomini XAVFSIZ o‘zgartiradi.

Nishon nomi oddiy matn emas: u bazada (Users.badges) saqlanadi va
kodda 6 ta joyda ishlatiladi. Faqat matnni almashtirsak, bolalar
qo‘lga kiritgan nishonlar yo‘qolib qoladi.

Bu skript hammasini birga bajaradi:
  1. Kodning barcha joyida nomni almashtiradi
  2. webapp/badges/index.json ni qayta chiqaradi
  3. webapp_api.py dagi ko‘chirish ro‘yxatiga (_BADGE_RENAMES) qo‘shadi —
     server ishga tushganda bazadagi eski nomlar yangisiga aylanadi

Ishlatish:
    python3 tools/texts/rename_badges.py <panel.html>          # ko‘rish
    python3 tools/texts/rename_badges.py <panel.html> --yoz    # bajarish
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
TEXTS = os.path.join(ROOT, "tools", "texts", "texts.json")
API = os.path.join(ROOT, "webapp_api.py")

# Nishon nomi uchraydigan barcha fayllar
FILES = [
    "tools/badges/badge_defs.py",
    "badges_engine.py",
    "webapp/app.js",
    "webapp_api.py",
    "demo_data.py",
]

AREA = "Nishonlar — nomi"


def read_panel(path):
    html = io.open(path, encoding="utf-8").read()
    m = re.search(r'<script type="application/json" id="pnl-data">(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit("Panel ma'lumoti topilmadi: %s" % path)
    return json.loads(m.group(1))


def pairs_from_panel(path):
    data = read_panel(path)
    edits = data.get("edits") or {}
    items = {it["id"]: it for it in json.load(io.open(TEXTS, encoding="utf-8"))}
    out = []
    for eid, new in edits.items():
        it = items.get(eid)
        if not it or it["area"] != AREA:
            continue
        old, new = it["text"], new.strip()
        if old != new and new:
            out.append((old, new))
    return out


def add_migration(pairs, write):
    """webapp_api.py ga bazani ko‘chirish ro‘yxatini qo‘shadi."""
    src = io.open(API, encoding="utf-8").read()
    block = "\n".join('    ("%s", "%s"),' % (o, n) for o, n in pairs)

    if "_BADGE_RENAMES" in src:
        m = re.search(r"_BADGE_RENAMES = \[\n", src)
        new_src = src[:m.end()] + block + "\n" + src[m.end():]
    else:
        anchor = "_migrate_old_badges()\n"
        assert src.count(anchor) == 1, "webapp_api.py da moslik topilmadi"
        added = '''
# ------------------------------------------------------------
# NISHON NOMI O‘ZGARGANDA BAZANI KO‘CHIRISH
# ------------------------------------------------------------
# Nishonlar bazada NOMI bo‘yicha saqlanadi (Users.badges). Nom
# o‘zgartirilsa, bolalar qo‘lga kiritgan nishon yo‘qolib qolmasligi
# uchun eski nom yangisiga ko‘chiriladi. Ro‘yxat o‘sib boradi;
# ikki marta ishga tushsa ham zarari yo‘q.
# ------------------------------------------------------------
_BADGE_RENAMES = [
%s
]


def _migrate_badge_renames():
    if not _BADGE_RENAMES:
        return
    table = dict(_BADGE_RENAMES)
    try:
        cursor.execute("SELECT user_id, badges FROM Users "
                       "WHERE badges IS NOT NULL AND badges != ''")
        rows = cursor.fetchall()
    except Exception:
        return
    changed = 0
    for uid, raw in rows:
        names = [b.strip() for b in (raw or "").split(",") if b.strip()]
        new_names = []
        for b in names:
            b = table.get(b, b)
            if b not in new_names:
                new_names.append(b)
        if new_names != names:
            try:
                cursor.execute("UPDATE Users SET badges = ? WHERE user_id = ?",
                               (",".join(new_names), uid))
                changed += 1
            except Exception:
                pass
    if changed:
        conn.commit()
        print(f"[webapp_api] {changed} ta foydalanuvchining nishon nomlari ko‘chirildi")


_migrate_badge_renames()
''' % block
        new_src = src.replace(anchor, anchor + added, 1)

    if write:
        io.open(API, "w", encoding="utf-8").write(new_src)
    return True


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Ishlatish: python3 tools/texts/rename_badges.py <panel.html> [--yoz]")
    write = "--yoz" in sys.argv
    pairs = pairs_from_panel(sys.argv[1])
    if not pairs:
        print("Nishon nomi o‘zgartirilmagan.")
        return

    print("Nishon nomlari o‘zgaradi:\n")
    for o, n in pairs:
        print("  %-24s → %s" % (o, n))
    print()

    for rel in FILES:
        path = os.path.join(ROOT, rel)
        if not os.path.exists(path):
            continue
        src = io.open(path, encoding="utf-8").read()
        hits = 0
        for o, n in pairs:
            c = src.count(o)
            if c:
                src = src.replace(o, n)
                hits += c
        if hits:
            if write:
                io.open(path, "w", encoding="utf-8").write(src)
            print("  %-30s %d joyda" % (rel, hits))

    add_migration(pairs, write)
    print("  %-30s bazani ko‘chirish qo‘shildi" % "webapp_api.py")

    if write:
        subprocess.run([sys.executable, os.path.join(ROOT, "tools", "badges", "render_badges.py")],
                       check=True)
        print("\nBajarildi.")
    else:
        print("\n[faqat ko‘rish] Bajarish uchun --yoz qo‘shing.")


if __name__ == "__main__":
    main()
