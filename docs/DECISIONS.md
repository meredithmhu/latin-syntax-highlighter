# Architecture Decision Records

Each record documents a non-obvious choice, why it was made, and what alternatives were considered.

---

## ADR-001: Static site, no server

**Decision:** No backend. Every page is a self-contained HTML file that runs in the browser.

**Reasoning:** The content is a personal Latin notebook — it should be hostable on any static file host, openable directly from the filesystem, and trivially archivable. A server would add deployment complexity with no benefit for a project of this scope.

**Consequence:** Notes persistence uses `localStorage` instead of a database. This means notes are per-browser and not backed up automatically. Acceptable for a personal tool.

---

## ADR-002: One HTML file per poem

**Decision:** Each poem is its own `.html` file rather than a SPA with client-side routing.

**Reasoning:** Simpler to share, archive, and debug. No routing logic. Adding a poem is just adding a file.

**Tradeoff:** Navbar links must be manually updated in `NAV_ITEMS` (build.py) and pages rebuilt when a new poem is added. Accepted.

---

## ADR-003: `__WORD_DATA__` sentinel for JSON injection

**Decision:** Word data JSON is injected into the HTML template using `.replace('__WORD_DATA__', word_data_js)` *after* `str.format()`, not as a template variable.

**Reasoning:** The JSON string contains `{` and `}` characters (dict braces, CSS-in-JSON, etc.) which would crash `str.format()` if passed as a variable. The sentinel is a plain string that `.format()` never sees.

**Alternative considered:** `string.Template` (uses `$var` syntax) — avoided because the HTML template already uses `$` for legitimate JS purposes, creating its own collision risk.

---

## ADR-004: No JS template literals in build.py HTML template

**Decision:** Inside the `HTML` string in build.py, string concatenation is used instead of JS template literals (`` `${var}` ``).

**Reasoning:** JS template literal syntax `${var}` is identical to Python `str.format()` substitution syntax. Python would try to substitute `${var}` as a format variable and raise a `KeyError`.

**Rule:** When adding JS to the build.py template, always use `'string' + variable + 'string'` instead of `` `${variable}` ``.

---

## ADR-005: Separate build.py and generate_annotations.py

**Decision:** HTML generation and annotation data generation are two separate scripts.

**Reasoning:** They serve different purposes and run at different times. You might rebuild the HTML after fixing a styling bug without wanting to re-fetch all annotation data (expensive API calls). You might regenerate annotations after editing notes without wanting to rebuild the HTML structure. Keeping them separate means each can be run independently.

**Alternative considered:** A single `build.py --annotate` flow that does both — rejected because it couples two slow operations and makes the cache logic more complex.

---

## ADR-006: Annotation cards positioned absolute within .verse

**Decision:** Annotation cards are `position: absolute` inside `.verse` (which is `position: relative; overflow: visible`), not globally fixed or appended to `<body>`.

**Reasoning:** This works correctly in both line-by-line mode (only one `.verse` visible at a time) and all-lines mode (all `.verse` elements stacked). A global fixed card would need complex coordinate math to position near the clicked word across both modes. A `.verse`-relative card is always naturally positioned below its Latin line.

**Tradeoff:** `overflow: visible` on `.verse` means cards can visually overlap adjacent verses in all-lines mode if the user clicks quickly. Acceptable — it's an edge case in a personal tool.

---

## ADR-007: External _annotations.js file vs. embedded data

**Decision:** Annotation data is loaded via `<script src="poem_annotations.js">` with an `onerror=""` attribute, not embedded in the HTML.

**Reasoning:**
1. Keeps the HTML file stable — you can regenerate or edit annotation data without rebuilding the HTML.
2. Edit `poem_annotations.json` (human-readable), re-run `generate_annotations.py`, done. No need to touch the HTML.
3. The `onerror=""` means the page works fine with no annotation data — annotations mode just shows empty cards.

**Alternative considered:** Embedding data in the HTML template via a build step — rejected because it tightly couples the two generation pipelines.

---

## ADR-008: Caveat font for annotation cards

**Decision:** Google Fonts "Caveat" (handwriting) for annotation card text.

**Reasoning:** The annotation cards are meant to feel like handwritten margin notes — like you'd find in a scholar's copy of a text. A serif or sans-serif font would feel like a UI widget, not a note. Caveat is clean enough to be readable at small sizes but has the right handmade character.

**Alternative considered:** System fonts (no external dependency) — rejected because the aesthetic is load-bearing here. The handwriting feel is the point.

---

## ADR-009: ANN_BASE_MARGIN = 280px

**Decision:** When entering annotations mode, `.english` elements slide down 280px as a baseline, and grow further if cards are taller.

**Reasoning:** 280px gives enough room for a short card to appear without the English immediately. The `Math.max(ANN_BASE_MARGIN, latinH + maxCardH + 28)` formula ensures the English never overlaps any card, but the 280px minimum means the layout shifts predictably on toggle even before a word is clicked.

**History:** Started at 200px, raised to 280px after finding that cards with expanded sections needed more room.

**If this feels wrong:** The constant is named `ANN_BASE_MARGIN` in `toothpaste.html` and in the `build.py` template. Change it in both places.

---

## ADR-010: constructions: [] reserved but not implemented

**Decision:** The annotation JSON has a `constructions: []` array at the top level, currently always empty.

**Reasoning:** Multi-word constructions (ablative absolutes, purpose clauses, indirect statements) are the natural next step for annotation. Reserving the field in the data model now means future implementation won't require a schema migration. The browser currently ignores this field.

**Future shape (not decided yet):** Something like `{ "type": "ablative_absolute", "tokens": ["1_servo", "1_mortuo"], "summary": "...", "notes": "" }`.

---

## ADR-011: Static map architecture for annotation cards

**Decision:** All annotation card positions and SVG lines are pre-computed once in `buildVerseLayouts()` when annotations mode is first entered. Cards and lines are never repositioned after that — only opacity changes.

**Reasoning:** Earlier iterations repositioned cards on every click (calculating new positions based on whatever word was active). This caused the layout to "jump" every time a new card opened, which felt unstable. The static map makes the layout feel like something that was always there, just becoming visible.

**Implementation:** `verseLayouts` is a `Map<verseEl, Map<wordEl, {cardEl, lineEl}>>`. `openCards` is a `Set<wordEl>`. `buildVerseLayouts()` runs inside a `requestAnimationFrame` after `body.annotations-mode` is added (so cards have `display: block` and can be measured). After the first call, `layoutsBuilt = true` prevents re-running.

**Tradeoff:** If the window is resized, card positions are stale (they were computed at the original width). Acceptable for a personal tool — not designed for responsive resize during a session.

---

## ADR-012: transform: translateY for English slide-down, not margin-top

**Decision:** When annotations mode opens, `.english` elements slide down using `transform: translateY(Xpx)` rather than `margin-top: Xpx`.

**Reasoning:** `margin-top` affects layout flow — it pushes `.english` down but also expands the `.verse` height, which caused the flex-centered slide to re-center around the new taller content, making the Latin line visually move upward. `transform` does not affect layout flow — the browser treats the element as if it's still at its original position for layout purposes, so the Latin stays exactly where it is. Only the English visually slides down.

**Rule:** Do not change English slide-down back to margin-top. The transform approach is correct.

---

## ADR-013: All-lines mode as default

**Decision:** The page loads in all-lines mode (all slides stacked, visible on scroll), not line-by-line mode.

**Reasoning:** All-lines mode is more immediately useful for annotation work — you can see all lines, scroll freely, and open annotation cards on any line without having to navigate to it first. Line-by-line mode is an alternate reading mode for when you want the slow, contemplative one-at-a-time experience.

**Implementation:** Body starts with class `noscroll-mode`. `enterNoScroll()` is called during JS initialization. The toggle button displays "line-by-line" (showing what you'll switch to, not what you're in).
