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

Blocks are separated by blank lines. Each block represents one line of the poem and has four parts:

```
<line number>
<latin text>
<english text>
<mappings>
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

### One Latin word that maps to multiple non-adjacent English chunks
Separate the English chunks with ` | `. Both English chunks will bold up when the Latin word is hovered:
```
Misi -> I sent, | to you,
```

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
- **Any word not covered by a mapping** will still appear in the Latin line, just without a hover group.
- **Line numbers** appear in small faded text to the left of each verse. They should match the actual line numbers in the source text.
- **The max-width of the viewer** is set automatically to fit the first English line without wrapping. Longer lines in later blocks will wrap to match that width.
