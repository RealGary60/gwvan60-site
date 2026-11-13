"""Build the GWVan60 static site.

Usage:  python build.py            (writes the site to ./docs, which GitHub Pages serves)
        Publish:  git add -A && git commit -m "Update site" && git push
        python build.py --serve    (build, then preview at http://localhost:8060)

Content lives in data/builds.json. To add a new video, add one entry there and rebuild.
Thumbnails are fetched from YouTube once and cached in static/img/thumbs/.
"""
import html, json, re, shutil, sys, urllib.request
from datetime import date
from io import BytesIO
from pathlib import Path

# ---- the one setting to change at go-live ---------------------------------
SITE_DOMAIN = "gwvan60.com"          # primary domain; the other domains forward here
# ---------------------------------------------------------------------------
SITE_URL = f"https://{SITE_DOMAIN}"
ROOT = Path(__file__).parent
DIST = ROOT / "docs"          # GitHub Pages serves this folder
STATIC = ROOT / "static"
THUMBS = STATIC / "img" / "thumbs"
HELD = ROOT / "data" / "held"     # git-ignored: kits/reviews kept off the site until publish_after

SOCIAL = [
    ("YouTube", "https://www.youtube.com/@GWVan60", "@GWVan60"),
    ("TikTok", "https://www.tiktok.com/@gwvan60", "@gwvan60"),
    ("Instagram", "https://www.instagram.com/gwvan/", "@gwvan"),
    ("Reddit", "https://www.reddit.com/r/rokrpuzzles/", "r/ROKRPuzzles"),
]
NAV = [("Builds", "/builds/"), ("Reviews", "/reviews/"),
       ("Active Meditation", "/active-meditation/"), ("Community", "/community/"), ("About", "/about/")]
WHITEPAPER = "/papers/active-meditation-through-model-building.pdf"
# Where clubs and kit makers can reach me. No email address on the public site.
CONTACT = [("YouTube", "https://www.youtube.com/@GWVan60", "@GWVan60"),
           ("Reddit", "https://www.reddit.com/user/GWVan60/", "u/GWVan60")]

e = lambda s: html.escape(str(s), quote=True)


# ---------------------------------------------------------------- helpers ---
def title_of(b):
    return " ".join(x for x in (b["brand"], b["kit"], b["model"]) if x)


def fmt_date(s):
    d = date.fromisoformat(s)
    return f"{d:%B} {d.day}, {d.year}"


def fetch_thumb(vid, vertical):
    """Cache a YouTube thumbnail as WebP. Shorts get the vertical 'oardefault' image."""
    out = THUMBS / f"{vid}.webp"
    if out.exists():
        return
    from PIL import Image
    for name in (["oardefault", "maxresdefault", "hqdefault"] if vertical else ["maxresdefault", "sddefault", "hqdefault"]):
        try:
            data = urllib.request.urlopen(f"https://i.ytimg.com/vi/{vid}/{name}.jpg", timeout=20).read()
        except Exception:
            continue
        im = Image.open(BytesIO(data)).convert("RGB")
        im.thumbnail((540, 960) if vertical else (960, 540))
        im.save(out, "WEBP", quality=80)
        print("  thumb", vid, name, im.size)
        return
    print("  !! no thumbnail for", vid)


def thumb(vid):
    return f"/img/thumbs/{vid}.webp"


def video_label(b):
    """What kind of video a kit has, with its runtime: 'Full build · 34 min' or 'Short'."""
    if b.get("full"):
        mins = b.get("full_minutes")
        return f"Full build · {mins} min" if mins else "Full build"
    if b.get("short"):
        return "Short"
    return None


def cover(b):
    """Best picture for a build: its own photo, else its video thumbnail, else None (placeholder tile)."""
    if b.get("image"):
        return b["image"]
    vid = b["short"] or b["full"]
    return thumb(vid) if vid else None


# --------------------------------------------------------------- reviews ----
def load_review(slug):
    """Parse data/reviews/<slug>.md: intro paragraphs, then **Category: n/5** (or **Heading**) sections."""
    p = ROOT / "data" / "reviews" / f"{slug}.md"
    if not p.exists():
        p = HELD / f"{slug}.md"          # private, git-ignored (e.g. gifts not yet given)
    if not p.exists():
        return None
    return parse_md(p)


def parse_md(p):
    text = re.sub(r"<!--.*?-->", "", p.read_text(encoding="utf-8"), flags=re.S).strip()
    intro, sections = [], []
    for para in (x.strip() for x in re.split(r"\n\s*\n", text) if x.strip()):
        scored = re.fullmatch(r"\*\*(.+?):\s*([\d.]+)\s*/\s*5\*\*", para)
        heading = re.fullmatch(r"\*\*([^*]+?)\*\*", para)
        if scored:
            sections.append({"name": scored.group(1), "score": float(scored.group(2)), "paras": []})
        elif heading:
            sections.append({"name": heading.group(1), "score": None, "paras": []})
        elif sections:
            sections[-1]["paras"].append(para)
        else:
            intro.append(para)
    overall = next((s["score"] for s in sections if s["score"] is not None and s["name"].lower().startswith("overall")), None)
    return {"intro": intro, "sections": sections, "overall": overall}


def num(x):
    return f"{x:g}"


def md_inline(p):
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", e(p))


def pips(score):
    whole = int(min(score, 5))
    half = score < 5 and score - int(score) >= .5
    out = '<i class="pip on"></i>' * whole + ('<i class="pip half"></i>' if half else "")
    out += '<i class="pip"></i>' * (5 - whole - (1 if half else 0))
    if score > 5:
        out += f'<span class="bonus">+{num(score - 5)}</span>'
    return f'<span class="pips" aria-hidden="true">{out}</span>'


def render_review(b, rv):
    archive = b.get("review_type") == "archive"
    parts = []
    if rv["overall"] is not None:
        verdict = f'<p class="verdict">{md_inline(b["verdict"])}</p>' if b.get("verdict") else ""
        parts.append(f'<div class="overall" aria-label="Overall rating {num(rv["overall"])} out of 5">'
                     f'<span class="overall-num">{num(rv["overall"])}<small>/5</small></span>'
                     f'<span class="overall-label">Overall rating{pips(rv["overall"])}</span>'
                     f'{verdict}</div>')
    scored = [s for s in rv["sections"] if s["score"] is not None and not s["name"].lower().startswith("overall")]
    if scored:
        rows = "".join(f'<li><span class="sc-name">{e(s["name"])}</span>{pips(s["score"])}<b>{num(s["score"])}/5</b></li>' for s in scored)
        parts.append(f'<ul class="scorecard" aria-label="Scores by category">{rows}</ul>')
    parts += [f"<p>{md_inline(p)}</p>" for p in rv["intro"]]
    for s in rv["sections"]:
        tag = f' <span class="score-tag">{num(s["score"])}/5</span>' if s["score"] is not None else ""
        parts.append(f'<h3>{e(s["name"])}{tag}</h3>' + "".join(f"<p>{md_inline(p)}</p>" for p in s["paras"]))
    if archive:
        parts.append('<p class="note">From the review archive: this is a summary of an earlier review. The full original wording was not recovered.</p>')
    if b["reddit"]:
        parts.append(f'<p class="ctas"><a class="btn ghost" href="{e(b["reddit"])}" rel="noopener">Read it on Reddit and join the discussion</a></p>')
    heading = "From the review archive" if archive else "My review"
    return f'<section class="review-full" id="review"><h2>{heading}</h2>{"".join(parts)}</section>'


def player(vid, vertical, label, start=None, end=None, poster=None):
    """Click-to-play facade: shows our cached thumbnail, loads YouTube only on click.
    start/end (seconds) limit playback to one segment of a longer video."""
    cls = "player vertical" if vertical else "player wide"
    seg = (f' data-start="{int(start)}"' if start else "") + (f' data-end="{int(end)}"' if end else "")
    return (f'<div class="{cls}"><button class="yt" data-id="{e(vid)}"{seg} aria-label="Play: {e(label)}">'
            f'<img src="{poster or thumb(vid)}" alt="" loading="lazy">'
            f'<span class="play" aria-hidden="true"><svg viewBox="0 0 68 48"><path d="M66.5 7.7a8.5 8.5 0 0 0-6-6C55.2.3 34 .3 34 .3S12.8.3 7.5 1.7a8.5 8.5 0 0 0-6 6C.2 13 .2 24 .2 24s0 11 1.3 16.3a8.5 8.5 0 0 0 6 6C12.8 47.7 34 47.7 34 47.7s21.2 0 26.5-1.4a8.5 8.5 0 0 0 6-6C67.8 35 67.8 24 67.8 24s0-11-1.3-16.3z" fill="#e8c766"/><path d="M27 34V14l18 10z" fill="#0d1626"/></svg></span>'
            f'</button></div>')


def builder_line(b):
    if b["builder"] == "gary":
        return "I built this one"
    if b["builder"] == "wife":
        return "Built by the love of my life"
    return None


# --------------------------------------------------------------- layout -----
def page(path, title, desc, body, og_image=None, active=None):
    full_title = f"{title} | GWVan60" if title else "GWVan60 | 3D Puzzles & Miniature Models"
    og = og_image or "/img/logo-512.png"
    nav = "".join(
        f'<a href="{href}"{" aria-current=\"page\"" if active == label else ""}>{label}</a>' for label, href in NAV)
    social = "".join(f'<a href="{u}" rel="me noopener">{n} <span>{h}</span></a>' for n, u, h in SOCIAL)
    doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(full_title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="canonical" href="{SITE_URL}{path}">
<meta property="og:type" content="website">
<meta property="og:site_name" content="GWVan60">
<meta property="og:title" content="{e(full_title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{SITE_URL}{path}">
<meta property="og:image" content="{SITE_URL}{og}">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#0d1626">
<link rel="icon" type="image/png" href="/img/favicon.png">
<link rel="apple-touch-icon" href="/img/apple-touch-icon.png">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Source+Sans+3:wght@400;600&display=swap">
<link rel="stylesheet" href="/css/site.css">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
<header class="site-head">
  <div class="wrap head-row">
    <a class="brand" href="/"><img src="/img/logo-256.webp" alt="" width="44" height="44"><span>GWVan60</span></a>
    <button class="menu-btn" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav" class="nav">{nav}</nav>
  </div>
</header>
<main id="main">
{body}
</main>
<footer class="site-foot">
  <div class="wrap">
    <div class="foot-card">
      <p class="foot-lines">3D Puzzles &bull; Miniature Models<br>More Builds &bull; Reviews &bull; Repairs</p>
      <hr>
      <div class="social">{social}</div>
      <p class="star" aria-hidden="true">&#10022;</p>
    </div>
    <p class="copy">&copy; {date.today().year} Gary VanOpdorp &middot; GWVan60</p>
  </div>
</footer>
<script src="/js/site.js" defer></script>
</body>
</html>
"""
    out = DIST / path.lstrip("/") / "index.html" if path.endswith("/") else DIST / path.lstrip("/")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(doc, encoding="utf-8")
    return path


def placeholder(b, cls="card-img", extra=""):
    """Gold-framed walnut tile shown until a kit has a photo or video."""
    mono = e(b["model"] or b["brand"] or "GWVan60")
    return (f'<span class="{cls} ph"><span class="ph-frame"><span class="ph-star">&#10022;</span>'
            f'<span class="ph-name">{e(b["kit"])}</span><span class="ph-mono">{mono}</span></span>{extra}</span>')


def card(b):
    pic = cover(b)
    sub = " · ".join(x for x in (b["brand"], b["model"]) if x)
    vl = video_label(b)
    badge = f'<span class="badge">{e(vl)}</span>' if vl else ""
    rv = b.get("_review")
    if rv and rv["overall"] is not None:
        badge += f'<span class="score-badge" aria-label="Rated {num(rv["overall"])} out of 5">&#9733; {num(rv["overall"])}/5</span>'
    img = (f'<span class="card-img"><img src="{pic}" alt="" loading="lazy">{badge}</span>' if pic
           else placeholder(b, extra=badge))
    search = " ".join(x for x in (b["kit"], b["model"], b["brand"]) if x).lower()
    return (f'<a class="card" href="/builds/{b["slug"]}/" data-brand="{e(b["brand"] or "Other")}" data-search="{e(search)}">'
            f'{img}'
            f'<span class="card-body"><span class="card-title">{e(b["kit"])}</span>'
            f'<span class="card-sub">{e(sub)}</span></span></a>')


def title_block(kicker, title, sub=None):
    s = f'<p class="rule-sub">{e(sub)}</p>' if sub else ""
    return f'<header class="title-block"><p class="kicker">{e(kicker)}</p><h1>{e(title)}</h1>{s}</header>'


# ---------------------------------------------------------------- pages -----
def build_home(builds, community):
    latest = "".join(card(b) for b in [x for x in builds if x["short"] or x["full"]][:4])
    n_reviews = sum(1 for b in builds if b.get("_review"))
    ev = community[0]
    body = f"""
<section class="hero">
  <div class="wrap hero-row">
    <img class="hero-logo" src="/img/logo-512.webp" alt="GWVan60 logo: Gary and his boxer at the workbench with a wooden steam locomotive" width="320" height="320">
    <div class="hero-text">
      <p class="kicker">&#10022; Gary VanOpdorp &#10022;</p>
      <h1>GWVan60</h1>
      <p class="rule-sub">3D Puzzles &middot; Miniature Models</p>
      <p class="lede">I'm Gary, and I'm endlessly curious. That's how a wooden bulldozer, a miniature pub, and a tiny metal sea turtle all ended up on my workbench. I film my builds and write about what worked, what broke, and what needed wax.</p>
      <p class="ctas"><a class="btn" href="/reviews/">Browse kit reviews</a><a class="btn" href="/builds/">Watch build videos</a></p>
    </div>
  </div>
</section>

<section class="wrap section">
  <div class="section-head"><h2>Latest builds</h2><a href="/builds/">All {len(builds)} builds &rarr;</a></div>
  <div class="grid">{latest}</div>
</section>

<section class="band wood">
  <div class="wrap band-row">
    <div class="framed">
      <p class="kicker">White paper &middot; September 2026</p>
      <h2>Active Meditation Through Model Building</h2>
      <p>For some people, the route to a quieter mind is not stillness. It is focused making. I wrote this after 70+ builds: a framework linking precision craft with attention, flow, dexterity, completion, community and stress.</p>
      <p class="ctas"><a class="btn" href="/active-meditation/">Read the summary</a><a class="btn ghost" href="{WHITEPAPER}">Download the PDF</a></p>
    </div>
  </div>
</section>

<section class="wrap section two-col">
  <div>
    <h2>Reviews</h2>
    <p>{n_reviews} candid reviews from my workbench, scored out of 5 in eight categories: Challenge, Enjoyment, Engineering and Fit, Materials and Finish, Instructions, Display Appeal, Value, and Overall.</p>
    <p><a class="link" href="/reviews/">Read my reviews &rarr;</a></p>
  </div>
  <div>
    <h2>Community</h2>
    <p>I help moderate three model-building communities on Reddit, and I host build events at the Port Orange Elks Lodge. I'm also on the board of Florida Elks Children's Therapy Services, and I spoke at Rolife's 9th anniversary celebration. Most recently: the {e(ev["title"])}.</p>
    <p><a class="link" href="/community/">See what I'm up to &rarr;</a></p>
  </div>
</section>
"""
    page("/", None, "Gary VanOpdorp (GWVan60) builds wooden 3D puzzles and miniature models, films them, and writes honest reviews of what worked and what broke.", body)


def build_index(builds):
    brands = sorted({b["brand"] or "Other" for b in builds})
    chips = '<button class="chip" aria-pressed="true" data-filter="*">All</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-filter="{e(x)}">{e(x)}</button>' for x in brands)
    body = f"""
<div class="wrap section">
  {title_block("The workbench", "Builds", f"{len(builds)} kits and counting")}
  <div class="finder">
    <label class="search" for="build-search">
      <span class="vh">Search builds by kit name or model number</span>
      <input id="build-search" type="search" placeholder="Search by kit name or model number" autocomplete="off">
    </label>
    <div class="chips" role="group" aria-label="Filter by brand">{chips}</div>
    <p class="no-hits" hidden>No builds match that. Try another name or model number.</p>
  </div>
  <div class="grid" id="build-grid">{"".join(card(b) for b in builds)}</div>
</div>"""
    page("/builds/", "Builds", "Every GWVan60 build: ROKR, Rolife and other wooden kits, with short videos, full builds and reviews.", body, active="Builds")


def build_kit(b, builds):
    name = title_of(b)
    sub = " · ".join(x for x in (b["brand"], b["model"]) if x)
    full_label = b.get("full_title") or "Full build"
    full_vert = bool(b.get("full_vertical"))   # a full build filmed upright (phone portrait)
    full_fig = (f'<figure{"" if full_vert else " class=\"wide-fig\""}>'
                f'{player(b["full"], full_vert, f"{name}: {full_label}", poster=b.get("image") if full_vert else None)}'
                f'<figcaption>{e(full_label)}</figcaption></figure>') if b["full"] else ""
    full_section = ""
    if b["short"]:
        main_player = f'<figure>{player(b["short"], True, name)}<figcaption>The short</figcaption></figure>'
        full_section = (f'<section class="full-build"><h2>{e(full_label)}</h2>{full_fig}</section>' if full_fig else "")
        layout = ""
    elif b["full"]:
        main_player, layout = full_fig, ("" if full_vert else " wide-main")
    elif b.get("image"):
        main_player = f'<figure class="photo"><img src="{b["image"]}" alt="The finished {e(b["kit"])}"></figure>'
        layout = ""
    else:
        main_player, layout = placeholder(b, cls="photo"), ""
    rv = b.get("_review")
    facts = [("Brand", b["brand"]), ("Model", b["model"]), ("Posted", fmt_date(b["date"]) if b["date"] else None),
             ("Video", video_label(b)),
             ("Rating", f'{num(rv["overall"])}/5' if rv and rv["overall"] is not None else None), ("", builder_line(b))]
    facts_html = "".join(f"<div><dt>{k}</dt><dd>{e(v)}</dd></div>" if k else f'<div class="credit"><dd>{e(v)}</dd></div>'
                         for k, v in facts if v)
    links = []
    if b["short"]:
        links.append(("YouTube", f"https://www.youtube.com/shorts/{b['short']}"))
    if b["full"]:
        links.append(("YouTube (full build)" if b["short"] else "YouTube", f"https://www.youtube.com/watch?v={b['full']}"))
    if b["tiktok"]:
        links.append(("TikTok", f"https://www.tiktok.com/@gwvan60/video/{b['tiktok']}"))
    if b["instagram"]:
        links.append(("Instagram", f"https://www.instagram.com/reel/{b['instagram']}/"))
    links_html = "".join(f'<a class="pill" href="{u}" rel="noopener">{n}</a>' for n, u in links)
    watch = f'<h2 class="h3">Watch on</h2><p class="pills">{links_html}</p>' if links else ""
    # a plain link right under the player, for anyone whose browser blocks the embed
    yt_url = (f"https://www.youtube.com/watch?v={b['full']}" if b["full"]
              else f"https://www.youtube.com/shorts/{b['short']}" if b["short"] else None)
    yt_line = (f'<p class="watch-yt"><a class="link" href="{yt_url}" rel="noopener">Watch on YouTube &rarr;</a></p>'
               if yt_url else "")
    jump = '<p class="ctas"><a class="btn" href="#review">Read my review</a></p>' if rv else ""
    if not rv and b["reddit"]:
        jump = f'<p class="ctas"><a class="btn" href="{e(b["reddit"])}" rel="noopener">Read the review on Reddit</a></p>'
    review_html = render_review(b, rv) if rv else ""
    guides_html = "".join(
        f'<aside class="guide-link"><p class="kicker">Troubleshooting</p><h2>{e(g["title"])}</h2>'
        f'<p>{e(g["blurb"])}</p><p class="ctas"><a class="btn" href="/guides/{g["slug"]}/">Read the guide</a></p></aside>'
        for g in b.get("_guides", []))
    more = [x for x in builds if x is not b and x["brand"] == b["brand"]][:3] or [x for x in builds if x is not b][:3]
    body = f"""
<div class="wrap section">
  <p class="crumbs"><a href="/builds/">Builds</a> / {e(b["kit"])}</p>
  {title_block(b["brand"] or "Build", b["kit"], sub if b["model"] else None)}
  <div class="kit-row{layout}">
    <div class="players">{main_player}{yt_line}</div>
    <aside class="kit-info">
      <dl class="facts">{facts_html}</dl>
      {watch}
      {jump}
    </aside>
  </div>
  {review_html}
  {guides_html}
  {full_section}
  <section class="section"><div class="section-head"><h2>More builds</h2><a href="/builds/">All builds &rarr;</a></div>
  <div class="grid">{"".join(card(x) for x in more)}</div></section>
</div>"""
    if rv and rv["overall"] is not None:
        desc = f"{name}: my review, rated {num(rv['overall'])}/5, with notes on challenge, fit, materials, instructions and value. By GWVan60."
    elif rv:
        desc = f"{name}: my build story and review. By GWVan60."
    else:
        desc = f"{name}: build video{' and review' if b['reddit'] else ''} by GWVan60."
    page(f"/builds/{b['slug']}/", name, desc, body, og_image=cover(b), active="Builds")


CATEGORIES = ["Challenge", "Enjoyment", "Engineering and Fit", "Materials and Finish",
              "Instructions", "Display Appeal", "Value", "Overall Rating"]


def rev_row(b):
    rv = b["_review"]
    pic = cover(b)
    img = f'<img src="{pic}" alt="" loading="lazy">' if pic else placeholder(b, cls="rev-ph")
    meta = " · ".join(x for x in (b["brand"], b["model"]) if x)
    score = (f'<span class="rev-score">{pips(rv["overall"])}<b>{num(rv["overall"])}/5</b></span>'
             if rv["overall"] is not None else "")
    first = rv["intro"][0] if rv["intro"] else next((s["paras"][0] for s in rv["sections"] if s["paras"]), "")
    teaser = first if len(first) <= 150 else first[:first.rfind(" ", 0, 150)] + "..."
    search = " ".join(x for x in (b["kit"], b["model"], b["brand"]) if x).lower()
    return (f'<li data-brand="{e(b["brand"] or "Other")}" data-search="{e(search)}">'
            f'<a class="rev-row" href="/builds/{b["slug"]}/#review">{img}'
            f'<span class="rev-text"><strong>{e(b["kit"])}</strong><span class="card-sub">{e(meta)}</span>'
            f'{score}<span class="rev-teaser">{e(teaser)}</span></span></a></li>')


def build_reviews(builds):
    reviewed = [b for b in builds if b.get("_review")]
    rated = [b for b in reviewed if b.get("review_type") == "full" and b["_review"]["overall"] is not None]
    story = [b for b in reviewed if b.get("review_type") == "full" and b["_review"]["overall"] is None]
    archive = [b for b in reviewed if b.get("review_type") == "archive"]
    cats = "".join(f"<li>{c}</li>" for c in CATEGORIES)
    brands = sorted({b["brand"] or "Other" for b in reviewed})
    chips = '<button class="chip" aria-pressed="true" data-filter="*">All</button>' + "".join(
        f'<button class="chip" aria-pressed="false" data-filter="{e(x)}">{e(x)}</button>' for x in brands)
    body = f"""
<div class="wrap section narrow">
  {title_block("Honest takes", "Reviews", f"{len(reviewed)} kits reviewed")}
  <p class="lede">What worked, what broke, what needed wax, and whether the finished model earned its spot on the shelf.</p>

  <div class="finder" id="rev-filter">
    <label class="search" for="rev-search">
      <span class="vh">Search reviews by kit name or model number</span>
      <input id="rev-search" type="search" placeholder="Search by kit name or model number" autocomplete="off">
    </label>
    <div class="chips" role="group" aria-label="Filter by brand">{chips}</div>
    <p class="no-hits" hidden>No reviews match that. Try another name or model number.</p>
  </div>

  <h2>Rated reviews</h2>
  <ul class="rev-list">{"".join(rev_row(b) for b in rated)}</ul>
  <h2>Before the rating system</h2>
  <p>Earlier reviews, written as build stories.</p>
  <ul class="rev-list">{"".join(rev_row(b) for b in story)}</ul>
  <h2>From the archive</h2>
  <p>Summaries of my earliest reviews. The full original wording was not recovered.</p>
  <ul class="rev-list">{"".join(rev_row(b) for b in archive)}</ul>

  <details class="framed system">
    <summary><h2>How I rate kits</h2></summary>
    <p>I score each kit out of 5 in eight categories. I came up with the system while building a KPOP Demon Hunters 4D kit. Now and then a kit earns a 6. My rating system, my rules.</p>
    <ol class="cat-list">{cats}</ol>
  </details>
</div>"""
    page("/reviews/", "Reviews", "My written reviews of wooden model kits from ROKR, Rolife and more, scored with my eight-category rating system.", body, active="Reviews")


def build_meditation():
    active = [
        ("A", "Attention anchored", "A concrete present-moment target keeps pulling attention back: the next part, joint, alignment, color or fit."),
        ("C", "Challenge calibrated", "Difficulty sits near the builder's current skill, the zone associated with flow rather than boredom or overload."),
        ("T", "Tactile motor engagement", "Hands, eyes and planning work together through precise manipulation, sanding, painting, gluing and assembly."),
        ("I", "Immediate feedback", "A tab seats or it doesn't. A gear turns or it binds. The task answers right away."),
        ("V", "Visible progress", "Small completed steps add up to a real object, which draws you back to the bench."),
        ("E", "Enjoyment, completion & meaning", "Customizing, gifting, collecting, community and finishing the build add intrinsic reward."),
    ]
    rows = "".join(f'<li><span class="letter">{l}</span><div><h3>{e(t)}</h3><p>{e(d)}</p></div></li>' for l, t, d in active)
    body = f"""
<div class="wrap section narrow">
  {title_block("Conceptual white paper · v2.1 · September 2026", "Active Meditation Through Model Building", "By Gary VanOpdorp")}
  <blockquote class="pull">For some people, the route to a quieter mind is not stillness. It is focused making.</blockquote>
  <p class="lede">Builders of wooden and mechanical kits often describe a good session in words that sound close to meditation: attention narrows, time changes, mental noise recedes, and the session ends calmer than it began. This paper proposes a framework for why, drawing on 70+ personal builds and published research on mindfulness, flow, manual dexterity, creative activity, completion and community.</p>
  <p class="ctas"><a class="btn" href="{WHITEPAPER}">Download the full paper (PDF)</a></p>

  <h2>The working definition</h2>
  <p class="definition">Active meditation is a deliberately absorbing physical activity that anchors attention in the present through coordinated sensory, cognitive and motor demands, while providing enough challenge and feedback to support deep engagement without excessive pressure.</p>

  <h2>The ACTIVE framework</h2>
  <ul class="active-list">{rows}</ul>

  <h2>What the evidence says</h2>
  <ul class="evidence">
    <li><strong>Attention can live in ordinary manual tasks.</strong> In one study, simply attending mindfully while washing dishes raised state mindfulness and lowered nervousness.</li>
    <li><strong>Demanding tasks crowd out mind wandering,</strong> and minds that wander less tend to be happier in the moment.</li>
    <li><strong>Model kits fit flow almost perfectly:</strong> clear goals, immediate feedback and a challenge you can choose.</li>
    <li><strong>Hands-on making can lower short-term stress,</strong> including measurable cortisol drops after art making.</li>
    <li><strong>Dexterity practice is also cognitive work.</strong> Randomized trials in older adults found gains in trained dexterity and some executive-function measures.</li>
    <li><strong>Finishing matters.</strong> The "IKEA effect" shows we value what we build, but only when we complete it.</li>
    <li><strong>Community adds a second pathway,</strong> from subreddits to lodge build events.</li>
  </ul>

  <aside class="note"><strong>Scope note.</strong> "Active meditation" is a proposed descriptive framework, not an established clinical term. The paper does not claim that model kits treat any medical or psychological condition. No controlled trial of wooden model kits exists yet; the paper proposes a 12-week randomized study to test it directly.</aside>
</div>"""
    page("/active-meditation/", "Active Meditation Through Model Building",
         "A conceptual white paper by Gary VanOpdorp on precision model building as active meditation: attention, flow, dexterity, completion, community and stress.", body, active="Active Meditation")


def mmss(s):
    return f"{s // 60}:{s % 60:02d}"


def talk_block(t):
    return f"""
  <article class="talk">
    <h3>{e(t["title"])}</h3>
    <p class="card-sub">{e(t["role"])} &middot; {e(t["where"])} &middot; {e(t["when"])}</p>
    <p>{e(t["blurb"])}</p>
    {player(t["youtube"], False, f'{t["title"]}: Gary VanOpdorp', t.get("start"), t.get("end"))}
    <p class="credit-line">{e(t["credit"])} This player shows my talk only ({mmss(t["start"])}&ndash;{mmss(t["end"])}).
      <a class="link" href="https://www.youtube.com/watch?v={e(t["youtube"])}&amp;t={t["start"]}s" rel="noopener">Watch on YouTube</a></p>
  </article>"""


def build_community(community, talks):
    ev = community[0]
    talks_html = "".join(talk_block(t) for t in talks)
    signup = (f'<p class="ctas"><a class="btn" href="{e(ev["signup"])}" rel="noopener">Sign up for the next build event</a></p>'
              if ev.get("signup") else "")
    contact = "".join(f'<a class="pill" href="{u}" rel="noopener">{n}: {h}</a>' for n, u, h in CONTACT)
    body = f"""
<div class="wrap section narrow">
  {title_block("Around the workbench", "Community")}
  <p class="lede">I help moderate three model-building communities on Reddit, and I host build events at the Port Orange Elks Lodge.</p>
  <h2>Speaking</h2>{talks_html}
  <h2>Moderator</h2>
  <ul class="pills-list">
    <li><a class="pill" href="https://www.reddit.com/r/rokrpuzzles/" rel="noopener">r/ROKRPuzzles</a></li>
    <li><a class="pill" href="https://www.reddit.com/r/ugears/" rel="noopener">r/ugears</a></li>
    <li><a class="pill" href="https://www.reddit.com/r/DIYModelKits/" rel="noopener">r/DIYModelKits</a></li>
  </ul>
  <h2>Florida Elks Children's Therapy Services</h2>
  <p>I serve on the board of Florida Elks Children's Therapy Services.</p>
  <h2>{e(ev["title"])}</h2>
  <p class="card-sub">{e(ev["where"])} &middot; {fmt_date(ev["date"])}</p>
  <p>{e(ev["blurb"])}</p>
  {player(ev["youtube"], False, ev["title"])}
  {signup}
  <h2 id="contact">Contact me</h2>
  <p>If you run a club or make kits and want to talk about an event, a build or a review, message me. I read both.</p>
  <p class="pills">{contact}</p>
</div>"""
    page("/community/", "Community", "GWVan60 in the community: speaking at Rolife's 9th anniversary, Reddit moderation, Florida Elks Children's Therapy Services, and lodge build events.", body, active="Community")


def build_about(builds):
    body = f"""
<div class="wrap section narrow">
  {title_block("Hello", "About Gary")}
  <div class="about-row">
    <img src="/img/logo-256.webp" alt="" width="200" height="200">
    <div>
      <p class="lede">I'm Gary VanOpdorp, GWVan60 online. My first kit was a Rolife carousel. These days I'll try just about any kit once, especially if I find it secondhand for next to nothing.</p>
      <p>Once I get a kit on the bench, I start asking questions. Would those plywood edges look better in black? Why does Santa keep getting stuck in the cuckoo clock? And where am I going to put the dog? There's usually room for a dog.</p>
      <p>I've built more than 70 wooden and mechanical kits, and over the years the hobby has grown from plain assembly into sanding, edge coloring, painting, rigging, custom signs, electrical add-ons and repairs. I film my builds at the bench and write up what I find, so other builders know what they're getting into. The {len(builds)} builds on this site are the ones I've published so far.</p>
      <p>In September 2026 I was one of the speakers at Rolife's 9th anniversary celebration at American Dream Mall in New Jersey. <a class="link" href="/community/">Watch my talk</a>.</p>
      <p>Away from the bench, I work as a fractional and full-time consultant in data and business analytics.</p>
    </div>
  </div>
  <h2>Find me</h2>
  <p class="pills">{"".join(f'<a class="pill" href="{u}" rel="me noopener">{n}: {h}</a>' for n, u, h in SOCIAL)}<span class="pill static">Craftime: GWVan60</span></p>
  <p><a class="link" href="/community/#contact">Contact me &rarr;</a></p>
</div>"""
    page("/about/", "About", "About Gary VanOpdorp (GWVan60): model builder, reviewer, Reddit moderator and data consultant.", body, active="About")


def build_guide(g, builds):
    """A short troubleshooting write-up, linked from the kit it belongs to."""
    doc = parse_md(ROOT / "data" / "guides" / f"{g['slug']}.md")
    kit = next((b for b in builds if b["slug"] == g.get("kit")), None)
    parts = [f"<p>{md_inline(p)}</p>" for p in doc["intro"]]
    for s in doc["sections"]:
        parts.append(f'<h2>{e(s["name"])}</h2>' + "".join(f"<p>{md_inline(p)}</p>" for p in s["paras"]))
    back = (f'<p class="ctas"><a class="btn ghost" href="/builds/{kit["slug"]}/">Read my {e(kit["kit"])} review</a></p>'
            if kit else "")
    body = f"""
<div class="wrap section narrow">
  <p class="crumbs"><a href="/builds/">Builds</a>{f' / <a href="/builds/{kit["slug"]}/">{e(kit["kit"])}</a>' if kit else ""} / Troubleshooting</p>
  {title_block("Troubleshooting", g["title"], g.get("sub"))}
  {"".join(parts)}
  {back}
</div>"""
    page(f"/guides/{g['slug']}/", g["title"], g["blurb"], body, og_image=cover(kit) if kit else None, active="Builds")


def build_redirect(old_path, new_path):
    """Static forwarding page for a renamed address (GitHub Pages has no server-side redirects)."""
    out = DIST / old_path.strip("/") / "index.html"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>Moved | GWVan60</title><link rel="canonical" href="{SITE_URL}{new_path}">
<meta name="robots" content="noindex"><meta http-equiv="refresh" content="0; url={new_path}">
</head><body><p>This page moved to <a href="{new_path}">{SITE_URL}{new_path}</a>.</p></body></html>
""", encoding="utf-8")


def build_404():
    body = f"""<div class="wrap section narrow center">{title_block("404", "That part isn't in the box")}<p>The page you were looking for doesn't exist. Try the <a class="link" href="/builds/">builds</a> or head <a class="link" href="/">home</a>.</p></div>"""
    page("/404.html", "Not found", "Page not found.", body)


# ----------------------------------------------------------------- main -----
def main():
    data = json.loads((ROOT / "data" / "builds.json").read_text(encoding="utf-8"))
    # Held kits (data/held/held.json, never committed) join the site only on/after their publish_after date.
    held_file = HELD / "held.json"
    if held_file.exists():
        for b in json.loads(held_file.read_text(encoding="utf-8"))["builds"]:
            if date.today().isoformat() >= b["publish_after"]:
                data["builds"].append(b)
                print("  releasing held kit:", b["slug"])
            else:
                print(f"  holding {b['slug']} until {b['publish_after']}")
    # newest first; kits with no date (reviewed but not posted yet) go after, in file order
    builds = sorted(data["builds"], key=lambda b: b["date"] or "", reverse=True)
    for b in builds:
        b["_review"] = load_review(b["slug"])
    guides = data.get("guides", [])
    for b in builds:
        b["_guides"] = [g for g in guides if g.get("kit") == b["slug"]]
    community = data["community"]

    THUMBS.mkdir(parents=True, exist_ok=True)
    for b in builds:
        if b["short"]:
            fetch_thumb(b["short"], True)
        if b["full"]:
            fetch_thumb(b["full"], bool(b.get("full_vertical")))
    talks = data.get("talks", [])
    for c in community + talks:
        fetch_thumb(c["youtube"], False)

    # empty dist without removing the folder itself (a shell or the preview server may be using it)
    DIST.mkdir(exist_ok=True)
    for child in DIST.iterdir():
        shutil.rmtree(child) if child.is_dir() else child.unlink()
    shutil.copytree(STATIC, DIST, dirs_exist_ok=True)

    paths = []
    build_home(builds, community); paths.append("/")
    build_index(builds); paths.append("/builds/")
    for b in builds:
        build_kit(b, builds); paths.append(f"/builds/{b['slug']}/")
        for old in b.get("aliases", []):      # old addresses forward to the current page
            build_redirect(f"/builds/{old}/", f"/builds/{b['slug']}/")
    for g in guides:
        build_guide(g, builds); paths.append(f"/guides/{g['slug']}/")
    build_reviews(builds); paths.append("/reviews/")
    build_meditation(); paths.append("/active-meditation/")
    build_community(community, talks); paths.append("/community/")
    build_about(builds); paths.append("/about/")
    build_404()

    (DIST / "CNAME").write_text(SITE_DOMAIN + "\n")
    (DIST / ".nojekyll").write_text("")
    (DIST / "robots.txt").write_text(f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n")
    (DIST / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE_URL}{p}</loc></url>\n" for p in paths) + "</urlset>\n")
    print(f"Built {len(paths)} pages into {DIST}")

    if "--serve" in sys.argv:
        import functools, http.server
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(DIST))
        print("Preview at http://localhost:8060")
        http.server.ThreadingHTTPServer(("127.0.0.1", 8060), handler).serve_forever()


if __name__ == "__main__":
    main()
