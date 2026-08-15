#!/usr/bin/env python3
"""Build the static site from the portable content layer.

    python3 build.py            # -> repo root (what GitHub Pages serves)
    python3 build.py preview/   # -> preview/ (throwaway copy, assets included)

This repo is a GitHub Pages *user site* (jannasaf.github.io), so Pages serves the
root of `main`. The generated pages therefore live at the root next to the sources,
and reference `assets/img/` in place rather than copying it.

Reads  content/site.json      site-level model (hand-authored, verified)
       content/<slug>.json    machine-extracted case-study blocks
       assets/img/*           harvested imagery
Writes index.html, about.html, work/*.html, assets/css/site.css
"""
import html
import json
import os
import re
import shutil
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
IN_PLACE = len(sys.argv) < 2
OUT = ROOT if IN_PLACE else os.path.join(ROOT, sys.argv[1])
SITE = json.load(open(f"{ROOT}/content/site.json"))
T = SITE["tokens"]

CASES = [p["slug"] for p in SITE["projects"]]


def e(s):
    return html.escape(s or "", quote=True)


def up(path, depth):
    """Rewrite a root-relative asset path for a page nested `depth` levels down."""
    return ("../" * depth) + path


# ---------------------------------------------------------------- chrome


def head(title, desc, depth, extra_class=""):
    css = up("assets/css/site.css", depth)
    return f"""<!doctype html>
<html lang="en" class="{extra_class}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Instrument+Serif:ital@0;1&family=Inter+Tight:wght@300;400;500;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{css}">
</head>
<body>
<a class="skip" href="#main">Skip to content</a>
"""


def nav(depth, active):
    items = []
    for n in SITE["nav"]:
        href = n["href"] if n["href"].startswith("#") else up(n["href"], depth)
        cur = ' aria-current="page"' if n["label"] == active else ""
        items.append(f'<a href="{e(href)}"{cur}>{e(n["label"])}</a>')
    return f"""<header class="topbar">
  <div class="shell topbar__inner">
    <a class="brand" href="{up('index.html', depth)}">{e(SITE['profile']['name'])}</a>
    <nav class="nav" aria-label="Main">{''.join(items)}</nav>
  </div>
</header>
<main id="main">
"""


def footer(depth, script=""):
    f, p = SITE["footer"], SITE["profile"]
    return f"""</main>
<footer class="connect" id="connect">
  <div class="shell connect__inner">
    <h2 class="d-section">{e(f['heading'])}</h2>
    <p class="lede">{e(f['body'])}</p>
    <div class="connect__links">
      <a class="mailto" href="mailto:{e(p['email'])}">{e(p['email'])}</a>
      <a class="mailto" href="{e(p['linkedin'])}" target="_blank" rel="noopener">LinkedIn</a>
    </div>
  </div>
</footer>
{script}</body>
</html>
"""


PROCNAV_SCRIPT = """<script>
(function(){
  var steps = Array.prototype.slice.call(document.querySelectorAll(".step"));
  var fill = document.querySelector("[data-progress-fill]");
  var sections = steps.map(function(s){
    var href = s.querySelector(".step__link").getAttribute("href");
    return document.getElementById(href.slice(1));
  }).filter(Boolean);

  function setActive(id){
    steps.forEach(function(s){
      var href = s.querySelector(".step__link").getAttribute("href");
      s.classList.toggle("is-active", href === "#" + id);
    });
  }

  if ("IntersectionObserver" in window && sections.length){
    var observer = new IntersectionObserver(function(entries){
      entries.forEach(function(entry){
        if (entry.isIntersecting) setActive(entry.target.id);
      });
    }, { rootMargin: "-40% 0px -55% 0px", threshold: 0 });
    sections.forEach(function(s){ observer.observe(s); });
  }

  function updateProgress(){
    if (!fill) return;
    var doc = document.documentElement;
    var scrollTop = doc.scrollTop || document.body.scrollTop;
    var scrollHeight = (doc.scrollHeight || document.body.scrollHeight) - doc.clientHeight;
    var pct = scrollHeight > 0 ? (scrollTop / scrollHeight) * 100 : 0;
    fill.style.width = pct + "%";
  }
  document.addEventListener("scroll", updateProgress, { passive: true });
  updateProgress();
})();
</script>
"""


# ---------------------------------------------------------------- pieces


def rich(text):
    """Render {{...}} emphasis spans from the content model."""
    parts = re.split(r"\{\{(.+?)\}\}", text)
    out = []
    for i, part in enumerate(parts):
        out.append(f'<span class="muted">{e(part)}</span>' if i % 2 else e(part))
    return "".join(out)


def img(src, alt, depth, cls=""):
    return (f'<img class="{cls}" src="{e(up(src, depth))}" alt="{e(alt or "")}"'
            f' loading="lazy" decoding="async">')


def project_card(p, depth):
    labels = "".join(f'<span class="pill">{e(l)}</span>' for l in p["labels"])
    thumbs = "".join(img(t, f'{p["name"]} — interface detail {i + 1}', depth, "collage__item")
                     for i, t in enumerate(p["thumbs"]))
    return f"""<a class="card" href="{e(up(p['href'], depth))}">
  <div class="card__media"><div class="collage collage--{len(p['thumbs'])}">{thumbs}</div></div>
  <div class="card__body">
    <div class="pills">{labels}</div>
    <h3 class="d-card">{e(p['title'])}</h3>
    <p class="card__meta">{e(p['subtitle'])}</p>
  </div>
</a>"""


# ---------------------------------------------------------------- blocks


def render_text(runs, depth, lead_class="d-section", min_level=2):
    """min_level=1 lets a block own the page's <h1>; sections default to <h2>.

    The source levels come from uxfolio and skip around (h1 then h3, h2 after h3),
    which leaves a broken outline for screen readers. Derive the *semantic* level
    from position instead — first heading in a section, then subordinates — and keep
    the *visual* size from the original level, so appearance is unchanged.
    """
    out = []
    seen_heading = False
    for r in runs:
        if r["kind"] == "heading":
            orig = r["level"] or min_level
            cls = lead_class if orig <= 3 else "d-sub"
            lvl = min_level if not seen_heading else min(min_level + 1, 6)
            seen_heading = True
            out.append(f'<h{lvl} class="{cls}">{e(r["text"])}</h{lvl}>')
        elif r["kind"] == "li":
            out.append(f'<li>{e(r["text"])}</li>')
        elif r["kind"] == "link":
            out.append(f'<a class="btn" href="{e(r["href"])}" target="_blank" rel="noopener">{e(r["text"])}</a>')
        else:
            out.append(f'<p>{e(r["text"])}</p>')
    # wrap consecutive <li> in a <ul>
    joined, buf, res = "", [], []
    for frag in out:
        if frag.startswith("<li>"):
            buf.append(frag)
        else:
            if buf:
                res.append('<ul class="ticks">' + "".join(buf) + "</ul>")
                buf = []
            res.append(frag)
    if buf:
        res.append('<ul class="ticks">' + "".join(buf) + "</ul>")
    return "".join(res)


def render_block(b, depth):
    t, runs, images = b["type"], b.get("text", []), b.get("images", [])
    anchor = b.get("anchor")
    id_attr = f' id="{e(anchor)}"' if anchor else ""

    if t == "process":
        steps = "".join(
            f'<li class="step" data-step="{s["n"]}">'
            f'<a class="step__link" href="#{e(s["anchor"])}">'
            f'<span class="step__n">{s["n"]}</span>'
            f'<span class="step__label">{e(s["label"])}</span></a></li>'
            for s in b.get("steps", []))
        return f"""<nav class="procnav" aria-label="Case study sections">
  <div class="procnav__bar"><div class="procnav__fill" data-progress-fill></div></div>
  <ol class="steps">{steps}</ol>
</nav>"""

    if t in ("mainheader", "header"):
        head_runs = [r for r in runs if r["kind"] == "heading"]
        rest = [r for r in runs if r["kind"] != "heading"]
        title = e(head_runs[0]["text"]) if head_runs else ""
        sub = "".join(f"<p>{e(r['text'])}</p>" for r in rest)
        media = "".join(img(i["src"], i["alt"], depth, "casehero__img") for i in images)
        return f"""<section class="sec casehero"{id_attr}>
  <div class="casehero__text"><h1 class="d-hero">{title}</h1><div class="lede">{sub}</div></div>
  <div class="casehero__media">{media}</div>
</section>"""

    if t == "cards":
        items = b.get("items")
        if items:
            italic_lead = b.get("italic_label")
            def render_tile(it):
                out, li_buf = [], []
                def flush():
                    if li_buf:
                        out.append('<ul class="ticks">' + "".join(li_buf) + "</ul>")
                        li_buf.clear()
                for r in it["text"]:
                    if r["kind"] == "li":
                        li_buf.append(f'<li>{e(r["text"])}</li>')
                        continue
                    flush()
                    if r["kind"] == "heading":
                        out.append(f'<p class="tile__body">{e(r["text"])}</p>')
                    elif italic_lead and ":" in r["text"]:
                        lead, rest = r["text"].split(":", 1)
                        out.append(f'<p class="tile__label"><em>{e(lead)}:</em>{e(rest)}</p>')
                    else:
                        out.append(f'<p class="tile__label">{e(r["text"])}</p>')
                flush()
                return '<div class="tile">' + "".join(out) + "</div>"
            cards = "".join(render_tile(it) for it in items)
        else:
            cards = "".join(f'<div class="tile">{e(r["text"])}</div>' for r in runs if r["text"])
        tiles_cls = "tiles"
        if b.get("cols"):
            tiles_cls += f' tiles--{b["cols"]}'
        if b.get("bold_heading"):
            tiles_cls += " tiles--bold-heading"
        return f'<section class="sec"{id_attr}><div class="{tiles_cls}">{cards}</div></section>'

    if t == "gallery":
        media = "".join(img(i["src"], i["alt"], depth, "gallery__img") for i in images)
        return f'<section class="sec"{id_attr}><div class="gallery">{media}</div></section>'

    if t == "columns":
        cols = b.get("columns")
        if cols:
            is_stat = b.get("stat")
            cells = []
            for c in cols:
                inner = render_text(c["text"], depth, "stat__value" if is_stat else "d-section")
                inner += "".join(img(i["src"], i["alt"], depth, "figure__img") for i in c["images"])
                if is_stat:
                    cls = "stat"
                else:
                    # A column of short label/value pairs is meta, not prose.
                    is_meta = (c["text"] and not c["images"]
                               and all(len(r["text"]) < 60 for r in c["text"]))
                    cls = "meta" if is_meta else "prose"
                cells.append(f'<div class="{cls}">{inner}</div>')
            extra = " cols--stat" if is_stat else ""
            return (f'<section class="sec cols cols--{len(cells)}{extra}"{id_attr}>'
                    + "".join(cells) + "</section>")
        body = render_text(runs, depth)
        media = "".join(img(i["src"], i["alt"], depth, "figure__img") for i in images)
        if body and media:
            return (f'<section class="sec sec--split"{id_attr}><div class="prose">{body}</div>'
                    f'<div class="figure">{media}</div></section>')
        if media:
            return f'<section class="sec"{id_attr}><div class="figure figure--wide">{media}</div></section>'
        return f'<section class="sec"{id_attr}><div class="prose">{body}</div></section>'

    if t == "textandmedia":
        body = render_text(runs, depth)
        media = "".join(img(i["src"], i["alt"], depth, "figure__img") for i in images)
        if media:
            figure_cls = "figure figure--compact" if b.get("compact_media") else "figure"
            return (f'<section class="sec sec--split"{id_attr}><div class="prose">{body}</div>'
                    f'<div class="{figure_cls}">{media}</div></section>')
        return f'<section class="sec"{id_attr}><div class="prose">{body}</div></section>'

    body = render_text(runs, depth)
    media = "".join(img(i["src"], i["alt"], depth, "figure__img") for i in images)
    prose_cls = "prose prose--wide" if b.get("wide") else "prose"
    inner = f'<div class="{prose_cls}">{body}</div>' + (f'<div class="figure figure--wide">{media}</div>' if media else "")
    return f'<section class="sec"{id_attr}>{inner}</section>'


# ---------------------------------------------------------------- pages


def build_home():
    h = SITE["hero"]
    pi = SITE["projects_intro"]
    cards = "".join(project_card(p, 0) for p in SITE["projects"])
    body = f"""<section class="sec hero">
  <p class="eyebrow">{e(h['eyebrow'])}</p>
  <h1 class="d-hero">{rich(h['headline'])}</h1>
  <p class="lede hero__lede">{e(h['subhead'])}</p>
</section>
<section class="sec">
  <h2 class="d-section">{e(pi['heading'])}</h2>
  <p class="lede">{e(pi['body'])}</p>
  <div class="grid">{cards}</div>
</section>"""
    return (head(f"{SITE['profile']['name']} — {SITE['profile']['role']}",
                 SITE["profile"]["meta_description"], 0)
            + nav(0, "Home") + f'<div class="shell">{body}</div>' + footer(0))


def build_about():
    a = SITE["about"]
    doc = json.load(open(f"{ROOT}/content/about.json"))
    prose_runs, edu_runs, tags, methods_runs = [], [], None, None
    for b in doc["blocks"]:
        heads = [r["text"] for r in b["text"] if r["kind"] == "heading"]
        if "Education" in heads:
            edu_runs = [r for r in b["text"] if r["kind"] != "heading"]
        elif "What I do" in heads:
            tags = b.get("tags", [])
        elif "Methods & tools" in heads:
            methods_runs = b["text"]
        elif SITE["footer"]["heading"].replace("'", "’") in " ".join(heads) or "connect" in " ".join(heads).lower():
            continue
        else:
            prose_runs += b["text"]
    # "Hello!" is this page's title, so it owns the <h1>.
    prose = render_text(prose_runs, 0, "d-hero", min_level=1)
    edu = "".join(f'<li>{e(r["text"])}</li>' for r in edu_runs) or \
          "".join(f"<li>{e(x)}</li>" for x in a["education"])
    tags_section = ""
    if tags:
        pills = "".join(f'<span class="pill">{e(t)}</span>' for t in tags)
        tags_section = f"""<section class="sec">
  <h2 class="d-section">What I do</h2>
  <div class="pills pills--lg">{pills}</div>
</section>
"""
    methods_section = ""
    if methods_runs:
        methods_section = f"""<section class="sec">
  <div class="prose">{render_text(methods_runs, 0, "d-section")}</div>
</section>
"""
    body = f"""<section class="sec sec--split">
  <div class="prose">{prose}</div>
  <div class="figure"><img class="portrait" src="{e(a['portrait'])}" alt="Portrait of {e(SITE['profile']['name'])}" loading="lazy" decoding="async"></div>
</section>
{tags_section}{methods_section}<section class="sec">
  <h2 class="d-section">Education</h2>
  <ul class="rows">{edu}</ul>
</section>"""
    return (head(f"About — {SITE['profile']['name']}", SITE["profile"]["meta_description"], 0)
            + nav(0, "About") + f'<div class="shell">{body}</div>' + footer(0))


def build_case(slug):
    doc = json.load(open(f"{ROOT}/content/{slug}.json"))
    meta = next(p for p in SITE["projects"] if p["slug"] == slug)
    others = [p for p in SITE["projects"] if p["slug"] != slug]
    blocks = doc["blocks"]

    # Drop the trailing "read more" + footer blocks; we regenerate those from site.json
    drop = ("read more of my case studies", "let’s connect!", "let's connect!")
    keep = []
    for b in blocks:
        heads = " ".join(r["text"].lower() for r in b.get("text", []) if r["kind"] == "heading")
        if any(d in heads for d in drop):
            continue
        keep.append(b)

    has_procnav = any(b["type"] == "process" for b in keep)
    body = "".join(render_block(b, 1) for b in keep)
    more = "".join(project_card(p, 1) for p in others)
    nxt = f"""<section class="sec sec--more">
  <h2 class="d-section">More case studies</h2>
  <div class="grid">{more}</div>
</section>"""
    return (head(f"{meta['name']} — {SITE['profile']['name']}", meta["title"], 1)
            + nav(1, "Home") + f'<div class="shell">{body}{nxt}</div>'
            + footer(1, PROCNAV_SCRIPT if has_procnav else ""))


# ---------------------------------------------------------------- css

CSS = f""":root {{
  --page:{T['color']['page']};
  --panel:{T['color']['panel']};
  --surface:{T['color']['surface']};
  --ink:{T['color']['ink']};
  --muted:{T['color']['muted']};
  --shell:{T['layout']['max_width']};
  --display:{T['type']['display']};
  --body:{T['type']['body']};
  --gap:clamp(1.25rem,3vw,2.5rem);
  --topbar-h:4rem;
  --procnav-h:5rem;
}}
*,*::before,*::after{{box-sizing:border-box}}
html{{-webkit-text-size-adjust:100%;scroll-behavior:smooth}}
body{{margin:0;background:var(--page);color:var(--ink);
  font-family:var(--body);font-weight:{T['type']['body_weight']};font-size:1.125rem;line-height:1.45}}
img{{max-width:100%;height:auto;display:block}}
a{{color:inherit}}
.skip{{position:absolute;left:-9999px}}
.skip:focus{{left:1rem;top:1rem;background:var(--ink);color:var(--page);padding:.6rem 1rem;z-index:99}}
:focus-visible{{outline:2px solid var(--ink);outline-offset:3px}}

.shell{{max-width:var(--shell);margin-inline:auto;padding-inline:clamp(1.25rem,5vw,5rem)}}

/* type */
.d-hero{{font-family:var(--display);font-weight:400;font-size:clamp(2rem,4.6vw,3.5rem);
  line-height:1.07;margin:0 0 1rem;letter-spacing:-.005em}}
.d-section{{font-family:var(--display);font-weight:400;font-size:clamp(1.5rem,2.6vw,2rem);
  line-height:1.25;margin:0 0 .5rem}}
.d-sub{{font-family:var(--display);font-weight:400;font-size:1.3rem;line-height:1.3;margin:0 0 .4rem}}
.d-card{{font-family:var(--display);font-weight:400;font-size:clamp(1.25rem,1.9vw,1.75rem);
  line-height:1.22;margin:0 0 .4rem}}
.eyebrow{{font-size:1.125rem;font-weight:700;margin:0 0 1.25rem}}
.lede{{color:var(--muted);max-width:62ch;margin:0 0 1rem}}
.hero__lede{{max-width:none}}
.muted{{color:var(--muted)}}
p{{margin:0 0 1rem;max-width:74ch}}

/* chrome */
.topbar{{position:sticky;top:0;z-index:10;background:var(--page);
  border-bottom:1px solid color-mix(in srgb,var(--ink) 12%,transparent)}}
.topbar__inner{{display:flex;align-items:center;justify-content:space-between;
  gap:1rem;padding-block:1rem}}
.brand{{text-decoration:none;font-size:1.125rem}}
.nav{{display:flex;gap:clamp(.9rem,2vw,1.6rem);font-size:1rem}}
.nav a{{text-decoration:none;color:var(--muted);padding-block:.2rem}}
.nav a:hover,.nav a[aria-current]{{color:var(--ink)}}

/* sections */
.sec{{padding-block:clamp(1.75rem,4vw,3.5rem)}}
.sec--split{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);
  gap:var(--gap);align-items:start}}
.prose>:last-child,.lede:last-child{{margin-bottom:0}}
.cols{{display:grid;gap:var(--gap);align-items:start}}
.cols--2{{grid-template-columns:minmax(0,1.35fr) minmax(0,1fr)}}
.cols--3{{grid-template-columns:repeat(3,minmax(0,1fr))}}
.cols--4{{grid-template-columns:repeat(auto-fit,minmax(min(220px,100%),1fr))}}
.cols--stat{{grid-template-columns:repeat(4,minmax(0,1fr))}}
.stat__value{{font-family:var(--body);font-weight:700;font-size:clamp(2.25rem,5vw,3.25rem);
  line-height:1.05;margin:0 0 .35rem}}
.stat p{{color:var(--muted);margin:0;font-size:.95rem}}
.stat>:last-child{{margin-bottom:0}}
.meta .d-section{{font-size:1.05rem;font-family:var(--body);font-weight:500;margin:0}}
.meta p{{color:var(--muted);margin:0 0 1.25rem}}
.meta>:last-child{{margin-bottom:0}}
.prose--wide p{{max-width:none}}
.figure--wide{{grid-column:1/-1}}
.figure--compact{{max-width:320px;margin-inline:auto}}
.figure__img,.gallery__img,.casehero__img{{border-radius:2px;background:var(--surface)}}
.figure__img+.figure__img{{margin-top:1rem}}
.btn{{display:inline-block;background:var(--ink);color:var(--page);text-decoration:none;
  padding:.75rem 1.5rem;border-radius:2px;font-size:1rem;margin-top:.5rem}}
.btn:hover{{opacity:.85}}
.gallery{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(320px,100%),1fr));gap:var(--gap)}}
.ticks{{margin:0 0 1rem;padding-left:1.1rem}}
.ticks li{{margin-bottom:.4rem;max-width:70ch}}
.rows{{list-style:none;margin:0;padding:0}}
.rows li{{padding-block:.85rem;border-top:1px solid color-mix(in srgb,var(--ink) 14%,transparent)}}
.rows li:last-child{{border-bottom:1px solid color-mix(in srgb,var(--ink) 14%,transparent)}}

/* case hero */
.casehero{{display:grid;grid-template-columns:minmax(0,.85fr) minmax(0,1.15fr);
  gap:var(--gap);align-items:center}}

/* process */
section[id]{{scroll-margin-top:calc(var(--topbar-h) + var(--procnav-h))}}
.procnav{{position:sticky;top:var(--topbar-h);z-index:9;background:var(--page);
  padding-block:.85rem;border-bottom:1px solid color-mix(in srgb,var(--ink) 12%,transparent)}}
.procnav__bar{{height:3px;background:color-mix(in srgb,var(--ink) 12%,transparent);
  border-radius:2px;margin-bottom:.85rem;overflow:hidden}}
.procnav__fill{{height:100%;width:0%;background:var(--ink);transition:width .1s linear}}
.steps{{list-style:none;display:flex;flex-wrap:wrap;gap:clamp(1rem,3vw,2.5rem);
  margin:0;padding:0;counter-reset:none}}
.step__link{{display:flex;align-items:center;gap:.6rem;font-size:1rem;
  color:var(--muted);text-decoration:none}}
.step__label{{font-weight:700}}
.step__n{{display:grid;place-items:center;width:2rem;height:2rem;flex:0 0 auto;
  border-radius:50%;border:1px solid color-mix(in srgb,var(--ink) 30%,transparent);
  font-family:var(--display);font-size:1rem;color:var(--ink);transition:background-color .15s,color .15s}}
.step__link:hover{{color:var(--ink)}}
.step.is-active .step__link{{color:var(--ink)}}
.step.is-active .step__n,.step__link:hover .step__n{{background:var(--ink);color:var(--page)}}

/* tiles / insight cards */
.tiles{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(300px,100%),1fr));gap:var(--gap)}}
.tiles--2{{grid-template-columns:repeat(2,minmax(0,1fr))}}
.tile{{background:var(--surface);padding:clamp(1.1rem,2.2vw,1.75rem);border-radius:2px}}
.tile__label{{font-size:.95rem;font-weight:500;color:var(--muted);margin:0 0 .4rem}}
.tile__body{{margin:0;font-family:var(--display);font-size:1.15rem;line-height:1.35}}
.tiles--bold-heading .tile__body{{font-family:var(--body);font-weight:700;font-size:1.05rem;margin:0 0 .4rem}}
.tile>:last-child{{margin-bottom:0}}

/* project cards */
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(340px,100%),1fr));
  gap:var(--gap);margin-top:2rem}}
.card{{text-decoration:none;display:flex;flex-direction:column;background:var(--panel);
  border-radius:2px;overflow:hidden;transition:transform .2s ease,box-shadow .2s ease}}
.card:hover{{transform:translateY(-3px);box-shadow:0 12px 32px rgba(0,0,0,.14)}}
.card__media{{padding:clamp(1rem,2vw,1.75rem)}}
.collage{{display:grid;gap:.5rem;align-items:center}}
.collage--1{{grid-template-columns:1fr}}
.collage--2{{grid-template-columns:repeat(2,1fr)}}
.collage--4{{grid-template-columns:repeat(2,1fr)}}
.collage__item{{border-radius:2px;background:var(--surface);
  box-shadow:0 2px 10px rgba(0,0,0,.10);width:100%;object-fit:cover;aspect-ratio:3/4}}
.collage--1 .collage__item,.collage--2 .collage__item{{aspect-ratio:auto}}
.card__body{{padding:0 clamp(1rem,2vw,1.75rem) clamp(1.25rem,2.4vw,1.75rem)}}
.pills{{display:flex;flex-wrap:wrap;gap:.4rem;margin-bottom:.85rem}}
.pill{{background:var(--ink);color:var(--page);border-radius:999px;
  padding:.28rem .7rem;font-size:.75rem;line-height:1.4}}
.pills--lg{{gap:.6rem;margin-bottom:0}}
.pills--lg .pill{{font-size:.9rem;padding:.45rem .95rem}}
.card__meta{{color:var(--muted);font-size:1rem;margin:0}}
.sec--more{{border-top:1px solid color-mix(in srgb,var(--ink) 14%,transparent)}}

/* about */
.portrait{{border-radius:2px;width:100%;object-fit:cover;aspect-ratio:1}}

/* footer */
.connect{{background:var(--panel);margin-top:clamp(2rem,5vw,4rem)}}
.connect__inner{{padding-block:clamp(2.5rem,6vw,4rem)}}
.connect__links{{display:flex;gap:1.5rem;margin-top:.25rem;flex-wrap:wrap}}
.mailto{{display:inline-block}}

@media (max-width:820px){{
  .sec--split,.casehero,.cols--2,.cols--3,.tiles--2{{grid-template-columns:1fr}}
  .cols--stat{{grid-template-columns:repeat(2,minmax(0,1fr))}}
  .steps{{flex-wrap:nowrap;overflow-x:auto;gap:1.5rem}}
  .step__link{{white-space:nowrap}}
}}
@media (prefers-reduced-motion:reduce){{
  html{{scroll-behavior:auto}}
  *{{transition:none!important;animation:none!important}}
  .card:hover{{transform:none}}
}}
"""


# ---------------------------------------------------------------- main

def main():
    generated = ["index.html", "about.html", "assets/css/site.css"] + \
                [f"work/{s}.html" for s in CASES]

    if IN_PLACE:
        # Never rmtree the repo root — remove only what a previous run wrote.
        for rel in generated:
            p = f"{OUT}/{rel}"
            if os.path.exists(p):
                os.remove(p)
    else:
        if os.path.isdir(OUT):
            shutil.rmtree(OUT)
        os.makedirs(f"{OUT}/assets", exist_ok=True)
        shutil.copytree(f"{ROOT}/assets/img", f"{OUT}/assets/img")

    os.makedirs(f"{OUT}/assets/css", exist_ok=True)
    os.makedirs(f"{OUT}/work", exist_ok=True)

    open(f"{OUT}/assets/css/site.css", "w").write(CSS)
    open(f"{OUT}/index.html", "w").write(build_home())
    open(f"{OUT}/about.html", "w").write(build_about())
    for slug in CASES:
        open(f"{OUT}/work/{slug}.html", "w").write(build_case(slug))

    # Pages runs Jekyll unless told not to; that would skip files it does not expect.
    open(f"{OUT}/.nojekyll", "w").write("")

    for rel in generated:
        print(f"  {os.path.getsize(f'{OUT}/{rel}'):>7,} B  {rel}")
    n = len(os.listdir(f"{OUT}/assets/img"))
    print(f"\n  {len(generated) - 1} pages + {n} images -> "
          f"{'repo root' if IN_PLACE else OUT}")


if __name__ == "__main__":
    main()
