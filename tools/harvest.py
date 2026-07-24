"""Playwright harvest of https://uxfol.io/7a0815b4 — home, about, contact, and every case study."""
import hashlib, json, os, re, sys
from urllib.parse import urlparse, unquote
from playwright.sync_api import sync_playwright

OUT, URL = sys.argv[1], "https://uxfol.io/7a0815b4"
for d in ("dom", "shots", "assets"):
    os.makedirs(f"{OUT}/{d}", exist_ok=True)

assets, pages = set(), []


def fname(u):
    n = re.sub(r"[^A-Za-z0-9._-]", "_", unquote(os.path.basename(urlparse(u).path)))[:70] or "a"
    return f"{hashlib.md5(u.encode()).hexdigest()[:8]}_{n}"


def settle(pg):
    """Scroll the whole page to force lazy-loaded media, then return to top."""
    pg.wait_for_timeout(2500)
    last = 0
    for _ in range(60):
        pg.mouse.wheel(0, 1400)
        pg.wait_for_timeout(200)
        h = pg.evaluate("window.scrollY")
        if h == last:
            break
        last = h
    pg.wait_for_timeout(2000)
    pg.evaluate("window.scrollTo(0,0)")
    pg.wait_for_timeout(600)


def grab(pg, tag):
    settle(pg)
    open(f"{OUT}/dom/{tag}.html", "w").write(pg.content())
    open(f"{OUT}/dom/{tag}.txt", "w").write(pg.inner_text("body"))
    try:
        pg.screenshot(path=f"{OUT}/shots/{tag}.png", full_page=True)
    except Exception:
        pg.screenshot(path=f"{OUT}/shots/{tag}.png")
    for u in pg.evaluate("""() => {
        const s = new Set();
        document.querySelectorAll('img').forEach(e => (e.currentSrc||e.src) && s.add(e.currentSrc||e.src));
        document.querySelectorAll('video, source').forEach(e => {
            if (e.src) s.add(e.src);
            (e.srcset||'').split(',').forEach(p => p.trim() && s.add(p.trim().split(' ')[0]));
        });
        document.querySelectorAll('*').forEach(e => {
            const m = (getComputedStyle(e).backgroundImage||'').match(/url\\(["']?([^"')]+)["']?\\)/);
            if (m) s.add(m[1]);
        });
        return [...s];
    }"""):
        if not u.startswith("data:"):
            assets.add(u)
    pages.append({"tag": tag, "url": pg.url, "chars": len(pg.inner_text("body"))})
    print(f"  [saved] {tag:38} {pg.url}", flush=True)


with sync_playwright() as pw:
    b = pw.chromium.launch()
    ctx = b.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
    pg = ctx.new_page()

    print("== HOME ==", flush=True)
    pg.goto(URL, wait_until="networkidle", timeout=90000)
    grab(pg, "00_home")

    n = len(pg.query_selector_all(".project"))
    print(f"== {n} CASE STUDIES ==", flush=True)
    for i in range(n):
        pg.goto(URL, wait_until="networkidle", timeout=90000)
        pg.wait_for_timeout(2500)
        cards = pg.query_selector_all(".project")
        if i >= len(cards):
            break
        title = re.sub(r"[^A-Za-z0-9]+", "-", (cards[i].inner_text() or "").strip())[:45].strip("-")
        try:
            cards[i].scroll_into_view_if_needed()
            cards[i].click(timeout=8000)
            pg.wait_for_load_state("networkidle", timeout=90000)
            pg.wait_for_timeout(2000)
            if pg.url.rstrip("/") == URL.rstrip("/"):
                print(f"  [warn] card {i} did not navigate ({title})", flush=True)
                continue
            grab(pg, f"{i+1:02d}_case_{title}")
        except Exception as e:
            print(f"  [fail] card {i} ({title}): {e}", flush=True)

    print("== NAV PAGES ==", flush=True)
    for label in ("About", "Contact me"):
        try:
            pg.goto(URL, wait_until="networkidle", timeout=90000)
            pg.wait_for_timeout(2000)
            pg.get_by_text(label, exact=True).first.click(timeout=8000)
            pg.wait_for_timeout(3500)
            grab(pg, f"90_{label.split()[0].lower()}")
        except Exception as e:
            print(f"  [fail] nav {label}: {e}", flush=True)

    print(f"== {len(assets)} ASSETS ==", flush=True)
    man = []
    for u in sorted(assets):
        try:
            r = ctx.request.get(u, timeout=60000)
            if not r.ok:
                print(f"  [fail {r.status}] {u}", flush=True); continue
            data, f = r.body(), fname(u)
            if not os.path.splitext(f)[1]:
                f += "." + (r.headers.get("content-type", "bin").split("/")[-1].split(";")[0])
            open(f"{OUT}/assets/{f}", "wb").write(data)
            man.append({"url": u, "file": f, "bytes": len(data)})
        except Exception as e:
            print(f"  [err] {u}: {e}", flush=True)
    print(f"  downloaded {len(man)}", flush=True)

    b.close()

json.dump({"pages": pages, "assets": man}, open(f"{OUT}/manifest.json", "w"), indent=2)
print("\nPAGES:")
for p in pages:
    print(f"  {p['chars']:>7} chars  {p['tag']}")
