# Architecture

## Overview

Meredith's Latin Notebook is a **fully static site** — no server, no database, no build pipeline at runtime. Each poem is a self-contained HTML file that runs entirely in the browser. Python scripts handle the one-time build step (generating HTML from text) and the one-time data step (fetching grammatical annotations from the Anthropic API).

---

## Tech stack

| Layer | Technology | Why |
|---|---|---|
| Pages | Plain HTML/CSS/JS | No framework overhead; files are shareable as single URLs |
| Build | Python 3 (`build.py`) | One-time generation; keeps source text readable and editable |
| Annotation data | Anthropic API (`claude-haiku-4-5-20251001`) | Grammatical annotation is too nuanced for a lookup table |
| Annotation font | Google Fonts — Caveat | Handwriting feel for margin-note aesthetic |
| Notes persistence | `localStorage` | No server; notes live in the browser |
| Background | `marble.jpg` (shared file) | Single image shared by all pages via relative path |

---

## File topology

```
build.py  ──────────────────────────► poem.html   (one-time build)
  + poem.txt (source)
  + --enrich flag (optional)

generate_annotations.py ────────────► poem_annotations.json   (human-editable)
  + poem.txt                           poem_annotations.js    (browser-loaded)
  + ANTHROPIC_API_KEY

poem.html loads at runtime:
  ├── marble.jpg
  ├── poem_annotations.js  (if present; onerror silently skipped)
  ├── phraseData            (embedded inline — parsed from PHRASES: lines at build time)
  └── Google Fonts CDN (Caveat)
```

---

## HTML template pipeline

`build.py` contains a large HTML string (`HTML`) that is the full page template.

1. **Parse** `poem.txt` into blocks (slide number, Latin line, English translation, word mapping).
2. **Generate** `slides_html` — the `<div class="slide">` markup for each block.
3. **Inject** via `HTML.format(title=..., slides_html=..., input_stem=..., ...)`.
   - All literal CSS braces in the template are doubled (`{{`, `}}`) to survive `.format()`.
   - JS template literals are avoided inside the template (use string concatenation instead).
4. **Inject word data** via `.replace('__WORD_DATA__', word_data_js)` *after* `.format()`.
   - This sentinel pattern is necessary because word data JSON contains `{` and `}` which would crash `.format()`.
5. **Write** to `poem.html`.

**Warning:** `build.py`'s HTML template is currently **out of sync** with `toothpaste.html`. The template does not yet include the static-map annotations architecture, the navigation mode restructure, or the `transform`-based English slide. Before using `build.py` to generate a new poem, the template must be updated to match `toothpaste.html`. See ROADMAP.md.

---

## Annotation data pipeline

Separate from the HTML build, so annotations can be regenerated without rebuilding the page.

- `generate_annotations.py poem.txt` — calls the Anthropic API once per unique word per slide, caches results in `poem_annotations.json`.
- Output: `poem_annotations.js` — a single JS file that sets `var annotationData = {...}`.
- The HTML page loads this via `<script src="poem_annotations.js" onerror="">` — the `onerror=""` means the page works fine with no annotation data; annotations mode just shows empty cards.
- Edit `"notes"` fields directly in `poem_annotations.json`, then re-run `generate_annotations.py` to regenerate the `.js`. Only missing words are re-fetched.

---

## Runtime JS architecture

### State

```
mode            'noscroll' | 'scroll'     — current navigation mode
current         number                    — index of active slide (line-by-line mode)
animating       bool                      — prevents double-advancing during fade
observer        IntersectionObserver      — used in all-lines mode, null in line-by-line
annotationsMode bool                      — whether annotations mode is active
layoutsBuilt    bool                      — whether buildVerseLayouts() has run
verseLayouts    Map<verse, Map<word, {cardEl, lineEl}>>  — static annotation layout
openCards       Set<wordEl>               — words with currently visible cards
phraseData      object                    — { "1": [[tok, ...], ...], ... } phrase groups per slide
```

### Mode system

Two modes controlled by CSS classes on `<body>`:

- `noscroll-mode` — all slides stacked, IntersectionObserver fades them in, page scrolls freely.
- `scroll-mode` — one slide at a time, three-phase fade on `←`/`→` arrows.

`enterNoScroll()` and `enterScroll()` handle transitions between modes. `enterNoScroll()` is called at JS initialization to set the default.

### Annotation layout

`buildVerseLayouts()` runs once (inside a `requestAnimationFrame` after `body.annotations-mode` is applied). It:
1. Measures each verse's width and Latin line height.
2. Creates N card elements at fixed horizontal positions (equal-width slots, greedy placement).
3. Pre-draws N SVG lines at those positions (invisible).
4. Measures card heights and sets each verse's English `transform` to accommodate all cards.

After this, toggling cards is purely CSS class + opacity changes — no measurement or positioning happens.

---

## Slide indexing

- Slide 0 is always the **title card** (auto-generated from the title/subtitle arguments).
- Poem content slides start at `data-idx="1"`, matching the 1-based index used in annotation keys.
- Word/annotation key format: `"{slide_idx}_{stripped_token}"` — e.g. `"1_Calpurniane"`.
- `stripPunct()` removes leading/trailing non-word characters from tokens.

---

## Key design constraints

**No server.** The site is designed to be opened directly from the filesystem or served as static files. `localStorage` handles all persistence.

**Self-contained HTML files.** Each poem page is a single `.html` file (plus the shared `marble.jpg` and its `_annotations.js`). Easy to share or archive.

**Separation of build and data.** `build.py` generates the HTML structure. `generate_annotations.py` generates the linguistic data. They run independently.

**No frameworks, no npm.** Plain JS with `var` (matching existing code style). No TypeScript, no bundler. Adding a dependency requires an explicit decision.

**Aesthetic is intentional.** The 3.8s fade-in, the marble background, the Caveat font for annotations — these are not accidental. Do not change them without being asked.
