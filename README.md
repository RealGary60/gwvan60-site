# GWVan60 website

Source for [gwvan60.com](https://gwvan60.com): Gary VanOpdorp's 3D puzzle and miniature model builds, reviews, and the *Active Meditation Through Model Building* white paper.

- `data/builds.json`: one entry per kit (YouTube/TikTok/Instagram ids, Reddit review link, builder credit).
- `build.py`: generates the site into `docs/`, which GitHub Pages serves. Requires Python 3 + Pillow.
- `static/`: CSS, JS, images, the white paper PDF.

To add a build: add an entry to `data/builds.json`, run `python build.py`, then commit and push.
Preview locally with `python build.py --serve` (http://localhost:8060).
