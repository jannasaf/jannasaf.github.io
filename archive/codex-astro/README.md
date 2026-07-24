# Janna Safran portfolio

An independent, static port of Janna's UX research and product strategy
portfolio. The first version preserves the published UXfolio content and visual
direction while moving the source and image assets into this project.

## Local development

```sh
npm install
npm run dev
```

Astro prints the local URL, normally `http://localhost:4321`.

## Production check

```sh
npm run build
npm run preview
```

The generated static site is written to `dist/` and can be hosted by
Cloudflare Pages, GitHub Pages, Netlify, or any static web server.

## Where things live

- `src/pages/` contains the routes.
- `src/components/` contains the shared layout and case-study renderer.
- `src/data/uxfolio.json` is the first-pass content snapshot from the published
  portfolio. It is build-time data and is not shipped to visitors.
- `public/assets/portfolio/` contains local copies of the portfolio images.
- `src/styles/global.css` controls the overall visual system.

## Before deployment

1. Set `PUBLIC_SITE_URL` to the final production origin.
2. Review the migrated copy and the open editorial notes below.
3. Connect the Git remote supplied by Janna. This project intentionally has no
   default GitHub remote.

## Editorial notes carried over from the original

- Confirm whether the Safe Water Network result is 11 or 12 peer-to-peer
  fundraisers; both numbers appear in the source.
- Review any client-sensitive screenshots before making a new repository public.
- Add more specific descriptions to image alt text where the visual contains
  information that is not already explained by nearby copy.
