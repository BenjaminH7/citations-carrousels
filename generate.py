#!/usr/bin/env python3
"""Carrousel Instagram, typographie de livre classique, noir sur blanc.

Usage : python3 generate.py spec.json out_dir/

spec.json :
{
  "id": "2026-10-09-baudelaire",
  "quote": "Il faut être toujours ivre. Tout est là : c'est l'unique question.",
  "author": "Baudelaire",                 # nom court sous la citation
  "author_full": "Charles Baudelaire",
  "work": "Le Spleen de Paris",
  "year": "1869",
  "context": "2-3 phrases",
  "reading": "2-3 phrases",
  "music": "Gnossienne n° 1, Erik Satie"
}

Slides : 1 citation · 2 source + contexte · 3 lecture · 4 bande-son.
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
def slide_quote(spec):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    f, lh = font(48), 1.48
    lines, colw = best(d, spec["quote"], f)
    x0 = (W - colw) / 2
    block = len(lines) * f.size * lh + 60 + 44
    y = (H - block) / 2 - 50
    y = justify(d, lines, colw, x0, y, f, lh)
    sc = font(42)
    name = spec["author"]
    nw = d.textlength(name, font=sc, features=["smcp"])
    d.text((x0 + colw - nw, y + 60), name, font=sc, fill=INK, features=["smcp"])
    return im


def slide_text(spec, n, head, sub, body):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    f, lh = font(40), 1.5
    lines, colw = best(d, body, f)
    x0 = (W - colw) / 2
    hsz, ssz = 34, 38
    block = hsz * 1.4 + (ssz * 1.4 if sub else 0) + 110 + len(lines) * f.size * lh
    y = (H - block) / 2 - 40
    centered(d, head, y, font(hsz), GREY, ["smcp"]); y += hsz * 1.4
    if sub:
        centered(d, typo(sub).replace(THIN, " "), y + 4, font(ssz, True), GREY); y += ssz * 1.4
    centered(d, "❧", y + 28, font(34), GREY); y += 110
    justify(d, lines, colw, x0, y, f, lh)
    folio(d, n)
    return im


def slide_music(spec, n):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    y = H / 2 - 190
    centered(d, "À écouter avec", y, font(34), GREY, ["smcp"]); y += 70
    centered(d, typo(spec["music"]).replace(THIN, " "), y, font(46, True)); y += 150
    centered(d, "❧", y, font(34), GREY); y += 110
    centered(d, "Enregistre-la.", y, font(40)); y += 60
    centered(d, "Tu en auras besoin un jour.", y, font(40))
    folio(d, n)
    return im


def render(spec, out):
    os.makedirs(out, exist_ok=True)
    slides = [
        slide_quote(spec),
        slide_text(spec, 2, spec["author_full"], f'{spec["work"]}, {spec["year"]}', spec["context"]),
        slide_text(spec, 3, "Ce qu’elle nous dit", None, spec["reading"]),
        slide_music(spec, 4),
    ]
    paths = []
    for n, im in enumerate(slides, 1):
        p = os.path.join(out, f"{spec['id']}-{n}.jpg")
        im.save(p, quality=95, subsampling=0)
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]):
        print(p)
