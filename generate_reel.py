#!/usr/bin/env python3
"""Reel vertical (1080x1920, 9:16) à partir du même spec JSON que le carrousel.

Usage : python3 generate_reel.py spec.json out_dir/

Les slides du carrousel sont posées au centre d'une page blanche 9:16 : le texte reste
dans la zone sûre (hors légende et boutons Instagram). Chaque citation reste affichée le
temps de la lire calmement, avec un fondu enchaîné entre les plans. La vidéo est muette
(piste audio silencieuse) : la musique est ajoutée par Instagram via le catalogue audio.
"""
import json, os, shutil, subprocess, sys, tempfile
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from generate import build_slides, W, H  # noqa: E402

RW, RH = 1080, 1920


def ffmpeg_bin():
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        subprocess.run([sys.executable, "-m", "pip", "install", "-q", "--break-system-packages", "imageio-ffmpeg"], check=True)
        import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()
FADE = 0.6


def durations(spec):
    qs = spec["quotes"][:8]
    d = [2.6]                                         # couverture : accroche rapide
    for q in qs:
        words = len(q["quote"].split())
        d.append(max(3.6, min(7.5, 1.6 + words / 4.0)))   # ~4 mots/s : lecture posée, Reel autour de 30 s
    d.append(3.5)                                     # bande-son + appel à l'enregistrement
    return d


def render_reel(spec, out):
    os.makedirs(out, exist_ok=True)
    slides, durs = build_slides(spec), durations(spec)
    tmp = tempfile.mkdtemp()
    frames = []
    for i, im in enumerate(slides):
        canvas = Image.new("RGB", (RW, RH), (255, 255, 255))
        canvas.paste(im, (0, (RH - H) // 2 - 60))   # léger décalage vers le haut : la légende Instagram couvre le bas
        p = os.path.join(tmp, f"f{i:02d}.png")
        canvas.save(p)
        frames.append(p)
    # chaque plan dure d + FADE pour que les fondus ne rognent pas le temps de lecture
    args = [ffmpeg_bin(), "-y", "-loglevel", "error"]
    for p, d in zip(frames, durs):
        args += ["-loop", "1", "-t", f"{d + FADE:.2f}", "-framerate", "30", "-i", p]
    total = sum(durs) + FADE
    args += ["-f", "lavfi", "-t", f"{total:.2f}", "-i", "anullsrc=r=44100:cl=stereo"]
    chain, prev, offset = [], "0:v", 0.0
    for i in range(1, len(frames)):
        offset += durs[i - 1]
        lbl = f"v{i}"
        chain.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={FADE}:offset={offset:.2f}[{lbl}]")
        prev = lbl
    chain.append(f"[{prev}]format=yuv420p[vout]")
    out_path = os.path.join(out, f"{spec['id']}-reel.mp4")
    args += ["-filter_complex", ";".join(chain), "-map", "[vout]", "-map", f"{len(frames)}:a",
             "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-r", "30",
             "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", out_path]
    subprocess.run(args, check=True)
    return out_path, total


if __name__ == "__main__":
    path, total = render_reel(json.load(open(sys.argv[1], encoding="utf-8")), sys.argv[2])
    print(path, f"{total:.1f}s")
