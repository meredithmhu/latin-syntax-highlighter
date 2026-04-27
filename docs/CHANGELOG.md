# Changelog

Entries are in reverse chronological order. Dates are approximate based on session history.

---

## 2026-04-24 (session 2)

### Navigation mode restructure
- **Default mode changed** — page now loads in all-lines mode (all slides stacked, visible on scroll), not line-by-line
- **All-lines mode** (formerly "no-scroll mode") is now the default: `body` starts with class `noscroll-mode`, `enterNoScroll()` is called at JS init
- **Line-by-line mode** (formerly "scroll mode") is now the alternate: navigated by `←` / `→` arrow buttons fixed at bottom-right (`#prev-slide`, `#next-slide`)
- Scroll wheel still wired but has no effect in all-lines mode (existing guard: `if (mode !== 'scroll') return`)
- Arrow buttons hidden in all-lines mode via `body.scroll-mode .slide-nav { display: block }` — only appear in line-by-line mode
- Toggle button label: shows **"line-by-line"** when in all-lines mode, **"all lines"** when in line-by-line mode

### Annotations mode — static map architecture (major refactor)
- Replaced single-active-card system with `Map`/`Set` architecture supporting any number of simultaneously open cards
- `verseLayouts: Map<verse, Map<wordEl, { cardEl, lineEl }>>` — all positions pre-computed once in `buildVerseLayouts()`
- `openCards: Set<wordEl>` — tracks which words have visible cards
- Clicking a word toggles only that word's card; mode never closes from a word click
- Card positions and SVG lines are fixed at layout time and never repositioned
- Greedy left-to-right placement: N equal-width slots across verse width, centered on words, no overlap
- SVG lines pre-drawn at fixed positions with `opacity: 0`, fade to `opacity: 1` when word is clicked
- English margin set to fit all cards simultaneously: `Math.max(ANN_BASE_MARGIN, latinH + maxCardH + 28)`

### Annotations mode — English slide-down fix
- Changed from `margin-top` to `transform: translateY(...)` — transform does not affect layout flow, so Latin text no longer shifts when English slides down

### Annotations mode — visual polish
- `ANN_BASE_MARGIN` raised to 280px (was 200px)
- `ann-summary` font size set to 1.8rem (Caveat)
- `ann-expand-hint` added ("↓ expand") — hidden once expanded
- Expand/collapse behavior: clicking summary or hint toggles `ann-expanded.open`; hint disappears when open
- Persistent glow on annotated words: same `text-shadow` values as `lat-active` so hover doesn't intensify an already-glowing word
- Left-to-right underline reveal on annotated words via `background-size: 0% → 100% 2.5px` (1s ease)
- SVG line drawn from word bottom-center to card top-center (not top-left)
- `stroke-dasharray="4,3"` dashed style on SVG lines

### English slide transition
- Transition duration 1.55s ease (reduced from 2.55s)

---

## 2026-04-24 (session 1)

### Project cleanup
- Deleted `v3.html` (wipe-transition variant, abandoned)
- Deleted `toothpaste.html` (stale build.py output that predated v2)
- Renamed `v2.html` → `toothpaste.html` (the canonical Apuleius page)
- Deleted `index.html` (old dark-themed prototype, unrelated to current project)
- Updated all `href="v2.html"` references to `href="toothpaste.html"` in `perpetua.html`, `toothpaste.html`, and `build.py`'s `NAV_ITEMS`

### Documentation
- Created `docs/` directory with ARCHITECTURE.md, FEATURES.md, ROADMAP.md, CHANGELOG.md, DECISIONS.md
- Created `CLAUDE.md` at project root (auto-read by Claude Code each session)
- Created `.cursorrules` at project root (mirrors key points from CLAUDE.md)

---

## 2026-04-23 (session 2)

### Annotations mode (initial implementation)
- Added annotations mode toggle button at `top: 88px; right: 44px`
- English slide-down: `.english` elements animate via `margin-top` on toggle
- Annotation cards: `position: absolute` within `position: relative; overflow: visible` `.verse`
- Dashed SVG line from word to card
- Caveat (Google Fonts) handwriting font for cards
- Expand/collapse panels: "Dictionary gloss / form info" and "Drill this form"
- `localStorage` notes persistence: `ann_notes_{slideIdx}_{token}`
- Click handler routes by mode: annotations mode → `showAnnotation()`, default → `showCard()`

### generate_annotations.py (new file)
- Standalone script to fetch annotation data for any poem
- Fields: `summary`, `why`, `gloss`, `paradigm_label`, `paradigm`, `notes`
- Outputs `_annotations.json` (human-editable) and `_annotations.js` (browser-loaded)
- Caching: re-run is safe, only missing words are fetched
- `constructions: []` array reserved for future multi-word annotation support
- Uses `claude-haiku-4-5-20251001`

---

## 2026-04-23 (session 1)

### Word info cards (click mode)
- Clicking a Latin word in default mode shows a card with gloss, summary, paradigm drill
- `wordData` object keyed by `{slide_idx}_{token}`
- `--enrich` flag in build.py calls Anthropic API to populate `wordData`
- `__WORD_DATA__` sentinel pattern: JSON injected after `.format()` to avoid brace collision

### Site title
- Added "Meredith's Latin Notebook" as fixed centered title above navbar

### Navbar
- Renamed "Latin Translations" → "Latin Texts"

### CLI warning system
- `validate_block()` in build.py checks for: unmapped words, missing English targets, duplicate group IDs

### USAGE.md
- Full documentation: input format, `->` and `|` syntax, mapping rules, warning descriptions

---

## Earlier (session 0 / initial)

- Initial commit: `v2.html` (Apuleius, Apologia ch. 6, lines 3–11)
- Hover glow + English highlight with left-to-right underline animation
- Word mapping groups, non-adjacent English chunks
- Slide-by-slide scroll mode (three-phase fade transition)
- No-scroll mode toggle
- Three color schemes: mud, light, dark
- `toothpaste.txt` source file
- `marble.jpg` background image
