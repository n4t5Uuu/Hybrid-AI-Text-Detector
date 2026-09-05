"""Dataset-specific cleaning entry points."""

import ast
import re
import xml.etree.ElementTree as ET
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
    runs clean_pipeline on each row, filters by placeholder
    density, saves one CSV per subject to processed_dir, and returns the
    cleaned DataFrame. sample_size is applied per subject.
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

    for subject, group in df_processed.groupby('subject', sort=False):
        output_path = processed_dir / f"{str(subject).lower()}_mgtbench.csv"
        group.to_csv(output_path, index=False)
        print(f"Saved {len(group)} rows -> {output_path.resolve()}")

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
    df_processed.to_csv(output_path, index=False)
    print(f"\nSuccessfully saved cleaned dataset ({len(df_processed)} rows) to:\n  {output_path.resolve()}")

    print("\n--- SAMPLE CLEANED DATA (FIRST 10 ROWS) ---")
    ipd.display(df_processed.head(10))

    return df_processed
