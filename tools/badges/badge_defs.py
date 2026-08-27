# -*- coding: utf-8 -*-
"""29 ta nishonning ta'rifi: rang oilasi va ramzi."""

# Rang oilalari: (rim_a, rim_b, field_a, field_b, ornament, orn_opacity, petals)
PAL = {
    "yashil":   ("#7FCB92", "#3E9A62", "#FBFDF6", "#DFF1E2", "#2F7A4B", .50, 18),
    "moviy":    ("#6FC7DE", "#2C8AAE", "#F4FCFF", "#D5EFF8", "#1D6C8A", .50, 18),
    "oltin":    ("#F7D35C", "#C8901A", "#3A2F63", "#241C46", "#8A5E10", .60, 22),
    "tosh":     ("#B8C4CE", "#6E8296", "#F7FAFC", "#DCE6EE", "#4A5C6E", .50, 20),
    "koinot":   ("#9B7FE0", "#5B3FA8", "#231B47", "#12102B", "#7C5FD0", .60, 24),
    "olov":     ("#FFC24D", "#E2701A", "#FFF6E6", "#FFD9A8", "#A63F0C", .48, 20),
    "chaqmoq":  ("#FFE066", "#EFA100", "#FFFCEB", "#FFEDAF", "#B37400", .52, 20),
    "yulduz":   ("#C08BE8", "#7B3FBF", "#2A1B4A", "#191036", "#8E5FD0", .58, 22),
    "olmos":    ("#A8E8F0", "#3FA8C4", "#F2FDFF", "#CDEFF8", "#2A7F99", .50, 22),
    "sayyora":  ("#7FB4F0", "#2F63D6", "#111C3D", "#0A1128", "#4E8EF7", .58, 24),
    "polat":    ("#C6D0DA", "#7A8B9C", "#F5F8FB", "#DDE6EE", "#52646F", .50, 18),
    "gilos":    ("#F19A9A", "#C4482F", "#FFF7F5", "#FBDFD8", "#8E2F1D", .50, 18),
    "zumrad":   ("#7ED9B8", "#2E9E78", "#F5FFFB", "#D5F3E7", "#1F7255", .50, 18),
    "siyoh":    ("#8FA8D8", "#3D5B96", "#F6F9FF", "#DCE5F7", "#2B4372", .50, 20),
    "shafaq":   ("#FFB48A", "#E86A3C", "#FFF8F3", "#FFE2D0", "#A6421C", .50, 18),
    "tun":      ("#8E9BD6", "#3F4B9E", "#1B2050", "#111436", "#6B78C4", .58, 22),
    "yaqut":    ("#E88AA8", "#B23A63", "#FFF5F9", "#FBDCE7", "#7E2244", .52, 20),
    "zaytun":   ("#CFD98A", "#8A9B3C", "#FCFEF2", "#EAF1D2", "#5F6E22", .50, 18),
    "marjon":   ("#F2A65A", "#C4682A", "#FFFAF3", "#FBE8D2", "#8A4515", .50, 18),
}


def d(pal, emblem):
    return {"pal": pal, "emblem": emblem}


# =====================================================================
BADGES = {}

# ---------- I. MUTOLAA HAJMI ----------
BADGES["birinchi-qadam"] = ("Birinchi qadam", "Ilk 5 sahifa o‘qilganda", "yashil", """
  <path d="M60 74V51" stroke="#3E8F58" stroke-width="4.6" stroke-linecap="round"/>
  <path d="M60 58c-3-9-11-12-17-11-1 7 4 15 12 15 2 0 4-1 5-4z" fill="#5FBE7B"/>
  <path d="M60 58c-5-4-10-6-15-6" stroke="#2F7A4B" stroke-opacity=".45" stroke-width="1.7" stroke-linecap="round"/>
  <path d="M60 53c3-11 13-14 20-12 1 8-5 17-14 17-2 0-5-1-6-5z" fill="#79D18F"/>
  <path d="M60 53c6-5 12-7 18-7" stroke="#2F7A4B" stroke-opacity=".45" stroke-width="1.7" stroke-linecap="round"/>
  <circle cx="60" cy="47" r="4.2" fill="#F5C542"/>
  <circle cx="58.6" cy="45.6" r="1.4" fill="#fff" opacity=".8"/>
  <path d="M60 76c-6-5-14-7-23-6v18c9-1 17 1 23 6z" fill="#F3E6CE" stroke="#B99A63" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 76c6-5 14-7 23-6v18c-9-1-17 1-23 6z" fill="#FBF3E2" stroke="#B99A63" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 76v18" stroke="#B99A63" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M43 79h9M43 84h9M68 79h9M68 84h9" stroke="#C9AF7E" stroke-width="1.5" stroke-linecap="round"/>""")

BADGES["kitobxon-sayyoh"] = ("Kitobxon sayyoh", "100 bet o‘qilganda", "moviy", """
  <path d="M60 80c-7-5-16-7-25-6v16c9-1 18 1 25 6z" fill="#DCEEF7" stroke="#2C7C9E" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 80c7-5 16-7 25-6v16c-9-1-18 1-25 6z" fill="#EDF8FD" stroke="#2C7C9E" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 80v16" stroke="#2C7C9E" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="60" cy="50" r="21" fill="#2C8AAE" stroke="#1D6C8A" stroke-width="2.4"/>
  <circle cx="60" cy="50" r="16" fill="#8FD8EC" opacity=".55"/>
  <path d="M60 32l4.6 12.4L77 50l-12.4 4.6L60 68l-4.6-13.4L42 50l13.4-5.6z" fill="#FFF3D0" stroke="#C8901A" stroke-width="1.6" stroke-linejoin="round"/>
  <circle cx="60" cy="50" r="3.4" fill="#E2701A"/>""")

BADGES["kitoblar-sultoni"] = ("Kitoblar sultoni", "500 bet o‘qilganda", "oltin", """
  <g opacity=".22">
    <path d="M60 24 62.4 46 60 52 57.6 46z" fill="#FFE9A8"/>
    <path d="M96 60 74 62.4 68 60 74 57.6z" fill="#FFE9A8"/>
    <path d="M24 60 46 57.6 52 60 46 62.4z" fill="#FFE9A8"/>
  </g>
  <rect x="34" y="80" width="52" height="9" rx="3" fill="#C4482F" stroke="#8E2F1D" stroke-width="1.6"/>
  <rect x="37" y="71" width="46" height="9" rx="3" fill="#2E7FA8" stroke="#1D5B7C" stroke-width="1.6"/>
  <rect x="40" y="62" width="40" height="9" rx="3" fill="#3E9A62" stroke="#2A6E45" stroke-width="1.6"/>
  <path d="M41 84.5h8M44 75.5h8M47 66.5h8" stroke="#fff" stroke-opacity=".45" stroke-width="1.6" stroke-linecap="round"/>
  <path d="M40 56 44 36l8 10 8-14 8 14 8-10 4 20z" fill="#F7D35C" stroke="#A9761A" stroke-width="2.2" stroke-linejoin="round"/>
  <rect x="40" y="55" width="40" height="7" rx="2.4" fill="#EFC244" stroke="#A9761A" stroke-width="2"/>
  <circle cx="60" cy="58.5" r="2.6" fill="#C4482F"/>
  <circle cx="49" cy="58.5" r="2" fill="#2E7FA8"/><circle cx="71" cy="58.5" r="2" fill="#3E9A62"/>
  <circle cx="44" cy="34" r="2.8" fill="#FFF0B8"/><circle cx="60" cy="30" r="3.4" fill="#FFF0B8"/>
  <circle cx="76" cy="34" r="2.8" fill="#FFF0B8"/>""")

BADGES["ming-betlik-dovon"] = ("Ming betlik dovon", "1 000 bet o‘qilganda", "tosh", """
  <path d="M22 88 44 50l12 19 9-13 25 32z" fill="#8FA3B5" stroke="#4A5C6E" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M44 50 33 69h22z" fill="#F2F7FB"/>
  <path d="M65 56 56 69h18z" fill="#F2F7FB"/>
  <path d="M22 88h68" stroke="#4A5C6E" stroke-width="2.4" stroke-linecap="round"/>
  <path d="M65 56V30" stroke="#6E8296" stroke-width="2.8" stroke-linecap="round"/>
  <path d="M65 31h17l-4.5 6 4.5 6H65z" fill="#E2701A" stroke="#A63F0C" stroke-width="1.8" stroke-linejoin="round"/>
  <path d="M31 76h9M50 78h8M72 76h9" stroke="#fff" stroke-opacity=".4" stroke-width="1.8" stroke-linecap="round"/>
  <text x="60" y="103" font-family="Nunito,sans-serif" font-size="13" font-weight="800"
        fill="#4A5C6E" text-anchor="middle">1000</text>""")

BADGES["kitoblar-ummoni"] = ("Kitoblar ummoni", "5 000 bet o‘qilganda", "koinot", """
  <g opacity=".85">
    <circle cx="38" cy="38" r="1.8" fill="#FFF"/><circle cx="80" cy="34" r="1.4" fill="#FFF"/>
    <circle cx="88" cy="56" r="1.6" fill="#FFF"/><circle cx="32" cy="60" r="1.3" fill="#FFF"/>
    <circle cx="46" cy="28" r="1.1" fill="#FFE9A8"/><circle cx="72" cy="26" r="1.5" fill="#FFE9A8"/>
  </g>
  <ellipse cx="60" cy="52" rx="27" ry="10" fill="none" stroke="#C08BE8" stroke-width="2.4" opacity=".8"
           transform="rotate(-18 60 52)"/>
  <circle cx="60" cy="52" r="14" fill="#7B5FD8"/>
  <path d="M46 52a14 14 0 0 1 28 0z" fill="#9B7FE0" opacity=".7"/>
  <circle cx="55" cy="47" r="3" fill="#C8B6F5" opacity=".7"/>
  <circle cx="66" cy="56" r="2" fill="#C8B6F5" opacity=".55"/>
  <path d="M60 84c-7-5-16-7-25-6v14c9-1 18 1 25 6z" fill="#3B2E6B" stroke="#B9A3F0" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 84c7-5 16-7 25-6v14c-9-1-18 1-25 6z" fill="#463A78" stroke="#B9A3F0" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 84v14" stroke="#B9A3F0" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="47" cy="86" r="1.3" fill="#FFE9A8"/><circle cx="73" cy="86" r="1.3" fill="#FFE9A8"/>""")

# ---------- II. UZLUKSIZLIK ----------
BADGES["olovli-qanot"] = ("Olovli qanot", "3 kun uzluksiz o‘qilganda", "olov", """
  <path d="M60 88c-14-3-26-13-30-27-2-7-1-14 2-20 4 6 9 10 15 12-3-7-3-14 0-20 5 7 12 11 20 12z" fill="#F2711C" opacity=".28"/>
  <path d="M60 86c-11-3-20-11-23-22-1-5 0-11 2-15 3 5 7 8 12 10-2-6-2-11 0-16 4 6 10 9 16 10z" fill="#F4842B"/>
  <path d="M60 83c-8-3-14-9-16-17-1-4 0-8 1-11 2 4 6 6 9 8-2-4-2-8 0-12 3 5 8 7 12 8z" fill="#FFB03A"/>
  <path d="M74 92c9 0 16-7 16-16 0-12-10-17-13-36-6 7-9 13-9 19 0 3 1 5 2 8-3-1-6-3-7-6-4 5-5 10-5 15 0 9 7 16 16 16z" fill="#E8541A"/>
  <path d="M74 92c5 0 8-4 8-9 0-5-4-7-8-13-4 6-8 8-8 13 0 5 3 9 8 9z" fill="#FFC93F"/>
  <path d="M74 92c2.4 0 4-2 4-4.5 0-2.6-2-3.6-4-6.5-2 2.9-4 3.9-4 6.5 0 2.5 1.6 4.5 4 4.5z" fill="#FFF0B8"/>
  <circle cx="38" cy="42" r="2.6" fill="#FFD766"/><circle cx="86" cy="46" r="2" fill="#FFD766" opacity=".85"/>
  <circle cx="32" cy="58" r="1.7" fill="#FFE9A3" opacity=".8"/>""")

BADGES["yengilmas-qahramon"] = ("Yengilmas qahramon", "7 kun uzluksiz o‘qilganda", "chaqmoq", """
  <path d="M60 26 78 30v22c0 15-8 26-18 31-10-5-18-16-18-31V30z" fill="#FFDF7A" stroke="#B37400" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 26 78 30v22c0 15-8 26-18 31z" fill="#FFC93F" opacity=".75"/>
  <path d="M64 38 49 60h9l-3 18 17-23h-9z" fill="#EFA100" stroke="#8A5A00" stroke-width="1.8" stroke-linejoin="round"/>
  <g fill="#B37400" opacity=".85">
    <circle cx="47" cy="88" r="2"/><circle cx="53" cy="90" r="2"/><circle cx="59" cy="91" r="2"/>
    <circle cx="65" cy="90" r="2"/><circle cx="71" cy="88" r="2"/>
    <circle cx="44" cy="84" r="2"/><circle cx="74" cy="84" r="2"/>
  </g>""")

BADGES["mutolaa-afsonasi"] = ("Mutolaa afsonasi", "30 kun uzluksiz o‘qilganda", "yulduz", """
  <g opacity=".9">
    <circle cx="34" cy="40" r="1.6" fill="#FFF"/><circle cx="86" cy="42" r="1.4" fill="#FFF"/>
    <circle cx="30" cy="66" r="1.2" fill="#FFF"/><circle cx="90" cy="66" r="1.5" fill="#FFF"/>
  </g>
  <path d="M60 28l7.4 15 16.6 2.4-12 11.7 2.8 16.5L60 65.8 45.2 73.6 48 57.1 36 45.4 52.6 43z"
        fill="#F7D35C" stroke="#A9761A" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 36l4.6 9.4 10.4 1.5-7.5 7.3 1.8 10.4L60 59.7z" fill="#FFF0B8" opacity=".85"/>
  <path d="M42 84h36" stroke="#C08BE8" stroke-width="3" stroke-linecap="round"/>
  <text x="60" y="97" font-family="Nunito,sans-serif" font-size="14" font-weight="900"
        fill="#E6D6FF" text-anchor="middle">30</text>""")

BADGES["olmos-iroda"] = ("Olmos iroda", "100 kun uzluksiz o‘qilganda", "olmos", """
  <path d="M42 46h36l14 16-32 34-32-34z" fill="#7FD8EC" stroke="#1F6E88" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M42 46 34 62h20z" fill="#CFF3FC"/>
  <path d="M78 46l8 16H66z" fill="#CFF3FC"/>
  <path d="M42 46h36l-6 16H48z" fill="#A8E8F0"/>
  <path d="M34 62h52L60 96z" fill="#5FC5DD" opacity=".85"/>
  <path d="M48 62 60 96 72 62" fill="none" stroke="#1F6E88" stroke-width="2" stroke-linejoin="round"/>
  <path d="M46 40l2.5 5.5L54 48l-5.5 2.5L46 56l-2.5-5.5L38 48l5.5-2.5z" fill="#FFF" opacity=".75"/>
  <text x="60" y="36" font-family="Nunito,sans-serif" font-size="13" font-weight="900"
        fill="#1F6E88" text-anchor="middle">100</text>""")

BADGES["yil-qahramoni"] = ("Yil qahramoni", "365 kun uzluksiz o‘qilganda", "sayyora", """
  <g opacity=".85">
    <circle cx="32" cy="44" r="1.5" fill="#FFF"/><circle cx="88" cy="42" r="1.3" fill="#FFF"/>
    <circle cx="86" cy="72" r="1.5" fill="#FFF"/><circle cx="34" cy="74" r="1.2" fill="#FFF"/>
  </g>
  <ellipse cx="60" cy="58" rx="30" ry="11" fill="none" stroke="#7FB4F0" stroke-width="2.6"
           transform="rotate(-22 60 58)"/>
  <circle cx="60" cy="58" r="17" fill="#3F79DC"/>
  <path d="M43 58a17 17 0 0 1 34 0z" fill="#6FA4FA" opacity=".65"/>
  <path d="M50 52c4-2 8-1 10 1M64 66c4 1 8 0 10-2" stroke="#BBD6FA" stroke-width="2.2" stroke-linecap="round"/>
  <circle cx="88" cy="41" r="3.4" fill="#FFD766"/>
  <text x="60" y="97" font-family="Nunito,sans-serif" font-size="14" font-weight="900"
        fill="#BBD6FA" text-anchor="middle">365</text>""")

BADGES["qalqon"] = ("Qalqon", "Olov qalqonidan keyin darhol qaytganda", "polat", """
  <path d="M60 24 82 30v24c0 16-9 28-22 34-13-6-22-18-22-34V30z" fill="#DCE6EE" stroke="#52646F" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M60 24 82 30v24c0 16-9 28-22 34z" fill="#B8C6D2" opacity=".7"/>
  <path d="M60 30 76 34.5V54c0 12-6.6 21-16 26z" fill="none" stroke="#7A8B9C" stroke-width="1.6"/>
  <path d="M60 74c6 0 10.5-4.6 10.5-10.5 0-8-6.6-11-8.6-23.5-4 4.6-6 8.6-6 12.6 0 2 .6 3.4 1.3 5.3-2-.6-4-2-4.6-4-2.6 3.3-3.3 6.6-3.3 9.6C49.3 69.4 54 74 60 74z" fill="#E2701A"/>
  <path d="M60 74c3 0 5-2.4 5-5.4 0-3-2.4-4.3-5-7.6-2.6 3.3-5 4.6-5 7.6 0 3 2 5.4 5 5.4z" fill="#FFC93F"/>""")

# ---------- III. TUGATILGAN KITOBLAR ----------
BADGES["marra-golibi"] = ("Marra g‘olibi", "Ilk kitob yakunlanganda", "gilos", """
  <path d="M40 34h40v14c0 12-9 21-20 21S40 60 40 48z" fill="#F2C94C" stroke="#A9761A" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M40 38H31c0 9 4 14 10 15M80 38h9c0 9-4 14-10 15" fill="none" stroke="#A9761A" stroke-width="2.6" stroke-linecap="round"/>
  <path d="M56 69h8v9h-8z" fill="#C8901A"/>
  <path d="M44 78h32v7H44z" rx="2" fill="#F2C94C" stroke="#A9761A" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 40l3.2 6.6 7.3 1-5.3 5.1 1.3 7.3L60 56.6l-6.5 3.4 1.3-7.3-5.3-5.1 7.3-1z" fill="#FFF3D0"/>
  <path d="M36 92l10-8M84 92l-10-8" stroke="#C4482F" stroke-width="3" stroke-linecap="round"/>""")

BADGES["tezkor-mutolaa"] = ("Tezkor mutolaa", "Kitob 3 kun ichida tugatilganda", "shafaq", """
  <path d="M60 22c9 8 14 19 14 32v14H46V54c0-13 5-24 14-32z" fill="#FBE8D2" stroke="#A6421C" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 22c9 8 14 19 14 32v14H60z" fill="#F0C9AC" opacity=".6"/>
  <circle cx="60" cy="48" r="7" fill="#2C8AAE" stroke="#1D6C8A" stroke-width="2.2"/>
  <circle cx="60" cy="48" r="3" fill="#CFF3FC"/>
  <path d="M46 60 34 74l12-2z" fill="#E86A3C" stroke="#A6421C" stroke-width="2" stroke-linejoin="round"/>
  <path d="M74 60l12 14-12-2z" fill="#E86A3C" stroke="#A6421C" stroke-width="2" stroke-linejoin="round"/>
  <path d="M52 76c3 5 3 10 0 14M60 78c3 6 3 11 0 16M68 76c3 5 3 10 0 14"
        fill="none" stroke="#FFB03A" stroke-width="3.4" stroke-linecap="round"/>""")

BADGES["kichik-kutubxonachi"] = ("Kichik kutubxonachi", "10 ta kitob tugatilganda", "zumrad", """
  <rect x="28" y="34" width="64" height="56" rx="5" fill="#F0FBF6" stroke="#1F7255" stroke-width="2.6"/>
  <path d="M28 60h64" stroke="#1F7255" stroke-width="2.4"/>
  <g stroke="#1F7255" stroke-width="1.6">
    <rect x="34" y="40" width="7" height="17" rx="2" fill="#C4482F"/>
    <rect x="43" y="43" width="7" height="14" rx="2" fill="#2E7FA8"/>
    <rect x="52" y="39" width="7" height="18" rx="2" fill="#F2C94C"/>
    <rect x="61" y="44" width="7" height="13" rx="2" fill="#7B3FBF"/>
    <rect x="70" y="41" width="7" height="16" rx="2" fill="#2E9E78"/>
    <rect x="79" y="45" width="7" height="12" rx="2" fill="#E86A3C"/>
    <rect x="34" y="66" width="7" height="18" rx="2" fill="#2E9E78"/>
    <rect x="43" y="69" width="7" height="15" rx="2" fill="#F2C94C"/>
    <rect x="52" y="65" width="7" height="19" rx="2" fill="#2E7FA8"/>
    <rect x="61" y="70" width="7" height="14" rx="2" fill="#C4482F"/>
    <rect x="70" y="67" width="7" height="17" rx="2" fill="#7B3FBF"/>
    <rect x="79" y="71" width="7" height="13" rx="2" fill="#E86A3C"/>
  </g>
  <text x="60" y="103" font-family="Nunito,sans-serif" font-size="13" font-weight="900"
        fill="#1F7255" text-anchor="middle">10</text>""")

BADGES["mutolaa-akademigi"] = ("Mutolaa akademigi", "25 ta kitob tugatilganda", "siyoh", """
  <path d="M60 30 92 44 60 58 28 44z" fill="#4C6BAE" stroke="#2B4372" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 30 92 44 60 58z" fill="#6B87C9" opacity=".7"/>
  <path d="M42 51v14c0 6 8 10 18 10s18-4 18-10V51" fill="#3D5B96" stroke="#2B4372" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M88 46v18" stroke="#2B4372" stroke-width="2.4" stroke-linecap="round"/>
  <circle cx="88" cy="67" r="4" fill="#F2C94C" stroke="#A9761A" stroke-width="1.8"/>
  <rect x="36" y="80" width="48" height="8" rx="3" fill="#8FA8D8" stroke="#2B4372" stroke-width="2"/>
  <text x="60" y="103" font-family="Nunito,sans-serif" font-size="13" font-weight="900"
        fill="#2B4372" text-anchor="middle">25</text>""")

# ---------- IV. NOTIQLIK ----------
BADGES["bilim-notigi"] = ("Bilim notig‘i", "Audio xulosada 5 Bilig olinganda", "marjon", """
  <rect x="50" y="28" width="20" height="36" rx="10" fill="#E88A4A" stroke="#8A4515" stroke-width="2.4"/>
  <path d="M56 36h8M56 43h8M56 50h8" stroke="#FFE0C2" stroke-width="2" stroke-linecap="round"/>
  <path d="M38 56v4c0 12 10 22 22 22s22-10 22-22v-4" fill="none" stroke="#8A4515" stroke-width="3" stroke-linecap="round"/>
  <path d="M60 82v10M50 92h20" stroke="#8A4515" stroke-width="3" stroke-linecap="round"/>
  <path d="M30 46c-3 5-3 12 0 17M90 46c3 5 3 12 0 17" fill="none" stroke="#F2A65A" stroke-width="3" stroke-linecap="round"/>
  <path d="M24 40c-5 8-5 20 0 28M96 40c5 8 5 20 0 28" fill="none" stroke="#F2A65A" stroke-width="2.4" stroke-linecap="round" opacity=".6"/>""")

BADGES["tafakkur"] = ("Tafakkur", "Mustaqil fikr yuqori baholanganda", "chaqmoq", """
  <path d="M60 26c-12 0-21 9-21 20 0 8 4 13 7 17 2 3 3 5 3 8h22c0-3 1-5 3-8 3-4 7-9 7-17 0-11-9-20-21-20z"
        fill="#FFDF7A" stroke="#B37400" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 26c12 0 21 9 21 20 0 8-4 13-7 17-2 3-3 5-3 8H60z" fill="#FFC93F" opacity=".6"/>
  <path d="M49 79h22M51 86h18" stroke="#B37400" stroke-width="3.2" stroke-linecap="round"/>
  <path d="M60 40v18M60 40l-6 7M60 40l6 7" fill="none" stroke="#A66A00" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="34" cy="36" r="2.4" fill="#FFD766"/><circle cx="86" cy="38" r="2" fill="#FFD766"/>
  <circle cx="30" cy="56" r="1.8" fill="#FFE9A3"/><circle cx="90" cy="58" r="1.8" fill="#FFE9A3"/>""")

BADGES["buyuk-suxandon"] = ("Buyuk suxandon", "10 ta kitob bo‘yicha a'lo xulosa", "marjon", """
  <path d="M60 36c-5-6.5-11-10-17.5-9.6 1 5.4 3.2 9.2 5.6 12.3C39 44.4 33 53.6 33 64.5 33 78.6 45 89.5 60 89.5S87 78.6 87 64.5c0-10.9-6-20.1-15.1-25.8 2.4-3.1 4.6-6.9 5.6-12.3C71 26 65 29.5 60 36z"
        fill="#C98A4E" stroke="#6B4420" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 36c5-6.5 11-10 17.5-9.6-1 5.4-3.2 9.2-5.6 12.3C81 44.4 87 53.6 87 64.5 87 78.6 75 89.5 60 89.5z"
        fill="#B0743C" opacity=".38"/>
  <ellipse cx="60" cy="60" rx="22" ry="19" fill="#FDF3E4" stroke="#6B4420" stroke-width="1.6"/>
  <circle cx="50.5" cy="57.5" r="8.6" fill="#FFF" stroke="#6B4420" stroke-width="1.7"/>
  <circle cx="69.5" cy="57.5" r="8.6" fill="#FFF" stroke="#6B4420" stroke-width="1.7"/>
  <circle cx="50.5" cy="57.5" r="4.4" fill="#3A2A18"/><circle cx="69.5" cy="57.5" r="4.4" fill="#3A2A18"/>
  <circle cx="52.2" cy="55.7" r="1.6" fill="#FFF"/><circle cx="71.2" cy="55.7" r="1.6" fill="#FFF"/>
  <path d="M60 66.5l-4 6h8z" fill="#E8A030" stroke="#A6701A" stroke-width="1.5" stroke-linejoin="round"/>
  <path d="M37.5 62c-2.2 7-1 14.4 3.6 20M82.5 62c2.2 7 1 14.4-3.6 20"
        fill="none" stroke="#A8703A" stroke-width="2.6" stroke-linecap="round"/>
  <path d="M53 89v4M60 90v4M67 89v4" stroke="#E8A030" stroke-width="2.8" stroke-linecap="round"/>
  <text x="60" y="106" font-family="Nunito,sans-serif" font-size="11.5" font-weight="900"
        fill="#8A4515" text-anchor="middle">10</text>""")

BADGES["oltin-qalam"] = ("Oltin qalam", "Go‘zal adabiy so‘zlar bilan bayon etganda", "oltin", """
  <path d="M78 26c-14 6-28 20-36 34-4 7-6 13-7 20 6-3 12-8 17-14 8-9 18-24 26-40z"
        fill="#F7D35C" stroke="#A9761A" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M78 26c-8 16-18 31-26 40-5 6-11 11-17 14 8-2 17-7 24-14 10-10 17-25 19-40z" fill="#FFF0B8" opacity=".6"/>
  <path d="M35 80c-3 4-6 8-8 14 7-2 12-5 16-9z" fill="#EFC244" stroke="#A9761A" stroke-width="2" stroke-linejoin="round"/>
  <path d="M60 52c-6 5-11 12-14 18" stroke="#A9761A" stroke-opacity=".55" stroke-width="1.8" stroke-linecap="round"/>
  <path d="M40 40c4 1 7 4 8 8M32 52c3 1 5 3 6 6" fill="none" stroke="#FFE9A8" stroke-width="2" stroke-linecap="round" opacity=".7"/>""")

# ---------- V. ZUKKOLIK ----------
BADGES["zukko-kitobxon"] = ("Zukko kitobxon", "Testda 100% to‘g‘ri javob", "yulduz", """
  <circle cx="60" cy="58" r="27" fill="#F3EDFF" stroke="#5B2E96" stroke-width="2.6"/>
  <circle cx="60" cy="58" r="19" fill="#C9AEF2"/>
  <circle cx="60" cy="58" r="11" fill="#F3EDFF"/>
  <circle cx="60" cy="58" r="4" fill="#7B3FBF"/>
  <path d="M60 22v9M60 85v9M24 58h9M87 58h9" stroke="#C08BE8" stroke-width="3" stroke-linecap="round"/>
  <path d="M46 56l9 9 18-19" fill="none" stroke="#2E9E78" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>
  <text x="60" y="103" font-family="Nunito,sans-serif" font-size="12" font-weight="900"
        fill="#E6D6FF" text-anchor="middle">100%</text>""")

BADGES["mantiq-ustasi"] = ("Mantiq ustasi", "Jami 50 ta to‘g‘ri javob", "moviy", """
  <path d="M32 34h22c0-5 3-8 7-8s7 3 7 8h20v22c5 0 8 3 8 7s-3 7-8 7v18H66c0-5-3-8-6-8s-6 3-6 8H32z"
        fill="#7FD0E8" stroke="#1D6C8A" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M60 26c4 0 7 3 7 8h20v22c5 0 8 3 8 7s-3 7-8 7v18H66c0-5-3-8-6-8z" fill="#A8E4F4" opacity=".55"/>
  <circle cx="46" cy="52" r="3.6" fill="#FFF" opacity=".8"/>
  <circle cx="72" cy="70" r="3" fill="#FFF" opacity=".65"/>
  <text x="60" y="102" font-family="Nunito,sans-serif" font-size="13" font-weight="900"
        fill="#1D6C8A" text-anchor="middle">50</text>""")

BADGES["bilim-akademiyasi"] = ("Bilim akademiyasi", "10 ta test ketma-ket 100%", "koinot", """
  <path d="M60 30 92 44 60 58 28 44z" fill="#7B5FD8" stroke="#C8B6F5" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 30 92 44 60 58z" fill="#9B7FE0" opacity=".7"/>
  <path d="M42 51v13c0 6 8 10 18 10s18-4 18-10V51" fill="#5B3FA8" stroke="#C8B6F5" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M88 46v17" stroke="#C8B6F5" stroke-width="2.4" stroke-linecap="round"/>
  <circle cx="88" cy="66" r="4" fill="#F7D35C"/>
  <g fill="#FFE9A8">
    <path d="M36 78l1.9 4 4.4.6-3.2 3.1.8 4.4-3.9-2.1-3.9 2.1.8-4.4-3.2-3.1 4.4-.6z"/>
    <path d="M84 78l1.9 4 4.4.6-3.2 3.1.8 4.4-3.9-2.1-3.9 2.1.8-4.4-3.2-3.1 4.4-.6z"/>
    <path d="M60 82l2.2 4.6 5.1.7-3.7 3.6.9 5.1L60 93.6 55.5 96l.9-5.1-3.7-3.6 5.1-.7z"/>
  </g>""")

# ---------- VI. ODAT VA INTIZOM ----------
BADGES["tonggi-qaldirgoch"] = ("Tonggi qaldirg‘och", "06:00–09:00 oralig‘ida o‘qilganda", "shafaq", """
  <circle cx="60" cy="72" r="20" fill="#FFD766"/>
  <path d="M28 72a32 32 0 0 1 64 0" fill="none" stroke="#E86A3C" stroke-width="2.6" stroke-linecap="round"/>
  <g stroke="#F2A65A" stroke-width="2.8" stroke-linecap="round">
    <path d="M60 40v-8"/><path d="M36 50l-6-6"/><path d="M84 50l6-6"/>
    <path d="M26 68h-8"/><path d="M94 68h8"/>
  </g>
  <path d="M30 84h60" stroke="#E86A3C" stroke-width="3" stroke-linecap="round"/>
  <path d="M52 56c6-8 16-10 24-6-4 2-6 5-7 8 5-1 9 0 12 3-6 1-10 4-12 8-3-6-10-11-17-13z"
        fill="#3D5B96" stroke="#22355C" stroke-width="1.8" stroke-linejoin="round"/>
  <circle cx="72" cy="55" r="1.4" fill="#FFF"/>""")

BADGES["qutb-yulduzi"] = ("Qutb yulduzi", "Uxlashdan oldin o‘qilganda", "tun", """
  <g opacity=".9">
    <circle cx="34" cy="40" r="1.6" fill="#FFF"/><circle cx="88" cy="44" r="1.4" fill="#FFF"/>
    <circle cx="30" cy="62" r="1.2" fill="#FFF"/><circle cx="46" cy="32" r="1.1" fill="#FFE9A8"/>
  </g>
  <path d="M78 30a24 24 0 1 0 12 34A26 26 0 0 1 78 30z" fill="#FFE9A8" stroke="#C8A840" stroke-width="2.2" stroke-linejoin="round"/>
  <circle cx="76" cy="44" r="3" fill="#E8D89A" opacity=".7"/>
  <circle cx="84" cy="56" r="2" fill="#E8D89A" opacity=".55"/>
  <path d="M60 78c-7-5-16-7-25-6v14c9-1 18 1 25 6z" fill="#2B3270" stroke="#8E9BD6" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 78c7-5 16-7 25-6v14c-9-1-18 1-25 6z" fill="#343C82" stroke="#8E9BD6" stroke-width="2.2" stroke-linejoin="round"/>
  <path d="M60 78v14" stroke="#8E9BD6" stroke-width="2.2" stroke-linecap="round"/>
  <path d="M40 34l1.7 3.6 4 .5-2.9 2.8.7 4-3.5-1.9-3.5 1.9.7-4-2.9-2.8 4-.5z" fill="#FFE9A8"/>""")

BADGES["maroqli"] = ("Maroqli", "Dam olish kunlari o‘qilganda", "zaytun", """
  <path d="M60 30 88 84H32z" fill="#DCE8B0" stroke="#5F6E22" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M60 30 88 84H60z" fill="#C4D48E" opacity=".6"/>
  <path d="M60 44 74 84H46z" fill="#8A9B3C" opacity=".5"/>
  <path d="M60 30v54" stroke="#5F6E22" stroke-width="2.2"/>
  <path d="M28 84h64" stroke="#5F6E22" stroke-width="3" stroke-linecap="round"/>
  <path d="M52 70c0-4 3-7 8-7s8 3 8 7v14H52z" fill="#F2C94C" stroke="#A9761A" stroke-width="2" stroke-linejoin="round"/>
  <circle cx="34" cy="40" r="3.4" fill="#F2C94C"/>
  <path d="M88 36c3 2 4 6 2 9" fill="none" stroke="#8A9B3C" stroke-width="2.4" stroke-linecap="round"/>""")

BADGES["oila-iftixori"] = ("Oila iftixori", "Ota-ona bilan suhbat a'lo o‘tganda", "yaqut", """
  <path d="M60 88c-16-11-26-21-26-32 0-8 6-14 13-14 5 0 10 3 13 8 3-5 8-8 13-8 7 0 13 6 13 14 0 11-10 21-26 32z"
        fill="#E8779E" stroke="#7E2244" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M60 88c16-11 26-21 26-32 0-8-6-14-13-14-5 0-10 3-13 8z" fill="#F09CBA" opacity=".55"/>
  <circle cx="47" cy="52" r="6" fill="#FFF3F7" stroke="#7E2244" stroke-width="1.8"/>
  <circle cx="73" cy="52" r="6" fill="#FFF3F7" stroke="#7E2244" stroke-width="1.8"/>
  <circle cx="60" cy="62" r="5" fill="#FFE0EC" stroke="#7E2244" stroke-width="1.8"/>
  <path d="M41 64c0-4 3-6 6-6s6 2 6 6M67 64c0-4 3-6 6-6s6 2 6 6" fill="none" stroke="#7E2244" stroke-width="1.8" stroke-linecap="round"/>""")

BADGES["chaqmoq-kitobxon"] = ("Chaqmoq kitobxon", "Bir o‘tirishda 30+ bet o‘qilganda", "chaqmoq", """
  <path d="M60 74c-8-6-19-8-28-7V30c9-1 20 1 28 7z" fill="#FFF6DC" stroke="#B37400" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 74c8-6 19-8 28-7V30c-9-1-20 1-28 7z" fill="#FFFBEE" stroke="#B37400" stroke-width="2.4" stroke-linejoin="round"/>
  <path d="M60 37v37" stroke="#B37400" stroke-width="2.4" stroke-linecap="round"/>
  <path d="M67 30 50 56h10l-4 22 19-28H64z" fill="#EFA100" stroke="#8A5A00" stroke-width="2" stroke-linejoin="round"/>
  <path d="M38 42h8M38 48h6M76 42h-8M76 48h-6" stroke="#D8B76A" stroke-width="1.8" stroke-linecap="round"/>
  <text x="60" y="97" font-family="Nunito,sans-serif" font-size="13" font-weight="900"
        fill="#8A5A00" text-anchor="middle">30</text>""")

BADGES["ezgulik-elchisi"] = ("Ezgulik elchisi", "Qahramon fazilatlari bo‘yicha xulosa", "moviy", """
  <path d="M60 88c-16-11-27-21-27-33 0-9 7-15 14-15 6 0 11 3 13 8 2-5 7-8 13-8 7 0 14 6 14 15 0 12-11 22-27 33z"
        fill="#FFF" stroke="#1D6C8A" stroke-width="2.4" stroke-linejoin="round" opacity=".95"/>
  <path d="M36 52c-4-8-12-12-20-11 2 9 9 16 18 17" fill="#A8E4F4" stroke="#1D6C8A" stroke-width="2" stroke-linejoin="round"/>
  <path d="M84 52c4-8 12-12 20-11-2 9-9 16-18 17" fill="#A8E4F4" stroke="#1D6C8A" stroke-width="2" stroke-linejoin="round"/>
  <path d="M60 48c2-3 5-4 8-4" stroke="#7FD0E8" stroke-width="2.4" stroke-linecap="round"/>
  <path d="M60 30l2.4 5.2 5.6.8-4 3.9 1 5.6L60 42.8 54.9 45.5l1-5.6-4-3.9 5.6-.8z" fill="#F2C94C"/>""")

BADGES["xazinabon"] = ("Xazinabon", "2000 Bilig to‘planganda", "oltin", """
  <path d="M30 56c0-11 13-18 30-18s30 7 30 18v26a4 4 0 0 1-4 4H34a4 4 0 0 1-4-4z"
        fill="#B5762A" stroke="#6E4412" stroke-width="2.6" stroke-linejoin="round"/>
  <path d="M30 56c0-11 13-18 30-18s30 7 30 18z" fill="#D9974A"/>
  <rect x="30" y="56" width="60" height="10" rx="3" fill="#8A5A1E" stroke="#6E4412" stroke-width="2"/>
  <rect x="53" y="52" width="14" height="20" rx="3" fill="#F7D35C" stroke="#A9761A" stroke-width="2"/>
  <circle cx="60" cy="61" r="2.6" fill="#6E4412"/>
  <g stroke="#A9761A" stroke-width="1.8">
    <circle cx="40" cy="76" r="6" fill="#F7D35C"/>
    <circle cx="52" cy="80" r="5" fill="#EFC244"/>
    <circle cx="80" cy="76" r="6" fill="#F7D35C"/>
  </g>
  <text x="40" y="79.5" font-family="Nunito,sans-serif" font-size="8" font-weight="900"
        fill="#8A5A1E" text-anchor="middle">B</text>
  <text x="80" y="79.5" font-family="Nunito,sans-serif" font-size="8" font-weight="900"
        fill="#8A5A1E" text-anchor="middle">B</text>""")
