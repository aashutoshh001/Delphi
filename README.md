# Delphi
AI Science Officer

## What is this?

A minimalist, SHL-branded, Inshorts-style news brief viewer. Stories are shown one at a time as full-screen cards (image, title, description, "Read more" link) that you page through with a **Next** button, swipe, mouse wheel, or arrow keys — just like the Inshorts app.

It also has a **Web / Mobile** toggle in the header:
- **Web** — the card fills a wide panel on the page.
- **Mobile** — the whole screen turns black and the card is shown inside a phone-shaped mockup (notch, rounded bezel) centered on the page, simulating how it'd look on a phone.

Each card also has a **thumbs up / thumbs down** review control next to "Read more", so you can react to a story. Your reaction is saved per-story in the browser's `localStorage`, so it's remembered if you reload the page.

It's a static site — plain HTML/CSS/JS, no build step, no backend, no dependencies.

## What's been done

- Built the full front end from scratch: [index.html](index.html), [styles.css](styles.css), [script.js](script.js).
- Theme colors (`#78D64B` green, `#4A4A4A` grey) were sampled directly from `assets/shl-logo.png` to match SHL's actual branding.
- Story data is embedded directly in `script.js` (based on `sample_data/stories.json`), with dummy values filled in for the currently-empty `imageURL` / `readmoreURL` fields:
  - Image → `assets/shl-logo.png`
  - Read more link → `https://www.shl.com/careers/`
- Implemented the Inshorts-style card deck: vertical slide transition, segmented progress bar, Next button, plus swipe/wheel/keyboard navigation.
- Implemented the Web/Mobile toggle, including the phone-bezel mockup used in Mobile mode.
- Added the thumbs up/down review control per card, with mutually-exclusive state, toggle-off-on-repeat-click, and persistence via `localStorage`.
- Verified end-to-end in a real headless Chromium session (card rendering, Next navigation, mode toggle, reaction state + persistence) — no console errors.

## Project structure

```
Delphi/
├── index.html          # page structure (header, toggle, card viewport)
├── styles.css           # SHL theme, web layout, phone-mockup layout, card styles
├── script.js             # story data + card rendering, navigation, toggle, reactions
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
| Next card | Click the green ⌄ button, swipe up, scroll down, or press `↓` / `Space` |
| Previous card | Swipe down, scroll up, or press `↑` |
| Open full story | Click **Read more** |
| React to a story | Click 👍 or 👎 in the card footer (click again to undo) |
| Switch layout | Click **Web** / **Mobile** in the top-right toggle |

## Customizing

- **Story content**: edit the `RAW_STORIES` array in [script.js](script.js).
- **Dummy image/link**: change `DUMMY_IMAGE` / `DUMMY_URL` at the top of [script.js](script.js) — swap these once real per-story images and URLs are available.
- **Colors**: all theme colors are CSS custom properties at the top of [styles.css](styles.css) (`:root`).
