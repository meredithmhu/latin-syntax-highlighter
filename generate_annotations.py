#!/usr/bin/env python3
"""
generate_annotations.py — Fetch grammatical annotation data for a Latin poem.

Usage:
    python3 generate_annotations.py poem.txt

Writes:
  poem_annotations.json   human-readable data; edit the "notes" fields here
  poem_annotations.js     loaded by the browser at runtime

Requires:
  pip install anthropic
  ANTHROPIC_API_KEY environment variable

Re-running is safe — only missing words are fetched (results are cached).

JSON structure
--------------
{
  "meta": { "source": "...", "generated": "..." },
  "words": {
    "{slide_idx}_{token}": {
      "token":          "Calpurniane",
      "slide_idx":      1,
      "summary":        "vocative singular of 2nd declension masculine noun Calpurnianus",
      "why":            "vocative because he is being directly addressed",
      "gloss":          "Calpurnianus, -i, m.",
      "paradigm_label": "2nd declension masculine noun endings",
      "paradigm":       "     Sg    Pl\\nNom  -us   -i\\n...",
      "notes":          ""   <-- edit this to add personal notes
    },
    ...
  },
  "constructions": []   <-- reserved for future multi-word annotations
}
"""

import json
import os
import re
import sys
from datetime import date
from pathlib import Path


def _strip_punct(s):
    return re.sub(r'^[^\w]+|[^\w]+$', '', s)


def parse_blocks(text):
    blocks = []
    for raw in re.split(r'\n{2,}', text.strip()):
        lines = [l for l in raw.strip().splitlines() if l.strip()]
        if len(lines) < 3:
            continue
        blocks.append({'num': lines[0].strip(), 'latin': lines[1].strip()})
    return blocks


def fetch_annotation(word, latin_line, client):
    prompt = (
        f'Given the Latin word "{word}" in the context "{latin_line}", '
        f'return a JSON object with exactly these fields:\n\n'
        f'- "summary": one concise sentence giving the grammatical form, '
        f'e.g. "vocative singular of 2nd declension masculine noun Calpurnianus"\n'
        f'- "why": 1-2 sentences explaining why this word takes that form in this sentence\n'
        f'- "gloss": the dictionary entry, '
        f'e.g. "Calpurnianus, -i, m." or "salutem, -are, -avi, -atum"\n'
        f'- "paradigm_label": a short label, '
        f'e.g. "2nd declension masculine endings" or "1st conjugation present active"\n'
        f'- "paradigm": the relevant paradigm as compact plain text with space alignment. '
        f'Endings only (not full words). Under 10 lines.\n'
        f'- "notes": ""\n\n'
        f'Return only valid JSON. No markdown fences, no text outside the JSON object.'
    )

    message = client.messages.create(
        model='claude-haiku-4-5-20251001',
        max_tokens=1024,
        messages=[{'role': 'user', 'content': prompt}],
    )

    raw = message.content[0].text.strip()
    raw = re.sub(r'^```[a-z]*\n?', '', raw)
    raw = re.sub(r'\n?```$', '', raw)
    return json.loads(raw)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    input_path = Path(sys.argv[1])
    text       = input_path.read_text(encoding='utf-8')
    blocks     = parse_blocks(text)

    if not blocks:
        print("No blocks parsed — check your input file format.")
        sys.exit(1)

    try:
        import anthropic
    except ImportError:
        print("Error: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        print("Error: ANTHROPIC_API_KEY environment variable not set.")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    json_path = input_path.with_name(input_path.stem + '_annotations.json')
    js_path   = input_path.with_name(input_path.stem + '_annotations.js')

    # Load cache
    data = {
        'meta':          {'source': input_path.name, 'generated': str(date.today())},
        'words':         {},
        'constructions': [],   # reserved — multi-word constructions go here later
    }
    if json_path.exists():
        saved            = json.loads(json_path.read_text(encoding='utf-8'))
        data['words']         = saved.get('words', {})
        data['constructions'] = saved.get('constructions', [])
        print(f"Loaded {len(data['words'])} cached entries from {json_path.name}")

    # Fetch missing words
    new_count = 0
    for idx, block in enumerate(blocks):
        data_idx   = idx + 1   # slide 0 is always the title slide
        latin_line = block['latin']
        seen = set()
        for raw_tok in latin_line.split():
            token = _strip_punct(raw_tok)
            if not token or token in seen:
                continue
            seen.add(token)
            key = f"{data_idx}_{token}"
            if key in data['words']:
                continue
            print(f"  {key} …", end=' ', flush=True)
            try:
                info              = fetch_annotation(token, latin_line, client)
                info['token']     = token
                info['slide_idx'] = data_idx
                info.setdefault('notes', '')
                data['words'][key] = info
                new_count += 1
                print("done")
            except Exception as exc:
                print(f"failed ({exc})")
                data['words'][key] = {
                    'token': token, 'slide_idx': data_idx,
                    'summary': None, 'why': None,
                    'gloss': None, 'paradigm_label': None,
                    'paradigm': None, 'notes': '',
                }

    data['meta']['generated'] = str(date.today())

    # Write JSON (human-readable; edit "notes" fields here)
    json_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8'
    )
    print(f"\nSaved {len(data['words'])} words ({new_count} new) → {json_path}")

    # Write JS (loaded by the browser via <script src="...">)
    js_path.write_text(
        '// Auto-generated by generate_annotations.py\n'
        f'// Edit notes in {json_path.name}, then re-run to regenerate this file.\n'
        f'var annotationData = {json.dumps(data, ensure_ascii=False)};\n',
        encoding='utf-8',
    )
    print(f"Saved → {js_path}")
    print(f"\nNow open v2.html in your browser — annotation cards will be populated.")


if __name__ == '__main__':
    main()
