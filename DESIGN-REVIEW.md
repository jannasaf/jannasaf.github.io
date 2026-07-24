# Design review — Janna Safran portfolio

Reviewed: the live site at `https://uxfol.io/7a0815b4`, harvested 2026-07-24 at 1440×1000 (2× DPR).
Every number below is measured from that harvest, not estimated. Reproduce with `claude/build.py` and the scripts noted per finding.

## What the current site gets right

Worth protecting through any rebuild:

- **The case studies are genuinely strong.** 2,051 / 1,768 / 1,130 words with a real research → decision → outcome spine. Concierj carries 59 interviews across 4 stakeholder groups; Safe Water Network carries 87 usability participants across 4 rounds. Most portfolios at this level have process theatre. This has evidence.
- **"Key design decision:" as a recurring marker.** It appears at each fork and states the call plus the reasoning. That is the single most valuable structural device on the site and it should survive verbatim.
- **Outcomes are quantified** — +30% donations, +35% engagement, $80k+ raised, 2 hours → 30 seconds, 95% less manual entry, 100% adoption in 2 weeks.
- **The type pairing is a real choice.** Instrument Serif against Inter Tight is not the default portfolio pairing, and the serif at 56px carries the hero.

## Findings

Ordered by how much they cost the work.

### 1. Two numbers contradict themselves inside the same case study

The most serious problem on the site, and it is a content problem, not a design one.

| Case study | Claim A | Claim B |
|---|---|---|
| Workflow automation | "reducing setup time from two hours to **under two minutes**" (overview) | "reduced project setup went from two hours to **under 30 seconds**" (body) — and "**under 30 seconds**" again in Impact |
| Safe Water Network | "donors launched **11** fundraisers" (prose) | "**12** — Peer-to-peer fundraisers launched" (stat tile) |

A hiring manager who notices either one starts discounting every other number on the site. Pick one figure per claim and make the stat tile and the prose read from the same source.

Verify: `grep -o "two hours to under [a-z0-9 ]*" claude/content/workflow-automation.json`

### 2. Cards are invisible as containers

Measured WCAG 2.1 contrast on the harvested palette:

| Pair | Ratio | Normal text |
|---|---|---|
| `#CBCBCB` panel on `#DDDDDD` page | **1.19:1** | — (container edge) |
| `#5A5A5A` muted on `#CBCBCB` panel | **4.25:1** | **fails AA** (needs 4.5) |
| `#5A5A5A` muted on `#DDDDDD` page | 5.08:1 | passes AA |
| `#060606` ink on `#DDDDDD` page | 14.92:1 | passes AA |

Two consequences. The project cards do not read as cards — 1.19:1 is below the 3:1 floor for a meaningful non-text boundary, so the grid reads as loose imagery on grey rather than three selectable things. And every card subtitle ("Independent Venture · 2026", "Safe Water Network", "Adolescent Health Initiative, Michigan Medicine") is muted-on-panel at 16px, which fails AA for normal text.

Cheapest fix that keeps the palette: put cards on `#FEFEFE` (1.35:1 edge — still soft, but subtitles jump to 6.84:1 and pass), or darken the subtitle to `#3C3C3C` on the existing panel.

### 3. Roughly 45% of the canvas is empty at desktop width

The container is 1440px, but the hero headline wraps inside about 55% of it and stops. Same pattern down the page: the Overview prose sits left while the right column holds only Role / Team / Timeline; the "See the live site" and "Explore the Demo" CTAs sit alone in a left column with the image far right. The result is a persistent right-hand void that reads as a template the content never filled rather than as deliberate negative space.

This is the highest-leverage layout change available, and it costs nothing in content.

### 4. The two grey emphasis passages de-emphasize the wrong words

The hero markup is one Instrument Serif sentence with two spans pushed to `#5A5A5A`:

> I'm a ⟨systems-minded⟩ UX researcher and product strategist who turns complex needs into clear product direction, ⟨from early discovery through launch⟩.

"systems-minded" is the differentiator and "from early discovery through launch" is the scope claim — the two most load-bearing phrases in the sentence are the two that are visually receded. The grey reads as washed-out rather than as emphasis. Either invert it (grey the connective tissue, ink the claims) or drop the second span entirely and let one emphasis carry.

### 5. The third case study is half a case study

| | Blocks | Images | Words | Page height | Numbered process strip |
|---|---|---|---|---|---|
| Concierj | 26 | 16 | 2,051 | 13,661px | yes (5 steps) |
| Safe Water Network | 23 | 17 | 1,768 | 13,162px | yes (5 steps) |
| Workflow automation | 14 | 12 | 1,130 | **6,907px** | **no** |

Workflow automation is the one that shows operational range — internal tools, systems thinking, an automation build — and it presents at half the depth of the others and without the process strip that frames them. Either bring it up to the same scaffold or make its brevity deliberate (label it a shorter-form piece) rather than accidental.

### 6. Platform artifacts leak into the work

The "Made with uxfolio" badge renders *over* page content — it lands on the Team / Timeline column of the Concierj overview, and over the second project card on the home page. On a page whose entire argument is craft and attention to detail, a third-party badge occluding your own content is the wrong first impression. Removed in the rebuilt base.

### 7. Eleven copy defects, all verified

| Case study | Defect |
|---|---|
| Concierj | "an expeirence" → experience |
| Concierj | "unconver edge cases" → uncover |
| Concierj | "while minimalizing" → minimizing |
| Concierj | "identifying the ore capabilities" → core |
| Concierj | "guest-decison making" → decision |
| Concierj | "one of Concerj's three core pillars" → Concierj (own product name) |
| Concierj | "important to say flexible" → stay flexible |
| Concierj | "asked guests to self-identity their trip" → self-identify |
| Concierj | "The assistant become significantly more resilient" → became |
| Safe Water Network | "sent donors directly do a third-party form" → to |
| Safe Water Network | "a psychological barrier that prevent some supporters" → prevented |

The misspelling of the product's own name is the one that stings. Note also that Concierj carries 9 of 11 — it is the newest case study and reads as the least proofread, which is the opposite of the impression the most recent work should give.

Reproduce: the grep block in the review transcript, run over `claude/content/*.json`.

### 8. Smaller items

- **The footer repeats on all five pages.** "Let's connect!" plus the same 27-word paragraph appears on home, about, and all three case studies. Fine as a footer; it currently reads as a section.
- **No visible CTA hierarchy.** "Explore the Demo" (Concierj, a live product) and "See the live site" (SWN) are the highest-value actions on the site and render as small black pills orphaned in a left column.
- **Thumbnail density is inconsistent.** Concierj's card is a 4-image collage of tall phone screens; workflow automation's is a single 858×536 laptop. The grid reads unevenly because the source imagery was never normalized.
- **No LinkedIn URL.** The footer icon is present on the live site but `site.json` has an empty `linkedin` field — needs the real URL.
- **`0 -> 1`** appears as an ASCII arrow in the DOM text and renders as `0 → 1`. Normalized to `→` in the content model.

## What the rebuilt base already changes

`claude/site/` is a faithful, framework-free reproduction — same tokens, same content, same structure — with the mechanical problems fixed:

- uxfolio badge, Meta Pixel, GTM, LinkedIn Insight, and Google Analytics all removed (5 third-party trackers on the original)
- Real semantic landmarks, skip link, visible focus states, `aria-current` on nav
- The Overview column split preserved as a genuine two-column grid (prose | meta) instead of CSS `columns`
- Responsive to 390px with no horizontal overflow; `prefers-reduced-motion` respected
- Verified: 0 broken images, 0 console errors, no horizontal overflow at 1440px and 390px

Content and palette are deliberately **unchanged** — findings 1–5 and 7 are decisions for Janna, not ones to make silently in a rebuild.

## Suggested order of work

1. Fix the two numeric contradictions and the eleven typos — free, and the highest credibility return.
2. Resolve the dead right-hand column; it is one layout decision that affects every page.
3. Fix card contrast so the grid reads as three selectable projects.
4. Decide the hero emphasis.
5. Bring workflow automation up to depth, or frame its brevity.
6. Promote the live-demo CTAs.

Framework choice is orthogonal to all six — the content layer in `claude/content/` is plain JSON and ports to anything.
