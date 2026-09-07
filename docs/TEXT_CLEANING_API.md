# Text Cleaning Functions Reference

**Package:** `src/utils/cleaning/`

- `cleaning_methods.py` — regex cleaners, filters, `clean_pipeline`, constants
- `placeholder_density.py` — row density filters
- `dataset_cleaning.py` — `clean_claude_dataset`, `clean_mgtbench_ai_dataset`, `clean_gemini_dataset`, `clean_bawe_dataset`, `ingest_bawe_dataset`

Import from `utils.cleaning`.

Quick reference for all the cleaning functions we use in the project. Everything here replaces noise with placeholder tags like `[[EQUATION]]`, `[[CODE]]`, etc.

---

## Math Cleaning Functions

### `clean_math_texts(text)`
Removes LaTeX and mathematical notation → `[[EQUATION]]`

Cleans: LaTeX environments, `$$math$$`, `$inline$` (math only, not `$word$` or currency spans), `\[\]`, integrals, `(mv)/dt`, `b = -5`, comparisons, Greek letters

### `clean_bare_expressions(text)`  
Catches leftover math that `clean_math_texts()` missed

Cleans: Factorials `n!`, fractions `1/2`, parenthesized expressions `(x+y)`

### `clean_residual_math_noise(text)`
Final pass for Unicode math symbols

Cleans: `α β Σ ∞`, `f(x)`, `|x|`, `√x`, `²³`, `[[EQUATION]]²`, `±`, subscripts like `xn+1`

---

## Code Cleaning Functions

### `clean_code_texts(text)`
Removes markdown code blocks → `[[CODE]]`

Cleans: `` ```code``` ``, `` `inline` ``

### `clean_pseudocode_and_diagrams(text)`
Catches non-markdown code

Cleans: `[Start] -> [End]`, `[Car] |-- [Dashboard]`, `class Foo {}`, `object.method()`, Python/JS keywords

---

## Other Cleaning Functions

### `clean_complexity_notation(text)` → `[[COMPLEXITY]]`
Cleans: `O(n)`, `O(log n)`, `Θ(n)`, `Ω(n²)`

### `clean_citations(text)` → `[[CITATION]]`
Cleans numeric refs (`[1]`, `[1-3]`), parenthetical author-date (`(Smith, 2020)`, `(pederson, 2002: 303; see also Hargeaves, 1994)`, `(Smith & Jones, 2020)`, `(Jones, 1990, cited in Smith, 2000)`), narrative/inverted forms (`Smith et al (2000)`, `Green, E. et al (2000)`, `Pilkingtonm, H. (2007)`), edited-volume secondary (`Jones C & Baker G in Lewis J (ed) 1994`), conservative MLA author-page (`(Nietzsche 9)`), and numbered volume markers (`Vol 1`, `Volume 2`, `vol. 12, no. 3`). Strips leftover page markers (`p.139`, `pp.200`, `p135`, `2000: 572`). Skips `(Figure 1)`, `(Table 2)`, `(see below)`, and prose like `volume of water`.

### `clean_url(text)` → `[[URL]]`
Cleans: `https://...`, `www....`

### `clean_music_notation(text)` → `[[MUSIC]]`
Cleans: `C-G-D-A`, `F#-Bb-D`

### `clean_list_numbering(text)`
Removes: `1.`, `a)` / `b.` after start/newline/colon (not after `a + b. Step`), `i.`, `- bullet`

### `clean_markdown_formatting(text)`
Strips Gemini-style markdown to plain text (call before `clean_pipeline`; not in global pipeline)

Cleans: line headings `## Title`, `### Section ###`, `## Title ##`; bold `**text**`; line-start `* ` bullets; single-word `_italic_`

Example: `## Car-Free Cities` → `Car-Free Cities`; `**Environmental Benefits:**` → `Environmental Benefits:`

### `strip_surrogate_characters(text)`
Removes UTF-16 surrogate code points that break UTF-8 CSV writes. Called automatically at the end of `clean_pipeline()`. Dataset savers also sanitize all string columns before write.

### `strip_reference_list(text)`
Cuts off everything after "References:" or "Bibliography:"

### `merge_continuous_equations(text, tag='[[EQUATION]]')`
Merges adjacent placeholders separated by operators, short math, trig names, or (for CODE) `return`/`returns`  
Example: `[[EQUATION]] + [[EQUATION]]` → `[[EQUATION]]`  
Example: `[[CODE]] returns [[CODE]]` → `[[CODE]]`

### `mop_up_leftover_math_and_code(text)`
Last-pass fold for leftovers next to tags: trig, `dΦ/dt`, both sides of `=`, `±`, `2a`/`4ac`/`x + c`, named quantities (`Mass (m) = 1,500 kg`), `(xn, yn, zn)`, unit products, `[[CODE]] [[EQUATION]] [[CODE]]` sandwiches, leftover LaTeX shells (`$h([[CODE]])$`, `$h([[CODE]] _Z)$`, `∠ABC`, `+ bx + c`, `{d+c}`, stacked `^_{j}`, `U_i`, `$(2IJS)$`), plus common paper families (`\frac`, `\sqrt`, `\left/\right`, environments, `\label/\eqref`, kets/bras). Array reads `dp[i][j]` are handled earlier in `clean_pseudocode_and_diagrams`. Underscores whose middle is not a word/name (`_Z`, `S_{1}`) become `[[EQUATION]]`; italic titles (`_Pamela_`, `_this_`) stay. Currency `$25,000` stays.

### `clean_code_assignments(text)`
Code-only numeric assignments like `num = -1, condition false` next to `[[CODE]]` or Iteration/condition keywords

---

## Filter Functions

### `is_academic_content(prompt="", text="")`
Returns `False` if text is creative/non-academic

Filters out: poems, stories, scripts, ads, letters, stage directions, vivid/sensory creative prompts, roleplay, original-fiction anime/scenes, sports-drill prompts, compose-a-symphony tasks (matched on **prompt only**)

### `contains_foreign_language(text)`
Returns `True` if text has non-English content

Detects: Chinese/Japanese/Korean/Arabic/Cyrillic scripts, French/Spanish sentences  
Ignores: Common loanwords like "café", "résumé"

---

## Density Functions

### `placeholder_density(text)`
Returns ratio of placeholders to total tokens (0.0 to 1.0)

We usually drop rows with density ≥ 0.4

### `placeholder_density_windowed(text, window_chars=150, threshold=0.5)`
Returns `True` if any 150-char window has >50% placeholders

Catches equation-heavy clusters that whole-document density misses

---

## Main Pipeline

### `clean_pipeline(text)`
**USE THIS ONE** - runs all cleaners in the right order

Order:
1. URLs → code/diagrams → markdown code → code assignments → music → complexity
2. References → citations → list markers
3. Math (3 passes: bare → full → residual)
4. Merge adjacent tags
5. Mop-up leftover math/code fragments, then merge again
6. `strip_surrogate_characters()` (final pass)

Example:
```python
from utils.cleaning import clean_pipeline

text = "The paper (Smith, 2020) shows $E=mc^2$ with O(n) complexity."
cleaned = clean_pipeline(text)
# "The paper [[CITATION]] shows [[EQUATION]] with [[COMPLEXITY]] complexity."
```

---

## Dataset Functions

### `extract_claude_prompt_and_response(text)`
Parses Claude's ShareGPT conversation format  
Returns: `(prompt, response)` tuple

### `clean_claude_dataset(claude_csv_path, processed_dir, sample_size=None, density_threshold=0.4, drop_foreign_rows=True)`
Full pipeline for Claude dataset:
1. Loads CSV
2. Filters non-academic content
3. Filters foreign language (optional)
4. Runs `clean_pipeline()` on responses
5. Filters by density (whole + windowed)
6. Saves cleaned CSV with summary stats

Use in notebook:
```python
claude_dataset = RAW_AI_DIR / 'claude_dataset.csv'
df = clean_claude_dataset(claude_dataset, PROCESSED_AI_DIR, sample_size=None)
```

### `preprocess_mgtbench_text(text)`
Removed — MGTBench uses `clean_pipeline()` directly (newline flattening is handled inside the shared pipeline).

### `clean_mgtbench_ai_dataset(mgtbench_csv_path, processed_dir, sample_size=None, density_threshold=0.4, drop_foreign_rows=True)`
Full pipeline for MGTBench AI (`id`, `text`, `file`) — mirrors `clean_claude_dataset`:
1. Loads CSV
2. Filters foreign language on raw text (optional)
3. Runs `clean_pipeline()` on each row
4. Drops empty rows and rows failing `placeholder_density()` / `placeholder_density_windowed()`
5. Saves one combined `mgtbench_ai_dataset_cleaned.csv` (or `mgtbench_ai_dataset_cleaned_{N}.csv` when `sample_size=N`) with columns `id`, `text`, `file`, and `subject` (derived from `file`). Per-subject `*_mgtbench.csv` files are not written.

Use in notebook:
```python
mgtbench_ai_path = RAW_AI_DIR / 'mgtbench_ai_dataset.csv'
df = clean_mgtbench_ai_dataset(mgtbench_ai_path, PROCESSED_AI_DIR, sample_size=None)
```

### `clean_gemini_dataset(gemini_csv_path, processed_dir, sample_size=None, density_threshold=0.4, drop_foreign_rows=True)`
Full pipeline for Gemini essays (`text`, `label`, `prompt_name`, `source`, `RDizzl3_seven`):
1. Loads CSV
2. Filters foreign language on raw text (optional)
3. Runs `clean_markdown_formatting()` then `clean_pipeline()` on each row
4. Drops empty rows and rows failing `placeholder_density()` / `placeholder_density_windowed()`
5. Saves `gemini_essays_v1_cleaned.csv` (or `gemini_essays_v1_cleaned_{N}.csv` when `sample_size=N`)

Use in notebook:
```python
gemini_path = RAW_AI_DIR / 'gemini_essays_v1.csv'
df = clean_gemini_dataset(gemini_path, PROCESSED_AI_DIR, sample_size=None)
```

### `ingest_bawe_dataset(corpus_dir, output_path)`
Parses BAWE TEI XML under `CORPUS_ByDisc` and writes one raw CSV (`id`, `text`, `file`, `subject`, `course`). Used in `data_ingestion.ipynb` after downloading/extracting the BAWE zip.

Use in notebook:
```python
bawe_corpus_dir = RAW_HUMAN_DIR / 'bawe' / 'download' / 'CORPUS_ByDisc'
bawe_csv_path = RAW_HUMAN_DIR / 'bawe_dataset.csv'
df_bawe = ingest_bawe_dataset(bawe_corpus_dir, bawe_csv_path)
```

### `clean_bawe_dataset(bawe_csv_path, processed_dir, sample_size=None, density_threshold=0.4, drop_foreign_rows=True)`
Full pipeline for BAWE human essays (`id`, `text`, `file`, `subject`, `course`):
1. Loads CSV
2. Filters foreign language on raw text (optional)
3. Runs `clean_pipeline()` on each row
4. Drops empty rows and rows failing `placeholder_density()` / `placeholder_density_windowed()`
5. Saves `bawe_corpus_dataset_cleaned.csv` (or `bawe_corpus_dataset_cleaned_{N}.csv` when `sample_size=N`; `sample_size` is per subject when set)

Use in notebook:
```python
bawe_path = RAW_HUMAN_DIR / 'bawe_dataset.csv'
df = clean_bawe_dataset(bawe_path, PROCESSED_HUMAN_DIR, sample_size=None)
```

### `combine_cleaned_datasets(processed_ai_dir, processed_human_dir, output_dir=None, output_name='combined_dataset.csv')`
Stacks the four cleaned datasets into one labeled table for modeling:
1. Loads BAWE, MGTBench, Claude, and Gemini cleaned CSVs (skips any that are missing)
2. Normalizes to columns `text`, `label`, `source`, `subject`
3. Drops rows with empty text
4. Saves `combined_dataset.csv` under `data/processed/` (or `output_dir`)

| source | label | text column |
|--------|-------|-------------|
| bawe | 0 | `text` |
| mgtbench | 1 | `text` |
| claude | 1 | `cleaned_text` |
| gemini | 1 | `text` |

Use in notebook (after all four cleaners):
```python
PROCESSED_DIR = DATA_DIR / "processed"
df = combine_cleaned_datasets(PROCESSED_AI_DIR, PROCESSED_HUMAN_DIR, output_dir=PROCESSED_DIR)
```

---

## Placeholder Tags We Use

| Tag | What it replaces |
|-----|------------------|
| `[[EQUATION]]` | Math, LaTeX, Greek symbols |
| `[[CODE]]` | Code blocks, function calls |
| `[[CITATION]]` | `(Smith, 2020)`, `[1-3]`, `Smith et al (2000)`, `(pederson, 2002: 303)`, `Vol 1` |
| `[[COMPLEXITY]]` | O(n), Θ(n) |
| `[[URL]]` | Links |
| `[[MUSIC]]` | C-G-D-A chords |

---

## Tips for Team

1. **Always use `clean_pipeline()`** unless you have a specific reason not to
2. **Filter BEFORE cleaning** - check `is_academic_content()` and `contains_foreign_language()` first (faster)
3. **Check both density functions** after cleaning
4. **Order matters** - don't rearrange the pipeline steps
5. **Test with `sample_size=200`** before running on full dataset

---

## When You Add New Datasets

Copy a dataset cleaner in `dataset_cleaning.py` (see `clean_claude_dataset` or `clean_bawe_dataset`):

1. Load raw CSV from `data/raw/ai/` or `data/raw/human/`
2. Filter (foreign language, academic content if needed)
3. Optional dataset-specific pre-pass (e.g. `clean_markdown_formatting` for Gemini)
4. `clean_pipeline()` per row
5. Drop rows failing `placeholder_density()` and `placeholder_density_windowed()`
6. Save with `_save_cleaned_csv()` (UTF-8 + surrogate sanitization on all string columns)
7. Print summary stats like existing cleaners

Wire the new function into `utils/cleaning/__init__.py` and add a cell to `data_cleaning.ipynb`.
