# Delphi
AI Science Officer

## What is this?

A minimalist, SHL-branded news brief viewer with **two interface styles**, each viewable in **two device layouts** — four combinations total, switched instantly with two independent toggles in the header.

**Interface style** (`Cards` / `Headlines`):
- **Cards** — the original Inshorts-style experience. One story at a time, shown as a full-bleed card (image, title, description, "Read more") that you page through with a **Next** button, swipe, mouse wheel, or arrow keys.
- **Headlines** — a Hacker News-style scannable list. All stories at once, each as a numbered row with a linked title, source domain, and a one-line description — built for someone (e.g. a CXO) who wants to scan many headlines quickly rather than swipe through them one by one. There are no images in this view — only Cards shows images.

**Device layout** (`Web` / `Mobile`):
- **Web** — the current view fills a wide panel on the page.
- **Mobile** — the whole screen turns black and the current view is shown inside a phone-shaped mockup (notch, rounded bezel) centered on the page, simulating how it'd look on a phone.

Every story — in either interface style — has a **thumbs up / thumbs down** review control, so you can react to it. A reaction is saved per-story in the browser's `localStorage` (so it survives a page reload) and stays in sync between Cards and Headlines — react to a story in one view, switch to the other, and the same reaction is already reflected there.

It's a static site — plain HTML/CSS/JS, no build step, no backend, no dependencies.

## What's been done

**Phase 1 — Cards + Web/Mobile**
- Built the full front end from scratch: [index.html](index.html), [styles.css](styles.css), [script.js](script.js).
- Theme colors (`#78D64B` green, `#4A4A4A` grey) were sampled directly from `assets/shl-logo.png` to match SHL's actual branding.
- Story data is embedded directly in `script.js` (based on `sample_data/stories.json`), with dummy values filled in for the currently-empty `imageURL` / `readmoreURL` fields:
  - Image → `assets/shl-logo.png`
  - Read more link → `https://www.shl.com/careers/`
- Implemented the Inshorts-style card deck: vertical slide transition, segmented progress bar, Next button, plus swipe/wheel/keyboard navigation.
- Implemented the Web/Mobile toggle, including the phone-bezel mockup used in Mobile mode.
- Added the thumbs up/down review control per card, with mutually-exclusive state, toggle-off-on-repeat-click, and persistence via `localStorage`.

**Phase 2 — Headlines interface style**
- Added a second header toggle, **Cards / Headlines**, independent of the existing Web/Mobile toggle, so all four combinations (Cards×Web, Cards×Mobile, Headlines×Web, Headlines×Mobile) work.
- Built the Headlines view: a scrollable, numbered list in the same green/white SHL theme as Cards, with no images — title (linked to "Read more"), source domain, a short description, and the same thumbs up/down control.
- Refactored the reaction system so a story's thumbs up/down state is shared between however many places it's rendered (Cards and Headlines both exist in the DOM at once) — reacting in one view updates the other immediately.
- Verified end-to-end in a real headless Chromium session across all four view combinations, plus reaction-state sync and `localStorage` persistence — no console errors.

## Project structure

```
Delphi/
├── index.html          # page structure (header, both toggles, card viewport, headline list)
├── styles.css           # SHL theme, web/mobile layouts, card styles, headline-list styles
├── script.js             # story data + card + headline rendering, navigation, toggles, reactions
├── assets/
│   └── shl-logo.png     # SHL logo — used in the header and as the dummy card image
├── sample_data/
│   └── stories.json      # source story content (title/description) used to seed script.js
└── README.md
```

## Running it locally

No install, no build — just serve the folder and open it in Chrome or Edge.

### Option A — serve it (recommended)

From the parent directory (one level above `Delphi/`):

```bash
cd ~/AI-Thon/Delphie?
python3 -m http.server 8100
```

Then open:

```
http://localhost:8100/Delphi/
```

> Note the `/Delphi/` in the URL — `http.server` serves whatever directory you ran it from, and here that's the parent folder, not `Delphi/` itself.

If you'd rather not deal with the path, `cd` straight into the app folder instead and drop the `/Delphi/` suffix:

```bash
cd ~/AI-Thon/Delphie?/Delphi
python3 -m http.server 8100
```
then open `http://localhost:8100/`.

Stop the server with `Ctrl+C` in that terminal.

### Option B — open the file directly

Double-click `index.html`, or:

```bash
xdg-open "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/index.html"   # Linux
open "/home/aashutosh.joshi/AI-Thon/Delphie?/Delphi/index.html"        # macOS
```

This works fine here since all story data is embedded in `script.js` rather than fetched — no CORS issues from opening via `file://`.

## Using the app

| Action | How |
|---|---|
| Switch interface style | Click **Cards** / **Headlines** in the top-right toggle |
| Switch device layout | Click **Web** / **Mobile** in the top-right toggle |
| Next card *(Cards view)* | Click the green ⌄ button, swipe up, scroll down, or press `↓` / `Space` |
| Previous card *(Cards view)* | Swipe down, scroll up, or press `↑` |
| Open full story | Click the title (**Headlines**) or **Read more** (**Cards**) |
| React to a story | Click 👍 or 👎 next to the story (click again to undo) — synced across both interface styles |

## Customizing

- **Story content**: edit the `RAW_STORIES` array in [script.js](script.js).
- **Dummy image/link**: change `DUMMY_IMAGE` / `DUMMY_URL` at the top of [script.js](script.js) — swap these once real per-story images and URLs are available.
- **Colors**: all theme colors are CSS custom properties at the top of [styles.css](styles.css) (`:root`).
