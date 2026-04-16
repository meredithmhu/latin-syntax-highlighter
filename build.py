#!/usr/bin/env python3
"""
build.py — Convert a Latin poem .txt file into the styled HTML viewer.

Usage:
    python build.py poem.txt "Page Title" "Author — Source"

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
            lat_tokens  = lat_side.strip().split()          # e.g. ["properis", "versibus"]
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
# HTML builders
# ─────────────────────────────────────────────────────────────────────────────

def _strip_punct(s):
    """Remove leading/trailing punctuation for lookup purposes."""
    return re.sub(r'^[^\w]+|[^\w]+$', '', s)


def build_latin_html(latin, mappings, letter):
    # Map each raw Latin token (and its de-punctuated form) → group id
    token_to_group = {}
    for i, m in enumerate(mappings):
        gid = f"{letter}{i + 1}"
        for tok in m['lat']:
            token_to_group[tok]              = gid
            token_to_group[_strip_punct(tok)] = gid

    parts = []
    for tok in latin.split():
        gid = token_to_group.get(tok) or token_to_group.get(_strip_punct(tok))
        if gid:
            parts.append(f'<span class="lat-word" data-group="{gid}">{tok}</span>')
        else:
            # No mapping — still wrap so spacing is consistent
            parts.append(f'<span class="lat-word">{tok}</span>')

    return '\n            '.join(parts)


def build_english_html(english, mappings, letter):
    # Collect (start, end, group_id, chunk) for every chunk in the English string
    placements = []
    search_from = {}  # track search offset per chunk to handle duplicates in order

    for i, m in enumerate(mappings):
        gid = f"{letter}{i + 1}"
        for chunk in m['eng']:
            start_from = search_from.get(chunk, 0)
            pos = english.find(chunk, start_from)
            if pos == -1:
                # Try case-insensitive as a fallback
                lower_pos = english.lower().find(chunk.lower(), start_from)
                if lower_pos != -1:
                    pos = lower_pos
            if pos != -1:
                placements.append((pos, pos + len(chunk), gid, chunk))
                search_from[chunk] = pos + len(chunk)

    placements.sort(key=lambda x: x[0])

    # Walk through the English string, wrapping matched chunks in spans
    result = []
    cursor = 0
    for start, end, gid, chunk in placements:
        if cursor < start:
            result.append(english[cursor:start])  # unmatched text between chunks
        result.append(f'<span class="eng-word" data-group="{gid}">{english[start:end]}</span>')
        cursor = end
    if cursor < len(english):
        result.append(english[cursor:])

    return ''.join(result)


def build_slide(block, idx, letter):
    latin_html   = build_latin_html(block['latin'],   block['mappings'], letter)
    english_html = build_english_html(block['english'], block['mappings'], letter)
    active = ' active' if idx == 0 else ''

    return f"""\
    <div class="slide{active}" data-idx="{idx}">
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
  <style>
    html, body {{ margin: 0; height: 100%; }}

    body {{
      background: #e8dcc8;
      font-family: Georgia, "Times New Roman", serif;
    }}

    .mode-toggle {{
      position: fixed;
      top: 36px; right: 44px;
      background: none; border: none;
      font-family: Georgia, "Times New Roman", serif;
      font-size: 0.82rem;
      color: rgba(26,26,26,0.35);
      cursor: pointer;
      letter-spacing: 0.08em;
      z-index: 100; padding: 0;
      transition: color 0.25s;
    }}
    .mode-toggle:hover {{ color: rgba(26,26,26,0.65); }}

    /* ── Scroll mode ── */
    body.scroll-mode {{ overflow: hidden; height: 100vh; }}
    body.scroll-mode h1 {{
      position: absolute; top: 52px; left: 50%;
      transform: translateX(-50%);
      white-space: nowrap; pointer-events: none;
    }}
    body.scroll-mode .subtitle {{
      position: absolute; top: 130px; left: 50%;
      transform: translateX(-50%);
      white-space: nowrap; pointer-events: none;
    }}
    body.scroll-mode .slides {{ position: absolute; inset: 0; }}
    body.scroll-mode .slide {{
      position: absolute; inset: 0;
      display: flex; align-items: center; justify-content: center;
      opacity: 0; pointer-events: none;
      transition: opacity 0.55s ease;
    }}
    body.scroll-mode .slide.active {{ opacity: 1; pointer-events: auto; }}

    /* ── No-scroll mode ── */
    body.noscroll-mode {{ overflow: auto; height: auto; min-height: 100vh; }}
    body.noscroll-mode h1 {{
      position: static; transform: none; white-space: normal;
      padding-top: 72px; margin-bottom: 12px;
    }}
    body.noscroll-mode .subtitle {{
      position: static; transform: none; white-space: normal; margin-bottom: 0;
    }}
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

    /* ── Shared ── */
    h1 {{
      font-size: 3.2rem; font-weight: bold; color: #1a1a1a;
      letter-spacing: 0.01em; line-height: 1.2;
      margin: 0; text-align: center; z-index: 10;
    }}
    .subtitle {{
      font-size: 1.1rem; color: #555;
      font-style: italic; text-align: center; z-index: 10;
    }}
    .verse-wrapper {{ display: flex; align-items: flex-start; gap: 0.7em; }}
    .line-num {{
      font-size: 0.85em; color: rgba(26,26,26,0.45);
      padding-top: 0.18em; flex-shrink: 0; letter-spacing: 0;
    }}
    .verse {{ display: flex; flex-direction: column; align-items: flex-start; }}
    .latin  {{ font-size: 1.6rem; color: #1a1a1a; letter-spacing: 0.04em; margin: 0; }}
    .english {{
      font-size: 1.6rem; color: rgba(26,26,26,0.42);
      font-style: italic; margin: 20px 0 0 0;
    }}

    /* ── Hover: Latin glow ── */
    .lat-word {{ cursor: default; transition: text-shadow 0.28s ease 0.07s; }}
    .lat-word.lat-active {{
      text-shadow:
        0 0  1px #fff, 0 0  3px #fff, 0 0  6px #fff,
        0 0 12px rgba(255,255,255,0.95), 0 0 22px rgba(255,255,255,0.85),
        0 0 40px rgba(255,255,255,0.6),  0 0 65px rgba(255,255,255,0.35);
    }}

    /* ── Hover: English reveal ── */
    .eng-word {{ transition: text-shadow 0.65s ease 0.12s, color 0.65s ease 0.12s; }}
    .eng-word.eng-active {{
      color: rgba(26,26,26,0.75);
      text-shadow: 0 0 0.5px rgba(26,26,26,0.7), 0 0 0.5px rgba(26,26,26,0.7);
    }}
  </style>
</head>
<body class="scroll-mode">

  <h1>{title}</h1>
  <div class="subtitle">{subtitle}</div>
  <button class="mode-toggle" id="mode-toggle">no scroll</button>

  <div class="slides" id="slides">
{slides}
  </div>

  <script>
    // ── Max-width from first English line ─────────────────────────────────────
    window.addEventListener('load', () => {{
      const firstEng = document.querySelector('.slide[data-idx="0"] .english');
      firstEng.style.display    = 'inline-block';
      firstEng.style.whiteSpace = 'nowrap';
      const w = Math.ceil(firstEng.getBoundingClientRect().width);
      firstEng.style.display    = '';
      firstEng.style.whiteSpace = '';
      document.querySelectorAll('.verse').forEach(v => {{ v.style.maxWidth = w + 'px'; }});
    }});

    // ── Hover ─────────────────────────────────────────────────────────────────
    document.getElementById('slides').addEventListener('mouseover', e => {{
      const word = e.target.closest('[data-group]');
      if (!word) return;
      const group = word.dataset.group;
      const slide = word.closest('.slide');
      slide.querySelectorAll('.lat-word, .eng-word')
           .forEach(el => el.classList.remove('lat-active', 'eng-active'));
      slide.querySelectorAll(`.lat-word[data-group="${{group}}"]`)
           .forEach(el => el.classList.add('lat-active'));
      slide.querySelectorAll(`.eng-word[data-group="${{group}}"]`)
           .forEach(el => el.classList.add('eng-active'));
    }});
    document.getElementById('slides').addEventListener('mouseleave', () => {{
      document.querySelectorAll('.lat-active, .eng-active')
              .forEach(el => el.classList.remove('lat-active', 'eng-active'));
    }});

    // ── Scroll navigation ─────────────────────────────────────────────────────
    const slides  = Array.from(document.querySelectorAll('.slide'));
    let current   = 0;
    let animating = false;
    let mode      = 'scroll';

    function goTo(next) {{
      if (mode !== 'scroll' || next < 0 || next >= slides.length) return;
      if (next === current || animating) return;
      animating = true;
      slides[current].classList.remove('active');
      slides[next].classList.add('active');
      current = next;
      setTimeout(() => {{ animating = false; }}, 600);
    }}

    window.addEventListener('wheel', e => {{
      if (mode !== 'scroll') return;
      e.deltaY > 0 ? goTo(current + 1) : goTo(current - 1);
    }}, {{ passive: true }});

    // ── No-scroll mode ────────────────────────────────────────────────────────
    let observer;

    function enterNoScroll() {{
      slides.forEach(s => s.classList.remove('active', 'visible'));
      document.body.classList.replace('scroll-mode', 'noscroll-mode');
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
      document.body.classList.replace('noscroll-mode', 'scroll-mode');
      mode = 'scroll';
      slides[current].classList.add('active');
    }}

    const btn = document.getElementById('mode-toggle');
    btn.addEventListener('click', () => {{
      if (mode === 'scroll') {{ enterNoScroll(); btn.textContent = 'scroll'; }}
      else                   {{ enterScroll();   btn.textContent = 'no scroll'; }}
    }});
  </script>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    title    = sys.argv[2] if len(sys.argv) > 2 else input_path.stem
    subtitle = sys.argv[3] if len(sys.argv) > 3 else ""

    text   = input_path.read_text(encoding='utf-8')
    blocks = parse_file(text)

    if not blocks:
        print("No blocks parsed. Check your input file format.")
        sys.exit(1)

    slides_html = '\n\n'.join(
        build_slide(block, idx, _LETTERS[idx % len(_LETTERS)])
        for idx, block in enumerate(blocks)
    )

    html = HTML.format(
        title    = title,
        subtitle = subtitle,
        slides   = slides_html,
    )

    output_path = input_path.with_suffix('.html')
    output_path.write_text(html, encoding='utf-8')
    print(f"Done → {output_path}  ({len(blocks)} line{'s' if len(blocks) != 1 else ''})")


if __name__ == '__main__':
    main()
