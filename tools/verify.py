"""Screenshot the built site at desktop + mobile, and report console errors / broken images."""
import os, sys, glob
from playwright.sync_api import sync_playwright

SITE, OUT = sys.argv[1], sys.argv[2]
os.makedirs(OUT, exist_ok=True)
PAGES = ["index.html", "about.html", "work/concierj.html",
         "work/safe-water-network.html", "work/workflow-automation.html"]

with sync_playwright() as pw:
    b = pw.chromium.launch()
    for label, vp in (("desktop", {"width": 1440, "height": 1000}),
                      ("mobile", {"width": 390, "height": 844})):
        ctx = b.new_context(viewport=vp, device_scale_factor=2)
        pg = ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(f"console.{m.type}: {m.text}") if m.type == "error" else None)
        pg.on("pageerror", lambda x: errs.append(f"pageerror: {x}"))
        for p in PAGES:
            pg.goto(f"file://{SITE}/{p}", wait_until="load")
            pg.wait_for_timeout(1800)
            pg.evaluate("""async () => { for (let y=0; y<document.body.scrollHeight; y+=800){
                window.scrollTo(0,y); await new Promise(r=>setTimeout(r,60)); } window.scrollTo(0,0); }""")
            pg.wait_for_timeout(900)
            tag = p.replace("/", "_").replace(".html", "")
            pg.screenshot(path=f"{OUT}/{label}_{tag}.png", full_page=True)
            broken = pg.evaluate("""() => [...document.images]
                .filter(i => !i.complete || i.naturalWidth === 0).map(i => i.getAttribute('src'))""")
            over = pg.evaluate("() => document.documentElement.scrollWidth > window.innerWidth + 1")
            print(f"  {label:8} {p:34} broken_imgs={len(broken)} h_overflow={over}")
            for x in broken[:6]:
                print(f"      BROKEN: {x}")
        for x in errs[:10]:
            print(f"  !! {label} {x}")
        ctx.close()
    b.close()
print("\nshots ->", OUT)
