# -*- coding: utf-8 -*-
import re, json, unicodedata, difflib
files = json.load(open('word_index.json'))
files = [x for x in files if len(x['n']) >= 3]
def norm(s):
    s = (s or '').lower()
    for ch in "ʻʼ‘’'`´": s = s.replace(ch,'')
    s = unicodedata.normalize('NFKD', s).encode('ascii','ignore').decode()
    return re.sub(r'[^a-z0-9]','',s)
def find(t, a=''):
    nt, na = norm(re.sub(r'\(.*?\)','',t)), norm(a)
    if len(nt) < 3: return (0, None)
    best = (0, None)
    for x in files:
        s = difflib.SequenceMatcher(None, nt, x['n']).ratio()
        sh, lo = (nt, x['n']) if len(nt) < len(x['n']) else (x['n'], nt)
        if sh and sh in lo and (len(sh) >= 10 or (len(sh) >= 8 and len(sh)/len(lo) >= 0.5) or (len(sh) >= 3 and sh == lo)): s = max(s, .93)
        if na and x['na'] and s > .6:
            s = s*0.72 + difflib.SequenceMatcher(None, na, x['na']).ratio()*0.28
        if s > best[0]: best = (s, x)
    return best
