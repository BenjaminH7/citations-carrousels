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
    # poésie : séparer les vers par " / " -> composés vers par vers
    ...                                   # 4 à 8 citations
  ],
  "music": "Gymnopédie n° 1, Erik Satie"
}

Slides : couverture · une citation par slide · appel à l'enregistrement
(la bande-son n'est annoncée que dans le Reel, où elle est réellement entendue).
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


def best(d, text, f):
    """Essaie plusieurs largeurs de colonne, garde la plus belle composition."""
    opts = []
    for dw in range(-30, 61, 10):
        colw = COLW - dw
        lines, sc = compose(d, text, f, colw)
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


def verse_lines(d, verses, f, maxw):
    """Vers par vers ; un vers trop long continue à la ligne avec un retrait."""
    out = []
    for v in verses:
        words, cur = v.split(" "), []
        for w in words:
            if cur and tl(d, " ".join(cur + [w]).replace(" ", ""), f) + d.textlength(" ", font=f) * len(cur) > maxw:
                out.append((cur, len(out) and out[-1][2] == v and True, v))
                cur = [w]
            else:
                cur.append(w)
        out.append((cur, False, v))
    # marque les lignes de continuation (même vers que la ligne précédente)
    res, prev = [], None
    for words, _, v in out:
        res.append((words, v == prev))
        prev = v
    return res


def draw_line(d, words, x, y, f, fill=INK):
    sp = d.textlength(" ", font=f)
    for w in words:
        draw_word(d, x, y, w, f, fill)
        x += tl(d, w, f) + sp


def line_w(d, words, f):
    return sum(tl(d, w, f) for w in words) + d.textlength(" ", font=f) * (len(words) - 1)


def slide_quote(q, n):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    text = q["quote"].strip()
    sc, it = font(42), font(34, True)
    src = typo(f'{q["work"]}, {q["year"]}').replace(THIN, " ")
    VSEP = r"[\s\u00a0\u202f]+/[\s\u00a0\u202f]+"
    if re.search(VSEP, text):                           # poésie : composée vers par vers
        verses = [typo(v.strip()) for v in re.split(VSEP, text) if v.strip()]
        maxw = W - 2 * 120
        size = 48
        while size > 40:
            f = font(size)
            if max(line_w(d, v.split(" "), f) for v in verses) <= maxw:
                break
            size -= 1
        f, lh = font(size), 1.45
        lines = verse_lines(d, verses, f, maxw)
        blockw = max(line_w(d, w, f) for w, cont in lines)
        blockw = max(blockw, d.textlength(q["author"], font=sc, features=["smcp"]), d.textlength(src, font=it))
        x0 = (W - blockw) / 2
        y = (H - (len(lines) * size * lh + 60 + 44 + 46)) / 2 - 50
        for words, cont in lines:
            # rejet d'un vers trop long : aligné à droite, comme dans les éditions classiques
            draw_line(d, words, (x0 + blockw - line_w(d, words, f)) if cont else x0, y, f)
            y += size * lh
        right = x0 + blockw
    else:                                               # prose : justifiée avec césure
        f, lh = font(48), 1.48
        lines, colw = best(d, text, f)
        x0 = (W - colw) / 2
        y = (H - (len(lines) * f.size * lh + 60 + 44 + 46)) / 2 - 50
        y = justify(d, lines, colw, x0, y, f, lh)
        right = x0 + colw
    nw = d.textlength(q["author"], font=sc, features=["smcp"])
    d.text((right - nw, y + 60), q["author"], font=sc, fill=INK, features=["smcp"])
    d.text((right - d.textlength(src, font=it), y + 112), src, font=it, fill=GREY)
    folio(d, n)
    return im


def slide_music(spec, n):
    """Dernière slide du Reel : la musique y est réellement entendue."""
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


def slide_end(n):
    """Dernière slide du carrousel : pas de musique annoncée, puisqu'on ne l'entend pas."""
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    y = H / 2 - 110
    centered(d, "❧", y, font(34), GREY); y += 110
    centered(d, "Enregistre-les.", y, font(40)); y += 60
    centered(d, "Tu en auras besoin un jour.", y, font(40))
    folio(d, n)
    return im


def build_slides(spec, reel=False):
    qs = spec["quotes"][:8]                 # Instagram : 10 slides max
    slides = [slide_cover(spec, len(qs))]
    slides += [slide_quote(q, i) for i, q in enumerate(qs, 2)]
    slides.append(slide_music(spec, len(qs) + 2) if reel else slide_end(len(qs) + 2))
    return slides


def render(spec, out):
    os.makedirs(out, exist_ok=True)
    slides = build_slides(spec)
    paths = []
    for n, im in enumerate(slides, 1):
        p = os.path.join(out, f"{spec['id']}-{n:02d}.jpg")
        im.save(p, quality=95, subsampling=0)
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]):
        print(p)
