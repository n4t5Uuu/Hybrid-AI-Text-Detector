# Text Cleaning Functions Reference

**Package:** `src/utils/cleaning/`

- `cleaning_methods.py` — regex cleaners, filters, `clean_pipeline`, constants
- `placeholder_density.py` — row density filters
- `dataset_cleaning.py` — `clean_claude_dataset`, `clean_mgtbench_ai_dataset`

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
Cleans numeric refs (`[1]`, `[1-3]`), parenthetical author-date (`(Smith, 2020)`, `(pederson, 2002: 303; see also Hargeaves, 1994)`, `(Smith & Jones, 2020)`, `(Jones, 1990, cited in Smith, 2000)`), narrative/inverted forms (`Smith et al (2000)`, `Green, E. et al (2000)`, `Pilkingtonm, H. (2007)`), edited-volume secondary (`Jones C & Baker G in Lewis J (ed) 1994`), conservative MLA author-page (`(Nietzsche 9)`), and numbered volume markers (`Vol 1`, `Volume 2`, `vol. 12, no. 3`). Skips `(Figure 1)`, `(Table 2)`, `(see below)`, and prose like `volume of water`.

### `clean_url(text)` → `[[URL]]`
Cleans: `https://...`, `www....`

### `clean_music_notation(text)` → `[[MUSIC]]`
Cleans: `C-G-D-A`, `F#-Bb-D`

### `clean_list_numbering(text)`
Removes: `1.`, `a)` / `b.` after start/newline/colon (not after `a + b. Step`), `i.`, `- bullet`

### `strip_reference_list(text)`
Cuts off everything after "References:" or "Bibliography:"

### `merge_continuous_equations(text, tag='[[EQUATION]]')`
Merges adjacent placeholders separated by operators, short math, trig names, or (for CODE) `return`/`returns`  
Example: `[[EQUATION]] + [[EQUATION]]` → `[[EQUATION]]`  
Example: `[[CODE]] returns [[CODE]]` → `[[CODE]]`

### `mop_up_leftover_math_and_code(text)`
Last-pass fold for leftovers next to tags: trig, `dΦ/dt`, both sides of `=`, `±`, `2a`/`4ac`/`x + c`, named quantities (`Mass (m) = 1,500 kg`), `(xn, yn, zn)`, unit products, `[[CODE]] [[EQUATION]] [[CODE]]` sandwiches

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
5. Saves `mgtbench_ai_dataset_cleaned.csv` with summary stats (uses `[[EQUATION]]` tags like Claude)

Use in notebook:
```python
mgtbench_ai_path = RAW_AI_DIR / 'mgtbench_ai_dataset.csv'
df = clean_mgtbench_ai_dataset(mgtbench_ai_path, PROCESSED_AI_DIR, sample_size=None)
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

Copy the `clean_claude_dataset()` pattern:

```python
def clean_your_dataset(csv_path, output_dir, sample_size=None):
    df = pd.read_csv(csv_path, nrows=sample_size)
    
    cleaned = []
    for text in tqdm(df['text_column']):
        # Filter
        if not is_academic_content(text=text):
            continue
        if contains_foreign_language(text):
            continue
        
        # Clean
        cleaned_text = clean_pipeline(text)
        
        # Density check
        if placeholder_density(cleaned_text) >= 0.4:
            continue
        if placeholder_density_windowed(cleaned_text):
            continue
        
        cleaned.append(cleaned_text)
    
    # Save
    output = output_dir / "your_dataset_cleaned.csv"
    pd.DataFrame({'cleaned_text': cleaned}).to_csv(output, index=False)
```
