#!/usr/bin/env python3
"""
build.py — Convert a Latin poem .txt file into the styled HTML viewer.

Usage:
    python build.py poem.txt "Page Title" "Author — Source"
    python build.py poem.txt "Page Title" "Author — Source" --enrich

Flags:
  --enrich   Call the Anthropic API to fetch grammatical data for every Latin
             word, embedding it in the page. Requires the ANTHROPIC_API_KEY
             environment variable. Results are cached in <stem>_worddata.json
             so re-runs only fetch new/missing words.

Input file format (blocks separated by blank lines):
    <line_number>
    <latin line>
    <english line>
    <latin token(s)> -> <english chunk> [| <english chunk> ...]
    ...

Rules:
  - Multiple Latin tokens in one group: space-separated (e.g. "properis versibus")
  - Multiple English chunks for one Latin group: separated by " | "
    (use this when one Latin word maps to non-adjacent English words,
     e.g. "Misi -> I sent, | to you,")
  - Latin token matching ignores surrounding punctuation (commas, periods, etc.)
  - Blank lines separate blocks; extra blank lines are fine
"""

import json
import os
import re
import sys
from pathlib import Path

# One letter per slide for group IDs (a1, a2 … b1, b2 … etc.)
_LETTERS = "abcdefghijklmnopqrstuvwxyz"


# ─────────────────────────────────────────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_file(text):
    blocks = []
    for raw in re.split(r'\n{2,}', text.strip()):
        lines = [l for l in raw.strip().splitlines() if l.strip()]
        if len(lines) < 4:
            continue

        line_num = lines[0].strip()
        latin    = lines[1].strip()
        english  = lines[2].strip()

        mappings = []
        for line in lines[3:]:
            if '->' not in line:
                continue
            lat_side, eng_side = line.split('->', 1)
            lat_tokens  = lat_side.strip().split()
            eng_chunks  = [c.strip() for c in eng_side.split('|') if c.strip()]
            mappings.append({'lat': lat_tokens, 'eng': eng_chunks})

        blocks.append({
            'num':      line_num,
            'latin':    latin,
            'english':  english,
            'mappings': mappings,
        })

    return blocks


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

def _strip_punct(s):
    """Remove leading/trailing punctuation for lookup purposes."""
    return re.sub(r'^[^\w]+|[^\w]+$', '', s)


def validate_block(block):
    """Return a list of warning strings for a parsed block."""
    warnings = []
    line_num = block['num']

    latin_words  = set(_strip_punct(w) for w in block['latin'].split())
    mapped_latin = set()

    for m in block['mappings']:
        for tok in m['lat']:
            stripped = _strip_punct(tok)
            mapped_latin.add(stripped)
            if stripped not in latin_words:
                warnings.append(
                    f"  Line {line_num}: Latin token '{tok}' in mapping "
                    f"not found in Latin text"
                )
        for chunk in m['eng']:
            pos = block['english'].find(chunk)
            if pos == -1:
                pos = block['english'].lower().find(chunk.lower())
            if pos == -1:
                warnings.append(
                    f"  Line {line_num}: English chunk '{chunk}' in mapping "
                    f"not found in translation — possible character mismatch "
                    f"(apostrophes, dashes, or encoding)"
                )

    for word in block['latin'].split():
        stripped = _strip_punct(word)
        if stripped and stripped not in mapped_latin:
            warnings.append(
                f"  Line {line_num}: Latin word '{word}' has no mapping"
            )

    return warnings


# ─────────────────────────────────────────────────────────────────────────────
# LLM enrichment
# ─────────────────────────────────────────────────────────────────────────────

def fetch_word_info(word, latin_line, client):
    """Call the Anthropic API and return a dict with parse/why/paradigm/notes."""
    prompt = (
        f'Given the Latin word "{word}" in the context "{latin_line}", '
        f'return a JSON object with exactly these fields:\n\n'
        f'- "parse": dictionary form and full grammatical parse '
        f'(e.g., "vocative singular of Calpurnianus, 2nd declension masculine noun")\n'
        f'- "why": why this word takes that form in this sentence (1-2 sentences, plain text)\n'
        f'- "paradigm": the relevant paradigm as compact plain text using spaces for alignment — '
        f'just the endings or forms, not full words. For a noun show case endings; '
        f'for a verb show the conjugation pattern. Keep it under 10 lines.\n'
        f'- "notes": null\n\n'
        f'Return only valid JSON. No markdown, no code fences, no text outside the JSON object.'
    )

    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )

    raw = message.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith('```'):
        raw = re.sub(r'^```[a-z]*\n?', '', raw)
        raw = re.sub(r'\n?```$', '', raw)
    return json.loads(raw)


def enrich_blocks(blocks, input_path, client):
    """Fetch word info for every unique token in every block.

    Results are cached in <stem>_worddata.json; only missing keys are fetched.
    Returns the full word_data dict keyed by "{data_idx}_{token}".
    """
    cache_path = input_path.with_name(input_path.stem + '_worddata.json')

    word_data = {}
    if cache_path.exists():
        word_data = json.loads(cache_path.read_text(encoding='utf-8'))
        print(f"  Loaded {len(word_data)} cached entries from {cache_path.name}")

    new_entries = 0
    for idx, block in enumerate(blocks):
        data_idx   = idx + 1  # slide 0 is the title
        latin_line = block['latin']
        seen = set()
        for raw_tok in latin_line.split():
            token = _strip_punct(raw_tok)
            if not token or token in seen:
                continue
            seen.add(token)
            key = f"{data_idx}_{token}"
            if key in word_data:
                continue
            print(f"  Fetching {key} …", end=' ', flush=True)
            try:
                info = fetch_word_info(token, latin_line, client)
                word_data[key] = info
                new_entries += 1
                print("done")
            except Exception as exc:
                print(f"failed ({exc})")
                word_data[key] = {'parse': None, 'why': None, 'paradigm': None, 'notes': None}

    if new_entries:
        cache_path.write_text(json.dumps(word_data, ensure_ascii=False, indent=2), encoding='utf-8')
        print(f"  Saved {len(word_data)} entries → {cache_path.name}")

    return word_data


# ─────────────────────────────────────────────────────────────────────────────
# HTML builders
# ─────────────────────────────────────────────────────────────────────────────

def build_latin_html(latin, mappings, letter):
    token_to_group = {}
    for i, m in enumerate(mappings):
        gid = f"{letter}{i + 1}"
        for tok in m['lat']:
            token_to_group[tok]               = gid
            token_to_group[_strip_punct(tok)]  = gid

    parts = []
    for tok in latin.split():
        gid = token_to_group.get(tok) or token_to_group.get(_strip_punct(tok))
        if gid:
            parts.append(f'<span class="lat-word" data-group="{gid}">{tok}</span>')
        else:
            parts.append(f'<span class="lat-word">{tok}</span>')

    return '\n            '.join(parts)


def build_english_html(english, mappings, letter):
    placements  = []
    search_from = {}

    for i, m in enumerate(mappings):
        gid = f"{letter}{i + 1}"
        for chunk in m['eng']:
            start_from = search_from.get(chunk, 0)
            pos = english.find(chunk, start_from)
            if pos == -1:
                lower_pos = english.lower().find(chunk.lower(), start_from)
                if lower_pos != -1:
                    pos = lower_pos
            if pos != -1:
                placements.append((pos, pos + len(chunk), gid, chunk))
                search_from[chunk] = pos + len(chunk)

    placements.sort(key=lambda x: x[0])

    result = []
    cursor = 0
    for start, end, gid, chunk in placements:
        if cursor < start:
            result.append(english[cursor:start])
        result.append(f'<span class="eng-word" data-group="{gid}">{english[start:end]}</span>')
        cursor = end
    if cursor < len(english):
        result.append(english[cursor:])

    return ''.join(result)


def build_slide(block, data_idx, letter):
    """Build one poem slide. data_idx starts at 1 (slide 0 is the title)."""
    latin_html   = build_latin_html(block['latin'],   block['mappings'], letter)
    english_html = build_english_html(block['english'], block['mappings'], letter)

    return f"""\
    <div class="slide" data-idx="{data_idx}">
      <div class="verse-wrapper">
        <span class="line-num">({block['num']})</span>
        <div class="verse">
          <p class="latin">
            {latin_html}
          </p>
          <p class="english">
            {english_html}
          </p>
        </div>
      </div>
    </div>"""


# ─────────────────────────────────────────────────────────────────────────────
# HTML template
# ─────────────────────────────────────────────────────────────────────────────

HTML = """\
<!DOCTYPE html>
<html lang="la">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title}</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Caveat:wght@400;500&display=swap" rel="stylesheet">
  <style>
    html, body {{ margin: 0; height: 100%; }}

    body {{
      background:
        linear-gradient(rgba(200, 175, 148, 0.54), rgba(200, 175, 148, 0.54)),
        url('marble.jpg') center / cover no-repeat fixed;
      font-family: Georgia, "Times New Roman", serif;
    }}

    /* ── Site title ── */
    .site-title {{
      position: fixed;
      top: 14px;
      left: 0; right: 0;
      text-align: center;
      z-index: 200;
      pointer-events: none;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 1.1rem;
      letter-spacing: 0.18em;
      color: rgba(26, 26, 26, 0.55);
    }}

    /* ── Navbar ── */
    .navbar {{
      position: fixed;
      top: 0; left: 0; right: 0;
      z-index: 200;
      display: flex;
      justify-content: center;
      padding-top: 46px;
      pointer-events: none;
    }}
    .nav-item {{
      position: relative;
      display: inline-block;
      pointer-events: auto;
    }}
    .nav-label {{
      font-family: Georgia, "Times New Roman", serif;
      font-size: 18pt;
      color: #1a1a1a;
      letter-spacing: 0.04em;
      cursor: default;
      background-image: linear-gradient(currentColor, currentColor);
      background-size: 0% 1px;
      background-repeat: no-repeat;
      background-position: left bottom;
      transition: background-size 0.7s ease 0.3s;
    }}
    .nav-item:hover .nav-label {{ background-size: 100% 1px; }}
    .nav-dropdown {{
      position: absolute;
      top: 100%;
      left: 50%;
      transform: translateX(-50%);
      min-width: 360px;
      padding-top: 14px;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.35s ease 0.85s;
    }}
    .nav-dropdown-inner {{
      background: rgba(255, 255, 255, 0.08);
      backdrop-filter: blur(40px) saturate(180%);
      -webkit-backdrop-filter: blur(40px) saturate(180%);
      border: 1px solid rgba(255, 255, 255, 0.3);
      border-radius: 8px;
      padding: 6px 0;
      box-shadow:
        0 8px 32px rgba(0, 0, 0, 0.08),
        inset 0 1px 0 rgba(255, 255, 255, 0.5);
    }}
    .nav-item:hover .nav-dropdown {{ opacity: 1; pointer-events: auto; }}
    .nav-dropdown-item {{
      display: block;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 0.92rem;
      color: #1a1a1a;
      letter-spacing: 0.02em;
      text-decoration: none;
      white-space: nowrap;
      padding: 10px 22px;
      cursor: pointer;
      background-image: linear-gradient(currentColor, currentColor);
      background-size: 0% 1px;
      background-repeat: no-repeat;
      background-position: 22px bottom;
      transition: background-size 0.35s ease 0.05s;
    }}
    .nav-dropdown-item:hover {{ background-size: calc(100% - 44px) 1px; }}

    /* ── Scheme toggle ── */
    .scheme-toggle {{
      position: fixed;
      top: 36px; right: 44px;
      background: none; border: none;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 0.82rem;
      color: rgba(26, 26, 26, 0.35);
      cursor: pointer;
      letter-spacing: 0.08em;
      z-index: 100; padding: 0;
      transition: color 0.25s;
    }}
    .scheme-toggle:hover {{ color: rgba(26, 26, 26, 0.65); }}

    /* ── Mode toggle ── */
    .mode-toggle {{
      position: fixed;
      top: 62px; right: 44px;
      background: none; border: none;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 0.82rem;
      color: rgba(26, 26, 26, 0.35);
      cursor: pointer;
      letter-spacing: 0.08em;
      z-index: 100; padding: 0;
      transition: color 0.25s;
    }}
    .mode-toggle:hover {{ color: rgba(26, 26, 26, 0.65); }}

    /* ════════════════════════════════════════
       SCROLL MODE
    ════════════════════════════════════════ */
    body.scroll-mode {{ overflow: hidden; height: 100vh; }}
    body.scroll-mode .slides {{ position: absolute; inset: 0; }}
    body.scroll-mode .slide {{
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      padding-bottom: 18vh;
      opacity: 0; pointer-events: none;
      transition: opacity 0.6s ease;
    }}
    body.scroll-mode .slide.active {{
      opacity: 1; pointer-events: auto;
      transition: opacity 3.8s ease;
    }}

    /* ════════════════════════════════════════
       NO-SCROLL MODE
    ════════════════════════════════════════ */
    body.noscroll-mode {{ overflow: auto; height: auto; min-height: 100vh; }}
    body.noscroll-mode .slides {{
      position: static;
      display: flex; flex-direction: column; align-items: center;
      padding-top: 90px; padding-bottom: 120px; gap: 120px;
    }}
    body.noscroll-mode .slide {{
      position: static; width: auto; height: auto;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; pointer-events: none;
      transition: opacity 0.7s ease;
    }}
    body.noscroll-mode .slide.visible {{ opacity: 1; pointer-events: auto; }}

    /* ════════════════════════════════════════
       SHARED
    ════════════════════════════════════════ */
    h1 {{
      font-size: 3.2rem; font-weight: bold; color: #1a1a1a;
      letter-spacing: 0.01em; line-height: 1.2;
      margin: 0; text-align: center;
    }}
    .subtitle {{
      font-size: 1.1rem; color: #555;
      font-style: italic; text-align: center;
    }}
    .title-content {{
      display: flex; flex-direction: column;
      align-items: center; gap: 1.1rem;
    }}
    .verse-wrapper {{ display: flex; align-items: flex-start; gap: 0.7em; }}
    .line-num {{
      font-size: 0.85em; color: rgba(26, 26, 26, 0.45);
      padding-top: 0.18em; flex-shrink: 0; letter-spacing: 0;
    }}
    .verse {{ display: flex; flex-direction: column; align-items: flex-start; position: relative; overflow: visible; }}
    .latin  {{ font-size: 2.4rem; color: #1a1a1a; letter-spacing: 0.04em; margin: 0; }}
    .english {{
      font-size: 2.4rem; color: rgba(26, 26, 26, 0.42);
      font-style: italic; margin: 20px 0 0 0;
    }}

    /* ── Hover: Latin glow ── */
    .lat-word {{ cursor: pointer; transition: text-shadow 0.28s ease 0.07s; }}
    .lat-word.lat-active {{
      text-shadow:
        0 0  1px #fff,
        0 0  3px #fff,
        0 0  6px #fff,
        0 0 12px rgba(255, 255, 255, 0.95),
        0 0 22px rgba(255, 255, 255, 0.85),
        0 0 40px rgba(255, 255, 255, 0.6),
        0 0 65px rgba(255, 255, 255, 0.35);
    }}

    /* ── Hover: English reveal ── */
    .eng-word {{
      transition: color 0.35s ease, text-shadow 0.35s ease, background-size 0.15s ease;
      background-image: linear-gradient(rgba(26, 26, 26, 0.75), rgba(26, 26, 26, 0.75));
      background-size: 0% 1px;
      background-repeat: no-repeat;
      background-position: left bottom;
    }}
    .eng-word.eng-active {{
      transition: color 0.65s ease 0.12s, text-shadow 0.65s ease 0.12s, background-size 0.65s ease 0.12s;
      color: rgba(26, 26, 26, 0.75);
      text-shadow: 0 0 0.5px rgba(26, 26, 26, 0.7), 0 0 0.5px rgba(26, 26, 26, 0.7);
      background-size: 100% 1px;
    }}

    /* ════════════════════════════════════════
       MODE — LIGHT
    ════════════════════════════════════════ */
    body.mode-light {{
      background:
        linear-gradient(rgba(255, 248, 235, 0.2), rgba(255, 248, 235, 0.2)),
        url('marble.jpg') center / cover no-repeat fixed;
    }}
    body.mode-light .lat-word.lat-active {{
      text-shadow:
        0 0  1px rgba(178, 228, 242, 1),
        0 0  3px rgba(145, 212, 232, 1),
        0 0  5px rgba(110, 195, 218, 0.95),
        0 0  9px rgba( 78, 174, 204, 0.75),
        0 0 15px rgba( 48, 152, 188, 0.4);
    }}

    /* ════════════════════════════════════════
       MODE — DARK
    ════════════════════════════════════════ */
    body.mode-dark {{ background: #1c1a17; }}
    body.mode-dark h1                   {{ color: rgba(255, 255, 255, 0.88); }}
    body.mode-dark .subtitle            {{ color: rgba(255, 255, 255, 0.48); }}
    body.mode-dark .latin               {{ color: rgba(255, 255, 255, 0.88); }}
    body.mode-dark .english             {{ color: rgba(255, 255, 255, 0.35); }}
    body.mode-dark .line-num            {{ color: rgba(255, 255, 255, 0.28); }}
    body.mode-dark .site-title          {{ color: rgba(255, 255, 255, 0.3); }}
    body.mode-dark .eng-word {{
      background-image: linear-gradient(rgba(255, 255, 255, 0.75), rgba(255, 255, 255, 0.75));
    }}
    body.mode-dark .eng-word.eng-active {{
      color: rgba(255, 255, 255, 0.82);
      text-shadow: 0 0 0.5px rgba(255, 255, 255, 0.7), 0 0 0.5px rgba(255, 255, 255, 0.7);
    }}
    body.mode-dark .mode-toggle         {{ color: rgba(255, 255, 255, 0.3); }}
    body.mode-dark .mode-toggle:hover   {{ color: rgba(255, 255, 255, 0.6); }}
    body.mode-dark .scheme-toggle       {{ color: rgba(255, 255, 255, 0.3); }}
    body.mode-dark .scheme-toggle:hover {{ color: rgba(255, 255, 255, 0.6); }}
    body.mode-dark .nav-label           {{ color: rgba(255, 255, 255, 0.85); }}
    body.mode-dark .nav-dropdown-item   {{ color: rgba(255, 255, 255, 0.78); }}
    body.mode-dark .nav-dropdown-inner {{
      background: rgba(255, 255, 255, 0.06);
      border-color: rgba(255, 255, 255, 0.12);
    }}

    /* ════════════════════════════════════════
       WORD INFO CARD
    ════════════════════════════════════════ */
    .word-card-overlay {{
      position: fixed; inset: 0;
      z-index: 499; display: none;
    }}
    .word-card-overlay.visible {{ display: block; }}

    .word-card {{
      position: fixed;
      top: 50%; left: 50%;
      transform: translate(-50%, -50%);
      background: rgba(255, 255, 255, 0.14);
      backdrop-filter: blur(40px) saturate(180%);
      -webkit-backdrop-filter: blur(40px) saturate(180%);
      border: 1px solid rgba(255, 255, 255, 0.38);
      border-radius: 12px;
      padding: 28px 32px 24px;
      max-width: 520px; width: 90vw;
      z-index: 500;
      font-family: Georgia, "Times New Roman", serif;
      color: #1a1a1a;
      box-shadow: 0 20px 60px rgba(0, 0, 0, 0.13);
      display: none;
    }}
    .word-card.visible {{ display: block; }}

    .word-card-close {{
      position: absolute; top: 12px; right: 16px;
      background: none; border: none;
      font-size: 1.2rem;
      color: rgba(26, 26, 26, 0.35);
      cursor: pointer; padding: 0; line-height: 1;
      transition: color 0.2s;
    }}
    .word-card-close:hover {{ color: rgba(26, 26, 26, 0.65); }}

    .word-card-word {{
      font-size: 1.7rem; letter-spacing: 0.04em;
      margin-bottom: 22px; color: #1a1a1a;
    }}

    .word-card-section {{ margin-bottom: 15px; }}
    .word-card-section:last-child {{ margin-bottom: 0; }}

    .word-card-label {{
      font-size: 0.65rem; letter-spacing: 0.15em;
      color: rgba(26, 26, 26, 0.42);
      text-transform: lowercase;
      margin-bottom: 3px;
    }}

    .word-card-value {{
      font-size: 0.93rem; color: rgba(26, 26, 26, 0.82);
      line-height: 1.55;
    }}

    .word-card-paradigm {{
      font-family: "Courier New", Courier, monospace;
      font-size: 0.8rem; color: rgba(26, 26, 26, 0.68);
      line-height: 1.65; margin: 0; white-space: pre;
    }}

    body.mode-dark .word-card {{
      background: rgba(40, 36, 30, 0.85);
      border-color: rgba(255, 255, 255, 0.1);
      color: rgba(255, 255, 255, 0.88);
    }}
    body.mode-dark .word-card-close       {{ color: rgba(255, 255, 255, 0.3); }}
    body.mode-dark .word-card-close:hover {{ color: rgba(255, 255, 255, 0.65); }}
    body.mode-dark .word-card-word        {{ color: rgba(255, 255, 255, 0.9); }}
    body.mode-dark .word-card-label       {{ color: rgba(255, 255, 255, 0.35); }}
    body.mode-dark .word-card-value       {{ color: rgba(255, 255, 255, 0.75); }}
    body.mode-dark .word-card-paradigm    {{ color: rgba(255, 255, 255, 0.55); }}

    /* ════════════════════════════════════════
       ANNOTATIONS MODE
    ════════════════════════════════════════ */
    .annotations-toggle {{
      position: fixed; top: 88px; right: 44px;
      background: none; border: none;
      font-family: Georgia, "Times New Roman", serif; font-size: 0.82rem;
      color: rgba(26, 26, 26, 0.35); cursor: pointer;
      letter-spacing: 0.08em; z-index: 100; padding: 0; transition: color 0.25s;
    }}
    .annotations-toggle:hover                    {{ color: rgba(26, 26, 26, 0.65); }}
    body.annotations-mode .annotations-toggle    {{ color: rgba(26, 26, 26, 0.65); }}

    body.annotations-mode .lat-word.annotated {{
      text-decoration: underline; text-underline-offset: 5px;
      text-decoration-thickness: 1px; text-decoration-color: rgba(26, 26, 26, 0.45);
    }}
    .annotation-svg {{
      position: absolute; top: 0; left: 0;
      overflow: visible; pointer-events: none; display: none; z-index: 5;
    }}
    body.annotations-mode .annotation-svg.visible {{ display: block; }}

    .annotation-card {{
      position: absolute; z-index: 10;
      font-family: 'Caveat', cursive; font-size: 1.2rem;
      color: rgba(26, 26, 26, 0.78); line-height: 1.45;
      max-width: 320px; display: none; cursor: default;
    }}
    body.annotations-mode .annotation-card.visible {{ display: block; }}
    .ann-summary     {{ cursor: pointer; }}
    .ann-expand-hint {{ font-size: 0.9rem; color: rgba(26,26,26,0.38); margin-top: 2px; cursor: pointer; }}
    .ann-expanded    {{ display: none; margin-top: 8px; }}
    .ann-expanded.open {{ display: block; }}
    .ann-why         {{ font-size: 1.05rem; color: rgba(26,26,26,0.62); margin-bottom: 10px; line-height: 1.4; }}
    .ann-notes {{
      width: 100%; box-sizing: border-box; display: block;
      background: none; border: none; border-bottom: 1px solid rgba(26,26,26,0.16);
      font-family: 'Caveat', cursive; font-size: 1.05rem; color: rgba(26,26,26,0.7);
      resize: none; outline: none; padding: 2px 0 4px; margin-bottom: 12px;
    }}
    .ann-notes::placeholder {{ color: rgba(26,26,26,0.26); }}
    .ann-buttons {{ display: flex; gap: 8px; margin-bottom: 6px; }}
    .ann-btn {{
      background: none; border: 1px solid rgba(26,26,26,0.2); border-radius: 4px;
      font-family: 'Caveat', cursive; font-size: 1rem; color: rgba(26,26,26,0.58);
      cursor: pointer; padding: 3px 10px; transition: border-color 0.2s, color 0.2s;
    }}
    .ann-btn:hover {{ border-color: rgba(26,26,26,0.45); color: rgba(26,26,26,0.85); }}
    .ann-detail     {{ display: none; margin-top: 8px; font-size: 1rem; color: rgba(26,26,26,0.68); line-height: 1.5; }}
    .ann-detail.open {{ display: block; }}
    .ann-detail-label {{ font-size: 0.82rem; color: rgba(26,26,26,0.42); display: block; margin-bottom: 3px; }}
    .ann-detail pre {{ font-family: 'Caveat', cursive; font-size: 1rem; white-space: pre; margin: 0; }}

    body.mode-dark .annotations-toggle          {{ color: rgba(255,255,255,0.3); }}
    body.mode-dark .annotations-toggle:hover    {{ color: rgba(255,255,255,0.6); }}
    body.mode-dark.annotations-mode .annotations-toggle {{ color: rgba(255,255,255,0.6); }}
    body.mode-dark.annotations-mode .lat-word.annotated {{ text-decoration-color: rgba(255,255,255,0.4); }}
    body.mode-dark .annotation-card             {{ color: rgba(255,255,255,0.78); }}
    body.mode-dark .ann-expand-hint             {{ color: rgba(255,255,255,0.32); }}
    body.mode-dark .ann-why                     {{ color: rgba(255,255,255,0.6); }}
    body.mode-dark .ann-notes                   {{ border-bottom-color: rgba(255,255,255,0.16); color: rgba(255,255,255,0.65); }}
    body.mode-dark .ann-notes::placeholder      {{ color: rgba(255,255,255,0.24); }}
    body.mode-dark .ann-btn                     {{ border-color: rgba(255,255,255,0.2); color: rgba(255,255,255,0.55); }}
    body.mode-dark .ann-btn:hover               {{ border-color: rgba(255,255,255,0.5); color: rgba(255,255,255,0.85); }}
    body.mode-dark .ann-detail, body.mode-dark .ann-detail pre {{ color: rgba(255,255,255,0.62); }}
    body.mode-dark .ann-detail-label            {{ color: rgba(255,255,255,0.36); }}
  </style>
</head>
<body class="scroll-mode mode-mud">

  <div class="site-title">Meredith's Latin Notebook</div>

  <button class="scheme-toggle" id="scheme-toggle">mud</button>

  <nav class="navbar">
    <div class="nav-item">
      <span class="nav-label">Latin Texts</span>
      <div class="nav-dropdown">
        <div class="nav-dropdown-inner">
{nav_items}
        </div>
      </div>
    </div>
  </nav>

  <button class="mode-toggle" id="mode-toggle">no scroll</button>
  <button class="annotations-toggle" id="annotations-toggle">annotations</button>

  <!-- Annotation data: generate with python3 generate_annotations.py {input_stem}.txt -->
  <script>var annotationData = null;</script>
  <script src="{annotations_js}" onerror=""></script>

  <div class="slides" id="slides">

    <div class="slide active" data-idx="0">
      <div class="title-content">
        <h1>{title}</h1>
        <div class="subtitle">{subtitle}</div>
      </div>
    </div>

{slides}
  </div>

  <div class="word-card-overlay" id="word-card-overlay"></div>
  <div class="word-card" id="word-card">
    <button class="word-card-close" id="word-card-close">&times;</button>
    <div class="word-card-word" id="wc-word"></div>
    <div class="word-card-section">
      <div class="word-card-label">grammatical parse</div>
      <div class="word-card-value" id="wc-parse"></div>
    </div>
    <div class="word-card-section">
      <div class="word-card-label">why this form</div>
      <div class="word-card-value" id="wc-why"></div>
    </div>
    <div class="word-card-section">
      <div class="word-card-label">quick reference</div>
      <pre class="word-card-paradigm" id="wc-paradigm"></pre>
    </div>
    <div class="word-card-section">
      <div class="word-card-label">Meredith's notes</div>
      <div class="word-card-value" id="wc-notes"></div>
    </div>
  </div>

  <script>
    // ── Max-width from first poem line ────────────────────────────────────────
    window.addEventListener('load', () => {{
      const firstEng = document.querySelector('.slide[data-idx="1"] .english');
      if (firstEng) {{
        firstEng.style.display    = 'inline-block';
        firstEng.style.whiteSpace = 'nowrap';
        const w = Math.ceil(firstEng.getBoundingClientRect().width);
        firstEng.style.display    = '';
        firstEng.style.whiteSpace = '';
        document.querySelectorAll('.verse').forEach(v => {{ v.style.width = w + 'px'; }});
      }}
    }});

    // ── Hover ─────────────────────────────────────────────────────────────────
    function clearAll() {{
      document.querySelectorAll('.lat-active, .eng-active').forEach(el =>
        el.classList.remove('lat-active', 'eng-active')
      );
    }}

    document.getElementById('slides').addEventListener('mouseover', e => {{
      const word = e.target.closest('[data-group]');
      if (!word) {{ clearAll(); return; }}
      const group = word.dataset.group;
      const slide = word.closest('.slide');
      slide.querySelectorAll('.lat-word, .eng-word')
           .forEach(el => el.classList.remove('lat-active', 'eng-active'));
      slide.querySelectorAll(`.lat-word[data-group="${{group}}"]`)
           .forEach(el => el.classList.add('lat-active'));
      slide.querySelectorAll(`.eng-word[data-group="${{group}}"]`)
           .forEach(el => el.classList.add('eng-active'));
    }});

    document.getElementById('slides').addEventListener('mouseleave', clearAll);

    // ── Scroll mode navigation ────────────────────────────────────────────────
    const slides  = Array.from(document.querySelectorAll('.slide'));
    let current   = 0;
    let animating = false;
    let mode      = 'scroll';

    const FADE_OUT = 650;
    const PAUSE    = 600;
    const FADE_IN  = 3800;

    function goTo(next) {{
      if (mode !== 'scroll')                  return;
      if (next < 0 || next >= slides.length) return;
      if (next === current || animating)      return;
      animating = true;
      clearAll();
      const prev = current;
      current = next;
      slides[prev].classList.remove('active');
      setTimeout(() => {{
        setTimeout(() => {{
          slides[next].classList.add('active');
          setTimeout(() => {{ animating = false; }}, FADE_IN);
        }}, PAUSE);
      }}, FADE_OUT);
    }}

    window.addEventListener('wheel', e => {{
      if (mode !== 'scroll') return;
      e.deltaY > 0 ? goTo(current + 1) : goTo(current - 1);
    }}, {{ passive: true }});

    // ── No-scroll mode ────────────────────────────────────────────────────────
    let observer;

    function enterNoScroll() {{
      slides.forEach(s => s.classList.remove('active', 'visible'));
      document.body.classList.remove('scroll-mode');
      document.body.classList.add('noscroll-mode');
      mode = 'noscroll';
      slides[0].classList.add('visible');
      observer = new IntersectionObserver(entries => {{
        entries.forEach(e => {{ if (e.isIntersecting) e.target.classList.add('visible'); }});
      }}, {{ threshold: 0.15 }});
      slides.slice(1).forEach(s => observer.observe(s));
    }}

    function enterScroll() {{
      if (observer) {{ observer.disconnect(); observer = null; }}
      slides.forEach(s => s.classList.remove('active', 'visible'));
      document.body.classList.remove('noscroll-mode');
      document.body.classList.add('scroll-mode');
      mode = 'scroll';
      slides[current].classList.add('active');
    }}

    // ── Color scheme ──────────────────────────────────────────────────────────
    const schemes     = ['mode-light', 'mode-mud', 'mode-dark'];
    const schemeNames = ['light', 'mud', 'dark'];
    let schemeIdx = 1;
    const schemeBtn = document.getElementById('scheme-toggle');

    function applyScheme(idx) {{
      document.body.classList.remove(...schemes);
      document.body.classList.add(schemes[idx]);
      schemeBtn.textContent = schemeNames[idx];
    }}

    schemeBtn.addEventListener('click', () => {{
      schemeIdx = (schemeIdx + 1) % 3;
      applyScheme(schemeIdx);
    }});

    // ── Mode toggle ───────────────────────────────────────────────────────────
    const toggleBtn = document.getElementById('mode-toggle');
    toggleBtn.addEventListener('click', () => {{
      if (mode === 'scroll') {{ enterNoScroll(); toggleBtn.textContent = 'scroll'; }}
      else                   {{ enterScroll();   toggleBtn.textContent = 'no scroll'; }}
    }});

    // ── Word info card ────────────────────────────────────────────────────────
    __WORD_DATA__

    const card        = document.getElementById('word-card');
    const cardOverlay = document.getElementById('word-card-overlay');

    function stripPunct(s) {{
      return s.replace(/^[^a-zA-Z\u00C0-\u024F]+|[^a-zA-Z\u00C0-\u024F]+$/g, '');
    }}

    function showCard(wordEl) {{
      const slideIdx = wordEl.closest('.slide').dataset.idx;
      const token    = stripPunct(wordEl.textContent.trim());
      const key      = slideIdx + '_' + token;
      const info     = wordData[key];

      document.getElementById('wc-word').textContent     = token;
      document.getElementById('wc-parse').textContent    = info ? (info.parse     || '—') : 'No data — run build.py --enrich to populate.';
      document.getElementById('wc-why').textContent      = info ? (info.why       || '—') : '—';
      document.getElementById('wc-paradigm').textContent = info ? (info.paradigm  || '—') : '—';
      document.getElementById('wc-notes').textContent    = info ? (info.notes     || 'N/A') : 'N/A';

      card.classList.add('visible');
      cardOverlay.classList.add('visible');
    }}

    function hideCard() {{
      card.classList.remove('visible');
      cardOverlay.classList.remove('visible');
    }}

    document.getElementById('word-card-close').addEventListener('click', hideCard);
    cardOverlay.addEventListener('click', hideCard);
    document.addEventListener('keydown', e => {{ if (e.key === 'Escape') hideCard(); }});

    document.getElementById('slides').addEventListener('click', e => {{
      const word = e.target.closest('.lat-word');
      if (!word) return;
      if (annotationsMode) {{ showAnnotation(word); }} else {{ showCard(word); }}
    }});

    // ── Annotations mode ──────────────────────────────────────────────────────
    var annotationsMode      = false;
    var activeAnnotationWord = null;

    document.querySelectorAll('.verse').forEach(function(verse) {{
      var svgEl = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svgEl.classList.add('annotation-svg');
      verse.appendChild(svgEl);

      var cardEl = document.createElement('div');
      cardEl.className = 'annotation-card';
      cardEl.innerHTML =
        '<div class="ann-summary"></div>' +
        '<div class="ann-expand-hint">\u2193 expand</div>' +
        '<div class="ann-expanded">' +
          '<div class="ann-why"></div>' +
          '<textarea class="ann-notes" rows="2" placeholder="your notes\u2026"></textarea>' +
          '<div class="ann-buttons">' +
            '<button class="ann-btn" data-action="gloss">Dictionary gloss</button>' +
            '<button class="ann-btn" data-action="drill">Drill this form</button>' +
          '</div>' +
          '<div class="ann-detail"></div>' +
        '</div>';
      verse.appendChild(cardEl);

      function toggleExpand() {{
        var exp  = cardEl.querySelector('.ann-expanded');
        var hint = cardEl.querySelector('.ann-expand-hint');
        var opening = !exp.classList.contains('open');
        exp.classList.toggle('open', opening);
        hint.style.display = opening ? 'none' : '';
        adjustEnglishMargin(verse);
      }}
      cardEl.querySelector('.ann-summary').addEventListener('click', toggleExpand);
      cardEl.querySelector('.ann-expand-hint').addEventListener('click', toggleExpand);

      cardEl.querySelector('.ann-buttons').addEventListener('click', function(e) {{
        var btn = e.target.closest('.ann-btn');
        if (!btn) return;
        var action = btn.dataset.action;
        var detail = cardEl.querySelector('.ann-detail');
        var info   = annotationData && cardEl.dataset.wordKey
          ? (annotationData.words || {{}})[cardEl.dataset.wordKey] : null;
        if (detail.classList.contains('open') && detail.dataset.showing === action) {{
          detail.classList.remove('open');
        }} else {{
          if (action === 'gloss') {{
            detail.innerHTML = info && info.gloss
              ? '<span class="ann-detail-label">dictionary entry</span>' + info.gloss
              : '<em>no data loaded</em>';
          }} else {{
            detail.innerHTML = info && info.paradigm
              ? '<span class="ann-detail-label">' + (info.paradigm_label || 'paradigm') + '</span>' +
                '<pre>' + info.paradigm + '</pre>'
              : '<em>no data loaded</em>';
          }}
          detail.dataset.showing = action;
          detail.classList.add('open');
        }}
        adjustEnglishMargin(verse);
      }});

      cardEl.querySelector('.ann-notes').addEventListener('input', function(e) {{
        if (cardEl.dataset.wordKey) {{
          localStorage.setItem('ann_notes_' + cardEl.dataset.wordKey, e.target.value);
        }}
      }});
    }});

    function adjustEnglishMargin(verse) {{
      var cardEl  = verse.querySelector('.annotation-card');
      var english = verse.querySelector('.english');
      if (!english || !cardEl || !cardEl.classList.contains('visible')) return;
      var latinH  = verse.querySelector('.latin').offsetHeight;
      english.style.marginTop = Math.max(24, latinH + cardEl.offsetHeight + 28) + 'px';
      if (activeAnnotationWord && activeAnnotationWord.closest('.verse') === verse) {{
        redrawLine(activeAnnotationWord, cardEl, verse);
      }}
    }}

    function redrawLine(wordEl, cardEl, verse) {{
      var svgEl     = verse.querySelector('.annotation-svg');
      var verseRect = verse.getBoundingClientRect();
      var wordRect  = wordEl.getBoundingClientRect();
      var cardRect  = cardEl.getBoundingClientRect();
      var x1 = (wordRect.left + wordRect.width / 2 - verseRect.left).toFixed(1);
      var y1 = (wordRect.bottom - verseRect.top).toFixed(1);
      var x2 = (cardRect.left + 10 - verseRect.left).toFixed(1);
      var y2 = (cardRect.top - verseRect.top).toFixed(1);
      var dark  = document.body.classList.contains('mode-dark');
      var color = dark ? 'rgba(255,255,255,0.22)' : 'rgba(26,26,26,0.28)';
      svgEl.setAttribute('width',  verse.offsetWidth + 'px');
      svgEl.setAttribute('height', (verse.offsetHeight + cardEl.offsetHeight + 60) + 'px');
      svgEl.innerHTML = '<line x1="' + x1 + '" y1="' + y1 + '" x2="' + x2 + '" y2="' + y2 + '"' +
        ' stroke="' + color + '" stroke-width="1.2" stroke-dasharray="4,3"/>';
      svgEl.classList.add('visible');
    }}

    function showAnnotation(wordEl) {{
      document.querySelectorAll('.lat-word.annotated').forEach(function(w) {{ w.classList.remove('annotated'); }});
      document.querySelectorAll('.annotation-card').forEach(function(c) {{
        c.classList.remove('visible');
        c.querySelector('.ann-expanded').classList.remove('open');
        c.querySelector('.ann-expand-hint').style.display = '';
        c.querySelector('.ann-detail').classList.remove('open');
      }});
      document.querySelectorAll('.annotation-svg').forEach(function(s) {{ s.innerHTML = ''; s.classList.remove('visible'); }});
      document.querySelectorAll('.verse .english').forEach(function(e) {{ e.style.marginTop = ''; }});

      wordEl.classList.add('annotated');
      activeAnnotationWord = wordEl;

      var verse    = wordEl.closest('.verse');
      var slideIdx = wordEl.closest('.slide').dataset.idx;
      var token    = stripPunct(wordEl.textContent.trim());
      var key      = slideIdx + '_' + token;
      var info     = annotationData && annotationData.words ? annotationData.words[key] : null;

      var cardEl = verse.querySelector('.annotation-card');
      cardEl.dataset.wordKey = key;
      cardEl.querySelector('.ann-summary').textContent =
        info && info.summary ? info.summary : token + ' \u2014 run generate_annotations.py to load data';
      cardEl.querySelector('.ann-why').textContent = info && info.why ? info.why : '';
      cardEl.querySelector('.ann-notes').value =
        localStorage.getItem('ann_notes_' + key) || (info && info.notes) || '';

      var verseRect = verse.getBoundingClientRect();
      var wordRect  = wordEl.getBoundingClientRect();
      var latinH    = verse.querySelector('.latin').offsetHeight;
      var rawLeft   = wordRect.left - verseRect.left;
      cardEl.style.left = Math.max(0, Math.min(rawLeft, verseRect.width - 320)) + 'px';
      cardEl.style.top  = (latinH + 20) + 'px';

      cardEl.classList.add('visible');
      adjustEnglishMargin(verse);
      requestAnimationFrame(function() {{ redrawLine(wordEl, cardEl, verse); }});
    }}

    function hideAnnotations() {{
      document.querySelectorAll('.lat-word.annotated').forEach(function(w) {{ w.classList.remove('annotated'); }});
      document.querySelectorAll('.annotation-card').forEach(function(c) {{
        c.classList.remove('visible');
        c.querySelector('.ann-expanded').classList.remove('open');
        c.querySelector('.ann-expand-hint').style.display = '';
        c.querySelector('.ann-detail').classList.remove('open');
      }});
      document.querySelectorAll('.annotation-svg').forEach(function(s) {{ s.innerHTML = ''; s.classList.remove('visible'); }});
      document.querySelectorAll('.verse .english').forEach(function(e) {{ e.style.marginTop = ''; }});
      activeAnnotationWord = null;
    }}

    var annToggleBtn = document.getElementById('annotations-toggle');
    annToggleBtn.addEventListener('click', function() {{
      annotationsMode = !annotationsMode;
      document.body.classList.toggle('annotations-mode', annotationsMode);
      annToggleBtn.textContent = annotationsMode ? 'close annotations' : 'annotations';
      if (!annotationsMode) hideAnnotations();
    }});
  </script>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

# Navbar links — update when you add new poems to the site.
NAV_ITEMS = """\
          <a href="v2.html" class="nav-dropdown-item">Apuleius &mdash; Apologia, Chapter 6 (The Toothpaste Poem)</a>
          <a href="perpetua.html" class="nav-dropdown-item">Perpetua&rsquo;s Diary &mdash; Paragraphs 1 &amp; 2</a>"""


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    flags = [a for a in sys.argv[1:] if a.startswith('--')]

    if not args:
        print(__doc__)
        sys.exit(1)

    input_path = Path(args[0])
    title      = args[1] if len(args) > 1 else input_path.stem
    subtitle   = args[2] if len(args) > 2 else ''

    text   = input_path.read_text(encoding='utf-8')
    blocks = parse_file(text)

    if not blocks:
        print("No blocks parsed. Check your input file format.")
        sys.exit(1)

    all_warnings = []
    for block in blocks:
        all_warnings.extend(validate_block(block))

    # ── Enrichment ────────────────────────────────────────────────────────────
    if '--enrich' in flags:
        try:
            import anthropic
        except ImportError:
            print("Error: 'anthropic' package required. Install with: pip install anthropic")
            sys.exit(1)
        api_key = os.environ.get('ANTHROPIC_API_KEY')
        if not api_key:
            print("Error: ANTHROPIC_API_KEY environment variable not set.")
            sys.exit(1)
        print("Enriching word data…")
        client    = anthropic.Anthropic(api_key=api_key)
        word_data = enrich_blocks(blocks, input_path, client)
        word_data_js = 'const wordData = ' + json.dumps(word_data, ensure_ascii=False) + ';'
    else:
        word_data_js = 'const wordData = {};'

    # ── Build HTML ────────────────────────────────────────────────────────────
    slides_html = '\n\n'.join(
        build_slide(block, idx + 1, _LETTERS[idx % len(_LETTERS)])
        for idx, block in enumerate(blocks)
    )

    html = HTML.format(
        title           = title,
        subtitle        = subtitle,
        nav_items       = NAV_ITEMS,
        slides          = slides_html,
        input_stem      = input_path.stem,
        annotations_js  = input_path.stem + '_annotations.js',
    )
    html = html.replace('__WORD_DATA__', word_data_js)

    output_path = input_path.with_suffix('.html')
    output_path.write_text(html, encoding='utf-8')
    print(f"Done → {output_path}  ({len(blocks)} line{'s' if len(blocks) != 1 else ''})")

    if all_warnings:
        print(f"\nWarnings ({len(all_warnings)}):")
        for w in all_warnings:
            print(w)
        print()


if __name__ == '__main__':
    main()
