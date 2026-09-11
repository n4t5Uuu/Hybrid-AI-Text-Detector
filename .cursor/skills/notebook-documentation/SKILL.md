---
name: notebook-documentation
description: >-
  Add plain-language comments, docstrings, and notebook markdown for .ipynb and .py
  pipelines — what each step does and how it connects, without heavy ML jargon. Use
  when the user asks to document, comment, or annotate notebooks, scripts, or thesis code.
disable-model-invocation: true
---

# Pipeline documentation (notebooks + Python)

Use this when editing **`.ipynb`** or **`.py`** files the user asked you to document. Goal: the next reader sees **what each piece does** and **how it plugs into what came before and what runs after** — without template voice or path spam.

## Voice

- Write like you're walking someone through the code once, then leaving.
- Short sentences. One idea per comment or docstring paragraph.
- **We** / **this function** / **this cell** are fine; don't force corporate tone.
- Concrete verbs: "pull", "fit", "stack", "hold out" — not "leverage", "utilize", "comprehensive".
- Boring setup (imports, constants): one line or skip. Spend words on logic, contracts, and handoffs.

## Keep it plain (not too technical)

Comments are for teammates on the thesis, not a methods paper. **Say what happens in everyday words.**

- Prefer: "glue spaCy and ELECTRA columns", "same essay order", "only learn word lists from train essays", "free GPU memory before the next model".
- Avoid unless the user asked for precision: *forward pass*, *memmap*, *stratified*, *caller*, *vocabulary leakage*, *inference*, *CLS token*, *discriminator*, *idx\_\**, *GridSearchCV* in prose (the code can still use those APIs).
- Thesis symbols (**S**, **E**, **H**, **R**) are fine when the reader already knows the chapter — pair them with a plain phrase once ("**S** = spaCy stats per essay").
- No stack traces of implementation detail ("NER/lemmatizer disabled", "float32", "refit inside GridSearchCV") in docstrings unless it changes what someone should do.
- If a non-technical friend would squint, rewrite the sentence.

## What to explain

**Everywhere (notebook or script)**

- What this **block or function** is for in this pipeline — not a full tutorial on the library.
- **Connection**: who calls it, what it returns, what must already be true (row order, train-only fit, GPU freed).
- **Why** when it's not obvious (leakage, empty text, shape alignment).

**Notebooks — markdown between cells**

- Plain-language purpose of the section.
- What it **feeds** next (same row order, same split indices, etc.).
- Flags the reader might flip and what breaks if they skip an earlier cell.

**Notebooks — comments in code cells**

- Comment the **steps in the cell** (load → extract → save, split → train loop), not every line.
- Prefer short comments above each logical block. Heavy detail stays in `.py`; don't repeat full docstrings from imports.

**Python scripts / modules**

- **Module** (top of file, if missing): one short block — what this file is for and which notebook or step imports it. No directory tree.
- **Public functions**: docstring with purpose, inputs/outputs in plain words, and one line on **who uses the result** (e.g. "late_fusion stacks this with E").
- **Inside the function body**: comment the **steps of the logic**, not the syntax. A reader should follow what the code is doing without reading every line.
  - Use a short comment before each **meaningful chunk** (setup, loop, transform, save, guard clause) — usually 2–6 comments per non-trivial function, not 2–6 per line.
  - Group related lines under one comment ("count word types and rare words", "pull off test rows first, then split train vs val").
  - Skip comments on obvious one-liners (`return x`, `import`, simple assignments).
  - Docstring = what/why for the whole function; inline comments = how this block moves the data forward.
- **Private helpers**: comment only if the name isn't enough.
- **Section breaks** in long files: `# --- split / train ---` plus one line if the next chunk depends on the previous.

Do **not** comment every line. Enough that someone can skim comments top-to-bottom and understand the function.

## How pieces connect (thread the story)

For pipelines (notebook cells or a chain of functions):

1. Load / validate inputs.
2. Extract or transform (each branch: what artifact it produces).
3. Merge or align (row order, keys, dtypes).
4. Split or train (what must not see test/val when fitting).
5. Save or evaluate (what downstream reuses).

In a notebook, a short bullet list in markdown is enough. In a `.py` file, say the handoff in the docstring of the function that **produces** the artifact the next step needs.

Example tone (adapt to real names):

```markdown
## Stylometric features (spaCy)

Each essay becomes a fixed-length **S** vector. We keep labels alongside so the parquet
still lines up with the combined table. ELECTRA in the next step must see the **same**
texts in the **same** order — don't shuffle between steps.
```

```python
def fuse_spacy_electra(spacy_matrix, electra_matrix, spacy_feature_names):
    """
    Stick spaCy and ELECTRA numbers into one row per essay (**H**).

    Same number of rows in both inputs — same essay order as when you extracted.
    """
    if spacy_matrix.shape[0] != electra_matrix.shape[0]:
        raise ValueError("S and E must have the same number of essays")

    # Side by side: spaCy columns, then ELECTRA columns.
    hybrid = np.hstack([spacy_matrix, electra_matrix])
    ...
```

```python
# Word list comes from train essays only; we still score every essay for the TF-IDF baseline.
vectorizer = fit_tfidf_on_train(train_texts)
R = transform_tfidf(vectorizer, texts)
```

## Sounds human — sounds AI

| Prefer | Avoid |
|--------|--------|
| "Run GPU checks before the long extract." | "This section performs comprehensive GPU validation." |
| "Late fusion concatenates S and E per row." | "We leverage late fusion to synergize multimodal representations." |
| "Fit the scaler on train only so val/test don't leak in." | "Ensures robust generalization via best practices." |
| "Empty text → zero vector so rows still line up." | "Handles edge cases robustly via zero-padding semantics." |
| "Same essay order as spaCy." | "Caller must ensure aligned row indices across modalities." |
| One reason tied to *this* code | Generic filler with no link to the pipeline |

## Paths and names — don't litter the file

- **Do not** paste absolute paths, repo trees, or `src/utils/...` in markdown or docstrings **unless** the user asked or one relative path is required to run the thing.
- **Do not** repeat where files live in every section. Say it once at setup (notebook) or in the writer function's docstring when relevant.
- In code, prefer existing variables (`FEATURES_DIR`) over repeating the string in a comment above.
- Model IDs and package names are fine when the reader must install or load them.

## Notebooks (structure)

- Opening: title + a few sentences on the experiment — not a chapter outline.
- Before big cells: optional `##` + 1–3 sentences linking to the previous step.
- No emoji. No "In this section we will explore…". No dependency laundry lists unless requested.

## Python scripts (structure)

- Match the **existing style** in the file (Google vs short one-liners).
- Docstrings on public API; **plus** sparse inline comments inside longer functions (see above).
- If the notebook imports from this module, the module docstring can mention "used from feature extraction" without path dumps.
- `assert` messages: readable ("S and E row counts must match") not cryptic.

## When editing

1. Read call order: notebook top-to-bottom, or importers + callees for `.py`.
2. Add or refresh **connections**, not line-by-line narration.
3. Trim AI-ish prose (path dumps, "robust", "seamlessly", duplicate overviews).
4. Documentation-only diff unless the user asked for behavior changes.

## Quick checklist

- [ ] Each major stage/function says what it outputs and what consumes it next.
- [ ] Train-only fit / no leakage called out where it matters.
- [ ] No gratuitous paths in markdown or docstrings.
- [ ] Reads like a lab mate, not a README generator.
- [ ] A non-ML reader could follow it without a glossary.
- [ ] Non-trivial functions have enough inline comments to show the step-by-step logic.
