"""Dataset-specific cleaning entry points."""

import ast
from pathlib import Path

import IPython.display as ipd
import pandas as pd
from tqdm.auto import tqdm

from .cleaning_methods import (
    clean_pipeline,
    contains_foreign_language,
    foreign_skip_counter,
    is_academic_content,
)
from .placeholder_density import placeholder_density, placeholder_density_windowed

def extract_claude_prompt_and_response(text):
    """
    Extracts human prompt and claude/gpt response specifically from
    Claude dataset's dictionary-style conversation strings.
    Handles plain text datasets by returning an empty prompt and raw text.
    """
    if not isinstance(text, str):
        return "", str(text)

    if text.strip().startswith('[') and "'from'" in text and "'value'" in text:
        try:
            data = ast.literal_eval(text)
            prompt = ""
            raw_response = ""

            for turn in data:
                if isinstance(turn, dict):
                    role = turn.get('from')
                    val = turn.get('value', '')

                    if role == 'human' and not prompt:
                        prompt = val
                    elif role in ('gpt', 'assistant'):
                        raw_response += val + " "

            return prompt.strip(), raw_response.strip()

        except Exception:
            prompt_match = re.search(r"\{'from':\s*'human',\s*'value':\s*\"\"?(.*?)\"\"?\}", text, flags=re.DOTALL)
            resp_match = re.search(r"\{'from':\s*'(?:gpt|assistant)',\s*'value':\s*\"\"?(.*?)\"\"?\}", text, flags=re.DOTALL)
            prompt = prompt_match.group(1) if prompt_match else ""
            raw_response = resp_match.group(1) if resp_match else text

            return prompt.strip(), raw_response.strip()

    return "", text.strip()


def clean_claude_dataset(claude_csv_path, processed_dir, sample_size=None, density_threshold=0.4, drop_foreign_rows=True):
    """
    Cleans the Claude AI dataset, filters out non-academic creative prompts,
    extracts prompt and cleaned response, filters out placeholder-dense rows
    and rows containing foreign-language content, counts tag insertions,
    displays summary & sample tables, and saves output to processed_dir.

    Args:
        claude_csv_path: Path to the raw Claude CSV file
        processed_dir: Directory path where cleaned CSV will be saved
        sample_size: Number of rows to process (None for all rows)
        density_threshold: Maximum placeholder density ratio (default 0.4)
        drop_foreign_rows: Whether to drop rows with foreign language content

    Returns:
        DataFrame with 'prompt' and 'cleaned_text' columns
    """
    if not claude_csv_path.exists():
        print(f"File not found at: {claude_csv_path}")
        return None

    foreign_skip_counter["too_short"] = 0

    print(f"Loading {'first ' + str(sample_size) if sample_size else 'all'} rows from {claude_csv_path.name}...")
    df_raw = pd.read_csv(claude_csv_path, nrows=sample_size)
    prompts = []
    cleaned_responses = []
    dropped_creative = 0
    dropped_density = 0
    dropped_locally_dense = 0
    dropped_foreign = 0

    print("Cleaning & filtering Claude dataset...")
    for raw_text in tqdm(df_raw['conversations'], desc="Processing Rows"):
        prompt, raw_response = extract_claude_prompt_and_response(str(raw_text))

        if not is_academic_content(prompt, raw_response):
            dropped_creative += 1
            continue

        if drop_foreign_rows and contains_foreign_language(raw_response):
            dropped_foreign += 1
            continue

        cleaned_resp = clean_pipeline(raw_response)

        density = placeholder_density(cleaned_resp)
        if density >= density_threshold:
            dropped_density += 1
            continue

        if placeholder_density_windowed(cleaned_resp):
            dropped_locally_dense += 1
            continue

        prompts.append(prompt)
        cleaned_responses.append(cleaned_resp)

    df_processed = pd.DataFrame({
        'prompt': prompts,
        'cleaned_text': cleaned_responses
    })

    summary_data = {
        "Metric": [
            "Total Rows Loaded",
            "Dropped (Non-Academic/Creative)",
            "Dropped (Foreign-Language Content)",
            "Dropped (Too Placeholder-Dense)",
            "Dropped (Locally Dense Cluster)",
            "Total Academic Rows Kept",
            "[[EQUATION]] Tags Inserted",
            "[[CODE]] Tags Inserted",
            "[[CITATION]] Tags Inserted",
            "[[COMPLEXITY]] Tags Inserted",
            "[[URL]] Tags Inserted",
            "[[MUSIC]] Tags Inserted",
            "Sentences Skipped (Too Short to Detect Language)"
        ],
        "Count": [
            len(df_raw),
            dropped_creative,
            dropped_foreign,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['cleaned_text'].str.count(r'\[\[EQUATION\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[CODE\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[CITATION\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[COMPLEXITY\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[URL\]\]').sum(),
            df_processed['cleaned_text'].str.count(r'\[\[MUSIC\]\]').sum(),
            foreign_skip_counter["too_short"]
        ]
    }
    df_summary = pd.DataFrame(summary_data)

    print("\n--- CLEANING SUMMARY ---")
    ipd.display(df_summary)

    filename = f"claude_dataset_cleaned_{sample_size}.csv" if sample_size else "claude_dataset_cleaned.csv"
    output_path = Path(processed_dir) / filename
    df_processed.to_csv(output_path, index=False)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 20 ROWS) ---")
    ipd.display(df_processed.head(20))

    return df_processed
def clean_mgtbench_ai_dataset(
    mgtbench_csv_path,
    processed_dir,
    sample_size=None,
    density_threshold=0.4,
    drop_foreign_rows=True,
):
    """
    Cleans the MGTBench AI CSV (id, text, file), filters foreign-language rows,
    runs clean_pipeline on each row, filters by placeholder
    density, saves to processed_dir, and returns the cleaned DataFrame.
    """
    mgtbench_csv_path = Path(mgtbench_csv_path)
    if not mgtbench_csv_path.exists():
        print(f"File not found at: {mgtbench_csv_path}")
        return None

    foreign_skip_counter["too_short"] = 0

    print(
        f"Loading {'first ' + str(sample_size) if sample_size else 'all'} rows "
        f"from {mgtbench_csv_path.name}..."
    )
    df_raw = pd.read_csv(mgtbench_csv_path, nrows=sample_size)

    ids = []
    files = []
    cleaned_texts = []
    dropped_foreign = 0
    dropped_empty = 0
    dropped_density = 0
    dropped_locally_dense = 0

    print("Cleaning & filtering MGTBench AI dataset...")
    for _, row in tqdm(df_raw.iterrows(), total=len(df_raw), desc="Processing Rows"):
        raw_text = str(row['text']).strip() if pd.notna(row['text']) else ''
        if not raw_text:
            dropped_empty += 1
            continue

        if drop_foreign_rows and contains_foreign_language(raw_text):
            dropped_foreign += 1
            continue

        cleaned = clean_pipeline(raw_text).strip()
        if not cleaned:
            dropped_empty += 1
            continue

        if placeholder_density(cleaned) >= density_threshold:
            dropped_density += 1
            continue

        if placeholder_density_windowed(cleaned):
            dropped_locally_dense += 1
            continue

        ids.append(row['id'])
        files.append(row['file'] if 'file' in row.index else '')
        cleaned_texts.append(cleaned)

    df_processed = pd.DataFrame({
        'id': ids,
        'text': cleaned_texts,
        'file': files,
    })

    summary_data = {
        'Metric': [
            'Total Rows Loaded',
            'Dropped (Foreign-Language Content)',
            'Dropped (Empty After Cleaning)',
            'Dropped (Too Placeholder-Dense)',
            'Dropped (Locally Dense Cluster)',
            'Total Rows Kept',
            '[[EQUATION]] Tags Inserted',
            '[[CODE]] Tags Inserted',
            '[[CITATION]] Tags Inserted',
            '[[COMPLEXITY]] Tags Inserted',
            '[[URL]] Tags Inserted',
            '[[MUSIC]] Tags Inserted',
            'Sentences Skipped (Too Short to Detect Language)',
            'Unique Source Files',
        ],
        'Count': [
            len(df_raw),
            dropped_foreign,
            dropped_empty,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['text'].str.count(r'\[\[EQUATION\]\]').sum(),
            df_processed['text'].str.count(r'\[\[CODE\]\]').sum(),
            df_processed['text'].str.count(r'\[\[CITATION\]\]').sum(),
            df_processed['text'].str.count(r'\[\[COMPLEXITY\]\]').sum(),
            df_processed['text'].str.count(r'\[\[URL\]\]').sum(),
            df_processed['text'].str.count(r'\[\[MUSIC\]\]').sum(),
            foreign_skip_counter['too_short'],
            df_processed['file'].nunique() if 'file' in df_processed.columns else None,
        ],
    }

    print("\n--- MGTBENCH AI CLEANING SUMMARY ---")
    ipd.display(pd.DataFrame(summary_data))

    filename = (
        f"mgtbench_ai_dataset_cleaned_{sample_size}.csv"
        if sample_size else "mgtbench_ai_dataset_cleaned.csv"
    )
    output_path = Path(processed_dir) / filename
    df_processed.to_csv(output_path, index=False)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df_processed.head(10))

    return df_processed
