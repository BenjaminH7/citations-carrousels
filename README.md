# Citations carrousels

Moteur des carrousels de citations littéraires (domaine public), publiés chaque jour sur Instagram via Metricool.

- `generate.py` : spec JSON → couverture + une citation par slide + bande-son, 1080×1350, typographie de livre classique (EB Garamond, césure française, espaces fines).
- `historique.json` : citations déjà publiées, pour ne jamais republier la même.
- `posts/AAAA-MM-JJ/` : visuels du jour, servis à Metricool via raw.githubusercontent.com.

```
pip install -r requirements.txt
python3 generate.py spec.json posts/2026-10-09/
```
