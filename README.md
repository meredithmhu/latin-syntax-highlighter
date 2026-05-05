# Meredith's Latin Notebook

An interactive viewer for Latin translations, built with plain HTML/CSS/JS. Each poem lives on its own page, presented against a marble background, and lets you explore the Latin word by word.

---

## What the pages look like

Every poem page shares the same aesthetic: a marble parchment background with a warm beige overlay, a frosted-glass navbar fixed at the top, and the poem presented in large, unhurried text.

**Hover interaction** — hover over any Latin word and it glows with a soft text-shadow. Simultaneously, the corresponding English word or phrase below brightens and receives a slow left-to-right underline. Multiple Latin words can share a group (hovering any one lights up all of them), and one Latin word can map to non-adjacent English chunks (both light up at once). Moving off a word fades everything back out.

**Line-by-line mode (default)** — the poem is presented one line at a time, navigated with `←` / `→` arrow buttons at the bottom-right of the screen. Transitioning between lines uses a three-phase fade: 0.65s fade-out, a 0.6s breath of empty page, then a slow 3.8s fade-in. The first slide is always a title card with the poem name and source.

**All-lines mode** — a toggle button in the top-right switches to a continuous scrolling layout where all lines are stacked vertically and fade in as they enter the viewport.

**Three color schemes** — a second button cycles between:
- *mud* (default) — marble with a warm beige overlay; white glow on hover
- *light* — marble with a lighter translucent overlay; cyan-blue glow on hover
- *dark* — near-black background; white glow; all text shifted to light values

---

## Annotations mode

Each poem page has an **annotations** toggle button. Clicking it enters a margin-annotation view inspired by handwritten notes in a manuscript.

In annotations mode, the English translation slides down to make room. Clicking any Latin word opens a floating annotation card written in a handwriting font (Caveat), showing:
- A one-sentence grammatical summary of the word's form
- An expand arrow (pointing left or right depending on which side has space) — clicking it reveals the full detail panel to the side of the card:
  - Why this particular form appears in context
  - A personal notes textarea (saved to `localStorage`)
  - Two buttons: **Dictionary gloss** and **Drill this form**, each opening a further panel that stacks beside the card
- Clicking the Latin word again closes that card; all other open cards stay open

Any number of cards can be open simultaneously. When one card's detail panel is expanded, sibling cards on the same line dim to keep focus.

For lines with syntactic phrase groupings defined in the source text, annotations mode also reflows the line into phrase-group rows — each phrase of Latin sits above its corresponding English, making the structure of the sentence visually explicit.

Annotation data (summaries, glosses, paradigms) is generated separately via `generate_annotations.py`, which calls the Anthropic API once per word and caches results.

---

## Current pages

- **toothpaste.html** — Apuleius, *Apologia* Chapter 6 (the Toothpaste Poem, lines 3–11). Fully annotated.
- **perpetua.html** — Perpetua's Diary, Paragraphs 1 & 2. Placeholder — content coming soon.
- **build_your_own.html** — Upload your own `.txt` file and get back a formatted HTML page in the same style.
- **tutorial.html** — Tutorial page. Coming soon.

---

## Build your own

You can generate a page for any Latin text you have a translation for. Write a `.txt` source file following the format in [USAGE.md](USAGE.md), then either:

**Use the web interface** — go to the Build Your Own page in the navbar, upload your `.txt` file, fill in a title and author/source, and download the generated HTML.

**Use the CLI directly:**
```bash
python3 build.py mypoem.txt "My Poem Title" "Author — Source"
```

This generates `mypoem.html` in the same directory. Drop `marble.jpg` in the same folder (shared by all pages) and open in any browser.

To also generate annotation data:
```bash
python3 generate_annotations.py mypoem.txt
```
Requires `ANTHROPIC_API_KEY` in the environment and `pip install anthropic`. Only missing words are fetched on re-runs (cached in `mypoem_annotations.json`).

---

## Adding a new poem to the site

1. Write `newpoem.txt` in the input format (see USAGE.md).
2. Run `python3 build.py newpoem.txt "Title" "Author — Source"`.
3. Optionally run `python3 generate_annotations.py newpoem.txt` for annotation data.
4. Update `NAV_ITEMS` in `build.py` and rebuild existing pages so their navbars include the new link.
5. Add the new page to the navbar in `template.html` for future pages.

---

## Running locally

```bash
npm install
npm start
```

Opens at `http://localhost:3000`. The Express server serves all static files and handles the `/api/build` endpoint used by the Build Your Own page.
