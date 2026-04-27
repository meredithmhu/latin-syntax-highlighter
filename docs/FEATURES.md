# Features

## Hover glow + English highlight

Hovering over a Latin word causes it to glow (CSS `text-shadow`) and simultaneously reveals its corresponding English translation below, which brightens and gets a slow left-to-right underline (CSS `background-size` transition from `0%` to `100%`).

**Mapping system:**
- Each Latin word (or group of words) maps to one or more English "chunks" — spans within the English translation.
- Multiple Latin words can share a group ID, so hovering any one of them lights up all of them together.
- A single Latin word can map to non-adjacent English chunks (both light up at once).
- Unmapped words (no `->` in the source text) get no hover behavior — they render as plain text.

**Implementation:** A single `mouseover`/`mouseleave` event listener on the `#slides` container reads `data-group` attributes and adds/removes `.lat-active` / `.eng-active` classes.

---

## All-lines mode (default)

The page loads with all poem lines stacked vertically. Slides fade in as they scroll into the viewport (IntersectionObserver with `threshold: 0.15`). The page scrolls normally — the wheel has no special navigation behavior in this mode.

- Body class: `noscroll-mode`
- Toggle button text while in this mode: **"line-by-line"** (click to switch)
- The IntersectionObserver is created in `enterNoScroll()` and disconnected when switching modes.

---

## Line-by-line mode

An alternate reading mode where one slide is shown at a time, navigated with `←` / `→` arrow buttons fixed at the bottom-right of the screen. Each transition uses a three-phase fade:

1. **Fade out** — current slide disappears over 650ms.
2. **Pause** — the page is empty for 600ms.
3. **Fade in** — next slide surfaces slowly over 3800ms (intentionally contemplative).

The long fade-in is intentional. Do not change it without being asked.

- Body class: `scroll-mode`
- Toggle button text while in this mode: **"all lines"** (click to switch)
- Arrow buttons (`#prev-slide`, `#next-slide`) are `display: none` in all-lines mode and `display: block` in line-by-line mode via `body.scroll-mode .slide-nav { display: block; }`.
- Scroll wheel is wired but has no effect in all-lines mode (guarded by `if (mode !== 'scroll') return`).

---

## Three color schemes

Cycled with a button in the top-right (`#scheme-toggle`). The class on `<body>` drives all color changes.

| Class | Background | Overlay | Glow color |
|---|---|---|---|
| `mode-mud` (default) | `marble.jpg` | warm beige `rgba(200,175,148,0.54)` | white |
| `mode-light` | `marble.jpg` | lighter, more translucent | cyan-blue (see DECISIONS.md ADR-008 for exact values) |
| `mode-dark` | soft near-black `#1c1a17` | none | white, all text shifted to light values |

---

## Word info cards (default click mode)

Clicking a Latin word (when *not* in annotations mode) shows a frosted-glass card centered on the viewport with:
- The word token as heading
- Grammatical parse
- Why this form appears here
- Quick reference paradigm table
- Meredith's notes

**Requires** the `--enrich` flag when building with `build.py`, which calls the Anthropic API to fetch word data and embeds it as `var wordData = {...}` in the HTML. Without enrichment, `wordData` is an empty object and cards show a placeholder message.

---

## Annotations mode

A toggle button (`annotations` / `close annotations`) at top-right (below the mode-toggle, at `top: 88px; right: 44px`) switches the page into a margin-annotation view, inspired by handwritten notes in a manuscript.

### Layout

- Body class: `annotations-mode`
- When entering, all `.english` elements immediately receive `transform: translateY(280px)` — note this is `transform`, not `margin-top`, so Latin text position is unaffected.
- `ANN_BASE_MARGIN = 280` is the constant for this baseline offset.
- After cards are measured, each verse's English margin is increased if needed: `Math.max(ANN_BASE_MARGIN, latinH + maxCardH + 28)`.

### Static map architecture (important)

All annotation cards and SVG lines are **pre-computed once** when annotations mode is first entered, via `buildVerseLayouts()`. They are never repositioned after that.

- `verseLayouts`: a `Map<verseEl, Map<wordEl, { cardEl, lineEl }>>` — the complete layout.
- `openCards`: a `Set<wordEl>` tracking which words currently have visible cards.
- Cards start at `opacity: 0; transform: translateY(10px); pointer-events: none` and transition to `opacity: 1; transform: translateY(0); pointer-events: auto` when `.visible` is added.
- SVG lines start at `opacity: 0` and transition to `opacity: 1` when their word is clicked.

### Card placement algorithm

For each verse, N cards are placed across the full verse width:

1. `cardWidth = Math.max(100, Math.floor((verseWidth - (N-1) * GAP) / N))` — equal-width slots.
2. Words sorted left-to-right by `getBoundingClientRect().left`.
3. Cards placed greedily: each card centered on its word, pushed right if it would overlap the previous card.
4. If total placement overflows the verse width, all positions are shifted left uniformly.

### Clicking a word in annotations mode

Clicking toggles that word's card independently. Any number of cards can be open simultaneously. Clicking the word again closes only that card. Annotations mode itself stays open — clicking a word never closes the mode.

### Card content

Written in Caveat (Google Fonts handwriting font). Each card has:
- `ann-summary` (1.8rem) — one-sentence grammatical summary. Click to expand/collapse the detail section.
- `ann-expand-hint` — "↓ expand" prompt, hidden when expanded.
- `ann-expanded` section (hidden until clicked):
  - `ann-why` — explanation of why this form appears in context.
  - `ann-notes` textarea — persisted to `localStorage` with key `ann_notes_{slideIdx}_{token}`.
  - Two buttons: **Dictionary gloss** and **Drill this form** — each toggles an `ann-detail` panel.

### SVG lines

One SVG canvas per verse (`position: absolute; top: 0; left: 0; overflow: visible`), pre-injected into `.verse` elements at page load. Lines are `<line>` elements with `stroke-dasharray` (dashed style), drawn from word bottom-center to card top-center, pre-rendered at fixed positions.

### Dark mode annotated-word underline

In `body.mode-dark.annotations-mode .lat-word.annotated`, an explicit `text-decoration-color: rgba(255,255,255,0.4)` is set (the underline via `background-size` gradient inherits from the non-dark rule).

### Data source

`annotationData` is loaded from `poem_annotations.js` via `<script src="..." onerror="">`. If missing, cards render with empty fields and no data. The `onerror=""` means the page never breaks.

Fields used: `summary`, `why`, `gloss`, `paradigm_label`, `paradigm`, `notes`.

---

## Navbar

Frosted-glass dropdown navbar, fixed at the top. Structure:

- Site title "Meredith's Latin Notebook" — fixed, centered, above the navbar, `pointer-events: none`, `font-size: 1.1rem`, `letter-spacing: 0.18em`, `color: rgba(26,26,26,0.55)`.
- "Latin Texts" label — hover reveals a dropdown listing all poem pages.
- Dropdown uses `backdrop-filter: blur(40px) saturate(180%)` for the frosted glass effect.
- Each new poem page must be added to `NAV_ITEMS` in `build.py` and pages rebuilt.

---

## CLI warning system (build.py)

`validate_block()` runs on each parsed block and prints warnings to stdout:

1. **Unmapped word** — a Latin word with no `->` mapping.
2. **Missing English target** — a `->` reference points to a group ID that doesn't exist in the English spans.
3. **Duplicate group ID** — the same group ID appears on two different Latin words in the same slide.

Warnings do not stop the build.

---

## Phrase groups

An optional `PHRASES:` line in each `.txt` block declares the syntactic phrase groups within that Latin line:

```
PHRASES: quaeso | quid habent isti versus | re aut verbo pudendum
```

Both `,` and `|` act as group separators. Leading/trailing punctuation is stripped from each token. The parsed data is embedded in the generated HTML as `const phraseData = { "9": [[...], ...] }`, keyed by slide index (1-based). Lines without a `PHRASES:` line are unaffected.

This data is used by the annotation reflow layout to break each line into phrase-group rows.

---

## Input format (poem.txt)

See USAGE.md for the full spec. Quick summary:

```
1
Latin line here, word1-> word2->
English translation {group1}here{/group1} and {group2}here{/group2}
word1->group1 word2->group2
```

`->` marks a word as hoverable.
`|` separates Latin words that share a hover group.
The fourth line declares the word→group mappings.
