# Roadmap

## Done

- [x] Hover glow on Latin words with corresponding English highlight
- [x] Word mapping groups (multiple Latin → shared English chunk, non-adjacent chunks)
- [x] Three-phase slide fade transition (650ms out / 600ms pause / 3800ms in)
- [x] All-lines mode (default) — continuous vertical layout, IntersectionObserver fade-in
- [x] Line-by-line mode — one slide at a time, ← / → arrow buttons at bottom-right
- [x] Three color schemes: mud (default), light, dark
- [x] Site title "Meredith's Latin Notebook" above navbar
- [x] Frosted-glass navbar with "Latin Texts" dropdown
- [x] `build.py` — generates full HTML from `.txt` source
- [x] CLI warning system in `build.py` (unmapped words, missing targets, duplicate groups)
- [x] `--enrich` flag in `build.py` for Anthropic API word enrichment
- [x] Word info cards (click in default mode) — gloss, summary, paradigm drill
- [x] `generate_annotations.py` — standalone script for annotation data (caching, JSON + JS output)
- [x] Annotations mode toggle — smooth English slide-down via `transform: translateY`, Latin stays fixed
- [x] Static map architecture — all card positions and SVG lines pre-computed once in `buildVerseLayouts()`
- [x] Multiple simultaneous annotation cards — any number of cards can be open at once
- [x] Per-word card toggle — clicking a word again closes only that card; mode stays open
- [x] Caveat (handwriting) font for annotation cards
- [x] Expand/collapse panels in annotation cards (summary → expand → gloss + drill)
- [x] `localStorage` persistence for annotation notes (`ann_notes_{slideIdx}_{token}`)
- [x] `constructions: []` reserved in annotation JSON for future multi-word support
- [x] USAGE.md — full input format documentation
- [x] README.md — project description and quick-start
- [x] Project documentation (docs/ directory)
- [x] `PHRASES:` field in `.txt` input format — pipe/comma-delimited phrase groups parsed by `build.py` into `phraseData` JS variable embedded in generated HTML

## In progress / known issues

- [ ] **toothpaste.txt typos** — two known issues in the source text, not yet fixed:
  - Line 8: apostrophe encoding mismatch ("yesterday's")
  - Line 11: `omino` should be `omnino`
  - After fixing: rebuild with `python3 build.py toothpaste.txt "The Toothpaste Poem" "Apuleius — Apologia, Chapter 6"`
- [ ] **build.py not updated** — `build.py`'s HTML template has not been updated to match the current state of `toothpaste.html`. The two are out of sync. Any page built by `build.py` will not have the current annotations mode, navigation mode, or layout. This needs a full sync pass before adding a new poem.
- [ ] **perpetua.html** — currently a placeholder navbar shell. Needs actual poem content once Perpetua's Diary text is ready.

## Next up (likely)

- [ ] Sync `build.py` template with the current `toothpaste.html` — this is the most important outstanding task before adding any new poem.
- [ ] Fix typos in `toothpaste.txt`, rebuild and regenerate.
- [ ] Write actual `perpetua.html` content (Paragraphs 1 & 2 of Perpetua's Diary).

## Future / speculative

- [ ] **Multi-word constructions** — the `constructions: []` array in annotation JSON is reserved for ablative absolutes, purpose clauses, indirect statements, etc. Would require new UI (highlight spanning multiple words, construction card type).
- [ ] Chinese poetry support (mentioned in README as a long-term goal).
- [ ] Print/export view — a clean layout for printing annotations.
- [ ] Annotation sharing — export notes as a readable summary.
- [ ] More poems added to the notebook.
