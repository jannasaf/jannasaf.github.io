"""Convert harvested uxfol.io DOM into a portable, framework-agnostic content layer.

Emits content/*.json  — ordered blocks per page (type, heading, body, images, items)
       assets/        — deduped, human-named image files
"""
import hashlib, json, os, re, shutil, sys
from bs4 import BeautifulSoup

HARVEST, DEST = sys.argv[1], sys.argv[2]
DOM = f"{HARVEST}/dom"
man = json.load(open(f"{HARVEST}/manifest.json"))
URL2FILE = {a["url"]: a["file"] for a in man["assets"]}

os.makedirs(f"{DEST}/content", exist_ok=True)
os.makedirs(f"{DEST}/assets/img", exist_ok=True)

PAGES = [
    ("00_home", "home", "/"),
    ("90_about", "about", "/about"),
    ("01_case_AI-0-1-Entrepreneurship-Building-an-AI-Powere", "concierj", "/work/concierj"),
    ("02_case_UX-Research-UX-UI-Design-B2C-Redesigning-the", "safe-water-network", "/work/safe-water-network"),
    ("03_case_Operational-UX-Systems-Design-Internal-Tools", "workflow-automation", "/work/workflow-automation"),
]

used_names = {}


def norm(t):
    return re.sub(r"[ \t]+", " ", (t or "").replace("\xa0", " ")).strip()


def asset(url, page, idx):
    """Copy a harvested asset to a stable, readable filename; return relative path."""
    if not url or url.startswith("data:"):
        return None
    f = URL2FILE.get(url)
    if not f or not os.path.exists(f"{HARVEST}/assets/{f}"):
        return None
    ext = os.path.splitext(f)[1] or ".png"
    base = f"{page}-{idx:02d}{ext}"
    if url in used_names:
        return used_names[url]
    shutil.copy2(f"{HARVEST}/assets/{f}", f"{DEST}/assets/img/{base}")
    used_names[url] = f"assets/img/{base}"
    return used_names[url]


def imgs_in(node, page, counter):
    out = []
    for im in node.select("img"):
        src = im.get("src") or im.get("data-src")
        if not src:
            continue
        counter[0] += 1
        p = asset(src, page, counter[0])
        if p:
            out.append({"src": p, "alt": norm(im.get("alt")) or None})
    return out


def texts_in(node):
    """Ordered visible text runs, preserving heading vs paragraph distinction."""
    blocks = []
    for el in node.find_all(["h1", "h2", "h3", "h4", "h5", "h6", "p", "li"]):
        if el.find_parent(["nav"]):
            continue
        t = norm(el.get_text(" ", strip=True))
        if not t:
            continue
        kind = "heading" if el.name.startswith("h") else ("li" if el.name == "li" else "p")
        if blocks and blocks[-1]["text"] == t:
            continue
        blocks.append({"kind": kind, "level": int(el.name[1]) if el.name.startswith("h") else None, "text": t})
    if blocks:
        return blocks
    # Fallback: this section styles its copy with bare <div>/<span> (process strips,
    # stat tiles, label pills). Take leaf-node text in document order.
    seen = set()
    for el in node.find_all(["div", "span"]):
        if el.find(["div", "span"]):
            continue
        t = norm(el.get_text(" ", strip=True))
        if not t or t in seen:
            continue
        seen.add(t)
        blocks.append({"kind": "p", "level": None, "text": t})
    return blocks


def steps_in(node):
    """Numbered process strip.

    The DOM emits a leading duplicate of the active step, so tokens arrive as
    e.g. [5, Prototype, 1, Research, 2, ...]. Pair each number token with the
    label that follows it, then key by number to collapse the duplicate.
    """
    tokens = []
    for el in node.find_all(["a", "div", "span"]):
        if el.find(["a", "div", "span"]):
            continue
        t = norm(el.get_text(" ", strip=True))
        if t:
            tokens.append(t)
    steps = {}
    for i, t in enumerate(tokens):
        if re.fullmatch(r"\d+", t) and i + 1 < len(tokens) and not re.fullmatch(r"\d+", tokens[i + 1]):
            steps[int(t)] = tokens[i + 1]
    return [{"n": n, "label": steps[n]} for n in sorted(steps)]


for tag, slug, route in PAGES:
    path = f"{DOM}/{tag}.html"
    if not os.path.exists(path):
        print(f"  skip missing {tag}")
        continue
    soup = BeautifulSoup(open(path).read(), "html.parser")

    # strip platform chrome we do not want to carry over
    for sel in ("nav", ".ufo-sec--navigation", "[class*=made-with]", "[class*=uxfolio-badge]",
                "script", "style", "noscript"):
        for el in soup.select(sel):
            el.decompose()
    for el in soup.find_all(string=re.compile(r"Made with", re.I)):
        parent = el.find_parent()
        if parent and len(norm(parent.get_text())) < 40:
            parent.decompose()

    counter = [0]
    blocks = []
    for sec in soup.select("div.ufo-sec"):
        m = re.search(r"ufo-sec--([a-z0-9]+)", " ".join(sec.get("class", [])))
        stype = m.group(1) if m else "text"
        if stype in ("bg", "navigation"):
            continue
        # skip nested sections (handled by their own iteration)
        if sec.find_parent("div", class_="ufo-sec"):
            continue
        if stype == "process":
            blocks.append({"type": "process", "steps": steps_in(sec),
                           "text": [], "images": imgs_in(sec, slug, counter)})
            continue

        if stype == "columns":
            # Preserve the author's real column split (div.col) instead of
            # flattening it — these carry meta pairs like Role / Team / Timeline.
            cols = sec.select("div.col")
            cols = [c for c in cols if not c.find_parent("div", class_="col")]
            if len(cols) > 1:
                packed = []
                for c in cols:
                    packed.append({"text": texts_in(c), "images": imgs_in(c, slug, counter)})
                packed = [c for c in packed if c["text"] or c["images"]]
                if packed:
                    blocks.append({"type": "columns", "columns": packed, "text": [], "images": []})
                    continue

        images = imgs_in(sec, slug, counter)
        txt = texts_in(sec)
        if not txt and not images:
            continue
        blocks.append({"type": stype, "text": txt, "images": images})

    doc = {"slug": slug, "route": route, "source_url": next(
        (p["url"] for p in man["pages"] if p["tag"] == tag), None), "blocks": blocks}
    json.dump(doc, open(f"{DEST}/content/{slug}.json", "w"), indent=2, ensure_ascii=False)
    nt = sum(len(b["text"]) for b in blocks)
    ni = sum(len(b["images"]) for b in blocks)
    print(f"  {slug:22} {len(blocks):>3} blocks  {nt:>4} text runs  {ni:>3} images")

# leftover assets not referenced by any page (icons, thumbnails)
extra = [a for a in man["assets"] if a["url"] not in used_names]
print(f"\n  {len(used_names)} images placed, {len(extra)} unreferenced harvest assets")
json.dump({"unreferenced": extra}, open(f"{DEST}/content/_unreferenced-assets.json", "w"), indent=2)
