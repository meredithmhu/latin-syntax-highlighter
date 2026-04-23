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
# HTML builders
# ─────────────────────────────────────────────────────────────────────────────

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
    .verse {{ display: flex; flex-direction: column; align-items: flex-start; }}
    .latin  {{ font-size: 2.4rem; color: #1a1a1a; letter-spacing: 0.04em; margin: 0; }}
    .english {{
      font-size: 2.4rem; color: rgba(26, 26, 26, 0.42);
      font-style: italic; margin: 20px 0 0 0;
    }}

    /* ── Hover: Latin glow ── */
    .lat-word {{ cursor: default; transition: text-shadow 0.28s ease 0.07s; }}
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
    body.mode-dark .site-title {{ color: rgba(255, 255, 255, 0.3); }}
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

  <div class="slides" id="slides">

    <div class="slide active" data-idx="0">
      <div class="title-content">
        <h1>{title}</h1>
        <div class="subtitle">{subtitle}</div>
      </div>
    </div>

{slides}
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

    const FADE_OUT = 650;   // ms — current slide fades out
    const PAUSE    = 600;   // ms — empty page
    const FADE_IN  = 3800;  // ms — next slide surfaces slowly

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
  </script>

</body>
</html>"""


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

# Navbar links — update this list when you add new poems to the site.
NAV_ITEMS = """\
          <a href="v2.html" class="nav-dropdown-item">Apuleius &mdash; Apologia, Chapter 6 (The Toothpaste Poem)</a>
          <a href="perpetua.html" class="nav-dropdown-item">Perpetua&rsquo;s Diary &mdash; Paragraphs 1 &amp; 2</a>"""


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

    all_warnings = []
    for block in blocks:
        all_warnings.extend(validate_block(block))

    # Poem slides start at data-idx=1; slide 0 is the title slide.
    slides_html = '\n\n'.join(
        build_slide(block, idx + 1, _LETTERS[idx % len(_LETTERS)])
        for idx, block in enumerate(blocks)
    )

    html = HTML.format(
        title      = title,
        subtitle   = subtitle,
        nav_items  = NAV_ITEMS,
        slides     = slides_html,
    )

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
