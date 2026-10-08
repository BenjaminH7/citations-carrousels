#!/usr/bin/env python3
"""Carrousel Instagram thématique : plusieurs citations sur un même thème.
Typographie de livre classique, noir sur blanc.

Usage : python3 generate.py spec.json out_dir/

spec.json :
{
  "id": "2026-10-09-solitude",
  "title": "La solitude",
  "subtitle": "par ceux qui l'ont écrite",
  "quotes": [
    {"quote": "...", "author": "Pascal", "work": "Pensées", "year": "1670"},
    # vers : séparer par "\n" → un vers par ligne, au fer à gauche
    ...                                   # 4 à 8 citations
  ],
  "music": "Gymnopédie n° 1, Erik Satie"
}

Slides : couverture · une citation par slide · bande-son + appel à l'enregistrement.
Typographie : EB Garamond, justification avec césure française, espaces fines
insécables avant ; ! ? et dans les guillemets, insécable avant :, apostrophe courbe.
"""
import json, os, re, sys
import pyphen
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, "fonts")
W, H = 1080, 1350
BG, INK, GREY = (255, 255, 255), (20, 20, 20), (135, 135, 135)
LEFT = 205
COLW = W - 2 * LEFT
NB, THIN = " ", " "          # THIN n'existe pas dans la police : dessiné à la main
HY = pyphen.Pyphen(lang="fr_FR", left=3, right=3)
TRAIL = ",.;:!?…»)" + NB + THIN

_cache = {}


def font(size, italic=False):
    k = (size, italic)
    if k not in _cache:
        f = ImageFont.truetype(os.path.join(FD, "EBGaramond-Italic.ttf" if italic else "EBGaramond.ttf"), size)
        f.set_variation_by_axes([400])
        _cache[k] = f
    return _cache[k]


# ---------- typographie française ----------
def typo(t):
    t = t.strip().replace("'", "’").replace("...", "…")
    t = re.sub(r'"([^"]+)"', r"« \1 »", t)
    t = re.sub(r"«\s*", "«" + THIN, t)
    t = re.sub(r"\s*»", THIN + "»", t)
    t = re.sub(r"(?<=\S)\s*([;!?])", THIN + r"\1", t)
    t = re.sub(r"(?<=\S)\s*:(?=\s|$)", NB + ":", t)
    t = re.sub(r"\bn°\s*", "n°" + NB, t)
    return re.sub(r" {2,}", " ", t)


def tl(d, s, f):
    """Largeur d'un mot, espaces fines comprises."""
    parts = s.split(THIN)
    return sum(d.textlength(p, font=f) for p in parts if p) + (len(parts) - 1) * f.size * 0.17


def draw_word(d, x, y, s, f, fill):
    for i, p in enumerate(s.split(THIN)):
        if i:
            x += f.size * 0.17
        if p:
            d.text((x, y), p, font=f, fill=fill)
            x += d.textlength(p, font=f)


def hyphen_splits(word):
    """Coupures possibles (début-, fin), du plus long début au plus court."""
    out = []
    # mots composés : coupure sur le trait d'union existant
    if "-" in word.strip("-"):
        k = word.rindex("-", 0, len(word) - 1)
        while k > 0:
            out.append((word[:k + 1], word[k + 1:]))
            k = word.rfind("-", 0, k)
        return out
    m = re.match(r"^([«(" + THIN + r"]*(?:[^’]*’)?)([A-Za-zÀ-ÿœŒæÆ]+)([" + re.escape(TRAIL) + r"]*)$", word)
    if not m or m.group(2)[0].isupper():
        return out
    pre, core, post = m.group(1), m.group(2), m.group(3)
    return [(pre + a + "-", b + post) for a, b in HY.iterate(core)]


# ---------- composition ----------
def compose(d, text, f, colw):
    """Coupe en lignes justifiables. Renvoie [(mots, derniere_ligne)] et un score (plus bas = mieux)."""
    sp = d.textlength(" ", font=f)
    words = [w for w in typo(text).split(" ") if w]
    lines, cur, score, i = [], [], 0.0, 0
    while i < len(words):
        w = words[i]
        trial = cur + [w]
        if not cur or sum(tl(d, x, f) for x in trial) + sp * (len(trial) - 1) <= colw:
            cur, i = trial, i + 1
            continue
        used = sum(tl(d, x, f) for x in cur)
        gap = (colw - used) / max(1, len(cur) - 1)
        if gap > sp * 1.35:  # trop d'air : on tente une césure du mot suivant
            for a, b in hyphen_splits(w):
                g2 = (colw - used - tl(d, a, f)) / len(cur)
                if g2 >= sp * 0.85:
                    cur.append(a)
                    words[i] = b
                    used += tl(d, a, f)
                    gap = (colw - used) / max(1, len(cur) - 1)
                    score += 0.6
                    break
        score += max(0, gap / sp - 1) ** 2 + max(0, 0.9 - gap / sp) * 4
        if len(re.sub(r"[^\wÀ-ÿ]", "", cur[-1])) <= 2 and not cur[-1][-1] in "-,.;:!?»…":
            score += 1.5  # pas de mot d'une ou deux lettres en bout de ligne
        lines.append((cur, False))
        cur = []
    lines.append((cur, True))
    last_w = sum(tl(d, x, f) for x in cur) + sp * (len(cur) - 1)
    if len(lines) > 1 and (len(cur) == 1 or last_w < colw * 0.22):
        score += 3  # ligne creuse finale
    return lines, score


def compose_dp(d, text, f, colw):
    """Coupure optimale (programmation dynamique) : minimise la somme des pénalités de ligne."""
    sp = d.textlength(" ", font=f)
    words = [w for w in typo(text).split(" ") if w]
    n = len(words)
    W_ = [tl(d, w, f) for w in words]
    splits = [hyphen_splits(w) for w in words]
    INF = float("inf")
    memo = {}

    def line_cost(items, hyph, last):
        used = sum(tl(d, x, f) for x in items)
        if used + sp * (len(items) - 1) > colw and len(items) > 1:
            return None
        if last:
            lw = used + sp * (len(items) - 1)
            return 3.0 if (len(items) == 1 or lw < colw * 0.22) else 0.0
        if len(items) == 1:
            return 50.0
        gap = (colw - used) / (len(items) - 1)
        c = max(0, gap / sp - 1) ** 2 + max(0, 0.9 - gap / sp) * 4 + (0.6 if hyph else 0)
        if not hyph and len(re.sub(r"[^\wÀ-ÿ]", "", items[-1])) <= 2 and items[-1][-1] not in "-,.;:!?»…":
            c += 1.5
        return c

    def solve(i, head):
        key = (i, head)
        if key in memo:
            return memo[key]
        res = (INF, None)
        start = [head] if head is not None else []
        j0 = i if head is None else i + 1
        items = list(start)
        j = j0
        while True:
            # fin de ligne après le mot j-1 complet
            if items:
                last = j >= n
                c = line_cost(items, False, last)
                if c is None:
                    break
                sub = (0.0, []) if last else solve(j, None)
                if c + sub[0] < res[0]:
                    res = (c + sub[0], [(list(items), last)] + sub[1])
                if last:
                    break
            if j >= n:
                break
            # fin de ligne sur une césure du mot j
            if items:
                for a, b in splits[j]:
                    c = line_cost(items + [a], True, False)
                    if c is None:
                        continue
                    sub = solve(j, b)
                    if c + sub[0] < res[0]:
                        res = (c + sub[0], [(items + [a], False)] + sub[1])
            items = items + [words[j]]
            j += 1
        memo[key] = res
        return res

    sc, lines = solve(0, None)
    return lines, sc


def best(d, text, f):
    """Essaie plusieurs largeurs de colonne, garde la plus belle composition."""
    opts = []
    for dw in range(-110, 111, 10):
        colw = COLW - dw
        for comp in (compose, compose_dp):
            lines, sc = comp(d, text, f, colw)
            if lines:
                opts.append((sc + abs(dw) * 0.004, lines, colw))
    _, lines, colw = min(opts, key=lambda o: o[0])
    return lines, colw


def justify(d, lines, colw, x0, y, f, lh, fill=INK):
    sp = d.textlength(" ", font=f)
    for words, last in lines:
        used = sum(tl(d, w, f) for w in words)
        gap = sp if (last or len(words) == 1) else (colw - used) / (len(words) - 1)
        x = x0
        for w in words:
            draw_word(d, x, y, w, f, fill)
            x += tl(d, w, f) + gap
        y += f.size * lh
    return y


def centered(d, s, y, f, fill=INK, features=None):
    w = d.textlength(s, font=f, features=features)
    d.text(((W - w) / 2, y), s, font=f, fill=fill, features=features)


def folio(d, n):
    centered(d, str(n), H - 120, font(30), GREY)


# ---------- slides ----------
def wrap_centered(d, text, f, maxw):
    lines, cur = [], ""
    for w in typo(text).replace(THIN, " ").split(" "):
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


def slide_cover(spec, count):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    tf = font(76)
    tl_ = wrap_centered(d, spec["title"], tf, COLW)
    sf = font(42, True)
    sl = wrap_centered(d, spec.get("subtitle", ""), sf, COLW) if spec.get("subtitle") else []
    block = 50 + 80 + len(tl_) * 76 * 1.2 + 30 + len(sl) * 42 * 1.4
    y = (H - block) / 2 - 40
    nums = ["", "", "", "trois", "quatre", "cinq", "six", "sept", "huit", "neuf", "dix"]
    label = f"{nums[count].capitalize()} citations" if count < len(nums) else f"{count} citations"
    centered(d, label, y, font(34), GREY, ["smcp"]); y += 50
    centered(d, "❧", y + 10, font(34), GREY); y += 80
    for ln in tl_:
        centered(d, ln, y, tf); y += 76 * 1.2
    y += 30
    for ln in sl:
        centered(d, ln, y, sf, GREY); y += 42 * 1.4
    return im


def slide_quote(q, n):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    f, lh = font(48), 1.48
    if "\n" in q["quote"]:              # vers : un vers par ligne, au fer à gauche
        lines = [([w for w in typo(v).split(" ") if w], True) for v in q["quote"].split("\n")]
        sp = d.textlength(" ", font=f)
        colw = max(sum(tl(d, w, f) for w in ws) + sp * (len(ws) - 1) for ws, _ in lines)
        if colw > W - 2 * 120:          # vers trop long : retour à la prose justifiée
            lines, colw = best(d, q["quote"].replace("\n", " / "), f)
    else:
        lines, colw = best(d, q["quote"], f)
    x0 = (W - colw) / 2
    block = len(lines) * f.size * lh + 60 + 44 + 46
    y = (H - block) / 2 - 50
    y = justify(d, lines, colw, x0, y, f, lh)
    sc = font(42)
    nw = d.textlength(q["author"], font=sc, features=["smcp"])
    d.text((x0 + colw - nw, y + 60), q["author"], font=sc, fill=INK, features=["smcp"])
    src = typo(f'{q["work"]}, {q["year"]}').replace(THIN, " ")
    it = font(34, True)
    d.text((x0 + colw - d.textlength(src, font=it), y + 112), src, font=it, fill=GREY)
    folio(d, n)
    return im


def slide_music(spec, n):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    y = H / 2 - 190
    centered(d, "À écouter avec", y, font(34), GREY, ["smcp"]); y += 70
    for ln in wrap_centered(d, spec["music"], font(46, True), COLW):
        centered(d, ln, y, font(46, True)); y += 64
    y += 86
    centered(d, "❧", y, font(34), GREY); y += 110
    centered(d, "Enregistre-les.", y, font(40)); y += 60
    centered(d, "Tu en auras besoin un jour.", y, font(40))
    folio(d, n)
    return im


def render(spec, out):
    os.makedirs(out, exist_ok=True)
    qs = spec["quotes"][:8]                 # Instagram : 10 slides max
    slides = [slide_cover(spec, len(qs))]
    slides += [slide_quote(q, i) for i, q in enumerate(qs, 2)]
    slides.append(slide_music(spec, len(qs) + 2))
    paths = []
    for n, im in enumerate(slides, 1):
        p = os.path.join(out, f"{spec['id']}-{n:02d}.jpg")
        im.save(p, quality=95, subsampling=0)
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]):
        print(p)
