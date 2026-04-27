# Using build.py

`build.py` converts a plain text file of an annotated Latin poem into the interactive HTML viewer.

---

## Running it

```bash
python build.py <input.txt> "<Page Title>" "<Author — Source>"
```

**Example:**
```bash
python build.py toothpaste.txt "The Toothpaste Poem" "Apuleius — Apologia, Chapter 6"
```

This writes a file called `toothpaste.html` in the same directory as the input. Open it in any browser.

---

## Input file format

Blocks are separated by blank lines. Each block represents one line of the poem and has four parts (plus an optional fifth):

```
<line number>
<latin text>
<english text>
<mappings>
PHRASES: <optional phrase group declaration>
```

### Example block

```
3
Calpurniane, salve properis versibus.
Greetings, Calpurnius with these swift verses.
Calpurniane -> Calpurnius
salve -> Greetings,
properis versibus -> with these swift verses.
```

---

## Writing mappings

Each mapping line follows the pattern:

```
Latin token(s) -> English chunk(s)
```

### One Latin word, one English chunk
The simple case:
```
nitelas -> Whitening agents
```

### Multiple Latin words that share one English chunk
Put all the Latin words space-separated on the left. They will glow together on hover:
```
properis versibus -> with these swift verses.
Arabicis frugibus -> Arabic plants.
```

The Latin tokens don't have to be adjacent in the line. If `Misi` appears at position 1 and `dentium` appears at position 4, you can still group them:
```
Misi dentium -> I sent teeth
```
Both words will highlight together when either is hovered.

### One Latin word that maps to multiple non-adjacent English chunks
Separate the English chunks with ` | `. Both English chunks will light up when the Latin word is hovered:
```
Misi -> I sent, | to you,
```

---

## Phrase groups (optional)

A block can have an optional `PHRASES:` line (anywhere after the English line) that marks syntactic phrase groups within the Latin line:

```
PHRASES: quaeso | quid habent isti versus | re aut verbo pudendum | quid omnino quod philosophus | suum nolit videri
```

**Format rules:**
- Both `|` (pipe) and `,` (comma) separate phrase groups. Use whichever reads naturally.
- Words are written as they appear in the Latin line; leading/trailing punctuation is stripped automatically.
- Groups are listed in left-to-right order across the Latin line.
- The `PHRASES:` field is **optional** — lines without it behave exactly as before.

This produces a `phraseData` variable in the generated HTML (keyed by slide index):
```json
{
  "9": [["quaeso"], ["quid", "habent", "isti", "versus"], ["re", "aut", "verbo", "pudendum"],
        ["quid", "omnino", "quod", "philosophus"], ["suum", "nolit", "videri"]]
}
```

The phrase data is embedded in the page for use by the annotation reflow layout.

---

## Reserved characters

Two character sequences have special meaning in mapping lines and cannot appear literally in mapping text:

| Sequence | Meaning |
|----------|---------|
| `->` | Separates Latin tokens from English chunks |
| ` \| ` (space-pipe-space) | Separates multiple English chunks |

Everything else is safe. Slashes (`/`), colons (`:`), em-dashes (`—`), parentheses, brackets — all fine on either side of the arrow. If your English chunk contains a pipe character, write it differently (e.g., spell out "or" instead).

---

## What happens to unmapped Latin words

Any Latin word not covered by a mapping will still appear in the line. It just won't have a hover group — hovering over it does nothing. This is intentional: function words, connectives, or anything you'd rather not annotate can be left out of the mappings entirely.

---

## CLI warnings

After a successful build, `build.py` prints any issues it noticed about your mappings. For example:

```
Done → toothpaste.html  (9 lines)

Warnings (2):
  Line 7: Latin word 'quod' has no mapping
  Line 9: English chunk 'yesterday's leftovers' in mapping not found in translation — possible character mismatch (apostrophes, dashes, or encoding)
```

The build still completes — warnings don't block output. There are three kinds:

**Latin token not found in Latin text**
A word you wrote on the left side of `->` doesn't appear in that line's Latin. Usually a typo or you copied from the wrong line.
```
  Line 5: Latin token 'nitela' in mapping not found in Latin text
```

**English chunk not found in translation**
The text on the right side of `->` doesn't appear in that line's English. Common causes:
- Typo in the mapping
- Curly apostrophe in the English line (`'`) but straight apostrophe in the mapping (`'`), or vice versa — these look identical but aren't the same character
- Em-dash (`—`) in the English line but hyphen-minus (`-`) in the mapping

**Latin word has no mapping**
A word appears in the Latin line but isn't covered by any mapping. This is just a reminder — it's not necessarily an error if you intentionally left that word out.

---

## Apostrophes and special characters

The most common invisible mismatch is the apostrophe. If your English line contains a curly/smart apostrophe (`'`, Unicode U+2019) and your mapping line uses a straight apostrophe (`'`, ASCII 0x27), the English chunk lookup will silently fail, and the word won't be linked. The CLI warning will flag this:

```
  Line 8: English chunk "yesterday's leftovers" in mapping not found in translation — possible character mismatch (apostrophes, dashes, or encoding)
```

The fix: make sure the apostrophe in the mapping line exactly matches the one in the English text. Copy-paste from the English line directly into the mapping if you're unsure.

The same applies to dashes: `—` (em-dash, U+2014), `–` (en-dash, U+2013), and `-` (hyphen-minus, ASCII 0x2D) are all different characters.

---

## Full example

This is `toothpaste.txt`, which ships with the project:

```
3
Calpurniane, salve properis versibus.
Greetings, Calpurnius with these swift verses.
Calpurniane -> Calpurnius
salve -> Greetings,
properis versibus -> with these swift verses.

4
Misi, ut petisti, munditias dentium
I sent, as you asked, to you, the cleaning supplies for your teeth.
Misi -> I sent, | to you,
ut petisti -> as you asked,
munditias -> the cleaning supplies
dentium -> for your teeth.

5
nitelas oris ex Arabicis frugibus
Whitening agents of the mouth — from Arabic plants.
nitelas -> Whitening agents
oris -> of the mouth
ex -> from
Arabicis frugibus -> Arabic plants.
```

---

## Things to keep in mind

- **Punctuation is handled automatically.** You can write `Calpurniane` in a mapping even though the Latin line has `Calpurniane,` — the script strips surrounding punctuation when matching.
- **Blank lines separate blocks.** Extra blank lines between blocks are fine; blank lines within a block will break parsing.
- **Mapping direction is always Latin → English.** The left side of `->` must be Latin tokens; the right side must be English text. Reversed mappings will produce broken or missing links.
- **Any word not covered by a mapping** will still appear in the Latin line, just without a hover group.
- **Line numbers** appear in small faded text to the left of each verse. They should match the actual line numbers in the source text.
- **The max-width of the viewer** is set automatically to fit the first English line without wrapping. Longer lines in later blocks will wrap to match that width.
- **`marble.jpg` must be in the same folder** as the generated HTML file. The background image is referenced by filename only.
- **A title slide is always generated first** (slide 0) showing the page title and subtitle. Poem verses start at slide 1.
- **The navbar links are hardcoded** in `build.py` in the `NAV_ITEMS` constant near the bottom of the file. When you add a new poem to the site, update that constant to include the new link — otherwise all generated pages will have a stale navbar.
