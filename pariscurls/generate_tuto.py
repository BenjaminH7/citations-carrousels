#!/usr/bin/env python3
"""Carrousel « tuto » Paris Curls (1080x1350), tiré d'un article du journal.

Usage : python3 pariscurls/generate_tuto.py spec.json out_dir/

spec.json :
{
  "id": "2026-10-09-sotc",
  "kicker": "Technique",                      # catégorie en petites capitales
  "title": "Scrunch out the crunch",           # nom de la technique, court
  "hook": "Casser le gel sans perdre ses boucles.",
  "answer": "Réponse courte, 25 à 45 mots, chiffrée.",
  "steps": [                                   # 4 à 6 étapes, 2 par slide
    {"title": "Vérifiez le séchage à 100 %", "detail": "Pressez une mèche 3 s. Fraîche ? Attendez 15 à 30 min."},
    ...
  ],
  "mistake": "L'erreur la plus fréquente, en une ou deux phrases.",
  "product": {"name": "Le Bain d'Huile", "line": "romarin & ortie", "why": "Pourquoi il aide à cette étape, une phrase."},
  "handle": "@pariscurls"
}

Slides : couverture · en bref · étapes (2 par slide) · l'erreur n° 1 · le produit · enregistre.
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
from generate import typo, THIN, best, justify, tl, draw_word, font as serif  # noqa: E402

W, H = 1080, 1350
BG = (244, 239, 232)      # crème
INK = (31, 26, 23)        # brun très sombre
SOFT = (138, 128, 121)    # taupe
ACCENT = (140, 90, 60)    # caramel
M = 120
COLW = W - 2 * M
_sans = {}


def sans(size, weight=400):
    k = (size, weight)
    if k not in _sans:
        f = ImageFont.truetype(os.path.join(HERE, "fonts", "Inter.ttf"), size)
        f.set_variation_by_axes([min(32, max(14, size)), weight])
        _sans[k] = f
    return _sans[k]


def clean(s):
    return typo(s).replace(THIN, " ")


def wrap(d, text, f, maxw):
    words, lines, cur = clean(text).split(" "), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if d.textlength(t, font=f) <= maxw or not cur:
            cur = t
        else:
            lines.append(cur); cur = w
    return lines + [cur]


def block(d, text, x, y, f, lh, fill=INK, maxw=COLW):
    for ln in wrap(d, text, f, maxw):
        d.text((x, y), ln, font=f, fill=fill)
        y += f.size * lh
    return y


def frame(spec, n, total):
    im = Image.new("RGB", (W, H), BG); d = ImageDraw.Draw(im)
    s = sans(24, 600)
    brand = "P A R I S   C U R L S"
    d.text((M, 84), brand, font=s, fill=INK)
    num = f"{n:02d} / {total:02d}"
    d.text((W - M - d.textlength(num, font=sans(24, 500)), 84), num, font=sans(24, 500), fill=SOFT)
    d.line([(M, H - 118), (W - M, H - 118)], fill=(222, 214, 204), width=2)
    d.text((M, H - 96), spec.get("handle", "@pariscurls"), font=sans(24, 500), fill=SOFT)
    if n < total:
        a = "glisse  →"
        d.text((W - M - d.textlength(a, font=sans(24, 500)), H - 96), a, font=sans(24, 500), fill=SOFT)
    return im, d


def slide_cover(spec, total):
    im, d = frame(spec, 1, total)
    k = spec.get("kicker", "Technique").upper()
    kf = sans(28, 600)
    ks = " ".join(k)  # espacement des lettres
    y = 380
    d.text((M, y), ks, font=kf, fill=ACCENT); y += 90
    tf = serif(108)
    for ln in wrap(d, spec["title"], tf, COLW):
        d.text((M - 4, y), ln, font=tf, fill=INK); y += 118
    y += 30
    d.line([(M, y), (M + 80, y)], fill=ACCENT, width=3); y += 50
    block(d, spec["hook"], M, y, serif(50, True), 1.3, fill=INK)
    return im


def slide_answer(spec, n, total):
    im, d = frame(spec, n, total)
    y = 260
    d.text((M, y), " ".join("EN BREF"), font=sans(28, 600), fill=ACCENT); y += 100
    f = serif(54)
    lines, colw = best(d, spec["answer"], f)
    justify(d, lines, colw, M, y, f, 1.42)
    return im


def slide_steps(spec, steps, start, n, total):
    im, d = frame(spec, n, total)
    tf, df, nf = sans(44, 650), sans(37, 400), serif(124)
    x, mw = M + 190, COLW - 190
    hs = []
    for st in steps:
        h = len(wrap(d, st["title"], tf, mw)) * 44 * 1.25 + 16 + len(wrap(d, st["detail"], df, mw)) * 37 * 1.45
        hs.append(max(h, 140))
    gap = 110
    label_h = 120
    total_h = label_h + sum(hs) + gap * (len(steps) - 1)
    y = max(230, (H - total_h) / 2 - 20)
    d.text((M, y), " ".join("LA MÉTHODE"), font=sans(28, 600), fill=ACCENT); y += label_h
    for st, h in zip(steps, hs):
        d.text((M, y - 14), f"{start:02d}", font=nf, fill=ACCENT)
        yy = block(d, st["title"], x, y + 8, tf, 1.25, fill=INK, maxw=mw)
        block(d, st["detail"], x, yy + 16, df, 1.45, fill=INK, maxw=mw)
        y += h + gap
        start += 1
    return im


def slide_mistake(spec, n, total):
    im, d = frame(spec, n, total)
    y = 330
    d.text((M, y), " ".join("L'ERREUR N° 1"), font=sans(28, 600), fill=ACCENT); y += 110
    f = serif(58)
    lines, colw = best(d, spec["mistake"], f)
    justify(d, lines, colw, M, y, f, 1.38)
    return im


def slide_product(spec, n, total):
    im, d = frame(spec, n, total)
    p = spec["product"]
    y = 330
    d.text((M, y), " ".join("NOTRE ALLIÉ"), font=sans(28, 600), fill=ACCENT); y += 100
    for ln in wrap(d, p["name"], serif(84), COLW):
        d.text((M - 3, y), ln, font=serif(84), fill=INK); y += 96
    if p.get("line"):
        d.text((M, y + 4), clean(p["line"]), font=serif(46, True), fill=SOFT); y += 80
    y += 40
    d.line([(M, y), (M + 80, y)], fill=ACCENT, width=3); y += 50
    y = block(d, p["why"], M, y, sans(36, 400), 1.45)
    y += 50
    d.text((M, y), "Lien en bio  →", font=sans(34, 650), fill=ACCENT)
    return im


def slide_save(spec, n, total):
    im, d = frame(spec, n, total)
    y = 470
    for ln in ["Enregistre-le", "pour ta prochaine", "wash day."]:
        d.text((M - 3, y), ln, font=serif(88), fill=INK); y += 100
    y += 50
    d.line([(M, y), (M + 80, y)], fill=ACCENT, width=3); y += 50
    block(d, "Une technique de boucles par jour, chiffrée et sourcée.", M, y, sans(34, 400), 1.45, fill=SOFT)
    return im


def render(spec, out):
    os.makedirs(out, exist_ok=True)
    steps = spec["steps"][:6]
    groups = [steps[i:i + 2] for i in range(0, len(steps), 2)]
    total = 1 + 1 + len(groups) + 1 + (1 if spec.get("product") else 0) + 1
    slides, n = [slide_cover(spec, total)], 2
    slides.append(slide_answer(spec, n, total)); n += 1
    k = 1
    for g in groups:
        slides.append(slide_steps(spec, g, k, n, total)); n += 1; k += len(g)
    slides.append(slide_mistake(spec, n, total)); n += 1
    if spec.get("product"):
        slides.append(slide_product(spec, n, total)); n += 1
    slides.append(slide_save(spec, n, total))
    paths = []
    for i, im in enumerate(slides, 1):
        p = os.path.join(out, f"{spec['id']}-{i:02d}.jpg")
        im.save(p, quality=95, subsampling=0)
        paths.append(p)
    return paths


if __name__ == "__main__":
    for p in render(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2]):
        print(p)
