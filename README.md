# latin-syntax-highlighter
A Latin syntax highlighter I'm building with the help of Claude Code. See README for a more detailed description. You can follow the traces of my thoughts in glowing, incandescent Latin and English as if you were me.

## Basic Description
I've always wanted to make an interactive webpage that displays the Latin translations I do. There's so much more to a Latin translation than the literal translation of the line. For example, Latin is known as an "inflected" language in language studies. This means that some of the grammar forms for words in Latin can contain a lot of meaning by themselves, based on their endings. For example, let's look at the verb amo, which is the verb for love in Latin.

Just plain "amo" would be "I love". "Amas" would be "you love". That's just people who love in the present tense. Fun fact, "amans" is the favored word used in Latin love poetry to mean "lover", as opposed to the noun "amator/ amatrix" (lover) because "amans" is the present participle of this verb. So, according to Latin, a lover is a person they prefer expressing as the act of loving itself rather than a person who loves you. That is very meaningful and all of Latin is full of great pockets of meaning like that. 

My syntax highlighter will be designed to show you details about each word in a Latin line of poetry as you mouse over each word. I want the text to glow as you mouse over the words, the corresponding English word in my translation to glow, and a pop-up to appear for the option to expand for even more grammatical insights. I can't wait to share the magic of Latin with you. For years, every time I've explain one of my translations to someone, I've wished that I had a tool like this, to support and illustrate what I'm trying to explain and give the person a visual demo to cling onto so they don't zone out in my explanation. I also honestly want to get people to translate a line of Latin on their own right away - once you know a couple of rules, you can get started right away, and it should be accessible anyway - it's some great writing. Future versions hopefully will support Chinese poetry, and maybe even other languages beyond that - who knows? 

---

## What the pages look like

The viewer is built around a single aesthetic: a marbled parchment background with a frosted-glass navbar at the top, presenting each line of poetry one at a time.

**Hover interaction** — hovering over any Latin word causes it to glow and simultaneously reveals its corresponding English translation below. The English word brightens and gets a slow left-to-right underline. Multiple Latin words can share a group (they all glow together), and one Latin word can map to non-adjacent English chunks (both light up at once). Moving off a word fades everything back out.

**Slide-by-slide scroll mode (default)** — the poem is presented one line at a time, like turning pages. Scrolling fades the current line out (0.65s), leaves the page empty for a breath (0.6s), then lets the next line surface very slowly (3.8s). The first slide is always a title card.

**No-scroll mode** — a button in the top-right corner switches to a continuous scrolling layout where all lines are stacked vertically and fade in as they enter the viewport.

**Three color schemes** — a second button cycles between:
- *mud* (default) — marble background with a warm beige overlay; white glow on hover
- *light* — marble with a lighter, more translucent overlay; cyan-blue glow on hover
- *dark* — soft near-black background; white glow on hover, all text shifted to light values

---

## Current pages

- **v2.html** — Apuleius, *Apologia* Chapter 6 (the Toothpaste Poem, lines 3–11)
- **perpetua.html** — placeholder for Perpetua's Diary

---

## Adding a new poem

Poems are authored in a plain `.txt` format and built into HTML with `build.py`.

See **[USAGE.md](USAGE.md)** for the full input format, mapping syntax, and how the CLI warning system works.

Quick start:
```bash
python3 build.py mypoem.txt "My Poem Title" "Author — Source"
```

This generates `mypoem.html` in the same directory. Drop `marble.jpg` in the same folder (it's shared by all pages) and open in any browser. When you're ready to add the new page to the site's navbar, update the `NAV_ITEMS` constant near the bottom of `build.py`.