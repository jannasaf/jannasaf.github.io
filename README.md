# Janna Safran — portfolio

Static portfolio site. Content and imagery were migrated off the hosted uxfol.io
build (`https://uxfol.io/7a0815b4`) into a plain JSON content layer so the site is
no longer tied to that platform.

No framework yet — deliberately. The content layer is portable, so the framework
decision is still open.

## Layout

```
content/           portable content layer (plain JSON, no framework coupling)
  site.json          site-level model: profile, nav, projects, tokens (hand-authored)
  <slug>.json        per-page ordered blocks (machine-extracted from the original)
assets/img/         39 images pulled from the original site
build.py            generator: content/ + assets/ -> site/
site/               build output (5 static pages, self-contained)
tools/              the migration pipeline, kept so the harvest is reproducible
  harvest.py         drives headless Chromium over the live site, saves DOM + assets
  extract.py         converts harvested DOM into content/*.json
  verify.py          screenshots the build, reports broken images / overflow / console errors
reference/          original-site screenshots + asset manifest, for fidelity checks
archive/codex-astro/  earlier Astro attempt, kept for reference
DESIGN-REVIEW.md    review of the original site with measured findings
```

## Build

```sh
python3 build.py            # -> site/
python3 -m http.server -d site 8747
```

Requires Python 3 only. `tools/` additionally needs `playwright` and `beautifulsoup4`,
and is only needed to re-harvest from the original site.

## Content model

`content/site.json` holds everything site-level and is meant to be edited by hand.
`content/<slug>.json` holds per-page blocks in document order, each tagged with a
type (`mainheader`, `columns`, `textandmedia`, `cards`, `gallery`, `process`, `text`)
that `build.py` maps to a layout. Both are plain JSON with no build-tool assumptions.

Design tokens live in `content/site.json` under `tokens` — they were measured from the
original site's computed styles, not guessed:

| Token | Value |
|---|---|
| page | `#DDDDDD` |
| panel | `#CBCBCB` |
| surface | `#FEFEFE` |
| ink | `#060606` |
| muted | `#5A5A5A` |
| display | Instrument Serif |
| body | Inter Tight 300 |

## What changed from the original

Removed: the "Made with uxfolio" badge (it rendered over page content), plus Google
Tag Manager, Google Analytics, the Meta Pixel, and the LinkedIn Insight tag.

Added: semantic landmarks, a skip link, visible focus states, `aria-current` on nav,
responsive layout down to 390px, and `prefers-reduced-motion` support.

Content and palette are unchanged — see `DESIGN-REVIEW.md` for the findings that are
still open decisions rather than mechanical fixes.
