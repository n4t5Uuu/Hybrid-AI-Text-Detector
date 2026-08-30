# Text Cleaning Functions Reference

**File:** `src/utils/text_cleaning.py`

Quick reference for all the cleaning functions we use in the project. Everything here replaces noise with placeholder tags like `[[EQUATION]]`, `[[CODE]]`, etc.

---

## Math Cleaning Functions

### `clean_math_texts(text)`
Removes LaTeX and mathematical notation → `[[EQUATION]]`

Cleans: LaTeX environments, `$$math$$`, `$inline$`, `\[\]`, integrals, derivatives, comparisons, Greek letters

### `clean_bare_expressions(text)`  
Catches leftover math that `clean_math_texts()` missed

Cleans: Factorials `n!`, fractions `1/2`, parenthesized expressions `(x+y)`

### `clean_residual_math_noise(text)`
Final pass for Unicode math symbols

Cleans: `α β Σ ∞`, `f(x)`, `|x|`, `√x`, `²³`, `±`, subscripts like `xn+1`

---

## Code Cleaning Functions

### `clean_code_texts(text)`
Removes markdown code blocks → `[[CODE]]`

Cleans: `` ```code``` ``, `` `inline` ``

### `clean_pseudocode_and_diagrams(text)`
Catches non-markdown code

Cleans: `[Start] -> [End]`, `class Foo {}`, `object.method()`, Python/JS keywords

---

## Other Cleaning Functions

### `clean_complexity_notation(text)` → `[[COMPLEXITY]]`
Cleans: `O(n)`, `O(log n)`, `Θ(n)`, `Ω(n²)`

### `clean_citations(text)` → `[[CITATION]]`
Cleans: `(Smith, 2020)`, `[1]`, `Smith et al. (2020)`

### `clean_url(text)` → `[[URL]]`
Cleans: `https://...`, `www....`

### `clean_music_notation(text)` → `[[MUSIC]]`
Cleans: `C-G-D-A`, `F#-Bb-D`

### `clean_list_numbering(text)`
Removes: `1.`, `a)`, `i.`, `- bullet`

### `strip_reference_list(text)`
Cuts off everything after "References:" or "Bibliography:"

### `merge_continuous_equations(text, tag='[[EQUATION]]')`
Merges adjacent placeholders separated by non-prose fragments  
Example: `[[EQUATION]] + [[EQUATION]]` → `[[EQUATION]]`

---

## Filter Functions

### `is_academic_content(prompt="", text="")`
Returns `False` if text is creative/non-academic

Filters out: poems, stories, scripts, ads, letters, stage directions

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
1. URLs → code/diagrams → markdown code → music → complexity
2. References → citations → list markers
3. Math (3 passes: bare → full → residual)
4. Merge adjacent tags

Example:
```python
from utils.text_cleaning import clean_pipeline

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

---

## Placeholder Tags We Use

| Tag | What it replaces |
|-----|------------------|
| `[[EQUATION]]` | Math, LaTeX, Greek symbols |
| `[[CODE]]` | Code blocks, function calls |
| `[[CITATION]]` | (Smith, 2020), [1] |
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
