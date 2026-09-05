---
name: code-documentation
description: >-
  Write plain, human-readable code comments and docstrings that walk the reader
  through what the code does. Use when the user asks to comment code, document
  functions, improve readability, add docstrings, or explain code for teammates.
disable-model-invocation: true
---

# Code Documentation

Write comments like a teammate showing someone the code for the first time — clear, warm, and practical. The reader should understand **what happens** and **why it matters** without needing regex jargon or framework trivia.

**Read [examples.md](examples.md) before commenting a file** — it has before/after pairs for this repo.

## Voice

- Use plain English. Say "we skip this row" not "this branch short-circuits the iteration."
- Talk about outcomes: "This turns `(Smith, 2020)` into a citation tag."
- Prefer short sentences. One idea per comment line.
- Sound like a walkthrough: "First we…", "Then we…", "If the text is empty, we move on."
- Match the project's existing tone in the file you're editing.

## What to comment

| Comment this | Skip this |
|--------------|-----------|
| Non-obvious steps (regex intent, pipeline order, filter rules) | Obvious assignments (`i += 1`, `return text`) |
| Why a check exists ("so currency like `$19.5` isn't treated as math") | Restating the line below (`# increment counter`) |
| Function purpose and return value in docstrings | Every parameter when names are already clear |
| Tricky edge cases the code handles | Imports, boilerplate, or self-explanatory loops |
| Section breaks in long functions | Code the user didn't ask you to touch |

When in doubt: if deleting the comment would confuse the next reader, keep it.

## What not to do

- No walls of text. A docstring over ~6 lines usually needs trimming.
- No implementation lectures (`# uses negative lookahead with atomic grouping`).
- No stale comments. If you change behavior, update or remove the comment.
- No comment-only drive-by refactors. Comment what the user asked for.
- No emoji in comments.

## Docstrings (Python)

Use triple-quoted docstrings on public functions and classes. Keep them conversational:

```python
def clean_citations(text):
    """
    Swap in-text and parenthetical citations for [[CITATION]] tags.

    Handles author-date forms like (Smith, 2020), narrative cites like
    Smith (2020), and numbered refs like [1-3]. Returns the cleaned string.
    """
```

For dataset helpers, mention inputs, outputs, and one line on filtering:

```python
def clean_bawe_dataset(bawe_csv_path, processed_dir, sample_size=None, ...):
    """
    Clean BAWE essays and save them to processed_dir.

    Loads the raw CSV, runs clean_pipeline on each row, drops rows that are
    too dense with placeholders or in a foreign language, then writes the
    result. sample_size limits rows per subject when set.
    """
```

Skip Args/Returns blocks unless the function has many parameters or non-obvious return shapes.

## Inline comments

Place comments **above** the block they describe, not on every line.

**Section header** (long functions):

```python
# Turn bracketed refs like [1] or [1-3] into citation tags.
text = re.sub(...)
```

**Explain the why** (one line):

```python
# Initials are optional — BAWE uses both "Smith, 2020" and "Green, E. et al (2000)".
```

**Edge case**:

```python
# Leave "volume of water" alone; only match "Vol 1" / "Volume 2" style labels.
```

## Workflow

When the user asks you to comment code:

1. Read the full function or file first. Match existing comment style.
2. Add or refresh the **module docstring** if the file lacks a one-line purpose.
3. Add **function docstrings** for public entry points missing them.
4. Add **inline comments** only at decision points, regex passes, or filters — not on every line.
5. Remove comments that repeat the code or are now wrong.
6. Touch only files the user asked for (or code you changed in the same task).

## Quick checklist

Before finishing:

- [ ] A new reader could follow the main path without opening other files
- [ ] Comments explain *what* and *why*, not *how the syntax works*
- [ ] No comment restates the code literally
- [ ] Docstrings say what goes in and what comes out
- [ ] Tone sounds like a person demonstrating the code, not a spec sheet

## Additional resources

- Before/after comment examples: [examples.md](examples.md)
- Project rule of thumb (don't over-comment): `AGENTS.md` section 2
