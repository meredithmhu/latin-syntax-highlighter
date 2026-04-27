# CLAUDE.md — Project conventions for Claude Code

This file is read automatically at the start of every Claude Code session.
Follow everything here without being asked.

---

## Project identity

**Meredith's Latin Notebook** — a personal interactive Latin translation viewer.
Static site. No server, no npm, no React, no build tools beyond `build.py`.
Pure HTML/CSS/JS + Python.

---

## Folder structure

```
latin-syntax-highlighter/
├── build.py                      # HTML generator — run once per poem
├── generate_annotations.py       # Fetches word annotation data via Anthropic API
├── marble.jpg                    # Shared background image (all pages)
├── toothpaste.html               # Apuleius, Apologia ch. 6
├── toothpaste.txt                # Source text for toothpaste.html
├── toothpaste_annotations.json   # Human-editable annotation data (edit "notes" here)
├── toothpaste_annotations.js     # Browser-loaded annotation data (auto-generated)
├── perpetua.html                 # Perpetua's Diary (placeholder)
├── README.md
├── USAGE.md                      # Input format and CLI warning docs
├── docs/                         # Internal project documentation
│   ├── ARCHITECTURE.md
│   ├── FEATURES.md
│   ├── ROADMAP.md
│   ├── CHANGELOG.md
│   └── DECISIONS.md
└── CLAUDE.md                     # This file
```

---

## Code style

- **No frameworks.** HTML/CSS/JS only. No dependencies to install in the browser.
- **No TypeScript.** Plain JS with `var` (matching existing style in build.py template).
- **No comments** added to code unless the logic is genuinely non-obvious.
- **No extra features** beyond what's explicitly requested. No "while I'm here" improvements.
- **No docstrings** added to functions that didn't have them.
- **Python**: 4-space indent, single quotes, f-strings. Match existing style in build.py.

---

## Build pipeline

### build.py
Converts a `.txt` poem file into a self-contained `.html` page.

```bash
python3 build.py poem.txt "Poem Title" "Author — Source"
python3 build.py poem.txt "Poem Title" "Author — Source" --enrich   # also fetches word data via API
```

**Critical implementation details:**
- The HTML template uses Python `str.format()`, so all literal CSS braces must be doubled: `{{` and `}}`.
- JS template literals (`${var}`) cannot be used inside the template — use string concatenation instead.
- Word data JSON is injected using a sentinel: `__WORD_DATA__` in the template, replaced with `.replace('__WORD_DATA__', word_data_js)` *after* `.format()` — because the JSON contains `{` and `}` that would break format().
- Template variables: `{title}`, `{subtitle}`, `{slides_html}`, `{input_stem}`, `{annotations_js}`.
- `NAV_ITEMS` constant near the bottom of build.py must be manually updated when adding new pages.

### generate_annotations.py
Fetches grammatical annotation data for each word in a poem.

```bash
python3 generate_annotations.py poem.txt
```

- Requires `ANTHROPIC_API_KEY` environment variable and `pip install anthropic`.
- Uses `claude-haiku-4-5-20251001`.
- Outputs `poem_annotations.json` (edit `"notes"` fields here) and `poem_annotations.js` (loaded by browser).
- Safe to re-run — only fetches missing words (cached).

---

## Data model

### Slide indexing
- Slide 0 is always the **title slide** (auto-generated, never from the .txt file).
- Poem content starts at `data-idx="1"`.
- Word/annotation keys use this 1-based index: `"{slide_idx}_{token}"` e.g. `"1_Calpurniane"`.

### Word key format
`{slide_idx}_{stripped_token}` where stripped_token has leading/trailing punctuation removed.
Function: `_strip_punct(s)` — `re.sub(r'^[^\w]+|[^\w]+$', '', s)`.

### annotationData structure
```json
{
  "meta": { "source": "poem.txt", "generated": "2026-04-24" },
  "words": {
    "1_Calpurniane": {
      "token": "Calpurniane",
      "slide_idx": 1,
      "summary": "vocative singular of 2nd declension masculine noun Calpurnianus",
      "why": "...",
      "gloss": "Calpurnianus, -i, m.",
      "paradigm_label": "2nd declension masculine endings",
      "paradigm": "     Sg    Pl\nNom  -us   -i\n...",
      "notes": ""
    }
  },
  "constructions": []
}
```
`constructions` is reserved for future multi-word annotation support — do not populate it yet.

### phraseData structure
Embedded inline in the HTML as `const phraseData = {...}`. Keyed by slide index (1-based string).
Each value is an array of phrase groups; each phrase group is an array of stripped token strings.
```json
{
  "9": [["quaeso"], ["quid", "habent", "isti", "versus"], ["re", "aut", "verbo", "pudendum"]]
}
```
Populated from `PHRASES:` lines in the `.txt` source. Slides with no `PHRASES:` line are absent from the object.
The sentinel `__PHRASE_DATA__` in the HTML template is replaced after `.format()`, same pattern as `__WORD_DATA__`.

---

## CSS / JS conventions

### Color scheme classes (on `<body>`)
- `mode-mud` — default. Marble background, warm beige overlay, white glow on hover.
- `mode-light` — lighter translucent overlay, cyan-blue glow on hover (`0 0 18px 4px rgba(100,210,255,0.85)`).
- `mode-dark` — near-black background, white glow, light text.

### Key constants
- `ANN_BASE_MARGIN = 280` — px of margin-top added to `.english` when entering annotations mode.
- Three-phase slide transition: 650ms fade-out → 600ms pause → 3800ms fade-in.

### English slide-down (annotations mode)
`.english` has `transition: margin-top 2.55s ease`. When entering annotations mode, all `.english` elements get `marginTop = ANN_BASE_MARGIN + 'px'` immediately. `adjustEnglishMargin()` may increase it further: `Math.max(ANN_BASE_MARGIN, latinH + cardEl.offsetHeight + 28)`.

### Annotation card positioning
Cards are `position: absolute` within `.verse` (which is `position: relative; overflow: visible`).
`left = Math.max(0, Math.min(wordLeft, verseWidth - 320))`, `top = latinH + 20`.
SVG line is dashed (`stroke-dasharray="4,3"`), drawn from word bottom-center to card top-left+10.

### Annotation notes persistence
`localStorage` key: `ann_notes_{slideIdx}_{token}`.

---

## Aesthetics — do not change without being asked

- Background: `marble.jpg` with color overlay.
- Font: Georgia, "Times New Roman", serif (body). Caveat (Google Fonts) for annotation cards.
- Site title "Meredith's Latin Notebook": fixed top center, `font-size: 1.1rem`, `color: rgba(26,26,26,0.55)`, `letter-spacing: 0.18em`.
- Navbar: frosted glass (`backdrop-filter: blur(40px) saturate(180%)`), padding-top 46px (below site title).
- Hover glow: slow left-to-right underline on English (`background-size` transition), text-shadow on Latin.
- All transitions should feel unhurried — the 3.8s slide fade-in is intentional.

---

## Adding a new poem

1. Write `newpoem.txt` in the input format (see USAGE.md).
2. Run `python3 build.py newpoem.txt "Title" "Author — Source"`.
3. Optionally run `python3 generate_annotations.py newpoem.txt` for annotation data.
4. Update `NAV_ITEMS` in `build.py` to add the page to the navbar.
5. Rebuild any existing pages so their navbars include the new link.
6. Place `marble.jpg` in the same folder (already there — shared).

---

## Things to never do

- Do not introduce npm, a bundler, a JS framework, or a CSS preprocessor.
- Do not add a backend or server-side component.
- Do not add error handling for scenarios that can't happen in practice.
- Do not redesign the aesthetic without explicit direction.
- Do not change the slide transition timing without being asked.
- Do not commit API keys.
