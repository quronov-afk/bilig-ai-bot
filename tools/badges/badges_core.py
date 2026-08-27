# -*- coding: utf-8 -*-
"""Bilig AI nishonlari — SVG.

Uslub: doiraviy medalyon. Chetida o'zbek do'ppi/ikat naqshiga ishora qiluvchi
naqsh halqasi, ichida nishon ramzi. Har bosqich o'z rang oilasiga ega.
"""
import math


def rosette(cx, cy, r, n, petal, color, opacity=1.0, rot=0):
    """Halqa bo'ylab n ta kichik barg — do'ppi kashtasiga ishora."""
    out = []
    for i in range(n):
        a = rot + i * 360 / n
        x = cx + r * math.cos(math.radians(a))
        y = cy + r * math.sin(math.radians(a))
        out.append(
            f'<path d="M{x:.2f} {y - petal:.2f}'
            f'c{petal*.62:.2f} {petal*.36:.2f} {petal*.62:.2f} {petal*1.28:.2f} 0 {petal*2:.2f}'
            f'c-{petal*.62:.2f} -{petal*.72:.2f} -{petal*.62:.2f} -{petal*1.64:.2f} 0 -{petal*2:.2f}z"'
            f' fill="{color}" opacity="{opacity}"'
            f' transform="rotate({a + 90:.1f} {x:.2f} {y:.2f})"/>'
        )
    return "".join(out)


def frame(uid, rim_a, rim_b, field_a, field_b, orn, orn_op=.55, petals=18):
    """Nishonning umumiy ramkasi: tashqi halqa + naqsh + ichki maydon."""
    return f"""
  <defs>
    <linearGradient id="rim{uid}" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="{rim_a}"/><stop offset="1" stop-color="{rim_b}"/>
    </linearGradient>
    <radialGradient id="fld{uid}" cx=".5" cy=".38" r=".72">
      <stop offset="0" stop-color="{field_a}"/><stop offset="1" stop-color="{field_b}"/>
    </radialGradient>
  </defs>
  <circle cx="60" cy="60" r="56" fill="url(#rim{uid})"/>
  <circle cx="60" cy="60" r="56" fill="none" stroke="#000" stroke-opacity=".13" stroke-width="1.5"/>
  {rosette(60, 60, 50, petals, 3.4, orn, orn_op)}
  <circle cx="60" cy="60" r="44" fill="url(#fld{uid})"/>
  <circle cx="60" cy="60" r="44" fill="none" stroke="{orn}" stroke-opacity=".5" stroke-width="1.6"/>
  <path d="M28 40a44 44 0 0 1 64 0" fill="none" stroke="#fff" stroke-opacity=".28" stroke-width="3" stroke-linecap="round"/>"""


