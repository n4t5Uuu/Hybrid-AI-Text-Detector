"""Dataset-specific cleaning entry points."""

import ast
import re
import xml.etree.ElementTree as ET
from pathlib import Path

import IPython.display as ipd
import pandas as pd
from tqdm.auto import tqdm

from .cleaning_methods import (
    clean_markdown_formatting,
    clean_pipeline,
    contains_foreign_language,
    foreign_skip_counter,
    is_academic_content,
    strip_surrogate_characters,
)
from .placeholder_density import placeholder_density, placeholder_density_windowed
from ..text_prep import chunk_bawe_essays, count_words


def _save_cleaned_csv(df, output_path):
    """Write a cleaned dataset CSV with utf-8 and no surrogate code points."""
    df_out = df.copy()
    for col in df_out.columns:
        if df_out[col].dtype == object or pd.api.types.is_string_dtype(df_out[col]):
            df_out[col] = df_out[col].map(
                lambda v: strip_surrogate_characters(v) if isinstance(v, str) else v
            )
    df_out.to_csv(output_path, index=False, encoding='utf-8')


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
    _save_cleaned_csv(df_processed, output_path)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 20 ROWS) ---")
    ipd.display(df_processed.head(20))

    return df_processed


def _mgtbench_subject_from_file(file_path):
    """Physics_task3_resultsgpt-35.txt -> Physics."""
    name = Path(str(file_path)).name
    match = re.search(r'([A-Za-z_]+)_task', name)
    return match.group(1) if match else 'unknown'


def clean_mgtbench_ai_dataset(
    mgtbench_csv_path,
    processed_dir,
    sample_size=None,
    density_threshold=0.4,
    drop_foreign_rows=True,
):
    """
    Cleans the MGTBench AI CSV (id, text, file), filters foreign-language rows,
    runs clean_pipeline on each row, filters by placeholder density, saves one
    combined CSV to processed_dir, and returns the cleaned DataFrame.
    sample_size is applied per subject.
    """
    mgtbench_csv_path = Path(mgtbench_csv_path)
    processed_dir = Path(processed_dir)
    if not mgtbench_csv_path.exists():
        print(f"File not found at: {mgtbench_csv_path}")
        return None

    foreign_skip_counter["too_short"] = 0

    print(f"Loading all rows from {mgtbench_csv_path.name}...")
    df_raw = pd.read_csv(mgtbench_csv_path)
    df_raw['subject'] = df_raw['file'].map(_mgtbench_subject_from_file)

    if sample_size:
        df_raw = (
            df_raw.groupby('subject', sort=False, group_keys=False)
            .head(sample_size)
            .reset_index(drop=True)
        )
        print(f"Using first {sample_size} rows per subject ({len(df_raw)} rows).")

    ids = []
    files = []
    subjects = []
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
        subjects.append(row['subject'])
        cleaned_texts.append(cleaned)

    df_processed = pd.DataFrame({
        'id': ids,
        'text': cleaned_texts,
        'file': files,
        'subject': subjects,
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
            'Unique Subjects',
        ],
        'Count': [
            len(df_raw),
            dropped_foreign,
            dropped_empty,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['text'].str.count(r'\[\[EQUATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CODE\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CITATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[COMPLEXITY\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[URL\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[MUSIC\]\]').sum() if len(df_processed) else 0,
            foreign_skip_counter['too_short'],
            df_processed['subject'].nunique() if len(df_processed) else 0,
        ],
    }

    print("\n--- MGTBENCH AI CLEANING SUMMARY ---")
    ipd.display(pd.DataFrame(summary_data))

    processed_dir.mkdir(parents=True, exist_ok=True)
    for old in processed_dir.glob('mgtbench_ai_dataset_cleaned*.csv'):
        old.unlink()
        print(f"Removed old combined file: {old.name}")
    for old in processed_dir.glob('*_mgtbench.csv'):
        old.unlink()
        print(f"Removed old per-subject file: {old.name}")

    filename = (
        f"mgtbench_ai_dataset_cleaned_{sample_size}.csv"
        if sample_size
        else "mgtbench_ai_dataset_cleaned.csv"
    )
    output_path = processed_dir / filename
    _save_cleaned_csv(df_processed, output_path)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df_processed.head(10))

    return df_processed


def clean_mgtbench_human_dataset(
    mgtbench_human_csv_path,
    processed_dir,
    sample_size=None,
    density_threshold=0.4,
    drop_foreign_rows=True,
):
    """
    Clean the MGTBench human originals (text, meta, subject, file).

    Same steps as the MGTBench AI cleaner: skip foreign-language rows, run
    clean_pipeline, drop rows that are mostly placeholders, then save one CSV.
    The raw rows have no id, so id is the row's position inside its own file
    (the same numbering the polished AI rows use, which is not yet verified
    as a pairing). Kept apart from combined_dataset.csv on purpose: this is
    the separate robustness experiment, not the student-essay corpus.
    sample_size is applied per subject.
    """
    mgtbench_human_csv_path = Path(mgtbench_human_csv_path)
    processed_dir = Path(processed_dir)
    if not mgtbench_human_csv_path.exists():
        print(f"File not found at: {mgtbench_human_csv_path}")
        return None

    foreign_skip_counter["too_short"] = 0

    print(f"Loading all rows from {mgtbench_human_csv_path.name}...")
    df_raw = pd.read_csv(mgtbench_human_csv_path)
    missing = {'text', 'subject', 'file'} - set(df_raw.columns)
    if missing:
        print(f"Missing columns {missing}: re-run the MGTBench human cell in data_ingestion.ipynb.")
        return None
    # Position inside the source file, taken before any sampling.
    df_raw['id'] = df_raw.groupby('file').cumcount()

    if sample_size:
        df_raw = (
            df_raw.groupby('subject', sort=False, group_keys=False)
            .head(sample_size)
            .reset_index(drop=True)
        )
        print(f"Using first {sample_size} rows per subject ({len(df_raw)} rows).")

    ids = []
    files = []
    subjects = []
    cleaned_texts = []
    dropped_foreign = 0
    dropped_empty = 0
    dropped_density = 0
    dropped_locally_dense = 0

    print("Cleaning & filtering MGTBench human dataset...")
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
        files.append(row['file'])
        subjects.append(row['subject'])
        cleaned_texts.append(cleaned)

    df_processed = pd.DataFrame({
        'id': ids,
        'text': cleaned_texts,
        'file': files,
        'subject': subjects,
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
            'Unique Subjects',
        ],
        'Count': [
            len(df_raw),
            dropped_foreign,
            dropped_empty,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['text'].str.count(r'\[\[EQUATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CODE\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CITATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[COMPLEXITY\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[URL\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[MUSIC\]\]').sum() if len(df_processed) else 0,
            foreign_skip_counter['too_short'],
            df_processed['subject'].nunique() if len(df_processed) else 0,
        ],
    }

    print("\n--- MGTBENCH HUMAN CLEANING SUMMARY ---")
    ipd.display(pd.DataFrame(summary_data))

    processed_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"mgtbench_human_dataset_cleaned_{sample_size}.csv"
        if sample_size
        else "mgtbench_human_dataset_cleaned.csv"
    )
    output_path = processed_dir / filename
    _save_cleaned_csv(df_processed, output_path)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df_processed.head(10))

    return df_processed


def clean_gemini_dataset(
    gemini_csv_path,
    processed_dir,
    sample_size=None,
    density_threshold=0.4,
    drop_foreign_rows=True,
):
    """
    Cleans the Gemini essays CSV (text, label, prompt_name, source, RDizzl3_seven),
    filters foreign-language rows, strips markdown, runs clean_pipeline on each row,
    filters by placeholder density, saves one combined CSV to processed_dir, and
    returns the cleaned DataFrame.
    """
    gemini_csv_path = Path(gemini_csv_path)
    processed_dir = Path(processed_dir)
    if not gemini_csv_path.exists():
        print(f"File not found at: {gemini_csv_path}")
        return None

    foreign_skip_counter['too_short'] = 0

    print(f"Loading {'first ' + str(sample_size) if sample_size else 'all'} rows from {gemini_csv_path.name}...")
    df_raw = pd.read_csv(gemini_csv_path, nrows=sample_size)

    texts = []
    labels = []
    prompt_names = []
    sources = []
    rdizzl3_seven = []
    dropped_foreign = 0
    dropped_empty = 0
    dropped_density = 0
    dropped_locally_dense = 0

    print("Cleaning & filtering Gemini dataset...")
    for _, row in tqdm(df_raw.iterrows(), total=len(df_raw), desc="Processing Rows"):
        raw_text = str(row['text']).strip() if pd.notna(row['text']) else ''
        if not raw_text:
            dropped_empty += 1
            continue

        if drop_foreign_rows and contains_foreign_language(raw_text):
            dropped_foreign += 1
            continue

        cleaned = clean_markdown_formatting(raw_text).strip()
        cleaned = clean_pipeline(cleaned).strip()
        if not cleaned:
            dropped_empty += 1
            continue

        if placeholder_density(cleaned) >= density_threshold:
            dropped_density += 1
            continue

        if placeholder_density_windowed(cleaned):
            dropped_locally_dense += 1
            continue

        texts.append(cleaned)
        labels.append(row['label'])
        prompt_names.append(row['prompt_name'] if pd.notna(row.get('prompt_name')) else '')
        sources.append(row['source'] if pd.notna(row.get('source')) else '')
        rdizzl3_seven.append(row['RDizzl3_seven'] if pd.notna(row.get('RDizzl3_seven')) else '')

    df_processed = pd.DataFrame({
        'text': texts,
        'label': labels,
        'prompt_name': prompt_names,
        'source': sources,
        'RDizzl3_seven': rdizzl3_seven,
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
        ],
        'Count': [
            len(df_raw),
            dropped_foreign,
            dropped_empty,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['text'].str.count(r'\[\[EQUATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CODE\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CITATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[COMPLEXITY\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[URL\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[MUSIC\]\]').sum() if len(df_processed) else 0,
            foreign_skip_counter['too_short'],
        ],
    }

    print("\n--- GEMINI CLEANING SUMMARY ---")
    ipd.display(pd.DataFrame(summary_data))

    processed_dir.mkdir(parents=True, exist_ok=True)
    for old in processed_dir.glob('gemini_essays_v1_cleaned*.csv'):
        old.unlink()
        print(f"Removed old combined file: {old.name}")

    filename = (
        f"gemini_essays_v1_cleaned_{sample_size}.csv"
        if sample_size
        else "gemini_essays_v1_cleaned.csv"
    )
    output_path = processed_dir / filename
    _save_cleaned_csv(df_processed, output_path)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df_processed.head(10))

    return df_processed


def _bawe_p_value(parent, n_attr):
    """Return text of <p n="..."> under parent, or empty string."""
    if parent is None:
        return ''
    for p in parent.findall('p'):
        if p.get('n') == n_attr:
            return ''.join(p.itertext()).strip()
    return ''


def _bawe_element_text(elem):
    """Concatenate all text under an XML element."""
    return ' '.join(''.join(elem.itertext()).split())


def _bawe_subject(discipline, disciplinary_group, folder_name):
    """Disambiguate the three 'other' discipline folders."""
    if discipline.lower() == 'other' or folder_name.lower() == 'other':
        group = disciplinary_group or folder_name
        return f"{group}_other" if group else 'other'
    return discipline or folder_name.replace('_', ' ')


def parse_bawe_xml(xml_path, corpus_root=None):
    """
    Parse one BAWE TEI XML file into id, text, file, subject, course.

    Returns None if the file cannot be parsed or has no body text.
    """
    xml_path = Path(xml_path)
    try:
        raw = xml_path.read_text(encoding='utf-8')
        raw = re.sub(r'<!DOCTYPE[^>]*>', '', raw, count=1)
        root = ET.fromstring(raw)
    except (ET.ParseError, OSError, UnicodeDecodeError):
        return None

    source_desc = root.find('.//sourceDesc')
    person = root.find('.//person')
    body = root.find('.//body')
    if body is None:
        return None

    text = _bawe_element_text(body)
    if not text:
        return None

    discipline = _bawe_p_value(source_desc, 'discipline')
    disciplinary_group = _bawe_p_value(source_desc, 'disciplinary group')
    course = _bawe_p_value(person, 'course')

    folder_name = xml_path.parent.name
    if corpus_root is not None:
        try:
            rel_parts = xml_path.relative_to(corpus_root).parts
            if not disciplinary_group and rel_parts:
                disciplinary_group = rel_parts[0]
            if len(rel_parts) > 1:
                folder_name = rel_parts[1]
            file_rel = '/'.join(rel_parts)
        except ValueError:
            file_rel = xml_path.name
    else:
        file_rel = xml_path.name

    subject = _bawe_subject(discipline, disciplinary_group, folder_name)

    return {
        'id': xml_path.stem,
        'text': text,
        'file': file_rel,
        'subject': subject,
        'course': course,
    }


def ingest_bawe_dataset(corpus_dir, output_path):
    """
    Walk CORPUS_ByDisc XML files and write one raw CSV (id, text, file, subject, course).

    Skips unreadable files and prints a summary count.
    """
    corpus_dir = Path(corpus_dir)
    output_path = Path(output_path)
    if not corpus_dir.exists():
        print(f"BAWE corpus directory not found: {corpus_dir}")
        return None

    xml_files = sorted(corpus_dir.rglob('*.xml'))
    rows = []
    skipped = 0

    print(f"Parsing {len(xml_files)} BAWE XML files from {corpus_dir.name}...")
    for xml_path in tqdm(xml_files, desc="Parsing XML"):
        record = parse_bawe_xml(xml_path, corpus_root=corpus_dir)
        if record is None:
            skipped += 1
            continue
        rows.append(record)

    df = pd.DataFrame(rows, columns=['id', 'text', 'file', 'subject', 'course'])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_path, index=False, encoding='utf-8')

    print(f"\n--- BAWE INGEST SUMMARY ---")
    print(f"  XML files found:     {len(xml_files)}")
    print(f"  Rows written:        {len(df)}")
    print(f"  Skipped (unreadable): {skipped}")
    print(f"  Unique subjects:     {df['subject'].nunique()}")
    print(f"  Saved to:            {output_path.resolve()}")

    return df


def clean_bawe_dataset(
    bawe_csv_path,
    processed_dir,
    sample_size=None,
    density_threshold=0.4,
    drop_foreign_rows=True,
):
    """
    Cleans the BAWE CSV (id, text, file, subject, course), filters foreign-language rows,
    runs clean_pipeline on each row, filters by placeholder density, saves one combined
    CSV to processed_dir, and returns the cleaned DataFrame.
    sample_size is applied per subject when set.
    """
    bawe_csv_path = Path(bawe_csv_path)
    processed_dir = Path(processed_dir)
    if not bawe_csv_path.exists():
        print(f"File not found at: {bawe_csv_path}")
        return None

    foreign_skip_counter['too_short'] = 0

    print(f"Loading all rows from {bawe_csv_path.name}...")
    df_raw = pd.read_csv(bawe_csv_path)

    if sample_size:
        df_raw = (
            df_raw.groupby('subject', sort=False, group_keys=False)
            .head(sample_size)
            .reset_index(drop=True)
        )
        print(f"Using first {sample_size} rows per subject ({len(df_raw)} rows).")

    ids = []
    files = []
    subjects = []
    courses = []
    cleaned_texts = []
    dropped_foreign = 0
    dropped_empty = 0
    dropped_density = 0
    dropped_locally_dense = 0

    print("Cleaning & filtering BAWE dataset...")
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
        subjects.append(row['subject'])
        courses.append(row['course'] if pd.notna(row.get('course')) else '')
        cleaned_texts.append(cleaned)

    df_processed = pd.DataFrame({
        'id': ids,
        'text': cleaned_texts,
        'file': files,
        'subject': subjects,
        'course': courses,
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
            'Unique Subjects',
        ],
        'Count': [
            len(df_raw),
            dropped_foreign,
            dropped_empty,
            dropped_density,
            dropped_locally_dense,
            len(df_processed),
            df_processed['text'].str.count(r'\[\[EQUATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CODE\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[CITATION\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[COMPLEXITY\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[URL\]\]').sum() if len(df_processed) else 0,
            df_processed['text'].str.count(r'\[\[MUSIC\]\]').sum() if len(df_processed) else 0,
            foreign_skip_counter['too_short'],
            df_processed['subject'].nunique() if len(df_processed) else 0,
        ],
    }

    print("\n--- BAWE CLEANING SUMMARY ---")
    ipd.display(pd.DataFrame(summary_data))

    processed_dir.mkdir(parents=True, exist_ok=True)
    filename = (
        f"bawe_corpus_dataset_cleaned_{sample_size}.csv"
        if sample_size
        else "bawe_corpus_dataset_cleaned.csv"
    )
    output_path = processed_dir / filename
    _save_cleaned_csv(df_processed, output_path)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df_processed.head(10))

    return df_processed


def _row_group_ids(source, df):
    """One id per row: source:file:id when the cleaned CSV has both, else the row position."""
    if 'file' in df.columns and 'id' in df.columns:
        return (source + ':' + df['file'].astype(str) + ':' + df['id'].astype(str)).tolist()
    return [f'{source}:{i}' for i in range(len(df))]


def combine_cleaned_datasets(
    processed_ai_dir,
    processed_human_dir,
    output_dir=None,
    output_name='combined_dataset.csv',
    chunk_human=True,
    min_chunk_words=75,
    max_chunk_words=520,
    random_state=42,
):
    """
    Stack the cleaned datasets into one labeled table for modeling.

    Output columns: text, label, source, subject, group_id
    - label: 0 = human (BAWE, MGTBench human), 1 = AI (MGTBench, Claude, Gemini)
    - source: bawe | mgtbench_human | mgtbench | claude | gemini
    - group_id: rows that must land in the same split. Passages cut from one
      BAWE essay share an id; every other row gets its own.

    The MGTBench human texts are only added when their cleaned file exists. They
    are the originals GPT-3.5 polished into the MGTBench AI rows. Exact duplicate
    originals are dropped, and each original is cut to an AI-like length (its
    opening passage is kept). Linking each original to its polished version
    happens later, in data_splitting.ipynb. Identical texts left after combining
    are dropped as well.

    BAWE essays are about ten times longer than the AI texts, so with
    chunk_human=True we cut each essay into passages whose lengths follow the
    AI word counts (see chunk_bawe_essays). Set it to False to keep whole essays.
    """
    processed_ai_dir = Path(processed_ai_dir)
    processed_human_dir = Path(processed_human_dir)
    output_dir = Path(output_dir) if output_dir else processed_ai_dir.parent

    sources = {
        'bawe': {
            'path': processed_human_dir / 'bawe_corpus_dataset_cleaned.csv',
            'label': 0,
            'source': 'bawe',
        },
        'mgtbench_human': {
            'path': processed_human_dir / 'mgtbench_human_dataset_cleaned.csv',
            'label': 0,
            'source': 'mgtbench_human',
        },
        'mgtbench': {
            'path': processed_ai_dir / 'mgtbench_ai_dataset_cleaned.csv',
            'label': 1,
            'source': 'mgtbench',
        },
        'claude': {
            'path': processed_ai_dir / 'claude_dataset_cleaned.csv',
            'label': 1,
            'source': 'claude',
        },
        'gemini': {
            'path': processed_ai_dir / 'gemini_essays_v1_cleaned.csv',
            'label': 1,
            'source': 'gemini',
        },
    }

    frames = {}
    bawe_essays = None
    mgtbench_human = None
    missing = []
    for name, meta in sources.items():
        path = meta['path']
        if not path.exists():
            missing.append(str(path))
            continue

        df = pd.read_csv(path)
        if name == 'claude':
            text_col = 'cleaned_text' if 'cleaned_text' in df.columns else 'text'
            rows = pd.DataFrame({
                'text': df[text_col].astype(str),
                'label': meta['label'],
                'source': meta['source'],
                'subject': '',
                'group_id': _row_group_ids(name, df),
            })
        elif name == 'gemini':
            rows = pd.DataFrame({
                'text': df['text'].astype(str),
                'label': meta['label'],
                'source': meta['source'],
                'subject': df['prompt_name'].fillna('').astype(str) if 'prompt_name' in df.columns else '',
                'group_id': _row_group_ids(name, df),
            })
        elif name == 'bawe':
            # Hold the essays back: how we cut them depends on the AI lengths below.
            bawe_essays = pd.DataFrame({
                'id': df['id'].astype(str),
                'text': df['text'].astype(str),
                'subject': df['subject'].fillna('').astype(str),
            })
            continue
        elif name == 'mgtbench_human':
            # Hold the originals back too: they are cut to AI lengths below.
            # The same text can appear twice in the raw files; keep the first copy
            # so a duplicate can never sit in both train and test.
            mgtbench_human = pd.DataFrame({
                'id': _row_group_ids(name, df),
                'text': df['text'].astype(str),
                'subject': df['subject'].fillna('').astype(str) if 'subject' in df.columns else '',
            })
            n_before = len(mgtbench_human)
            mgtbench_human = mgtbench_human.drop_duplicates('text').reset_index(drop=True)
            print(f"MGTBench human: dropped {n_before - len(mgtbench_human):,} exact duplicate originals.")
            continue
        else:
            rows = pd.DataFrame({
                'text': df['text'].astype(str),
                'label': meta['label'],
                'source': meta['source'],
                'subject': df['subject'].fillna('').astype(str) if 'subject' in df.columns else '',
                'group_id': _row_group_ids(name, df),
            })
        frames[name] = rows

    # Only AI rows set the target lengths for the human passages.
    ai_frames = [f['text'] for f in frames.values() if (f['label'] == 1).all()]
    ai_texts = pd.concat(ai_frames, ignore_index=True) if ai_frames else []

    if mgtbench_human is not None:
        if chunk_human and len(ai_texts):
            # The originals are about twice as long as the polished texts (History,
            # Physics and Statistics run to over 800 words), so cut each to an AI-like
            # length and keep its opening passage. One passage per original keeps the
            # human count steady and the group_id the original's own.
            ai_word_counts = [count_words(t) for t in ai_texts]
            passages = chunk_bawe_essays(
                mgtbench_human,
                ai_word_counts,
                min_words=min_chunk_words,
                max_words=max_chunk_words,
                random_state=random_state,
            )
            passages = passages[passages['chunk_idx'] == 0]
            print(
                f"MGTBench human cutting: {len(mgtbench_human):,} originals -> {len(passages):,} passages "
                f"(median {passages['text'].map(count_words).median():.0f} words vs "
                f"{pd.Series(ai_word_counts).median():.0f} for AI rows)"
            )
        else:
            if chunk_human:
                print('No AI datasets found, so MGTBench human originals are kept whole.')
            passages = mgtbench_human
        frames['mgtbench_human'] = pd.DataFrame({
            'text': passages['text'].to_numpy(),
            'label': sources['mgtbench_human']['label'],
            'source': sources['mgtbench_human']['source'],
            'subject': passages['subject'].to_numpy(),
            'group_id': passages['id'].to_numpy(),
        })

    if bawe_essays is not None:
        if chunk_human and len(ai_texts):
            # Cut essays so human passages have the same length mix as the AI rows.
            ai_word_counts = [count_words(t) for t in ai_texts]
            passages = chunk_bawe_essays(
                bawe_essays,
                ai_word_counts,
                min_words=min_chunk_words,
                max_words=max_chunk_words,
                random_state=random_state,
            )
            print(
                f"BAWE chunking: {len(bawe_essays):,} essays -> {len(passages):,} passages "
                f"(median {passages['text'].map(count_words).median():.0f} words vs "
                f"{pd.Series(ai_word_counts).median():.0f} for AI rows)"
            )
        else:
            if chunk_human:
                print('No AI datasets found, so BAWE essays are kept whole.')
            passages = bawe_essays
        frames['bawe'] = pd.DataFrame({
            'text': passages['text'],
            'label': sources['bawe']['label'],
            'source': sources['bawe']['source'],
            'subject': passages['subject'],
            'group_id': 'bawe:' + passages['id'],
        })

    if missing:
        print('Missing cleaned files (run the per-dataset cells first):')
        for path in missing:
            print(f'  - {path}')
    if not frames:
        print('No cleaned datasets found to combine.')
        return None

    # Keep the usual row order: bawe, mgtbench, claude, gemini.
    df_combined = pd.concat([frames[name] for name in sources if name in frames], ignore_index=True)
    df_combined = df_combined[df_combined['text'].str.strip().astype(bool)]
    # A few identical texts also sit inside the other sources; keep the first copy.
    n_before = len(df_combined)
    df_combined = df_combined.drop_duplicates('text').reset_index(drop=True)
    print(f"Dropped {n_before - len(df_combined):,} more exact duplicate texts after combining.")
    df_combined = df_combined[['text', 'label', 'source', 'subject', 'group_id']]

    summary = df_combined.groupby(['source', 'label'], as_index=False).size()
    summary.columns = ['source', 'label', 'rows']

    print('\n--- COMBINED DATASET SUMMARY ---')
    ipd.display(summary)
    print(f"\nTotal rows: {len(df_combined):,}")
    print(f"Human (label=0): {(df_combined['label'] == 0).sum():,}")
    print(f"AI (label=1):    {(df_combined['label'] == 1).sum():,}")

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / output_name
    _save_cleaned_csv(df_combined, output_path)
    print(f"\nSuccessfully saved combined dataset to:\n  {output_path.resolve()}")

    print('\n--- SAMPLE COMBINED DATA (FIRST 10 ROWS) ---')
    ipd.display(df_combined.head(10))

    return df_combined
