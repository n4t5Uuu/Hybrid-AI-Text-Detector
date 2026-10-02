# Comment examples

Before/after pairs for this repo's style. Prefer the **After** column.

## Function docstrings

**Before (too dry / technical)**

```python
def placeholder_density(text):
    """
    Computes ratio of placeholder tag characters to total string length.
    Returns float in [0, 1].
    """
```

**After (human walkthrough)**

```python
def placeholder_density(text):
    """
    Check how much of the text is placeholder tags vs real words.

    Returns a number from 0 to 1. Higher means more [[EQUATION]] / [[CODE]]
    noise — we use this to drop rows that aren't useful prose.
    """
```

---

**Before (too vague)**

```python
def clean_pipeline(text):
    """Runs cleaning."""
```

**After**

```python
def clean_pipeline(text):
    """
    Run the full cleaning pass on one piece of text.

    Strips URLs, code, math, citations, and other non-prose bits, replacing
    them with tags like [[EQUATION]]. Same pipeline for BAWE, MGTBench, and Claude.
    """
```

## Inline comments

**Before (restates the code)**

```python
# Replace with citation tag
text = re.sub(pattern, ' [[CITATION]] ', text)
```

**After (explains the situation)**

```python
# BAWE essays use messy Harvard cites — colon pages, "see also", missing commas.
text = re.sub(pattern, ' [[CITATION]] ', text)
```

---

**Before (jargon)**

```python
# Negative lookahead prevents matching volume-of-water false positives
text = re.sub(r'(?<![\w-])(?:Vol\.?s?\.?|Volume|volume)\s+(?!of\s)\d+', ...)
```

**After (plain language)**

```python
# Match "Vol 1" / "Volume 2" but not phrases like "volume of water".
text = re.sub(r'(?<![\w-])(?:Vol\.?s?\.?|Volume|volume)\s+(?!of\s)\d+', ...)
```

---

**Before (over-commented loop)**

```python
for _, row in df_raw.iterrows():  # loop over rows
    raw_text = str(row['text'])   # get text column
    if not raw_text:              # if empty
        dropped_empty += 1        # increment counter
        continue                  # skip row
```

**After (comment only the policy)**

```python
for _, row in df_raw.iterrows():
    raw_text = str(row['text']).strip() if pd.notna(row['text']) else ''
    if not raw_text:
        dropped_empty += 1
        continue
```

## Section headers in long functions

Use sparingly to orient the reader:

```python
def clean_citations(text):
    ...

    # --- Numeric refs: [1], [1, 2], [1-3] ---
    text = re.sub(...)

    # --- Author-date in parentheses: (Smith, 2020), multi-cite with semicolons ---
    text = re.sub(...)

    # --- Narrative cites: Smith (2020), Smith and Jones (2020) ---
    text = re.sub(...)
```

## Comments to leave out

These add noise — delete or never write them:

```python
# Import pandas
import pandas as pd

# Define function
def ingest_bawe_dataset(...):

# Return dataframe
return df
```

## Notebook cells

For Jupyter, one markdown cell above a complex cell is enough. In code cells, one short comment at the top:

```python
# Clean the full BAWE corpus (sample_size=None). Expect ~2000 rows after filtering.
df_cleaned_bawe = clean_bawe_dataset(bawe_path, PROCESSED_HUMAN_DIR, sample_size=None)
```
