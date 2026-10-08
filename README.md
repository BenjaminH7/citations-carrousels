# Citations carrousels

Moteur des carrousels de citations littéraires (domaine public), publiés chaque jour sur Instagram via Metricool.

- `generate.py` : spec JSON → couverture + une citation par slide + bande-son, 1080×1350, typographie de livre classique (EB Garamond, césure française, espaces fines).
- `generate_reel.py` : même spec → Reel vertical 1080×1920 (~30 s, fondus enchaînés, piste muette : la musique vient du catalogue Instagram).
- `historique.json` : citations déjà publiées, pour ne jamais republier la même.
- `posts/AAAA-MM-JJ/` : visuels du jour, servis à Metricool via raw.githubusercontent.com.

```
pip install -r requirements.txt
python3 generate.py spec.json posts/2026-10-09/
```

## Paris Curls

- `pariscurls/generate_tuto.py` : article du journal → carrousel « tuto » 1080×1350 (crème, serif + Inter, étapes chiffrées, produit associé).
- `pariscurls/historique.json` : articles déjà transformés en carrousel.
- `pariscurls/posts/AAAA-MM-JJ/` : visuels du jour.
