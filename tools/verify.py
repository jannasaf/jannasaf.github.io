"""Verify the built site: screenshots plus broken images, overflow, console errors.

    python3 tools/verify.py .            out/     # a local build (file://)
    python3 tools/verify.py https://...  out/     # the deployed site

Every image is decoded before the screenshot fires. Without that, `loading="lazy"`
images on these very tall case-study pages are sometimes still blank at capture
time, which makes screenshot comparison nondeterministic.
"""
import os
import sys

from playwright.sync_api import sync_playwright

TARGET, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)

PAGES = ["index.html", "about.html", "work/concierj.html",
         "work/safe-water-network.html", "work/workflow-automation.html"]

BASE = TARGET.rstrip("/") if TARGET.startswith("http") else \
    "file://" + os.path.abspath(TARGET).rstrip("/")

# Scroll the page so lazy images enter the viewport, then wait for every one of
# them to actually decode. `complete` alone can be true while the bitmap is not
# yet painted, so decode() is what makes the capture stable.
SETTLE = """async () => {
  for (let y = 0; y < document.body.scrollHeight; y += 700) {
    window.scrollTo(0, y);
    await new Promise(r => requestAnimationFrame(() => setTimeout(r, 40)));
  }
  window.scrollTo(0, 0);
  await document.fonts.ready;
  await Promise.all([...document.images].map(i =>
    i.decode ? i.decode().catch(() => {}) : Promise.resolve()));
  await new Promise(r => requestAnimationFrame(() => setTimeout(r, 120)));
}"""

failures = 0

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    for label, vp in (("desktop", {"width": 1440, "height": 1000}),
                      ("mobile", {"width": 390, "height": 844})):
        ctx = browser.new_context(viewport=vp, device_scale_factor=2)
        pg = ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}")
              if m.type == "error" else None)
        pg.on("pageerror", lambda x: errs.append(f"pageerror: {x}"))

        for p in PAGES:
            pg.goto(f"{BASE}/{p}", wait_until="load", timeout=60000)
            pg.evaluate(SETTLE)
            tag = p.replace("/", "_").replace(".html", "")
            pg.screenshot(path=f"{OUT}/{label}_{tag}.png", full_page=True)

            r = pg.evaluate("""() => ({
                broken: [...document.images]
                    .filter(i => !i.complete || i.naturalWidth === 0)
                    .map(i => i.getAttribute('src')),
                overflow: document.documentElement.scrollWidth > window.innerWidth + 1,
                h1: document.querySelectorAll('h1').length,
                noalt: [...document.querySelectorAll('img:not([alt])')].length,
                skips: (() => {
                    const l = [...document.querySelectorAll('h1,h2,h3,h4,h5,h6')]
                        .map(e => +e.tagName[1]);
                    return l.filter((v, i) => i && v > l[i - 1] + 1).length;
                })(),
            })""")
            bad = (len(r["broken"]) or r["overflow"] or r["h1"] != 1
                   or r["noalt"] or r["skips"])
            failures += bool(bad)
            print(f"  {label:8}{p:32} broken={len(r['broken'])} overflow={r['overflow']} "
                  f"h1={r['h1']} no-alt={r['noalt']} heading-skips={r['skips']}"
                  f"{'   <-- CHECK' if bad else ''}")
            for x in r["broken"][:6]:
                print(f"      BROKEN: {x}")

        for x in errs[:10]:
            print(f"  !! {label} {x}")
        failures += len(errs)
        ctx.close()
    browser.close()

print(f"\nshots -> {OUT}")
print("all checks passed" if not failures else f"{failures} page(s) need attention")
sys.exit(1 if failures else 0)
